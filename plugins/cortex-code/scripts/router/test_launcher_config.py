#!/usr/bin/env python3
"""Offline regressions for interpreter selection and fail-closed configuration."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import execute_cortex
from security import config_manager

ROUTER = Path(__file__).resolve().parent
PLUGIN = ROUTER.parent.parent
LAUNCHER = PLUGIN / "scripts" / "run_python.sh"


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.user = self.root / "config.yaml"
        self.policy = self.root / "policy.yaml"
        for patcher in (
            patch.object(config_manager, "DEFAULT_CONFIG_PATH", self.user),
            patch.object(config_manager, "DEFAULT_ORG_POLICY_PATH", self.policy),
            patch.dict(os.environ, {}, clear=False),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        os.environ.pop("CORTEX_SKILL_CONFIG", None)
        os.environ.pop("CORTEX_SKILL_ORG_POLICY", None)

    def write(self, path, text):
        path.write_text(text, encoding="utf-8")

    def test_no_yaml_no_files_uses_defaults(self):
        with patch.object(config_manager, "HAS_YAML", False):
            config = config_manager.ConfigManager()
        self.assertEqual(config.get("security.approval_mode"), "prompt")
        self.assertEqual(set(config.get("security.allowed_envelopes")), {"RO", "RW", "RESEARCH"})

    def test_no_yaml_rejects_either_file_with_actionable_error(self):
        for path in (self.user, self.policy):
            with self.subTest(path=path):
                self.write(path, "security:\n  allowed_envelopes: [RO]\n")
                with patch.object(config_manager, "HAS_YAML", False):
                    with self.assertRaises(config_manager.ConfigValidationError) as caught:
                        config_manager.ConfigManager()
                message = str(caught.exception)
                self.assertIn(str(path), message)
                self.assertIn(sys.executable, message)
                self.assertIn("-m pip install PyYAML", message)
                path.unlink()

    def test_explicit_missing_files_are_errors(self):
        for argument, path in (("config_path", self.user), ("org_policy_path", self.policy)):
            with self.subTest(argument=argument):
                with self.assertRaisesRegex(config_manager.ConfigValidationError, "not found"):
                    config_manager.ConfigManager(**{argument: path})

    def test_env_missing_files_are_errors(self):
        for name in ("CORTEX_SKILL_CONFIG", "CORTEX_SKILL_ORG_POLICY"):
            with self.subTest(name=name), patch.dict(os.environ, {name: str(self.root / "missing")}):
                with self.assertRaisesRegex(config_manager.ConfigValidationError, "not found"):
                    config_manager.ConfigManager()

    def test_unreadable_files_are_errors(self):
        original = Path.read_text
        for denied in (self.user, self.policy):
            def read_text(path, *args, **kwargs):
                if path == denied:
                    raise PermissionError("access denied")
                return original(path, *args, **kwargs)

            with self.subTest(path=denied), patch.object(Path, "read_text", read_text):
                with self.assertRaisesRegex(config_manager.ConfigValidationError, "Cannot read"):
                    config_manager.ConfigManager()

    def test_directory_and_invalid_utf8_are_errors(self):
        self.user.mkdir()
        with self.assertRaisesRegex(config_manager.ConfigValidationError, "Cannot read"):
            config_manager.ConfigManager()
        self.user.rmdir()
        self.user.write_bytes(b"\xff")
        with self.assertRaisesRegex(config_manager.ConfigValidationError, "Cannot read"):
            config_manager.ConfigManager()

    @unittest.skipIf(os.name == "nt", "Creating symlinks can require Windows administrator rights")
    def test_dangling_policy_is_not_absent(self):
        self.policy.symlink_to(self.root / "missing")
        with self.assertRaisesRegex(config_manager.ConfigValidationError, "not found"):
            config_manager.ConfigManager()

    @unittest.skipUnless(config_manager.HAS_YAML, "PyYAML-dependent parsing")
    def test_invalid_documents_rejected_before_floor_or_merge(self):
        documents = (
            "", "null", "false", "[]", "42", "security: [", "security: null",
            "security: []", "security:\n  allowed_envelopes: RO",
            "security:\n  allowed_envelopes: [typo]",
            "security:\n  allowed_envelopes: [[RO]]",
            "security:\n  approval_mode: invalid",
            "security:\n  override_user_config: 'false'",
            "security:\n  sanitize_conversation_history: 'false'",
            "security:\n  tool_prediction_confidence_threshold: true",
            "security:\n  tool_prediction_confidence_threshold: null",
            "security:\n  tool_prediction_confidence_threshold: .nan",
            "security:\n  audit_log_retention: -1",
            "security:\n  cache_dir: null",
            "security:\n  audit_log_rotation: invalid",
        )
        for path in (self.user, self.policy):
            for document in documents:
                with self.subTest(path=path, document=document):
                    self.write(path, document)
                    with self.assertRaises(config_manager.ConfigValidationError) as caught:
                        config_manager.ConfigManager()
                    self.assertIn(str(path), str(caught.exception))
            path.unlink()

    @unittest.skipUnless(config_manager.HAS_YAML, "PyYAML-dependent parsing")
    def test_precedence_and_override_preserved(self):
        self.write(self.user, "security:\n  allowed_envelopes: [RO, RW]\n  max_history_items: 1\n")
        self.write(self.policy, "security:\n  allowed_envelopes: [RO]\n  approval_mode: envelope_only\n")
        config = config_manager.ConfigManager()
        self.assertEqual(config.get("security.allowed_envelopes"), ["RO"])
        self.assertEqual(config.get("security.approval_mode"), "envelope_only")
        self.assertEqual(config.get("security.max_history_items"), 1)
        self.write(self.policy, "security:\n  override_user_config: true\n  allowed_envelopes: [RO]\n")
        self.assertEqual(config_manager.ConfigManager().get("security.max_history_items"), 3)

    @unittest.skipUnless(config_manager.HAS_YAML, "PyYAML-dependent parsing")
    def test_empty_allowlist_denies_execution(self):
        self.write(self.policy, "security:\n  allowed_envelopes: []\n")
        self.assertIsNotNone(execute_cortex._check_envelope_allowed("RO"))

    def test_validation_error_blocks_both_execution_paths_before_subprocess(self):
        self.write(self.policy, "security:\n  allowed_envelopes: [RO]\n")
        with patch.object(config_manager, "HAS_YAML", False), \
             patch.object(execute_cortex.subprocess, "Popen") as popen, \
             patch.object(execute_cortex.subprocess, "run") as run:
            result = execute_cortex.execute_cortex_streaming("show tables", envelope="RO")
            self.assertIn("PyYAML", result["error"])
            output = io.StringIO()
            args = argparse.Namespace(prompt="show tables", envelope="RO")
            with contextlib.redirect_stdout(output):
                status = execute_cortex._run_codex_mode(args)
            self.assertEqual(status, 1)
            self.assertIn("PyYAML", json.loads(output.getvalue())["error"])
            popen.assert_not_called()
            run.assert_not_called()

    def test_envelope_check_does_not_swallow_config_errors(self):
        with patch.object(config_manager, "ConfigManager", side_effect=RuntimeError("broken loader")):
            self.assertIn("execution stopped", execute_cortex._check_envelope_allowed("RO"))

    @unittest.skipUnless(config_manager.HAS_YAML, "PyYAML-dependent parsing")
    def test_invalid_policy_blocks_both_paths_before_subprocess(self):
        for policy in ("security: [", "security:\n  allowed_envelopes: RO",
                       "security:\n  allowed_envelopes: []"):
            with self.subTest(policy=policy), \
                 patch.object(execute_cortex.subprocess, "Popen") as popen, \
                 patch.object(execute_cortex.subprocess, "run") as run:
                self.write(self.policy, policy)
                result = execute_cortex.execute_cortex_streaming("show tables", envelope="RO")
                self.assertTrue(result["error"])
                with contextlib.redirect_stdout(io.StringIO()):
                    status = execute_cortex._run_codex_mode(
                        argparse.Namespace(prompt="show tables", envelope="RO")
                    )
                self.assertEqual(status, 1)
                popen.assert_not_called()
                run.assert_not_called()

    @unittest.skipUnless(config_manager.HAS_YAML, "PyYAML-dependent parsing")
    def test_valid_ro_policy_loads_in_both_execution_paths(self):
        self.write(self.policy, "security:\n  allowed_envelopes: [RO]\n")
        with patch.object(execute_cortex, "check_mcp_conflict", return_value=None), \
             patch.object(execute_cortex, "check_cortex_cli", return_value=True), \
             patch.object(execute_cortex, "_get_audit_logger", return_value=None), \
             patch.object(execute_cortex.subprocess, "Popen", side_effect=OSError("test stop")) as popen:
            execute_cortex.execute_cortex_streaming("show tables", envelope="RO")
            popen.assert_called_once()
        args = argparse.Namespace(prompt="show tables", envelope="RO", connection=None,
                                  resume_session_id=None, resume_last=False)
        completed = subprocess.CompletedProcess([], 0, '{"type":"result","result":"ok"}\n', "")
        with patch.object(execute_cortex.subprocess, "run", return_value=completed) as run, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(execute_cortex._run_codex_mode(args), 0)
            run.assert_called_once()

    def test_cache_and_audit_helpers_propagate_config_errors(self):
        import predict_tools
        import route_request
        self.write(self.policy, "security: {}")
        with patch.object(config_manager, "HAS_YAML", False):
            for helper in (execute_cortex._get_audit_logger, predict_tools.load_capabilities,
                           route_request.load_cortex_capabilities):
                with self.subTest(helper=helper.__name__):
                    with self.assertRaises(config_manager.ConfigValidationError):
                        helper()

    def test_cli_errors_are_actionable_without_tracebacks(self):
        self.write(self.policy, "security:\n  allowed_envelopes: [RO]\n")
        environment = os.environ.copy()
        environment["CORTEX_SKILL_ORG_POLICY"] = str(self.policy)
        environment["HOME"] = str(self.root)
        environment["USERPROFILE"] = str(self.root)
        # Even a regression must not launch a real CLI or touch Snowflake.
        environment["PATH"] = str(self.root / "no-cli")
        commands = (
            ("execute_cortex.py", ["--prompt", "show tables"], 1),
            ("execute_cortex.py", ["--prompt", "show tables", "--codex"], 1),
            ("route_request.py", ["--prompt", "show tables"], 1),
            ("predict_tools.py", ["--prompt", "show tables"], 1),
            ("discover_cortex.py", ["--cache-dir", str(self.root / "cache")], 1),
            ("prompt_filter.py", [], 2),
        )
        for script, arguments, expected_status in commands:
            with self.subTest(script=script, arguments=arguments):
                # -S isolates site packages so this tests actual import failure, not a mock.
                result = subprocess.run(
                    [sys.executable, "-S", str(ROUTER / script), *arguments],
                    input=json.dumps({"prompt": "show snowflake tables"}),
                    capture_output=True, text=True, env=environment, timeout=10,
                )
                self.assertEqual(result.returncode, expected_status, result.stderr)
                self.assertIn("PyYAML", result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_unrelated_prompts_do_not_load_policy(self):
        import prompt_filter
        output = io.StringIO()
        with patch.object(config_manager, "ConfigManager") as loader, \
             patch.object(sys, "stdin", io.StringIO('{"prompt":"what is the weather today"}')), \
             contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as caught:
                prompt_filter.main()
        self.assertEqual(caught.exception.code, 0)
        self.assertEqual(json.loads(output.getvalue()), {})
        loader.assert_not_called()


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.bash = shutil.which("bash")
        if os.name == "nt":
            git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
            if git_bash.exists():
                self.bash = str(git_bash)
        if not self.bash:
            self.skipTest("Bash is required for plugin hooks")
        self.directory = tempfile.TemporaryDirectory(prefix="launcher tests ")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def stub(self, name, body):
        script = self.root / name
        with script.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("#!/bin/bash\n" + body + "\n")
        script.chmod(0o755)

    def launch(self, arguments=None, stdin=""):
        search_path = self.root.as_posix()
        if os.name == "nt":
            search_path = "/" + search_path[0].lower() + search_path[2:]
        return subprocess.run(
            [self.bash, "--noprofile", "--norc", "-c",
             'export PATH="$1"; shift; source "$@"', "test-launcher",
             search_path, LAUNCHER.as_posix(), *(arguments or [])],
            input=stdin, text=True, capture_output=True, timeout=10,
        )

    def test_python3_only_preserves_stdin_and_arguments(self):
        executable = Path(sys.executable).as_posix()
        self.stub("python3", f"exec {shlex.quote(executable)} \"$@\"")
        result = self.launch(
            ["-c", "import json,sys; print(json.dumps([sys.argv[1:], sys.stdin.read()]))",
             "value with spaces", "literal;$argument"], stdin='{"prompt":"hello"}',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout),
                         [["value with spaces", "literal;$argument"], '{"prompt":"hello"}'])

    def test_python3_preferred_and_script_failure_never_retried(self):
        self.stub("python3", 'if [ "$1" = -c ]; then exit 0; fi\nprintf "first\\n"; exit 23')
        self.stub("python", 'printf "UNEXPECTED FALLBACK\\n"; exit 0')
        result = self.launch(["script.py"])
        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout, "first\n")

    def test_python_only_fallback(self):
        executable = Path(sys.executable).as_posix()
        self.stub("python", f"exec {shlex.quote(executable)} \"$@\"")
        result = self.launch(["-c", "print('ok')"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "ok\n")

    def test_bad_python3_probe_uses_verified_python(self):
        self.stub("python3", "exit 1")
        executable = Path(sys.executable).as_posix()
        self.stub("python", f"exec {shlex.quote(executable)} \"$@\"")
        result = self.launch(["-c", "print('ok')"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_or_python2_interpreter_is_rejected(self):
        self.assertEqual(self.launch().returncode, 127)
        self.stub("python", 'if [ "$1" = -c ]; then exit 1; fi\nprintf "SHOULD NOT RUN\\n"')
        result = self.launch(["script.py"])
        self.assertEqual(result.returncode, 127)
        self.assertIn("requires Python 3", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_hooks_and_skills_use_shared_launcher(self):
        hooks = json.loads((PLUGIN / "hooks/hooks.json").read_text())["hooks"]
        for matchers in hooks.values():
            for matcher in matchers:
                for hook in matcher["hooks"]:
                    self.assertIn("scripts/run_python.sh", hook["command"])
                    self.assertNotIn("||", hook["command"])
        for skill in ("cortex-router", "cortex-run", "cortex-setup"):
            text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("scripts/run_python.sh", text)
            self.assertNotRegex(text, r"(?m)^python(?:3)? ")


if __name__ == "__main__":
    unittest.main()