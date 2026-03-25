---
name: cortex-ai-pipeline
description: "Build AI enrichment pipelines using Snowflake Cortex AI Functions (AI_CLASSIFY, AI_SENTIMENT, AI_SUMMARIZE, AI_EXTRACT, AI_COMPLETE, AI_TRANSLATE, AI_AGG). Use for: text classification, sentiment analysis, entity extraction, summarization, translation, content filtering, batch AI processing. Triggers: cortex ai, ai pipeline, classify text, sentiment analysis, summarize text, extract entities, translate, ai enrich, ai functions pipeline, batch ai, text analytics."
---

# Cortex AI Pipeline

Build an AI enrichment pipeline that runs entirely inside Snowflake using Cortex AI Functions. No external APIs, no data movement — just SQL.

## When to Use

- User wants to classify, summarize, or extract information from text data
- User needs sentiment analysis across a table
- User wants to translate content or filter rows with natural language conditions
- User asks about Cortex AI Functions or building an AI pipeline in SQL
- User wants to enrich existing tables with AI-generated columns

## Tools Used

- `snowflake_sql_execute` — Create tables, run AI functions, verify results
- `ask_user_question` — Confirm targets, get approval at checkpoints
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
cortex-ai-pipeline/
├── SKILL.md                    # This file (agent instructions)
├── README.md                   # Human-facing docs
└── templates/
    ├── setup.sql               # Create demo DB, seed SUPPORT_TICKETS table
    ├── enrich-pipeline.sql     # AI_CLASSIFY, AI_SENTIMENT, AI_SUMMARIZE, AI_EXTRACT
    └── batch-insights.sql      # AI_AGG cross-row analysis, AI_COMPLETE custom prompts
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects (database, schema, warehouse)
- Step 3: User verifies enrichment columns before batch insights
- Step 5: User reviews aggregated insights

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex AI Pipeline — What This Skill Does
>
> I'll build an AI enrichment pipeline using Snowflake Cortex AI Functions.
> These functions run inside Snowflake — your data never leaves the platform.
>
> **What gets created:**
> 1. A demo table with support ticket data (or we use your existing table)
> 2. AI-enriched columns: category, sentiment, summary, extracted fields
> 3. Cross-row aggregated insights using AI_AGG
>
> **AI Functions used:**
> - `AI_CLASSIFY` — Categorize text into labels you define
> - `AI_SENTIMENT` — Score text from -1 (negative) to +1 (positive)
> - `AI_SUMMARIZE` — Condense text into short summaries
> - `AI_EXTRACT` — Pull structured fields from unstructured text
> - `AI_TRANSLATE` — Convert text between languages
> - `AI_AGG` — Aggregate insights across multiple rows
> - `AI_COMPLETE` — Custom LLM prompts for anything else
>
> **Cost note:** AI Functions consume credits based on token usage.
> We'll start with a small sample before processing full tables.
>
> Ready to proceed?

**STOP** — Wait for user approval before continuing.

---

## Step 1: Gather Targets

Ask the user:

```
Where should I set up the AI pipeline?

- Database: (e.g., AI_DEMO)
- Schema: (e.g., PUBLIC)
- Warehouse: (e.g., COMPUTE_WH)
- Use demo data or your own table?
```

**STOP** — Wait for response.

If user has their own table, ask which text column(s) to enrich and skip the demo data setup in Step 2.

---

## Step 2: Create Demo Data (if needed)

Read `templates/setup.sql` and substitute:
- `{{DATABASE}}` → user's database
- `{{SCHEMA}}` → user's schema
- `{{WAREHOUSE}}` → user's warehouse

Execute the setup SQL. This creates a `SUPPORT_TICKETS` table with 200 synthetic tickets spanning categories like billing, technical issues, feature requests, and account problems.

Verify the data:

```sql
SELECT COUNT(*) AS total_tickets,
       COUNT(DISTINCT TICKET_CATEGORY) AS categories
FROM {{DATABASE}}.{{SCHEMA}}.SUPPORT_TICKETS;
```

---

## Step 3: Enrich with AI Functions

Read `templates/enrich-pipeline.sql` and substitute placeholders.

**Important — run on a sample first:**

```sql
-- Test on 5 rows before full table
SELECT
    TICKET_ID,
    TICKET_TEXT,
    AI_CLASSIFY(
        TICKET_TEXT,
        ['billing_issue', 'technical_bug', 'feature_request', 'account_access', 'general_inquiry']
    ):labels[0]::VARCHAR AS ai_category,
    ROUND(AI_SENTIMENT(TICKET_TEXT), 2) AS sentiment_score,
    AI_SUMMARIZE(TICKET_TEXT) AS summary
FROM {{DATABASE}}.{{SCHEMA}}.SUPPORT_TICKETS
LIMIT 5;
```

