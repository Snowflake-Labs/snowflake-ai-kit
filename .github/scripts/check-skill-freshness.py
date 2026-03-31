#!/usr/bin/env python3
"""Skill Freshness Checker for snowflake-ai-kit.

Detects when upstream Snowflake documentation has changed for skills
tracked in docs-manifest.yml. Designed to run as a GitHub Actions
scheduled workflow or locally.

Usage:
    python check-skill-freshness.py [--local]

Flags:
    --local   Print report only; skip GitHub Actions output variables.
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "snowflake-skills" / "docs-manifest.yml"
HASHES_PATH = REPO_ROOT / "snowflake-skills" / ".doc-hashes.json"
DOCS_BASE_URL = "https://docs.snowflake.com"
RELEASE_NOTES_PATH = "/en/release-notes/new-features.md"
REQUEST_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # seconds (doubles each retry)


def load_manifest() -> dict:
    """Load the docs-manifest.yml skill mapping."""
    with open(MANIFEST_PATH) as f:
        return yaml.safe_load(f)


def load_hashes() -> dict:
    """Load stored content hashes, or return empty state."""
    if HASHES_PATH.exists():
        with open(HASHES_PATH) as f:
            return json.load(f)
    return {"last_checked": None, "hashes": {}}


def save_hashes(state: dict) -> None:
    """Persist updated content hashes."""
    state["last_checked"] = datetime.now(timezone.utc).isoformat()
    with open(HASHES_PATH, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def fetch_page(path: str) -> str | None:
    """Fetch a doc page with retries. Returns content or None on failure."""
    url = f"{DOCS_BASE_URL}{path}"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 404:
                print(f"  WARN: {url} returned 404")
                return None
            # Transient error — retry
            print(f"  WARN: {url} returned {resp.status_code} (attempt {attempt}/{MAX_RETRIES})")
        except requests.RequestException as e:
            print(f"  WARN: Failed to fetch {url}: {e} (attempt {attempt}/{MAX_RETRIES})")
        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * attempt)
    print(f"  ERROR: Giving up on {url} after {MAX_RETRIES} attempts")
    return None


def content_hash(text: str) -> str:
    """SHA-256 hex digest of content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_doc_changes(manifest: dict, state: dict) -> list[dict]:
    """Compare current doc hashes against stored state.

    Returns a list of changed-doc entries:
        [{"skill": ..., "path": ..., "status": "changed"|"new"|"removed", "diff_hint": ...}]
    """
    stored = state.get("hashes", {})
    content_cache = state.get("content_cache", {})
    changes = []
    seen_paths = set()

    for skill, config in manifest.items():
        for doc_path in config.get("docs", []):
            seen_paths.add(doc_path)
            print(f"  Fetching {doc_path} ...")
            page = fetch_page(doc_path)
            if page is None:
                # Could not fetch — skip but don't mark as changed
                continue

            new_hash = content_hash(page)
            old_hash = stored.get(doc_path)

            if old_hash is None:
                changes.append({
                    "skill": skill,
                    "path": doc_path,
                    "status": "new",
                })
            elif new_hash != old_hash:
                diff_hint = _diff_hint(content_cache.get(doc_path, ""), page)
                changes.append({
                    "skill": skill,
                    "path": doc_path,
                    "status": "changed",
                    "diff_hint": diff_hint,
                })

            # Update hash and cache a trimmed snapshot for future diffs
            stored[doc_path] = new_hash
            content_cache[doc_path] = page[:5000]

    state["hashes"] = stored
    state["content_cache"] = content_cache
    return changes


def _diff_hint(old_text: str, new_text: str, max_lines: int = 5) -> str:
    """Return a short hint showing the first few changed lines."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    diffs = []
    for i, (o, n) in enumerate(zip(old_lines, new_lines)):
        if o != n:
            diffs.append(f"  L{i+1}: -{o[:80]}")
            diffs.append(f"  L{i+1}: +{n[:80]}")
            if len(diffs) >= max_lines * 2:
                break
    # Check for length difference
    if len(new_lines) > len(old_lines):
        diffs.append(f"  (+{len(new_lines) - len(old_lines)} new lines)")
    elif len(old_lines) > len(new_lines):
        diffs.append(f"  (-{len(old_lines) - len(new_lines)} removed lines)")
    return "\n".join(diffs[:12]) if diffs else "(content changed but diff unavailable)"


def check_release_notes(manifest: dict) -> list[dict]:
    """Scan recent release notes for skill keywords.

    Returns a list of keyword-hit entries:
        [{"skill": ..., "keyword": ..., "context": ...}]
    """
    print(f"\n  Fetching release notes ...")
    page = fetch_page(RELEASE_NOTES_PATH)
    if page is None:
        print("  WARN: Could not fetch release notes, skipping keyword scan.")
        return []

    hits = []
    for skill, config in manifest.items():
        for keyword in config.get("keywords", []):
            # Case-insensitive search
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            for match in pattern.finditer(page):
                # Extract surrounding context (up to 120 chars)
                start = max(0, match.start() - 60)
                end = min(len(page), match.end() + 60)
                context = page[start:end].replace("\n", " ").strip()
                hits.append({
                    "skill": skill,
                    "keyword": keyword,
                    "context": f"...{context}...",
                })
                break  # One hit per keyword per skill is enough

    return hits


def set_github_output(key: str, value: str) -> None:
    """Set a GitHub Actions output variable."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{key}={value}\n")


