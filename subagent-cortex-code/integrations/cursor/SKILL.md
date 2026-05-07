---
name: cortex-code
description: Routes Snowflake-related operations to Cortex Code agent for specialized Snowflake expertise. Use when querying databases, checking data quality, or asking about Snowflake features.
license: Proprietary. See LICENSE for complete terms
---

# Cortex Code Integration

Routes Snowflake queries to Cortex Code agent with conversation context enrichment.

## When to Use

Use this skill when the user asks about:
- Snowflake databases, warehouses, schemas, tables, views
- SQL queries for Snowflake data ("How many databases?", "Show top customers")
- Data quality checks, validation, profiling
- Cortex AI features (Cortex Search, Cortex Analyst, ML functions)
- Semantic views, data modeling
- Snowpark, dynamic tables, streams, tasks
- Snowflake security, roles, policies, governance

## Instructions

### Step 1: Build Enriched Context

Before executing, build an enriched prompt that includes:

1. **Conversation Context** (if relevant):
   - Previous 2-3 exchanges from this conversation
   - Any Snowflake-specific details already discussed
   - User's stated goals or requirements

2. **User's Question**:
   - The current query being asked

### Step 2: Execute with Context

Pass the enriched context to Cortex Code:

```bash
python3 scripts/execute_cortex.py \
  --prompt "# Conversation Context
[relevant prior exchanges if any]

# Current Question
[USER'S QUESTION]" \
  --envelope "RO"
```

### Example with Context

If user previously asked "Which databases have stock data?" and now asks "Show me the schema for the main table":

```bash
python3 scripts/execute_cortex.py \
  --prompt "# Recent Context
User previously identified databases with stock data: DB_STOCK, FINANCE__ECONOMICS

# Current Question
Show me the schema for the main table in DB_STOCK" \
  --envelope "RO"
```

### Example without Context

For standalone questions:

```bash
python3 scripts/execute_cortex.py \
  --prompt "How many databases do I have in Snowflake?" \
  --envelope "RO"
```

## How It Works

1. Agent builds enriched prompt with conversation context
2. Routes to Cortex Code agent (headless execution)
3. Cortex executes `cortex` CLI with stream-json format
4. Runs SQL queries via `snowflake_sql_execute` tool
5. Returns formatted results with analysis

## Configuration

- **Approval mode**: prompt by default; request user approval before execution
- **Security envelope**: RO for reads; RW only for approved writes
- **Connection**: Uses default Snowflake connection from cortex CLI
