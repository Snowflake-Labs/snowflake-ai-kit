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


def check_remote_tool(backend: Backend, tool: object) -> dict:
    """Check an advertised host tool contract, not its server-side agent identity."""
    if backend.mode != "remote":
        raise ValueError("Tool schema checks require the remote backend.")
    if not isinstance(tool, dict) or tool.get("name") != backend.tool:
        raise ValueError("Tool name does not match CORTEX_PLUGIN_MCP_TOOL exactly.")
    schema = tool.get("inputSchema")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ValueError("Expected an object inputSchema from the configured MCP tool.")
    # We only implement the simple managed-agent contract, not general JSON Schema.
    if any(key in schema for key in ("$ref", "allOf", "anyOf", "oneOf", "not", "if",
                                     "dependentRequired", "dependentSchemas", "dependencies")):
        raise ValueError("Unsupported inputSchema constraints; do not guess tool arguments.")
    properties = schema.get("properties")
    required = schema.get("required")
    if (not isinstance(properties, dict) or not isinstance(required, list)
            or not all(isinstance(field, str) for field in required)
            or "text" not in required):
        raise ValueError("The managed agent tool must require a string 'text' argument.")
    text_schema = properties.get("text")
    if not isinstance(text_schema, dict) or text_schema.get("type") != "string":
        raise ValueError("The managed agent tool must require a string 'text' argument.")
    if set(required) != {"text"}:
        raise ValueError("Additional required tool arguments are not supported by this workflow.")
    thread_schema = properties.get("thread_id")
    supports_thread = isinstance(thread_schema, dict) and thread_schema.get("type") == "integer"
    return {
        "tool_check": "passed",
        "supports_thread_id": supports_thread,
        "agent_identity_verified": False,
        "note": (
            "This checks the input contract only. An administrator must verify the "
            "MCP CORTEX_AGENT_RUN identifier points to an agent with code_toolset_all."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument(
        "--check-prompt", action="store_true",
        help='Also check a JSON object {"prompt": "..."} from stdin for credential paths',
    )
    checks.add_argument(
        "--check-tool", action="store_true",
        help="Check a host tool descriptor {name, inputSchema} from stdin (not agent identity)",
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
        if args.check_tool:
            result.update(check_remote_tool(backend, json.load(sys.stdin)))
        print(json.dumps(result))
        return 0
    except (BackendConfigError, ValueError, OSError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())