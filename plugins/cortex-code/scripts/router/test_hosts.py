#!/usr/bin/env python3
"""Tests for host-specific routing: which agent runs the plugin and what it is told.

Run: python3 test_hosts.py -v
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import prompt_filter  # noqa: E402
from security import config_manager  # noqa: E402

HOST_ENV_VARS = (
    "CLAUDECODE",
    "CLAUDE_CODE_ENTRYPOINT",
    "PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT",
    "DEVIN_PLUGIN_ROOT",
    "DEVIN_PROJECT_DIR",
)

CLAUDE_INSTRUCTION = (
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

CODEX_ROOT = "/tmp/fake-plugin"
CODEX_INSTRUCTION = (
    "[CORTEX ROUTER] This prompt needs Cortex Code CLI. "
    "Follow these steps IN ORDER:\n"
    "Step 1: Verify cortex CLI is installed by running: which cortex && cortex --version\n"
    f"Step 2: Run the routing check: bash \"{CODEX_ROOT}/scripts/run_python.sh\" \"{CODEX_ROOT}/scripts/router/route_request.py\" "
    "--prompt \"<USER_PROMPT>\"\n"
    "  - Replace <USER_PROMPT> with the actual user prompt (shell-escaped).\n"
    "  - If output says route: claude -> STOP routing and handle the request yourself.\n"
    "  - If output says route: cortex -> proceed to Step 3.\n"
    "  - If the command fails, STOP and report the error. Never bypass configuration/policy errors.\n"
    f"Step 3: Execute via Cortex Code: bash \"{CODEX_ROOT}/scripts/run_python.sh\" \"{CODEX_ROOT}/scripts/router/execute_cortex.py\" "
    "--prompt \"<USER_PROMPT>\" --envelope \"RW\" --codex\n"
    "  - Use --envelope RO for read-only queries (SELECT, SHOW, DESCRIBE).\n"
    "  - Use --envelope RW for modifications (CREATE, ALTER, INSERT).\n"
    "  - The --codex flag is REQUIRED (enables non-interactive mode).\n"
    "  - For follow-up prompts, add --resume-last to maintain context.\n"
    "  - IMPORTANT: This command requires network access to Snowflake. Do NOT run it in a background terminal. Run it as a foreground command.\n"
    "Do NOT use SnowSQL, snow CLI, or any other tool for Snowflake operations. "
    "ONLY use the cortex CLI via the scripts above."
)

CLAUDE_INSTALL = (
    "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
    "snow CLI, or any other workaround. "
    "Load the snowflake-cortex-code:cortex-setup skill NOW using the Skill tool, "
    "then follow its instructions to install the CLI. "
    "If the user declines, tell them to visit "
    "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli"
)

CODEX_INSTALL = (
    "STOP. Cortex Code CLI is not installed. Do NOT attempt to use SnowSQL, "
    "snow CLI, or any other workaround. "
    "Tell the user to install it: visit "
    "https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli "
    "and follow the installation instructions. Then retry."
)

CLAUDE_PAYLOAD = {
    "hook_event_name": "UserPromptSubmit",
    "transcript_path": "/tmp/t.jsonl",
    "session_id": "x",
    "cwd": "/tmp",
    "prompt": "show me my snowflake tables",
}


def run_filter(payload, env=None, cortex_installed=True, files=None):
    """Run prompt_filter.main() in an isolated home and cwd; return additionalContext.

    files maps a path relative to the temporary home (or "cwd/<path>") to a JSON object.
    """
    env = env or {}
    with tempfile.TemporaryDirectory(prefix="test_hosts_") as tmp:
        home = Path(tmp) / "home"
        cwd = Path(tmp) / "project"
        home.mkdir()
        cwd.mkdir()
        for rel, data in (files or {}).items():
            target = cwd / rel[len("cwd/"):] if rel.startswith("cwd/") else home / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data), encoding="utf-8")
        clean = {k: v for k, v in os.environ.items() if k not in HOST_ENV_VARS}
        clean.update(env)
        stdout = io.StringIO()
        prompt_filter._detected_claude_code_from_stdin = False
        clean.update({"HOME": str(home), "USERPROFILE": str(home)})
        for name in ("CORTEX_SKILL_CONFIG", "CORTEX_SKILL_ORG_POLICY", "APPDATA"):
            clean.pop(name, None)
        with patch.dict(os.environ, clean, clear=True), \
             patch.object(config_manager, "DEFAULT_CONFIG_PATH", home / "config.yaml"), \
             patch.object(config_manager, "DEFAULT_ORG_POLICY_PATH", home / "policy.yaml"), \
             patch("prompt_filter.Path.home", return_value=home), \
             patch("prompt_filter.Path.cwd", return_value=cwd), \
             patch("prompt_filter.sys.stdin", io.StringIO(json.dumps(payload))), \
             patch("prompt_filter.sys.stdout", stdout), \
             patch("prompt_filter.shutil.which",
                   return_value="/usr/bin/cortex" if cortex_installed else None):
            try:
                prompt_filter.main()
            except SystemExit:
                pass
        out = json.loads(stdout.getvalue().strip() or "{}")
        return out.get("hookSpecificOutput", {}).get("additionalContext", "")


class CurrentRoutingCharacterization(unittest.TestCase):
    """Pins Claude Code and Codex output so the Host refactor can't change it."""

    def test_claude_code_routing_instruction(self):
        self.assertEqual(run_filter(CLAUDE_PAYLOAD), CLAUDE_INSTRUCTION)

    def test_codex_routing_instruction(self):
        got = run_filter({"prompt": "show me my snowflake warehouses"},
                         env={"PLUGIN_ROOT": CODEX_ROOT})
        self.assertEqual(got, CODEX_INSTRUCTION)

    def test_claude_code_install_message(self):
        self.assertEqual(run_filter(CLAUDE_PAYLOAD, cortex_installed=False), CLAUDE_INSTALL)

    def test_codex_install_message(self):
        got = run_filter({"prompt": "show me my snowflake warehouses"},
                         env={"PLUGIN_ROOT": CODEX_ROOT}, cortex_installed=False)
        self.assertEqual(got, CODEX_INSTALL)

    def test_non_snowflake_prompt_is_not_routed(self):
        self.assertEqual(run_filter({**CLAUDE_PAYLOAD, "prompt": "fix the bug in main.py"}), "")

    def test_claude_mcp_conflict_locations(self):
        server = {"mcpServers": {"snowflake": {"command": "snowflake-mcp"}}}
        for rel, label in (
            ("cwd/.mcp.json", ".mcp.json (project scope)"),
            (".claude.json", "~/.claude.json (user scope)"),
            (".claude/settings.json", "~/.claude/settings.json"),
        ):
            with self.subTest(rel=rel):
                got = run_filter(CLAUDE_PAYLOAD, files={rel: server})
                self.assertTrue(got.startswith("STOP. A Snowflake MCP server 'snowflake'"), got)
                self.assertIn(label, got)

    def test_disabled_flag_does_not_hide_claude_or_codex_conflicts(self):
        # Claude Code doesn't document "disabled" in mcpServers, so it must not suppress the STOP.
        server = {"mcpServers": {"snowflake": {"command": "snowflake-mcp", "disabled": True}}}
        for payload, env in ((CLAUDE_PAYLOAD, {}), ({"prompt": "show me my snowflake warehouses"},
                                                    {"PLUGIN_ROOT": CODEX_ROOT})):
            with self.subTest(env=env):
                got = run_filter(payload, env=env, files={"cwd/.mcp.json": server})
                self.assertTrue(got.startswith("STOP. A Snowflake MCP server 'snowflake'"), got)


