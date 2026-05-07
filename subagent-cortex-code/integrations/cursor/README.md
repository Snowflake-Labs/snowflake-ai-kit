# Cortex Code Skill — Cursor Setup

Enables Cursor to route Snowflake queries to Cortex Code CLI automatically.

## Prerequisites

- Cursor IDE
- Cortex Code CLI installed and configured (`which cortex` should return a path)
- Active Snowflake connection in Cortex (`cortex connections list`)

## Install

**Step 1 — Install the skill:**

Recommended from a local clone:

```bash
bash integrations/cursor/install.sh
```

Or install the packaged skill via `npx`:

```bash
npx skills add snowflake-labs/subagent-cortex-code --copy --global
```

Both paths install the skill to `~/.cursor/skills/cortex-code/`.

**Step 2 — Activate the Cursor routing rule:**

```bash
mkdir -p ~/.cursor/rules
cp ~/.cursor/skills/cortex-code/cortex-snowflake-routing.mdc ~/.cursor/rules/
```

If you used `integrations/cursor/install.sh`, you can also copy the project-local rule template into a repository root as `.cursorrules`.

**Step 3 — Restart Cursor.**

That's it. Cursor will now automatically route Snowflake questions to Cortex Code.

## Security defaults

- The skill defaults to `approval_mode: prompt` and read-only (`RO`) behavior for reads.
- Cursor examples do not force `--approval-mode "auto"`.
- User config cannot relax approval mode or expand envelopes unless organization policy explicitly authorizes that field/value.
- Requested envelopes are checked against `security.allowed_envelopes` before routing, approval, or Cortex execution; `NONE` is rejected.
- Cache and audit logs use private cache/skill directories with restrictive permissions.

---

## What the routing rule does

The rule (`cortex-snowflake-routing.mdc`) instructs Cursor to invoke `/cortex-code` whenever you ask about Snowflake, SQL, or Cortex topics — without you needing to type the slash command.

**Without rule:** you type `/cortex-code how many databases do I have?`

**With rule:** you type `how many databases do I have?` and Cursor invokes the skill automatically.

### Rule content (copy-paste if you prefer manual setup)

Create `~/.cursor/rules/cortex-snowflake-routing.mdc`:

```
---
description: Route Snowflake queries to the cortex-code skill for specialized Snowflake expertise via Cortex Code CLI
globs:
alwaysApply: true
---

# Snowflake Query Routing

When the user asks about Snowflake, databases, warehouses, Cortex, or SQL queries, invoke the cortex-code skill with conversation context.

/cortex-code [user's question with relevant context]

## Detection Keywords

Invoke `/cortex-code` when user mentions:
- Snowflake, warehouse, database, schema, table, view
- SQL, query, SELECT, data quality, data analysis
- Cortex Search, Cortex Analyst, Cortex AI
- Snowpark, dynamic tables, streams, tasks
- "how many databases", "show me", "query", "check data"

## How to Invoke

1. **Detect Snowflake query**
2. **Include context**: If there were previous Snowflake-related exchanges in this conversation, include that context
3. **Invoke skill**: Call `/cortex-code` with enriched query
4. **Display results**: Show output from Cortex Code agent

## Examples

**Standalone query:**
User: "How many databases do I have in Snowflake?"
You: /cortex-code How many databases do I have in Snowflake?

**Query with context:**
User: "Which databases have stock data?" → [answered: DB_STOCK, FINANCE__ECONOMICS]
User: "Show me the schema for the main table"
You: /cortex-code User previously identified databases with stock data: DB_STOCK, FINANCE__ECONOMICS. Show me the schema for the main table in DB_STOCK.

## Important

- Do NOT answer Snowflake questions yourself
- ALWAYS invoke `/cortex-code` skill
- Include prior conversation context when relevant
- The skill handles: Cortex routing, SQL execution, formatting

## Non-Snowflake Queries

Handle normally without skill:
- General programming questions
- Local file operations
- Git operations
- Non-Snowflake databases (PostgreSQL, MySQL, etc.)
```

---

## Verify installation

```bash
# Skill installed
ls ~/.cursor/skills/cortex-code/SKILL.md

# Routing rule active
ls ~/.cursor/rules/cortex-snowflake-routing.mdc
```

## Troubleshooting

**Skill not found in Cursor:** Restart Cursor after install.

**Cortex hangs or no output:** Check your Cortex connection is active:
```bash
cortex connections list
cortex -p "SHOW DATABASES;" --output-format stream-json
```

**Rule not auto-triggering:** Confirm the `.mdc` file is in `~/.cursor/rules/` (global) not just in `~/.cursor/skills/cortex-code/`.
