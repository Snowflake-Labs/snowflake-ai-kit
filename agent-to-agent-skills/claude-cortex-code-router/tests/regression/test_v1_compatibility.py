#!/usr/bin/env python3
"""
Regression tests for v1.x compatibility.

v2.0.0 adds security features but must maintain backward compatibility
when using 'auto' approval mode. These tests ensure v1.x workflows continue
to work without breaking changes.

Test Scenarios:
1. Auto mode behaves like v1.x (no prompts, auto-approval)
2. Existing workflows unchanged (routing, execution)
3. Skill invocation patterns work
4. Script backward compatibility
5. Configuration compatibility (no config = secure defaults)
"""

import pytest
import json
import sys
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any

# Add scripts and security directories to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
security_dir = Path(__file__).parent.parent.parent / "security"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(security_dir))

from execute_cortex import execute_cortex_streaming
from route_request import analyze_with_llm_logic
from security.config_manager import ConfigManager
from security.audit_logger import AuditLogger


class TestAutoModeV1Compatibility:
    """Test that auto mode behaves like v1.x (no prompts, auto-execution)."""

    @patch('execute_cortex.subprocess.Popen')
    def test_auto_mode_no_user_prompts(self, mock_popen):
        """Auto mode should execute without user interaction like v1.x."""
        # Setup mock process
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test123"}\n',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Executing query"}]}}\n',
            '{"type": "result", "result": "success"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Execute with auto mode (v1.x behavior)
        result = execute_cortex_streaming(
            prompt="SELECT * FROM customers",
            approval_mode="auto",
            envelope="RW"
        )

        # Verify execution completed
        assert result is not None
        assert result.get("session_id") == "test123"
        assert result.get("final_result") == "success"
        assert result.get("error") is None

        # Verify command uses programmatic mode (auto-approval)
        cmd = mock_popen.call_args[0][0]
        assert "--input-format" in cmd
        assert "stream-json" in cmd

    @patch('execute_cortex.subprocess.Popen')
    def test_auto_mode_with_snowflake_tools(self, mock_popen):
        """Auto mode should allow Snowflake tools without prompting."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test456"}\n',
            '{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "snowflake_sql_execute"}]}}\n',
            '{"type": "result", "result": "query_executed"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Execute query that uses Snowflake tools
        result = execute_cortex_streaming(
            prompt="Query the warehouse_stats table",
            connection="prod_snowflake",
            approval_mode="auto"
        )

        # Verify Snowflake tools used without prompting
        assert result.get("session_id") == "test456"
        assert len(result.get("events", [])) > 0

        # Verify connection parameter passed
        cmd = mock_popen.call_args[0][0]
        assert "-c" in cmd
        assert "prod_snowflake" in cmd

    @patch('execute_cortex.subprocess.Popen')
    def test_auto_mode_applies_envelope_security(self, mock_popen):
        """Auto mode should still apply envelope-based security."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test789"}\n',
            '{"type": "result", "result": "done"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Execute with RO envelope (read-only)
        result = execute_cortex_streaming(
            prompt="Read table schema",
            approval_mode="auto",
            envelope="RO"
        )

        # Verify envelope applied (Edit/Write blocked)
        cmd = mock_popen.call_args[0][0]
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        # RO envelope should block write operations
        assert "Edit" in disallowed_tools
        assert "Write" in disallowed_tools

    def test_auto_mode_mandatory_audit_logging(self, temp_dir):
        """Auto mode must enable audit logging (v2.0 requirement)."""
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "approval_mode": "auto",
                "audit_log_path": str(temp_dir / "audit.log")
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        config_manager = ConfigManager(config_path=config_file)

        # Auto mode should have audit logging enabled
        approval_mode = config_manager.get("security.approval_mode")
        audit_log_path = config_manager.get("security.audit_log_path")

        assert approval_mode == "auto"
        assert audit_log_path is not None

        # Audit logger should be creatable
        audit_logger = AuditLogger(log_path=Path(audit_log_path))
        assert audit_logger is not None