Show the sample results to the user.

**STOP** — Ask: "Sample looks good? Ready to enrich the full table?"

Then run the full enrichment pipeline from the template. This adds columns via CREATE TABLE AS SELECT (CTAS) to create an `ENRICHED_TICKETS` table with:
- `AI_CATEGORY` — classified ticket type
- `SENTIMENT_SCORE` — sentiment from -1 to 1
- `SUMMARY` — condensed ticket text
- `EXTRACTED_FIELDS` — structured extraction (customer name, product, urgency)

---

## Step 4: Translate (if multilingual data)

If the user's data contains non-English text, add translation:

```sql
SELECT
    TICKET_ID,
    TICKET_TEXT,
    AI_TRANSLATE(TICKET_TEXT, '', 'en') AS translated_text
FROM {{DATABASE}}.{{SCHEMA}}.SUPPORT_TICKETS
WHERE TICKET_LANGUAGE != 'en'
LIMIT 5;
```

Skip this step if data is English-only. The empty string `''` for source language lets Snowflake auto-detect.

---

## Step 5: Batch Insights with AI_AGG

Read `templates/batch-insights.sql` and substitute placeholders.

Run cross-row aggregation:

```sql
-- Summarize all negative tickets
SELECT AI_AGG(
    TICKET_TEXT,
    'What are the top 3 recurring complaints? List them with frequency.'
) AS complaint_summary
FROM {{DATABASE}}.{{SCHEMA}}.ENRICHED_TICKETS
WHERE SENTIMENT_SCORE < -0.3;
```

```sql
-- Aggregate by category
SELECT
    AI_CATEGORY,
    COUNT(*) AS ticket_count,
    ROUND(AVG(SENTIMENT_SCORE), 2) AS avg_sentiment,
    AI_AGG(SUMMARY, 'Summarize the key themes in these tickets.') AS theme_summary
FROM {{DATABASE}}.{{SCHEMA}}.ENRICHED_TICKETS
GROUP BY AI_CATEGORY;
```

**STOP** — Show results to user. Ask if they want custom AI_COMPLETE prompts.

---

## Step 6: Custom Prompts with AI_COMPLETE (Optional)

If the user wants custom analysis:

```sql
SELECT
    TICKET_ID,
    AI_COMPLETE(
        'snowflake-arctic',
        'Based on this support ticket, suggest a resolution in 2 sentences: ' || TICKET_TEXT
    ) AS suggested_resolution
FROM {{DATABASE}}.{{SCHEMA}}.ENRICHED_TICKETS
WHERE AI_CATEGORY = 'technical_bug'
LIMIT 10;
```

**Model choices:**
- `snowflake-arctic` — Snowflake's open model, good for most tasks
- `mistral-large2` — Strong reasoning, good for complex analysis
- `llama3.1-70b` — Meta's model, balanced performance
- `claude-3-5-sonnet` — Anthropic, excellent for nuanced text

---

## Decision Guide: Which AI Function?

| Task | Function | Example |
|------|----------|---------|
| Categorize into labels | `AI_CLASSIFY` | Route tickets, tag content |
| Positive/negative score | `AI_SENTIMENT` | Customer satisfaction tracking |
| Condense text | `AI_SUMMARIZE` | Summarize reviews, articles |
| Pull structured data | `AI_EXTRACT` | Extract names, dates, amounts |
| Yes/no filtering | `AI_FILTER` | "Is this a complaint?" in WHERE |
| Translate languages | `AI_TRANSLATE` | Multilingual support |
| Insights across rows | `AI_AGG` | Trend analysis, theme detection |
| Custom prompts | `AI_COMPLETE` | Anything else |
| Generate embeddings | `AI_EMBED` | Similarity search, clustering |

## Performance Tips

- **Start small**: Always test on LIMIT 5-10 before full table runs
- **Batch processing**: AI functions work best on batches, not row-by-row
- **Model selection**: Use smaller models (Arctic, Llama 8B) for simple tasks to save credits
- **Token awareness**: Use `SNOWFLAKE.CORTEX.COUNT_TOKENS(model, text)` to estimate costs
- **Avoid in DTs**: AI functions are not supported in Dynamic Tables — use CTAS or Tasks instead

## Namespace Note

The newer `AI_*` functions (AI_CLASSIFY, AI_SENTIMENT, etc.) are the recommended namespace. The legacy `SNOWFLAKE.CORTEX.*` functions (COMPLETE, SENTIMENT, SUMMARIZE, TRANSLATE, EXTRACT_ANSWER) still work but the `AI_*` versions have more features including image and multi-label support.

## Access Control

All Cortex AI Functions require the `SNOWFLAKE.CORTEX_USER` database role. Grant it with:

```sql
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};
```
