#!/usr/bin/env python3
"""Structural and docs-consistency checks for the Devin plugin and repo docs.

Pure Python, no network, no Snowflake connection. Run from anywhere:
    python3 tests/test_repo_docs.py -v
"""

import json
import re
import tempfile
import subprocess
import os
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEVIN_DIR = REPO_ROOT / "plugins" / "snowflake-mcp-devin"
CLIENT_ID = "Cognition_Devin"
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

    def test_user_agent_is_client_id(self):
        for manifest in (self.devin, self.claude):
            agent = manifest["mcpServers"]["snowflake"]["headers"]["User-Agent"]
            self.assertEqual(agent, CLIENT_ID)
        readme = read(DEVIN_DIR / "README.md")
        self.assertNotIn("Devin-Snowflake-MCP", readme)
        self.assertIn(f"User-Agent: {CLIENT_ID}", readme)

    def test_no_oauth_settings_in_manifests(self):
        # Devin rejects OAuth secrets in plugin files; OAuth is a custom MCP.
        for name in (".devin-plugin", ".claude-plugin"):
            text = read(DEVIN_DIR / name / "plugin.json")
            self.assertNotRegex(text, r"oauthClient(Id|Secret)|oauthScopes")


class CortexCodeDevinManifestTests(unittest.TestCase):
    """The Devin Marketplace reads plugins/cortex-code/.devin-plugin/plugin.json."""

    def setUp(self):
        self.devin = load_json(CORTEX_DIR / ".devin-plugin" / "plugin.json")

    def test_keeps_plugin_name_and_version(self):
        # Same name as the Claude manifest, so /snowflake-cortex-code:* commands and installs keep working.
        claude = load_json(CORTEX_DIR / ".claude-plugin" / "plugin.json")
        self.assertEqual(self.devin["name"], claude["name"])
        self.assertEqual(self.devin["version"], cortex_code_version())

    def test_has_marketplace_metadata(self):
        for key in ("displayName", "description", "shortDescription", "repository", "logo"):
            self.assertTrue(self.devin.get(key), f"missing {key}")
        self.assertLessEqual(len(self.devin["shortDescription"]), 40)
        self.assertFalse(self.devin["description"].endswith("."))
        self.assertTrue((CORTEX_DIR / self.devin["logo"]).is_file(), "logo file missing")

    def test_card_names_coco_cli_and_aim(self):
        self.assertEqual(self.devin["displayName"], "Snowflake Cortex Code (CoCo CLI + AIM)")
        self.assertIn("CoCo CLI + AIM", self.devin["shortDescription"])
        rule = section(read(REPO_ROOT / "AGENTS.md"), "Critical Rules")
        self.assertIn("**Snowflake Cortex Code (CoCo CLI + AIM)**", rule)

    def test_setup_explains_local_cli_and_aim(self):
        setup = self.devin["setup"]
        self.assertEqual(set(setup), {"notice", "steps"})
        self.assertIn("Cortex Code CLI", setup["notice"])
        steps = " ".join(setup["steps"])
        self.assertIn("/snowflake-cortex-code:cortex-setup", steps)
        self.assertIn("AIM", steps)

    def test_both_devin_plugins_use_the_official_snowflake_bug(self):
        # From snowflake.com/brand-guidelines: Snowflake Blue bug with the required ® mark.
        logos = [read(d / "logo.svg") for d in (CORTEX_DIR, DEVIN_DIR)]
        self.assertEqual(logos[0], logos[1], "Devin plugin logos differ")
        self.assertIn("#29b5e8", logos[0].lower())
        self.assertIn('viewBox="0 0 146.36 139.16"', logos[0])
        self.assertNotRegex(logos[0], r"<script|<image|xlink:href")

    def test_declares_skills_and_no_mcp_servers(self):
        self.assertEqual(self.devin.get("skills"), "./skills")
        self.assertNotIn("mcpServers", self.devin)


