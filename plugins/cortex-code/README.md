# Cortex Code plugin for Claude Code

Use Cortex Code (CoCo) from inside Claude Code — slash commands for reviews and task delegation, plus automatic routing of Snowflake operations.

## What You Get

### Slash Commands (explicit)

- `/cortex-code:review` for a Cortex Code review of your changes
- `/cortex-code:adversarial-review` for a steerable challenge review
- `/cortex-code:data-review` for Snowflake data engineering review (SQL, pipelines, schema, warehouse cost)
- `/cortex-code:dbt-review` for dbt model review (materialization, testing, lineage)
- `/cortex-code:sql-review` for Snowflake SQL optimization review (performance, anti-patterns, cost)
- `/cortex-code:security-review` for Snowflake security review (RBAC, credentials, data governance)
- `/cortex-code:rescue` to delegate work to Cortex Code
- `/cortex-code:status`, `/cortex-code:result`, `/cortex-code:cancel` to manage background jobs
- `/cortex-code:router-setup` to discover Cortex skills and verify auto-routing
- `/cortex-code:router-config` to view or change auto-routing settings

### Auto-Routing (implicit)

The plugin includes a built-in router that automatically detects Snowflake-related prompts and routes them to Cortex Code — no slash command needed. Just ask about your Snowflake data naturally.

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
- **Node.js 18.18 or later**

## Install

### Via the Claude Code marketplace (recommended)

Run from your terminal (not inside a Claude Code session):

```bash
claude plugin marketplace add https://github.com/Snowflake-Labs/snowflake-ai-kit
claude plugin install cortex-code-plugin@snowflake-ai-kit
```

To update later: `claude plugin update cortex-code-plugin`

### Manual setup (local clone)

Prerequisites: [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code), Node.js 18.18+.

If you cloned the repo, add the marketplace from the local path:

```bash
claude plugin marketplace add /path/to/snowflake-ai-kit
claude plugin install cortex-code-plugin@snowflake-ai-kit
```

### Setup

Then run:

```bash
/cortex-code:setup
```

This checks whether the `cortex` CLI is installed and ready.

One simple first run:

```bash
/cortex-code:review --background
/cortex-code:status
/cortex-code:result
```

## Usage

### `/cortex-code:review`

Runs a Cortex Code review on your current work.

```bash
/cortex-code:review
/cortex-code:review --base main
/cortex-code:review --background
```

Use `--base <ref>` for branch review. Supports `--wait` and `--background`.
This command is read-only.

### `/cortex-code:adversarial-review`

Runs a **steerable** review that questions the implementation and design.

```bash
/cortex-code:adversarial-review
/cortex-code:adversarial-review --base main challenge whether this caching design is safe
/cortex-code:adversarial-review --background look for race conditions
```

Takes optional focus text after the flags. Read-only.

### `/cortex-code:data-review`

Snowflake data engineering review: SQL correctness, pipeline reliability, schema evolution, warehouse cost.

```bash
/cortex-code:data-review
/cortex-code:data-review --base main focus on the COPY INTO changes
```

### `/cortex-code:dbt-review`

dbt model review: materialization strategy, incremental correctness, testing coverage, lineage impact.

```bash
/cortex-code:dbt-review
/cortex-code:dbt-review --background
```

### `/cortex-code:sql-review`

Snowflake SQL optimization: query performance, anti-patterns, cost.

```bash
/cortex-code:sql-review
```

### `/cortex-code:security-review`

Snowflake security: RBAC, credentials, data governance, access policies.

```bash
/cortex-code:security-review
```

### `/cortex-code:rescue`

Hands a task to Cortex Code.

```bash
/cortex-code:rescue investigate why the tests started failing
/cortex-code:rescue fix the failing test with the smallest safe patch
/cortex-code:rescue --background investigate the regression
/cortex-code:rescue -c my_connection --model claude-sonnet-4-5-20250514 fix the bug
```

Supports `-c connection`, `--model`, `--effort`, `--write`, `--background`.

### `/cortex-code:status`

Shows running and recent Cortex Code jobs.

```bash
/cortex-code:status
/cortex-code:status task-abc123
```

### `/cortex-code:result`

Shows the stored output for a finished job.

```bash
/cortex-code:result
/cortex-code:result task-abc123
```

### `/cortex-code:cancel`

Cancels an active background job.

```bash
/cortex-code:cancel
/cortex-code:cancel task-abc123
```

## Typical Flows

### Review Before Shipping

```bash
/cortex-code:review
```

### Hand A Problem To Cortex Code

```bash
/cortex-code:rescue investigate why the build is failing in CI
```

### Start Something Long-Running

```bash
/cortex-code:adversarial-review --background
/cortex-code:rescue --background investigate the flaky test
```

Then check in with:

```bash
/cortex-code:status
/cortex-code:result
```

## Auto-Routing

### How It Works

The plugin includes a `cortex-router` skill that activates automatically (no slash command needed). On session start, it:

1. Runs `discover_cortex.py` to enumerate available Cortex skills
2. Caches the result to `/tmp/cortex-capabilities.json`
3. Listens for Snowflake-related prompts during the session

When you type a prompt, the router uses LLM-based semantic analysis (not keyword matching) to decide whether to route to Cortex Code or handle locally in Claude Code.

### Security Model

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

### Configuration

```bash
# View current settings
/cortex-code:router-config

# Change approval mode
/cortex-code:router-config --set approval_mode=auto

# Full config file
~/.claude/skills/cortex-code/config.yaml
```

See `scripts/router/config.yaml.example` for all available options.

### Re-discover Skills

If Cortex skills change mid-session:

```bash
/cortex-code:router-setup
```
