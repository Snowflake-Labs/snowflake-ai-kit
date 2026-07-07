#!/usr/bin/env python3
"""Lightweight Snowflake keyword pre-filter for Claude Code UserPromptSubmit hook.

Reads the user prompt from stdin, checks for Snowflake-related keywords,
and if matched, prints a routing instruction to stdout that gets injected
into the conversation context. Runs in <50ms -- no LLM calls, no network.
"""
from __future__ import annotations

import json as _json
import os
import sys
import re
import shutil
from pathlib import Path

# Keywords that strongly indicate Snowflake intent
SNOWFLAKE_KEYWORDS = [
    r"\bsnowflake\b",
    r"\bcortex\b",
    r"\bsnowpark\b",
    r"\bdynamic\s+table",
    r"\bwarehouse\b",
    r"\bsnowsql\b",
    r"\biceberg\s+table",
    r"\bdata\s+quality\b",
    r"\bdata\s+governance\b",
    r"\bsemantic\s+view\b",
    r"\bcortex\s+search\b",
    r"\bcortex\s+analyst\b",
    r"\bcortex\s+agent\b",
    r"\bnative\s+app\b",
    r"\bstreamlit\s+in\s+snowflake\b",
    r"\bsnowflake\s+sql\b",
    r"\bshow\s+(me\s+)?(my\s+)?.*\btables\b",
    r"\bshow\s+(me\s+)?(my\s+)?.*\bdatabases\b",
    r"\bshow\s+(me\s+)?(my\s+)?.*\bschemas\b",
    r"\bshow\s+(me\s+)?(my\s+)?.*\bwarehouses\b",
]

# Keywords that indicate local/non-Snowflake work -- skip routing
LOCAL_KEYWORDS = [
    r"\blocal\s+file",
    r"\bgit\s+(commit|push|pull|status|log|diff|branch)\b",
    r"\bfix\s+(the|this|a)\s+bug\b",
    r"\bread\s+(the|this)\s+file\b",
    r"\bedit\s+(the|this)\s+file\b",
    r"\bwrite\s+a\s+(python|javascript|typescript|rust|go)\b",
    r"\bunit\s+test\b",
    r"\bnpm\b",
    r"\bpip\s+install\b",
]

COMPILED_SF = [re.compile(p, re.IGNORECASE) for p in SNOWFLAKE_KEYWORDS]
COMPILED_LOCAL = [re.compile(p, re.IGNORECASE) for p in LOCAL_KEYWORDS]


def _check_mcp_conflict():
    """Return a STOP message if a Snowflake MCP server is active, else None."""
    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        if not settings_path.exists():
            return None
        data = _json.loads(settings_path.read_text(encoding="utf-8"))
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
                    f"STOP. A Snowflake MCP server '{name}' is active in "
                    "~/.claude/settings.json. This CONFLICTS with Cortex Code CLI "
                    "(duplicate tools, auth issues). "
                    "Do NOT proceed with any Snowflake operations. "
                    "Tell the user: 'A Snowflake MCP server is active and conflicts "
                    "with Cortex Code. Please disable or remove it from Claude Code "
                    "settings (Settings > MCP Servers) and try again.'"
                )
    except (ValueError, PermissionError, OSError):
        pass
    return None


def _get_plugin_root():
    """Get the plugin root directory from environment."""
    return os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or ""


# Module-level flag set by main() based on stdin format detection
_detected_claude_code_from_stdin = False


def _is_claude_code():
    """Detect if running inside Claude Code (vs Codex). Fail-safe: ambiguous = Claude Code.

    Claude Code signals (any one is sufficient):
    1. Env: CLAUDECODE=1 or CLAUDE_CODE_ENTRYPOINT set
    2. Stdin payload contains hook_event_name or transcript_path

    Codex signals (must be present AND no Claude Code signal):
    1. Env: PLUGIN_ROOT or CLAUDE_PLUGIN_ROOT set
    """
    # Positive Claude Code detection
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return True
    if _detected_claude_code_from_stdin:
        return True
    # Only Codex if PLUGIN_ROOT is explicitly set
    if os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return False
    # Ambiguous — default to Claude Code (permission-gated = safe)
    return True


def check_prompt(prompt: str) -> str | None:
    """Return routing instruction if Snowflake keywords detected, else None."""
    # Skip empty or very short prompts
    if not prompt or len(prompt.strip()) < 5:
        return None

    # Check for local keywords first -- if present, don't route
    for pattern in COMPILED_LOCAL:
        if pattern.search(prompt):
            return None

    # Check for Snowflake keywords
    for pattern in COMPILED_SF:
        if pattern.search(prompt):
            if _is_claude_code():
                return _claude_code_routing_instruction()
            else:
                plugin_root = _get_plugin_root()
                return _codex_routing_instruction(plugin_root)

    return None


