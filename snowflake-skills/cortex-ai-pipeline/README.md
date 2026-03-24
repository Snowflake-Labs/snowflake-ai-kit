# Cortex AI Pipeline

Build AI enrichment pipelines using Snowflake Cortex AI Functions — classify, summarize, extract, translate, and analyze text data entirely within Snowflake.

## What It Does

This skill guides your AI coding agent through building a complete text analytics pipeline using Cortex AI Functions:

1. **Setup** — Create a demo table with support ticket data (or use your own)
2. **Classify** — Categorize text into custom labels with `AI_CLASSIFY`
3. **Sentiment** — Score text from negative to positive with `AI_SENTIMENT`
4. **Summarize** — Condense text with `AI_SUMMARIZE`
5. **Extract** — Pull structured fields from unstructured text with `AI_EXTRACT`
6. **Aggregate** — Get cross-row insights with `AI_AGG`
7. **Custom** — Run any prompt with `AI_COMPLETE`

## Prerequisites

- Snowflake account with Cortex AI Functions enabled
- `SNOWFLAKE.CORTEX_USER` database role granted to your role
- A warehouse (XS is fine for demo data)

## Quick Start

Ask your AI coding agent:

> "Set up a Cortex AI pipeline to classify and analyze my support tickets"

Or for a demo:

> "Build a demo AI enrichment pipeline using Cortex AI Functions"

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Create demo database and seed support tickets |
| `templates/enrich-pipeline.sql` | AI_CLASSIFY + AI_SENTIMENT + AI_SUMMARIZE + AI_EXTRACT |
| `templates/batch-insights.sql` | AI_AGG cross-row analysis + AI_COMPLETE custom prompts |
