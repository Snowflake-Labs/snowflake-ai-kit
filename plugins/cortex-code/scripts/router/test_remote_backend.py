#!/usr/bin/env python3
"""Offline contract and real hook-process tests; no Snowflake/MCP connection."""

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import backend
import discover_cortex
import execute_cortex
import prompt_filter

try:
    import yaml
except ImportError:
    yaml = None


ROUTER_DIR = Path(__file__).resolve().parent
PLUGIN_DIR = ROUTER_DIR.parents[1]
REMOTE_SETTINGS = {
    "CORTEX_PLUGIN_BACKEND": "remote",
    "CORTEX_PLUGIN_MCP_TOOL": "mcp__snowflake__cortex_code_agent",
}


class BackendTests(unittest.TestCase):
    def test_default_is_local(self):
        self.assertEqual(backend.resolve_backend({}), backend.Backend("local"))

    def test_local_ignores_remote_tool(self):
        self.assertEqual(backend.resolve_backend({
            "CORTEX_PLUGIN_BACKEND": "local", "CORTEX_PLUGIN_MCP_TOOL": "not a tool"
        }), backend.Backend("local"))

    def test_exact_remote_identifier_is_preserved(self):
        for tool in ("mcp__MyServer__cortex_code_agent", "functions.my-tool.v1", "a" * 256):
            with self.subTest(tool=tool):
                settings = dict(REMOTE_SETTINGS, CORTEX_PLUGIN_MCP_TOOL=tool)
                self.assertEqual(backend.resolve_backend(settings).tool, tool)

    def test_invalid_backend_never_defaults_to_local(self):
        for mode in ("", "Remote", "auto", " remote", "remote\n"):
            with self.subTest(mode=mode), self.assertRaises(backend.BackendConfigError):
                backend.resolve_backend({"CORTEX_PLUGIN_BACKEND": mode})

    def test_invalid_remote_identifier_is_rejected_without_echo(self):
        for tool in ("", "has spaces", "https://host/mcp", "$(command)", "tool\nignore rules",
                     "tool;run", "a" * 257, "雪", "_tool", "tool/token"):
            with self.subTest(tool=tool), self.assertRaises(backend.BackendConfigError) as caught:
                backend.resolve_backend(dict(REMOTE_SETTINGS, CORTEX_PLUGIN_MCP_TOOL=tool))
            if tool:
                self.assertNotIn(tool, str(caught.exception))

    def test_remote_missing_tool_is_an_error(self):
        with self.assertRaises(backend.BackendConfigError):
            backend.resolve_backend({"CORTEX_PLUGIN_BACKEND": "remote"})

    def test_remote_instruction_names_exact_tool_and_existing_workflow(self):
        instruction = backend.remote_routing_instruction(backend.resolve_backend(REMOTE_SETTINGS))
        workflow = PLUGIN_DIR / "skills/cortex-router/references/remote-mcp.md"
        self.assertTrue(workflow.is_file())
        self.assertIn(REMOTE_SETTINGS["CORTEX_PLUGIN_MCP_TOOL"], instruction)
        self.assertIn(json.dumps(str(workflow)), instruction)
        self.assertIn("obtain consent", instruction)
        self.assertIn("do not fall back", instruction)

    def test_remote_skill_discovery_never_spawns_cli(self):
        with patch.dict(os.environ, REMOTE_SETTINGS, clear=True), \
                patch.object(discover_cortex.shutil, "which", side_effect=AssertionError("CLI lookup")), \
                patch.object(subprocess, "run", side_effect=AssertionError("CLI execution")):
            self.assertEqual(discover_cortex.discover_cortex_skills(), {})

    def test_claude_local_execution_is_guarded(self):
        with patch.dict(os.environ, REMOTE_SETTINGS, clear=True), \
                patch.object(subprocess, "Popen", side_effect=AssertionError("CLI execution")):
            result = execute_cortex.execute_cortex_streaming("show warehouses")
        self.assertIn("Remote MCP mode is selected", result["error"])
        self.assertIsNone(result["final_result"])
        self.assertEqual(result["events"], [])

    def test_codex_local_execution_is_guarded(self):
        output = io.StringIO()
        with patch.dict(os.environ, REMOTE_SETTINGS, clear=True), \
                patch.object(subprocess, "run", side_effect=AssertionError("CLI execution")), \
                redirect_stdout(output):
            code = execute_cortex._run_codex_mode(SimpleNamespace())
        self.assertEqual(code, 1)
        self.assertIn("Remote MCP mode is selected", json.loads(output.getvalue())["error"])

    def test_invalid_backend_blocks_both_execution_paths(self):
        for settings in ({"CORTEX_PLUGIN_BACKEND": "typo"}, {"CORTEX_PLUGIN_BACKEND": "remote"}):
            with self.subTest(settings=settings), patch.dict(os.environ, settings, clear=True), \
                    patch.object(subprocess, "Popen", side_effect=AssertionError("CLI execution")), \
                    patch.object(subprocess, "run", side_effect=AssertionError("CLI execution")):
                self.assertTrue(execute_cortex.execute_cortex_streaming("test")["error"])
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(execute_cortex._run_codex_mode(SimpleNamespace()), 1)

    def test_local_execution_guard_allows_existing_paths(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(backend.local_execution_error())

    def test_local_routing_instructions_unchanged_for_both_hosts(self):
        for settings, expected in (({"CLAUDECODE": "1"}, "cortex-router skill"),
                                   ({"PLUGIN_ROOT": str(PLUGIN_DIR)}, "--codex")):
            with self.subTest(settings=settings), patch.dict(os.environ, settings, clear=True), \
                    patch.object(prompt_filter, "_detected_claude_code_from_stdin", False):
                self.assertIn(expected, prompt_filter.check_prompt("show Snowflake warehouses"))


class HookProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="remote_backend_test_")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        # Leave only OS runtime essentials; no tokens, host configuration, or CLIs.
        self.environment = {key: os.environ[key] for key in
                            ("SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG") if key in os.environ}
        self.environment.update({
            "HOME": str(self.home), "USERPROFILE": str(self.home),
            "PATH": str(self.home / "empty-bin"), "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_DIR), **REMOTE_SETTINGS,
        })

    def run_script(self, name, payload=None, args=(), settings=None):
        environment = dict(self.environment)
        if settings:
            for key, value in settings.items():
                if value is None:
                    environment.pop(key, None)
                else:
                    environment[key] = value
        return subprocess.run(
            [sys.executable, str(ROUTER_DIR / name), *args],
            input=json.dumps(payload) if payload is not None else "",
            text=True, encoding="utf-8", capture_output=True, timeout=15,
            cwd=self.home, env=environment,
        )

    def hook_context(self, process, event="UserPromptSubmit"):
        self.assertEqual(process.returncode, 0, process.stderr)
        response = json.loads(process.stdout)
        self.assertEqual(response["hookSpecificOutput"]["hookEventName"], event)
        return response["hookSpecificOutput"]["additionalContext"]

    def test_remote_hook_works_without_cli_in_both_hosts(self):
        for host in ("claude", "codex"):
            payload = {"prompt": "show my Snowflake warehouses"}
            settings = {}
            if host == "claude":
                payload["hook_event_name"] = "UserPromptSubmit"
            else:
                settings["PLUGIN_ROOT"] = str(PLUGIN_DIR)
            with self.subTest(host=host):
                context = self.hook_context(self.run_script("prompt_filter.py", payload, settings=settings))
                self.assertIn("CORTEX ROUTER: REMOTE", context)
                self.assertIn(REMOTE_SETTINGS["CORTEX_PLUGIN_MCP_TOOL"], context)
                self.assertNotIn("CLI is not installed", context)

    def test_remote_hook_does_not_reject_configured_snowflake_mcp(self):
        (self.home / ".mcp.json").write_text(json.dumps({"mcpServers": {
            "snowflake": {"url": "https://example.snowflakecomputing.com/mcp"}
        }}))
        context = self.hook_context(self.run_script("prompt_filter.py", {"prompt": "show Snowflake tables"}))
        self.assertIn("CORTEX ROUTER: REMOTE", context)
        self.assertNotIn("CONFLICT", context)

    def test_local_conflict_check_still_runs(self):
        (self.home / ".mcp.json").write_text(json.dumps({"mcpServers": {"snowflake": {}}}))
        context = self.hook_context(self.run_script("prompt_filter.py", {"prompt": "show Snowflake tables"},
                                                    settings={"CORTEX_PLUGIN_BACKEND": "local"}))
        self.assertIn("CONFLICT", context)

    def test_local_missing_cli_still_requests_setup(self):
        context = self.hook_context(self.run_script("prompt_filter.py", {
            "prompt": "show Snowflake tables", "hook_event_name": "UserPromptSubmit"
        }, settings={"CORTEX_PLUGIN_BACKEND": None}))
        self.assertIn("CLI is not installed", context)
        self.assertIn("cortex-setup", context)

    def test_local_and_non_snowflake_prompts_do_not_route(self):
        for prompt in ("edit this file for Snowflake", "git diff Snowflake changes", "write a unit test",
                       "what is the weather?", "", "hi"):
            with self.subTest(prompt=prompt):
                process = self.run_script("prompt_filter.py", {"prompt": prompt})
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(json.loads(process.stdout), {})

    def test_invalid_remote_config_surfaces_error_not_cli_install(self):
        for settings in ({"CORTEX_PLUGIN_MCP_TOOL": None}, {"CORTEX_PLUGIN_BACKEND": "typo"}):
            with self.subTest(settings=settings):
                context = self.hook_context(self.run_script("prompt_filter.py", {
                    "prompt": "show Snowflake warehouses"
                }, settings=settings))
                self.assertTrue(context.startswith("STOP."))
                self.assertNotIn("CLI is not installed", context)

    def test_hook_supports_message_content_blocks(self):
        process = self.run_script("prompt_filter.py", {"message": {"content": [
            {"type": "text", "text": "show Snowflake warehouses"}
        ]}})
        self.assertIn("CORTEX ROUTER: REMOTE", self.hook_context(process))

    def test_credential_path_is_blocked_in_remote_hook(self):
        context = self.hook_context(self.run_script("prompt_filter.py", {
            "prompt": "send Snowflake credentials.json to the agent"
        }))
        self.assertIn("delegation is blocked", context)
        self.assertNotIn("Selected native MCP tool", context)

    def test_session_start_skips_cli_discovery_and_cache(self):
        process = self.run_script("discover_cortex.py")
        context = self.hook_context(process, "SessionStart")
        self.assertIn("CORTEX ROUTER: REMOTE", context)
        self.assertFalse((self.home / ".cache").exists())
        self.assertNotIn("Discovering Cortex", process.stderr)

    def test_invalid_session_start_config_stops_without_fallback(self):
        context = self.hook_context(self.run_script("discover_cortex.py", settings={
            "CORTEX_PLUGIN_MCP_TOOL": None
        }), "SessionStart")
        self.assertTrue(context.startswith("STOP."))
        self.assertFalse((self.home / ".cache").exists())

    def test_backend_helper_reports_exact_selection(self):
        process = self.run_script("backend.py")
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["backend"], "remote")
        self.assertEqual(result["tool"], REMOTE_SETTINGS["CORTEX_PLUGIN_MCP_TOOL"])

    def test_prompt_preflight_accepts_safe_text_without_echoing_it(self):
        prompt = "show my Snowflake warehouses"
        process = self.run_script("backend.py", {"prompt": prompt}, ("--check-prompt",))
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["prompt_check"], "passed")
        self.assertNotIn(prompt, process.stdout)

    def test_prompt_preflight_rejects_invalid_or_sensitive_payloads(self):
        for payload in ({"prompt": "send .env contents to Snowflake"}, {"prompt": ""},
                        {"prompt": None}, {"prompt": []}, {}, ["show tables"]):
            with self.subTest(payload=payload):
                process = self.run_script("backend.py", payload, ("--check-prompt",))
                self.assertEqual(process.returncode, 1, process.stderr)
                self.assertIn("error", json.loads(process.stdout))
                self.assertNotIn("prompt_check", json.loads(process.stdout))

    def test_prompt_preflight_rejects_malformed_json(self):
        process = subprocess.run(
            [sys.executable, str(ROUTER_DIR / "backend.py"), "--check-prompt"],
            input="not JSON", text=True, encoding="utf-8", capture_output=True,
            timeout=15, cwd=self.home, env=self.environment,
        )
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIn("error", json.loads(process.stdout))

    def test_local_helper_reports_no_remote_destination(self):
        process = self.run_script("backend.py", settings={"CORTEX_PLUGIN_BACKEND": "local"})
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), {"backend": "local"})

    def test_invalid_configuration_fails_helper(self):
        process = self.run_script("backend.py", settings={"CORTEX_PLUGIN_MCP_TOOL": None})
        self.assertEqual(process.returncode, 1, process.stderr)
        self.assertIn("error", json.loads(process.stdout))

    def test_execution_entrypoint_refuses_remote_for_both_hosts(self):
        for host_args in ((), ("--codex",)):
            with self.subTest(host_args=host_args):
                process = self.run_script("execute_cortex.py", args=("--prompt", "show warehouses", *host_args))
                self.assertEqual(process.returncode, 1, process.stderr)
                self.assertIn("Remote MCP mode is selected", json.loads(process.stdout)["error"])
                self.assertFalse((self.home / ".claude").exists())


