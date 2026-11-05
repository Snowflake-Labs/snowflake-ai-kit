#!/usr/bin/env python3
"""Tests for workloads: what kind of Cortex Code work a prompt is.

The migration workload hands database migrations to Snowflake AIM, the Cortex Code
migration agent. Only hosts that support workloads (Devin CLI) route it; Claude Code
and Codex output stays exactly as before.

Run: python3 test_workloads.py -v
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
import hosts  # noqa: E402
import route_request  # noqa: E402
from test_hosts import (  # noqa: E402
    CLAUDE_INSTRUCTION, CLAUDE_PAYLOAD, CODEX_INSTRUCTION, CODEX_ROOT, run_filter,
)

DEVIN_ROOT = "/tmp/devin-plugin"
DEVIN_ENV = {"DEVIN_PLUGIN_ROOT": DEVIN_ROOT, "DEVIN_PROJECT_DIR": "/tmp/proj"}

# Prompts from the AIM docs and typical migration asks, with what main does today
# for Claude Code and Codex: (prompt, hook routes, route_request route, confidence).
MIGRATION_PROMPTS = [
    ("start a database migration", False, "claude", 0.5),
    ("continue my migration", False, "claude", 0.5),
    ("migrate my SQL Server database to Snowflake", True, "cortex", 1.0),
    ("convert this T-SQL stored procedure", False, "claude", 0.5),
    ("convert my Oracle PL/SQL package to Snowflake", True, "cortex", 1.0),
    ("migrate Redshift to Snowflake", True, "cortex", 1.0),
    ("migrate my postgres and mysql databases to Snowflake", True, "claude", 4 / 7),
    ("assess my SSIS packages", False, "claude", 0.5),
    ("import SQL files from ./my-exported-scripts/", False, "claude", 0.5),
    ("what is the current state of my migration?", False, "claude", 0.5),
    ("run snowconvert on ./src", False, "claude", 0.5),
    ("/migrate deploy tables", False, "claude", 0.5),
    ("decommission our Teradata data warehouse", True, "cortex", 1.0),
]

NOT_MIGRATIONS = [
    "migrate my React app to Vite",
    "convert this CSV to JSON",
    "move files to another folder",
    "fix the bug in oracle_client.py",
    "write a python script that reads a file",
    "show me my snowflake tables",
    "run the unit test suite",
]


def analyze(prompt, host=None):
    """Today's scorer when no host is given; the host-aware decision otherwise."""
    if host is None:
        return route_request.analyze_with_llm_logic(prompt, {})
    return route_request.decide_route(prompt, {}, host)


class MigrationCharacterization(unittest.TestCase):
    """Pins Claude Code and Codex behaviour for migration prompts (Devin-only scope)."""

    def test_claude_code_hook_output_unchanged(self):
        for prompt, routes, _, _ in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                got = run_filter({**CLAUDE_PAYLOAD, "prompt": prompt}, env={"CLAUDECODE": "1"})
                self.assertEqual(got, CLAUDE_INSTRUCTION if routes else "")

    def test_codex_hook_output_unchanged(self):
        for prompt, routes, _, _ in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                got = run_filter({"prompt": prompt}, env={"PLUGIN_ROOT": CODEX_ROOT})
                self.assertEqual(got, CODEX_INSTRUCTION if routes else "")

    def test_route_request_without_host_unchanged(self):
        for prompt, _, route, confidence in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                got_route, got_conf = analyze(prompt)
                self.assertEqual(got_route, route)
                self.assertAlmostEqual(got_conf, confidence)

    def test_route_request_cli_without_host_unchanged(self):
        with patch.object(sys, "argv", ["route_request.py", "--prompt", "start a database migration"]), \
             patch.object(route_request, "load_cortex_capabilities", return_value={}), \
             patch.object(route_request, "check_credential_allowlist", return_value={"blocked": False}), \
             patch("builtins.print") as printed, self.assertRaises(SystemExit):
            route_request.main()
        self.assertIn('"route": "claude"', printed.call_args_list[0].args[0])


class WorkloadModel(unittest.TestCase):
    def test_migration_matches_aim_prompts(self):
        import workloads
        for prompt, *_ in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                self.assertIs(workloads.classify(prompt), workloads.MIGRATION)

    def test_migration_matches_case_and_windows_paths(self):
        import workloads
        for prompt in ("START A DATABASE MIGRATION", "Convert T-SQL in C:\\src\\procs",
                       "Resume the migration", "  /migrate continue"):
            with self.subTest(prompt=prompt):
                self.assertIs(workloads.classify(prompt), workloads.MIGRATION)

    def test_other_prompts_are_general(self):
        import workloads
        for prompt in NOT_MIGRATIONS:
            with self.subTest(prompt=prompt):
                self.assertIs(workloads.classify(prompt), workloads.GENERAL)

    def test_migration_needs_rw_and_resumes(self):
        import workloads
        self.assertEqual(workloads.MIGRATION.required_envelope, "RW")
        self.assertTrue(workloads.MIGRATION.multi_turn)
        self.assertIsNone(workloads.GENERAL.required_envelope)

    def test_only_devin_supports_workloads(self):
        self.assertTrue(hosts.DEVIN_CLI.supports_workloads)
        self.assertFalse(hosts.CLAUDE_CODE.supports_workloads)
        self.assertFalse(hosts.CODEX.supports_workloads)


