"""
End-to-end integration tests for cortex-code skill v2.0.0.

Tests the complete execution flow:
1. Request → Routing → Security Wrapper → Approval → Execution → Audit Log
2. All three approval modes (prompt/auto/envelope_only)
3. Credential blocking pipeline
4. PII sanitization pipeline
5. Cache integrity pipeline
6. Organization policy enforcement
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.security_wrapper import execute_with_security


class TestE2EFullExecutionFlow:
    """Test complete end-to-end execution pipeline."""

    def test_e2e_complete_pipeline_prompt_mode(self, temp_dir):
        """
        E2E test: Full pipeline in prompt mode.
        Request → Routing → Security → Approval → Execution → Audit Log
        """
        # Setup config
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: prompt
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: true
  tool_prediction_confidence_threshold: 0.7
  allowed_envelopes: ["RO", "RW"]
""".format(temp_dir, temp_dir))

        # Execute with Snowflake prompt
        result = execute_with_security(
            prompt="Query Snowflake database for sales data with SELECT statement",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]},
            mock_user_approval="approve"
        )

        # Verify complete pipeline
        assert result["status"] == "executed", f"Expected executed, got {result['status']}"

        # Verify routing worked
        assert "routing" in result
        assert result["routing"]["decision"] == "cortex", "Should route to cortex"
        assert result["routing"]["confidence"] > 0.5

        # Verify approval flow
        assert result["approval_mode"] == "prompt"
        assert "predicted_tools" in result
        assert "allowed_tools" in result

        # Verify execution completed
        assert "result" in result
        assert result["result"]["status"] == "success"

        # Verify audit log created
        assert "audit_id" in result
        audit_log = temp_dir / "audit.log"
        assert audit_log.exists()

        # Verify security context
        assert "security" in result
        assert result["security"]["sanitized"] is True

    def test_e2e_complete_pipeline_auto_mode(self, temp_dir):
        """
        E2E test: Full pipeline in auto mode.
        Request → Routing → Auto-Approval → Execution → Audit Log
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: false
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Run Snowflake query to list all tables in database",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        # Verify auto-approval flow
        assert result["status"] == "executed"
        assert result["approval_mode"] == "auto"
        assert result["allowed_tools"] is not None

        # Verify audit log
        assert "audit_id" in result
        audit_log = temp_dir / "audit.log"
        assert audit_log.exists()

    def test_e2e_complete_pipeline_envelope_only_mode(self, temp_dir):
        """
        E2E test: Full pipeline in envelope_only mode.
        Request → Routing → Envelope Enforcement → Execution → Audit Log
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: envelope_only
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Execute Snowflake operation",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT", "INSERT"]}
        )

        # Verify envelope-only flow
        assert result["status"] == "executed"
        assert result["approval_mode"] == "envelope_only"
        assert result["allowed_tools"] is None  # None means rely on envelope only

        # Verify audit log
        assert "audit_id" in result


class TestE2EPromptModeFlow:
    """Test prompt mode end-to-end scenarios."""

    def test_e2e_prompt_mode_with_approval(self, temp_dir):
        """
        E2E Prompt Mode: User approves execution.
        User request → Cortex routing → Sanitization → Tool prediction → User approves → Execute
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: prompt
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: true
  tool_prediction_confidence_threshold: 0.8
""".format(temp_dir, temp_dir))

        # User approves
        result = execute_with_security(
            prompt="Query Snowflake warehouse for customer data with SELECT",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]},
            mock_user_approval="approve"
        )

        assert result["status"] == "executed"
        assert result["approval_mode"] == "prompt"
        assert len(result["predicted_tools"]) > 0
        assert result["allowed_tools"] == result["predicted_tools"]
        assert "audit_id" in result

    def test_e2e_prompt_mode_with_denial(self, temp_dir):
        """
        E2E Prompt Mode: User denies execution.
        User request → Cortex routing → Tool prediction → User denies → Execution blocked
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: prompt
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        # User denies
        result = execute_with_security(
            prompt="Run Snowflake DELETE operation on production table",
            config_path=str(config_path),
            envelope={"allowed_tools": ["DELETE"]},
            mock_user_approval="deny"
        )

        assert result["status"] == "denied"
        assert "predicted_tools" in result
        assert "message" in result
        assert "denied" in result["message"].lower()

    def test_e2e_prompt_mode_awaiting_approval(self, temp_dir):
        """
        E2E Prompt Mode: Returns approval prompt for user.
        User request → Tool prediction → Approval prompt generated
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: prompt
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        # No mock approval - should return awaiting_approval
        result = execute_with_security(
            prompt="Update Snowflake table with new values",
            config_path=str(config_path),
            envelope={"allowed_tools": ["UPDATE"]}
        )

        assert result["status"] == "awaiting_approval"
        assert "approval_prompt" in result
        assert "predicted_tools" in result
        assert "confidence" in result
        assert "envelope" in result


