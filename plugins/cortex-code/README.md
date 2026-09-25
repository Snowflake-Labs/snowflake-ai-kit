# Cortex Code plugin for Claude Code and OpenAI Codex

Route Snowflake work from Claude Code or OpenAI Codex to Cortex Code automatically.
The default backend is the local CLI. An opt-in remote backend delegates to a
host-authenticated Snowflake-managed MCP Coding Agent without a local Cortex CLI.
Non-Snowflake prompts stay in your current agent.

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

- **Python** for the plugin hooks and helpers.
- **Local mode (default):** Cortex Code CLI (`cortex`) installed and configured.
- **Remote mode:** an authenticated native MCP connection in your host, exposing
  a Coding Agent with `code_toolset_all`. See [Remote MCP setup](REMOTE_MCP.md).

## Choose a backend

Leave settings unset for the existing local flow. For remote mode, set these
before launching Claude Code or Codex:

```bash
export CORTEX_PLUGIN_BACKEND=remote
export CORTEX_PLUGIN_MCP_TOOL=mcp__snowflake__cortex_code_agent
```

Replace the example with the **exact host-visible tool identifier**. The host
owns authentication; the plugin neither stores credentials nor connects by URL.
Missing/invalid configuration or an unavailable tool blocks delegation, with
no automatic fallback. [Setup, limitations and smoke tests](REMOTE_MCP.md).

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

## Local Security Model

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

**Remote mode does not inherit local envelope enforcement or audit logging.**
The host approves the outer MCP call; the remote agent policy controls inner
commands. The workflow obtains consent to this difference before delegation.
Organizations requiring per-command local policy must not use remote mode.
See [approval and data boundaries](REMOTE_MCP.md#approval-and-data-boundaries).

## Configuration

The router config file lives at `scripts/router/config.yaml.example`. To customize:

```bash
cp plugins/cortex-code/scripts/router/config.yaml.example ~/.claude/skills/cortex-code/config.yaml
```

Edit the config to change approval mode, allowed envelopes, audit settings, and sanitization options.

Local skill discovery runs automatically on session start. Remote mode skips it
and lets the hosted agent discover its own skills. Restart the host after changing
backend settings. Remote continuation uses returned `thread_id` only when the
server advertises support; local `--resume-last` is unchanged.

## Testing

Tests live in `tests/run-tests.sh` at the repo root. Two tiers:

```bash
# Structural + unit tests (no network, runs in CI)
bash tests/run-tests.sh

# Include integration tests (requires cortex CLI + Snowflake connection)
bash tests/run-tests.sh --integration
```

**Structural tests** (always run): file existence checks, config validation, Python syntax, and unit tests for `envelope_policy.py`, `prompt_filter.py`, and plugin hooks.

**Integration tests** (`--integration` flag): spawn real Cortex CLI sessions against a live Snowflake connection. Located at `scripts/router/test_integration.py`. Verifies:

- Credential path blocking (prompts referencing `.ssh/`, `.env`, etc. are rejected pre-flight)
- End-to-end query flow (RO envelope, permission protocol, result event)
- Envelope enforcement (RO blocks DDL — via hard gate denial or LLM self-policing)
- Process cleanup (no orphaned `cortex` processes after execution)

Set `CORTEX_TEST_CONNECTION` env var to test against a specific Snowflake connection (defaults to your CLI default).

## License

Copyright (c) Snowflake Inc. All rights reserved.

The skills in this project are licensed under the [Snowflake Skills License](../../LICENSE-SKILLS.md).