class DevinMigrationRouting(unittest.TestCase):
    def test_every_migration_prompt_routes_with_migration_instruction(self):
        for prompt, *_ in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                got = run_filter({"hook_event_name": "UserPromptSubmit", "prompt": prompt}, env=DEVIN_ENV)
                self.assertIn("Snowflake AIM", got)

    def test_instruction_uses_rw_absolute_paths_and_devin_host(self):
        got = run_filter({"prompt": "start a database migration"}, env=DEVIN_ENV)
        self.assertIn(f'bash "{DEVIN_ROOT}/scripts/run_python.sh" "{DEVIN_ROOT}/scripts/router/execute_cortex.py"', got)
        self.assertIn('--envelope "RW" --host devin_cli', got)
        self.assertIn(f'"{DEVIN_ROOT}/scripts/router/route_request.py" --prompt "<USER_PROMPT>" --host devin_cli', got)
        self.assertNotIn("--codex", got)
        self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", got)

    def test_instruction_relays_questions_and_resumes(self):
        got = run_filter({"prompt": "continue my migration"}, env=DEVIN_ENV)
        self.assertIn("Relay", got)
        self.assertIn("Never answer for them", got)
        self.assertIn("--resume-last", got)
        self.assertIn("install", got)

    def test_general_devin_prompts_unchanged(self):
        got = run_filter({"prompt": "show me my snowflake tables"}, env=DEVIN_ENV)
        self.assertEqual(got, hosts.DEVIN_CLI.routing_instruction(DEVIN_ROOT))
        self.assertNotIn("Snowflake AIM", got)

    def test_mcp_conflict_still_stops_migrations(self):
        server = {"mcpServers": {"snowflake": {"command": "snowflake-labs-mcp"}}}
        got = run_filter({"prompt": "start a database migration"}, env=DEVIN_ENV,
                         files={".config/devin/mcp_config.json": server})
        self.assertTrue(got.startswith("STOP. A Snowflake MCP server 'snowflake'"), got)

    def test_local_keywords_still_win(self):
        self.assertEqual(run_filter({"prompt": "git status before I migrate Redshift"}, env=DEVIN_ENV), "")

    def test_route_request_with_devin_host_routes_migrations(self):
        for prompt, *_ in MIGRATION_PROMPTS:
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze(prompt, hosts.DEVIN_CLI), ("cortex", 1.0))

    def test_route_request_with_devin_host_general_unchanged(self):
        for prompt in NOT_MIGRATIONS:
            with self.subTest(prompt=prompt):
                self.assertEqual(analyze(prompt, hosts.DEVIN_CLI), analyze(prompt))

    def test_route_request_host_flag(self):
        with patch.object(sys, "argv", ["route_request.py", "--prompt", "start a database migration",
                                        "--host", "devin_cli"]), \
             patch.object(route_request, "load_cortex_capabilities", return_value={}), \
             patch.object(route_request, "check_credential_allowlist", return_value={"blocked": False}), \
             patch("builtins.print") as printed, self.assertRaises(SystemExit):
            route_request.main()
        self.assertIn('"route": "cortex"', printed.call_args_list[0].args[0])

    def test_credential_block_still_wins_for_migrations(self):
        with patch.object(sys, "argv", ["route_request.py", "--prompt", "migrate ~/.ssh/id_rsa to Snowflake",
                                        "--host", "devin_cli"]), \
             patch("builtins.print") as printed, self.assertRaises(SystemExit):
            route_request.main()
        self.assertIn('"route": "blocked"', printed.call_args_list[0].args[0])

    def test_policy_without_rw_stops_migrations_before_cortex(self):
        import execute_cortex
        import workloads

        class Policy:
            def get(self, key, default=None):
                return ["RO"] if key == "security.allowed_envelopes" else default

        error = execute_cortex._check_envelope_allowed(workloads.MIGRATION.required_envelope, Policy())
        self.assertIn("not in allowed_envelopes", error)
        got = run_filter({"prompt": "start a database migration"}, env=DEVIN_ENV)
        self.assertIn("If the command fails, STOP and report the error", got)


if __name__ == "__main__":
    unittest.main()
