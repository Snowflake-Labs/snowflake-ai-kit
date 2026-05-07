#!/usr/bin/env python3
"""
Unit tests for execute_cortex.py approval mode support.
Tests tool inversion logic and integration with security wrapper.
"""

import pytest
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Optional

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from execute_cortex import (
    execute_cortex_streaming,
    invert_tools_to_disallowed,
    KNOWN_TOOLS,
    main
)


class RaisingStdout:
    def __iter__(self):
        raise RuntimeError("stream failed")


class BlockingStdout:
    def __iter__(self):
        while True:
            yield ""


class TestToolInversion:
    """Test tool inversion logic (allowed -> disallowed)."""

    def test_invert_empty_allowed_list(self):
        """When no tools are allowed, all tools should be disallowed."""
        allowed = []
        disallowed = invert_tools_to_disallowed(allowed)

        assert set(disallowed) == set(KNOWN_TOOLS + ["*"])
        assert len(disallowed) == len(KNOWN_TOOLS) + 1

    def test_invert_single_allowed_tool(self):
        """When one tool is allowed, all others should be disallowed."""
        allowed = ["Read"]
        disallowed = invert_tools_to_disallowed(allowed)

        expected = [t for t in KNOWN_TOOLS if t != "Read"] + ["*"]
        assert set(disallowed) == set(expected)
        assert "Read" not in disallowed

    def test_invert_multiple_allowed_tools(self):
        """When multiple tools are allowed, remaining should be disallowed."""
        allowed = ["Read", "Grep", "Glob"]
        disallowed = invert_tools_to_disallowed(allowed)

        expected = [t for t in KNOWN_TOOLS if t not in allowed] + ["*"]
        assert set(disallowed) == set(expected)
        for tool in allowed:
            assert tool not in disallowed

    def test_invert_all_tools_allowed(self):
        """When all tools are allowed, disallowed list should be empty."""
        allowed = list(KNOWN_TOOLS)
        disallowed = invert_tools_to_disallowed(allowed)

        assert disallowed == ["*"]

    def test_invert_unknown_tool_ignored(self):
        """Unknown tools in allowed list should be ignored."""
        allowed = ["Read", "UnknownTool", "Grep"]
        disallowed = invert_tools_to_disallowed(allowed)

        # UnknownTool is not in KNOWN_TOOLS, so it's ignored
        # Only Read and Grep should be excluded from disallowed
        expected = [t for t in KNOWN_TOOLS if t not in ["Read", "Grep"]] + ["*"]
        assert set(disallowed) == set(expected)

    def test_invert_preserves_tool_names(self):
        """Tool names should be preserved exactly (case-sensitive)."""
        allowed = ["Read", "Write"]
        disallowed = invert_tools_to_disallowed(allowed)

        # Check exact names are preserved
        assert "Edit" in disallowed
        assert "Bash" in disallowed
        assert "read" not in disallowed  # Case-sensitive


