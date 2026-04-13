# Agent Guidelines — snowflake-ai-kit

## What This Repo Is

Developer tools for building on Snowflake with AI coding agents. Includes installers (shell + PowerShell + npx), a Claude-to-Cortex Code router skill, and a sample Cortex Agent chat app (React + FastAPI).

**Org:** Snowflake-Labs (INTERNAL visibility)

## Architecture

```
install.sh / install.ps1 / bin/install.mjs   ← one-command installers
agent-to-agent-skills/
  claude-cortex-code-router/                  ← router skill v2.0.0
    SKILL.md                                  ← skill definition (installed to ~/.claude/skills/cortex-code/)
    scripts/
      discover_cortex.py                      ← dual-format parser (discovers 32+ skills)
      execute_cortex.py                       ← stdin=DEVNULL fix required
    tests/                                    ← 209 tests (96 unit, 45 integration, 46 security, 22 regression)
    security/                                 ← security envelope implementation
    config.yaml.example
builder-apps/
  cortex-agent/                               ← React + FastAPI sample app
tests/
  run-tests.ps1                               ← PowerShell test runner
  validate-install.ps1                        ← install validation
```

## Critical Rules

1. **All 209 tests must pass before merging.** Run `cd agent-to-agent-skills/claude-cortex-code-router && pytest tests/` to verify.
2. **License split:** Root LICENSE is Apache 2.0. The router skill README states "Copyright 2026 Snowflake Inc. All rights reserved." Do not change either.
3. **Branch protection:** PRs required on main. 0 approvals needed, bypass allowed.
4. **Never commit credentials.** Use environment variables or Snowflake built-in auth.
5. **README uses HTTPS clone URLs** (not SSH) — keep it that way for external users.

## Python Scripts

- `discover_cortex.py` — parses Cortex Code skill output in two formats (table and list). If the output format changes, both parsers need updating.
- `execute_cortex.py` — spawns `cortex` CLI. The `stdin=DEVNULL` fix prevents the subprocess from stealing terminal input. Do not remove it.

## Related Repos

- `Snowflake-Labs/subagent-cortex-code` — public repo with the same router skill, still at v1.0.0 strings. Changes here should eventually be synced there.
- `snowflake-eng/cortex-code-skills` — bundled skills repo (separate from this).

## Installers

The three installers (`install.sh`, `install.ps1`, `bin/install.mjs`) share the same logic:
- Install Snow CLI + Cortex Code CLI by default
- `--with-claude` / `-WithClaude` adds Claude Code CLI + router skill
- `--check` / `--update` / `--list` flags for status, re-install, and listing
- Skip anything already installed; verify Snowflake connection at the end

Do not convert these to `pip install` or `npm install` patterns — they are intentionally standalone.

## Auth

- SSH remote (id_rsa key for Snowflake-Labs)
- `gh auth login` (iamontheinet account) for GitHub CLI operations