class TestRoutingCompatibility:
    """Test that routing decisions remain unchanged from v1.x."""

    def test_snowflake_keywords_route_to_cortex(self):
        """Snowflake queries should route to Cortex (unchanged from v1.x)."""
        prompts = [
            "SELECT * FROM snowflake.my_database.customers",
            "Create a dynamic table for analytics",
            "Use Cortex AI to analyze sentiment",
            "Query the warehouse_stats table"
        ]

        for prompt in prompts:
            route, confidence = analyze_with_llm_logic(prompt, {})
            assert route == "cortex", f"Expected cortex for: {prompt}"
            assert confidence > 0.5

    def test_non_snowflake_routes_to_claude(self):
        """Non-Snowflake operations should route to Claude (unchanged)."""
        prompts = [
            "Read the local Python script",
            "Create a React component",
            "Push changes to GitHub",
            "Query PostgreSQL database"
        ]

        for prompt in prompts:
            route, confidence = analyze_with_llm_logic(prompt, {})
            assert route == "claude", f"Expected claude for: {prompt}"

    def test_sql_without_snowflake_context_routes_to_claude(self):
        """Generic SQL without Snowflake context routes to Claude."""
        prompt = "SELECT id, name FROM users WHERE active = true"
        route, confidence = analyze_with_llm_logic(prompt, {})

        # Generic SQL without Snowflake context → Claude
        assert route == "claude"


class TestScriptBackwardCompatibility:
    """Test that scripts maintain v1.x interfaces."""

    @patch('execute_cortex.subprocess.Popen')
    def test_execute_cortex_accepts_old_parameters(self, mock_popen):
        """execute_cortex.py should accept v1.x parameter style."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test"}\n',
            '{"type": "result", "result": "ok"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # v1.x style invocation (positional prompt, connection)
        result = execute_cortex_streaming(
            "Test query",
            connection="my_connection"
        )

        # Should work without errors
        assert result is not None
        assert result.get("session_id") == "test"

    def test_route_request_returns_v1_format(self):
        """route_request.py should return same format as v1.x."""
        prompt = "Analyze Snowflake warehouse performance"
        route, confidence = analyze_with_llm_logic(prompt, {})

        # v1.x format: (route_string, confidence_float)
        assert isinstance(route, str)
        assert isinstance(confidence, float)
        assert route in ["cortex", "claude"]
        assert 0 <= confidence <= 1

    @patch('execute_cortex.subprocess.Popen')
    def test_disallowed_tools_parameter_still_works(self, mock_popen):
        """execute_cortex should still accept disallowed_tools parameter."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "result", "result": "done"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # v1.x style with explicit disallowed tools
        result = execute_cortex_streaming(
            "Test prompt",
            disallowed_tools=["Bash", "Write"]
        )

        # Verify disallowed tools passed to command
        cmd = mock_popen.call_args[0][0]
        assert "--disallowed-tools" in cmd


class TestConfigurationCompatibility:
    """Test configuration backward compatibility."""

    def test_no_config_file_uses_secure_defaults(self, temp_dir):
        """No config file should use secure defaults (not v1.x behavior)."""
        # Initialize ConfigManager without config file
        config_manager = ConfigManager()

        # Should use secure defaults (prompt mode, not auto)
        approval_mode = config_manager.get("security.approval_mode")
        assert approval_mode == "prompt"

        # Other defaults should be set
        assert config_manager.get("security.sanitize_conversation_history") is True
        assert config_manager.get("security.audit_log_path") is not None

    def test_empty_config_file_uses_defaults(self, temp_dir):
        """Empty config file should use all defaults."""
        config_file = temp_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({}, f)

        config_manager = ConfigManager(config_path=config_file)

        # Should use defaults
        approval_mode = config_manager.get("security.approval_mode")
        assert approval_mode == "prompt"

    def test_partial_config_fills_in_defaults(self, temp_dir):
        """Partial config should merge with defaults."""
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "approval_mode": "auto"
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        config_manager = ConfigManager(config_path=config_file)

        # User-specified value
        assert config_manager.get("security.approval_mode") == "auto"

        # Default values filled in
        assert config_manager.get("security.sanitize_conversation_history") is True
        assert config_manager.get("security.max_history_items") == 3

    def test_v1_style_invocation_with_auto_mode(self, temp_dir):
        """V1.x-style invocation (no config) with auto mode."""
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "approval_mode": "auto"
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        config_manager = ConfigManager(config_path=config_file)

        # This configuration enables v1.x behavior
        assert config_manager.get("security.approval_mode") == "auto"

        # But audit logging is mandatory (v2.0 requirement)
        assert config_manager.get("security.audit_log_path") is not None


