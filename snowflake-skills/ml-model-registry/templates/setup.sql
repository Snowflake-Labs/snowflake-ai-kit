-- ============================================================
-- ML Model Registry — Setup
-- Creates registry schema and seeds training data
-- ============================================================

USE ROLE {{ROLE}};
USE WAREHOUSE {{WAREHOUSE}};

-- Create the model registry database and schema
CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.REGISTRY;
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.DATA;

USE SCHEMA {{DATABASE}}.DATA;

-- ────────────────────────────────────────────────────────────
-- CUSTOMER_CHURN: Synthetic churn prediction dataset
-- 1000 customers with features and a binary churn label
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE CUSTOMER_CHURN (
    CUSTOMER_ID         NUMBER,
    TENURE_MONTHS       NUMBER,
    MONTHLY_CHARGES     FLOAT,
    TOTAL_CHARGES       FLOAT,
    CONTRACT_TYPE       VARCHAR,
    PAYMENT_METHOD      VARCHAR,
    NUM_SUPPORT_TICKETS NUMBER,
    HAS_PREMIUM_SUPPORT BOOLEAN,
    NUM_PRODUCTS        NUMBER,
    CHURNED             NUMBER  -- 0 = retained, 1 = churned
);

INSERT INTO CUSTOMER_CHURN
SELECT
    SEQ4() + 1 AS CUSTOMER_ID,
    -- Tenure: 1-72 months
    GREATEST(1, MOD(ABS(HASH(SEQ4())), 72)) AS TENURE_MONTHS,
    -- Monthly charges: $20-$120
    ROUND(20 + (MOD(ABS(HASH(SEQ4() * 7)), 10000) / 100.0), 2) AS MONTHLY_CHARGES,
    -- Total charges = tenure * monthly (with some variation)
    ROUND(TENURE_MONTHS * MONTHLY_CHARGES * (0.9 + MOD(ABS(HASH(SEQ4() * 13)), 20) / 100.0), 2) AS TOTAL_CHARGES,
    -- Contract type
    CASE MOD(ABS(HASH(SEQ4() * 3)), 3)
        WHEN 0 THEN 'month-to-month'
        WHEN 1 THEN 'one-year'
        ELSE 'two-year'
    END AS CONTRACT_TYPE,
    -- Payment method
    CASE MOD(ABS(HASH(SEQ4() * 5)), 4)
        WHEN 0 THEN 'credit_card'
        WHEN 1 THEN 'bank_transfer'
        WHEN 2 THEN 'electronic_check'
        ELSE 'mailed_check'
    END AS PAYMENT_METHOD,
    -- Support tickets: 0-10
    MOD(ABS(HASH(SEQ4() * 11)), 11) AS NUM_SUPPORT_TICKETS,
    -- Premium support
    MOD(ABS(HASH(SEQ4() * 17)), 2) = 0 AS HAS_PREMIUM_SUPPORT,
    -- Number of products: 1-5
    GREATEST(1, MOD(ABS(HASH(SEQ4() * 19)), 5) + 1) AS NUM_PRODUCTS,
    -- Churn label: higher for month-to-month, high charges, many tickets
    CASE
        WHEN MOD(ABS(HASH(SEQ4() * 3)), 3) = 0  -- month-to-month
             AND MOD(ABS(HASH(SEQ4() * 11)), 11) > 5  -- many tickets
             AND MOD(ABS(HASH(SEQ4() * 23)), 100) < 70  -- 70% churn probability
        THEN 1
        WHEN MOD(ABS(HASH(SEQ4() * 3)), 3) = 0  -- month-to-month
             AND MOD(ABS(HASH(SEQ4() * 23)), 100) < 35  -- 35% churn otherwise
        THEN 1
        WHEN MOD(ABS(HASH(SEQ4() * 23)), 100) < 10  -- 10% base churn for contracts
        THEN 1
        ELSE 0
    END AS CHURNED
FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- Verify data
SELECT
    COUNT(*) AS total_customers,
    SUM(CHURNED) AS churned_count,
    ROUND(AVG(CHURNED::FLOAT), 3) AS churn_rate,
    ROUND(AVG(MONTHLY_CHARGES), 2) AS avg_monthly_charges,
    ROUND(AVG(TENURE_MONTHS), 1) AS avg_tenure
FROM CUSTOMER_CHURN;

-- Feature distribution
SELECT
    CONTRACT_TYPE,
    COUNT(*) AS count,
    ROUND(AVG(CHURNED::FLOAT), 3) AS churn_rate,
    ROUND(AVG(MONTHLY_CHARGES), 2) AS avg_charges
FROM CUSTOMER_CHURN
GROUP BY CONTRACT_TYPE
ORDER BY churn_rate DESC;
