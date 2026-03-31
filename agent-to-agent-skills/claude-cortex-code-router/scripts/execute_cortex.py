#!/usr/bin/env python3
"""Execute Cortex Code CLI in headless mode with streaming output.

Uses --input-format stream-json for programmatic auto-approval of tool calls.
Security is controlled via --disallowed-tools blocklist (security envelopes).

Requires: Cortex Code CLI (cortex) installed and in PATH.
No external Python dependencies — stdlib only.

Inspired by: https://github.com/sfc-gh-tjia/claude_skill_cortexcode
"""

import argparse
import json
import shutil
import subprocess
import sys
from typing import Dict, List, Optional

# Security envelope definitions: envelope name -> blocked tools
ENVELOPES: Dict[str, List[str]] = {
    "RO": [
        "Edit", "Write",
        "Bash(rm *)", "Bash(rm -rf *)", "Bash(rm -r *)",
        "Bash(sudo *)", "Bash(chmod 777 *)",
        "Bash(git push *)", "Bash(git reset --hard *)",
    ],
    "RW": [
        "Bash(rm -rf *)", "Bash(rm -r /)",
        "Bash(sudo *)", "Bash(chmod 777 *)",
        "Bash(git push --force *)", "Bash(git reset --hard *)",
    ],
    "RESEARCH": [
        "Edit", "Write",
        "Bash(rm *)", "Bash(rm -rf *)", "Bash(rm -r *)",
        "Bash(sudo *)", "Bash(chmod 777 *)",
    ],
    "DEPLOY": [],
}


def execute_cortex(
    prompt: str,
    connection: Optional[str] = None,
    envelope: str = "RW",
    disallowed_tools: Optional[List[str]] = None,
) -> Dict:
    """Execute Cortex Code headlessly and return structured results.

    Args:
        prompt: The enriched prompt to send to Cortex.
        connection: Optional Snowflake connection name.
        envelope: Security envelope (RO, RW, RESEARCH, DEPLOY).
        disallowed_tools: Custom tool blocklist (overrides envelope).

    Returns:
        Dict with session_id, events, final_result, and error fields.
    """
    if not shutil.which("cortex"):
        return {
            "session_id": None,
            "events": [],
            "final_result": None,
            "error": "cortex CLI not found in PATH. Install: curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh",
        }

    # Build command
    cmd = [
        "cortex",
        "-p", prompt,
        "--output-format", "stream-json",
        "--input-format", "stream-json",
    ]

    if connection:
        cmd.extend(["-c", connection])

    # Resolve tool blocklist: custom list takes precedence over envelope
    blocked = disallowed_tools if disallowed_tools is not None else ENVELOPES.get(envelope, [])
    for tool in blocked:
        cmd.extend(["--disallowed-tools", tool])

    print(f"→ Envelope: {envelope}, blocked tools: {len(blocked)}", file=sys.stderr)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        results = {
            "session_id": None,
            "events": [],
            "final_result": None,
            "error": None,
        }

        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            results["events"].append(event)
            event_type = event.get("type")

            if event_type == "system" and event.get("subtype") == "init":
                results["session_id"] = event.get("session_id")
                print(f"→ Session: {results['session_id']}", file=sys.stderr)

            elif event_type == "assistant":
                message = event.get("message", {})
                for item in message.get("content", []):
                    if item.get("type") == "text":
                        text = item.get("text", "")
                        # Print first 200 chars as progress
                        preview = text[:200].replace("\n", " ")
                        print(f"[cortex] {preview}{'...' if len(text) > 200 else ''}", file=sys.stderr)
                    elif item.get("type") == "tool_use":
                        print(f"[cortex] tool: {item.get('name')}", file=sys.stderr)

            elif event_type == "result":
                results["final_result"] = event.get("result")
                print(f"→ Done.", file=sys.stderr)

        process.wait()

        if process.returncode != 0:
            stderr_output = process.stderr.read()
            results["error"] = stderr_output or f"cortex exited with code {process.returncode}"

        return results

    except Exception as e:
        return {
            "session_id": None,
            "events": [],
            "final_result": None,
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser(description="Execute Cortex Code headlessly")
    parser.add_argument("--prompt", required=True, help="Prompt to send to Cortex")
    parser.add_argument("--connection", "-c", help="Snowflake connection name")
    parser.add_argument(
        "--envelope",
        default="RW",
        choices=list(ENVELOPES.keys()),
        help="Security envelope (default: RW)",
    )
    parser.add_argument(
        "--disallowed-tools",
        nargs="+",
        help="Custom tool blocklist (overrides envelope)",
    )
    args = parser.parse_args()

    results = execute_cortex(
        prompt=args.prompt,
        connection=args.connection,
        envelope=args.envelope,
        disallowed_tools=args.disallowed_tools,
    )

    print(json.dumps(results, indent=2))
    return 1 if results.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
