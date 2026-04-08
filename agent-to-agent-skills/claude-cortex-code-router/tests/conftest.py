"""Pytest configuration and shared fixtures."""
import os
import tempfile
import shutil
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def mock_config_dir(temp_dir):
    """Create mock config directory structure."""
    config_dir = temp_dir / ".claude" / "skills" / "cortex-code"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def mock_cache_dir(temp_dir):
    """Create mock cache directory."""
    cache_dir = temp_dir / ".cache" / "cortex-skill"
    cache_dir.mkdir(parents=True)
    return cache_dir


@pytest.fixture
def sample_config(mock_config_dir, mock_cache_dir):
    """Return sample configuration dictionary with temp paths."""
    return {
        "security": {
            "approval_mode": "prompt",
            "audit_log_path": str(mock_config_dir / "audit.log"),
            "audit_log_rotation": "10MB",
            "audit_log_retention": 30,
            "sanitize_conversation_history": True,
            "sanitize_session_files": True,
            "max_history_items": 3,
            "cache_dir": str(mock_cache_dir),
            "cache_permissions": "0600",
            "allowed_envelopes": ["RO", "RW", "RESEARCH"],
            "deploy_envelope_confirmation": True,
            "credential_file_allowlist": [
                "~/.ssh/*",
                "~/.snowflake/*",
                "**/.env",
                "**/credentials.json"
            ]
        }
    }
