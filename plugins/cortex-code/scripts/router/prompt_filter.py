#!/usr/bin/env python3
"""Lightweight Snowflake keyword pre-filter for Claude Code UserPromptSubmit hook.

Reads the user prompt from stdin, checks for Snowflake-related keywords,
and if matched, prints a routing instruction to stdout that gets injected
into the conversation context. Runs in <50ms -- no LLM calls, no network.
"""

import sys
import re
import shutil

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
            return (
                "[CORTEX ROUTER] This prompt may need Cortex Code CLI. "
                "Load the cortex-code:cortex-router skill using the Skill tool, "
                "then follow ALL steps IN ORDER — do NOT skip any steps. "
                "Step 1: verify cortex CLI is installed. "
                "Step 2: run route_request.py to check if this should go to Cortex or stay in Claude Code. "
                "Step 3: ONLY if Step 2 says route=cortex, execute via execute_cortex.py. "
                "Do NOT load cortex-run (that is for explicit $cortex-run invocation only)."
            )

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
    prompt = ""
    if isinstance(data, dict):
        # The hook receives the full message object
        prompt = data.get("message", "")
        if isinstance(prompt, dict):
            prompt = prompt.get("content", "")
        if isinstance(prompt, list):
            # Content blocks
            prompt = " ".join(
                block.get("text", "") for block in prompt if isinstance(block, dict)
            )

    result = check_prompt(str(prompt))
    if result:
        # Snowflake prompt detected -- check if cortex CLI is available
        if not shutil.which("cortex"):
            install_msg = (
                "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
                "snow CLI, or any other workaround. "
                "Load the cortex-code:cortex-setup skill NOW using the Skill tool, "
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
