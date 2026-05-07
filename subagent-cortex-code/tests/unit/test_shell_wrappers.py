"""Regression tests for shell wrappers used by Codex integrations."""
from pathlib import Path


def test_codex_wrapper_uses_argv_for_output_file_json_read():
    """OUTPUT_FILE must not be interpolated into a python -c string."""
    text = Path("shared/scripts/execute_cortex_codex.sh").read_text()
    assert "json.load(open('$OUTPUT_FILE'))" not in text
    assert "sys.argv[1]" in text


def test_codex_wrappers_do_not_default_to_predictable_tmp_path():
    """Wrappers should not use a predictable /tmp/codex-cortex-latest.json path."""
    for wrapper in [
        "shared/scripts/execute_cortex_codex.sh",
        "shared/scripts/execute_cortex_async.sh",
    ]:
        text = Path(wrapper).read_text()
        assert "/tmp/codex-cortex-latest.json" not in text
        assert "mktemp" in text


def test_async_wrapper_persists_pid_file():
    """Async wrapper should persist the child PID for cleanup/watchdog tooling."""
    text = Path("shared/scripts/execute_cortex_async.sh").read_text()
    assert "PID_FILE" in text
    assert 'echo "$JOB_PID"' in text


def test_cli_setup_uses_private_config_permissions_and_no_sandbox_escape_docs():
    text = Path("integrations/cli-tool/setup.sh").read_text()
    assert "chmod 600 \"$INSTALL_DIR/config.yaml\"" in text
    assert "sandbox triggers a bypass prompt" not in text
    assert "PermissionError → tool runs outside sandbox" not in text


def test_codex_config_does_not_document_sandbox_escape():
    text = Path("integrations/codex/cortexcode-tool-codex.yaml").read_text()
    assert "sandbox triggers a bypass prompt" not in text
    assert "PermissionError → tool runs outside sandbox" not in text


def test_install_scripts_do_not_use_unquoted_sed_exec_or_broad_chmod():
    for path in [
        "integrations/cursor/install.sh",
        "integrations/claude-code/install.sh",
    ]:
        text = Path(path).read_text()
        assert "sed -i" not in text
        assert 'chmod +x "$TARGET/scripts/"*.py' not in text
        assert "chmod 700 \"$TARGET\"" in text
        assert "chmod 600" in text


def test_org_policy_env_var_not_documented():
    for path in [
        "integrations/codex/SECURITY.md",
        "integrations/claude-code/config.yaml.example",
    ]:
        assert "CORTEX_SKILL_ORG_POLICY" not in Path(path).read_text()
