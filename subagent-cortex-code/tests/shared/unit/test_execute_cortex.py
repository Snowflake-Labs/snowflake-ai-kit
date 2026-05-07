"""
Unit tests for execute_cortex.py module.

Tests command building, tool inversion, envelope security, and streaming execution.
"""

import pytest
import subprocess
from unittest.mock import patch, MagicMock
from shared.scripts.execute_cortex import (
    invert_tools_to_disallowed,
    execute_cortex_streaming,
    KNOWN_TOOLS
)


@pytest.mark.unit
def test_invert_tools_basic():
    """Test basic tool inversion from allowed to disallowed."""
    allowed = ["Read", "Grep"]
    disallowed = invert_tools_to_disallowed(allowed)

    # Should contain all KNOWN_TOOLS except the allowed ones
    assert "Write" in disallowed
    assert "Edit" in disallowed
    assert "Bash" in disallowed
    assert "Read" not in disallowed
    assert "Grep" not in disallowed


@pytest.mark.unit
def test_invert_tools_empty_allowed():
    """Test tool inversion with empty allowed list."""
    allowed = []
    disallowed = invert_tools_to_disallowed(allowed)

    # Should return all KNOWN_TOOLS
    assert len(disallowed) == len(KNOWN_TOOLS) + 1
    assert set(disallowed) == set(KNOWN_TOOLS + ["*"])


@pytest.mark.unit
def test_invert_tools_all_allowed():
    """Test tool inversion when all tools are allowed."""
    allowed = KNOWN_TOOLS.copy()
    disallowed = invert_tools_to_disallowed(allowed)

    # Should return empty list
    assert disallowed == ["*"]


@pytest.mark.unit
def test_execute_cortex_command_structure():
    """Test basic command structure for execute_cortex_streaming."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute
        list(execute_cortex_streaming("test prompt"))

        # Verify command structure
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]

        assert cmd[0] == "cortex"
        assert "-p" in cmd
        assert "test prompt" in cmd
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--input-format" not in cmd


@pytest.mark.unit
def test_execute_cortex_print_mode_closes_stdin():
    """Test print-mode prompt delivery closes stdin without JSON input mode."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute
        list(execute_cortex_streaming("test prompt"))

        # Verify stdin=DEVNULL and --input-format is absent. Combining -p with
        # stream-json input mode makes Cortex wait for JSON stdin and exit early.
        cmd = mock_popen.call_args[0][0]
        assert "--input-format" not in cmd
        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs['stdin'] == subprocess.DEVNULL


@pytest.mark.unit
def test_execute_cortex_ro_envelope():
    """Test RO envelope blocks write operations via disallowed-tools."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute with RO envelope
        list(execute_cortex_streaming("test prompt", envelope="RO", approval_mode="auto"))

        # Verify command
        cmd = mock_popen.call_args[0][0]

        # RO envelope should block Edit and Write
        assert "--disallowed-tools" in cmd
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        assert "Edit" in disallowed_tools
        assert "Write" in disallowed_tools
        assert "Bash" in disallowed_tools


@pytest.mark.unit
def test_execute_cortex_no_allowed_tools_flag():
    """Test that --allowed-tools is NEVER used (prevents MCP blocking)."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Test all approval modes and envelopes
        test_cases = [
            {"approval_mode": "auto", "envelope": "RO"},
            {"approval_mode": "envelope_only", "envelope": "RW"},
            {"approval_mode": "prompt", "allowed_tools": ["Read"]},
        ]

        for test_case in test_cases:
            mock_popen.reset_mock()
            list(execute_cortex_streaming("test prompt", **test_case))

            cmd = mock_popen.call_args[0][0]
            assert "--allowed-tools" not in cmd


@pytest.mark.unit
def test_execute_cortex_prompt_mode_inversion():
    """Test prompt mode inverts allowed_tools to disallowed_tools."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute in prompt mode with specific allowed tools
        list(execute_cortex_streaming(
            "test prompt",
            approval_mode="prompt",
            allowed_tools=["Read", "Grep"]
        ))

        # Verify disallowed tools includes inverted list
        cmd = mock_popen.call_args[0][0]
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        # Should block tools NOT in allowed list
        assert "Write" in disallowed_tools
        assert "Edit" in disallowed_tools
        # Should NOT block allowed tools
        assert "Read" not in disallowed_tools
        assert "Grep" not in disallowed_tools


@pytest.mark.unit
def test_execute_cortex_connection_parameter():
    """Test connection parameter is passed correctly."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute with connection
        list(execute_cortex_streaming("test prompt", connection="my_connection"))

        # Verify connection flag
        cmd = mock_popen.call_args[0][0]
        assert "-c" in cmd
        connection_idx = cmd.index("-c")
        assert cmd[connection_idx + 1] == "my_connection"


@pytest.mark.unit
def test_execute_cortex_deploy_envelope_blocks_destructive_shell():
    """Test DEPLOY envelope still blocks destructive shell operations."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute with DEPLOY envelope
        list(execute_cortex_streaming("test prompt", envelope="DEPLOY", approval_mode="auto", deploy_confirmed=True))

        cmd = mock_popen.call_args[0][0]
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        assert "Bash(rm *)" in disallowed_tools
        assert "Bash(rm -rf *)" in disallowed_tools
        assert "Bash(sudo *)" in disallowed_tools
        assert "Bash(git reset --hard *)" in disallowed_tools


@pytest.mark.unit
def test_execute_cortex_rw_envelope_blocks_destructive_shell():
    """Test RW envelope blocks destructive shell operations."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        list(execute_cortex_streaming("test prompt", envelope="RW", approval_mode="auto"))

        cmd = mock_popen.call_args[0][0]
        disallowed_tools = []
        for i, arg in enumerate(cmd):
            if arg == "--disallowed-tools" and i + 1 < len(cmd):
                disallowed_tools.append(cmd[i + 1])

        assert "Bash" in disallowed_tools
        assert "Bash(rm *)" in disallowed_tools
        assert "Bash(rm -rf *)" in disallowed_tools
        assert "Bash(sudo *)" in disallowed_tools


@pytest.mark.unit
def test_execute_cortex_streaming_json_parsing():
    """Test streaming JSON event parsing."""
    with patch('shared.scripts.execute_cortex.subprocess.Popen') as mock_popen:
        # Configure mock with streaming events
        mock_process = MagicMock()
        mock_process.stdout = [
            '{"type": "system", "subtype": "init", "session_id": "test-123"}',
            '{"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"}]}}',
            '{"type": "result", "result": "success"}'
        ]
        mock_process.poll.return_value = 0
        mock_process.returncode = 0
        mock_process.stderr.read.return_value = ""
        mock_popen.return_value = mock_process

        # Execute
        results = execute_cortex_streaming("test prompt")

        # Verify results structure
        assert "session_id" in results
        assert results["session_id"] == "test-123"
        assert "events" in results
        assert len(results["events"]) == 3
        assert "final_result" in results
        assert results["final_result"] == "success"
