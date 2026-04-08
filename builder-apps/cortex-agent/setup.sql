-- =============================================================================
-- Cortex Agent App — Sample Setup
-- Run this in a Snowflake worksheet to create sample data and a Cortex Agent.
-- =============================================================================

-- 1. Database and schema
-- -------------------------------------------------------
CREATE DATABASE IF NOT EXISTS CORTEX_AGENT_DEMO;
USE DATABASE CORTEX_AGENT_DEMO;
CREATE SCHEMA IF NOT EXISTS DATA;
USE SCHEMA DATA;

-- 2. Sample data — sales transactions
-- -------------------------------------------------------
CREATE OR REPLACE TABLE SALES (
    ORDER_ID       STRING,
    ORDER_DATE     DATE,
    PRODUCT_NAME   STRING,
    CATEGORY       STRING,
    QUANTITY       INT,
    UNIT_PRICE     DECIMAL(10,2),
    TOTAL_AMOUNT   DECIMAL(10,2),
    REGION         STRING,
    SALES_REP      STRING
);

INSERT INTO SALES VALUES
    ('ORD-001', '2024-10-01', 'Snowflake Pro License', 'Software', 5, 2000.00, 10000.00, 'West', 'Alice'),
    ('ORD-002', '2024-10-03', 'Data Integration Pack', 'Services', 2, 5000.00, 10000.00, 'East', 'Bob'),
    ('ORD-003', '2024-10-07', 'Snowflake Pro License', 'Software', 3, 2000.00, 6000.00, 'East', 'Charlie'),
    ('ORD-004', '2024-10-12', 'Consulting Hours', 'Services', 40, 250.00, 10000.00, 'West', 'Alice'),
    ('ORD-005', '2024-10-15', 'Data Integration Pack', 'Services', 1, 5000.00, 5000.00, 'Central', 'Diana'),
    ('ORD-006', '2024-10-20', 'Training Package', 'Education', 10, 500.00, 5000.00, 'West', 'Bob'),
    ('ORD-007', '2024-11-01', 'Snowflake Pro License', 'Software', 8, 2000.00, 16000.00, 'East', 'Charlie'),
    ('ORD-008', '2024-11-05', 'Consulting Hours', 'Services', 20, 250.00, 5000.00, 'Central', 'Alice'),
    ('ORD-009', '2024-11-10', 'Data Integration Pack', 'Services', 3, 5000.00, 15000.00, 'West', 'Diana'),
    ('ORD-010', '2024-11-15', 'Training Package', 'Education', 5, 500.00, 2500.00, 'East', 'Bob'),
    ('ORD-011', '2024-11-20', 'Snowflake Pro License', 'Software', 2, 2000.00, 4000.00, 'Central', 'Charlie'),
    ('ORD-012', '2024-12-01', 'Consulting Hours', 'Services', 60, 250.00, 15000.00, 'West', 'Alice'),
    ('ORD-013', '2024-12-05', 'Data Integration Pack', 'Services', 4, 5000.00, 20000.00, 'East', 'Diana'),
    ('ORD-014', '2024-12-10', 'Snowflake Pro License', 'Software', 10, 2000.00, 20000.00, 'West', 'Bob'),
    ('ORD-015', '2024-12-15', 'Training Package', 'Education', 15, 500.00, 7500.00, 'Central', 'Charlie');

-- 3. Sample data — product documentation
-- -------------------------------------------------------
CREATE OR REPLACE TABLE PRODUCT_DOCS (
    DOC_ID         STRING,
    PRODUCT_NAME   STRING,
    TITLE          STRING,
    CONTENT        STRING,
    UPDATED_AT     TIMESTAMP_NTZ
);

INSERT INTO PRODUCT_DOCS VALUES
    ('DOC-001', 'Snowflake Pro License', 'Overview',
     'Snowflake Pro License provides full access to the Snowflake data platform including compute, storage, and all standard features. Pricing is per-credit with volume discounts available for annual commitments.',
     '2024-10-01'::TIMESTAMP_NTZ),
    ('DOC-002', 'Data Integration Pack', 'Overview',
     'The Data Integration Pack includes connectors for 50+ data sources, automated schema detection, and incremental loading. Supports both batch and streaming ingestion patterns.',
     '2024-10-01'::TIMESTAMP_NTZ),
    ('DOC-003', 'Consulting Hours', 'Overview',
     'Professional consulting hours for architecture review, performance optimization, and migration planning. Available in 20-hour blocks with rollover for unused hours.',
     '2024-10-01'::TIMESTAMP_NTZ),
    ('DOC-004', 'Training Package', 'Overview',
     'Instructor-led training covering Snowflake fundamentals, advanced SQL, data engineering, and Cortex AI. Each package includes hands-on labs and certification exam vouchers.',
     '2024-10-01'::TIMESTAMP_NTZ);

