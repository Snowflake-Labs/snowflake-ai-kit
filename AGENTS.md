# Agent Guidelines — snowflake-ai-kit

## What This Repo Is

Developer tools for building on Snowflake with AI coding agents. Includes a Claude Code plugin (auto-routes Snowflake prompts to Cortex Code), installers (shell + PowerShell + npx), a standalone router skill, and a sample Cortex Agent chat app (React + FastAPI).

## Architecture

```
plugins/
  cortex-code/                                ← Claude Code plugin (v3.0.1)
    .claude-plugin/plugin.json                ← plugin manifest
    hooks/hooks.json                          ← UserPromptSubmit hook (prompt_filter.py)
    scripts/router/
      prompt_filter.py                        ← keyword detection, fires additionalContext
      discover_cortex.py                      ← finds Cortex CLI + discovers skills
      execute_cortex.py                       ← spawns cortex CLI, credential blocking
      route_request.py                        ← indicator scoring + skill trigger matching
    skills/
      cortex-router/                          ← auto-routing skill
      cortex-run/                             ← explicit invocation ($cortex-run)
      cortex-setup/                           ← CLI install + connection setup
install.sh / install.ps1 / bin/install.mjs    ← one-command installers
agent-to-agent-skills/
  claude-cortex-code-router/                  ← standalone router skill (legacy)
builder-apps/
  cortex-agent/                               ← React + FastAPI sample app
tests/
  run-tests.ps1                               ← PowerShell test runner
  validate-install.ps1                        ← install validation
```

## Critical Rules

1. **Never commit credentials.** Use environment variables or Snowflake built-in auth.
2. **License:** Root LICENSE is Apache 2.0.
3. **Branch protection:** PRs required on main.
4. **README uses HTTPS clone URLs** (not SSH) — keep it that way for external users.

## Plugin Scripts

- `prompt_filter.py` — reads `message` field from stdin JSON. Returns `additionalContext` for Snowflake-related prompts, `{}` otherwise.
- `discover_cortex.py` — finds Cortex CLI binary and parses skill output. Has Windows/macOS/Linux path handling.
- `execute_cortex.py` — spawns `cortex` CLI subprocess. Key behaviors: credential path blocking (`CREDENTIAL_PATTERNS`), break-on-result, `process.terminate()` cleanup. The `stdin=DEVNULL` fix prevents the subprocess from stealing terminal input — do not remove it.
- `route_request.py` — scores prompts via keyword indicators and skill trigger matching. Known issue: single-word trigger matching at line 88 can produce false positives.

## Installers

The three installers (`install.sh`, `install.ps1`, `bin/install.mjs`) share the same logic:
- Install Snow CLI + Cortex Code CLI by default
- `--with-claude` / `-WithClaude` adds Claude Code CLI + router skill
- `--check` / `--update` / `--list` flags for status, re-install, and listing
- Skip anything already installed; verify Snowflake connection at the end

Do not convert these to `pip install` or `npm install` patterns — they are intentionally standalone.
