---
name: cortex-search-rag
description: "Build Retrieval-Augmented Generation (RAG) pipelines using Snowflake Cortex Search and Cortex AI Functions. Use for: semantic search, RAG chatbot, knowledge base Q&A, document search, hybrid search, vector search, enterprise search. Triggers: cortex search, RAG, retrieval augmented generation, search service, semantic search, knowledge base, document search, vector search, hybrid search, chatbot, Q&A over documents."
---

# Cortex Search RAG Pipeline

Build a RAG pipeline inside Snowflake. Cortex Search handles the retrieval (hybrid keyword + vector search) and AI_COMPLETE generates answers grounded in your data.

## When to Use

- User wants to search documents with semantic understanding
- User asks about RAG, retrieval-augmented generation, or knowledge base Q&A
- User wants to build a chatbot backed by their Snowflake data
- User mentions Cortex Search, vector search, or hybrid search
- User needs enterprise search over unstructured text data

## Tools Used

- `snowflake_sql_execute` — Create tables, search service, run queries
- `ask_user_question` — Confirm targets, approve architecture decisions
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
cortex-search-rag/
├── SKILL.md                    # This file (agent instructions)
├── README.md                   # Human-facing docs
└── templates/
    ├── setup.sql               # Create DB, KNOWLEDGE_BASE table, seed docs
    ├── search-service.sql      # CREATE CORTEX SEARCH SERVICE + test queries
    └── rag-query.sql           # Full RAG: search → context → AI_COMPLETE
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects and data source
- Step 3: User verifies search results before building RAG prompt
- Step 5: User reviews RAG answer quality

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex Search RAG — What This Skill Does
>
> I'll build a Retrieval-Augmented Generation pipeline using Snowflake Cortex Search.
> This gives you semantic search over your documents with LLM-powered answers — all inside Snowflake.
>
> **Architecture:**
> ```
> User Question → Cortex Search (retrieve relevant docs)
>     → Build context prompt → AI_COMPLETE (generate answer)
>     → Answer with citations
> ```
>
> **What gets created:**
> 1. A knowledge base table (or use your existing data)
> 2. A Cortex Search Service (hybrid keyword + vector index)
> 3. RAG query templates that combine search + LLM generation
>
> **Key features:**
> - Hybrid search: combines keyword matching with semantic vector similarity
> - Auto-refresh: search index stays current with your data (configurable lag)
> - Attribute filtering: narrow search by metadata (category, date, source)
> - No external vector DB needed
>
> **Cost note:** Cortex Search consumes credits for indexing and queries.
> The search service runs on a dedicated warehouse.
>
> Ready to proceed?

**⚠️ MANDATORY STOPPING POINT**: Wait for user approval before continuing.

---

## Step 1: Gather Targets

Ask the user:

```
Where should I set up the RAG pipeline?

- Database: (e.g., RAG_DB)
- Schema: (e.g., PUBLIC)
- Warehouse: (e.g., COMPUTE_WH) — XS is fine for small datasets
- Data source: Demo data or your own table?
- If your own table: which column contains the searchable text?
```

**⚠️ MANDATORY STOPPING POINT**: Wait for response.

If user has their own table, adapt the search service to use their text column. They must have change tracking enabled on the table (`ALTER TABLE ... SET CHANGE_TRACKING = TRUE`).

---

## Step 2: Create Knowledge Base (if demo)

Read `templates/setup.sql` and substitute:
- `{{DATABASE}}` → user's database
- `{{SCHEMA}}` → user's schema
- `{{WAREHOUSE}}` → user's warehouse
- `{{ROLE}}` → user's role

Execute the setup SQL. This creates a `KNOWLEDGE_BASE` table with 15 sample articles about a fictional company's policies, products, and FAQs.

Important: The table must have `CHANGE_TRACKING = TRUE` for Cortex Search to detect updates.

Verify:

```sql
SELECT COUNT(*) AS total_docs, COUNT(DISTINCT CATEGORY) AS categories
FROM {{DATABASE}}.{{SCHEMA}}.KNOWLEDGE_BASE;
```

---

## Step 3: Create Cortex Search Service

Read `templates/search-service.sql` and substitute placeholders.

