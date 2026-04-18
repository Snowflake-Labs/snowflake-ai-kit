#!/usr/bin/env python3
"""
Executes Cortex Code in headless mode with streaming output parsing.
Uses --output-format stream-json for streaming results.
Handles tool use events and final results.
"""

import json
import shutil
import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from session_state import load_active_session, save_active_session


# Credential file patterns — block prompts referencing these paths.
# This check runs unconditionally (can't be skipped by LLM shortcutting).
CREDENTIAL_PATTERNS = [
    ".ssh/", ".snowflake/", ".env", "credentials.json",
    "_key.p8", "_key.pem", ".aws/credentials", ".kube/config",
    "private_key", "secret_key", "api_key_file", "token.json",
]


def check_credential_paths(prompt: str) -> Optional[str]:
    """Block prompts that reference credential file paths.

    Returns the matched pattern if blocked, None if safe.
    """
    prompt_lower = prompt.lower()
    for pattern in CREDENTIAL_PATTERNS:
        if pattern in prompt_lower:
            return pattern
    return None


def check_cortex_cli() -> bool:
    """Check if cortex CLI is available and functional."""
    if not shutil.which("cortex"):
        return False
    try:
        result = subprocess.run(
            ["cortex", "--version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


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
                             allowed_tools: Optional[List[str]] = None,
                             resume_session_id: Optional[str] = None) -> Dict:
    """
    Execute Cortex with streaming JSON output in programmatic mode.

    Uses --output-format stream-json for streaming results.
    Tools are controlled via --allowed-tools allowlist (envelope mode) or
    --disallowed-tools blocklist (prompt mode) for safety.

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
    # Pre-flight: check for credential file paths in prompt
    blocked_pattern = check_credential_paths(prompt)
    if blocked_pattern:
        msg = (f"BLOCKED: Prompt references credential path '{blocked_pattern}'. "
               "Refusing to send to Cortex Code for security. "
               "Remove credential references from your prompt and try again.")
        print(f"⛔ {msg}", file=sys.stderr)
        return {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": msg
        }

    # Pre-flight: ensure cortex CLI is installed
    if not check_cortex_cli():
        msg = ("Cortex Code CLI not found. "
               "Use the cortex-setup skill to install it, or visit "
               "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli")
        print(msg, file=sys.stderr)
        return {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": msg
        }

    # Build command with programmatic auto-approval mode.
    # --input-format stream-json enables headless auto-approval of all tool calls
    # (including snowflake_sql_execute and MCP tools) without --bypass or
    # --dangerously-allow-all-tool-calls which may be blocked by org policy.
    # Envelope security is enforced via --disallowed-tools blocklist.
    # NOTE: Do NOT use -p with --input-format stream-json -- the -p flag is
    # ignored in stream-json input mode. Instead, send the prompt via stdin
    # as a JSON user message (see below).
    cmd = [
        "cortex",
        "--output-format", "stream-json",
        "--input-format", "stream-json"
    ]

    # Resume prior cortex session so follow-up turns see earlier context.
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])
        print(f"[cortex] Resuming session {resume_session_id}", file=sys.stderr)

    # Add connection if specified
    if connection:
        cmd.extend(["-c", connection])

    # Step 1: Handle approval mode — build disallowed tools list for envelope security.
    # Note: --input-format stream-json auto-approves tools; --disallowed-tools
    # enforces the security boundary. Do NOT use --allowed-tools: it creates an
    # "must match pattern" check that blocks Snowflake MCP tools.
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
        # Envelope-only or auto mode: apply envelope-based security via blocklist.
        # --input-format stream-json (set above) auto-approves all non-blocked tools.
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

    debug_cmd = f"cortex --output-format stream-json --input-format stream-json (prompt via stdin)"
    if connection:
        debug_cmd += f" -c {connection}"
    if final_disallowed_tools:
        debug_cmd += f" --disallowed-tools {' '.join(final_disallowed_tools[:3])}{'...' if len(final_disallowed_tools) > 3 else ''}"
    print(debug_cmd, file=sys.stderr)

    try:
        # Start process with stdin=PIPE so we can send the prompt as a
        # stream-json user message. Previously used stdin=DEVNULL with -p flag,
        # but -p is ignored in --input-format stream-json mode -- the prompt
        # must arrive via stdin as a JSON user message.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Send the prompt as a stream-json user message, then close stdin
        # so Cortex knows no more input is coming and will process + exit.
        prompt_message = json.dumps({
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }
        }) + "\n"
        process.stdin.write(prompt_message)
        process.stdin.flush()
        process.stdin.close()

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

                # Extract session ID and persist so next turn can --resume.
                if event_type == "system" and event.get("subtype") == "init":
                    results["session_id"] = event.get("session_id")
                    print(f"→ Started Cortex session: {results['session_id']}", file=sys.stderr)
                    save_active_session(results["session_id"])

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

        # Terminate the process — it stays alive waiting for more stdin
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        # Check for errors
        if process.returncode not in (0, -15):  # -15 = SIGTERM (expected)
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
    parser.add_argument("--resume-last", action="store_true",
                       help="Resume the most recent cortex session for multi-turn continuation")
    parser.add_argument("--resume", dest="resume_session_id", default=None,
                       help="Resume a specific cortex session by id")
    args = parser.parse_args()

    # Resolve which session (if any) to resume.
    resume_session_id = args.resume_session_id
    if args.resume_last and not resume_session_id:
        active = load_active_session()
        if active:
            resume_session_id = active["session_id"]
        else:
            print("→ --resume-last requested but no active session found; starting fresh.",
                  file=sys.stderr)

    # Execute Cortex
    results = execute_cortex_streaming(
        args.prompt,
        connection=args.connection,
        disallowed_tools=args.disallowed_tools,
        envelope=args.envelope,
        approval_mode=args.approval_mode,
        allowed_tools=args.allowed_tools,
        resume_session_id=resume_session_id,
    )

    # Output results as JSON
    print(json.dumps(results, indent=2))

    # Exit with appropriate code
    if results.get("error"):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
