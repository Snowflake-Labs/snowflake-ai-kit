-- ============================================================
-- Cortex AI Pipeline — Batch Insights
-- AI_AGG for cross-row analysis, AI_COMPLETE for custom prompts
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- AI_AGG: Summarize themes across multiple rows
-- (not subject to single-row context window limits)
-- ────────────────────────────────────────────────────────────

-- Top complaints from negative tickets
SELECT AI_AGG(
    TICKET_TEXT,
    'What are the top 3 recurring complaints? List them with approximate frequency.'
) AS complaint_summary
FROM ENRICHED_TICKETS
WHERE SENTIMENT_SCORE < -0.3;

-- Theme summary per category
SELECT
    AI_CATEGORY,
    COUNT(*) AS ticket_count,
    ROUND(AVG(SENTIMENT_SCORE), 2) AS avg_sentiment,
    AI_AGG(
        SUMMARY,
        'Summarize the key themes across these tickets in 2-3 bullet points.'
    ) AS theme_summary
FROM ENRICHED_TICKETS
GROUP BY AI_CATEGORY;

-- Weekly trend analysis
SELECT
    DATE_TRUNC('week', CREATED_AT) AS week,
    COUNT(*) AS volume,
    AI_AGG(
        SUMMARY,
        'Identify any emerging issues or trends this week compared to normal operations.'
    ) AS weekly_trends
FROM ENRICHED_TICKETS
GROUP BY week
ORDER BY week DESC;

-- ────────────────────────────────────────────────────────────
-- AI_COMPLETE: Custom prompts for specific analysis
-- ────────────────────────────────────────────────────────────

-- Suggest resolutions for technical bugs
SELECT
    TICKET_ID,
    AI_COMPLETE(
        'snowflake-arctic',
        'You are a technical support agent. Based on this bug report, suggest a resolution in 2 sentences: ' || TICKET_TEXT
    ) AS suggested_resolution
FROM ENRICHED_TICKETS
WHERE AI_CATEGORY = 'technical_bug'
LIMIT 10;

-- Priority re-assessment
SELECT
    TICKET_ID,
    PRIORITY AS original_priority,
    AI_COMPLETE(
        'snowflake-arctic',
        'Assess the urgency of this support ticket. Reply with exactly one word: critical, high, medium, or low. Ticket: ' || TICKET_TEXT
    ) AS ai_priority
FROM ENRICHED_TICKETS
LIMIT 20;

-- ────────────────────────────────────────────────────────────
-- AI_COMPLETE with structured options (advanced)
-- ────────────────────────────────────────────────────────────

-- Using system prompt + user prompt for better control
SELECT
    TICKET_ID,
    AI_COMPLETE(
        'mistral-large2',
        [
            {'role': 'system', 'content': 'You are a customer support analyst. Respond in JSON format with keys: root_cause, impact, recommended_action.'},
            {'role': 'user', 'content': TICKET_TEXT}
        ],
        {'temperature': 0.1, 'max_tokens': 200}
    ) AS analysis
FROM ENRICHED_TICKETS
WHERE AI_CATEGORY = 'technical_bug'
LIMIT 5;

-- ────────────────────────────────────────────────────────────
-- AI_FILTER: Natural language WHERE clause
-- ────────────────────────────────────────────────────────────

-- Find tickets mentioning data loss or security concerns
SELECT TICKET_ID, TICKET_TEXT, AI_CATEGORY
FROM ENRICHED_TICKETS
WHERE AI_FILTER(
    'This ticket describes a potential data loss or security concern: ' || TICKET_TEXT
)
LIMIT 20;

-- ────────────────────────────────────────────────────────────
-- Cost estimation helper
-- ────────────────────────────────────────────────────────────

-- Check token counts before running expensive operations
SELECT
    TICKET_ID,
    SNOWFLAKE.CORTEX.COUNT_TOKENS('snowflake-arctic', TICKET_TEXT) AS arctic_tokens,
    SNOWFLAKE.CORTEX.COUNT_TOKENS('mistral-large2', TICKET_TEXT) AS mistral_tokens
FROM SUPPORT_TICKETS
LIMIT 10;
