-- =============================================================================
-- Data Product Sharing — Provider Setup
-- =============================================================================
-- Creates sample source data for sharing. In practice, replace with your
-- actual tables and views.
--
-- Replace these placeholders:
--   {{DATABASE}} — Source database
--   {{SCHEMA}}   — Source schema
-- =============================================================================

USE ROLE SYSADMIN;

-- 1. Source database and schema
CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- 2. Sample source table (replace with your actual data)
CREATE OR REPLACE TABLE PRODUCTS (
    product_id INT,
    product_name VARCHAR(200),
    category VARCHAR(100),
    price DECIMAL(10,2),
    in_stock BOOLEAN,
    last_updated TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

INSERT INTO PRODUCTS (product_id, product_name, category, price, in_stock)
SELECT
    SEQ4() AS product_id,
    'Product ' || SEQ4() AS product_name,
    CASE MOD(SEQ4(), 5)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Home & Garden'
        WHEN 3 THEN 'Sports'
        ELSE 'Books'
    END AS category,
    ROUND(UNIFORM(5.00, 500.00, RANDOM())::DECIMAL(10,2), 2) AS price,
    UNIFORM(0, 1, RANDOM())::BOOLEAN AS in_stock
FROM TABLE(GENERATOR(ROWCOUNT => 500));

-- 3. Secure view — best practice for sharing (controls which columns/rows)
CREATE OR REPLACE SECURE VIEW PRODUCTS_PUBLIC AS
SELECT
    product_id,
    product_name,
    category,
    price,
    in_stock
FROM PRODUCTS
WHERE in_stock = TRUE;  -- Only share in-stock products

-- 4. Aggregated view — share insights without raw data
CREATE OR REPLACE SECURE VIEW PRODUCT_SUMMARY AS
SELECT
    category,
    COUNT(*) AS total_products,
    COUNT_IF(in_stock) AS in_stock_count,
    ROUND(AVG(price), 2) AS avg_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price
FROM PRODUCTS
GROUP BY category;

-- Verify
SELECT * FROM PRODUCTS_PUBLIC LIMIT 10;
SELECT * FROM PRODUCT_SUMMARY;