class DevinPluginContentTests(unittest.TestCase):
    def test_setup_uses_coding_agent_without_agent_object(self):
        readme = read(DEVIN_DIR / "README.md")
        self.assertIn("type: CODING_AGENT", readme)
        for stale in ("CREATE OR REPLACE AGENT", "CORTEX_AGENT_RUN", "GRANT USAGE ON AGENT",
                      "MCP has no way to pass an approval back",
                      "must create the agent", "the agent above uses"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, readme)
        agents = read(DEVIN_DIR / "AGENTS.md")
        self.assertIn("| `cortex_code_agent` | CODING_AGENT |", agents)

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
        for entry in ("snowflake-mcp-devin/", "actions/", "test_repo_docs.py"):
            self.assertIn(entry, arch)

    def test_cortex_code_version_consistent_everywhere(self):
        codex = load_json(CORTEX_DIR / ".codex-plugin" / "plugin.json")["version"]
        market = load_json(REPO_ROOT / ".claude-plugin" / "marketplace.json")
        entry = next(p for p in market["plugins"] if p["name"] == "snowflake-cortex-code")
        router = read(CORTEX_DIR / "skills" / "cortex-router" / "SKILL.md")
        self.assertEqual(codex, self.version)
        self.assertEqual(entry["version"], self.version)
        self.assertIn(f"version: {self.version}", router)
        run = read(CORTEX_DIR / "skills" / "cortex-run" / "SKILL.md")
        self.assertIn(f"version: {self.version}", run)

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

    def test_plugin_readme_explains_enterprise_setup(self):
        # Enterprise orgs disable CLI plugins by default, and `devin -p` waits on the org picker.
        install = section(self.plugin_readme, "Install")
        self.assertIn("Devin CLI plugins", install)
        self.assertIn("devin.org_id", install)
        self.assertIn("devin auth status", install)

    def test_root_readme_offers_both_devin_paths(self):
        devin = self.root_readme.split("### Devin", 1)[1].split("\n## ", 1)[0]
        self.assertIn("plugins/cortex-code", devin)
        self.assertIn("plugins/snowflake-mcp-devin", devin)
        self.assertIn("Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code", devin)

    def test_agents_md_lists_devin_manifest_for_cortex_code(self):
        # Devin reads .devin-plugin/plugin.json when present, not .claude-plugin.
        arch = section(read(REPO_ROOT / "AGENTS.md"), "Architecture")
        cortex = arch.split("snowflake-mcp-devin/", 1)[0]
        self.assertIn(".devin-plugin/plugin.json", cortex)
        self.assertNotIn("Devin CLI reads it too", arch)
        self.assertIn("plugins/cortex-code", section(read(REPO_ROOT / "AGENTS.md"), "Critical Rules"))

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


