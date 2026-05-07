"""Regression tests for cortexcode-tool Cortex execution hardening."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cortexcode_tool.core.execute_cortex import execute_cortex_streaming


class RaisingStdout:
    def __iter__(self):
        raise RuntimeError("stream failed")


def _disallowed_from(cmd):
    return [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--disallowed-tools"]


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_uses_print_mode_stream_json_without_bypass(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = []
    mock_process.stderr = []
    mock_process.wait.return_value = 0
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    execute_cortex_streaming("test prompt", approval_mode="auto", envelope="RO")

    cmd = mock_popen.call_args[0][0]
    assert "-p" in cmd
    assert "test prompt" in cmd
    assert "--input-format" not in cmd
    assert "stream-json" in cmd
    assert "--bypass" not in cmd
    assert mock_popen.call_args[1]["stdin"] == subprocess.DEVNULL


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_ro_and_research_block_bash_entirely(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = []
    mock_process.stderr = []
    mock_process.wait.return_value = 0
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    execute_cortex_streaming("test prompt", approval_mode="auto", envelope="RO")
    ro_disallowed = _disallowed_from(mock_popen.call_args[0][0])

    execute_cortex_streaming("test prompt", approval_mode="auto", envelope="RESEARCH")
    research_disallowed = _disallowed_from(mock_popen.call_args[0][0])

    assert "Bash" in ro_disallowed
    assert "Bash" in research_disallowed


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_rw_and_deploy_block_destructive_shell_patterns(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = []
    mock_process.stderr = []
    mock_process.wait.return_value = 0
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    execute_cortex_streaming("test prompt", approval_mode="auto", envelope="RW")
    rw_disallowed = _disallowed_from(mock_popen.call_args[0][0])

    execute_cortex_streaming("test prompt", approval_mode="auto", envelope="DEPLOY", deploy_confirmed=True)
    deploy_disallowed = _disallowed_from(mock_popen.call_args[0][0])

    for disallowed_tools in (rw_disallowed, deploy_disallowed):
        assert "Bash" in disallowed_tools
        assert "Bash(rm *)" in disallowed_tools
        assert "Bash(rm -rf *)" in disallowed_tools
        assert "Bash(sudo *)" in disallowed_tools


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_timeout_kills_process(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = []
    mock_process.stderr = []
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="cortex", timeout=1)
    mock_popen.return_value = mock_process

    result = execute_cortex_streaming("test prompt", timeout_seconds=1)

    assert "timed out" in result["error"]
    mock_process.kill.assert_called_once()


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_nonzero_exit_captures_stderr_without_read_after_wait(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = []
    mock_process.stderr = MagicMock()
    mock_process.stderr.__iter__.return_value = iter(["bad\n", "worse\n"])
    mock_process.wait.return_value = 2
    mock_process.returncode = 2
    mock_popen.return_value = mock_process

    result = execute_cortex_streaming("test prompt", timeout_seconds=1)

    assert result["error"] == "bad\nworse\n"
    mock_process.stderr.read.assert_not_called()


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_list_tool_result_content_does_not_crash(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = [json.dumps({
        "type": "user",
        "message": {
            "content": [{
                "type": "tool_result",
                "tool_use_id": "tool-1",
                "content": [{"type": "text", "text": "Permission denied"}],
            }]
        },
    }) + "\n"]
    mock_process.stderr = []
    mock_process.wait.return_value = 0
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    result = execute_cortex_streaming("test prompt", timeout_seconds=1)

    assert result["permission_requests"][0]["tool_use_id"] == "tool-1"


@patch("cortexcode_tool.core.execute_cortex.subprocess.Popen")
def test_exception_kills_process(mock_popen):
    mock_process = MagicMock()
    mock_process.stdout = RaisingStdout()
    mock_process.stderr = []
    mock_popen.return_value = mock_process

    result = execute_cortex_streaming("test prompt", timeout_seconds=1)

    assert "stream failed" in result["error"]
    mock_process.kill.assert_called_once()
