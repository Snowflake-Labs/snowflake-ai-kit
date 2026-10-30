#!/usr/bin/env python3
"""Lightweight Snowflake keyword pre-filter for the UserPromptSubmit hook.

Reads the user prompt from stdin, checks for Snowflake-related keywords,
and if matched, prints a routing instruction to stdout that gets injected
into the conversation context. Runs in <50ms -- no LLM calls, no network.
"""
from __future__ import annotations

import os
import sys
import re
import shutil
from pathlib import Path

import hosts

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


def _check_mcp_conflict(host=None):
    """Return a STOP message if a Snowflake MCP server is active, else None.

    Scans every MCP config location the host owns.
    """
    host = host or hosts.detect(os.environ, {})
    found = hosts.find_snowflake_mcp_server(host, Path.home(), Path.cwd(), os.environ)
    if not found:
        return None
    name, location = found
    return (
        f"STOP. A Snowflake MCP server '{name}' is active in "
        f"{location}. This CONFLICTS with Cortex Code CLI "
        "(duplicate tools, auth issues). "
        "Do NOT proceed with any Snowflake operations. "
        "Tell the user: 'A Snowflake MCP server is active and conflicts "
        "with Cortex Code. Please disable or remove it and try again.'"
    )


# Retained so existing callers that reset it keep working; detection no longer reads it.
_detected_claude_code_from_stdin = False


def check_prompt(prompt: str, host=None) -> str | None:
    """Return routing instruction if Snowflake keywords detected, else None."""
    # Skip empty or very short prompts
    if not prompt or len(prompt.strip()) < 5:
        return None

    host = host or hosts.detect(os.environ, {})
    if host.is_explicit_invocation(prompt):
        return None

    # Check for local keywords first -- if present, don't route
    for pattern in COMPILED_LOCAL:
        if pattern.search(prompt):
            return None

    # Check for Snowflake keywords
    for pattern in COMPILED_SF:
        if pattern.search(prompt):
            return host.routing_instruction(hosts.plugin_root(os.environ))

    return None


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
    host = hosts.detect(os.environ, data)
    prompt = ""
    if isinstance(data, dict):
        # The hook receives the full message object
        prompt = data.get("prompt", data.get("message", ""))
        if isinstance(prompt, dict):
            prompt = prompt.get("content", "")
        if isinstance(prompt, list):
            # Content blocks
            prompt = " ".join(
                block.get("text", "") for block in prompt if isinstance(block, dict)
            )

    explicit = host.is_explicit_invocation(str(prompt))
    if explicit:
        result = host.explicit_invocation_context(hosts.plugin_root(os.environ))
    else:
        result = check_prompt(str(prompt), host)
    if result:
        from security.config_manager import ConfigManager, ConfigValidationError
        try:
            ConfigManager()
        except ConfigValidationError as error:
            # UserPromptSubmit exit 2 blocks this turn rather than routing around policy.
            print(str(error), file=sys.stderr)
            sys.exit(2)
        # Check MCP conflicts before CLI discovery.
        mcp_conflict = _check_mcp_conflict(host)
        if mcp_conflict:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": mcp_conflict,
                }
            }
            print(json.dumps(output))
            sys.exit(0)

        # Snowflake prompt detected -- check if cortex CLI is available.
        # Explicit commands (including setup) handle a missing CLI themselves.
        if not explicit and not shutil.which("cortex"):
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": host.install_message(),
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