class IncludeAimDocsTests(unittest.TestCase):
    """--include-aim installs the Snowflake AIM plugin with Cortex Code, and cortex-setup uses it in Devin CLI."""

    AIM_SOURCE = "https://github.com/Snowflake-Labs/cortex-code-migrations/tree/main/plugin"

    def setUp(self):
        self.setup_skill = read(CORTEX_DIR / "skills" / "cortex-setup" / "SKILL.md")
        self.plugin = read(CORTEX_DIR / "README.md")
        self.root = read(REPO_ROOT / "README.md")

    def test_setup_fallback_uses_the_real_cortex_installers(self):
        self.assertNotIn("curl -fsSL https://docs.snowflake.com", self.setup_skill)
        self.assertIn("https://ai.snowflake.com/static/cc-scripts/install.sh", self.setup_skill)
        self.assertIn("https://ai.snowflake.com/static/cc-scripts/install.ps1", self.setup_skill)

    def test_setup_installs_aim_in_devin_cli(self):
        self.assertIn("--include-aim", self.setup_skill)
        self.assertIn("-IncludeAim", self.setup_skill)
        self.assertIn(f"cortex plugin install {self.AIM_SOURCE}", self.setup_skill)
        self.assertIn("snowflake-migration", self.setup_skill)
        self.assertIn("Devin CLI", self.setup_skill)
        # Headless Cortex sessions skip AIM's SessionStart hook, which installs scai.
        self.assertIn("hooks/install-dependencies.sh", self.setup_skill)
        self.assertIn("hooks\\install-dependencies.ps1", self.setup_skill)
        self.assertIn("scai --version", self.setup_skill)

    def test_root_readme_documents_flag(self):
        self.assertIn("`--include-aim` / `-IncludeAim`", self.root)

    def test_plugin_readme_explains_aim_preinstall(self):
        migrations = section(self.plugin, "Install").split("#### Database migrations (Snowflake AIM)", 1)[1]
        self.assertIn("--include-aim", migrations)
        self.assertIn(f"cortex plugin install {self.AIM_SOURCE}", migrations)

    def test_devin_quick_start_installs_cli_and_aim_before_plugin(self):
        devin = section(self.plugin, "Install").split("### Devin CLI", 1)[1].split("#### Database migrations", 1)[0]
        steps = ["bash install.sh --include-aim", ".\\install.ps1 -IncludeAim",
                 "devin plugins install Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code --local"]
        for step in steps:
            self.assertIn(step, devin)
        self.assertLess(devin.index(steps[0]), devin.index(steps[2]), "install the CLI and AIM before the plugin")

    def test_root_devin_bullet_runs_installer_first(self):
        devin = self.root.split("### Devin", 1)[1].split("\n## ", 1)[0]
        self.assertIn("--include-aim", devin)

    def test_root_devin_section_has_two_options_with_numbered_steps(self):
        devin = self.root.split("### Devin", 1)[1].split("\n### ", 1)[0]
        a = devin.index("**Option A")
        b = devin.index("**Option B")
        self.assertLess(a, b)
        opt_a, opt_b = devin[a:b], devin[b:]
        for text in ("1. ", "2. ", "3. ", "4. ", "bash install.sh --include-aim",
                     "devin plugins install --local ./plugins/cortex-code",
                     "plugins/cortex-code/README.md#devin-desktop"):
            with self.subTest(option="A", text=text):
                self.assertIn(text, opt_a)
        for text in ("1. ", "2. ", "Snowflake (Managed MCP)", "Server URL"):
            with self.subTest(option="B", text=text):
                self.assertIn(text, opt_b)
        intro = devin[:a]
        for text in ("| Database migrations (Snowflake AIM) | Yes", "| No |"):
            with self.subTest(table=text):
                self.assertIn(text, intro)
        for text in ("**With AIM**", "**Without AIM**", "bash install.sh                      # Windows: .\\install.ps1\n"):
            with self.subTest(option="A", text=text):
                self.assertIn(text, opt_a)
        self.assertIn("**No AIM.**", opt_b)


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

    def test_plugin_readme_covers_devin_migration_field_findings(self):
        migrations = section(self.plugin, "Install").split("#### Database migrations (Snowflake AIM)", 1)[1]
        for text in ("Devin Desktop", "mcp-server-state.json", "/mcp", "--model",
                     "git_main_branch", "columnMappings"):
            with self.subTest(text=text):
                self.assertIn(text, migrations)
        self.assertIn("Devin CLI or Devin Desktop, with the Cortex Code CLI", self.root)
        self.assertIn("Use this plugin in Devin CLI or Devin Desktop when", self.plugin)

    def test_devin_sections_have_get_started_steps(self):
        cli = self.plugin.split("### Devin CLI", 1)[1].split("\n#### ", 1)[0]
        desktop = self.plugin.split("#### Devin Desktop", 1)[1].split("\n#### ", 1)[0]
        for name, text in (("cli", cli), ("desktop", desktop)):
            for step in ("**Get started**", "https://cli.devin.ai/install.sh", "devin auth login",
                         "git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git",
                         "bash install.sh --include-aim", "snow connection add",
                         "devin plugins install --local ./plugins/cortex-code",
                         "devin plugins info snowflake-cortex-code", "start a database migration"):
                with self.subTest(section=name, step=step):
                    self.assertIn(step, text)

    def test_snowflake_mcp_devin_installs_from_devin_marketplace(self):
        listing = "Snowflake (Managed MCP)"
        root = section(self.root, "Quick Start")
        self.assertIn(listing, root)
        self.assertIn("Marketplace", root)
        mcp = read(REPO_ROOT / "plugins" / "snowflake-mcp-devin" / "README.md")
        install = mcp.split("### 1. Install the plugin", 1)[1].split("\n### ", 1)[0]
        self.assertIn(f"**From Devin's Marketplace (recommended).**", install)
        self.assertIn(listing, install)
        self.assertLess(install.index("Marketplace"), install.index("From the repository"))
        agents = read(REPO_ROOT / "AGENTS.md")
        for text in ("CognitionAI/devin-marketplace", "sha"):
            with self.subTest(text=text):
                self.assertIn(text, section(agents, "Critical Rules"))

    def test_aim_install_options_are_clear(self):
        migrations = self.plugin.split("#### Database migrations (Snowflake AIM)", 1)[1].split("\n#### ", 1)[0]
        for text in ("**Installing AIM.**", "AIM isn't installed by default",
                     "--include-aim", "/snowflake-cortex-code:cortex-setup", "start a database migration"):
            with self.subTest(text=text):
                self.assertIn(text, migrations)
        self.assertIn("installs the CLI, and in Devin also Snowflake AIM", self.plugin)
        installer = section(self.root, "Installer")
        for text in ("AIM isn't installed by default", "/snowflake-cortex-code:cortex-setup",
                     "plugins/cortex-code/README.md#database-migrations-snowflake-aim"):
            with self.subTest(text=text):
                self.assertIn(text, installer)

    def test_devin_desktop_users_can_get_the_devin_cli(self):
        self.assertIn("#### Devin Desktop", self.plugin)
        desktop = self.plugin.split("#### Devin Desktop", 1)[1].split("\n#### ", 1)[0]
        for text in ("Install Devin CLI", "https://cli.devin.ai/install.sh", "--include-aim",
                     "devin plugins install --local ./plugins/cortex-code", "/mcp", "#database-migrations-snowflake-aim"):
            with self.subTest(text=text):
                self.assertIn(text, desktop)
        self.assertIn("plugins/cortex-code/README.md#devin-desktop", section(self.root, "Quick Start"))

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


