#!/usr/bin/env python3
"""
LLM-based routing logic to determine if request should go to Cortex Code or Claude Code.
Uses semantic understanding rather than simple keyword matching.
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

from cortexcode_tool.security.config_manager import ConfigManager
from cortexcode_tool.security.cache_manager import CacheManager


# Snowflake/Cortex indicators
SNOWFLAKE_INDICATORS = [
    "snowflake", "cortex", "warehouse", "snowpark", "data warehouse",
    "cortex ai", "cortex search", "cortex analyst", "dynamic table",
    "snowflake database", "snowflake schema", "snowflake table",
    "data governance", "data quality", "trust my data",
    "ml function", "classification", "forecasting",
    "stream", "task", "stage", "pipe"
]

# Non-Snowflake indicators (route to Claude Code)
CLAUDE_CODE_INDICATORS = [
    "local file", "git", "github", "commit", "push", "pull request",
    "python script", "javascript", "react", "frontend", "backend",
    "postgres", "mysql", "mongodb", "redis",
    "docker", "kubernetes", "infrastructure",
    "read file", "write file", "edit file", "create file"
]


def load_cortex_capabilities():
    """Load cached Cortex capabilities using CacheManager."""
    try:
        # Get cache directory from config
        config_manager = ConfigManager()
        cache_dir_str = config_manager.get("security.cache_dir")
        cache_dir = Path(cache_dir_str).expanduser()

        # Use CacheManager to read cache with integrity validation
        cache_manager = CacheManager(cache_dir)
        capabilities = cache_manager.read("cortex-capabilities")

        if capabilities is None:
            print("Warning: Cortex capabilities not cached. Run discover_cortex.py first.", file=sys.stderr)
            return {}

        return capabilities

    except Exception as e:
        print(f"Warning: Failed to load Cortex capabilities from cache: {e}", file=sys.stderr)
        print("Run discover_cortex.py to cache capabilities.", file=sys.stderr)
        return {}


def analyze_with_llm_logic(prompt, capabilities):
    """
    Analyze prompt using LLM-inspired logic.
    This is a deterministic approximation of what an LLM would consider.
    """
    prompt_lower = prompt.lower()

    # Score based on indicators
    snowflake_score = 0
    claude_score = 0

    # Check for explicit Snowflake/Cortex mentions
    for indicator in SNOWFLAKE_INDICATORS:
        if indicator in prompt_lower:
            snowflake_score += 3 if indicator in ["snowflake", "cortex"] else 1

    # Check for non-Snowflake indicators
    for indicator in CLAUDE_CODE_INDICATORS:
        if indicator in prompt_lower:
            claude_score += 2

    # Check against Cortex skill triggers
    for skill_name, skill_info in capabilities.items():
        for trigger in skill_info.get("triggers", []):
            trigger_lower = trigger.lower()
            if trigger_lower in prompt_lower or any(word in prompt_lower for word in trigger_lower.split()):
                snowflake_score += 2
                break

    # SQL query detection
    sql_keywords = ["select", "insert", "update", "delete", "create table", "alter", "drop"]
    if any(kw in prompt_lower for kw in sql_keywords):
        # Could be any database, but check for Snowflake context
        if any(ind in prompt_lower for ind in ["snowflake", "warehouse", "cortex"]):
            snowflake_score += 3
        else:
            # Generic SQL, likely not Snowflake
            claude_score += 1

    # Data-related terms (ambiguous, need context)
    data_terms = ["data quality", "schema", "table", "database", "query"]
    data_term_count = sum(1 for term in data_terms if term in prompt_lower)
    if data_term_count >= 2:
        # Multiple data terms suggest database work
        if snowflake_score > 0:
            snowflake_score += 2
    elif data_term_count == 1 and "database" in prompt_lower:
        # Single "database" mention in a Snowflake CLI context → lean toward Cortex
        snowflake_score += 1

    # Calculate confidence
    total_score = snowflake_score + claude_score
    if total_score == 0:
        # No strong indicators — default to Cortex since user explicitly invoked this CLI
        return "cortex", 0.5

    confidence = max(snowflake_score, claude_score) / total_score

    if snowflake_score > claude_score:
        return "cortex", confidence
    else:
        return "claude", confidence


def check_credential_allowlist(
    prompt: str,
    config_path: Optional[Path] = None,
    org_policy_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Check if prompt contains credential file paths from the allowlist.

    This function runs before routing analysis to block prompts that reference
    credential files, regardless of whether they would be routed to Cortex or Claude.

    Args:
        prompt: User prompt to check
        config_path: Path to user config file (optional)
        org_policy_path: Path to organization policy file (optional)

    Returns:
        Dict with blocking decision:
        - blocked: True if credential detected, False otherwise
        - route: "blocked" if blocked, None otherwise
        - confidence: 1.0 if blocked (100% confident in blocking)
        - reason: Human-readable reason for blocking
        - pattern_matched: The allowlist pattern that matched
    """
    # Initialize ConfigManager with optional config paths
    config_manager = ConfigManager(
        config_path=config_path,
        org_policy_path=org_policy_path
    )

    # Load credential allowlist
    credential_allowlist = config_manager.get("security.credential_file_allowlist")

    # Check each pattern against the prompt (case-insensitive)
    prompt_lower = prompt.lower()

    for pattern in credential_allowlist:
        # Strip wildcards from pattern: ~/ **/ * → base pattern
        pattern_check = pattern.replace('~/', '').replace('**/', '').replace('*', '')

        # Strip trailing slashes
        pattern_check = pattern_check.rstrip('/')

        # Skip empty patterns (patterns that are only wildcards)
        if not pattern_check:
            continue

        # Check if pattern is in prompt (case-insensitive)
        if pattern_check in prompt_lower:
            return {
                "blocked": True,
                "route": "blocked",
                "confidence": 1.0,
                "reason": f"Prompt contains credential file path from allowlist",
                "pattern_matched": pattern
            }

    # No credentials detected
    return {
        "blocked": False
    }


def main():
    """Main routing function."""
    parser = argparse.ArgumentParser(description="Route request to Cortex or Claude Code")
    parser.add_argument("--prompt", required=True, help="User prompt to analyze")
    parser.add_argument("--config", help="Path to user config file")
    parser.add_argument("--org-policy", help="Path to organization policy file")
    args = parser.parse_args()

    # Step 1: Check credential allowlist BEFORE routing
    config_path = Path(args.config) if args.config else None
    org_policy_path = Path(args.org_policy) if args.org_policy else None

    credential_check = check_credential_allowlist(
        args.prompt,
        config_path,
        org_policy_path
    )

    # If blocked by credential check, return immediately
    if credential_check.get("blocked"):
        print(json.dumps(credential_check, indent=2))
        print(f"\n⛔ BLOCKED: Credential file detected", file=sys.stderr)
        print(f"   Pattern: {credential_check['pattern_matched']}", file=sys.stderr)
        print(f"   Reason: {credential_check['reason']}", file=sys.stderr)
        sys.exit(0)

    # Step 2: Load Cortex capabilities
    capabilities = load_cortex_capabilities()

    # Step 3: Analyze prompt for routing
    route, confidence = analyze_with_llm_logic(args.prompt, capabilities)

    # Step 4: Output decision
    result = {
        "route": route,
        "confidence": confidence,
        "reasoning": f"Routed to {route} with {confidence:.2%} confidence"
    }

    print(json.dumps(result, indent=2))

    print(f"\n→ Route to: {route.upper()}", file=sys.stderr)
    print(f"   Confidence: {confidence:.2%}", file=sys.stderr)

    sys.exit(0)


if __name__ == "__main__":
    main()
