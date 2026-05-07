"""Shared pytest fixtures for all test modules."""

import pytest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for test isolation."""
    return tmp_path


@pytest.fixture
def mock_cortex_output_old_format():
    """Mock cortex skill list (pre-v1.0.50 format)."""
    return """snowflake-query /path/to/skill
data-quality /path/to/skill
cortex-search /path/to/skill"""


@pytest.fixture
def mock_cortex_output_new_format():
    """Mock cortex skill list (v1.0.50+ format with headers)."""
    return """[BUNDLED]
  - snowflake-query: /path/to/bundled/snowflake-query
  - data-quality: /path/to/bundled/data-quality
  - cortex-search: /path/to/bundled/cortex-search
[PROJECT]
  - custom-skill: /path/to/project/custom-skill
[GLOBAL]
  - global-skill: /path/to/global/global-skill"""


@pytest.fixture(params=["claude", "cursor", "codex"])
def coding_agent(request):
    """Parametrized fixture for all coding agents."""
    return request.param


@pytest.fixture
def mock_config_manager(tmp_path):
    """Mock ConfigManager with test defaults."""
    from shared.security.config_manager import ConfigManager

    # Create temp config file
    config_path = tmp_path / "config.yaml"
    config_content = """
security:
  approval_mode: "auto"
  audit_log_path: "~/test_audit.log"
  cache_dir: "~/.cache/test-cortex"
  sanitize_conversation_history: true
  tool_prediction_confidence_threshold: 0.7
  allowed_envelopes: ["RO", "RW", "RESEARCH"]
  credential_file_allowlist:
    - "~/.ssh/**"
    - "**/.env"
"""
    config_path.write_text(config_content)

    return ConfigManager(config_path=config_path)


@pytest.fixture
def mock_audit_logger(tmp_path):
    """Mock AuditLogger writing to temp file."""
    from shared.security.audit_logger import AuditLogger

    log_path = tmp_path / "test_audit.log"
    return AuditLogger(log_path=log_path, rotation_size="1MB", retention_days=7)


@pytest.fixture
def mock_subprocess_popen():
    """Mock subprocess.Popen for cortex CLI calls."""
    mock = MagicMock()
    mock.return_value.stdout = iter([])
    mock.return_value.stderr = MagicMock()
    mock.return_value.wait.return_value = 0
    mock.return_value.returncode = 0
    return mock
