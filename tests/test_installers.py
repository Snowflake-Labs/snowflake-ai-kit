#!/usr/bin/env python3
"""Behaviour tests for install.sh and install.ps1.

Each test runs the real installer in a temporary HOME with stub `snow` and `cortex`
commands on PATH, so nothing is installed. The `cortex` stub records its calls.
install.ps1 tests run when PowerShell (pwsh) is available.
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AIM_SOURCE = "https://github.com/Snowflake-Labs/cortex-code-migrations/tree/main/plugin"
PWSH = shutil.which("pwsh")
# The stub CLIs are shell scripts, so these tests run on macOS and Linux (install.ps1 via pwsh).
POSIX = os.name == "posix"

CORTEX_STUB = """#!/bin/sh
echo "$*" >> "$STUB_LOG"
if [ "$1 $2" = "plugin list" ]; then
  [ -d "$HOME/.snowflake/cortex/plugins/snowflake-migration" ] && echo "  snowflake-migration v2.52.5 [enabled, managed]"
  exit 0
fi
if [ "$1 $2" = "plugin install" ]; then
  [ "${STUB_AIM_RC:-0}" = 0 ] && sh "$STUB_MAKE_AIM"
  exit "${STUB_AIM_RC:-0}"
fi
exit 0
"""

# Lays down a fake AIM plugin whose dependency installers record that they ran.
MAKE_AIM = """#!/bin/sh
d="$HOME/.snowflake/cortex/plugins/snowflake-migration/hooks"
mkdir -p "$d"
printf '#!/bin/sh\\necho deps >> "$STUB_LOG"\\nexit "${STUB_DEPS_RC:-0}"\\n' > "$d/install-dependencies.sh"
printf 'Add-Content -Path $env:STUB_LOG -Value deps\\nexit [int]$env:STUB_DEPS_RC\\n' > "$d/install-dependencies.ps1"
"""


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class InstallerHarness:
    """Runs one installer against stub CLIs and reports output and cortex calls."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="installer_test_"))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.tmp / ".snowflake").mkdir()
        (self.tmp / ".snowflake" / "connections.toml").write_text("")
        self.log = self.tmp / "cortex.log"
        self.make_aim = self.tmp / "make_aim.sh"
        self.make_aim.write_text(MAKE_AIM)
        for name, body in (("cortex", CORTEX_STUB), ("snow", "#!/bin/sh\nexit 0\n")):
            stub = self.bin / name
            stub.write_text(body)
            stub.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_installer(self, *args, aim_listed=False, aim_rc=0, deps_rc=0, scai=False):
        env = {
            "HOME": str(self.tmp),
            "USERPROFILE": str(self.tmp),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "STUB_LOG": str(self.log),
            "STUB_AIM_RC": str(aim_rc),
            "STUB_DEPS_RC": str(deps_rc),
            "STUB_MAKE_AIM": str(self.make_aim),
        }
        env.update(getattr(self, "extra_env", {}))
        if aim_listed:
            subprocess.run(["sh", str(self.make_aim)], env=env, check=True)
        if scai:
            stub = self.bin / "scai"
            stub.write_text("#!/bin/sh\nexit 0\n")
            stub.chmod(0o755)
        result = subprocess.run(self.command(*args), env=env, cwd=self.tmp,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        return result.returncode, strip_ansi(result.stdout + result.stderr), calls

    def aim_installs(self, calls):
        return [c for c in calls if c.startswith("plugin install")]

    # The flag's name differs per installer; subclasses set FLAG.

    def test_default_run_never_touches_aim(self):
        rc, out, calls = self.run_installer()
        self.assertEqual(rc, 0, out)
        self.assertEqual(calls, [], "default run must not call cortex at all")
        self.assertNotIn("AIM", out)

    def test_include_aim_installs_the_aim_plugin_and_its_dependencies(self):
        rc, out, calls = self.run_installer(self.FLAG)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.aim_installs(calls), [f"plugin install {AIM_SOURCE}"])
        # Headless Cortex sessions skip AIM's SessionStart hook, so the installer runs
        # AIM's own dependency installer (scai) itself.
        self.assertEqual(calls.count("deps"), 1, calls)
        self.assertIn("Snowflake AIM plugin installed", out)
        self.assertIn("SnowConvert AI (scai) installed", out)

    def test_include_aim_skips_when_already_installed(self):
        rc, out, calls = self.run_installer(self.FLAG, aim_listed=True, scai=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.aim_installs(calls), [])
        self.assertNotIn("deps", calls)
        self.assertIn("Snowflake AIM plugin already installed", out)

    def test_include_aim_repairs_missing_scai(self):
        rc, out, calls = self.run_installer(self.FLAG, aim_listed=True)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.aim_installs(calls), [])
        self.assertEqual(calls.count("deps"), 1, calls)

    def test_failed_dependency_install_warns_and_explains_retry(self):
        rc, out, calls = self.run_installer(self.FLAG, deps_rc=1)
        self.assertEqual(rc, 0, out)
        self.assertIn("Could not install SnowConvert AI (scai)", out)
        self.assertIn("install-dependencies", out)
        self.assertIn("All done!", out)

    def test_failed_aim_install_keeps_cortex_and_explains_retry(self):
        rc, out, calls = self.run_installer(self.FLAG, aim_rc=1)
        self.assertEqual(rc, 0, out)
        self.assertIn("Cortex Code CLI (cortex) already installed", out)
        self.assertIn(f"cortex plugin install {AIM_SOURCE}", out)
        self.assertNotIn("deps", calls)
        self.assertIn("All done!", out)

    def test_check_reports_aim_status_only_with_flag(self):
        _, out, calls = self.run_installer(self.CHECK)
        self.assertNotIn("AIM", out)
        self.assertEqual(calls, [])
        _, out, calls = self.run_installer(self.CHECK, self.FLAG, aim_listed=True)
        self.assertIn("Snowflake AIM plugin installed", out)
        self.assertEqual(self.aim_installs(calls), [])

    def test_help_documents_flag(self):
        _, out, _ = self.run_installer(self.HELP)
        self.assertIn(self.FLAG, out)
        self.assertIn("AIM", out)


@unittest.skipUnless(POSIX, "stub CLIs need a POSIX shell")
class InstallShTests(InstallerHarness, unittest.TestCase):
    FLAG, CHECK, HELP = "--include-aim", "--check", "--help"

    def command(self, *args):
        return ["bash", str(REPO_ROOT / "install.sh"), *args]


@unittest.skipUnless(POSIX and PWSH, "needs pwsh on macOS or Linux")
class InstallPs1Tests(InstallerHarness, unittest.TestCase):
    FLAG, CHECK, HELP = "-IncludeAim", "-Check", "-Help"

    def command(self, *args):
        return [PWSH, "-NoProfile", "-NonInteractive", "-File", str(REPO_ROOT / "install.ps1"), *args]

    def test_finds_scai_where_aim_installs_it_on_windows(self):
        # AIM puts scai in %LOCALAPPDATA%\snowconvertai\bin and adds that to the user PATH,
        # which the current window doesn't see until a new terminal.
        scai = self.tmp / "AppData" / "Local" / "snowconvertai" / "bin" / "scai.cmd"
        scai.parent.mkdir(parents=True)
        scai.write_text("")
        self.extra_env = {"LOCALAPPDATA": str(self.tmp / "AppData" / "Local")}
        rc, out, calls = self.run_installer(self.FLAG, aim_listed=True)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("deps", calls)


if __name__ == "__main__":
    unittest.main()