class DocsAccuracyTests(unittest.TestCase):
    """Facts every audience (Claude Code, Codex, Devin CLI/Desktop) relies on."""

    def test_intros_name_devin_desktop(self):
        for path in (REPO_ROOT / "README.md", CORTEX_DIR / "README.md"):
            with self.subTest(path=path.name):
                intro = read(path).split("\n## ", 1)[0]
                self.assertIn("Devin Desktop", intro)

    def test_installer_flag_table_is_contiguous(self):
        readme = read(REPO_ROOT / "README.md")
        table = re.search(r"\| Flag \| Description \|\n\|---\|---\|\n((?:\|.*\|\n)+)", readme).group(1)
        for flag in ("--check", "--with-claude", "--with-codex", "--include-aim", "--help"):
            self.assertIn(f"`{flag}`", table)

    def test_readme_bundled_skill_examples_exist(self):
        readme = read(REPO_ROOT / "README.md")
        for stale in ("`semantic-view`", "`cortex-agent`", "`cortex-ai-functions`"):
            self.assertNotIn(stale, readme)

    def test_agents_md_matches_repo(self):
        agents = read(REPO_ROOT / "AGENTS.md")
        self.assertNotIn("mcp-servers/", agents)
        self.assertNotIn("--update", agents)
        self.assertNotIn("75 unit tests", agents)
        installers = section(agents, "Installers")
        for flag in ("--with-codex", "--include-aim"):
            self.assertIn(flag, installers)

    def test_codex_mode_auto_approve_is_stated(self):
        self.assertIn("auto-approve", section(read(REPO_ROOT / "SECURITY.md"), "Scope"))
        run = read(CORTEX_DIR / "skills" / "cortex-run" / "SKILL.md")
        self.assertIn("--codex", run)

    def test_cli_reference_documents_resume(self):
        ref = read(CORTEX_DIR / "skills" / "cortex-router" / "references" / "cortex-cli-reference.md")
        self.assertNotIn("No `--resume`", ref)

    def test_cortex_setup_steps_numbered_and_cover_desktop(self):
        setup = read(CORTEX_DIR / "skills" / "cortex-setup" / "SKILL.md")
        self.assertNotIn("Step 3a", setup)
        self.assertIn("Devin Desktop", setup)

    def test_manifest_descriptions_are_current(self):
        codex = load_json(CORTEX_DIR / ".codex-plugin" / "plugin.json")
        self.assertIn("55+", codex["interface"]["longDescription"])
        market = read(REPO_ROOT / ".claude-plugin" / "marketplace.json")
        self.assertNotIn("code-review", market)
        self.assertNotIn("reviews and task delegation", market)

    def test_mcp_devin_readme_warns_against_both_devin_plugins(self):
        readme = read(DEVIN_DIR / "README.md")
        self.assertIn("snowflake-cortex-code", readme)
        self.assertIn("Cortex Code (CoCo)", readme)

    def test_dcm_docs_use_dcm_project_commands(self):
        for path in (DEVIN_DIR / "skills" / "snowflake-dcm" / "SKILL.md", DEVIN_DIR / "AGENTS.md"):
            with self.subTest(path=path.name):
                text = read(path)
                dcm = text if path.name == "SKILL.md" else text.split("## DCM", 1)[1].split("\n## ", 1)[0]
                self.assertIn("EXECUTE DCM PROJECT", dcm)
                self.assertNotIn("DBT PROJECT", dcm)
                self.assertNotIn("snow dcm execute", dcm)

    def test_semantic_view_skill_uses_valid_ddl(self):
        text = read(DEVIN_DIR / "skills" / "snowflake-semantic-views" / "SKILL.md")
        self.assertIn("SYSTEM$CREATE_SEMANTIC_VIEW_FROM_YAML", text)
        self.assertNotRegex(text, r"SEMANTIC VIEW \S+ AS \$\$")
        self.assertIn("relationship_type: many_to_one", text)
        self.assertNotIn("join_type: many_to_one", text)


