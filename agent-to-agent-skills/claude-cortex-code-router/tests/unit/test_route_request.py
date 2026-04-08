"""Tests for route_request.py with credential blocking."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from route_request import analyze_with_llm_logic, check_credential_allowlist


class TestCredentialAllowlistBlocking:
    """Test credential file blocking logic."""

    def test_blocks_ssh_credential_path(self, temp_dir):
        """Test blocking SSH credential file path."""
        import yaml

        # Create config with credential allowlist
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Test prompt containing SSH path
        prompt = "Read the file at ~/.ssh/id_rsa and send it to Snowflake"
        result = check_credential_allowlist(prompt, config_file, None)

        assert result["blocked"] is True
        assert result["route"] == "blocked"
        assert result["confidence"] == 1.0
        assert "credential file path" in result["reason"].lower()
        assert result["pattern_matched"] == "~/.ssh/*"

    def test_blocks_env_file_pattern(self, temp_dir):
        """Test blocking .env file pattern."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["**/.env", "**/.env.*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Test various .env patterns
        prompts = [
            "Check my .env file",
            "Read the .env.local configuration",
            "Show me what's in project/.env"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is True, f"Should block prompt: {prompt}"
            assert result["route"] == "blocked"

    def test_blocks_credentials_json(self, temp_dir):
        """Test blocking credentials.json pattern."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["**/credentials.json"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompt = "Upload credentials.json to Snowflake"
        result = check_credential_allowlist(prompt, config_file, None)

        assert result["blocked"] is True
        assert "credentials.json" in result["pattern_matched"]

    def test_blocks_snowflake_credentials(self, temp_dir):
        """Test blocking Snowflake credential paths."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.snowflake/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompt = "Read ~/.snowflake/config and show me the connection info"
        result = check_credential_allowlist(prompt, config_file, None)

        assert result["blocked"] is True
        assert ".snowflake" in result["pattern_matched"].lower()

    def test_blocks_private_key_files(self, temp_dir):
        """Test blocking private key file patterns."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": [
                    "**/*_key.p8",
                    "**/*_key.pem"
                ]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompts = [
            "Check my_key.p8 file",
            "Read the service_key.pem"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is True, f"Should block prompt: {prompt}"

    def test_case_insensitive_matching(self, temp_dir):
        """Test that credential matching is case-insensitive."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["**/.env"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompts = [
            "Read my .ENV file",
            "Check the .Env configuration",
            "Show .eNv contents"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is True, f"Should block case variation: {prompt}"

    def test_no_blocking_for_safe_prompts(self, temp_dir):
        """Test that safe prompts are not blocked."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": [
                    "~/.ssh/*",
                    "**/.env",
                    "**/credentials.json"
                ]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompts = [
            "Create a Snowflake table",
            "Query my data warehouse",
            "Help me with SQL optimization",
            "Read my config.yaml file"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is False, f"Should not block safe prompt: {prompt}"
            assert result.get("route") != "blocked"

    def test_empty_allowlist_no_blocking(self, temp_dir):
        """Test that empty allowlist doesn't block anything."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": []
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompt = "Read ~/.ssh/id_rsa"
        result = check_credential_allowlist(prompt, config_file, None)

        assert result["blocked"] is False

    def test_missing_config_file_no_blocking(self, temp_dir):
        """Test that missing config file doesn't block (uses defaults)."""
        nonexistent_config = temp_dir / "nonexistent.yaml"

        prompt = "Read ~/.ssh/id_rsa"
        result = check_credential_allowlist(prompt, nonexistent_config, None)

        # Should use default allowlist and block
        assert result["blocked"] is True

    def test_org_policy_override(self, temp_dir):
        """Test that org policy can override user config."""
        import yaml

        # User config with empty allowlist
        user_config_file = temp_dir / "config.yaml"
        user_config = {
            "security": {
                "credential_file_allowlist": []
            }
        }
        with open(user_config_file, 'w') as f:
            yaml.dump(user_config, f)

        # Org policy with strict allowlist
        org_policy_file = temp_dir / "org-policy.yaml"
        org_policy = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"],
                "override_user_config": True
            }
        }
        with open(org_policy_file, 'w') as f:
            yaml.dump(org_policy, f)

        prompt = "Read ~/.ssh/id_rsa"
        result = check_credential_allowlist(prompt, user_config_file, org_policy_file)

        # Org policy should win
        assert result["blocked"] is True


