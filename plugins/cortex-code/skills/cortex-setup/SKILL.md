---
name: cortex-setup
description: Install Snowflake CLI and Cortex Code CLI. Use when cortex is not installed, when the user asks to set up Cortex Code, or when routing fails because the CLI is missing. Triggers: setup cortex, install cortex, cortex not found, CLI not installed, set up snowflake.
---

# Cortex Code Setup

Install Snowflake CLI (`snow`) and Cortex Code CLI (`cortex`) using the appropriate installer for the current OS.

## When to use

- Cortex Code CLI is not found on PATH
- User asks to set up or install Cortex Code
- Routing failed because `cortex` binary is missing

## Steps

### 1. Detect operating system

```python
import platform
print(platform.system())  # "Windows", "Darwin", or "Linux"
```

### 2. Check current state

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

### 3. Run the installer

**Option A — npx (any platform, requires Node.js):**

```bash
npx @snowflake-labs/ai-kit
```

**Option B — Windows (PowerShell, no Node.js):**

Run the bundled PowerShell installer:

```powershell
powershell -ExecutionPolicy Bypass -File "${CLAUDE_PLUGIN_ROOT}\..\..\install.ps1"
```

If that path does not exist (plugin installed from npm cache), run:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex"
```

**Option C — macOS / Linux (bash):**

```bash
bash "${CLAUDE_PLUGIN_ROOT}/../../install.sh"
```

If that path does not exist, run:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
```

The installer handles:
- Snowflake CLI (`snow`) via pipx/pip/brew (macOS/Linux) or pip (Windows)
- Cortex Code CLI (`cortex`) via the official installer
- PATH configuration

### 4. Verify installation

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

### 5. Set up Snowflake connection

Check if a connection exists:

```bash
snow connection list
```

If no connections exist, prompt the user to create one:

```bash
snow connection add
```

This is interactive — the user will need to provide their Snowflake account URL, username, and authentication method.

### 6. Confirm routing works

After setup, the cortex-router skill should work. Tell the user to try their original Snowflake prompt again.

## Notes

- The installer requires Python 3.10+ on the system
- On macOS, Homebrew may be used as a fallback for Snow CLI
- The installer is idempotent — safe to run again if partially completed
- Do NOT suggest `pip install snowflake-cortex-code` or similar — that package does not exist
- On Windows, if `bash` is not available, use the PowerShell (`install.ps1`) or npx method
