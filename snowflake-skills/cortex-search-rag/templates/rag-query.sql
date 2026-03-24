-- ============================================================
-- Cortex Search RAG — Full RAG Query
-- Search → Build Context → AI_COMPLETE with citations
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Full RAG query: search → context → answer
-- Replace {{USER_QUESTION}} with the actual question
-- ────────────────────────────────────────────────────────────

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
            OBJECT_CONSTRUCT(
                'role', 'system',
                'content', 'You are a helpful assistant. Answer the question using ONLY the context provided below. Cite sources by their [id]. If the answer is not in the provided context, say "I don''t have enough information to answer that."'
            ),
            OBJECT_CONSTRUCT(
                'role', 'user',
                'content', '{{USER_QUESTION}}'
            )
        ),
        ARRAY_AGG(
            OBJECT_CONSTRUCT(
                'role', 'user',
                'content', '[' || id || '] ' || title || E'\n' || LEFT(body, 800)
            )
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

-- ────────────────────────────────────────────────────────────
-- RAG with category filter
-- Only search within specific document categories
-- ────────────────────────────────────────────────────────────

WITH search_results AS (
    SELECT PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
            '{
                "query": "{{USER_QUESTION}}",
                "columns": ["id", "title", "body"],
                "filter": {"@eq": {"category": "{{FILTER_CATEGORY}}"}},
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
                'Answer using ONLY the CONTEXT. Cite sources by [id]. If unsure, say so.'),
            OBJECT_CONSTRUCT('role', 'user', 'content', '{{USER_QUESTION}}')
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

-- ────────────────────────────────────────────────────────────
-- Test questions for the demo knowledge base
-- ────────────────────────────────────────────────────────────

-- Question 1: "What is the return policy for electronics?"
-- Expected: References Return Policy Overview article, mentions 15-day window

-- Question 2: "How does the loyalty program work?"
-- Expected: References Loyalty Program Guide, describes tiers

-- Question 3: "What are the API rate limits for the Pro tier?"
-- Expected: References API Rate Limits doc, mentions 1000 req/min

-- Question 4: "Can I return a laptop I opened?"
-- Expected: References return policy, mentions 10% restocking fee

-- Question 5: "What holiday shipping deadlines do you have?"
-- Expected: References Holiday Season Policies article