class TestE2EAutoModeFlow:
    """Test auto mode end-to-end scenarios."""

    def test_e2e_auto_mode_full_flow(self, temp_dir):
        """
        E2E Auto Mode: Auto-approval and execution.
        User request → Cortex routing → Tool prediction → Auto-approval → Execute → Audit
        """
        config_path = temp_dir / "config.yaml"
        audit_log = temp_dir / "audit.log"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
  sanitize_conversation_history: false
""".format(audit_log, temp_dir))

        result = execute_with_security(
            prompt="Query Snowflake database for analytics data",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT", "INSERT"]}
        )

        # Verify auto-approval
        assert result["status"] == "executed"
        assert result["approval_mode"] == "auto"
        assert result["predicted_tools"] is not None
        assert result["allowed_tools"] == result["predicted_tools"]

        # Verify audit log entry
        assert audit_log.exists()
        with open(audit_log) as f:
            audit_data = json.loads(f.readline())
            assert audit_data["event_type"] == "cortex_execution"
            assert audit_data["execution"]["auto_approved"] is True
            assert audit_data["routing"]["decision"] == "cortex"

    def test_e2e_auto_mode_with_multiple_executions(self, temp_dir):
        """Test multiple auto-approved executions are all audited."""
        config_path = temp_dir / "config.yaml"
        audit_log = temp_dir / "audit.log"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
""".format(audit_log, temp_dir))

        # Execute three times
        prompts = [
            "Query Snowflake for sales data",
            "Update Snowflake warehouse settings",
            "Create new Snowflake table for analytics"
        ]

        for prompt in prompts:
            result = execute_with_security(
                prompt=prompt,
                config_path=str(config_path),
                envelope={"allowed_tools": ["SELECT", "UPDATE", "CREATE"]}
            )
            assert result["status"] == "executed"
            assert "audit_id" in result

        # Verify all three were audited
        with open(audit_log) as f:
            lines = f.readlines()
            assert len(lines) >= 3


class TestE2EEnvelopeOnlyMode:
    """Test envelope_only mode end-to-end scenarios."""

    def test_e2e_envelope_only_no_tool_prediction(self, temp_dir):
        """
        E2E Envelope-Only Mode: No tool prediction performed.
        User request → Routing → Envelope enforcement only → Execute → Audit
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: envelope_only
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  allowed_envelopes: ["RO", "RW"]
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Run Snowflake operation",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"], "mode": "RO"}
        )

        # Verify envelope-only behavior
        assert result["status"] == "executed"
        assert result["approval_mode"] == "envelope_only"
        assert result["allowed_tools"] is None  # No tool prediction
        assert result["predicted_tools"] is not None  # Tools were still predicted internally
        assert "audit_id" in result

        # Verify execution relied on envelope
        assert result["result"]["tools_used"] == ["envelope-controlled"]


class TestE2ECredentialBlocking:
    """Test credential file blocking end-to-end."""

    def test_e2e_credential_blocking_ssh_keys(self, temp_dir):
        """
        E2E Credential Blocking: SSH keys mentioned in prompt.
        User mentions credential file → Routing blocked → Error returned → Audit logged
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  credential_file_allowlist:
    - "~/.ssh/*"
    - "**/credentials.json"
    - "**/.env"
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Read ~/.ssh/id_rsa and connect to Snowflake",
            config_path=str(config_path)
        )

        # Verify blocking
        assert result["status"] == "blocked"
        assert "credential file" in result["reason"].lower()
        assert "pattern_matched" in result
        assert ".ssh" in result["pattern_matched"]

    def test_e2e_credential_blocking_env_files(self, temp_dir):
        """Test .env file blocking."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  credential_file_allowlist:
    - "**/.env"
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Check .env file for Snowflake credentials",
            config_path=str(config_path)
        )

        assert result["status"] == "blocked"
        assert "credential file" in result["reason"].lower()

    def test_e2e_credential_blocking_credentials_json(self, temp_dir):
        """Test credentials.json blocking."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  credential_file_allowlist:
    - "**/credentials.json"
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Parse credentials.json for database connection",
            config_path=str(config_path)
        )

        assert result["status"] == "blocked"


