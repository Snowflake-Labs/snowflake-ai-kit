#!/usr/bin/env python3
"""
Executes Cortex Code in headless mode with streaming output parsing.
Uses --output-format stream-json for streaming results.
Handles tool use events and final results.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from envelope_policy import decide as envelope_decide
from session_state import load_active_session, save_active_session


CREDENTIAL_PATTERNS: list[Tuple[re.Pattern, str]] = [
    (re.compile(r'\.ssh/'), ".ssh/"),
    (re.compile(r'\.snowflake/'), ".snowflake/"),
    (re.compile(r'(?<![a-z])\.env(?:\b|[./])'), ".env"),
    (re.compile(r'\bcredentials\.json\b'), "credentials.json"),
    (re.compile(r'_key\.p8\b'), "_key.p8"),
    (re.compile(r'_key\.pem\b'), "_key.pem"),
    (re.compile(r'\.aws/credentials\b'), ".aws/credentials"),
    (re.compile(r'\.kube/config\b'), ".kube/config"),
    (re.compile(r'\bprivate[_-]?key\b'), "private_key"),
    (re.compile(r'\bsecret[_-]?key\b'), "secret_key"),
    (re.compile(r'\bapi[_-]?key[_-]?file\b'), "api_key_file"),
    (re.compile(r'\btoken\.json\b'), "token.json"),
]


def check_credential_paths(prompt: str) -> Optional[str]:
    """Block prompts that reference credential file paths.

    Uses word-boundary-aware regex to avoid false positives
    (e.g., '.env' no longer matches 'environment').

    Returns the matched pattern label if blocked, None if safe.
    """
    prompt_lower = prompt.lower()
    for pattern_re, label in CREDENTIAL_PATTERNS:
        if pattern_re.search(prompt_lower):
            return label
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


def check_mcp_conflict() -> Optional[str]:
    """Check if a Snowflake MCP server is configured in Claude Code settings.

    If found, Cortex Code and the MCP server will conflict (duplicate tool
    registrations, auth confusion). Returns conflict message or None.
    """
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        if not settings_path.exists():
            return None
        data = json.loads(settings_path.read_text(encoding="utf-8"))
        servers = data.get("mcpServers", {})
        if not isinstance(servers, dict):
            return None
        for name, cfg in servers.items():
            if not isinstance(cfg, dict):
                continue
            command = cfg.get("command", "")
            args = " ".join(str(a) for a in cfg.get("args", []))
            search_str = f"{name} {command} {args}".lower()
            if "snowflake" in search_str:
                return (
                    f"CONFLICT: Snowflake MCP server '{name}' is active in "
                    "~/.claude/settings.json. This conflicts with Cortex Code CLI "
                    "(duplicate tools, auth issues). "
                    "Please disable or remove it from Claude Code settings "
                    "(Settings > MCP Servers), then retry."
                )
    except (json.JSONDecodeError, PermissionError, OSError):
        return None
    return None


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


def _check_deploy_allowed(envelope: str) -> Optional[str]:
    """Check if DEPLOY envelope is allowed by config. Returns error message or None."""
    if envelope != "DEPLOY":
        return None
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from security.config_manager import ConfigManager
        config = ConfigManager()
        allowed = config.get("security.allowed_envelopes", [])
        if "DEPLOY" not in allowed:
            return (
                "DEPLOY envelope is not in allowed_envelopes. "
                "Enable it in your org policy or config.yaml to use DEPLOY mode."
            )
    except Exception:
        pass
    return None


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

    # Pre-flight: check DEPLOY envelope is allowed
    deploy_error = _check_deploy_allowed(envelope)
    if deploy_error:
        print(f"⛔ {deploy_error}", file=sys.stderr)
        return {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": deploy_error
        }

    # Pre-flight: check for conflicting Snowflake MCP server
    mcp_conflict = check_mcp_conflict()
    if mcp_conflict:
        print(f"\u26d4 {mcp_conflict}", file=sys.stderr)
        return {
            "session_id": None,
            "events": [],
            "permission_requests": [],
            "final_result": None,
            "error": mcp_conflict
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

    cmd = [
        "cortex",
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--permission-prompt-tool", "stdio",
    ]

    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])
        print(f"[cortex] Resuming session {resume_session_id}", file=sys.stderr)

    if connection:
        cmd.extend(["-c", connection])

    debug_cmd = f"cortex --output-format stream-json --input-format stream-json --permission-prompt-tool stdio (envelope={envelope})"
    if connection:
        debug_cmd += f" -c {connection}"
    print(debug_cmd, file=sys.stderr)

    try:
        env = os.environ.copy()
        # Detect calling agent: Claude Code signals take precedence over PLUGIN_ROOT
        if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
            env["CORTEX_CODE_ENTRYPOINT"] = "Claude Code Plugin"
        elif os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT"):
            env["CORTEX_CODE_ENTRYPOINT"] = "Codex Plugin"
        else:
            env["CORTEX_CODE_ENTRYPOINT"] = "Unknown"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )

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

            if event_type == "system" and event.get("subtype") == "init":
                results["session_id"] = event.get("session_id")
                print(f"→ Started Cortex session: {results['session_id']}", file=sys.stderr)
                save_active_session(results["session_id"])

            elif event_type == "control_request":
                req = event.get("request", {}) or {}
                if req.get("subtype") != "can_use_tool":
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
                break

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

        if process.returncode not in (0, -15):
            stderr_output = process.stderr.read() if process.stderr else ""
            results["error"] = stderr_output
            print(f"Error: Cortex exited with code {process.returncode}", file=sys.stderr)
            if stderr_output:
                print(f"Stderr: {stderr_output}", file=sys.stderr)

        return results

    except Exception as e:
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


def _run_codex_mode(args):
    """Codex execution path: subprocess.run with auto-approve, no MCP, no pipe.

    This avoids the bidirectional stdin/stdout pipe that Codex background
    terminals can't handle. Uses subprocess.run which cleanly passes input
    and waits for completion.
    """
    # Pre-flight: credential path blocking (same as Claude Code path)
    blocked_pattern = check_credential_paths(args.prompt)
    if blocked_pattern:
        error_msg = (f"BLOCKED: Prompt references credential path '{blocked_pattern}'. "
                     "Refusing to send to Cortex Code for security.")
        print(json.dumps({"session_id": None, "events": [], "permission_decisions": [],
                          "final_result": None, "error": error_msg}, indent=2))
        return 1

    envelope_prompt = build_envelope_prompt(args.prompt, args.envelope)

    cmd = [
        "cortex",
        "--output-format", "stream-json",
        "--input-format", "stream-json",
        "--dangerously-allow-all-tool-calls",
        "--no-mcp",
    ]

    if args.connection:
        cmd.extend(["-c", args.connection])

    resume_session_id = args.resume_session_id
    if args.resume_last and not resume_session_id:
        active = load_active_session()
        if active:
            resume_session_id = active["session_id"]
    if resume_session_id:
        cmd.extend(["--resume", resume_session_id])

    prompt_message = json.dumps({
        "type": "user",
        "message": {
            "role": "user",
            "content": [{"type": "text", "text": envelope_prompt}]
        }
    }) + "\n"

    env = os.environ.copy()
    env["CORTEX_CODE_ENTRYPOINT"] = "Codex Plugin"

    perm_mode = "--dangerously-allow-all-tool-calls --no-mcp"
    debug_cmd = f"cortex --output-format stream-json --input-format stream-json {perm_mode} (envelope={args.envelope})"
    print(debug_cmd, file=sys.stderr)
    print("→ Running Cortex (this takes ~20-30s)...", flush=True)

    try:
        completed = subprocess.run(
            cmd,
            input=prompt_message,
            capture_output=True,
            text=True,
            timeout=600,
            env=env,
        )
    except subprocess.TimeoutExpired:
        error_msg = f"Command {cmd!r} timed out after 600 seconds"
        print(json.dumps({"session_id": None, "events": [], "permission_decisions": [],
                          "final_result": None, "error": error_msg}, indent=2))
        return 1

    # Parse all stdout lines
    results = {
        "session_id": None,
        "events": [],
        "permission_decisions": [],
        "final_result": None,
        "error": None
    }

    for line in completed.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        results["events"].append(event)
        event_type = event.get("type")
        if event_type == "system" and event.get("subtype") == "init":
            results["session_id"] = event.get("session_id")
            save_active_session(results["session_id"])
        elif event_type == "assistant":
            message = event.get("message", {}) or {}
            for item in (message.get("content") or []):
                if item.get("type") == "text":
                    print(f"[Cortex] {item.get('text', '')}", flush=True)
                elif item.get("type") == "tool_use":
                    print(f"[Cortex] Using tool: {item.get('name')}", flush=True)
        elif event_type == "result":
            results["final_result"] = event.get("result")
            print("[Cortex] Done.", flush=True)

    if completed.returncode != 0 and not results["final_result"]:
        results["error"] = completed.stderr or f"cortex exited with code {completed.returncode}"

    print(json.dumps(results, indent=2))
    return 0 if not results.get("error") else 1


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
    parser.add_argument("--codex", action="store_true",
                       help="Codex mode: auto-approve tools, skip MCP, use subprocess.run")
    args = parser.parse_args()

    # Codex mode: simple subprocess.run path (no bidirectional pipe)
    if args.codex:
        return _run_codex_mode(args)

    resume_session_id = args.resume_session_id
    if args.resume_last and not resume_session_id:
        active = load_active_session()
        if active:
            resume_session_id = active["session_id"]
        else:
            print("→ --resume-last requested but no active session found; starting fresh.",
                  file=sys.stderr)

    results = execute_cortex_streaming(
        args.prompt,
        connection=args.connection,
        envelope=args.envelope,
        resume_session_id=resume_session_id,
    )

    print(json.dumps(results, indent=2))

    if results.get("error"):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
