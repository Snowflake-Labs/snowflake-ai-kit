#!/usr/bin/env python3
"""Envelope-driven policy for cortex `can_use_tool` permission requests.

The cortex CLI, when launched with `--permission-prompt-tool stdio`, emits
a control_request for every tool call:

    {
      "type": "control_request", "request_id": "...",
      "request": {
        "subtype": "can_use_tool",
        "tool_name": "Bash" | "Read" | "Write" | "Edit" |
                     "SQL" | "WebSearch" | "WebFetch" | "MCP" | ...,
        "input": {"action": "...", "resource": "..."},
        "tool_use_id": "..."
      }
    }

Our wrapper replies with control_response carrying behavior=allow|deny.
This module holds that decision: pure function of envelope + request.

Design note: for RO/RESEARCH we default-deny writes and DDL/DML; for RW
we default-allow but block destructive bash. For DEPLOY everything is
allowed. The decision is enforcement, not advice -- the envelope text we
prepend to the prompt is a soft hint; this function is the hard gate.
"""

from __future__ import annotations

import re
import shlex
from typing import Tuple


SAFE_BASH_PREFIXES = (
    "git status", "git log", "git diff", "git show", "git branch",
    "git blame", "git remote", "git config --get", "git rev-parse",
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "rg",
    "find", "file", "stat", "which", "type", "echo", "printf",
    "env", "date", "uname", "whoami", "id",
    "snow sql", "snow connection", "snow stage list",
)

DESTRUCTIVE_BASH_PATTERNS = (
    re.compile(r"\brm\s+-rf?\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\bchmod\s+777\b"),
    re.compile(r"\bgit\s+push\s+.*--force\b"),
    re.compile(r"\bgit\s+push\s+-f\b"),
    re.compile(r"\bgit\s+reset\s+--hard\b"),
    re.compile(r"\bmkfs\b"),
    re.compile(r":>\s*/\S"),
    re.compile(r"\bdd\s+if=.*of=/dev/\S"),
)

READ_ONLY_SQL_PREFIXES = (
    "select", "show", "describe", "desc ", "explain", "with ", "use ",
)


def _strip_sql(stmt: str) -> str:
    return stmt.strip().lstrip("(").lstrip().lower()


def _is_read_only_sql(resource: str) -> bool:
    lowered = _strip_sql(resource)
    return any(lowered.startswith(p) for p in READ_ONLY_SQL_PREFIXES)


# Shell fragments that turn an otherwise-safe command into a write or a
# surface for arbitrary execution. Any presence disqualifies the command
# from SAFE_BASH_PREFIXES in RO/RESEARCH mode.
#
# NOTE: Redirect detection uses shlex tokenization (see _has_unsafe_fragments)
# to avoid false-positives on Snowflake's `param => value` named-argument
# syntax which appears inside quoted -q "..." arguments.
UNSAFE_SHELL_FRAGMENT_PATTERNS = (
    re.compile(r"\$\("),                     # command substitution $( ... )
    re.compile(r"`"),                        # backtick substitution
    re.compile(r";\s*\S"),                   # command chaining `a; b`
    re.compile(r"&&\s*\S"),                  # `a && b`
    re.compile(r"\|\|\s*\S"),                # `a || b`
    re.compile(r"\bsudo\b"),                 # privilege escalation
    re.compile(r"\btee\b"),                  # tee writes
    re.compile(r"\bxargs\s+rm\b"),           # piped deletion
)

# Redirect operators that indicate writes. Checked only on unquoted shell
# tokens (after shlex splitting) so that `=>` inside quoted SQL is safe.
_REDIRECT_RE = re.compile(r"(?<!\d)>(?!=|>)")
_APPEND_RE = re.compile(r">>")


