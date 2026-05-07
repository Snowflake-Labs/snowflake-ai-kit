"""Tests for Codex integration install script."""

import pytest
from pathlib import Path


@pytest.mark.integration
def test_codex_install_target_directory():
    """Codex install should target the cortexcode-tool CLI package."""
    target = Path.home() / ".local" / "lib" / "cortexcode-tool"
    assert ".local" in str(target)
    assert "cortexcode-tool" in str(target)


@pytest.mark.integration
def test_codex_cli_config_exists():
    """Codex ships a CLI config template."""
    assert Path("integrations/codex/cortexcode-tool-codex.yaml").exists()


@pytest.mark.integration
def test_codex_setup_guidance():
    """Codex has setup_guidance.md"""
    assert Path("integrations/codex/setup_guidance.md").exists()


@pytest.mark.integration
def test_codex_installer_mentions_yes_flag():
    """Codex docs should instruct agents to use --yes only after approval."""
    install_text = Path("integrations/codex/install.sh").read_text()
    assert "--yes" in install_text
    assert "Use --yes only after Codex chat approval" in install_text
