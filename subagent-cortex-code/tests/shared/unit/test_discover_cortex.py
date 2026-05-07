"""
Unit tests for discover_cortex.py module.

Tests skill discovery, parsing, metadata extraction, and caching.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from shared.scripts.discover_cortex import (
    run_command,
    discover_cortex_skills,
    read_skill_metadata,
    parse_skill_md,
    extract_triggers
)


@pytest.mark.unit
def test_run_command_success():
    """Test successful command execution."""
    with patch('shared.scripts.discover_cortex.subprocess.run') as mock_run:
        mock_run.return_value.stdout = "output"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        stdout, stderr, code = run_command("echo test")

        assert stdout == "output"
        assert stderr == ""
        assert code == 0


@pytest.mark.unit
def test_run_command_uses_shell_false():
    """Discovery should not use shell=True for fixed cortex commands."""
    with patch('shared.scripts.discover_cortex.subprocess.run') as mock_run:
        mock_run.return_value.stdout = "output"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        run_command(["cortex", "skill", "list"])

        assert mock_run.call_args.kwargs["shell"] is False
        assert mock_run.call_args.args[0] == ["cortex", "skill", "list"]


@pytest.mark.unit
def test_run_command_failure():
    """Test command execution failure."""
    with patch('shared.scripts.discover_cortex.subprocess.run') as mock_run:
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "error message"
        mock_run.return_value.returncode = 1

        stdout, stderr, code = run_command("invalid_command")

        assert stdout == ""
        assert stderr == "error message"
        assert code == 1


@pytest.mark.unit
def test_run_command_timeout():
    """Test command timeout handling."""
    import subprocess

    with patch('shared.scripts.discover_cortex.subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)

        stdout, stderr, code = run_command("long_running_command")

        assert stdout == ""
        assert stderr == "Command timed out"
        assert code == 1


@pytest.mark.unit
def test_discover_cortex_skills_new_format(mock_cortex_output_new_format):
    """Test skill discovery with v1.0.50+ format."""
    with patch('shared.scripts.discover_cortex.run_command', return_value=(mock_cortex_output_new_format, "", 0)):
        with patch('shared.scripts.discover_cortex.read_skill_metadata') as mock_read:
            # Mock successful metadata read
            mock_read.return_value = {
                "name": "Test Skill",
                "description": "Test description",
                "triggers": ["test trigger"]
            }

            skills = discover_cortex_skills()

            # Should discover all skills from new format
            assert isinstance(skills, dict)
            # Should have called read_skill_metadata for each skill
            assert mock_read.call_count >= 3  # At least 3 skills in new format
            assert set(skills) >= {"snowflake-query", "data-quality", "cortex-search"}


@pytest.mark.unit
def test_discover_cortex_skills_old_format(mock_cortex_output_old_format):
    """Test skill discovery with pre-v1.0.50 format."""
    with patch('shared.scripts.discover_cortex.run_command', return_value=(mock_cortex_output_old_format, "", 0)):
        with patch('shared.scripts.discover_cortex.read_skill_metadata') as mock_read:
            mock_read.return_value = {
                "name": "Test Skill",
                "description": "Test description",
                "triggers": []
            }

            skills = discover_cortex_skills()

            assert isinstance(skills, dict)
            # Should have called read_skill_metadata for each skill (3 in old format)
            assert mock_read.call_count == 3


@pytest.mark.unit
def test_discover_cortex_skills_command_failure():
    """Test skill discovery when cortex command fails."""
    with patch('shared.scripts.discover_cortex.run_command', return_value=("", "command failed", 1)):
        skills = discover_cortex_skills()

        # Should return empty dict on failure
        assert skills == {}


@pytest.mark.unit
def test_parse_skill_md_valid():
    """Test parsing valid SKILL.md with frontmatter."""
    skill_content = """---
name: "Test Skill"
description: "This is a test skill for unit testing"
---

# Test Skill

Use when: working with test data
Use for: testing purposes

Additional content here.
"""

    with patch('builtins.open', mock_open(read_data=skill_content)):
        result = parse_skill_md(Path("/fake/path/SKILL.md"))

        assert result is not None
        assert result["name"] == "Test Skill"
        assert result["description"] == "This is a test skill for unit testing"
        assert isinstance(result["triggers"], list)


@pytest.mark.unit
def test_extract_triggers():
    """Test extraction of trigger phrases from skill content."""
    content = """
Use when: working with databases
Use for: data analysis
When to use: querying data

Additional content.
- Use when: creating reports
"""

    triggers = extract_triggers(content)

    assert isinstance(triggers, list)
    assert len(triggers) > 0
    # Should limit to 10 triggers
    assert len(triggers) <= 10
