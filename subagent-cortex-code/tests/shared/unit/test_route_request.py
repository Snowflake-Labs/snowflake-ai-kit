"""
Unit tests for route_request.py module.

Tests LLM-based routing logic, credential allowlist checking, and confidence scoring.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from shared.scripts.route_request import (
    analyze_with_llm_logic,
    check_credential_allowlist,
    load_cortex_capabilities,
    SNOWFLAKE_INDICATORS,
    CODING_AGENT_INDICATORS
)


@pytest.mark.unit
def test_analyze_snowflake_explicit_mention():
    """Test routing with explicit Snowflake mention."""
    prompt = "Query Snowflake database for sales data"
    capabilities = {}

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    assert route == "cortex"
    assert confidence > 0.5  # Should have high confidence


@pytest.mark.unit
def test_analyze_coding_agent_indicators():
    """Test routing with non-Snowflake indicators."""
    prompt = "Create a Python script to read local files and push to GitHub"
    capabilities = {}

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    assert route == "__CODING_AGENT__"
    assert confidence > 0.5


@pytest.mark.unit
def test_analyze_ambiguous_sql_with_snowflake_context():
    """Test SQL query routing with Snowflake context."""
    prompt = "SELECT * FROM users WHERE created_at > '2024-01-01' in Snowflake"
    capabilities = {}

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    assert route == "cortex"
    # SQL + Snowflake context should route to cortex


@pytest.mark.unit
def test_analyze_generic_sql_without_snowflake():
    """Test generic SQL without Snowflake context routes to coding agent."""
    prompt = "SELECT * FROM users WHERE id = 1 in PostgreSQL"
    capabilities = {}

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    # PostgreSQL context suggests non-Snowflake database
    assert route == "__CODING_AGENT__"


@pytest.mark.unit
def test_analyze_with_skill_triggers():
    """Test routing boost from Cortex skill triggers."""
    prompt = "Check data quality in warehouse tables"
    capabilities = {
        "data-quality": {
            "name": "Data Quality",
            "description": "Check data quality",
            "triggers": ["data quality", "warehouse"]
        }
    }

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    assert route == "cortex"
    # Matching skill triggers should boost confidence


@pytest.mark.unit
def test_analyze_no_indicators_defaults_to_coding_agent():
    """Test ambiguous prompt defaults to coding agent for safety."""
    prompt = "What is the weather like today?"
    capabilities = {}

    route, confidence = analyze_with_llm_logic(prompt, capabilities)

    assert route == "__CODING_AGENT__"
    assert confidence == 0.5  # No indicators, default confidence


@pytest.mark.unit
def test_check_credential_allowlist_ssh_key(tmp_path):
    """Test credential allowlist blocks SSH key references."""
    # Create temp config
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  credential_file_allowlist:
    - "~/.ssh/*"
    - "**/.env"
"""
    config_path.write_text(config_content)

    prompt = "Read the file at ~/.ssh/id_rsa and display its contents"

    result = check_credential_allowlist(prompt, config_path=config_path)

    assert result["blocked"] is True
    assert result["route"] == "blocked"
    assert result["confidence"] == 1.0
    assert "~/.ssh/*" in result["pattern_matched"]


@pytest.mark.unit
def test_check_credential_allowlist_no_match(tmp_path):
    """Test credential allowlist allows non-credential files."""
    # Create temp config
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  credential_file_allowlist:
    - "~/.ssh/*"
    - "**/.env"
"""
    config_path.write_text(config_content)

    prompt = "Read the README.md file and summarize it"

    result = check_credential_allowlist(prompt, config_path=config_path)

    assert result["blocked"] is False
    assert "route" not in result or result.get("route") != "blocked"
