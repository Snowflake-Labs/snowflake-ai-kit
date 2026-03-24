-- ============================================================
-- Cortex AI Pipeline — Demo Setup
-- Creates a SUPPORT_TICKETS table with synthetic data
-- ============================================================

USE ROLE {{ROLE}};
USE WAREHOUSE {{WAREHOUSE}};

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};
USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Grant Cortex AI Functions access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};

-- Create the support tickets table
CREATE OR REPLACE TABLE SUPPORT_TICKETS (
    TICKET_ID       NUMBER AUTOINCREMENT,
    TICKET_TEXT      VARCHAR,
    TICKET_CATEGORY  VARCHAR,
    CUSTOMER_EMAIL   VARCHAR,
    PRIORITY         VARCHAR,
    CREATED_AT       TIMESTAMP_NTZ,
    TICKET_LANGUAGE  VARCHAR DEFAULT 'en'
);

-- Seed 200 synthetic support tickets across 5 categories
INSERT INTO SUPPORT_TICKETS (TICKET_TEXT, TICKET_CATEGORY, CUSTOMER_EMAIL, PRIORITY, CREATED_AT)
SELECT
    CASE MOD(SEQ4(), 5)
        WHEN 0 THEN 'I was charged twice for my subscription this month. Order #' || (10000 + SEQ4()) ||
                     '. Please refund the duplicate charge of $' || (10 + MOD(SEQ4(), 90)) || '.99 to my card ending in 4242.'
        WHEN 1 THEN 'The application crashes every time I try to export reports to PDF. ' ||
                     'Error code: ERR-' || (1000 + MOD(SEQ4(), 500)) || '. Running version 3.' || MOD(SEQ4(), 10) ||
                     ' on Windows 11. This started after the latest update.'
        WHEN 2 THEN 'It would be great if you could add ' ||
                     CASE MOD(SEQ4(), 4)
                         WHEN 0 THEN 'dark mode support for the mobile app'
                         WHEN 1 THEN 'bulk export functionality for large datasets'
                         WHEN 2 THEN 'two-factor authentication via hardware keys'
                         ELSE 'integration with Slack for real-time notifications'
                     END || '. This would save our team significant time. Company: Acme Corp #' || MOD(SEQ4(), 100) || '.'
        WHEN 3 THEN 'I cannot log into my account since yesterday. I have tried resetting my password ' ||
                     MOD(SEQ4(), 5) + 1 || ' times but the reset email never arrives. ' ||
                     'My username is user_' || (5000 + SEQ4()) || '@example.com. This is urgent as I have a deadline.'
        ELSE 'I have a question about my ' ||
             CASE MOD(SEQ4(), 3)
                 WHEN 0 THEN 'Enterprise plan limits — specifically how many seats are included'
                 WHEN 1 THEN 'data retention policy and whether archived data counts toward storage'
                 ELSE 'API rate limits for the Pro tier and if there is a way to increase them'
             END || '. Account ID: ACC-' || (2000 + MOD(SEQ4(), 500)) || '.'
    END AS TICKET_TEXT,
    CASE MOD(SEQ4(), 5)
        WHEN 0 THEN 'billing'
        WHEN 1 THEN 'technical_bug'
        WHEN 2 THEN 'feature_request'
        WHEN 3 THEN 'account_access'
        ELSE 'general_inquiry'
    END AS TICKET_CATEGORY,
    'customer_' || (1000 + SEQ4()) || '@example.com' AS CUSTOMER_EMAIL,
    CASE MOD(SEQ4(), 4)
        WHEN 0 THEN 'critical'
        WHEN 1 THEN 'high'
        WHEN 2 THEN 'medium'
        ELSE 'low'
    END AS PRIORITY,
    DATEADD('minute', -SEQ4() * 15, CURRENT_TIMESTAMP()) AS CREATED_AT
FROM TABLE(GENERATOR(ROWCOUNT => 200));

-- Verify
SELECT
    COUNT(*) AS total_tickets,
    COUNT(DISTINCT TICKET_CATEGORY) AS categories,
    MIN(CREATED_AT) AS earliest,
    MAX(CREATED_AT) AS latest
FROM SUPPORT_TICKETS;
