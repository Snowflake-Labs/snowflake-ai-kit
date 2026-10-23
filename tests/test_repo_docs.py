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

    def test_agents_md_versions_are_current(self):
        versions = set(re.findall(r"\bv(\d+\.\d+\.\d+)\b", self.agents))
        self.assertEqual(versions, {self.version})

    def test_agents_md_testing_covers_docs_checks(self):
        self.assertIn("test_repo_docs.py", section(self.agents, "Testing"))

    def test_security_scope_covers_devin_plugin(self):
        scope = section(read(REPO_ROOT / "SECURITY.md"), "Scope")
        self.assertIn("Devin", scope)
        self.assertIn("${SNOWFLAKE_PAT}", scope)


if __name__ == "__main__":
    unittest.main()