class TestApprovalModeParameters:
    """Test approval mode parameter handling."""

    @patch('execute_cortex.subprocess.Popen')
    def test_approval_mode_auto_default(self, mock_popen):
        """Auto mode should use print-mode prompt delivery."""
        mock_process = self._setup_mock_process(mock_popen)

        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="auto"
        )

        cmd = mock_popen.call_args[0][0]
        assert "-p" in cmd
        assert "Test prompt" in cmd
        assert "stream-json" in cmd
        assert "--input-format" not in cmd

    @patch('execute_cortex.subprocess.Popen')
    def test_approval_mode_prompt_with_allowed_tools(self, mock_popen):
        """Prompt mode with allowed tools should invert to disallowed."""
        mock_process = self._setup_mock_process(mock_popen)

        allowed_tools = ["Read", "Grep", "Glob"]
        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="prompt",
            allowed_tools=allowed_tools
        )

        # Check that disallowed tools were computed correctly
        cmd = mock_popen.call_args[0][0]
        assert "--disallowed-tools" in cmd

        # Extract disallowed tools from command
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # Verify Read, Grep, Glob are NOT in disallowed list
        for tool in allowed_tools:
            assert tool not in disallowed_tools

        # Verify other tools ARE in disallowed list
        for tool in KNOWN_TOOLS:
            if tool not in allowed_tools:
                assert tool in disallowed_tools

    @patch('execute_cortex.subprocess.Popen')
    def test_approval_mode_prompt_no_allowed_tools(self, mock_popen):
        """Prompt mode without allowed tools should block all tools."""
        mock_process = self._setup_mock_process(mock_popen)

        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="prompt",
            allowed_tools=None
        )

        # All tools should be disallowed
        cmd = mock_popen.call_args[0][0]
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # All known tools should be disallowed
        for tool in KNOWN_TOOLS:
            assert tool in disallowed_tools

    @patch('execute_cortex.subprocess.Popen')
    def test_approval_mode_envelope_only(self, mock_popen):
        """Envelope-only mode should use envelope blocklist only."""
        mock_process = self._setup_mock_process(mock_popen)

        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="envelope_only",
            envelope="RO"
        )

        # Should use envelope-based disallowed tools (Read-Only mode)
        cmd = mock_popen.call_args[0][0]
        assert "--disallowed-tools" in cmd

        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # RO envelope should block Write and Edit
        assert "Write" in disallowed_tools
        assert "Edit" in disallowed_tools

    @patch('execute_cortex.subprocess.Popen')
    def test_approval_mode_preserves_existing_disallowed(self, mock_popen):
        """Approval mode should merge with existing disallowed_tools."""
        mock_process = self._setup_mock_process(mock_popen)

        existing_disallowed = ["Bash(rm *)", "Bash(sudo *)"]
        allowed_tools = ["Read", "Write"]

        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="prompt",
            allowed_tools=allowed_tools,
            disallowed_tools=existing_disallowed
        )

        cmd = mock_popen.call_args[0][0]
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # Should include both inverted tools AND existing disallowed
        for tool in existing_disallowed:
            assert tool in disallowed_tools

        # Should also include inverted tools (exclude Read, Write)
        for tool in KNOWN_TOOLS:
            if tool not in allowed_tools:
                assert tool in disallowed_tools

    def _setup_mock_process(self, mock_popen):
        """Helper to set up mock subprocess."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process
        return mock_process


class TestApprovalModeIntegration:
    """Integration tests for approval mode with envelope system."""

    @patch('execute_cortex.subprocess.Popen')
    def test_prompt_mode_overrides_envelope(self, mock_popen):
        """In prompt mode, allowed_tools should override envelope defaults."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # RO envelope normally blocks Write, but we explicitly allow it
        allowed_tools = ["Read", "Write"]
        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="prompt",
            allowed_tools=allowed_tools,
            envelope="RO"
        )

        cmd = mock_popen.call_args[0][0]
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # Write should NOT be in disallowed (we allowed it)
        assert "Write" not in disallowed_tools
        # Edit should be in disallowed (not in allowed_tools)
        assert "Edit" in disallowed_tools

    @patch('execute_cortex.subprocess.Popen')
    def test_auto_mode_uses_envelope_defaults(self, mock_popen):
        """In auto mode, envelope defaults should be used."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="auto",
            envelope="RO"
        )

        cmd = mock_popen.call_args[0][0]
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # RO envelope should block Write and Edit
        assert "Write" in disallowed_tools
        assert "Edit" in disallowed_tools


class TestCLIInterface:
    """Test CLI argument parsing."""

    def test_cli_approval_mode_argument(self):
        """CLI should accept --approval-mode argument."""
        from execute_cortex import main

        # Test that parser accepts approval-mode
        with patch('execute_cortex.execute_cortex_streaming') as mock_exec:
            mock_exec.return_value = {"status": "success", "events": []}
            with patch('sys.argv', ['execute_cortex.py', '--prompt', 'test', '--approval-mode', 'prompt']):
                result = main()
                # Should return 0 (success)
                assert result == 0

    def test_cli_allowed_tools_argument(self):
        """CLI should accept --allowed-tools argument."""
        from execute_cortex import main

        with patch('execute_cortex.execute_cortex_streaming') as mock_exec:
            mock_exec.return_value = {"status": "success", "events": []}
            with patch('sys.argv', ['execute_cortex.py', '--prompt', 'test', '--allowed-tools', 'Read', 'Write']):
                result = main()
                assert result == 0

                # Check that allowed_tools was passed correctly
                call_kwargs = mock_exec.call_args[1]
                assert 'allowed_tools' in call_kwargs
                assert call_kwargs['allowed_tools'] == ['Read', 'Write']

    def test_cli_output_file_argument_writes_json(self, tmp_path, capsys):
        """CLI should accept --output-file and write results there."""
        output_file = tmp_path / "cortex-result.json"

        with patch.dict('os.environ', {'CORTEX_CODE_OUTPUT_DIR': str(tmp_path)}):
            with patch('execute_cortex.execute_cortex_streaming') as mock_exec:
                mock_exec.return_value = {"final_result": "ok", "error": None}
                with patch('sys.argv', [
                'execute_cortex.py',
                '--prompt', 'test',
                '--output-file', str(output_file)
            ]):
                    result = main()

        assert result == 0
        assert json.loads(output_file.read_text()) == {"final_result": "ok", "error": None}
        assert capsys.readouterr().out == ""


class TestSubprocessLifecycle:
    """Test subprocess timeout, stderr, and stream parsing behavior."""

    @patch('execute_cortex.subprocess.Popen')
    def test_nonzero_exit_captures_stderr_without_read_after_wait(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = MagicMock()
        mock_process.stderr.__iter__.return_value = iter(["bad\n", "worse\n"])
        mock_process.wait.return_value = 2
        mock_process.returncode = 2
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=1)

        assert result["error"] == "bad\nworse\n"
        mock_process.stderr.read.assert_not_called()

    @patch('execute_cortex.subprocess.Popen')
    def test_timeout_kills_process(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = []
        mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="cortex", timeout=1)
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=1)

        assert "timed out" in result["error"]
        mock_process.kill.assert_called_once()

    @patch('execute_cortex.subprocess.Popen')
    def test_timeout_kills_process_when_stdout_blocks(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = BlockingStdout()
        mock_process.stderr = []
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=0.01)

        assert "timed out" in result["error"]
        mock_process.kill.assert_called_once()

    @patch('execute_cortex.subprocess.Popen')
    def test_exception_kills_process(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = RaisingStdout()
        mock_process.stderr = []
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=1)

        assert "stream failed" in result["error"]
        mock_process.kill.assert_called_once()

    @patch('execute_cortex.subprocess.Popen')
    def test_tool_result_list_content_does_not_crash(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = [json.dumps({
            "type": "user",
            "message": {
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": "tool-1",
                    "content": [{"type": "text", "text": "Permission denied"}]
                }]
            }
        }) + "\n"]
        mock_process.stderr = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=1)

        assert result["permission_requests"][0]["tool_use_id"] == "tool-1"


class TestBackwardCompatibility:
    """Test that existing functionality is preserved."""

    @patch('execute_cortex.subprocess.Popen')
    def test_existing_calls_still_work(self, mock_popen):
        """Existing calls without approval_mode should work unchanged."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Old-style call without approval parameters
        result = execute_cortex_streaming(
            prompt="Test prompt",
            connection="myconn",
            disallowed_tools=["Bash"],
            envelope="RW"
        )

        # Should execute successfully
        assert result is not None
        assert "error" in result

    @patch('execute_cortex.subprocess.Popen')
    def test_envelope_logic_unchanged(self, mock_popen):
        """Envelope-based blocklists should work as before."""
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(
            prompt="Test prompt",
            envelope="RO"
        )

        cmd = mock_popen.call_args[0][0]
        disallowed_indices = [i for i, x in enumerate(cmd) if x == "--disallowed-tools"]
        disallowed_tools = [cmd[i + 1] for i in disallowed_indices]

        # RO envelope behavior should be unchanged
        assert "Write" in disallowed_tools
        assert "Edit" in disallowed_tools