class HostModel(unittest.TestCase):
    """The Host domain model: each host owns its detection, instructions and config."""

    def setUp(self):
        import hosts
        self.hosts = hosts

    def test_detect_claude_code_from_env(self):
        for env in ({"CLAUDECODE": "1"}, {"CLAUDE_CODE_ENTRYPOINT": "cli"},
                    {"CLAUDECODE": "1", "PLUGIN_ROOT": "/p"}):
            with self.subTest(env=env):
                self.assertIs(self.hosts.detect(env, {}), self.hosts.CLAUDE_CODE)

    def test_detect_claude_code_from_payload(self):
        for payload in ({"hook_event_name": "UserPromptSubmit"}, {"transcript_path": "/t"}):
            with self.subTest(payload=payload):
                self.assertIs(self.hosts.detect({"PLUGIN_ROOT": "/p"}, payload),
                              self.hosts.CLAUDE_CODE)

    def test_detect_codex_needs_plugin_root_and_no_claude_signal(self):
        for env in ({"PLUGIN_ROOT": "/p"}, {"CLAUDE_PLUGIN_ROOT": "/p"}):
            with self.subTest(env=env):
                self.assertIs(self.hosts.detect(env, {"prompt": "x"}), self.hosts.CODEX)

    def test_ambiguous_caller_is_claude_code(self):
        self.assertIs(self.hosts.detect({}, {"prompt": "x"}), self.hosts.CLAUDE_CODE)

    def test_routing_instructions_match_current_output(self):
        self.assertEqual(self.hosts.CLAUDE_CODE.routing_instruction(""), CLAUDE_INSTRUCTION)
        self.assertEqual(self.hosts.CODEX.routing_instruction(CODEX_ROOT), CODEX_INSTRUCTION)

    def test_install_messages_match_current_output(self):
        self.assertEqual(self.hosts.CLAUDE_CODE.install_message(), CLAUDE_INSTALL)
        self.assertEqual(self.hosts.CODEX.install_message(), CODEX_INSTALL)

    def test_plugin_root_from_env(self):
        self.assertEqual(self.hosts.plugin_root({"PLUGIN_ROOT": "/a", "CLAUDE_PLUGIN_ROOT": "/b"}), "/a")
        self.assertEqual(self.hosts.plugin_root({"CLAUDE_PLUGIN_ROOT": "/b"}), "/b")
        self.assertEqual(self.hosts.plugin_root({}), "")

    def test_mcp_config_sources_are_claude_locations(self):
        home, cwd = Path("/h"), Path("/c")
        want = [cwd / ".mcp.json", home / ".claude.json", home / ".claude" / "settings.json"]
        for host in (self.hosts.CLAUDE_CODE, self.hosts.CODEX):
            with self.subTest(host=host.name):
                got = [s.path for s in host.mcp_config_sources(home, cwd)]
                self.assertEqual(got, want)

    def test_entrypoint_labels(self):
        self.assertEqual(self.hosts.CLAUDE_CODE.entrypoint, "Claude Code Plugin")
        self.assertEqual(self.hosts.CODEX.entrypoint, "Codex Plugin")


