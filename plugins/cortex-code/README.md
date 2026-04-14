# Cortex Code plugin for Claude Code

Use Cortex Code (CoCo) from inside Claude Code for code reviews or to delegate tasks.

## What You Get

- `/cortex-code:review` for a Cortex Code review of your changes
- `/cortex-code:adversarial-review` for a steerable challenge review
- `/cortex-code:data-review` for Snowflake data engineering review (SQL, pipelines, schema, warehouse cost)
- `/cortex-code:dbt-review` for dbt model review (materialization, testing, lineage)
- `/cortex-code:sql-review` for Snowflake SQL optimization review (performance, anti-patterns, cost)
- `/cortex-code:security-review` for Snowflake security review (RBAC, credentials, data governance)
- `/cortex-code:rescue` to delegate work to Cortex Code
- `/cortex-code:status`, `/cortex-code:result`, `/cortex-code:cancel` to manage background jobs

## Requirements

- **Cortex Code CLI** (`cortex`) installed and on your PATH
- **Node.js 18.18 or later**

## Install

### Via the AI Kit installer (recommended)

From the [repo root](../../):

```bash
bash install.sh --with-plugin
```

This installs Snowflake CLI, Cortex Code CLI, Claude Code CLI, the router skill, and sets up the plugin.

### Manual setup

Prerequisites: [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code), Node.js 18.18+.

If you cloned the repo, register the plugin in Claude Code:

```
/plugins add /path/to/snowflake-ai-kit/plugins
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