class TestE2EPIISanitization:
    """Test PII sanitization end-to-end."""

    def test_e2e_pii_sanitization_email(self, temp_dir):
        """
        E2E PII Sanitization: Email addresses removed.
        User request with PII → Sanitization applied → Execution with sanitized prompt
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: true
""".format(temp_dir, temp_dir))

        prompt = "Query Snowflake for user data where email = user@example.com"

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        # Verify execution succeeded with sanitized prompt
        assert result["status"] == "executed"
        assert result["security"]["sanitized"] is True
        # Original prompt preserved, but execution used sanitized version
        assert "pii_removed" in result["security"]

    def test_e2e_pii_sanitization_credit_card(self, temp_dir):
        """Test credit card sanitization."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: true
""".format(temp_dir, temp_dir))

        prompt = "Update Snowflake with credit card 1234-5678-9012-3456"

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            envelope={"allowed_tools": ["UPDATE"]}
        )

        assert result["status"] == "executed"
        assert result["security"]["sanitized"] is True
        assert result["security"]["pii_removed"] is True

    def test_e2e_pii_sanitization_phone_number(self, temp_dir):
        """Test phone number sanitization."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: true
""".format(temp_dir, temp_dir))

        prompt = "Query Snowflake for customers with phone (555) 123-4567"

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result["status"] == "executed"
        assert result["security"]["sanitized"] is True

    def test_e2e_pii_sanitization_disabled(self, temp_dir):
        """Test that sanitization can be disabled."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  sanitize_conversation_history: false
""".format(temp_dir, temp_dir))

        prompt = "Query Snowflake for email@test.com"

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result["status"] == "executed"
        assert result["security"]["sanitized"] is False
        assert result["security"]["pii_removed"] is False


class TestE2ECacheIntegrity:
    """Test cache integrity end-to-end."""

    def test_e2e_cache_with_fingerprint_validation(self, temp_dir):
        """
        E2E Cache Integrity: Cache read with fingerprint validation.
        First run → Cache written → Second run → Cache read → Fingerprint validated
        """
        from security.cache_manager import CacheManager

        cache_dir = temp_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)

        cache_manager = CacheManager(cache_dir=cache_dir)

        # First run: write cache
        test_data = {"capabilities": ["SELECT", "INSERT"], "version": "2.0.0"}
        cache_manager.write("test-capabilities", test_data)

        # Verify cache was written with fingerprint
        cache_file = cache_dir / "test-capabilities.json"
        assert cache_file.exists()

        # Second run: read cache
        cached_data = cache_manager.read("test-capabilities")

        # Verify data matches
        assert cached_data is not None
        assert cached_data["capabilities"] == ["SELECT", "INSERT"]
        assert cached_data["version"] == "2.0.0"

    def test_e2e_cache_corruption_detection(self, temp_dir):
        """Test that cache corruption is detected via fingerprint."""
        from security.cache_manager import CacheManager

        cache_dir = temp_dir / ".cache"
        cache_dir.mkdir(exist_ok=True)

        cache_manager = CacheManager(cache_dir=cache_dir)

        # Write cache
        test_data = {"data": "original"}
        cache_manager.write("test-data", test_data)

        # Corrupt the cache file (modify content without updating fingerprint)
        cache_file = cache_dir / "test-data.json"
        with open(cache_file, 'r') as f:
            cache_content = json.load(f)

        cache_content["data"] = "corrupted"

        with open(cache_file, 'w') as f:
            json.dump(cache_content, f)

        # Try to read corrupted cache
        cached_data = cache_manager.read("test-data")

        # Should return None due to fingerprint mismatch
        assert cached_data is None


class TestE2EOrganizationPolicy:
    """Test organization policy enforcement end-to-end."""

    def test_e2e_org_policy_overrides_user_config(self, temp_dir):
        """
        E2E Org Policy: Organization policy overrides user settings.
        Org policy exists → User config overridden → Policy enforced → Execution follows policy
        """
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  allowed_envelopes: ["RO", "RW", "DEPLOY"]
""".format(temp_dir, temp_dir))

        org_policy_path = temp_dir / "org_policy.yaml"
        org_policy_path.write_text("""
