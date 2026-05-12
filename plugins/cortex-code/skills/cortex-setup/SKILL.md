---
name: cortex-setup
description: "Install Snowflake CLI and Cortex Code CLI. Use when cortex is not installed, when the user asks to set up Cortex Code, or when routing fails because the CLI is missing. Triggers: setup cortex, install cortex, cortex not found, CLI not installed, set up snowflake."
license: Proprietary. See LICENSE-SKILLS.md for complete terms
---

# Cortex Code Setup

Install Snowflake CLI (`snow`) and Cortex Code CLI (`cortex`) using the appropriate installer for the current OS.

## Prerequisite — ALWAYS run this FIRST, unconditionally

Before doing ANYTHING else in this skill, you MUST run this check. This is not optional. Do not skip it even if the CLIs are already installed.

```bash
cat ~/.claude/settings.json 2>/dev/null | python3 -c "
import sys, json
try:
    settings = json.load(sys.stdin)
    servers = settings.get('mcpServers', {})
    for name, cfg in servers.items():
        cmd = cfg.get('command', '') + ' ' + ' '.join(cfg.get('args', []))
        if 'snowflake' in name.lower() or 'snowflake' in cmd.lower():
            print(f'CONFLICT: {name}')
            sys.exit(1)
except: pass
print('OK: No Snowflake MCP server found')
"
```

**If exit code is 1 (conflict found)**, STOP IMMEDIATELY and tell the user:

> ⚠️ **Snowflake MCP Server detected.** The Cortex Code plugin replaces the Snowflake MCP server with more capabilities (security envelopes, session management, multi-turn). Please disable the MCP server before continuing:
>
> 1. Open `~/.claude/settings.json`
> 2. Remove the Snowflake MCP server entry from `"mcpServers"`
> 3. Restart Claude Code
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

**Step 3a — Find the installer:**

macOS / Linux:
```bash
find ~ -maxdepth 4 -name "install.sh" -path "*/snowflake-ai-kit/*" 2>/dev/null | head -1
```

Windows (PowerShell):
```powershell
Get-ChildItem -Path $HOME -Recurse -Depth 4 -Filter "install.ps1" -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match "snowflake-ai-kit" } | Select-Object -First 1 -ExpandProperty FullName
```

**Step 3b — Run the installer:**

If found (macOS/Linux):
```bash
bash /path/to/snowflake-ai-kit/install.sh
```

If found (Windows — look for install.ps1 in the same directory):
```powershell
powershell -ExecutionPolicy Bypass -File /path/to/snowflake-ai-kit/install.ps1
```

If NOT found, ask the user to clone the repo first:
```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
bash snowflake-ai-kit/install.sh
```

The installer handles Snowflake CLI, Cortex Code CLI, and connection verification.

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
- On Windows, if `bash` is not available, use the PowerShell (`install.ps1`) or npx method