def _codex_routing_instruction(plugin_root: str) -> str:
    """Routing instruction for OpenAI Codex — direct bash commands."""
    return (
        "[CORTEX ROUTER] This prompt needs Cortex Code CLI. "
        "Follow these steps IN ORDER:\n"
        "Step 1: Verify cortex CLI is installed by running: which cortex && cortex --version\n"
        f"Step 2: Run the routing check: python3 \"{plugin_root}/scripts/router/route_request.py\" "
        "--prompt \"<USER_PROMPT>\"\n"
        "  - Replace <USER_PROMPT> with the actual user prompt (shell-escaped).\n"
        "  - If output says route: claude -> STOP routing and handle the request yourself.\n"
        "  - If output says route: cortex -> proceed to Step 3.\n"
        f"Step 3: Execute via Cortex Code: python3 -u \"{plugin_root}/scripts/router/execute_cortex.py\" "
        "--prompt \"<USER_PROMPT>\" --envelope \"RW\" --codex\n"
        "  - Use --envelope RO for read-only queries (SELECT, SHOW, DESCRIBE).\n"
        "  - Use --envelope RW for modifications (CREATE, ALTER, INSERT).\n"
        "  - The --codex flag is REQUIRED (enables non-interactive mode).\n"
        "  - For follow-up prompts, add --resume-last to maintain context.\n"
        "  - IMPORTANT: This command requires network access to Snowflake. Do NOT run it in a background terminal. Run it as a foreground command.\n"
        "Do NOT use SnowSQL, snow CLI, or any other tool for Snowflake operations. "
        "ONLY use the cortex CLI via the scripts above."
    )


def _claude_code_routing_instruction() -> str:
    """Routing instruction for Claude Code — uses Skill tool."""
    return (
        "[CORTEX ROUTER] This prompt may need Cortex Code CLI. "
        "Load the snowflake-cortex-code:cortex-router skill using the Skill tool, "
        "then follow ALL steps IN ORDER — do NOT skip any steps. "
        "Step 1: verify cortex CLI is installed. "
        "Step 2: run route_request.py to check if this should go to Cortex or stay in Claude Code. "
        "Step 3: ONLY if Step 2 says route=cortex, execute via execute_cortex.py. "
        "If this prompt is a follow-up to a previous Cortex turn "
        "(continue/keep going/drill in/also/fix that), pass --resume-last "
        "to execute_cortex.py so Cortex sees prior context. "
        "Do NOT load snowflake-cortex-code:cortex-run (that is for explicit $cortex-run invocation only)."
    )


def main():
    # Read the user prompt from stdin (Claude Code passes it as JSON on stdin)
    import json

    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Not valid JSON, output empty result
        print("{}")
        sys.exit(0)

    # Extract the prompt text
    prompt = ""
    if isinstance(data, dict):
        # Detect Claude Code positively from stdin payload structure:
        # Claude Code UserPromptSubmit sends hook_event_name + transcript_path + prompt
        global _detected_claude_code_from_stdin
        if "hook_event_name" in data or "transcript_path" in data:
            _detected_claude_code_from_stdin = True

        # The hook receives the full message object
        prompt = data.get("prompt", data.get("message", ""))
        if isinstance(prompt, dict):
            prompt = prompt.get("content", "")
        if isinstance(prompt, list):
            # Content blocks
            prompt = " ".join(
                block.get("text", "") for block in prompt if isinstance(block, dict)
            )

    result = check_prompt(str(prompt))
    if result:
        # Check for MCP conflict FIRST — blocks everything if Snowflake MCP server is active
        mcp_conflict = _check_mcp_conflict()
        if mcp_conflict:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": mcp_conflict,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Snowflake prompt detected -- check if cortex CLI is available
        if not shutil.which("cortex"):
            if not _is_claude_code():
                install_msg = (
                    "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
                    "snow CLI, or any other workaround. "
                    "Tell the user to install it: visit "
                    "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli "
                    "and follow the installation instructions. Then retry."
                )
            else:
                install_msg = (
                    "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
                    "snow CLI, or any other workaround. "
                    "Load the snowflake-cortex-code:cortex-setup skill NOW using the Skill tool, "
                    "then follow its instructions to install the CLI. "
                    "If the user declines, tell them to visit "
                    "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli"
                )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": install_msg,
                }
            }
        else:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": result,
                }
            }
        print(json.dumps(output))
    else:
        print("{}")

    sys.exit(0)


if __name__ == "__main__":
    main()
