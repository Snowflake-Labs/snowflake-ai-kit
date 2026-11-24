---
name: cortex-setup
description: "Install Snowflake CLI and Cortex Code CLI. Use when cortex is not installed, when the user asks to set up Cortex Code, or when routing fails because the CLI is missing. In Devin, also installs Snowflake AIM for database migrations. Triggers: setup cortex, install cortex, cortex not found, CLI not installed, set up snowflake, install AIM, set up migrations."
license: Proprietary. See LICENSE-SKILLS.md for complete terms
---

# Cortex Code Setup

Install Snowflake CLI (`snow`) and Cortex Code CLI (`cortex`) using the appropriate installer for the current OS.

## Prerequisite — ALWAYS run this FIRST, unconditionally

Before doing ANYTHING else in this skill, you MUST run this check. This is not optional. Do not skip it even if the CLIs are already installed.

Use the host that's running this skill: `claude_code`, `codex`, or `devin_cli` (also for Devin Desktop). In Devin, `${CLAUDE_PLUGIN_ROOT}` isn't set; replace it with the absolute plugin root the prompt hook gives you.

```bash
bash "${CLAUDE_PLUGIN_ROOT}/scripts/run_python.sh" - "${CLAUDE_PLUGIN_ROOT}" <host> <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, os.path.join(sys.argv[1], "scripts", "router"))
import hosts
found = hosts.find_snowflake_mcp_server(hosts.by_name(sys.argv[2]), Path.home(), Path.cwd(), os.environ)
if found:
    print(f"CONFLICT: {found[0]} in {found[1]}")
    sys.exit(1)
print("OK: No Snowflake MCP server found")
PY
```

This is the same check the plugin's prompt hook runs, so it reads every MCP config file the agent reads.

**If exit code is 1 (conflict found)**, STOP IMMEDIATELY and tell the user:

> ⚠️ **Snowflake MCP Server detected.** The Cortex Code plugin replaces the Snowflake MCP server with more capabilities (security envelopes, session management, multi-turn). Please disable the MCP server before continuing:
>
> 1. Open the config file named in the CONFLICT line (Devin: run `devin mcp list`, then `devin mcp disable <name>`)
> 2. Remove or disable that Snowflake MCP server entry
> 3. Restart your agent (Claude Code, Codex, Devin CLI, or Devin Desktop)
>
> Then re-run this setup.

**Do NOT proceed. Do NOT check CLI versions. Do NOT install anything. STOP HERE.**

---

## When to use

- Cortex Code CLI is not found on PATH
- User asks to set up or install Cortex Code
- Routing failed because `cortex` binary is missing

## Steps

### 1. Detect OS and check current state

```python
import platform
print(platform.system())  # "Windows", "Darwin", or "Linux"
```

**Windows (Command Prompt or PowerShell):**
```cmd
where cortex 2>nul && cortex --version || echo "cortex not installed"
where snow 2>nul && snow --version || echo "snow not installed"
```

**macOS / Linux:**
```bash
which cortex 2>/dev/null && cortex --version || echo "cortex not installed"
which snow 2>/dev/null && snow --version || echo "snow not installed"
```

### 2. Install Cortex Code CLI

The installer is bundled with the snowflake-ai-kit repo. Find and run it:

**Step 2a — Find the installer:**

macOS / Linux:
```bash
find ~ -maxdepth 4 -name "install.sh" -path "*/snowflake-ai-kit/*" 2>/dev/null | head -1
```

Windows (PowerShell):
```powershell
Get-ChildItem -Path $HOME -Recurse -Depth 4 -Filter "install.ps1" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "snowflake-ai-kit" } | Select-Object -First 1 -ExpandProperty FullName
```

**Step 2b — Run the installer:**

In Devin CLI or Devin Desktop, add `--include-aim` (Windows: `-IncludeAim`). It also installs the Snowflake AIM plugin (`snowflake-migration`), which Devin uses for database migrations. In Claude Code and Codex, run the installer without it.

If found (macOS/Linux):
```bash
bash /path/to/snowflake-ai-kit/install.sh
```

If found (Windows — look for install.ps1 in the same directory):
```powershell
powershell -ExecutionPolicy Bypass -File /path/to/snowflake-ai-kit/install.ps1
```

If NOT found, install Cortex Code CLI directly:

macOS / Linux:
```bash
curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh
```

Windows (PowerShell):
```powershell
irm https://ai.snowflake.com/static/cc-scripts/install.ps1 | iex
```

Or follow the official install guide: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli

The installer handles Snowflake CLI, Cortex Code CLI, and connection verification.

**Step 2c — Devin CLI or Devin Desktop only: make sure the Snowflake AIM plugin is installed.** Do this even when Cortex Code CLI was already installed, and after a direct install. Check first:

```bash
cortex plugin list
```

If `snowflake-migration` isn't listed, install it:

```bash
cortex plugin install https://github.com/Snowflake-Labs/cortex-code-migrations/tree/main/plugin
```

Then, even if `snowflake-migration` was already listed, make sure SnowConvert AI (`scai`), which AIM needs, is installed. AIM normally installs it from a session-start hook, but routed Cortex sessions don't run that hook, so run the same script directly if `scai --version` fails:

macOS / Linux:
```bash
scai --version || bash ~/.snowflake/cortex/plugins/snowflake-migration/hooks/install-dependencies.sh
```

Windows (PowerShell):
```powershell
scai --version; if ($LASTEXITCODE -ne 0) { powershell -ExecutionPolicy Bypass -File "$HOME\.snowflake\cortex\plugins\snowflake-migration\hooks\install-dependencies.ps1" }
```

It installs `scai` into `~/.local/bin` (Windows: `%LOCALAPPDATA%\snowconvertai\bin`, which needs a new terminal to be on PATH). If either step fails, tell the user and continue: Cortex Code still works, and Cortex Code offers to install AIM the first time they start a migration. SnowConvert's terms and source drivers are set up when the first migration starts.

### 3. Verify installation

**Windows:**
```cmd
where cortex && cortex --version
where snow && snow --version
```

**macOS / Linux:**
```bash
which cortex && cortex --version
which snow && snow --version
```

Both commands should return version numbers.

### 4. Set up Snowflake connection

Check if a connection exists:

```bash
snow connection list
```

If no connections exist, prompt the user to create one:

```bash
snow connection add
```

This is interactive — the user will need to provide their Snowflake account URL, username, and authentication method.

### 5. Confirm routing works

After setup, the cortex-router skill should work. Tell the user to try their original Snowflake prompt again.

## Notes

- Cortex Code CLI installer requires an active internet connection
- On macOS, Homebrew may be used as a fallback for Snow CLI
- Do NOT suggest `pip install snowflake-cortex-code` or similar — that package does not exist
- On Windows, if `bash` is not available, use the PowerShell installer (`install.ps1`)