def _has_redirect_in_unquoted_tokens(command: str) -> bool:
    """Check for shell redirects only in unquoted token positions.

    Uses shlex.split to parse the command line, then inspects each token to
    see if it IS a shell redirect (e.g., ">", ">>", "2>", ">file", ">>file").
    Content inside quoted arguments (e.g., snow sql -q "... => 'val' ...") is
    collapsed into a single token whose text happens to contain `>` — but
    that's data, not a redirect operator.

    A token is flagged as a redirect if:
      - It matches a POSIX redirect pattern: optional fd digit(s) followed by
        > or >> optionally followed by a filename (e.g., ">" "2>" ">out" ">>log")
      - It is NOT the `=>` named-argument operator (which is purely data even
        when unquoted in the original command line, since in shell `=>` is just
        a word starting with `=` followed by a redirect).

    To catch the real-world exploit `cat a.txt =>b.txt` (which IS a redirect
    in POSIX shells because `=` just ends the preceding word and `>b.txt` is
    a redirect), we flag tokens matching `=?>.*` ONLY when the `>` is NOT
    preceded by `=` as part of a `=>` digraph that shlex would have kept
    together from a quoted context.
    """
    try:
        tokens = shlex.split(command)
    except ValueError:
        return True

    # Pattern: optional fd digits, then > or >>, optionally followed by filename
    redirect_re = re.compile(r"^\d*>{1,2}")
    # Pattern: `=>file` — in POSIX shells, `=` is just a character that ends
    # the preceding token, and `>file` is a redirect (e.g., `cat a.txt =>b.txt`)
    eq_redirect_re = re.compile(r"^=>{1,2}")
    for token in tokens:
        if redirect_re.match(token) or eq_redirect_re.match(token):
            return True
    return False


def _has_unsafe_fragments(command: str) -> bool:
    if _has_redirect_in_unquoted_tokens(command):
        return True
    return any(p.search(command) for p in UNSAFE_SHELL_FRAGMENT_PATTERNS)


def _is_safe_bash(command: str) -> bool:
    stripped = command.strip()
    if any(re.search(p, stripped) for p in DESTRUCTIVE_BASH_PATTERNS):
        return False
    if _has_unsafe_fragments(stripped):
        return False
    return any(stripped.startswith(p) for p in SAFE_BASH_PREFIXES)


def _is_destructive_bash(command: str) -> bool:
    return any(re.search(p, command) for p in DESTRUCTIVE_BASH_PATTERNS)


def decide(envelope: str, tool_name: str, action: str, resource: str) -> Tuple[str, str]:
    """Return ("allow"|"deny", reason) for a permission request.

    envelope: RO, RW, RESEARCH, DEPLOY
    tool_name: PascalCase tool (Bash, Read, Write, Edit, SQL, WebSearch,
               WebFetch, MCP, NotebookExecute, NotebookEdit, Glob, Grep, ...)
    action: permission action ("execute_command", "file_read", "file_write", ...)
    resource: the command, SQL text, or file path under request
    """
    env = envelope.upper()
    tool = tool_name

    if env == "DEPLOY":
        if tool == "Bash" and _is_destructive_bash(resource or ""):
            return "deny", f"DEPLOY envelope still blocks destructive bash: {resource!r}"
        return "allow", "DEPLOY: full access"

    read_only_tools = {"Read", "Glob", "Grep"}

    if env == "RESEARCH":
        if tool in read_only_tools | {"WebSearch", "WebFetch"}:
            return "allow", f"RESEARCH allows {tool}"
        if tool == "SQL" and _is_read_only_sql(resource or ""):
            return "allow", "RESEARCH allows read-only SQL"
        if tool == "Bash" and _is_safe_bash(resource or ""):
            return "allow", "RESEARCH allows safe read-only bash"
        return "deny", f"RESEARCH envelope denies {tool} ({action})"

    if env == "RO":
        if tool in read_only_tools:
            return "allow", f"RO allows {tool}"
        if tool == "SQL" and _is_read_only_sql(resource or ""):
            return "allow", "RO allows read-only SQL"
        if tool == "Bash" and _is_safe_bash(resource or ""):
            return "allow", "RO allows safe read-only bash"
        return "deny", f"RO envelope denies {tool} ({action})"

    # RW: default-allow, block destructive bash.
    if tool == "Bash" and _is_destructive_bash(resource or ""):
        return "deny", f"RW blocks destructive bash: {resource!r}"
    return "allow", f"RW allows {tool}"
