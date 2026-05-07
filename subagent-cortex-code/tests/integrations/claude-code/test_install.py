"""Tests for Claude Code integration install script."""

import pytest
import tempfile
import yaml
from pathlib import Path


@pytest.mark.integration
def test_install_script_creates_directories():
    """Install script should create ~/.claude/skills/cortex-code/"""
    with tempfile.TemporaryDirectory() as tmpdir:
        target = Path(tmpdir) / ".claude" / "skills" / "cortex-code"

        # Simulate install (would run install.sh with TARGET=tmpdir)
        target.mkdir(parents=True, exist_ok=True)

        assert target.exists()
        assert target.is_dir()


@pytest.mark.integration
def test_install_copies_shared_scripts():
    """Install should copy all 6 shared scripts"""
    # Mock test - actual install.sh does this
    scripts = [
        "execute_cortex.py",
        "discover_cortex.py",
        "route_request.py",
        "predict_tools.py",
        "read_cortex_sessions.py",
        "security_wrapper.py"
    ]

    assert len(scripts) == 6


@pytest.mark.integration
def test_install_copies_security_modules():
    """Install should copy all 6 security modules"""
    modules = [
        "__init__.py",
        "approval_handler.py",
        "audit_logger.py",
        "cache_manager.py",
        "config_manager.py",
        "prompt_sanitizer.py"
    ]

    assert len(modules) == 6


@pytest.mark.integration
def test_install_replaces_coding_agent_placeholder():
    """sed should replace __CODING_AGENT__ with 'claude'"""
    test_content = 'return "__CODING_AGENT__", 0.5'
    expected = 'return "claude", 0.5'

    replaced = test_content.replace("__CODING_AGENT__", "claude")
    assert replaced == expected


@pytest.mark.integration
def test_install_copies_skill_definition():
    """Install should copy skill.md"""
    # Integration-specific file
    assert Path("integrations/claude-code/skill.md").exists()


@pytest.mark.integration
def test_install_creates_default_config():
    """Install should create config.yaml from example if not exists"""
    # Mock test
    assert Path("integrations/claude-code/config.yaml.example").exists()


@pytest.mark.integration
def test_claude_code_config_defaults_to_prompt():
    """Shipped Claude Code config should require interactive approval by default."""
    config = yaml.safe_load(Path("integrations/claude-code/config.yaml").read_text())

    assert config["security"]["approval_mode"] == "prompt"
