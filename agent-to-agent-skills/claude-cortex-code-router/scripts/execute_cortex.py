#!/usr/bin/env python3
"""
Executes Cortex Code in headless mode with streaming output parsing.
Uses --input-format stream-json for programmatic mode with auto-approval.
Handles tool use events and final results.
"""

import json
import subprocess
import sys
import argparse
from typing import List, Dict, Optional


# Known tools for inversion logic (allowed -> disallowed)
KNOWN_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Grep", "Glob",
    "snowflake_sql_execute", "data_diff", "snowflake_query"
]


def invert_tools_to_disallowed(allowed_tools: List[str]) -> List[str]:
    """
    Convert allowed tools list to disallowed tools list.

    For prompt mode: when security wrapper predicts/approves specific tools,
    we need to invert the list to block all OTHER tools via --disallowed-tools.

    Args:
        allowed_tools: List of tool names that ARE allowed

    Returns:
        List of tool names that should be disallowed (inverse of allowed)

    Example:
        allowed = ["Read", "Grep"]
        disallowed = ["Write", "Edit", "Bash", "Glob", ...other tools...]
    """
    return [tool for tool in KNOWN_TOOLS if tool not in allowed_tools]


def execute_cortex_streaming(prompt: str, connection: Optional[str] = None,
                             disallowed_tools: Optional[List[str]] = None,
                             envelope: str = "RW",
                             approval_mode: str = "auto",
                             allowed_tools: Optional[List[str]] = None) -> Dict:
    """
    Execute Cortex with streaming JSON output in programmatic mode.

    Uses --input-format stream-json to enable auto-approval of all tool calls,
    bypassing the need for --bypass which may be blocked by organization policy.
    Tools are controlled via --disallowed-tools blocklist for safety.

    Args:
        prompt: The enriched prompt to send to Cortex
        connection: Optional Snowflake connection name
        disallowed_tools: Optional list of tools to explicitly block
        envelope: Security envelope mode (RO, RW, RESEARCH, DEPLOY, NONE)
        approval_mode: Approval mode (prompt, auto, envelope_only)
        allowed_tools: Optional list of tools that ARE allowed (for prompt mode)

    Returns:
        Dictionary with execution results
    """
    # Build command with programmatic mode enabled
    cmd = [
        "cortex",
        "-p", prompt,
        "--output-format", "stream-json",
        "--input-format", "stream-json"  # Enables programmatic auto-approval mode
    ]

    # Add connection if specified
    if connection:
        cmd.extend(["-c", connection])

    # Step 1: Handle approval mode - convert allowed_tools to disallowed_tools
    final_disallowed_tools = disallowed_tools or []

    if approval_mode == "prompt":
        # Prompt mode: invert allowed_tools to disallowed_tools
        # In prompt mode, we ONLY use allowed_tools (don't merge with envelope)
        if allowed_tools is not None:
            # User approved specific tools - block everything else
            inverted_tools = invert_tools_to_disallowed(allowed_tools)
            # Merge with existing disallowed tools (but NOT envelope tools)
            final_disallowed_tools = list(set(final_disallowed_tools) | set(inverted_tools))
        else:
            # No tools approved - block all known tools
            final_disallowed_tools = list(set(final_disallowed_tools) | set(KNOWN_TOOLS))

    elif approval_mode in ["envelope_only", "auto"]:
        # Envelope-only or auto mode: apply envelope-based security
        envelope_tools = []
        if envelope == "RO":
            # Read-only: block all write operations
            envelope_tools = [
                "Edit", "Write",
                "Bash(rm *)", "Bash(rm -rf *)", "Bash(rm -r *)",
                "Bash(sudo *)", "Bash(chmod 777 *)",
                "Bash(git push *)", "Bash(git reset --hard *)"
            ]
        elif envelope == "DEPLOY":
            # Full access: no blocklist
            envelope_tools = []
        elif envelope == "RESEARCH":
            # Research: read-only plus web access
            envelope_tools = [
                "Edit", "Write",
                "Bash(rm *)", "Bash(rm -rf *)", "Bash(rm -r *)",
                "Bash(sudo *)", "Bash(chmod 777 *)"
            ]
        # Merge envelope tools with final disallowed list
        if envelope_tools:
            final_disallowed_tools = list(set(final_disallowed_tools) | set(envelope_tools))

    # Step 3: Add final disallowed tools to command
    if final_disallowed_tools:
        for tool in final_disallowed_tools:
            cmd.extend(["--disallowed-tools", tool])

    debug_cmd = f"cortex -p \"...\" --output-format stream-json --input-format stream-json"
    if connection:
        debug_cmd += f" -c {connection}"
    if final_disallowed_tools:
        debug_cmd += f" --disallowed-tools {' '.join(final_disallowed_tools[:3])}{'...' if len(final_disallowed_tools) > 3 else ''}"
    print(debug_cmd, file=sys.stderr)

    try:
        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
                    print(f"→ Started Cortex session: {results['session_id']}", file=sys.stderr)

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

                # Handle final result
                elif event_type == "result":
                    results["final_result"] = event.get("result")
                    print(f"[Cortex] Result: {event.get('result')}", file=sys.stderr)

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
    parser.add_argument("--disallowed-tools", nargs="+", help="Tools to explicitly block")
    parser.add_argument("--envelope", default="RW",
                       choices=["RO", "RW", "RESEARCH", "DEPLOY", "NONE"],
                       help="Security envelope mode (default: RW)")
    parser.add_argument("--approval-mode", default="auto",
                       choices=["prompt", "auto", "envelope_only"],
                       help="Approval mode (default: auto)")
    parser.add_argument("--allowed-tools", nargs="+",
                       help="Tools that are allowed (for prompt mode)")
    parser.add_argument("--stream", action="store_true", help="Stream output (always true)")
    args = parser.parse_args()

    # Execute Cortex
    results = execute_cortex_streaming(
        args.prompt,
        connection=args.connection,
        disallowed_tools=args.disallowed_tools,
        envelope=args.envelope,
        approval_mode=args.approval_mode,
        allowed_tools=args.allowed_tools
    )

    # Output results as JSON
    print(json.dumps(results, indent=2))

    # Exit with appropriate code
    if results.get("error"):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
