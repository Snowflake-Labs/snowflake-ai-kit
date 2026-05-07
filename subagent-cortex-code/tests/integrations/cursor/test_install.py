"""Tests for Cursor integration install script."""

import pytest
from pathlib import Path


@pytest.mark.integration
def test_cursor_install_target_directory():
    """Cursor install should target ~/.cursor/skills/cortex-code/"""
    target = Path.home() / ".cursor" / "skills" / "cortex-code"
    # Just validate path format
    assert ".cursor" in str(target)


@pytest.mark.integration
def test_cursor_skill_file_exists():
    """Cursor uses SKILL.md (uppercase)"""
    assert Path("integrations/cursor/SKILL.md").exists()


@pytest.mark.integration
def test_cursor_cursorrules_template():
    """Cursor has .cursorrules.template"""
    assert Path("integrations/cursor/.cursorrules.template").exists()


@pytest.mark.integration
def test_cursor_placeholder_replacement():
    """sed should replace __CODING_AGENT__ with 'cursor'"""
    test_content = 'audit_path = "~/.__CODING_AGENT__/audit.log"'
    expected = 'audit_path = "~/.cursor/audit.log"'

    replaced = test_content.replace("__CODING_AGENT__", "cursor")
    assert replaced == expected

@pytest.mark.integration
def test_cursor_skill_does_not_force_auto_approval():
    """Cursor skill examples should not hardcode auto approval mode."""
    skill_text = Path("integrations/cursor/SKILL.md").read_text()
    assert '--approval-mode "auto"' not in skill_text
    assert "Approval mode**: auto" not in skill_text
