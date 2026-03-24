-- ============================================================
-- Cortex AI Pipeline — Enrich with AI Functions
-- Adds classification, sentiment, summaries, and extraction
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Test on a small sample first (5 rows)
-- ────────────────────────────────────────────────────────────

SELECT
    TICKET_ID,
    LEFT(TICKET_TEXT, 80) AS ticket_preview,
    AI_CLASSIFY(
        TICKET_TEXT,
        ['billing_issue', 'technical_bug', 'feature_request', 'account_access', 'general_inquiry']
    ):labels[0]::VARCHAR AS ai_category,
    ROUND(AI_SENTIMENT(TICKET_TEXT), 2) AS sentiment_score,
    AI_SUMMARIZE(TICKET_TEXT) AS summary
FROM SUPPORT_TICKETS
LIMIT 5;

-- ────────────────────────────────────────────────────────────
-- Full enrichment — Create ENRICHED_TICKETS table
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE ENRICHED_TICKETS AS
SELECT
    TICKET_ID,
    TICKET_TEXT,
    TICKET_CATEGORY AS ORIGINAL_CATEGORY,
    CUSTOMER_EMAIL,
    PRIORITY,
    CREATED_AT,

    -- AI Classification
    AI_CLASSIFY(
        TICKET_TEXT,
        ['billing_issue', 'technical_bug', 'feature_request', 'account_access', 'general_inquiry'],
        {'task_description': 'Classify this customer support ticket by issue type'}
    ):labels[0]::VARCHAR AS AI_CATEGORY,

    -- Sentiment Score (-1 to 1)
    ROUND(AI_SENTIMENT(TICKET_TEXT), 3) AS SENTIMENT_SCORE,

    -- Summary
    AI_SUMMARIZE(TICKET_TEXT) AS SUMMARY,

    -- Structured extraction
    AI_EXTRACT(
        TICKET_TEXT,
        OBJECT_CONSTRUCT(
            'customer_name', 'The customer name or identifier mentioned',
            'product_or_feature', 'The product, feature, or service mentioned',
            'urgency_level', 'How urgent: low, medium, high, or critical'
        )
    ) AS EXTRACTED_FIELDS

FROM SUPPORT_TICKETS;

-- ────────────────────────────────────────────────────────────
-- Verify enrichment results
-- ────────────────────────────────────────────────────────────

-- Check category distribution
SELECT
    AI_CATEGORY,
    COUNT(*) AS ticket_count,
    ROUND(AVG(SENTIMENT_SCORE), 2) AS avg_sentiment
FROM ENRICHED_TICKETS
GROUP BY AI_CATEGORY
ORDER BY ticket_count DESC;

-- Check sentiment distribution
SELECT
    CASE
        WHEN SENTIMENT_SCORE > 0.3 THEN 'Positive'
        WHEN SENTIMENT_SCORE < -0.3 THEN 'Negative'
        ELSE 'Neutral'
    END AS sentiment_bucket,
    COUNT(*) AS count
FROM ENRICHED_TICKETS
GROUP BY sentiment_bucket
ORDER BY count DESC;

-- Sample enriched rows
SELECT
    TICKET_ID,
    AI_CATEGORY,
    SENTIMENT_SCORE,
    SUMMARY,
    EXTRACTED_FIELDS
FROM ENRICHED_TICKETS
LIMIT 10;