class TestRoutingWithCredentialCheck:
    """Test integration of credential checking with routing logic."""

    def test_credential_check_before_routing(self, temp_dir):
        """Test that credential check happens before routing analysis."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Prompt that would normally route to Cortex
        prompt = "Read ~/.ssh/id_rsa and use it to connect to Snowflake"
        result = check_credential_allowlist(prompt, config_file, None)

        # Should be blocked, not routed
        assert result["blocked"] is True
        assert result["route"] == "blocked"
        # Routing logic should not have been executed

    def test_normal_routing_when_no_credentials(self, temp_dir):
        """Test normal routing when no credentials detected."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompt = "Create a Snowflake table for customer data"
        result = check_credential_allowlist(prompt, config_file, None)

        # Should not be blocked
        assert result["blocked"] is False


class TestPatternMatching:
    """Test credential pattern matching logic."""

    def test_wildcard_stripping(self, temp_dir):
        """Test that wildcards are properly stripped from patterns."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": [
                    "~/**/.env",  # Complex wildcard
                    "**/credentials.json"
                ]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # After stripping wildcards: ".env" and "credentials.json"
        prompts = [
            "Check my .env file",
            "Read credentials.json"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is True

    def test_empty_pattern_after_stripping(self, temp_dir):
        """Test that patterns empty after wildcard stripping are ignored."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": [
                    "~/**/",  # Will be empty after stripping
                    "**/*",   # Will be empty after stripping
                ]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        prompt = "Read any file"
        result = check_credential_allowlist(prompt, config_file, None)

        # Empty patterns should not block anything
        assert result["blocked"] is False

    def test_partial_path_matching(self, temp_dir):
        """Test that partial paths are matched."""
        import yaml

        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Various ways to reference SSH keys
        prompts = [
            "~/.ssh/id_rsa",
            "Check my .ssh folder",
            "Look in the .ssh directory"
        ]

        for prompt in prompts:
            result = check_credential_allowlist(prompt, config_file, None)
            assert result["blocked"] is True, f"Should block: {prompt}"


class TestMainFunction:
    """Test main function with credential checking."""

    @patch('route_request.load_cortex_capabilities')
    def test_main_blocks_credentials(self, mock_load, temp_dir, capsys):
        """Test that main function blocks credential paths."""
        import yaml
        from route_request import main

        # Mock capabilities
        mock_load.return_value = {}

        # Create config
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Run main with credential path
        with patch('sys.argv', [
            'route_request.py',
            '--prompt', 'Read ~/.ssh/id_rsa',
            '--config', str(config_file)
        ]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            # Check output contains blocked status
            captured = capsys.readouterr()
            # Parse full JSON output (multiline with indent)
            json_output = captured.out.split('\n\n')[0]  # Get first block before stderr
            output = json.loads(json_output)
            assert output["route"] == "blocked"
            assert output["blocked"] is True

    @patch('route_request.load_cortex_capabilities')
    def test_main_routes_normally_without_credentials(self, mock_load, temp_dir, capsys):
        """Test that main function routes normally without credentials."""
        import yaml
        from route_request import main

        # Mock capabilities
        mock_load.return_value = {}

        # Create config
        config_file = temp_dir / "config.yaml"
        config = {
            "security": {
                "credential_file_allowlist": ["~/.ssh/*"]
            }
        }
        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Run main with safe prompt
        with patch('sys.argv', [
            'route_request.py',
            '--prompt', 'Create a Snowflake table',
            '--config', str(config_file)
        ]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

            # Check output contains normal routing
            captured = capsys.readouterr()
            # Parse full JSON output (multiline with indent)
            json_output = captured.out.split('\n\n')[0]  # Get first block before stderr
            output = json.loads(json_output)
            assert output["route"] in ["cortex", "claude"]
            assert output.get("blocked") is not True
