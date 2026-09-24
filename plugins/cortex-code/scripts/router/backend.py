#!/usr/bin/env python3
"""Resolve plugin routing without connecting to MCP or loading credentials."""

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Mapping, Optional


class BackendConfigError(ValueError):
    """Backend settings are incomplete or invalid; do not fall back."""


@dataclass(frozen=True)
class Backend:
    mode: str
    tool: Optional[str] = None


def resolve_backend(environ: Optional[Mapping[str, str]] = None) -> Backend:
    settings = os.environ if environ is None else environ
    mode = settings.get("CORTEX_PLUGIN_BACKEND", "local")
    if mode not in ("local", "remote"):
        raise BackendConfigError(
            "CORTEX_PLUGIN_BACKEND must be 'local' or 'remote'. "
            "No backend was selected; execution is blocked."
        )
    if mode == "local":
        return Backend(mode)

    tool = settings.get("CORTEX_PLUGIN_MCP_TOOL", "")
    # Only a host-visible identifier is accepted, never a URL, token or instruction.
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,255}", tool):
        raise BackendConfigError(
            "Remote mode requires CORTEX_PLUGIN_MCP_TOOL: the exact host-visible "
            "MCP tool identifier (1-256 letters, digits, underscores, dots or hyphens, "
            "starting with a letter). Configure and authenticate the managed MCP "
            "server in your host first. Do not put a URL or credentials here."
        )
    return Backend(mode, tool)


def remote_routing_instruction(backend: Backend) -> str:
    workflow = Path(__file__).resolve().parents[2] / "skills/cortex-router/references/remote-mcp.md"
    return (
        f"[CORTEX ROUTER: REMOTE] Selected native MCP tool: {backend.tool}. "
        "Delegate only Snowflake-side tasks; unrelated requests stay with the host. "
        f"Read and follow the remote workflow at {json.dumps(str(workflow))} before calling it. "
        "Use only this exact tool through the host's authenticated MCP connection. "
        "If it is unavailable or incompatible, STOP and report the problem; do not "
        "fall back to another tool or the CLI. Do not install or invoke cortex, "
        "discover local skills, or disable the Snowflake MCP server. "
        "Before first delegation, obtain consent to remote execution without the "
        "plugin's local per-command security envelopes. If those guarantees are "
        "required by the user or organization, do not delegate. Keep local files "
        "with the host; do not upload files or transcripts automatically."
    )


def local_execution_error() -> Optional[str]:
    try:
        backend = resolve_backend()
    except BackendConfigError as error:
        return str(error)
    if backend.mode == "remote":
        return (
            "Remote MCP mode is selected. execute_cortex.py only executes the local "
            "CLI and will not run. Use the configured native MCP tool via the remote "
            "workflow, or explicitly select CORTEX_PLUGIN_BACKEND=local."
        )
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-prompt", action="store_true",
        help='Also check a JSON object {"prompt": "..."} from stdin for credential paths',
    )
    args = parser.parse_args()
    try:
        backend = resolve_backend()
        if args.check_prompt:
            payload = json.load(sys.stdin)
            if not isinstance(payload, dict) or not isinstance(payload.get("prompt"), str):
                raise ValueError("Expected a JSON object with a string 'prompt' on stdin.")
            if not payload["prompt"].strip():
                raise ValueError("The prompt must not be empty.")
            # Share the existing credential-path preflight; never execute the CLI.
            from execute_cortex import check_credential_paths
            if check_credential_paths(payload["prompt"]):
                raise ValueError("Prompt references a credential path; delegation is blocked.")
        result = {"backend": backend.mode}
        if backend.mode == "remote":
            result.update(tool=backend.tool, instructions=remote_routing_instruction(backend))
        if args.check_prompt:
            result["prompt_check"] = "passed"
        print(json.dumps(result))
        return 0
    except (BackendConfigError, ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())