DEVIN_ROOT = "/Users/dev/.local/share/devin/cli/plugins/cache/snowflake-cortex-code/3.6.0"
# Env and stdin Devin CLI 3000.11 actually sends to UserPromptSubmit hooks (spike-verified):
# it sets the Claude-compatible vars too, so DEVIN_* must take precedence.
DEVIN_ENV = {
    "DEVIN_PLUGIN_ROOT": DEVIN_ROOT,
    "DEVIN_PROJECT_DIR": "/tmp/proj",
    "CLAUDE_PLUGIN_ROOT": DEVIN_ROOT,
    "PLUGIN_ROOT": DEVIN_ROOT,
    "CLAUDE_PROJECT_DIR": "/tmp/proj",
}
DEVIN_PAYLOAD = {
    "hook_event_name": "UserPromptSubmit",
    "prompt": "Using Snowflake, run SELECT CURRENT_VERSION()",
    "session_id": "rhetorical-kilogram",
}


class DevinCliHost(unittest.TestCase):
    """Devin CLI runs the same plugin; it needs absolute paths and enforced envelopes."""

    def setUp(self):
        import hosts
        self.hosts = hosts

    def instruction(self):
        return run_filter(DEVIN_PAYLOAD, env=DEVIN_ENV)

    def test_detected_ahead_of_claude_compatible_signals(self):
        self.assertIs(self.hosts.detect(DEVIN_ENV, DEVIN_PAYLOAD), self.hosts.DEVIN_CLI)
        self.assertIs(self.hosts.detect({"DEVIN_PROJECT_DIR": "/p"}, {}), self.hosts.DEVIN_CLI)

    def test_plugin_root_prefers_devin_root(self):
        env = {"DEVIN_PLUGIN_ROOT": "/devin", "PLUGIN_ROOT": "/other"}
        self.assertEqual(self.hosts.plugin_root(env), "/devin")

    def test_instruction_uses_absolute_quoted_script_paths(self):
        got = self.instruction()
        self.assertTrue(got.startswith("[CORTEX ROUTER]"), got)
        self.assertIn(f'bash "{DEVIN_ROOT}/scripts/run_python.sh" "{DEVIN_ROOT}/scripts/router/route_request.py"', got)
        self.assertIn(f'bash "{DEVIN_ROOT}/scripts/run_python.sh" "{DEVIN_ROOT}/scripts/router/execute_cortex.py"', got)
        # Devin does not expand plugin variables in the agent's own shell commands.
        self.assertNotIn("${", got)

    def test_instruction_uses_enforced_envelope_and_names_host(self):
        got = self.instruction()
        self.assertNotIn("--codex", got)
        self.assertIn("--host devin_cli", got)
        self.assertIn("--envelope", got)

    def test_instruction_uses_devin_vocabulary(self):
        got = self.instruction()
        self.assertIn("/snowflake-cortex-code:cortex-run", got)
        self.assertNotIn("$cortex-run", got)
        self.assertNotIn("Skill tool", got)
        self.assertIn("Do NOT use SnowSQL", got)

    def test_explicit_command_gets_plugin_root_not_routing(self):
        # The skill's ${CLAUDE_PLUGIN_ROOT} isn't expanded by Devin, so the hook supplies the root.
        for prompt in ("/snowflake-cortex-code:cortex-run show my snowflake role",
                       "/snowflake-cortex-code:cortex-setup"):
            with self.subTest(prompt=prompt):
                got = run_filter({**DEVIN_PAYLOAD, "prompt": prompt}, env=DEVIN_ENV)
                self.assertNotIn("[CORTEX ROUTER]", got)
                self.assertIn(f'"{DEVIN_ROOT}"', got)
                self.assertIn("${CLAUDE_PLUGIN_ROOT}", got)

    def test_explicit_command_still_blocked_by_mcp_conflict(self):
        server = {"mcpServers": {"snowflake": {"command": "snowflake-mcp"}}}
        got = run_filter({**DEVIN_PAYLOAD, "prompt": "/snowflake-cortex-code:cortex-run show tables"},
                         env=DEVIN_ENV, files={"cwd/.devin/mcp_config.json": server})
        self.assertTrue(got.startswith("STOP. A Snowflake MCP server"), got)

    def test_install_message_points_to_setup_command(self):
        got = run_filter(DEVIN_PAYLOAD, env=DEVIN_ENV, cortex_installed=False)
        self.assertTrue(got.startswith("STOP. Cortex Code CLI is not installed."), got)
        self.assertIn("/snowflake-cortex-code:cortex-setup", got)
        self.assertNotIn("Skill tool", got)

    def test_mcp_conflict_in_devin_config_locations(self):
        server = {"mcpServers": {"sf": {"url": "https://acct.snowflakecomputing.com/api/v2/mcp"}}}
        for rel, label in (
            (".config/devin/mcp_config.json", "~/.config/devin/mcp_config.json (user scope)"),
            ("cwd/.devin/mcp_config.json", ".devin/mcp_config.json (project scope)"),
            ("cwd/.devin/mcp_config.local.json", ".devin/mcp_config.local.json (local scope)"),
            (".config/devin/config.json", "~/.config/devin/config.json (legacy user scope)"),
            ("cwd/.devin/config.json", ".devin/config.json (legacy project scope)"),
            ("cwd/.devin/config.local.json", ".devin/config.local.json (legacy local scope)"),
        ):
            with self.subTest(rel=rel):
                got = run_filter(DEVIN_PAYLOAD, env=DEVIN_ENV, files={rel: server})
                self.assertTrue(got.startswith("STOP. A Snowflake MCP server 'sf'"), got)
                self.assertIn(label, got)

    def test_disabled_mcp_server_is_not_a_conflict(self):
        server = {"mcpServers": {"snowflake": {"command": "snowflake-mcp", "disabled": True}}}
        got = run_filter(DEVIN_PAYLOAD, env=DEVIN_ENV,
                         files={".config/devin/mcp_config.json": server})
        self.assertTrue(got.startswith("[CORTEX ROUTER]"), got)

    def test_windows_user_config_uses_appdata(self):
        sources = self.hosts.DEVIN_CLI.mcp_config_sources(
            Path("/h"), Path("/c"), {"APPDATA": "/appdata"}, "nt")
        self.assertIn(Path("/appdata") / "devin" / "mcp_config.json", [s.path for s in sources])

    def test_entrypoint_label(self):
        self.assertEqual(self.hosts.DEVIN_CLI.entrypoint, "Devin CLI Plugin")
        self.assertIs(self.hosts.by_name("devin_cli"), self.hosts.DEVIN_CLI)


