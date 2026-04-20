#!/usr/bin/env python3
"""
Executes Cortex Code in headless mode with streaming output parsing.
Uses --output-format stream-json for streaming results.
Handles tool use events and final results.
"""

import json
import subprocess
import sys
import argparse
from typing import Dict, Optional


# Prompt-level security envelope instructions.
# --disallowed-tools is NOT used because:
#   1. --dangerously-allow-all-tool-calls overrides --disallowed-tools
#   2. --disallowed-tools doesn't work for sql_execute (non-builtin tool)
# Instead, envelope constraints are injected into the prompt where the LLM
# can follow them. This is advisory, not enforced at the CLI level.
ENVELOPE_INSTRUCTIONS = {
    "RO": (
        "# Security Envelope: READ-ONLY\n"
        "You are operating in READ-ONLY mode.\n"
        "ALLOWED: SELECT, SHOW, DESCRIBE, EXPLAIN queries. "
        "Reading files, searching, grepping.\n"
        "NOT ALLOWED: DDL (CREATE, ALTER, DROP), DML (INSERT, UPDATE, DELETE, MERGE), "
        "writing/editing/creating files, destructive bash (rm, sudo, chmod 777, git push --force).\n"
        "If the user's request requires write operations, explain what you would do "
        "and provide the SQL/commands for them to run manually.\n"
    ),
    "RW": (
        "# Security Envelope: READ-WRITE\n"
        "You are operating in READ-WRITE mode.\n"
        "ALLOWED: All SQL (SELECT, CREATE, ALTER, DROP, INSERT, UPDATE, DELETE), "
        "reading/writing files, bash commands.\n"
        "NOT ALLOWED: Destructive bash (rm -rf, sudo, chmod 777, git push --force, "
        "git reset --hard). Do not delete data or drop production tables without "
        "explicit confirmation in the prompt.\n"
    ),
    "RESEARCH": (
        "# Security Envelope: RESEARCH\n"
        "You are operating in RESEARCH mode.\n"
        "ALLOWED: SELECT, SHOW, DESCRIBE queries. Reading files, searching, "
        "web_fetch, web_search.\n"
        "NOT ALLOWED: DDL, DML, writing/editing files, destructive bash.\n"
    ),
    "DEPLOY": (
        "# Security Envelope: DEPLOY\n"
        "You are operating in DEPLOY mode with full access.\n"
        "All tools and operations are available. Use good judgment.\n"
    ),
}


def build_envelope_prompt(prompt: str, envelope: str) -> str:
    """Prepend security envelope instructions to the user prompt."""
    instructions = ENVELOPE_INSTRUCTIONS.get(envelope, "")
    if instructions:
        return f"{instructions}\n# User Request\n{prompt}"
    return prompt


def execute_cortex_streaming(prompt: str, connection: Optional[str] = None,
                             envelope: str = "RW") -> Dict:
    """
    Execute Cortex with streaming JSON output in programmatic mode.

    Uses --dangerously-allow-all-tool-calls for headless auto-approval of
    all tool calls (including DDL). Security envelope is enforced via
    prompt-level instructions, not CLI flags.

    Args:
        prompt: The enriched prompt to send to Cortex
        connection: Optional Snowflake connection name
        envelope: Security envelope mode (RO, RW, RESEARCH, DEPLOY)

    Returns:
        Dictionary with execution results
    """
    # Prepend envelope instructions to the prompt
    envelope_prompt = build_envelope_prompt(prompt, envelope)

    # Build command for headless execution.
    # -p flag + stdin=DEVNULL: standalone router pattern (no stream-json stdin).
    # --input-format stream-json: programmatic mode.
    # --dangerously-allow-all-tool-calls: REQUIRED for DDL and bash to work.
    #   Without this flag, DDL (CREATE/ALTER/DROP) and bash commands trigger
    #   interactive permission prompts that timeout in headless mode.
    cmd = [
        "cortex",
        "-p", envelope_prompt,
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--dangerously-allow-all-tool-calls",
    ]

    # Add connection if specified
    if connection:
        cmd.extend(["-c", connection])

    debug_cmd = f"cortex -p \"...\" --output-format stream-json --input-format stream-json --dangerously-allow-all-tool-calls (envelope={envelope})"
    if connection:
        debug_cmd += f" -c {connection}"
    print(debug_cmd, file=sys.stderr)

    try:
        # Start process. stdin=DEVNULL is critical: --input-format stream-json
        # puts Cortex in programmatic mode but it must not wait on stdin for
        # approval responses — closing it lets auto-approval proceed immediately.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )

        results = {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": None
        }

        # Read streaming output
        for line in process.stdout:
            if not line.strip():
                continue

            try:
                event = json.loads(line)
                results["events"].append(event)

                event_type = event.get("type")

                # Extract session ID
                if event_type == "system" and event.get("subtype") == "init":
                    results["session_id"] = event.get("session_id")
                    print(f"Started Cortex session: {results['session_id']}", file=sys.stderr)

                # Handle assistant responses
                elif event_type == "assistant":
                    message = event.get("message", {})
                    content = message.get("content", [])

                    for item in content:
                        if item.get("type") == "text":
                            print(f"[Cortex] {item.get('text', '')}", file=sys.stderr)

                        elif item.get("type") == "tool_use":
                            tool_name = item.get("name")
                            print(f"[Cortex] Using tool: {tool_name}", file=sys.stderr)

                # Handle permission requests (via user messages with tool_result containing denials)
                elif event_type == "user":
                    message = event.get("message", {})
                    content = message.get("content", [])

                    for item in content:
                        if item.get("type") == "tool_result":
                            tool_content = item.get("content", "")
                            if "Permission denied" in tool_content or "denied" in tool_content.lower():
                                results["permission_requests"].append({
                                    "tool_use_id": item.get("tool_use_id"),
                                    "content": tool_content
                                })
                                print(f"[Cortex] Permission request detected: {tool_content}", file=sys.stderr)

                # Handle final result — break to stop blocking on stdout
                elif event_type == "result":
                    results["final_result"] = event.get("result")
                    print(f"[Cortex] Result received.", file=sys.stderr)
                    break  # Cortex is done; exit read loop

            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line: {line[:100]}... Error: {e}", file=sys.stderr)
                continue

        # Wait for process to complete
        process.wait()

        # Check for errors
        if process.returncode != 0:
            stderr_output = process.stderr.read()
            results["error"] = stderr_output
            print(f"Error: Cortex exited with code {process.returncode}", file=sys.stderr)
            print(f"Stderr: {stderr_output}", file=sys.stderr)

        return results

    except Exception as e:
        return {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": str(e)
        }


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Execute Cortex Code headlessly")
    parser.add_argument("--prompt", required=True, help="Prompt to send to Cortex")
    parser.add_argument("--connection", "-c", help="Snowflake connection name")
    parser.add_argument("--envelope", default="RW",
                       choices=["RO", "RW", "RESEARCH", "DEPLOY"],
                       help="Security envelope mode (default: RW)")
    args = parser.parse_args()

    # Execute Cortex
    results = execute_cortex_streaming(
        args.prompt,
        connection=args.connection,
        envelope=args.envelope,
    )

    # Output results as JSON
    print(json.dumps(results, indent=2))

    # Exit with appropriate code
    if results.get("error"):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
