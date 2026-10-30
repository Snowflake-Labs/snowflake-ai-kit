#!/usr/bin/env python3
"""Structural and docs-consistency checks for the Devin plugin and repo docs.

Pure Python, no network, no Snowflake connection. Run from anywhere:
    python3 tests/test_repo_docs.py -v
"""

import json
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVIN_DIR = REPO_ROOT / "plugins" / "snowflake-mcp-devin"
CORTEX_DIR = REPO_ROOT / "plugins" / "cortex-code"

DEVIN_SKILLS = {
    "snowflake-query",
    "snowflake-explore",
    "snowflake-cortex",
    "snowflake-pipelines",
    "snowflake-governance",
    "snowflake-semantic-views",
    "snowflake-dcm",
}

# Values from test accounts that must never ship in the plugin.
ACCOUNT_SPECIFIC = re.compile(
    r"DASH_DB|DASH_SCHEMA|DEVIN_MCP_ROLE|COCO_MCP_SERVER|COCO_CLOUD_AGENT|"
    r"gen[_-]ai[_-]hol|sfsenorthamerica|sfsehol|iamontheinet|sfc-gh-",
    re.IGNORECASE,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def cortex_code_version() -> str:
    return load_json(CORTEX_DIR / ".claude-plugin" / "plugin.json")["version"]


def section(markdown: str, heading: str) -> str:
    """Return the body of a '## heading' section, up to the next '## '."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", markdown, re.M | re.S)
    return match.group(1) if match else ""


class DevinPluginManifestTests(unittest.TestCase):
    def setUp(self):
        self.devin = load_json(DEVIN_DIR / ".devin-plugin" / "plugin.json")
        self.claude = load_json(DEVIN_DIR / ".claude-plugin" / "plugin.json")

    def test_manifests_share_name_and_version(self):
        self.assertEqual(self.devin["name"], self.claude["name"])
        self.assertEqual(self.devin["version"], self.claude["version"])

    def test_devin_manifest_has_marketplace_metadata(self):
        for key in ("name", "displayName", "description", "repository", "logo"):
            self.assertTrue(self.devin.get(key), f"missing {key}")
        self.assertTrue((DEVIN_DIR / self.devin["logo"]).is_file(), "logo file missing")

    def test_mcp_server_uses_only_placeholders(self):
        for manifest in (self.devin, self.claude):
            server = manifest["mcpServers"]["snowflake"]
            self.assertEqual(server["url"], "${SNOWFLAKE_MCP_URL}")
            self.assertEqual(server["headers"]["Authorization"], "Bearer ${SNOWFLAKE_PAT}")

    def test_user_agent_tracks_plugin_version(self):
        version = self.devin["version"]
        for manifest in (self.devin, self.claude):
            agent = manifest["mcpServers"]["snowflake"]["headers"]["User-Agent"]
            self.assertRegex(agent, r"^Devin-Snowflake-MCP/\d+(\.\d+)*$")
            self.assertTrue(version.startswith(agent.split("/", 1)[1]),
                            f"User-Agent {agent} does not match version {version}")

    def test_no_oauth_settings_in_manifests(self):
        # Devin rejects OAuth secrets in plugin files; OAuth is a custom MCP.
        for name in (".devin-plugin", ".claude-plugin"):
            text = read(DEVIN_DIR / name / "plugin.json")
            self.assertNotRegex(text, r"oauthClient(Id|Secret)|oauthScopes")


class DevinPluginContentTests(unittest.TestCase):
    def test_expected_skills_present_with_matching_names(self):
        found = {p.parent.name for p in (DEVIN_DIR / "skills").glob("*/SKILL.md")}
        self.assertEqual(found, DEVIN_SKILLS)
        for skill in DEVIN_SKILLS:
            text = read(DEVIN_DIR / "skills" / skill / "SKILL.md")
            self.assertRegex(text, rf"(?m)^name: {re.escape(skill)}$")
            self.assertRegex(text, r"(?m)^description:")

    def test_readme_documents_every_skill_command(self):
        readme = read(DEVIN_DIR / "README.md")
        for skill in DEVIN_SKILLS:
            self.assertIn(f"/snowflake:{skill}", readme)

    def test_no_account_specific_values(self):
        for path in DEVIN_DIR.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json", ".svg"}:
                hit = ACCOUNT_SPECIFIC.search(read(path))
                self.assertIsNone(hit, f"{path.relative_to(REPO_ROOT)}: {hit and hit.group(0)}")

    def test_troubleshooting_covers_server_url_validation(self):
        table = section(read(DEVIN_DIR / "README.md"), "Troubleshooting")
        row = next((l for l in table.splitlines() if "Only letters, numbers" in l), "")
        self.assertIn("SNOWFLAKE_MCP_URL", row)
        self.assertIn("Secret", row)

    def test_query_skill_names_default_tool(self):
        text = read(DEVIN_DIR / "skills" / "snowflake-query" / "SKILL.md")
        self.assertIn("cortex_code_agent", text)


class RepoDocsTests(unittest.TestCase):
    def setUp(self):
        self.readme = read(REPO_ROOT / "README.md")
        self.agents = read(REPO_ROOT / "AGENTS.md")
        self.version = cortex_code_version()

    def test_readme_badge_matches_cortex_code_version(self):
        self.assertIn(f"badge/Plugin-v{self.version}-", self.readme)

    def test_readme_intro_mentions_devin(self):
        intro = self.readme.split("\n## ", 1)[0]
        self.assertIn("Devin", intro)

    def test_agents_md_describes_all_plugins(self):
        about = section(self.agents, "What This Repo Is")
        for word in ("Claude Code", "Codex", "Devin"):
            self.assertIn(word, about)

    def test_agents_md_architecture_lists_repo_layout(self):
        arch = section(self.agents, "Architecture")
        for entry in ("snowflake-mcp-devin/", "actions/", "mcp-servers/", "test_repo_docs.py"):
            self.assertIn(entry, arch)

    def test_cortex_code_version_consistent_everywhere(self):
        codex = load_json(CORTEX_DIR / ".codex-plugin" / "plugin.json")["version"]
        market = load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
        entry = next(p for p in market["plugins"] if p["name"] == "snowflake-cortex-code")
        router = read(CORTEX_DIR / "skills" / "cortex-router" / "SKILL.md")
        self.assertEqual(codex, self.version)
        self.assertEqual(entry["version"], self.version)
        self.assertIn(f"version: {self.version}", router)

    def test_codeowners_names_at_least_two_owners(self):
        path = REPO_ROOT / ".github" / "CODEOWNERS"
        self.assertTrue(path.is_file(), ".github/CODEOWNERS is missing")
        rule = next((l for l in read(path).splitlines() if l.startswith("* ")), "")
        owners = re.findall(r"@[\w-]+", rule)
        self.assertGreaterEqual(len(set(owners)), 2, "mythos-codeowners needs 2 users")

    def test_agents_md_versions_are_current(self):
        versions = set(re.findall(r"\bv(\d+\.\d+\.\d+)\b", self.agents))
        self.assertEqual(versions, {self.version})

    def test_agents_md_testing_covers_docs_checks(self):
        self.assertIn("test_repo_docs.py", section(self.agents, "Testing"))

    def test_security_scope_covers_devin_plugin(self):
        scope = section(read(REPO_ROOT / "SECURITY.md"), "Scope")
        self.assertIn("Devin", scope)
        self.assertIn("${SNOWFLAKE_PAT}", scope)


class CortexCodeDevinCliDocsTests(unittest.TestCase):
    """The Cortex Code plugin also runs in Devin CLI, routing to the local cortex CLI."""

    def setUp(self):
        self.plugin_readme = read(CORTEX_DIR / "README.md")
        self.root_readme = read(REPO_ROOT / "README.md")

    def test_plugin_readme_installs_in_devin_cli(self):
        install = section(self.plugin_readme, "Install")
        self.assertIn("### Devin CLI", install)
        self.assertIn("devin plugins install Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code --local", install)
        self.assertIn("/snowflake-cortex-code:cortex-run", self.plugin_readme)

    def test_plugin_readme_explains_choice_between_devin_plugins(self):
        install = section(self.plugin_readme, "Install")
        self.assertIn("snowflake-mcp-devin", install)

    def test_plugin_readme_explains_imported_mcp_conflicts(self):
        install = section(self.plugin_readme, "Install")
        self.assertIn("read_config_from", install)
        self.assertIn("devin mcp list", install)

    def test_root_readme_offers_both_devin_paths(self):
        devin = self.root_readme.split("### Devin", 1)[1].split("\n## ", 1)[0]
        self.assertIn("plugins/cortex-code", devin)
        self.assertIn("plugins/snowflake-mcp-devin", devin)
        self.assertIn("Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code", devin)

    def test_claude_manifest_read_by_devin_names_it(self):
        # Devin CLI falls back to .claude-plugin/plugin.json and shows its description.
        description = load_json(CORTEX_DIR / ".claude-plugin" / "plugin.json")["description"]
        self.assertIn("Devin CLI", description)

    def test_agents_md_covers_devin_cli_hosting(self):
        agents = read(REPO_ROOT / "AGENTS.md")
        self.assertIn("Devin CLI", section(agents, "What This Repo Is"))
        arch = section(agents, "Architecture")
        for entry in ("hosts.py", "test_hosts.py", "test_devin_e2e.py"):
            self.assertIn(entry, arch)
        testing = section(agents, "Testing")
        self.assertIn("test_hosts.py", testing)
        self.assertIn("--devin-e2e", testing)

    def test_security_scope_covers_devin_cli_routing(self):
        scope = section(read(REPO_ROOT / "SECURITY.md"), "Scope")
        self.assertIn("Devin CLI", scope)


class DevinCliMigrationDocsTests(unittest.TestCase):
    """Devin CLI routes database migrations to Snowflake AIM in Cortex Code."""

    def setUp(self):
        self.plugin = read(CORTEX_DIR / "README.md")
        self.root = read(REPO_ROOT / "README.md")
        self.agents = read(REPO_ROOT / "AGENTS.md")

    def test_plugin_readme_has_devin_migration_section(self):
        install = section(self.plugin, "Install")
        self.assertIn("#### Database migrations (Snowflake AIM)", install)
        migrations = install.split("#### Database migrations (Snowflake AIM)", 1)[1]
        for text in ("start a database migration", "continue my migration", "/migrate",
                     "RW", "--resume-last", "install", "Claude Code and Codex",
                     "https://docs.snowflake.com/en/migrations/aim-for-datawarehouses/overview"):
            self.assertIn(text, migrations)

    def test_root_troubleshooting_covers_devin_migrations(self):
        trouble = section(self.root, "Troubleshooting")
        self.assertIn("Snowflake AIM", trouble)

    def test_agents_md_covers_workloads(self):
        self.assertIn("workloads.py", section(self.agents, "Architecture"))
        self.assertIn("test_workloads.py", section(self.agents, "Architecture"))
        self.assertIn("workloads.py", section(self.agents, "Plugin Scripts"))
        self.assertIn("test_workloads.py", section(self.agents, "Testing"))

    def test_runners_run_workload_tests(self):
        for runner in ("run-tests.sh", "run-tests.ps1"):
            with self.subTest(runner=runner):
                self.assertIn("test_workloads.py", read(REPO_ROOT / "tests" / runner))


class ReadmeAccuracyTests(unittest.TestCase):
    """Root and Cortex Code READMEs stay accurate across Claude Code, Codex, and Devin CLI."""

    def setUp(self):
        self.root = read(REPO_ROOT / "README.md")
        self.plugin = read(CORTEX_DIR / "README.md")

    def test_root_intro_describes_one_plugin_for_three_agents(self):
        intro = self.root.split("\n## ", 1)[0]
        self.assertIn("One plugin", intro)
        self.assertNotIn("Plugins for", intro)

    def test_root_quick_start_ends_with_usage(self):
        quick = section(self.root, "Quick Start")
        headings = re.findall(r"^### (.+)$", quick, re.M)
        self.assertEqual(headings[-1], "That's it", headings)
        self.assertIn("Devin", headings)

    def test_root_devin_options_are_unambiguous(self):
        self.assertNotIn("no local CLI", self.root)

    def test_root_prerequisites_match_plugin_requirements(self):
        prereq = section(self.root, "Prerequisites")
        self.assertIn("Python 3.9", prereq)
        self.assertIn("Git Bash", prereq)

    def test_mcp_plugin_removal_uses_its_installed_name(self):
        name = load_json(DEVIN_DIR / ".devin-plugin" / "plugin.json")["name"]
        self.assertIn(f"devin plugins remove {name}`", self.plugin)
        self.assertIn(f"installed as `{name}`", self.plugin)

    def test_root_how_it_works_shows_devin_command(self):
        self.assertIn("/snowflake-cortex-code:cortex-run", section(self.root, "How It Works"))

    def test_root_troubleshooting_covers_devin(self):
        trouble = section(self.root, "Troubleshooting")
        for text in ("devin plugins list", "devin mcp list", "read_config_from", "os error 1314"):
            self.assertIn(text, trouble)

    def test_root_contributing_has_no_stale_test_count(self):
        contributing = section(self.root, "Contributing")
        self.assertNotRegex(contributing, r"\(\d+ tests\)")
        self.assertIn("--integration", contributing)
        self.assertIn("--devin-e2e", contributing)

    def test_python_requirement_matches_tested_minimum(self):
        # Python 3.8 fails to import execute_cortex.py; 3.9 runs the full suite.
        self.assertIn("badge/Python-3.9%2B-", self.root)
        self.assertIn("Python 3.9", section(self.plugin, "Requirements"))

    def test_plugin_how_it_works_covers_every_host(self):
        how = section(self.plugin, "How It Works")
        for host in ("Claude Code", "Codex", "Devin CLI"):
            self.assertIn(host, how)

    def test_plugin_requirements_cover_windows(self):
        self.assertIn("Git Bash", section(self.plugin, "Requirements"))

    def test_plugin_devin_section_covers_windows_install_error(self):
        install = section(self.plugin, "Install")
        self.assertIn("os error 1314", install)
        self.assertIn("Developer Mode", install)

    def test_plugin_testing_covers_new_suites(self):
        testing = section(self.plugin, "Testing")
        self.assertIn("test_hosts.py", testing)
        self.assertIn("--devin-e2e", testing)


if __name__ == "__main__":
    unittest.main()
