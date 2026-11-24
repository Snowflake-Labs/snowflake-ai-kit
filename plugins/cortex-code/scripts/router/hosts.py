#!/usr/bin/env python3
"""Hosts: the coding agents that run this plugin.

A Host owns everything that differs between agents: how it is detected, the
routing instruction it receives, its explicit routing command, where its MCP
servers are configured, and the entrypoint label Cortex Code records.
Routing logic asks the detected Host instead of branching on the agent.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

import workloads

CORTEX_DOCS_URL = "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli"


@dataclass(frozen=True)
class McpConfigSource:
    """A file where a host may configure MCP servers.

    claude_json: True for ~/.claude.json, which also nests servers under projects.<path>.
    imported_from: the read_config_from key when the host imports this file from another tool.
    schema: "standard" (mcpServers), "opencode" (mcp + enabled), or "zed" (context_servers).
    honors_disabled: the host documents `"disabled": true` for entries in this file.
    """
    path: Path
    label: str
    claude_json: bool = False
    imported_from: str | None = None
    schema: str = "standard"
    honors_disabled: bool = False


@dataclass(frozen=True)
class Host:
    name: str
    entrypoint: str
    explicit_command: str
    _routing_instruction: Callable[[str], str]
    _install_message: Callable[[], str]
    _mcp_config_sources: Callable[..., list]
    # Prompts starting with this prefix already invoke the plugin explicitly; don't reroute them.
    explicit_prefix: str | None = None
    _explicit_context: Callable[[str], str] | None = None
    # Instructions for non-GENERAL workloads; set only on hosts that support them.
    _workload_instruction: Callable[[str, "workloads.Workload"], str] | None = None

    @property
    def supports_workloads(self) -> bool:
        return self._workload_instruction is not None

    def routing_instruction(self, plugin_root: str,
                            workload: "workloads.Workload" = workloads.GENERAL) -> str:
        if workload is not workloads.GENERAL and self.supports_workloads:
            return self._workload_instruction(plugin_root, workload)
        return self._routing_instruction(plugin_root)

    def explicit_invocation_context(self, plugin_root: str) -> str | None:
        """Context for an explicit plugin command, or None if the host needs none."""
        return self._explicit_context(plugin_root) if self._explicit_context else None

    def install_message(self) -> str:
        return self._install_message()

    def mcp_config_sources(self, home: Path, cwd: Path,
                           env: Mapping[str, str] | None = None,
                           os_name: str | None = None) -> list[McpConfigSource]:
        return self._mcp_config_sources(home, cwd, env or {}, os_name or os.name)

    def is_explicit_invocation(self, prompt: str) -> bool:
        return bool(self.explicit_prefix) and prompt.lstrip().startswith(self.explicit_prefix)


def plugin_root(env: Mapping[str, str]) -> str:
    return (env.get("DEVIN_PLUGIN_ROOT") or env.get("PLUGIN_ROOT")
            or env.get("CLAUDE_PLUGIN_ROOT") or "")


def _claude_mcp_sources(home: Path, cwd: Path, _env=None, _os_name=None) -> list[McpConfigSource]:
    return [
        McpConfigSource(cwd / ".mcp.json", ".mcp.json (project scope)"),
        McpConfigSource(home / ".claude.json", "~/.claude.json", claude_json=True),
        McpConfigSource(home / ".claude" / "settings.json", "~/.claude/settings.json"),
    ]


def _claude_code_instruction(_plugin_root: str) -> str:
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


def _claude_code_install() -> str:
    return (
        "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
        "snow CLI, or any other workaround. "
        "Load the snowflake-cortex-code:cortex-setup skill NOW using the Skill tool, "
        "then follow its instructions to install the CLI. "
        "If the user declines, tell them to visit "
        f"{CORTEX_DOCS_URL}"
    )


def _codex_instruction(root: str) -> str:
    return (
        "[CORTEX ROUTER] This prompt needs Cortex Code CLI. "
        "Follow these steps IN ORDER:\n"
        "Step 1: Verify cortex CLI is installed by running: which cortex && cortex --version\n"
        f"Step 2: Run the routing check: bash \"{root}/scripts/run_python.sh\" \"{root}/scripts/router/route_request.py\" "
        "--prompt \"<USER_PROMPT>\"\n"
        "  - Replace <USER_PROMPT> with the actual user prompt (shell-escaped).\n"
        "  - If output says route: claude -> STOP routing and handle the request yourself.\n"
        "  - If output says route: cortex -> proceed to Step 3.\n"
        "  - If the command fails, STOP and report the error. Never bypass configuration/policy errors.\n"
        f"Step 3: Execute via Cortex Code: bash \"{root}/scripts/run_python.sh\" \"{root}/scripts/router/execute_cortex.py\" "
        "--prompt \"<USER_PROMPT>\" --envelope \"RW\" --codex\n"
        "  - Use --envelope RO for read-only queries (SELECT, SHOW, DESCRIBE).\n"
        "  - Use --envelope RW for modifications (CREATE, ALTER, INSERT).\n"
        "  - The --codex flag is REQUIRED (enables non-interactive mode).\n"
        "  - For follow-up prompts, add --resume-last to maintain context.\n"
        "  - IMPORTANT: This command requires network access to Snowflake. Do NOT run it in a background terminal. Run it as a foreground command.\n"
        "Do NOT use SnowSQL, snow CLI, or any other tool for Snowflake operations. "
        "ONLY use the cortex CLI via the scripts above."
    )


def _codex_install() -> str:
    return (
        "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
        "snow CLI, or any other workaround. "
        "Tell the user to install it: visit "
        f"{CORTEX_DOCS_URL} "
        "and follow the installation instructions. Then retry."
    )


CLAUDE_CODE = Host(
    name="claude_code",
    entrypoint="Claude Code Plugin",
    explicit_command="$cortex-run",
    _routing_instruction=_claude_code_instruction,
    _install_message=_claude_code_install,
    _mcp_config_sources=_claude_mcp_sources,
)

CODEX = Host(
    name="codex",
    entrypoint="Codex Plugin",
    explicit_command="$cortex-run",
    _routing_instruction=_codex_instruction,
    _install_message=_codex_install,
    _mcp_config_sources=_claude_mcp_sources,
)


DEVIN_COMMAND_PREFIX = "/snowflake-cortex-code:"


def _devin_instruction(root: str) -> str:
    # Devin runs the agent's shell commands without plugin variables, so paths are absolute.
    python = f'bash "{root}/scripts/run_python.sh"'
    return (
        "[CORTEX ROUTER] This prompt needs Cortex Code CLI. "
        "Follow these steps IN ORDER and run each command exactly as written:\n"
        "Step 1: Verify cortex CLI is installed by running: cortex --version\n"
        f"Step 2: Run the routing check: {python} \"{root}/scripts/router/route_request.py\" "
        "--prompt \"<USER_PROMPT>\"\n"
        "  - Replace <USER_PROMPT> with the actual user prompt (shell-escaped).\n"
        "  - If output says route: claude -> STOP routing and handle the request yourself.\n"
        "  - If output says route: cortex -> proceed to Step 3.\n"
        "  - If the command fails, STOP and report the error. Never bypass configuration/policy errors.\n"
        f"Step 3: Execute via Cortex Code: {python} \"{root}/scripts/router/execute_cortex.py\" "
        "--prompt \"<USER_PROMPT>\" --envelope \"RW\" --host devin_cli\n"
        "  - Use --envelope RO for read-only queries (SELECT, SHOW, DESCRIBE).\n"
        "  - Use --envelope RW for modifications (CREATE, ALTER, INSERT).\n"
        "  - Every Cortex tool call is checked against the envelope; denied calls are reported back.\n"
        "  - For follow-up prompts, add --resume-last to maintain context.\n"
        "  - Run it in the foreground; it needs network access to Snowflake.\n"
        "Do NOT use SnowSQL, snow CLI, or any other tool for Snowflake operations. "
        "ONLY use the cortex CLI via the scripts above. "
        f"The user can also invoke this explicitly with {DEVIN_COMMAND_PREFIX}cortex-run."
    )


def _devin_workload_instruction(root: str, workload: "workloads.Workload") -> str:
    # MIGRATION is the only non-GENERAL workload. Cortex Code hands it to Snowflake AIM,
    # which asks questions (including consent to install itself) and spans sessions.
    python = f'bash "{root}/scripts/run_python.sh"'
    return (
        "[CORTEX ROUTER] This is a database migration. Cortex Code runs it with Snowflake AIM, "
        "its migration agent. Follow these steps IN ORDER and run each command exactly as written:\n"
        "Step 1: Verify cortex CLI is installed by running: cortex --version\n"
        f"Step 2: Run the routing check: {python} \"{root}/scripts/router/route_request.py\" "
        "--prompt \"<USER_PROMPT>\" --host devin_cli\n"
        "  - Replace <USER_PROMPT> with the actual user prompt (shell-escaped).\n"
        "  - If output says route: claude -> STOP routing and handle the request yourself.\n"
        "  - If the command fails, STOP and report the error. Never bypass configuration/policy errors.\n"
        f"Step 3: Execute via Cortex Code: {python} \"{root}/scripts/router/execute_cortex.py\" "
        f"--prompt \"<USER_PROMPT>\" --envelope \"{workload.required_envelope}\" --host devin_cli\n"
        f"  - Always use --envelope {workload.required_envelope}: AIM works through its MCP server "
        "and writes project files, which RO denies.\n"
        "  - Add --resume-last to every prompt after the first, so AIM continues the same migration.\n"
        "  - Run it in the foreground; steps such as data migration can take many minutes.\n"
        "Step 4: Relay Cortex's reply to the user word for word. AIM asks questions and approvals "
        "(for example, consent to install itself, which project directory to use, "
        "which source connection). Never answer for them: wait for the user's reply, then send it "
        "with --resume-last.\n"
        "Do NOT use SnowSQL, snow CLI, SnowConvert, or any other tool for the migration yourself. "
        "ONLY use the cortex CLI via the scripts above."
    )


def _devin_install() -> str:
    return (
        "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
        "snow CLI, or any other workaround. "
        f"Tell the user to run {DEVIN_COMMAND_PREFIX}cortex-setup to install it, "
        f"or to visit {CORTEX_DOCS_URL}. Then retry."
    )


def _devin_explicit_context(root: str) -> str:
    return (
        f"[CORTEX CODE PLUGIN] The plugin root is \"{root}\". "
        "Devin does not set ${CLAUDE_PLUGIN_ROOT}: wherever the skill's commands use "
        f"${{CLAUDE_PLUGIN_ROOT}}, substitute \"{root}\" and add --host devin_cli to "
        "execute_cortex.py. Do not search for the plugin directory."
    )


def _devin_mcp_sources(home: Path, cwd: Path, env: Mapping[str, str],
                       os_name: str) -> list[McpConfigSource]:
    """Devin CLI MCP config files, current (v3000.3+) then legacy mcpServers locations,
    then other tools' files Devin imports unless read_config_from turns them off."""
    if os_name == "nt" and env.get("APPDATA"):
        user_dir, user_label = Path(env["APPDATA"]) / "devin", "%APPDATA%\\devin\\"
    else:
        user_dir, user_label = home / ".config" / "devin", "~/.config/devin/"
    project = cwd / ".devin"
    def own_source(path, label):
        return McpConfigSource(path, label, honors_disabled=True)

    own = [
        own_source(user_dir / "mcp_config.json", f"{user_label}mcp_config.json (user scope)"),
        own_source(project / "mcp_config.json", ".devin/mcp_config.json (project scope)"),
        own_source(project / "mcp_config.local.json", ".devin/mcp_config.local.json (local scope)"),
        own_source(user_dir / "config.json", f"{user_label}config.json (legacy user scope)"),
        own_source(project / "config.json", ".devin/config.json (legacy project scope)"),
        own_source(project / "config.local.json", ".devin/config.local.json (legacy local scope)"),
    ]
    enabled = _devin_imports_enabled([user_dir / "config.json", project / "config.json",
                                      project / "config.local.json"])
    imported = [s for s in _devin_imported_sources(home, cwd) if enabled.get(s.imported_from, True)]
    return own + imported


