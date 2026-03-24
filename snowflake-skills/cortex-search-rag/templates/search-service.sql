-- ============================================================
-- Cortex Search RAG — Search Service
-- Creates the Cortex Search Service and tests it
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Create the Cortex Search Service
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE CORTEX SEARCH SERVICE KB_SEARCH_SERVICE
    ON body
    ATTRIBUTES title, category, source_type
    WAREHOUSE = {{WAREHOUSE}}
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (
        SELECT
            id,
            title,
            category,
            source_type,
            body,
            updated_at
        FROM KNOWLEDGE_BASE
    );

-- Note: The CREATE may take a moment as it builds the initial index.
-- For large datasets (millions of rows), this can take longer.

-- ────────────────────────────────────────────────────────────
-- Test: Basic semantic search
-- ────────────────────────────────────────────────────────────

SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
        '{
            "query": "What is the return policy for electronics?",
            "columns": ["id", "title", "body"],
            "limit": 3
        }'
    )
)['results'] AS search_results;

-- ────────────────────────────────────────────────────────────
-- Test: Filtered search (by category)
-- ────────────────────────────────────────────────────────────

SELECT PARSE_JSON(
    SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
        '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
        '{
            "query": "payment options",
            "columns": ["id", "title", "body"],
            "filter": {"@eq": {"category": "billing"}},
            "limit": 3
        }'
    )
)['results'] AS filtered_results;

-- ────────────────────────────────────────────────────────────
-- Test: Flatten results into rows
-- ────────────────────────────────────────────────────────────

WITH raw AS (
    SELECT PARSE_JSON(
        SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
            '{{DATABASE}}.{{SCHEMA}}.KB_SEARCH_SERVICE',
            '{
                "query": "How does the loyalty program work?",
                "columns": ["id", "title", "body"],
                "limit": 5
            }'
        )
    )['results'] AS results
)
SELECT
    value:"id"::NUMBER AS id,
    value:"title"::VARCHAR AS title,
    LEFT(value:"body"::VARCHAR, 200) AS body_preview
FROM raw, LATERAL FLATTEN(input => results);

-- ────────────────────────────────────────────────────────────
-- Check service status
-- ────────────────────────────────────────────────────────────

SHOW CORTEX SEARCH SERVICES IN SCHEMA {{DATABASE}}.{{SCHEMA}};
