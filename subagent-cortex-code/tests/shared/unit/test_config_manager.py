"""
Unit tests for config_manager.py module.

Tests 3-layer precedence, validation, path expansion, and configuration merging.
"""

import pytest
from pathlib import Path
from shared.security.config_manager import ConfigManager, ConfigValidationError


@pytest.mark.unit
def test_default_config_loaded():
    """Test default configuration is loaded when no config file exists."""
    config_manager = ConfigManager()

    # Should have default values
    assert config_manager.get("security.approval_mode") == "prompt"
    assert config_manager.get("security.tool_prediction_confidence_threshold") == 0.7
    assert config_manager.get("security.allowed_envelopes") == ["RO", "RW", "RESEARCH"]


@pytest.mark.unit
def test_user_config_overrides_defaults(tmp_path):
    """Test user config overrides default values."""
    # Create user config
    config_path = tmp_path / "user_config.yaml"
    config_content = """
security:
  approval_mode: "auto"
  tool_prediction_confidence_threshold: 0.8
"""
    config_path.write_text(config_content)

    config_manager = ConfigManager(config_path=config_path)

    # User config should not relax the security floor without org policy
    assert config_manager.get("security.approval_mode") == "prompt"
    assert config_manager.get("security.tool_prediction_confidence_threshold") == 0.8
    # Non-overridden values should still have defaults
    assert config_manager.get("security.allowed_envelopes") == ["RO", "RW", "RESEARCH"]


@pytest.mark.unit
def test_org_policy_overrides_user_config(tmp_path):
    """Test org policy has highest precedence."""
    # Create user config
    user_config_path = tmp_path / "user_config.yaml"
    user_config_content = """
security:
  approval_mode: "auto"
  tool_prediction_confidence_threshold: 0.9
"""
    user_config_path.write_text(user_config_content)

    # Create org policy
    org_policy_path = tmp_path / "org_policy.yaml"
    org_policy_content = """
security:
  approval_mode: "prompt"
  allowed_envelopes: ["RO"]
"""
    org_policy_path.write_text(org_policy_content)

    config_manager = ConfigManager(
        config_path=user_config_path,
        org_policy_path=org_policy_path
    )

    # Org policy should override user config
    assert config_manager.get("security.approval_mode") == "prompt"
    assert config_manager.get("security.allowed_envelopes") == ["RO"]
    # User config values not in org policy should still apply
    assert config_manager.get("security.tool_prediction_confidence_threshold") == 0.9


@pytest.mark.unit
def test_validation_invalid_approval_mode(tmp_path):
    """Test validation fails on invalid approval mode."""
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  approval_mode: "invalid_mode"
"""
    config_path.write_text(config_content)

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigManager(config_path=config_path)

    assert "Invalid approval_mode" in str(exc_info.value)


@pytest.mark.unit
def test_validation_invalid_envelope(tmp_path):
    """Test validation fails on invalid envelope."""
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  allowed_envelopes: ["RO", "INVALID_ENVELOPE"]
"""
    config_path.write_text(config_content)

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigManager(config_path=config_path)

    assert "Invalid envelope" in str(exc_info.value)


@pytest.mark.unit
def test_validation_confidence_threshold_out_of_range(tmp_path):
    """Test validation fails when confidence threshold out of range."""
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  tool_prediction_confidence_threshold: 1.5
"""
    config_path.write_text(config_content)

    with pytest.raises(ConfigValidationError) as exc_info:
        ConfigManager(config_path=config_path)

    assert "must be between 0 and 1" in str(exc_info.value)


@pytest.mark.unit
def test_path_expansion(tmp_path):
    """Test path expansion for tilde and environment variables."""
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  audit_log_path: "~/test_audit.log"
  cache_dir: "~/.cache/test-cortex"
"""
    config_path.write_text(config_content)

    config_manager = ConfigManager(config_path=config_path)

    # Paths should be expanded
    audit_path = config_manager.get("security.audit_log_path")
    cache_dir = config_manager.get("security.cache_dir")

    assert "~" not in audit_path
    assert "~" not in cache_dir
    # Should contain user home directory
    assert str(Path.home()) in audit_path
    assert str(Path.home()) in cache_dir