def build_issue_body(doc_changes: list, rn_hits: list, last_checked: str | None) -> str:
    """Build a markdown issue body from results."""
    lines = []
    lines.append("## Skill Freshness Report\n")
    lines.append(f"**Checked:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if last_checked:
        lines.append(f"**Previous check:** {last_checked}")
    lines.append("")

    if doc_changes:
        lines.append("### Documentation Changes\n")
        lines.append("| Skill | Doc Page | Status |")
        lines.append("|-------|----------|--------|")
        for c in doc_changes:
            lines.append(f"| `{c['skill']}` | `{c['path']}` | {c['status']} |")
        lines.append("")
        # Include diff hints for changed docs
        hints = [c for c in doc_changes if c.get("diff_hint")]
        if hints:
            lines.append("<details><summary>Diff hints</summary>\n")
            for c in hints:
                lines.append(f"**`{c['skill']}`** — `{c['path']}`\n```diff")
                lines.append(c["diff_hint"])
                lines.append("```\n")
            lines.append("</details>\n")

    if rn_hits:
        lines.append("### Release Note Keyword Hits\n")
        lines.append("| Skill | Keyword | Context |")
        lines.append("|-------|---------|---------|")
        for h in rn_hits:
            ctx = h["context"][:100]
            lines.append(f"| `{h['skill']}` | `{h['keyword']}` | {ctx} |")
        lines.append("")

    if not doc_changes and not rn_hits:
        lines.append("All skills are up to date. No documentation changes detected.\n")

    lines.append("---")
    lines.append("*Generated by `check-skill-freshness.py`*")
    return "\n".join(lines)


def main() -> None:
    local_mode = "--local" in sys.argv

    print("=" * 60)
    print("Skill Freshness Checker")
    print("=" * 60)

    # Load inputs
    manifest = load_manifest()
    state = load_hashes()
    last_checked = state.get("last_checked")
    print(f"\nLoaded {len(manifest)} skills from manifest")
    print(f"Previous check: {last_checked or 'never'}\n")

    # Phase 1: Doc changes
    print("Phase 1: Checking documentation pages...")
    doc_changes = check_doc_changes(manifest, state)

    # Phase 2: Release notes
    print("\nPhase 2: Scanning release notes for keywords...")
    rn_hits = check_release_notes(manifest)

    # Deduplicate release note hits (keep first per skill+keyword)
    seen_rn = set()
    unique_rn_hits = []
    for h in rn_hits:
        key = (h["skill"], h["keyword"])
        if key not in seen_rn:
            seen_rn.add(key)
            unique_rn_hits.append(h)
    rn_hits = unique_rn_hits

    # Save updated hashes
    save_hashes(state)
    print(f"\nUpdated hashes saved to {HASHES_PATH}")

    # Build report
    has_stale = bool(doc_changes)
    stale_skills = list({c["skill"] for c in doc_changes})

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "previous_check": last_checked,
        "total_skills": len(manifest),
        "doc_changes": doc_changes,
        "release_note_hits": rn_hits,
        "stale_skills": stale_skills,
    }

    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if doc_changes:
        print(f"\n  Doc changes detected: {len(doc_changes)}")
        for c in doc_changes:
            print(f"    - [{c['status']}] {c['skill']}: {c['path']}")
    else:
        print("\n  No documentation changes detected.")

    if rn_hits:
        print(f"\n  Release note keyword hits: {len(rn_hits)}")
        for h in rn_hits:
            print(f"    - {h['skill']}: \"{h['keyword']}\"")
    else:
        print("\n  No release note keyword hits.")

    print(f"\n  Stale skills: {stale_skills or 'none'}")

    # GitHub Actions outputs
    if not local_mode:
        set_github_output("has_stale", "true" if has_stale else "false")
        set_github_output("stale_skills", json.dumps(stale_skills))

        # Write issue body to a temp file for the workflow
        issue_body = build_issue_body(doc_changes, rn_hits, last_checked)
        issue_path = REPO_ROOT / ".github" / "freshness-report.md"
        with open(issue_path, "w") as f:
            f.write(issue_body)
        set_github_output("issue_body_path", str(issue_path))
        print(f"\n  Issue body written to {issue_path}")

    # Also dump JSON report
    print(f"\n  Full report (JSON):")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