The key command:

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE {{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE
    ON body
    ATTRIBUTES title, category, source_type
    WAREHOUSE = {{WAREHOUSE}}
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (
        SELECT id, title, category, source_type, body, updated_at
        FROM {{DATABASE}}.{{SCHEMA}}.KNOWLEDGE_BASE
    );
```

**Key parameters explained:**
- `ON body` — The column to search against (your main text content)
- `ATTRIBUTES` — Metadata columns you can filter on in queries
- `TARGET_LAG` — How often the index refreshes from the base table
- `EMBEDDING_MODEL` — The model that generates vector embeddings

After creation, test with a search query:

```sql
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
        '{
            "query": "What is the return policy?",
            "columns": ["id", "title", "body"],
            "limit": 3
        }'
    )
)['results'] AS search_results;
```

**⚠️ MANDATORY STOPPING POINT**: Show search results to user. Ask: "Search looks good? Ready to build the RAG pipeline?"

---

## Step 4: Build RAG Query

Read `templates/rag-query.sql` and substitute placeholders.

The RAG pattern:
1. Search for relevant documents
2. Build a prompt with system instructions + retrieved context + user question
3. Send to AI_COMPLETE for answer generation

```sql
WITH search_results AS (
    SELECT PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
            '{
                "query": "{{USER_QUESTION}}",
                "columns": ["id", "title", "body"],
                "limit": 5
            }'
        )
    )['results'] AS results
),
context AS (
    SELECT
        value:"id"::STRING AS id,
        value:"title"::STRING AS title,
        value:"body"::STRING AS body
    FROM search_results, LATERAL FLATTEN(input => results)
),
prompt AS (
    SELECT ARRAY_CAT(
        ARRAY_CONSTRUCT(
            OBJECT_CONSTRUCT('role', 'system', 'content',
                'Answer using ONLY the CONTEXT provided. Cite sources by their [id]. If the answer is not in the context, say you do not know.'),
            OBJECT_CONSTRUCT('role', 'user', 'content',
                '{{USER_QUESTION}}')
        ),
        ARRAY_AGG(
            OBJECT_CONSTRUCT('role', 'user', 'content',
                '[' || id || '] ' || title || E'\n' || LEFT(body, 800))
        )
    ) AS messages
    FROM context
)
SELECT SNOWFLAKE.CORTEX.COMPLETE(
    'snowflake-arctic',
    messages,
    OBJECT_CONSTRUCT('max_tokens', 500, 'guardrails', TRUE)
) AS answer
FROM prompt;
```

---

## Step 5: Verify and Iterate

Test with several questions to check quality:

```sql
-- Test questions for the demo knowledge base
-- 1. "What is the return policy for electronics?"
-- 2. "How does the loyalty program work?"
-- 3. "What shipping options are available?"
```

**⚠️ MANDATORY STOPPING POINT**: Show results. Ask if the user wants to:
1. Adjust the number of retrieved documents (limit)
2. Add attribute filtering (e.g., only search specific categories)
3. Try a different LLM model
4. Integrate into a Streamlit app

---

## Filtered Search

To narrow results by metadata:

```sql
-- Search only within a specific category
SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
        '{
            "query": "refund process",
            "columns": ["id", "title", "body"],
            "filter": {"@eq": {"category": "policies"}},
            "limit": 5
        }'
    )
)['results'] AS filtered_results;
```

## Embedding Model Choices

| Model | Dimensions | Best For |
|-------|-----------|----------|
| `snowflake-arctic-embed-l-v2.0` | 1024 | General purpose (recommended) |
| `snowflake-arctic-embed-m-v1.5` | 768 | Smaller index, faster queries |
| `e5-base-v2` | 768 | Alternative general purpose |

## Python API (Streamlit / Snowpark)

For apps that query Cortex Search programmatically:

```python
from snowflake.core import Root

root = Root(session)
svc = (root.databases["{{DATABASE}}"]
           .schemas["{{SCHEMA}}"]
           .cortex_search_services["KB_SEARCH_SERVICE"])

# Basic search
response = svc.search(
    query="return policy",
    columns=["id", "title", "body"],
    limit=5
)

# Filtered search
response = svc.search(
    query="return policy",
    columns=["id", "title", "body"],
    filter={"@eq": {"category": "policies"}},
    limit=5
)

results = response.json()
```

## Access Control

Cortex Search requires:

```sql
-- Role must have CORTEX_USER
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};

-- Role needs usage on the warehouse
GRANT USAGE ON WAREHOUSE {{WAREHOUSE}} TO ROLE {{ROLE}};
```

## Refresh and Monitoring

```sql
-- Check service status
SHOW CORTEX SEARCH SERVICES IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Manually refresh (usually not needed — auto-refresh handles it)
ALTER CORTEX SEARCH SERVICE {{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE RESUME;
```

## Output

- A Cortex Search Service with hybrid keyword + vector search over the user's data
- A tested RAG query template that retrieves relevant documents and generates grounded answers via AI_COMPLETE
- Working SQL patterns for filtered search, attribute-based narrowing, and Python API integration
