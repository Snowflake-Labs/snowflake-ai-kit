#!/usr/bin/env python3
"""Opt-in end-to-end test: Devin CLI routes Snowflake prompts to the local Cortex Code CLI.

Installs a temporary copy of plugins/cortex-code into Devin CLI, sends real prompts with
`devin -p`, and checks the plugin's audit log for envelope-enforced Cortex sessions.
Requires the devin and cortex CLIs and a working Cortex Code connection. Runs real,
read-only Snowflake queries. Removes the plugin afterwards.

Run: DEVIN_E2E=1 python3 tests/test_devin_e2e.py -v   (or tests/run-tests.sh --devin-e2e)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugins" / "cortex-code"
PLUGIN_NAME = "snowflake-cortex-code"
AUDIT_LOG = Path.home() / ".claude" / "skills" / "cortex-code" / "audit.log"
TIMEOUT = 600


def devin(*args, cwd=None, timeout=120):
    # Devin waits on an open stdin, so close it.
    return subprocess.run(["devin", *args], cwd=cwd, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, timeout=timeout)


def audit_entries_after(offset):
    if not AUDIT_LOG.exists():
        return []
    with AUDIT_LOG.open(encoding="utf-8") as f:
        f.seek(offset)
        return [json.loads(line) for line in f if line.strip()]


def audit_size():
    return AUDIT_LOG.stat().st_size if AUDIT_LOG.exists() else 0


def skip_reason():
    if os.environ.get("DEVIN_E2E") != "1":
        return "set DEVIN_E2E=1 to run (installs a plugin into Devin CLI, queries Snowflake)"
    for cli in ("devin", "cortex"):
        if not shutil.which(cli):
            return f"{cli} CLI not found"
    listed = devin("plugins", "list").stdout
    if PLUGIN_NAME in listed:
        return f"{PLUGIN_NAME} is already installed in Devin CLI; not overwriting it"
    # The hook rightly refuses to route while a Snowflake MCP server is active for Devin.
    sys.path.insert(0, str(PLUGIN_DIR / "scripts" / "router"))
    import hosts
    found = hosts.find_snowflake_mcp_server(hosts.DEVIN_CLI, Path.home(), Path.cwd(), os.environ)
    if found:
        return f"Snowflake MCP server '{found[0]}' is active for Devin in {found[1]}; disable it first"
    return None


@unittest.skipIf(skip_reason(), skip_reason() or "")
class DevinCliRoutesToCortexCode(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="devin_e2e_"))
        cls.project = cls.tmp / "project"
        cls.project.mkdir()
        plugin_copy = cls.tmp / "cortex-code"
        shutil.copytree(PLUGIN_DIR, plugin_copy, ignore=shutil.ignore_patterns("__pycache__"))
        installed = devin("plugins", "install", "--local", str(plugin_copy), "-y", cwd=cls.project)
        if installed.returncode != 0:
            shutil.rmtree(cls.tmp, ignore_errors=True)
            raise RuntimeError(f"devin plugins install failed: {installed.stdout}{installed.stderr}")

    @classmethod
    def tearDownClass(cls):
        devin("plugins", "remove", PLUGIN_NAME, "-y", cwd=cls.project)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def run_prompt(self, prompt):
        offset = audit_size()
        result = devin("-p", prompt, "--permission-mode", "dangerous",
                       "--respect-workspace-trust", "false", cwd=self.project, timeout=TIMEOUT)
        return result, audit_entries_after(offset)

    def assert_enforced_session(self, result, entries):
        detail = f"\nstdout:\n{result.stdout[-2000:]}\nstderr:\n{result.stderr[-1000:]}"
        self.assertEqual(result.returncode, 0, detail)
        decisions = [e for e in entries if e.get("event_type") == "permission_decision"]
        completes = [e for e in entries if e.get("event_type") == "session_complete"]
        self.assertTrue(decisions, "no envelope permission decisions in audit log" + detail)
        self.assertTrue(completes, "no completed Cortex session in audit log" + detail)
        return decisions

    def test_auto_routed_read_only_query(self):
        result, entries = self.run_prompt(
            "Using Snowflake, run SELECT CURRENT_VERSION() and tell me the result")
        decisions = self.assert_enforced_session(result, entries)
        self.assertTrue(any((d.get("routing") or {}).get("envelope") == "RO" for d in decisions),
                        f"expected the read-only envelope: {decisions}")

    def test_explicit_command(self):
        result, entries = self.run_prompt(
            "/snowflake-cortex-code:cortex-run show my current Snowflake role")
        self.assert_enforced_session(result, entries)


if __name__ == "__main__":
    unittest.main()
