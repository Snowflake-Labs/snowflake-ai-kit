#!/usr/bin/env python3
"""Discover Cortex Code bundled skills and cache for the session.

Runs `cortex skill list`, reads each skill's metadata, and caches
the result to /tmp/cortex-capabilities.json.

Requires: Cortex Code CLI (cortex) installed and in PATH.
No external Python dependencies — stdlib only.

Inspired by: https://github.com/sfc-gh-tjia/claude_skill_cortexcode
"""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

CACHE_PATH = Path("/tmp/cortex-capabilities.json")


def discover_skills() -> dict:
    """Enumerate Cortex Code's bundled skills and return metadata.

    Returns:
        Dict mapping skill names to their descriptions and triggers.
        Empty dict if Cortex CLI is not available.
    """
    if not shutil.which("cortex"):
        print("cortex CLI not found — skipping discovery", file=sys.stderr)
        return {}

    # Get skill list
    try:
        result = subprocess.run(
            ["cortex", "skill", "list"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"cortex skill list failed: {result.stderr}", file=sys.stderr)
            return {}
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Failed to run cortex skill list: {e}", file=sys.stderr)
        return {}

    # Parse output — each line is a skill name or a table row
    skills = {}
    for line in result.stdout.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("-") or line.startswith("="):
            continue
        # Try to extract skill name (first column in table output)
        parts = line.split()
        if parts:
            name = parts[0].strip("|").strip()
            if name and not name.startswith("Name") and name.isidentifier() or "-" in name:
                skills[name] = {"name": name, "description": "", "triggers": []}

    # Try to read SKILL.md files from bundled skills directory
    bundled_dir = _find_bundled_skills_dir()
    if bundled_dir:
        for skill_name in list(skills.keys()):
            skill_md = bundled_dir / skill_name / "SKILL.md"
            if skill_md.exists():
                meta = _parse_frontmatter(skill_md)
                if meta.get("description"):
                    skills[skill_name]["description"] = meta["description"]
                    # Extract trigger words from description
                    trigger_match = re.search(r"Triggers?:\s*(.+?)\.?\s*$", meta["description"])
                    if trigger_match:
                        triggers = [t.strip() for t in trigger_match.group(1).split(",")]
                        skills[skill_name]["triggers"] = triggers

    return skills


def _find_bundled_skills_dir() -> Path | None:
    """Find the Cortex Code bundled skills directory."""
    # Common locations
    candidates = [
        Path.home() / ".local" / "share" / "cortex",
        Path.home() / ".snowflake" / "cortex",
    ]

    for base in candidates:
        if not base.exists():
            continue
        # Look for version directories with bundled_skills
        for child in sorted(base.iterdir(), reverse=True):
            bundled = child / "bundled_skills"
            if bundled.is_dir():
                return bundled

    return None


def _parse_frontmatter(path: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file (simple parser, no deps)."""
    meta = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return meta

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta

    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                meta[key] = value

    return meta


def main():
    print("Discovering Cortex Code capabilities...", file=sys.stderr)
    skills = discover_skills()

    if skills:
        # Cache for this session
        CACHE_PATH.write_text(json.dumps(skills, indent=2) + "\n")
        print(f"Cached {len(skills)} skills to {CACHE_PATH}", file=sys.stderr)
    else:
        print("No skills discovered (Cortex CLI may not be installed)", file=sys.stderr)

    # Output to stdout
    print(json.dumps(skills, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