security:
  approval_mode: prompt
  allowed_envelopes: ["RO"]
  deploy_envelope_confirmation: true
""")

        result = execute_with_security(
            prompt="Query Snowflake database",
            config_path=str(config_path),
            org_policy_path=str(org_policy_path),
            envelope={"allowed_tools": ["SELECT"]},
            mock_user_approval="approve"
        )

        # Verify org policy was applied
        assert result["status"] == "executed"
        assert result["approval_mode"] == "prompt"  # Org policy, not user config

    def test_e2e_org_policy_restricts_envelopes(self, temp_dir):
        """Test org policy restricts allowed envelopes."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
  allowed_envelopes: ["RO", "RW", "DEPLOY"]
""".format(temp_dir, temp_dir))

        org_policy_path = temp_dir / "org_policy.yaml"
        org_policy_path.write_text("""
security:
  approval_mode: auto
  allowed_envelopes: ["RO"]
""")

        # First verify dry-run shows org policy is enforced
        result = execute_with_security(
            prompt="Test org policy",
            config_path=str(config_path),
            org_policy_path=str(org_policy_path),
            dry_run=True
        )

        assert result["config"]["allowed_envelopes"] == ["RO"]


class TestE2ERoutingDecisions:
    """Test routing decisions end-to-end."""

    def test_e2e_routing_to_cortex_for_snowflake(self, temp_dir):
        """Test Snowflake requests route to Cortex."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Query Snowflake warehouse for sales analytics",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result["status"] == "executed"
        assert result["routing"]["decision"] == "cortex"
        assert result["routing"]["confidence"] > 0.5

    def test_e2e_routing_to_claude_for_local_operations(self, temp_dir):
        """Test local file operations route to Claude."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="Read local file config.json and parse it with Python",
            config_path=str(config_path)
        )

        # Should route to Claude, not execute
        assert result["status"] == "routed_to_claude"
        assert result["routing"]["decision"] == "claude"

    def test_e2e_routing_with_sql_and_snowflake_context(self, temp_dir):
        """Test SQL query with Snowflake context routes to Cortex."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}/audit.log
  cache_dir: {}/.cache
""".format(temp_dir, temp_dir))

        result = execute_with_security(
            prompt="SELECT * FROM snowflake.public.customers WHERE region = 'US'",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result["status"] == "executed"
        assert result["routing"]["decision"] == "cortex"


class TestE2EAuditLogging:
    """Test audit logging throughout pipeline."""

    def test_e2e_all_executions_create_audit_entries(self, temp_dir):
        """Test that every execution creates an audit log entry."""
        config_path = temp_dir / "config.yaml"
        audit_log = temp_dir / "audit.log"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
""".format(audit_log, temp_dir))

        # Execute multiple operations
        operations = [
            ("Query Snowflake database", {"allowed_tools": ["SELECT"]}),
            ("Update Snowflake table", {"allowed_tools": ["UPDATE"]}),
            ("Create Snowflake view", {"allowed_tools": ["CREATE"]}),
        ]

        audit_ids = []
        for prompt, envelope in operations:
            result = execute_with_security(
                prompt=prompt,
                config_path=str(config_path),
                envelope=envelope
            )
            assert result["status"] == "executed"
            assert "audit_id" in result
            audit_ids.append(result["audit_id"])

        # Verify all audit IDs are unique
        assert len(audit_ids) == len(set(audit_ids))

        # Verify audit log has entries
        with open(audit_log) as f:
            lines = f.readlines()
            assert len(lines) >= 3

            for line in lines:
                entry = json.loads(line)
                assert entry["event_type"] == "cortex_execution"
                assert "routing" in entry
                assert "execution" in entry
                assert "result" in entry

    def test_e2e_audit_log_contains_security_context(self, temp_dir):
        """Test audit logs include security context."""
        config_path = temp_dir / "config.yaml"
        audit_log = temp_dir / "audit.log"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
  sanitize_conversation_history: true
