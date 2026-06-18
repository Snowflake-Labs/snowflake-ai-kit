# Routing Decision Examples

**Principle:** ONLY Snowflake operations → Cortex Code. Everything else → Claude Code.

---

## Route to Cortex Code

### 1. Explicit Snowflake Query
**User:** "Show me all tables in my Snowflake database"
**Confidence:** 95% — Explicit "Snowflake database" mention.

### 2. Cortex AI Feature
**User:** "Use Cortex Search to find documents about customer retention"
**Confidence:** 98% — "Cortex Search" is a specific Cortex AI feature.

### 3. Data Quality (Cortex Skill)
**User:** "Check data quality for my orders table"
**Confidence:** 85% — Matches Cortex's data-quality skill.

### 4. ML Function
**User:** "Create a forecasting model for sales trends"
**Confidence:** 70% — Could be Snowflake ML or general Python ML. If user says "using Snowflake Cortex ML", jumps to 95%.

### 5. Dynamic Tables
**User:** "Create a dynamic table that refreshes hourly with top customers"
**Confidence:** 90% — Snowflake-specific feature.

### 6. Data Governance
**User:** "Show me the governance policies for sensitive columns"
**Confidence:** 80% — "governance policies" + "columns" suggests Snowflake context.

---

## Ambiguous Cases

### 7. Generic "data quality"
**User:** "Check data quality"
**Confidence:** 50%

**Resolution:** Check recent conversation for Snowflake context → if none, ask user.

### 8. Generic SQL
**User:** "Run this SQL query: SELECT * FROM users"
**Confidence:** 50%

**Resolution:** Check if Snowflake connection is configured → check recent conversation → default to asking which database.

---

## Decision Tree

```
User Request
    │
    ├── Mentions "Snowflake" or "Cortex"?  → YES → Cortex (95%)
    ├── Mentions local files/git/web dev?  → YES → Claude Code (95%)
    ├── Mentions non-Snowflake database?   → YES → Claude Code (90%)
    ├── Mentions data quality/governance/ML?
    │       ├── Recent Snowflake context?  → YES → Cortex (80%)
    │       └── No context?                → Ask user
    ├── SQL without database context?      → Ask user
    └── Ambiguous?                         → Default Claude Code, ask for clarification
```

## Confidence Thresholds

| Range | Action |
|-------|--------|
| 95%+ | Route immediately |
| 80-94% | Route with logging |
| 70-79% | Consider asking user |
| 50-69% | Ask user for clarification |
| <50% | Default to Claude Code |
