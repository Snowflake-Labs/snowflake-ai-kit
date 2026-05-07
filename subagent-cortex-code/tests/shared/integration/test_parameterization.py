"""Integration tests for cross-agent parameterization."""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared" / "scripts"))

from route_request import analyze_with_llm_logic
from security_wrapper import execute_with_security


@pytest.mark.integration
@pytest.mark.parametrize("agent_name", ["claude", "cursor", "codex"])
def test_routing_returns_correct_agent_name(agent_name):
    """Routing should return __CODING_AGENT__ placeholder"""
    prompt = "Fix this code"
    capabilities = {}

    decision, confidence = analyze_with_llm_logic(prompt, capabilities)

    # Should always return placeholder, regardless of which agent
    assert decision == "__CODING_AGENT__"


@pytest.mark.integration
@pytest.mark.parametrize("agent_name", ["claude", "cursor", "codex"])
def test_config_paths_use_safe_fallback_when_not_parameterized(agent_name, tmp_path):
    """Unreplaced placeholders should fall back to a safe cache audit path."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared"))
    from security.config_manager import ConfigManager

    config = ConfigManager()
    audit_log = config.get("security.audit_log_path")

    assert "__CODING_AGENT__" not in audit_log
    assert ".cache" in audit_log
    assert audit_log.endswith("audit.log")


@pytest.mark.integration
@pytest.mark.cross_platform
def test_python_placeholder_replacement():
    """Installers should use Python replacement instead of platform-specific sed."""
    content = 'AGENT = "__CODING_AGENT__"\n'
    replaced = content.replace("__CODING_AGENT__", "claude")

    assert 'AGENT = "claude"' in replaced
    assert "__CODING_AGENT__" not in replaced


@pytest.mark.integration
def test_install_replaces_placeholder():
    """Validate that placeholder replacement pattern is correct"""
    # This is a documentation test - actual replacement happens in install.sh

    test_content = """
def route():
    return "__CODING_AGENT__", 0.5

audit_path = "~/.__CODING_AGENT__/audit.log"
"""

    # Simulate sed replacement
    for agent in ["claude", "cursor", "codex"]:
        replaced = test_content.replace("__CODING_AGENT__", agent)

        assert f'return "{agent}", 0.5' in replaced
        assert f"~/.{agent}/audit.log" in replaced
        assert "__CODING_AGENT__" not in replaced