_IMPORT_TOOLS = {"cursor": "Cursor", "windsurf": "Windsurf", "claude": "Claude Code",
                 "opencode": "OpenCode", "zed": "Zed"}


def _devin_imported_sources(home: Path, cwd: Path) -> list[McpConfigSource]:
    """MCP files Devin CLI imports from other tools (docs: Configuration Import).

    ~/.cursor/mcp.json is not in that table but Devin 3000.11 loads it (`devin mcp list`).
    """
    def src(path, label, tool, **kw):
        return McpConfigSource(path, f"{label} (imported from {_IMPORT_TOOLS[tool]})", imported_from=tool, **kw)

    return [
        src(cwd / ".cursor" / "mcp.json", ".cursor/mcp.json", "cursor"),
        src(home / ".cursor" / "mcp.json", "~/.cursor/mcp.json", "cursor"),
        src(home / ".codeium" / "windsurf" / "mcp_config.json", "~/.codeium/windsurf/mcp_config.json", "windsurf"),
        src(cwd / ".mcp.json", ".mcp.json", "claude"),
        src(cwd / ".claude" / "settings.json", ".claude/settings.json", "claude"),
        src(cwd / ".claude" / "settings.local.json", ".claude/settings.local.json", "claude"),
        McpConfigSource(home / ".claude.json", "~/.claude.json", claude_json=True, imported_from="claude"),
        src(home / ".claude" / "settings.json", "~/.claude/settings.json", "claude"),
        src(home / ".claude" / "settings.local.json", "~/.claude/settings.local.json", "claude"),
        src(home / ".claude" / "mcp_servers.json", "~/.claude/mcp_servers.json", "claude"),
        src(cwd / "opencode.json", "opencode.json", "opencode", schema="opencode"),
        src(home / ".config" / "opencode" / "opencode.json", "~/.config/opencode/opencode.json", "opencode",
            schema="opencode"),
        src(cwd / ".zed" / "settings.json", ".zed/settings.json", "zed", schema="zed"),
        src(home / ".config" / "zed" / "settings.json", "~/.config/zed/settings.json", "zed", schema="zed"),
    ]


