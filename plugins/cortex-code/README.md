# Cortex Code plugin for Claude Code

Route Snowflake work from Claude Code to Cortex Code automatically. Ask about your data naturally — the plugin detects Snowflake intent and delegates to Cortex Code where 35+ built-in skills handle the work. Non-Snowflake prompts stay in Claude Code.

## How It Works

The plugin includes a `cortex-router` skill that activates automatically. On session start, it:

1. Runs `discover_cortex.py` to enumerate available Cortex skills
2. Caches the result locally (SHA256-validated, 24-hour TTL)
3. Listens for Snowflake-related prompts during the session

When you type a prompt, a lightweight keyword filter (`prompt_filter.py`) checks for Snowflake-related patterns and routes matching prompts to Cortex Code.

Examples that auto-route to Cortex Code:
- "Show me the top 10 customers by revenue"
- "Check data quality for the SALES_DATA table"
- "Create a dynamic table that refreshes hourly"

Examples that stay in Claude Code:
- "Read the config.json file"
- "Fix the bug in auth.py"
- "Write a Python unit test"

## Requirements

- **Cortex Code CLI** (`cortex`) installed and on your PATH

## Install

### Via the Claude Code marketplace (recommended)

Run from your terminal (not inside a Claude Code session):

```bash
claude plugin marketplace add https://github.com/Snowflake-Labs/snowflake-ai-kit
claude plugin install cortex-code@snowflake-ai-kit
```

To update later: `claude plugin update cortex-code`

### Manual setup (local clone)

Prerequisites: [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code).

If you cloned the repo, add the marketplace from the local path:

```bash
claude plugin marketplace add /path/to/snowflake-ai-kit
claude plugin install cortex-code@snowflake-ai-kit
```

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

The router config file lives at `scripts/router/config.yaml.example`. To customize:

```bash
cp plugins/cortex-code/scripts/router/config.yaml.example ~/.claude/skills/cortex-code/config.yaml
```

Edit the config to change approval mode, allowed envelopes, audit settings, and sanitization options.

Skill discovery runs automatically on session start. To force a re-discovery, start a new Claude Code session.
