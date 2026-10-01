# Cortex Code plugin for Claude Code, OpenAI Codex, and opencode

Route Snowflake work from Claude Code, OpenAI Codex, or opencode to Cortex Code automatically. Ask about your data naturally — the plugin detects Snowflake intent and delegates to Cortex Code where 55+ built-in skills handle the work. Non-Snowflake prompts stay in your current agent.

## How It Works

**Two ways to route prompts to Cortex Code:**

### Auto-routing (default)

A lightweight keyword filter (`prompt_filter.py`) runs on every prompt. When it detects Snowflake-related patterns, it loads the `cortex-router` skill which delegates to Cortex Code.

Examples that auto-route:
- "Show me my Snowflake warehouses"
- "What databases do I have access to?"
- "List all tables in my current schema"

Examples that stay in your agent:
- "Read the config.json file"
- "Fix the bug in auth.py"
- "Write a Python unit test"

### Explicit invocation (`$cortex-run`)

Type `$cortex-run` followed by your prompt to force routing to Cortex Code, bypassing the keyword filter. Useful when:

- Auto-routing didn't pick up your prompt
- You want to be explicit about using Cortex Code
- Your prompt mixes Snowflake and non-Snowflake work

```
$cortex-run analyze query performance for the last 7 days
```

## Requirements

- **Cortex Code CLI** (`cortex`) installed and on your PATH

## Install

### Claude Code

```bash
claude plugin install snowflake-cortex-code@claude-plugins-official
```

To update: `claude plugin update snowflake-cortex-code`

### OpenAI Codex

```bash
codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit
codex plugin add snowflake-cortex-code@snowflake-ai-kit
```

Or inside Codex, open `/plugins` and install "Snowflake Cortex Code" from the Snowflake AI Kit marketplace.

### opencode

```bash
bash install.sh --with-opencode
```

This copies the plugin to `~/.config/opencode/plugins/` and routing rules to `~/.config/opencode/rules/` — both are loaded globally for all opencode sessions.

> **Note:** opencode has no pre-LLM hook equivalent to Claude Code's `UserPromptSubmit`, so routing is LLM-driven via the rules file plus a `tool.execute.before` hook that blocks direct `snow sql`/`snowsql` bash calls. In practice the LLM reliably calls `cortex_run` for Snowflake work given the rules file.

To update, re-run `bash install.sh --with-opencode`.

## Security Model

The router wraps Cortex execution with a security layer. Three approval modes:

| Mode | Behavior | Audit | Best For |
|------|----------|-------|----------|
| `prompt` (default) | Ask user before execution | Optional | Interactive, production |
| `auto` | Auto-approve | Required | Automated workflows |
| `envelope_only` | Auto-approve, no tool prediction | Required | Low latency, trusted envs |

**Security envelopes** control what Cortex can do:
- **RO**: Read-only — blocks Edit, Write, destructive Bash
- **RW**: Read-write — blocks destructive operations
- **RESEARCH**: Read + web access
- **DEPLOY**: Full access (use cautiously)

Built-in protections: PII sanitization, credential path blocking, SHA256-validated cache, structured audit logging.

## Configuration

Hooks and skill commands use `scripts/run_python.sh` in Bash (Git Bash on Windows).
The launcher prefers `python3` and accepts `python` only after verifying Python 3.
It preserves stdin and arguments and never retries a failed script with another interpreter.

The router config file lives at `scripts/router/config.yaml.example`. To customize:

```bash
cp plugins/cortex-code/scripts/router/config.yaml.example ~/.claude/skills/cortex-code/config.yaml
```

Edit the config to change approval mode, allowed envelopes, audit settings, and sanitization options.

YAML configuration requires **PyYAML in the interpreter selected by the launcher**.
From the repository root, install it in that environment with:

```bash
bash plugins/cortex-code/scripts/run_python.sh -m pip install PyYAML
```

If Python is externally managed, create and activate a virtual environment, install
PyYAML there, and start the host from that environment. Restart the host after
changing its PATH. Do not use `--break-system-packages`.

Without configuration files, built-in defaults work without PyYAML. If a user
config or `~/.snowflake/cortex/claude-skill-policy.yaml` exists, missing PyYAML,
unreadable files, invalid YAML, and invalid setting types **stop routing/execution**
with an error identifying the file. Empty files must be replaced with an explicit
mapping such as `{}`. Paths explicitly supplied through flags or
`CORTEX_SKILL_CONFIG` / `CORTEX_SKILL_ORG_POLICY` must exist; missing default paths
remain optional. An empty `allowed_envelopes` list permits no execution.

This validation does not implement approval-mode behavior: the live executor still
uses envelope decisions; the approval-mode wrapper remains a simulation.
The existing Codex execution path still auto-approves individual tool calls; this
change validates configuration and the selected envelope before launching it,
but does not add per-tool envelope enforcement to that path.

Skill discovery runs automatically on session start. To force a re-discovery, start a new session.

## Testing

Tests live in `tests/run-tests.sh` at the repo root. Two tiers:

```bash
# Structural + unit tests (no network, runs in CI)
bash tests/run-tests.sh

# Include integration tests (requires cortex CLI + Snowflake connection)
bash tests/run-tests.sh --integration
```

**Structural tests** (always run): file existence checks, config validation, Python syntax, and unit tests for `envelope_policy.py`, `prompt_filter.py`, and plugin hooks.

CI tests macOS and Windows with and without PyYAML. Launcher/configuration regressions
are in `scripts/router/test_launcher_config.py`; they do not invoke Cortex or Snowflake.
Parsing-specific tests are skipped when PyYAML is absent; missing-dependency and
fail-closed tests still run.

**Integration tests** (`--integration` flag): spawn real Cortex CLI sessions against a live Snowflake connection. Located at `scripts/router/test_integration.py`. Verifies:

- Credential path blocking (prompts referencing `.ssh/`, `.env`, etc. are rejected pre-flight)
- End-to-end query flow (RO envelope, permission protocol, result event)
- Envelope enforcement (RO blocks DDL — via hard gate denial or LLM self-policing)
- Process cleanup (no orphaned `cortex` processes after execution)

Set `CORTEX_TEST_CONNECTION` env var to test against a specific Snowflake connection (defaults to your CLI default).

## License

Copyright (c) Snowflake Inc. All rights reserved.

The skills in this project are licensed under the [Snowflake Skills License](../../LICENSE-SKILLS.md).
