"""Tests for config_manager.py"""
import pytest
from pathlib import Path
from security.config_manager import ConfigManager


def test_load_default_config():
    """Test loading default configuration."""
    config = ConfigManager()

    # Should have default approval mode
    assert config.get("security.approval_mode") == "prompt"
    assert config.get("security.allowed_envelopes") == ["RO", "RW", "RESEARCH"]


def test_load_user_config(mock_config_dir, sample_config):
    """Test loading user configuration."""
    import yaml

    # Create user config file
    config_file = mock_config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(sample_config, f)

    config = ConfigManager(config_path=config_file)

    assert config.get("security.approval_mode") == "prompt"
    assert config.get("security.audit_log_path") == str(mock_config_dir / "audit.log")


def test_org_policy_override(mock_config_dir, temp_dir):
    """Test org policy overrides user config."""
    import yaml

    # Create user config (approval_mode: auto)
    user_config = {"security": {"approval_mode": "auto"}}
    user_config_file = mock_config_dir / "config.yaml"
    with open(user_config_file, 'w') as f:
        yaml.dump(user_config, f)

    # Create org policy (approval_mode: prompt, override: true)
    org_policy_dir = temp_dir / ".snowflake" / "cortex"
    org_policy_dir.mkdir(parents=True)
    org_policy = {
        "security": {
            "approval_mode": "prompt",
            "override_user_config": True
        }
    }
    org_policy_file = org_policy_dir / "claude-skill-policy.yaml"
    with open(org_policy_file, 'w') as f:
        yaml.dump(org_policy, f)

    config = ConfigManager(
        config_path=user_config_file,
        org_policy_path=org_policy_file
    )

    # Org policy should win
    assert config.get("security.approval_mode") == "prompt"


def test_malformed_yaml_fallback(mock_config_dir, tmp_path, capsys):
    """Verify fallback to defaults when config file contains invalid YAML."""
    config_file = mock_config_dir / "config.yaml"
    config_file.write_text("invalid: yaml: content: [")

    config = ConfigManager(config_path=config_file)

    # Should fall back to defaults
    assert config.get("security.approval_mode") == "prompt"

    # Should print warning to stderr
    captured = capsys.readouterr()
    assert "Failed to parse" in captured.err or "Warning" in captured.err


def test_file_permission_error_fallback(mock_config_dir, tmp_path, capsys):
    """Verify fallback when config file is not readable."""
    config_file = mock_config_dir / "config.yaml"
    config_file.write_text("security:\n  approval_mode: auto\n")
    config_file.chmod(0o000)  # Remove all permissions

    try:
        config = ConfigManager(config_path=config_file)

        # Should fall back to defaults
        assert config.get("security.approval_mode") == "prompt"

        # Should print warning to stderr
        captured = capsys.readouterr()
        assert "Failed to read" in captured.err or "Warning" in captured.err
    finally:
        config_file.chmod(0o644)  # Restore permissions for cleanup


def test_empty_config_file(mock_config_dir):
    """Verify yaml.safe_load returning None is handled."""
    config_file = mock_config_dir / "config.yaml"
    config_file.write_text("")  # Empty file

    config = ConfigManager(config_path=config_file)

    # Should use defaults (empty file means no overrides)
    assert config.get("security.approval_mode") == "prompt"


def test_org_policy_merge_without_override(mock_config_dir, temp_dir):
    """Verify org policy merges with user config when override_user_config is False."""
    import yaml

    # User config
    user_config_path = mock_config_dir / "config.yaml"
    user_config_path.write_text("""
security:
  approval_mode: auto
  max_concurrent_executions: 5
""")

    # Org policy (no override flag, so it merges)
    org_policy_path = temp_dir / "org_policy.yaml"
    org_policy_path.write_text("""
security:
  allowed_envelopes: ["RO"]
""")

    config = ConfigManager(config_path=user_config_path, org_policy_path=org_policy_path)

    # Both user config and org policy values should be present
    assert config.get("security.approval_mode") == "auto"  # From user config
    assert config.get("security.allowed_envelopes") == ["RO"]  # From org policy
    assert config.get("security.max_concurrent_executions") == 5  # From user config


def test_get_missing_key():
    """Verify default return value for missing key."""
    config = ConfigManager()
    assert config.get("nonexistent.key", "default_value") == "default_value"
    assert config.get("nonexistent.key") is None


def test_validate_approval_mode(mock_config_dir):
    """Test that invalid approval_mode raises ConfigValidationError."""
    import yaml
    from security.config_manager import ConfigValidationError

    # Create config with invalid approval_mode
    invalid_config = {"security": {"approval_mode": "invalid_mode"}}
    config_file = mock_config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(invalid_config, f)

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError, match="Invalid approval_mode"):
        ConfigManager(config_path=config_file)


def test_validate_envelope_list(mock_config_dir):
    """Test that invalid envelope raises ConfigValidationError."""
    import yaml
    from security.config_manager import ConfigValidationError

    # Create config with invalid envelope
    invalid_config = {"security": {"allowed_envelopes": ["RO", "INVALID_ENVELOPE"]}}
    config_file = mock_config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(invalid_config, f)

    # Should raise ConfigValidationError
    with pytest.raises(ConfigValidationError, match="Invalid envelope"):
        ConfigManager(config_path=config_file)


def test_validate_file_paths(mock_config_dir):
    """Test that ~/ in paths gets expanded."""
    import yaml
    import os

    # Create config with ~/ path
    config_with_tilde = {
        "security": {
            "audit_log_path": "~/test_audit.log",
            "cache_dir": "~/test_cache"
        }
    }
    config_file = mock_config_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_with_tilde, f)

    config = ConfigManager(config_path=config_file)

    # Paths should be expanded
    audit_path = config.get("security.audit_log_path")
    cache_dir = config.get("security.cache_dir")

    assert audit_path.startswith(os.path.expanduser("~"))
    assert not audit_path.startswith("~/")
    assert cache_dir.startswith(os.path.expanduser("~"))
    assert not cache_dir.startswith("~/")


def test_validate_confidence_threshold_range():
    """Test confidence threshold range validation."""
    from security.config_manager import ConfigManager, ConfigValidationError
    import yaml
    import tempfile

    # Test value > 1
    invalid_config = {"security": {"tool_prediction_confidence_threshold": 1.5}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="must be between 0 and 1"):
            ConfigManager(config_path=config_path)
    finally:
        config_path.unlink()

    # Test value < 0
    invalid_config = {"security": {"tool_prediction_confidence_threshold": -0.1}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="must be between 0 and 1"):
            ConfigManager(config_path=config_path)
    finally:
        config_path.unlink()

    # Test non-numeric value
    invalid_config = {"security": {"tool_prediction_confidence_threshold": "high"}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="must be a number"):
            ConfigManager(config_path=config_path)
    finally:
        config_path.unlink()


def test_validate_retention_value():
    """Test audit log retention validation."""
    from security.config_manager import ConfigManager, ConfigValidationError
    import yaml
    import tempfile

    # Test negative value
    invalid_config = {"security": {"audit_log_retention": -5}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="must be >= 0"):
            ConfigManager(config_path=config_path)
    finally:
        config_path.unlink()

    # Test non-integer value
    invalid_config = {"security": {"audit_log_retention": "forever"}}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        config_path = Path(f.name)

    try:
        with pytest.raises(ConfigValidationError, match="must be an integer"):
            ConfigManager(config_path=config_path)
    finally:
        config_path.unlink()