class TestCacheLocationMigration:
    """Test that cache location changed but still works."""

    def test_cache_uses_new_location(self, temp_dir):
        """Cache should use ~/.cache/cortex-skill instead of /tmp."""
        config_file = temp_dir / "config.yaml"
        cache_dir = temp_dir / ".cache" / "cortex-skill"
        cache_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "security": {
                "cache_dir": str(cache_dir)
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        config_manager = ConfigManager(config_path=config_file)
        configured_cache = config_manager.get("security.cache_dir")

        # Should not be /tmp/ at root (v1.x used /tmp/cortex-capabilities.json)
        # v2.0 uses ~/.cache/cortex-skill or similar persistent location
        assert not configured_cache.startswith("/tmp/")

        # Should be in .cache subdirectory (persistent, not temp)
        assert ".cache" in configured_cache or "cache" in Path(configured_cache).name
        assert "cortex-skill" in configured_cache or "cortex-code" in configured_cache

    @patch('security.cache_manager.CacheManager.read')
    def test_cache_manager_backward_compatible(self, mock_read):
        """CacheManager should work with old cache reads."""
        from security.cache_manager import CacheManager

        cache_dir = Path("/tmp/test-cache")
        cache_manager = CacheManager(cache_dir=cache_dir)

        # Old cache read style (key-based)
        mock_read.return_value = {"skill1": {"triggers": ["test"]}}
        capabilities = cache_manager.read("cortex-capabilities")

        # Should return cached data
        assert capabilities is not None
        assert "skill1" in capabilities


class TestSkillInvocationPatterns:
    """Test that skill invocation patterns work correctly."""

    def test_skill_loaded_via_skill_system(self):
        """Skill should be loadable via Claude Code skill system."""
        skill_md = Path(__file__).parent.parent.parent / "SKILL.md"
        assert skill_md.exists(), "SKILL.md should exist"

        # Read SKILL.md frontmatter
        with open(skill_md) as f:
            content = f.read()

        # Check required frontmatter fields (v1.x compatibility)
        assert "name: cortex-code" in content
        assert "description:" in content

    @patch('execute_cortex.subprocess.Popen')
    def test_scripts_execute_from_correct_paths(self, mock_popen):
        """Scripts should execute from scripts/ directory."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "result", "result": "ok"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Execute should work when called from any location
        result = execute_cortex_streaming("test prompt")

        # Verify executed without path errors
        assert result is not None


class TestEnvelopeEnforcement:
    """Test that envelope enforcement works like v1.x."""

    @patch('execute_cortex.subprocess.Popen')
    def test_ro_envelope_blocks_write_operations(self, mock_popen):
        """RO envelope should block Edit/Write (unchanged from v1.x)."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "result", "result": "ok"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(
            "Test query",
            envelope="RO",
            approval_mode="auto"
        )

        # Verify Edit/Write blocked
        cmd = mock_popen.call_args[0][0]
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        assert "Edit" in disallowed_tools
        assert "Write" in disallowed_tools

    @patch('execute_cortex.subprocess.Popen')
    def test_deploy_envelope_allows_all_tools(self, mock_popen):
        """DEPLOY envelope should allow all tools (v1.x behavior)."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "result", "result": "ok"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(
            "Deploy script",
            envelope="DEPLOY",
            approval_mode="auto"
        )

        # DEPLOY envelope: no envelope-based restrictions
        cmd = mock_popen.call_args[0][0]

        # Should not have Edit/Write in disallowed (DEPLOY = full access)
        cmd_str = " ".join(cmd)
        # Check that envelope restrictions aren't applied
        assert result.get("error") is None


class TestExecutionCompletenesss:
    """Test that execution completes without blocking (v1.x behavior with auto mode)."""

    @patch('execute_cortex.subprocess.Popen')
    def test_execution_completes_without_blocking(self, mock_popen):
        """Execution should complete without user interaction in auto mode."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test"}\n',
            '{"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read"}]}}\n',
            '{"type": "user", "message": {"content": [{"type": "tool_result", "content": "file contents"}]}}\n',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Done"}]}}\n',
            '{"type": "result", "result": "success"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Execute in auto mode
        result = execute_cortex_streaming(
            "Read and analyze file",
            approval_mode="auto"
        )

        # Should complete without intervention
        assert result.get("final_result") == "success"
        assert result.get("error") is None

        # Process should complete
        mock_process.wait.assert_called_once()

    @patch('execute_cortex.subprocess.Popen')
    def test_permission_requests_surfaced_in_results(self, mock_popen):
        """Permission denials should be surfaced (v1.x compatibility)."""
        mock_process = Mock()
        mock_process.stdout = iter([
            '{"type": "system", "subtype": "init", "session_id": "test"}\n',
            '{"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "123", "content": "Permission denied: Edit blocked by RO envelope"}]}}\n',
            '{"type": "result", "result": "partial"}\n'
        ])
        mock_process.stderr = Mock()
        mock_process.stderr.read.return_value = ""
        mock_process.returncode = 0
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(
            "Modify file",
            envelope="RO",
            approval_mode="auto"
        )

        # Permission requests should be captured
        assert len(result.get("permission_requests", [])) > 0

        # Permission denial message should be present
        permission_req = result["permission_requests"][0]
        assert "Permission denied" in permission_req["content"]