class ReleaseHygieneTests(unittest.TestCase):
    """Facts that keep a release consistent for every agent."""

    def test_no_unreferenced_version_file(self):
        # VERSION was never read by anything and drifted from the plugin version.
        self.assertFalse((REPO_ROOT / "VERSION").exists())

    def test_docs_do_not_offer_unpublished_npx_package(self):
        # @snowflake-labs/ai-kit isn't on npm, so `npx @snowflake-labs/ai-kit` fails.
        for path in (REPO_ROOT / "README.md", REPO_ROOT / "AGENTS.md",
                     CORTEX_DIR / "skills" / "cortex-setup" / "SKILL.md"):
            with self.subTest(path=path.name):
                text = read(path)
                self.assertNotIn("npx @snowflake-labs/ai-kit", text)
                self.assertNotIn("or npx method", text)


class CortexSetupConflictCheckTests(unittest.TestCase):
    """cortex-setup's MCP conflict check is the hook's check, for every agent."""

    def setUp(self):
        skill = read(CORTEX_DIR / "skills" / "cortex-setup" / "SKILL.md")
        # The local-mode prerequisite (remote mode skips it).
        prereq = re.split(r"## (?:Local p|P)rerequisite", skill, maxsplit=1)[1]
        self.snippet = re.search(r"```bash\n(.*?)```", prereq, re.S).group(1)

    def run_check(self, home: Path, host: str):
        # The agent fills in <host>; its shell supplies CLAUDE_PLUGIN_ROOT (in Devin, the agent pastes the path).
        script = self.snippet.replace("<host>", host)
        env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home), "CLAUDE_PLUGIN_ROOT": str(CORTEX_DIR)}
        return subprocess.run(["bash", "-c", script], cwd=home, env=env,
                              capture_output=True, text=True, timeout=60)

    def test_uses_the_hook_check(self):
        self.assertIn("find_snowflake_mcp_server", self.snippet)
        self.assertNotIn("cat ~/.claude/settings.json", self.snippet)

    def test_finds_user_scope_server_in_claude_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude.json").write_text(json.dumps(
                {"mcpServers": {"snowflake": {"command": "uvx", "args": ["snowflake-labs-mcp"]}}}))
            result = self.run_check(home, "claude_code")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("CONFLICT: snowflake", result.stdout)

    def test_finds_devin_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            cfg = home / ".config" / "devin"
            cfg.mkdir(parents=True)
            (cfg / "mcp_config.json").write_text(json.dumps(
                {"mcpServers": {"sf": {"url": "https://acct.snowflakecomputing.com/api/v2/x/mcp-servers/y"}}}))
            result = self.run_check(home, "devin_cli")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_passes_when_no_server(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_check(Path(tmp), "codex")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK", result.stdout)


class RemoteBackendDocsTests(unittest.TestCase):
    """Remote mode is set up with a CODING_AGENT tool, like the Managed MCP plugin."""

    def test_remote_setup_uses_coding_agent_without_agent_object(self):
        guide = read(CORTEX_DIR / "REMOTE_MCP.md")
        self.assertIn("type: CODING_AGENT", guide)
        for stale in ("identifier: EXAMPLE_DB", "GRANT USAGE ON AGENT", "DESCRIBE AGENT",
                      "type: CORTEX_AGENT_RUN"):
            with self.subTest(stale=stale):
                self.assertNotIn(stale, guide)
        self.assertIn("`CORTEX_AGENT_RUN` also works", guide)

    def test_remote_workflow_and_helper_name_coding_agent(self):
        workflow = read(CORTEX_DIR / "skills" / "cortex-router" / "references" / "remote-mcp.md")
        self.assertIn("CODING_AGENT", workflow)
        self.assertIn("CODING_AGENT", read(CORTEX_DIR / "scripts" / "router" / "backend.py"))

    def test_agents_md_lists_remote_backend_files(self):
        arch = section(read(REPO_ROOT / "AGENTS.md"), "Architecture")
        for entry in ("REMOTE_MCP.md", "backend.py", "test_remote_backend.py", "remote-mcp.md"):
            with self.subTest(entry=entry):
                self.assertIn(entry, arch)

    def test_remote_workflow_follows_the_helper_thread_arguments(self):
        workflow = read(CORTEX_DIR / "skills" / "cortex-router" / "references" / "remote-mcp.md")
        self.assertIn("thread_arguments", workflow)
        self.assertIn("message_id", workflow)
        self.assertNotIn("positive integer `thread_id`", workflow)
        self.assertNotIn("Omit `parent_message_id` for ordinary continuation", workflow)
        self.assertNotIn("cannot send the REST", workflow)

    def test_remote_guide_covers_devin_and_migrations(self):
        guide = read(CORTEX_DIR / "REMOTE_MCP.md")
        self.assertIn("Devin", guide)
        self.assertIn("CORTEX_PLUGIN_BACKEND=local", guide)


if __name__ == "__main__":
    unittest.main()
