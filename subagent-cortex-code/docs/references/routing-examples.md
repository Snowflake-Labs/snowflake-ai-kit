# Routing Decision Examples

This document provides examples of routing decisions to help understand when requests should go to Cortex Code vs. Claude Code.

## Principle

**Route to Cortex**: ONLY Snowflake-related operations
**Route to Claude Code**: Everything else

---

## Route to Cortex Code

### Example 1: Explicit Snowflake Query
**User**: "Show me all tables in my Snowflake database"

**Decision**: → Cortex
**Confidence**: 95%
**Reasoning**: Explicit "Snowflake database" mention. This is clearly a Snowflake operation.

**Predicted Tools**: `snowflake_sql_execute`, `bash`, `read`

---

### Example 2: Cortex AI Feature
**User**: "Use Cortex Search to find documents about customer retention"

**Decision**: → Cortex
**Confidence**: 98%
**Reasoning**: "Cortex Search" is a specific Cortex AI feature. Direct Cortex invocation.

**Predicted Tools**: `snowflake_sql_execute`, `bash`

---

### Example 3: Data Quality (Cortex Skill)
**User**: "Check data quality for the SALES_DATA table"

**Decision**: → Cortex
**Confidence**: 85%
**Reasoning**: "data quality" matches Cortex's data-quality skill. Likely Snowflake table context.

**Predicted Tools**: `snowflake_sql_execute`, `bash`, `read`, `write`, `glob`

---

### Example 4: ML Function
**User**: "Create a forecasting model for sales trends"

**Decision**: → Cortex
**Confidence**: 70%
**Reasoning**: "forecasting model" suggests Cortex ML functions (FORECAST, etc.). Could be Snowflake ML.

**Predicted Tools**: `snowflake_sql_execute`, `bash`

**Note**: This has lower confidence because it could also be general ML (Python scikit-learn, etc.). If user clarifies "using Snowflake Cortex ML", confidence increases to 95%.

---

### Example 5: Dynamic Tables
**User**: "Create a dynamic table that refreshes hourly with top customers"

**Decision**: → Cortex
**Confidence**: 90%
**Reasoning**: "dynamic table" is a Snowflake-specific feature. Cortex has expertise.

**Predicted Tools**: `snowflake_sql_execute`, `bash`, `read`

---

### Example 6: Data Governance
**User**: "Show me the governance policies for sensitive columns"

**Decision**: → Cortex
**Confidence**: 80%
**Reasoning**: "governance policies" + "columns" suggests Snowflake data governance. Cortex has data-governance skill.

**Predicted Tools**: `snowflake_sql_execute`, `bash`, `read`

---

## Route to Claude Code

### Example 7: Local File Operation
**User**: "Read the config.json file"

**Decision**: → Claude Code
**Confidence**: 95%
**Reasoning**: Local file operation. No Snowflake context. Claude Code handles directly.

**Claude Tool**: `Read`

---

### Example 8: Git Operation
**User**: "Commit these changes with message 'Fix bug'"

**Decision**: → Claude Code
**Confidence**: 98%
**Reasoning**: Git operation. Not Snowflake-related. Claude Code's core functionality.

**Claude Tool**: `Bash` (git commit)

---

### Example 9: Python Script (Non-Snowpark)
**User**: "Write a Python script to parse this CSV file"

**Decision**: → Claude Code
**Confidence**: 90%
**Reasoning**: General Python scripting. No Snowflake/Snowpark context. Claude Code handles.

**Claude Tool**: `Write`

**Note**: If user says "Write a Snowpark script", then → Cortex (95% confidence).

---

### Example 10: PostgreSQL Query
**User**: "Query my PostgreSQL database for user records"

**Decision**: → Claude Code
**Confidence**: 95%
**Reasoning**: PostgreSQL, not Snowflake. Claude Code can handle with appropriate tools/MCP.

**Claude Tool**: MCP server or direct psql

---

### Example 11: Web Development
**User**: "Create a React component for displaying customer data"

**Decision**: → Claude Code
**Confidence**: 95%
**Reasoning**: Frontend development. Not Snowflake-specific. Claude Code excels at this.

**Claude Tool**: `Write`

---

### Example 12: Infrastructure
**User**: "Set up a Docker container for this application"

**Decision**: → Claude Code
**Confidence**: 95%
**Reasoning**: Infrastructure/DevOps. Not Snowflake-related. Claude Code handles.

**Claude Tool**: `Write`, `Bash`