def _devin_imports_enabled(config_paths) -> dict:
    """Merge read_config_from across Devin config files, later (more local) files winning."""
    enabled: dict = {}
    for path in config_paths:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        settings = data.get("read_config_from") if isinstance(data, Mapping) else None
        if isinstance(settings, Mapping):
            enabled.update({k: v for k, v in settings.items() if isinstance(v, bool)})
    return enabled


DEVIN_CLI = Host(
    name="devin_cli",
    entrypoint="Devin CLI Plugin",
    explicit_command=f"{DEVIN_COMMAND_PREFIX}cortex-run",
    _routing_instruction=_devin_instruction,
    _install_message=_devin_install,
    _mcp_config_sources=_devin_mcp_sources,
    explicit_prefix=DEVIN_COMMAND_PREFIX,
    _explicit_context=_devin_explicit_context,
    _workload_instruction=_devin_workload_instruction,
)

HOSTS = {host.name: host for host in (CLAUDE_CODE, CODEX, DEVIN_CLI)}


def by_name(name: str) -> Host:
    return HOSTS[name]


def _servers_in_source(source: McpConfigSource, data: Mapping):
    """Yield (servers, location) pairs from one MCP config file's parsed JSON."""
    if source.schema == "opencode":
        yield data.get("mcp", {}), source.label
        return
    if source.schema == "zed":
        yield data.get("context_servers", {}), source.label
        return
    if not source.claude_json:
        yield data.get("mcpServers", {}), source.label
        return
    # ~/.claude.json: user scope at top level, local scope under projects.<path>
    prefix = f"imported from {_IMPORT_TOOLS[source.imported_from]}, " if source.imported_from else ""
    yield data.get("mcpServers", {}), f"{source.label} ({prefix}user scope)"
    projects = data.get("projects", {})
    if isinstance(projects, Mapping):
        for project_path, project_cfg in projects.items():
            if isinstance(project_cfg, Mapping):
                yield (project_cfg.get("mcpServers", {}),
                       f"{source.label} ({prefix}local scope: {project_path})")