class DevinImportedMcpConfig(unittest.TestCase):
    """Devin CLI also loads MCP servers from other tools' config (docs: Configuration Import)."""

    SERVER = {"snowflake-ai-gateway": {"command": "npx",
                                       "args": ["mcp-remote", "https://acct.snowflakecomputing.com/api/v2/mcp"]}}

    def conflict(self, files):
        return run_filter(DEVIN_PAYLOAD, env=DEVIN_ENV, files=files)

    def test_imported_locations_are_scanned(self):
        standard = {"mcpServers": self.SERVER}
        for rel, label in (
            (".cursor/mcp.json", "~/.cursor/mcp.json (imported from Cursor)"),
            ("cwd/.cursor/mcp.json", ".cursor/mcp.json (imported from Cursor)"),
            (".codeium/windsurf/mcp_config.json", "~/.codeium/windsurf/mcp_config.json (imported from Windsurf)"),
            ("cwd/.mcp.json", ".mcp.json (imported from Claude Code)"),
            ("cwd/.claude/settings.json", ".claude/settings.json (imported from Claude Code)"),
            ("cwd/.claude/settings.local.json", ".claude/settings.local.json (imported from Claude Code)"),
            (".claude/settings.json", "~/.claude/settings.json (imported from Claude Code)"),
            (".claude/settings.local.json", "~/.claude/settings.local.json (imported from Claude Code)"),
            (".claude/mcp_servers.json", "~/.claude/mcp_servers.json (imported from Claude Code)"),
        ):
            with self.subTest(rel=rel):
                got = self.conflict({rel: standard})
                self.assertTrue(got.startswith("STOP. A Snowflake MCP server 'snowflake-ai-gateway'"), got)
                self.assertIn(label, got)

    def test_claude_json_user_and_local_scope(self):
        got = self.conflict({".claude.json": {"projects": {"/repo": {"mcpServers": self.SERVER}}}})
        self.assertIn("~/.claude.json (imported from Claude Code, local scope: /repo)", got)

    def test_opencode_schema(self):
        server = {"mcp": {"sf": {"type": "remote", "url": "https://acct.snowflakecomputing.com/mcp"}}}
        for rel, label in (("cwd/opencode.json", "opencode.json (imported from OpenCode)"),
                           (".config/opencode/opencode.json", "~/.config/opencode/opencode.json (imported from OpenCode)")):
            with self.subTest(rel=rel):
                self.assertIn(label, self.conflict({rel: server}))
        disabled = {"mcp": {"sf": {"type": "local", "command": ["snowflake-mcp"], "enabled": False}}}
        self.assertTrue(self.conflict({"cwd/opencode.json": disabled}).startswith("[CORTEX ROUTER]"))

    def test_zed_schema(self):
        server = {"context_servers": {"snow": {"command": {"path": "uvx", "args": ["snowflake-labs-mcp"]}}}}
        for rel, label in (("cwd/.zed/settings.json", ".zed/settings.json (imported from Zed)"),
                           (".config/zed/settings.json", "~/.config/zed/settings.json (imported from Zed)")):
            with self.subTest(rel=rel):
                self.assertIn(label, self.conflict({rel: server}))

    def test_read_config_from_disables_import(self):
        cursor = {".cursor/mcp.json": {"mcpServers": self.SERVER}}
        for rel in (".config/devin/config.json", "cwd/.devin/config.json"):
            with self.subTest(rel=rel):
                got = self.conflict({**cursor, rel: {"read_config_from": {"cursor": False}}})
                self.assertTrue(got.startswith("[CORTEX ROUTER]"), got)
        # Project config can re-enable what the user config turned off.
        got = self.conflict({**cursor, ".config/devin/config.json": {"read_config_from": {"cursor": False}},
                             "cwd/.devin/config.json": {"read_config_from": {"cursor": True}}})
        self.assertTrue(got.startswith("STOP."), got)

    def test_devin_own_config_not_affected_by_read_config_from(self):
        got = self.conflict({".config/devin/mcp_config.json": {"mcpServers": self.SERVER},
                             ".config/devin/config.json": {"read_config_from": {"claude": False, "cursor": False}}})
        self.assertTrue(got.startswith("STOP."), got)

    def test_claude_code_and_codex_sources_unchanged(self):
        import hosts
        home, cwd = Path("/h"), Path("/c")
        for host in (hosts.CLAUDE_CODE, hosts.CODEX):
            sources = host.mcp_config_sources(home, cwd)
            self.assertEqual([(s.path, s.label) for s in sources], [
                (cwd / ".mcp.json", ".mcp.json (project scope)"),
                (home / ".claude.json", "~/.claude.json"),
                (home / ".claude" / "settings.json", "~/.claude/settings.json"),
            ])


