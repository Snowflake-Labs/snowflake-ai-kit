# Claude-to-Cortex Code Router

Route Snowflake operations from Claude Code to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) for specialized Snowflake expertise. Cortex Code has 30+ built-in Snowflake skills (data quality, semantic views, cost intelligence, dynamic tables, ML pipelines, and more) that Claude Code can tap into through this skill.

> **Attribution:** This skill is inspired by [sfc-gh-tjia/claude_skill_cortexcode](https://github.com/sfc-gh-tjia/claude_skill_cortexcode), which pioneered the multi-agent routing pattern between Claude Code and Cortex Code.

## What It Does

When you're working in Claude Code and need Snowflake-specific expertise, this skill delegates the task to Cortex Code running headlessly. Cortex Code executes the Snowflake work (SQL, data quality checks, pipeline setup, etc.) and streams results back to your Claude Code session.

```
Your request → Claude Code → Cortex Code CLI (headless) → Snowflake → Results back in Claude Code
```

**Why delegate instead of doing it directly?** Cortex Code is trained specifically on Snowflake's technical stack — it knows the nuances of metadata views, when to use dynamic tables vs streams, how to debug semantic views, and has 30+ specialized skills that activate automatically.

## Prerequisites

- [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) v1.0.42+ installed and in PATH
- A configured Snowflake connection (`cortex connections create`)
- Python 3.8+ (scripts use stdlib only — no pip install needed)

Verify your setup:
```bash
cortex --version        # Should show v1.0.42+
cortex connections list # Should show at least one connection
```

## Usage

### With Claude Code

Copy `SKILL.md` into your Claude Code rules:
```bash
cp snowflake-ai-kit/snowflake-skills/claude-cortex-code-router/SKILL.md .claude/rules/claude-cortex-code-router.md
```

Then in Claude Code, say things like:
- "Use Cortex Code to check data quality on my SALES table"
- "Delegate this Snowflake task to Cortex Code"
- "Route this to Cortex — set up a dynamic tables pipeline"

### With Other Agents

Copy `SKILL.md` into your agent's rules directory. See the [main README](../../README.md) for per-agent instructions.

## Security Envelopes

Control what Cortex Code can do during execution:

| Envelope | Use Case | Blocked |
|----------|----------|---------|
| **RO** | Queries, exploration | Edit, Write, destructive Bash |
| **RW** | DDL/DML, file creation | Destructive Bash (rm -rf, sudo) |
| **RESEARCH** | Read + web search | Write operations |
| **DEPLOY** | Full access | Nothing |

The skill asks you to choose an envelope before executing. Default is **RW**.

## How It Works

1. **Routing**: Claude Code's SKILL.md triggers activate when you mention Snowflake + Cortex delegation
2. **Discovery** (optional): `discover_cortex.py` enumerates Cortex Code's 30+ bundled skills
3. **Execution**: `execute_cortex.py` invokes `cortex` CLI with `--input-format stream-json` (programmatic auto-approval mode)
4. **Security**: `--disallowed-tools` blocklist enforces the chosen security envelope
5. **Results**: NDJSON event stream is parsed and surfaced in Claude Code

### Key Implementation Detail

The `--input-format stream-json` flag puts Cortex Code in programmatic mode where tool calls auto-execute without interactive prompts. This works for all tool types (built-in, Snowflake SQL, MCP, data_diff) without requiring `--bypass` which may be disabled by org policy. Security is enforced at the tool level via `--disallowed-tools`.
