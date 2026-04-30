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
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from envelope_policy import decide as envelope_decide
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


# Prompt-level security envelope instructions.
# Hard enforcement happens through `--permission-prompt-tool stdio`: cortex
# emits a control_request for every tool call and this wrapper replies via
# envelope_policy.decide(). The prompt text below is a soft hint so the LLM
# shapes its plan to the envelope (fewer denied tool calls, cleaner UX). Hard
# gate is the policy function -- the LLM cannot talk its way past it.
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


def _send_control_response(stdin, request_id: str, behavior: str, message: str = "") -> None:
    """Write a control_response back to cortex's stdin. Safe no-op if pipe is closed."""
    payload = {
        "type": "control_response",
        "response": {
            "subtype": "success",
            "request_id": request_id,
            "response": {"behavior": behavior, "message": message},
        },
    }
    try:
        stdin.write(json.dumps(payload) + "\n")
        stdin.flush()
    except (BrokenPipeError, ValueError):
        # cortex already exited -- nothing to do.
        pass


def execute_cortex_streaming(prompt: str, connection: Optional[str] = None,
                             envelope: str = "RW",
                             resume_session_id: Optional[str] = None) -> Dict:
    """
    Execute Cortex with streaming JSON output in programmatic mode.

    Uses --permission-prompt-tool stdio to route every tool call through this
    wrapper, which decides allow/deny via envelope_policy.decide(). This is
    hard enforcement: cortex will NOT execute a tool until we respond. LLM
    output cannot bypass it.

    Args:
        prompt: The enriched prompt to send to Cortex
        connection: Optional Snowflake connection name
        envelope: Security envelope mode (RO, RW, RESEARCH, DEPLOY)
        resume_session_id: Optional session ID to resume for multi-turn

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

    # Prepend envelope instructions to the prompt
    envelope_prompt = build_envelope_prompt(prompt, envelope)

    # Build command for headless execution.
    # --input-format stream-json: programmatic mode (prompt via stdin).
    # --permission-prompt-tool stdio: route every tool call through us as a
    #   control_request; we reply allow/deny based on the envelope policy.
    #   This is hard enforcement at the CLI boundary, not LLM self-policing.
    cmd = [
        "cortex",
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--permission-prompt-tool", "stdio",
    ]

    # Resume prior cortex session so follow-up turns see earlier context.
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])
        print(f"[cortex] Resuming session {resume_session_id}", file=sys.stderr)

    # Add connection if specified
    if connection:
        cmd.extend(["-c", connection])

    debug_cmd = f"cortex --output-format stream-json --input-format stream-json --permission-prompt-tool stdio (envelope={envelope})"
    if connection:
        debug_cmd += f" -c {connection}"
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

        # Send the user prompt. stdin stays OPEN for the duration of the turn
        # so we can write control_response messages back when cortex asks for
        # permission (--permission-prompt-tool stdio emits control_request on
        # stdout and awaits a control_response on stdin, same pipe).
        prompt_message = json.dumps({
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": envelope_prompt}]
            }
        }) + "\n"
        process.stdin.write(prompt_message)
        process.stdin.flush()

        results = {
            "session_id": None,
            "events": [],
            "permission_decisions": [],
            "final_result": None,
            "error": None
        }

        # Read streaming output. Two interleaved event kinds matter:
        #   - control_request (subtype=can_use_tool) -- permission ask; we reply
        #     immediately with a control_response based on envelope_policy.
        #   - result -- turn complete; break.
        for line in process.stdout:
            if not line.strip():
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse line: {line[:100]}... Error: {e}", file=sys.stderr)
                continue

            results["events"].append(event)
            event_type = event.get("type")

            # Extract session ID and persist so next turn can --resume.
            if event_type == "system" and event.get("subtype") == "init":
                results["session_id"] = event.get("session_id")
                print(f"→ Started Cortex session: {results['session_id']}", file=sys.stderr)
                save_active_session(results["session_id"])

            elif event_type == "control_request":
                req = event.get("request", {}) or {}
                if req.get("subtype") != "can_use_tool":
                    # Not a permission ask; ignore other control request subtypes.
                    continue
                tool_name = req.get("tool_name", "")
                tool_input = req.get("input", {}) or {}
                action = tool_input.get("action", "")
                resource = tool_input.get("resource", "")
                behavior, reason = envelope_decide(envelope, tool_name, action, resource)
                preview = (resource or "")[:120].replace("\n", " ")
                print(f"[policy] {envelope}: {behavior} {tool_name} — {preview}",
                      file=sys.stderr)
                results["permission_decisions"].append({
                    "tool_name": tool_name,
                    "action": action,
                    "resource": resource,
                    "behavior": behavior,
                    "reason": reason,
                })
                _send_control_response(
                    process.stdin,
                    event.get("request_id", ""),
                    behavior,
                    reason,
                )

            elif event_type == "assistant":
                message = event.get("message", {}) or {}
                for item in (message.get("content") or []):
                    if item.get("type") == "text":
                        print(f"[Cortex] {item.get('text', '')}", file=sys.stderr)
                    elif item.get("type") == "tool_use":
                        print(f"[Cortex] Using tool: {item.get('name')}", file=sys.stderr)

            elif event_type == "result":
                results["final_result"] = event.get("result")
                print(f"[Cortex] Result received.", file=sys.stderr)
                break  # turn complete

        # Turn complete: close stdin so cortex exits cleanly.
        try:
            process.stdin.close()
        except (BrokenPipeError, ValueError):
            pass

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

        if process.returncode not in (0, -15):  # -15 = SIGTERM (expected on kill)
            stderr_output = process.stderr.read() if process.stderr else ""
            results["error"] = stderr_output
            print(f"Error: Cortex exited with code {process.returncode}", file=sys.stderr)
            if stderr_output:
                print(f"Stderr: {stderr_output}", file=sys.stderr)

        return results

    except Exception as e:
        # Prevent orphaned cortex processes on unexpected exceptions
        try:
            process.terminate()
            process.wait(timeout=2)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
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
        envelope=args.envelope,
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