class ExecuteCortexHostLabel(unittest.TestCase):
    """Cortex records which host invoked it; Devin passes --host since its exec env lacks DEVIN_*."""

    def capture_entrypoint(self, env, host=None):
        import execute_cortex
        captured = {}

        def fake_popen(cmd, **kwargs):
            captured.update(kwargs.get("env") or {})
            raise OSError("stop after capturing env")

        clean = {k: v for k, v in os.environ.items() if k not in HOST_ENV_VARS}
        clean.update(env)
        with patch.dict(os.environ, clean, clear=True), \
             patch("execute_cortex.check_cortex_cli", return_value=True), \
             patch("execute_cortex.check_mcp_conflict", return_value=None), \
             patch("execute_cortex._check_envelope_allowed", return_value=None), \
             patch("execute_cortex.subprocess.Popen", side_effect=fake_popen):
            execute_cortex.execute_cortex_streaming("show tables", envelope="RO", host=host)
        return captured.get("CORTEX_CODE_ENTRYPOINT")

    def test_explicit_devin_host(self):
        self.assertEqual(self.capture_entrypoint({}, host="devin_cli"), "Devin CLI Plugin")

    def test_env_detection_unchanged_without_host(self):
        self.assertEqual(self.capture_entrypoint({"CLAUDECODE": "1", "PLUGIN_ROOT": "/p"}),
                         "Claude Code Plugin")
        self.assertEqual(self.capture_entrypoint({"PLUGIN_ROOT": "/p"}), "Codex Plugin")
        self.assertEqual(self.capture_entrypoint({}), "Unknown")

    def test_host_flag_is_validated(self):
        import execute_cortex
        with patch.object(sys, "argv", ["execute_cortex.py", "--prompt", "x", "--host", "bogus"]), \
             patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit):
                execute_cortex.main()