---

## Ambiguous Cases (Require Context)

### Example 13: Generic "data quality"
**User**: "Check data quality"

**Decision**: → ?
**Confidence**: 50%
**Reasoning**: Ambiguous. Need more context.

**Resolution Strategy**:
1. Check recent conversation for Snowflake context
2. If no context, ask user: "Are you referring to a Snowflake table?"
3. If yes → Cortex, if no → Claude Code

---

### Example 14: "Create a table"
**User**: "Create a table with columns: id, name, email"

**Decision**: → ?
**Confidence**: 50%
**Reasoning**: Could be Snowflake, PostgreSQL, MySQL, or even a markdown table.

**Resolution Strategy**:
1. Check recent conversation for database context
2. If Snowflake was mentioned recently → Cortex (70%)
3. Otherwise, ask user: "Which database? (Snowflake, PostgreSQL, etc.)"

---

### Example 15: "Run SQL query"
**User**: "Run this SQL query: SELECT * FROM users"

**Decision**: → ?
**Confidence**: 50%
**Reasoning**: Generic SQL. Need database context.

**Resolution Strategy**:
1. Check if user has Snowflake connection configured in Cortex
2. Check recent conversation for database mentions
3. Default to asking: "Which database should I run this on?"
4. If Snowflake → Cortex, else → Claude Code

---

## Multi-Step Workflows

### Example 16: Snowflake + Local Analysis
**User**: "Query Snowflake for sales data, then create a local CSV report"

**Decision**: → Cortex first, then Claude Code
**Reasoning**:
1. "Query Snowflake" → Cortex handles the query
2. "create a local CSV report" → Claude Code writes the local file

**Workflow**:
1. Route query part to Cortex
2. Get results from Cortex
3. Use Claude Code to format and write CSV locally

---

### Example 17: Local + Snowflake
**User**: "Read this local CSV file and load it into Snowflake"

**Decision**: → Claude Code first, then Cortex
**Reasoning**:
1. "Read this local CSV" → Claude Code reads local file
2. "load it into Snowflake" → Cortex handles Snowflake load

**Workflow**:
1. Claude Code reads CSV using `Read` tool
2. Pass CSV content to Cortex with prompt: "Load this data into Snowflake table X"
3. Cortex handles Snowflake operations

---

## Edge Cases

### Example 18: Snowpark Python
**User**: "Write a Snowpark Python script to process data"

**Decision**: → Cortex
**Confidence**: 90%
**Reasoning**: Snowpark is Snowflake's Python framework. Cortex has Snowpark expertise.

---

### Example 19: dbt with Snowflake
**User**: "Create a dbt model for Snowflake"

**Decision**: → Cortex (preferred) or Claude Code
**Confidence**: 70%
**Reasoning**: dbt is infrastructure as code for data transformation. Cortex understands Snowflake-specific dbt patterns better.

**Alternative**: Claude Code can handle generic dbt, but Cortex provides Snowflake-optimized guidance.

---

### Example 20: "Cortex" as Generic AI
**User**: "Use Cortex to analyze this text"

**Decision**: → ?
**Confidence**: 40%
**Reasoning**: User might mean "Cortex Code" or generic "AI cortex". Clarify intent.

**Resolution**: Ask "Did you mean Cortex Code (Snowflake's AI assistant) or general text analysis?"

---

## Summary Decision Tree

```
User Request
    |
    |─── Mentions "Snowflake" or "Cortex"? → YES → Cortex (95%)
    |
    |─── Mentions local files/git/web dev? → YES → Claude Code (95%)
    |
    |─── Mentions non-Snowflake database? → YES → Claude Code (90%)
    |
    |─── Mentions data quality/governance/ML? → Check context
          |
          |─── Recent Snowflake context? → YES → Cortex (80%)
          |─── No context? → Ask user
    |
    |─── SQL query without database context? → Ask user
    |
    |─── Ambiguous? → Default to Claude Code, ask for clarification
```

---

## Confidence Thresholds

- **95%+**: High confidence, route immediately
- **80-94%**: Good confidence, route with logging
- **70-79%**: Moderate confidence, consider asking user
- **50-69%**: Low confidence, ask user for clarification
- **<50%**: Very uncertain, default to Claude Code + ask

---

## Logging for Improvement

Log all routing decisions with:
- User prompt
- Routing decision (cortex/claude)
- Confidence score
- Actual outcome (did it work? did user correct?)

Use logs to improve routing algorithm over time.
