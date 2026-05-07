"""Integration tests for end-to-end routing and execution flow."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared" / "scripts"))

from security_wrapper import execute_with_security


@pytest.fixture(autouse=True)
def mock_cortex_execution():
    """Keep shared E2E routing tests from invoking a real Cortex process."""
    with patch("security_wrapper.execute_cortex_streaming") as mock_execute:
        mock_execute.return_value = {
            "session_id": "session-1",
            "events": [],
            "permission_requests": [],
            "final_result": "ok",
            "error": None,
        }
        yield mock_execute


@pytest.mark.integration
def test_full_snowflake_query_flow(tmp_path):
    """Full flow: Snowflake prompt → route → execute → audit"""
    prompt = "How many databases do I have in Snowflake?"

    with patch('security_wrapper.load_cortex_capabilities') as mock_cap:

        mock_cap.return_value = {"snowflake-query": {"name": "Query"}}

        result = execute_with_security(
            prompt=prompt,
            config_path=None,
            dry_run=False,
            envelope={"type": "RW", "user_prompt": prompt}
        )

        # Should route to cortex and execute
        assert result["status"] in ["executed", "awaiting_approval"]


@pytest.mark.integration
def test_full_local_file_flow():
    """Full flow: Local file prompt → route to agent → return decision"""
    prompt = "Fix the bug in app.py on line 42"

    with patch('security_wrapper.load_cortex_capabilities') as mock_cap:
        mock_cap.return_value = {}

        result = execute_with_security(
            prompt=prompt,
            config_path=None,
            dry_run=False,
            envelope={"type": "RO"}
        )

        assert result["status"] == "routed_to_coding_agent"
        assert result["routing"]["decision"] == "__CODING_AGENT__"


@pytest.mark.integration
def test_credential_blocking_flow():
    """Credential file paths should be blocked immediately"""
    prompt = "Show me the contents of ~/.ssh/id_rsa"

    result = execute_with_security(
        prompt=prompt,
        config_path=None,
        dry_run=False
    )

    assert result["status"] == "blocked"
    assert "credential" in result["reason"].lower()


@pytest.mark.integration
def test_approval_mode_prompt(tmp_path):
    """Prompt mode: should return awaiting_approval status"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text('security:\n  approval_mode: "prompt"')

    prompt = "Query Snowflake databases"

    with patch('security_wrapper.load_cortex_capabilities') as mock_cap:
        mock_cap.return_value = {"snowflake-query": {"name": "Query"}}

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            dry_run=False,
            envelope={"type": "RW", "user_prompt": prompt}
        )

        assert result["status"] == "awaiting_approval"
        assert "approval_prompt" in result


@pytest.mark.integration
def test_approval_mode_auto(tmp_path):
    """Auto mode: should execute immediately with audit"""
    config_path = tmp_path / "config.yaml"
    config_path.write_text('security:\n  approval_mode: "auto"')
    org_policy_path = tmp_path / "policy.yaml"
    org_policy_path.write_text('security:\n  approval_mode: "auto"')

    prompt = "Query Snowflake databases"

    with patch('security_wrapper.load_cortex_capabilities') as mock_cap:
        mock_cap.return_value = {"snowflake-query": {"name": "Query"}}

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            org_policy_path=str(org_policy_path),
            dry_run=False,
            envelope={"type": "RW", "user_prompt": prompt}
        )

        assert result["status"] == "executed"
        assert "audit_id" in result


@pytest.mark.integration
def test_envelope_ro_restrictions():
    """RO envelope should wait for approval instead of executing writes directly."""
    prompt = "Update Snowflake table"
    result = execute_with_security(
        prompt=prompt,
        config_path=None,
        dry_run=False,
        envelope={"type": "RO", "user_prompt": prompt}
    )

    assert result["status"] == "awaiting_approval"
    assert "approval_prompt" in result


@pytest.mark.integration
def test_envelope_rw_permissions(tmp_path):
    """RW envelope can execute only when org policy explicitly enables auto mode."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text('security:\n  approval_mode: "auto"')
    org_policy_path = tmp_path / "policy.yaml"
    org_policy_path.write_text('security:\n  approval_mode: "auto"')
    prompt = "Update Snowflake table"

    result = execute_with_security(
        prompt=prompt,
        config_path=str(config_path),
        org_policy_path=str(org_policy_path),
        dry_run=False,
        envelope={"type": "RW", "user_prompt": prompt}
    )

    assert result["status"] == "executed"
    assert result["approval_mode"] == "auto"


@pytest.mark.integration
def test_dry_run_mode():
    """Dry-run should initialize but not execute"""
    prompt = "Query Snowflake"

    result = execute_with_security(
        prompt=prompt,
        config_path=None,
        dry_run=True
    )

    assert result["status"] == "initialized"
    assert result["dry_run"] is True
    assert "routing" in result
    assert "config" in result