class SnowflakeMcpServerScan(unittest.TestCase):
    """One scan, used by both the hook and execute_cortex's pre-flight check."""

    def scan_with(self, host, files):
        import hosts
        with tempfile.TemporaryDirectory() as tmp:
            home, cwd = Path(tmp) / "home", Path(tmp) / "project"
            for rel, data in files.items():
                target = cwd / rel[len("cwd/"):] if rel.startswith("cwd/") else home / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(data), encoding="utf-8")
            return hosts.find_snowflake_mcp_server(host, home, cwd, {}, "posix")

    def test_finds_server_and_location(self):
        import hosts
        found = self.scan_with(hosts.DEVIN_CLI, {"cwd/.devin/mcp_config.json":
                                                 {"mcpServers": {"sf": {"command": "snowflake-labs-mcp"}}}})
        self.assertEqual(found, ("sf", ".devin/mcp_config.json (project scope)"))

    def test_claude_local_scope_and_unrelated_servers(self):
        import hosts
        data = {"mcpServers": {"github": {"command": "gh-mcp"}},
                "projects": {"/repo": {"mcpServers": {"snow": {"url": "https://x.snowflakecomputing.com"}}}}}
        found = self.scan_with(hosts.CLAUDE_CODE, {".claude.json": data})
        self.assertEqual(found, ("snow", "~/.claude.json (local scope: /repo)"))

    def test_ignores_disabled_and_malformed(self):
        import hosts
        files = {".config/devin/mcp_config.json": {"mcpServers": {"snowflake": {"command": "x", "disabled": True}}},
                 "cwd/.devin/mcp_config.json": ["not", "a", "dict"]}
        self.assertIsNone(self.scan_with(hosts.DEVIN_CLI, files))

    def test_execute_cortex_preflight_scans_devin_locations(self):
        import execute_cortex
        import hosts
        with tempfile.TemporaryDirectory() as tmp:
            home, cwd = Path(tmp) / "home", Path(tmp) / "project"
            (cwd / ".devin").mkdir(parents=True)
            home.mkdir()
            (cwd / ".devin" / "mcp_config.local.json").write_text(
                json.dumps({"mcpServers": {"snowflake": {"command": "snowflake-mcp"}}}), encoding="utf-8")
            with patch("execute_cortex.Path.home", return_value=home), \
                 patch("execute_cortex.Path.cwd", return_value=cwd):
                got = execute_cortex.check_mcp_conflict(hosts.DEVIN_CLI)
                self.assertIn(".devin/mcp_config.local.json (local scope)", got or "")
                self.assertIsNone(execute_cortex.check_mcp_conflict(hosts.CLAUDE_CODE))


if __name__ == "__main__":
    unittest.main()
