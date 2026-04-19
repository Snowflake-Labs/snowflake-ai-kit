---
name: cortex-setup
description: Install Snowflake CLI and Cortex Code CLI. Use when cortex is not installed, when the user asks to set up Cortex Code, or when routing fails because the CLI is missing. Triggers: setup cortex, install cortex, cortex not found, CLI not installed, set up snowflake.
---

# Cortex Code Setup

Install Snowflake CLI (`snow`) and Cortex Code CLI (`cortex`) using the bundled installer.

## When to use

- Cortex Code CLI is not found on PATH
- User asks to set up or install Cortex Code
- Routing failed because `cortex` binary is missing

## Steps

### 1. Check current state

```bash
which cortex 2>/dev/null && cortex --version || echo "cortex not installed"
which snow 2>/dev/null && snow --version || echo "snow not installed"
```

### 2. Run the installer

The installer is bundled with this plugin's parent repo. Run it:

```bash
bash "${CLAUDE_PLUGIN_ROOT}/../../install.sh"
```

If `CLAUDE_PLUGIN_ROOT` is not set, use the known path:

```bash
bash ~/Apps/snowflake-ai-kit/install.sh
```

The installer handles:
- Snowflake CLI (`snow`) via pipx/pip/brew
- Cortex Code CLI (`cortex`) via the official installer
- PATH configuration

### 3. Verify installation

```bash
cortex --version
snow --version
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

- The installer requires Python 3.10+ on the system
- On macOS, Homebrew may be used as a fallback for Snow CLI
- The installer is idempotent — safe to run again if partially completed
- Do NOT suggest `pip install snowflake-cortex-code` or similar — that package does not exist