def _snowflake_server(servers, schema: str = "standard", honors_disabled: bool = False) -> str | None:
    if not isinstance(servers, Mapping):
        return None
    for name, cfg in servers.items():
        if not isinstance(cfg, Mapping) or (honors_disabled and cfg.get("disabled") is True):
            continue
        if schema != "standard":
            # OpenCode/Zed nest command and args differently; match anywhere in the entry.
            if schema == "opencode" and cfg.get("enabled") is False:
                continue
            if "snowflake" in f"{name} {json.dumps(cfg)}".lower():
                return name
            continue
        args = " ".join(str(a) for a in cfg.get("args", []))
        if "snowflake" in f"{name} {cfg.get('command', '')} {args} {cfg.get('url', '')}".lower():
            return name
    return None


def find_snowflake_mcp_server(host: Host, home: Path, cwd: Path,
                              env: Mapping[str, str] | None = None,
                              os_name: str | None = None) -> tuple[str, str] | None:
    """Return (server name, config location) of an enabled Snowflake MCP server, else None.

    Such a server duplicates Cortex Code's Snowflake tools and confuses auth.
    """
    for source in host.mcp_config_sources(home, cwd, env, os_name):
        try:
            if not source.path.exists():
                continue
            data = json.loads(source.path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not isinstance(data, Mapping):
            continue
        for servers, location in _servers_in_source(source, data):
            name = _snowflake_server(servers, source.schema, source.honors_disabled)
            if name:
                return name, location
    return None


def detect(env: Mapping[str, str], payload: Mapping | None) -> Host:
    """Identify the host from hook env and stdin payload.

    Devin CLI sets DEVIN_* alongside Claude-compatible signals, so it is checked first.
    Claude Code signals win next; Codex requires a plugin root and no Claude signal.
    Ambiguous callers are treated as Claude Code, whose skill path is permission-gated.
    """
    payload = payload if isinstance(payload, Mapping) else {}
    if env.get("DEVIN_PLUGIN_ROOT") or env.get("DEVIN_PROJECT_DIR"):
        return DEVIN_CLI
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        return CLAUDE_CODE
    if "hook_event_name" in payload or "transcript_path" in payload:
        return CLAUDE_CODE
    if plugin_root(env):
        return CODEX
    return CLAUDE_CODE