class TestIssue13EnvelopeHardening:
    """Regression tests for issue #13 envelope hardening."""

    @patch('execute_cortex.subprocess.Popen')
    def test_none_envelope_rejected_in_auto_mode(self, mock_popen):
        """NONE envelope must not disable all restrictions in auto mode."""
        with pytest.raises(ValueError, match="NONE envelope"):
            execute_cortex_streaming(
                prompt="Test prompt",
                approval_mode="auto",
                envelope="NONE",
            )
        mock_popen.assert_not_called()

    @patch('execute_cortex.subprocess.Popen')
    def test_none_envelope_rejected_in_envelope_only_mode(self, mock_popen):
        """NONE envelope must not disable all restrictions in envelope_only mode."""
        with pytest.raises(ValueError, match="NONE envelope"):
            execute_cortex_streaming(
                prompt="Test prompt",
                approval_mode="envelope_only",
                envelope="NONE",
            )
        mock_popen.assert_not_called()


def _disallowed_from_cmd(cmd):
    return [cmd[i + 1] for i, value in enumerate(cmd) if value == "--disallowed-tools"]


class TestIssue13MediumEnvelopeHardening:
    @patch('execute_cortex.subprocess.Popen')
    def test_rw_blocks_bash_tool_by_default(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        execute_cortex_streaming(prompt="Test prompt", envelope="RW", approval_mode="auto")

        disallowed = _disallowed_from_cmd(mock_popen.call_args[0][0])
        assert "Bash" in disallowed

    @patch('execute_cortex.subprocess.Popen')
    def test_error_output_is_redacted(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = ["failure for john@example.com with sk-1234567890abcdef\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        result = execute_cortex_streaming(prompt="Test prompt", timeout_seconds=1)

        assert "john@example.com" not in result["error"]
        assert "sk-1234567890abcdef" not in result["error"]
        assert "<EMAIL>" in result["error"]


class TestIssue13FinalHardening:
    @patch('execute_cortex.subprocess.Popen')
    def test_deploy_requires_explicit_confirmation(self, mock_popen):
        with pytest.raises(ValueError, match="DEPLOY envelope requires explicit confirmation"):
            execute_cortex_streaming(
                prompt="Deploy Snowflake change",
                envelope="DEPLOY",
                approval_mode="auto",
            )
        mock_popen.assert_not_called()

    @patch('execute_cortex.subprocess.Popen')
    def test_prompt_mode_blocks_unknown_tools_when_allowed_tools_present(self, mock_popen):
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        execute_cortex_streaming(
            prompt="Test prompt",
            approval_mode="prompt",
            allowed_tools=["snowflake_sql_execute"],
        )

        disallowed = _disallowed_from_cmd(mock_popen.call_args[0][0])
        assert "*" in disallowed
        assert "snowflake_sql_execute" not in disallowed


def test_output_file_path_must_stay_under_safe_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("CORTEX_CODE_OUTPUT_DIR", str(tmp_path / "allowed"))
    output_file = tmp_path / "outside.json"
    with patch('execute_cortex.subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.stderr = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        with patch('sys.argv', ['execute_cortex.py', '--prompt', 'test', '--output-file', str(output_file)]):
            assert main() == 1
        assert not output_file.exists()


def test_execute_cortex_defaults_to_prompt_mode():
    import inspect
    import execute_cortex

    assert inspect.signature(execute_cortex.execute_cortex_streaming).parameters["approval_mode"].default == "prompt"


def test_execute_cortex_cli_default_is_prompt():
    text = Path("scripts/execute_cortex.py").read_text()
    assert 'parser.add_argument("--approval-mode", default="prompt"' in text
    assert 'Approval mode (default: prompt)' in text