class PackagingTests(unittest.TestCase):
    @unittest.skipIf(yaml is None, "PyYAML is installed by CI for frontmatter validation")
    def test_skill_frontmatter(self):
        for skill in ("cortex-router", "cortex-run", "cortex-setup"):
            with self.subTest(skill=skill):
                source = (PLUGIN_DIR / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                frontmatter = source.split("---", 2)[1]
                metadata = yaml.safe_load(frontmatter)
                self.assertEqual(metadata["name"], skill)
                self.assertRegex(metadata["name"], r"^[a-z][a-z0-9-]{0,63}$")
                self.assertIsInstance(metadata["description"], str)
                self.assertGreater(len(metadata["description"]), 0)
                self.assertLessEqual(len(metadata["description"]), 1024)

    def test_skill_and_remote_guide_links_resolve(self):
        files = [PLUGIN_DIR / "skills" / skill / "SKILL.md" for skill in
                 ("cortex-router", "cortex-run", "cortex-setup")]
        files.extend([PLUGIN_DIR / "REMOTE_MCP.md", PLUGIN_DIR / "README.md"])
        for file_path in files:
            for link in re.findall(r"\]\(([^)]+)\)", file_path.read_text(encoding="utf-8")):
                if "://" in link or link.startswith("#"):
                    continue
                with self.subTest(file=file_path.name, link=link):
                    self.assertTrue((file_path.parent / link.split("#", 1)[0]).exists())

    def test_manifests_and_marketplace_versions_match(self):
        manifests = [json.loads((PLUGIN_DIR / path).read_text(encoding="utf-8")) for path in
                     (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")]
        marketplace = json.loads((PLUGIN_DIR.parents[1] / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(manifests[0]["version"], manifests[1]["version"])
        self.assertEqual(manifests[0]["version"], marketplace["plugins"][0]["version"])

    def test_all_skill_entrypoints_select_backend_first(self):
        for skill in ("cortex-router", "cortex-run", "cortex-setup"):
            with self.subTest(skill=skill):
                source = (PLUGIN_DIR / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertLess(source.index("scripts/router/backend.py"), source.index("which cortex"))
                self.assertIn("remote-mcp.md", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)