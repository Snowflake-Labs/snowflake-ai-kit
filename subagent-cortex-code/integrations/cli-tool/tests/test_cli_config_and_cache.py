"""Regression tests for cortexcode-tool config and cache hardening."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cortexcode_tool.security.cache_manager import CacheManager
from cortexcode_tool.main import main, parse_args, should_request_codex_escalation


def test_cli_example_config_defaults_to_prompt():
    config = yaml.safe_load(Path("integrations/cli-tool/config.yaml.example").read_text())

    assert config["security"]["approval_mode"] == "prompt"


def test_cli_setup_writes_prompt_default():
    setup_text = Path("integrations/cli-tool/setup.sh").read_text()

    assert 'approval_mode: "prompt"' in setup_text
    assert 'approval_mode: "auto"' not in setup_text


def test_cli_setup_secures_install_and_bin_dirs():
    setup_text = Path("integrations/cli-tool/setup.sh").read_text()

    assert 'chmod 700 "$INSTALL_DIR"' in setup_text
    assert 'chmod 700 "$BIN_DIR"' in setup_text
    assert 'chmod 700 "$CONFIG_DIR"' in setup_text


def test_codex_install_secures_install_lib_dir():
    install_text = Path("integrations/codex/install.sh").read_text()

    assert 'chmod 700 "$INSTALL_LIB_DIR"' in install_text


def test_codex_cli_config_defaults_to_prompt():
    config = yaml.safe_load(Path("integrations/codex/cortexcode-tool-codex.yaml").read_text())

    assert config["security"]["approval_mode"] == "prompt"


def test_cli_supports_explicit_yes_after_host_approval():
    args = parse_args(["--yes", "--envelope", "RO", "How many databases?"])

    assert args.yes is True
    assert args.envelope == "RO"
    assert args.query == "How many databases?"


def test_codex_skill_uses_yes_flag_after_host_approval():
    skill_text = Path("integrations/codex/SKILL.md").read_text()

    assert "--yes" in skill_text
    assert "Ask the user for approval in Codex" in skill_text


def test_cli_cache_directory_chmod_failure_is_nonfatal(tmp_path):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    with pytest.warns(RuntimeWarning, match="Could not set secure permissions"):
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(os, "chmod", lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("denied")))
            cache = CacheManager(cache_dir)

    assert cache.cache_dir == cache_dir


def test_codex_network_disabled_sandbox_requests_host_escalation(monkeypatch):
    monkeypatch.setenv("CODEX_SANDBOX_NETWORK_DISABLED", "1")

    assert should_request_codex_escalation(approved=False) is True


def test_codex_sandbox_guard_allows_yes_after_host_approval(monkeypatch):
    monkeypatch.setenv("CODEX_SANDBOX_NETWORK_DISABLED", "1")

    assert should_request_codex_escalation(approved=True) is False


@patch("cortexcode_tool.main.execute_query")
@patch("cortexcode_tool.main.CacheManager")
@patch("cortexcode_tool.main.ConfigManager")
def test_cli_honors_explicit_envelope_argument(mock_config_manager, mock_cache_manager, mock_execute_query):
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "security.cache_dir": None,
        "security.approval_mode": "prompt",
        "cortex.default_envelope": "RW",
    }.get(key, default)
    mock_config_manager.return_value = config
    mock_cache_manager.return_value = MagicMock()
    mock_execute_query.return_value = 0

    assert main(["--envelope", "RO", "--yes", "How many databases?"]) == 0

    mock_execute_query.assert_called_once()
    assert mock_execute_query.call_args.kwargs["envelope"] == "RO"


@patch("cortexcode_tool.main.execute_query")
@patch("cortexcode_tool.main.CacheManager")
@patch("cortexcode_tool.main.ConfigManager")
def test_cli_rejects_none_envelope_before_execution(mock_config_manager, mock_cache_manager, mock_execute_query, capsys):
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "security.cache_dir": None,
        "security.approval_mode": "prompt",
        "cortex.default_envelope": "RW",
    }.get(key, default)
    mock_config_manager.return_value = config
    mock_cache_manager.return_value = MagicMock()

    assert main(["--envelope", "NONE", "--yes", "How many databases?"]) == 1

    mock_execute_query.assert_not_called()
    assert "NONE envelope is not allowed" in capsys.readouterr().err


@patch("cortexcode_tool.main.execute_query")
@patch("cortexcode_tool.main.CacheManager")
@patch("cortexcode_tool.main.ConfigManager")
def test_cli_rejects_envelope_outside_allowed_list_before_execution(
    mock_config_manager,
    mock_cache_manager,
    mock_execute_query,
    capsys,
):
    config = MagicMock()
    config.get.side_effect = lambda key, default=None: {
        "security.cache_dir": None,
        "security.approval_mode": "prompt",
        "security.allowed_envelopes": ["RO"],
        "cortex.default_envelope": "RO",
    }.get(key, default)
    mock_config_manager.return_value = config
    mock_cache_manager.return_value = MagicMock()

    assert main(["--envelope", "DEPLOY", "--yes", "How many databases?"]) == 1

    mock_execute_query.assert_not_called()
    assert "Envelope DEPLOY is not allowed" in capsys.readouterr().err