-- 4. Semantic view (for Cortex Analyst text-to-SQL)
-- -------------------------------------------------------
CREATE OR REPLACE SEMANTIC VIEW SALES_SEMANTIC_VIEW
  AS SEMANTIC MODEL
    NAME = 'Sales Analysis Model'
    TABLES = (
      CORTEX_AGENT_DEMO.DATA.SALES AS SALES
    )
    ENTITIES = (
      ENTITY ORDER_ID
        DESCRIPTION = 'Unique order identifier'
        COLUMNS = (SALES.ORDER_ID)
        PRIMARY_KEY = (SALES.ORDER_ID),
      ENTITY PRODUCT
        DESCRIPTION = 'Product name'
        COLUMNS = (SALES.PRODUCT_NAME),
      ENTITY REGION
        DESCRIPTION = 'Sales region (West, East, Central)'
        COLUMNS = (SALES.REGION),
      ENTITY SALES_REP
        DESCRIPTION = 'Name of the sales representative'
        COLUMNS = (SALES.SALES_REP)
    )
    METRICS = (
      METRIC TOTAL_REVENUE
        DESCRIPTION = 'Sum of total amount across all orders'
        EXPRESSION = 'SUM(SALES.TOTAL_AMOUNT)',
      METRIC ORDER_COUNT
        DESCRIPTION = 'Number of orders'
        EXPRESSION = 'COUNT(SALES.ORDER_ID)',
      METRIC AVG_ORDER_VALUE
        DESCRIPTION = 'Average order value'
        EXPRESSION = 'AVG(SALES.TOTAL_AMOUNT)',
      METRIC TOTAL_QUANTITY
        DESCRIPTION = 'Total units sold'
        EXPRESSION = 'SUM(SALES.QUANTITY)'
    )
    DIMENSIONS = (
      DIMENSION ORDER_DATE
        DESCRIPTION = 'Date the order was placed'
        EXPRESSION = 'SALES.ORDER_DATE',
      DIMENSION CATEGORY
        DESCRIPTION = 'Product category (Software, Services, Education)'
        EXPRESSION = 'SALES.CATEGORY'
    );

-- 5. Cortex Search service (for product docs RAG)
-- -------------------------------------------------------
CREATE OR REPLACE CORTEX SEARCH SERVICE PRODUCT_DOCS_SEARCH
  ON CONTENT
  ATTRIBUTES PRODUCT_NAME, TITLE
  WAREHOUSE = COMPUTE_WH
  TARGET_LAG = '1 hour'
  AS (
    SELECT
      CONTENT,
      PRODUCT_NAME,
      TITLE,
      DOC_ID
    FROM PRODUCT_DOCS
  );

-- 6. Cortex Agent
-- -------------------------------------------------------
CREATE OR REPLACE AGENT SALES_AGENT
  FROM SPECIFICATION $$
  models:
    - claude-4-sonnet
    - llama3.3-70b
  orchestration: cortex
  instructions: |
    You are a sales analytics assistant. You help users analyze sales data,
    look up product information, and generate charts.

    When users ask about sales metrics, revenue, or orders, use the Cortex Analyst
    tool to generate and run SQL queries against the sales data.

    When users ask about product details or documentation, use the Cortex Search
    tool to find relevant information.

    Always be concise and provide specific numbers when available.
  tools:
    - cortex_analyst_text_to_sql:
        semantic_view: CORTEX_AGENT_DEMO.DATA.SALES_SEMANTIC_VIEW
    - cortex_search:
        search_service: CORTEX_AGENT_DEMO.DATA.PRODUCT_DOCS_SEARCH
        max_results: 3
    - data_to_chart
  $$;

-- 7. Grant access (adjust role as needed)
-- -------------------------------------------------------
-- GRANT USAGE ON DATABASE CORTEX_AGENT_DEMO TO ROLE <your_role>;
-- GRANT USAGE ON SCHEMA CORTEX_AGENT_DEMO.DATA TO ROLE <your_role>;
-- GRANT SELECT ON ALL TABLES IN SCHEMA CORTEX_AGENT_DEMO.DATA TO ROLE <your_role>;
-- GRANT USAGE ON AGENT CORTEX_AGENT_DEMO.DATA.SALES_AGENT TO ROLE <your_role>;

SELECT 'Setup complete! Agent SALES_AGENT is ready.' AS STATUS;