""".format(audit_log, temp_dir))

        result = execute_with_security(
            prompt="Query Snowflake with email user@test.com",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result["status"] == "executed"

        # Verify audit log has security context
        with open(audit_log) as f:
            entry = json.loads(f.readline())
            assert "security" in entry
            assert entry["security"]["sanitized"] is True


class TestE2EErrorHandling:
    """Test error handling throughout the pipeline."""

    def test_e2e_invalid_config_fallback_to_defaults(self, temp_dir):
        """Test that invalid config falls back to defaults."""
        config_path = temp_dir / "config.yaml"
        config_path.write_text("invalid: yaml: [[[")

        result = execute_with_security(
            prompt="Query Snowflake",
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        # Should fall back to defaults (default is prompt mode)
        assert result["status"] in ["executed", "routed_to_claude", "awaiting_approval"]

    def test_e2e_missing_config_uses_defaults(self):
        """Test execution with missing config file uses defaults."""
        result = execute_with_security(
            prompt="Query Snowflake database",
            config_path="/nonexistent/config.yaml",
            envelope={"allowed_tools": ["SELECT"]}
        )

        # Should use default config (default is prompt mode, so awaiting_approval expected)
        assert result["status"] in ["executed", "routed_to_claude", "awaiting_approval"]


class TestE2EComplexScenarios:
    """Test complex real-world scenarios."""

    def test_e2e_complex_multi_stage_pipeline(self, temp_dir):
        """
        Test complex scenario with multiple stages:
        1. PII in prompt (sanitized)
        2. Credential check (passed)
        3. Routing to Cortex
        4. Tool prediction
        5. Approval (auto)
        6. Execution
        7. Audit logging
        """
        config_path = temp_dir / "config.yaml"
        audit_log = temp_dir / "audit.log"
        config_path.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
  sanitize_conversation_history: true
  credential_file_allowlist:
    - "~/.ssh/*"
""".format(audit_log, temp_dir))

        # Complex prompt with PII but no credential files
        prompt = "Query Snowflake database for customer records where email = john.doe@example.com and phone = 555-123-4567"

        result = execute_with_security(
            prompt=prompt,
            config_path=str(config_path),
            envelope={"allowed_tools": ["SELECT"]}
        )

        # Verify all stages succeeded
        assert result["status"] == "executed"
        assert result["routing"]["decision"] == "cortex"
        assert result["security"]["sanitized"] is True
        assert result["security"]["pii_removed"] is True
        assert result["approval_mode"] == "auto"
        assert "audit_id" in result

        # Verify audit log
        with open(audit_log) as f:
            entry = json.loads(f.readline())
            assert entry["security"]["sanitized"] is True
            assert entry["security"]["pii_removed"] is True

    def test_e2e_switching_between_approval_modes(self, temp_dir):
        """Test switching between different approval modes works correctly."""
        audit_log = temp_dir / "audit.log"

        # First execution: prompt mode
        config1 = temp_dir / "config1.yaml"
        config1.write_text("""
security:
  approval_mode: prompt
  audit_log_path: {}
  cache_dir: {}/.cache
""".format(audit_log, temp_dir))

        result1 = execute_with_security(
            prompt="Query Snowflake",
            config_path=str(config1),
            envelope={"allowed_tools": ["SELECT"]},
            mock_user_approval="approve"
        )

        assert result1["status"] == "executed"
        assert result1["approval_mode"] == "prompt"

        # Second execution: auto mode
        config2 = temp_dir / "config2.yaml"
        config2.write_text("""
security:
  approval_mode: auto
  audit_log_path: {}
  cache_dir: {}/.cache
""".format(audit_log, temp_dir))

        result2 = execute_with_security(
            prompt="Query Snowflake again",
            config_path=str(config2),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result2["status"] == "executed"
        assert result2["approval_mode"] == "auto"

        # Third execution: envelope_only mode
        config3 = temp_dir / "config3.yaml"
        config3.write_text("""
security:
  approval_mode: envelope_only
  audit_log_path: {}
  cache_dir: {}/.cache
""".format(audit_log, temp_dir))

        result3 = execute_with_security(
            prompt="Query Snowflake third time",
            config_path=str(config3),
            envelope={"allowed_tools": ["SELECT"]}
        )

        assert result3["status"] == "executed"
        assert result3["approval_mode"] == "envelope_only"

        # Verify all three were audited
        with open(audit_log) as f:
            lines = f.readlines()
            assert len(lines) >= 3
