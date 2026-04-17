# Cortex Code Skill — Cursor Setup

Enables Cursor to route Snowflake queries to Cortex Code CLI automatically.

## Prerequisites

- Cursor IDE
- Cortex Code CLI installed and configured (`which cortex` should return a path)
- Active Snowflake connection in Cortex (`cortex connections list`)

## Install

**Option A — From repo:**

```bash
git clone https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit
bash integrations/cursor/install.sh
```

**Option B — Via the unified installer:**

```bash
bash install.sh --with-cursor
```

Both methods install the skill to `~/.cursor/skills-cursor/cortex-code/` and copy the routing rule to `~/.cursor/rules/`.

## What gets installed

1. **Skill files** — SKILL.md + Python scripts from `agent-to-agent-skills/claude-cortex-code-router/`
2. **Routing rule** — `cortex-snowflake-routing.mdc` in `~/.cursor/rules/`

The routing rule instructs Cursor to invoke `/cortex-code` whenever you ask about Snowflake, SQL, or Cortex topics — without typing the slash command.

**Without rule:** you type `/cortex-code how many databases do I have?`
**With rule:** you type `how many databases do I have?` and Cursor routes it automatically.

## Verify

```bash
ls ~/.cursor/skills-cursor/cortex-code/SKILL.md
ls ~/.cursor/rules/cortex-snowflake-routing.mdc
```

## Uninstall

```bash
bash integrations/cursor/uninstall.sh
```

## Troubleshooting

**Skill not found in Cursor:** Restart Cursor after install.

**Cortex hangs or no output:** Check your Cortex connection:
```bash
cortex connections list
cortex -p "SHOW DATABASES;" --bypass --output-format stream-json
```

**Rule not auto-triggering:** Confirm the `.mdc` file is in `~/.cursor/rules/` (global).
