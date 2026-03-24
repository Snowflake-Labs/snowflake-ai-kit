-- ============================================================
-- Cortex Agents — Setup
-- Creates sample data, semantic view, and search service
-- ============================================================

USE ROLE {{ROLE}};
USE WAREHOUSE {{WAREHOUSE}};

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};
USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Grant Cortex access
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};

-- ────────────────────────────────────────────────────────────
-- Structured data: Sales transactions
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE SALES (
    ORDER_ID        NUMBER,
    ORDER_DATE      DATE,
    PRODUCT_NAME    VARCHAR,
    CATEGORY        VARCHAR,
    REGION          VARCHAR,
    QUANTITY        NUMBER,
    UNIT_PRICE      FLOAT,
    TOTAL_AMOUNT    FLOAT,
    CUSTOMER_SEGMENT VARCHAR
);

INSERT INTO SALES
SELECT
    SEQ4() + 1 AS ORDER_ID,
    DATEADD('day', -MOD(SEQ4(), 365), CURRENT_DATE()) AS ORDER_DATE,
    CASE MOD(SEQ4(), 6)
        WHEN 0 THEN 'Laptop Pro'
        WHEN 1 THEN 'Wireless Mouse'
        WHEN 2 THEN 'USB-C Hub'
        WHEN 3 THEN 'Monitor 27in'
        WHEN 4 THEN 'Keyboard Mech'
        ELSE 'Webcam HD'
    END AS PRODUCT_NAME,
    CASE MOD(SEQ4(), 3)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Accessories'
        ELSE 'Peripherals'
    END AS CATEGORY,
    CASE MOD(SEQ4(), 4)
        WHEN 0 THEN 'North America'
        WHEN 1 THEN 'Europe'
        WHEN 2 THEN 'Asia Pacific'
        ELSE 'Latin America'
    END AS REGION,
    GREATEST(1, MOD(ABS(HASH(SEQ4())), 20)) AS QUANTITY,
    CASE MOD(SEQ4(), 6)
        WHEN 0 THEN 1299.99
        WHEN 1 THEN 29.99
        WHEN 2 THEN 49.99
        WHEN 3 THEN 349.99
        WHEN 4 THEN 149.99
        ELSE 79.99
    END AS UNIT_PRICE,
    QUANTITY * UNIT_PRICE AS TOTAL_AMOUNT,
    CASE MOD(SEQ4(), 3)
        WHEN 0 THEN 'Enterprise'
        WHEN 1 THEN 'SMB'
        ELSE 'Consumer'
    END AS CUSTOMER_SEGMENT
FROM TABLE(GENERATOR(ROWCOUNT => 500));

-- ────────────────────────────────────────────────────────────
-- Semantic view for Cortex Analyst
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE SEMANTIC VIEW SALES_SEMANTIC_VIEW
  COMMENT = 'Sales data semantic view for Cortex Agent'
  AS SEMANTIC MODEL
  $$
  name: "Sales Analysis"
  description: "Semantic model for analyzing sales transactions by product, region, and customer segment."
  tables:
    - name: SALES
      base_table:
        database: "{{DATABASE}}"
        schema: "{{SCHEMA}}"
        table: SALES
      dimensions:
        - name: product_name
          expr: PRODUCT_NAME
          description: "Name of the product sold"
          data_type: VARCHAR
        - name: category
          expr: CATEGORY
          description: "Product category: Electronics, Accessories, or Peripherals"
          data_type: VARCHAR
        - name: region
          expr: REGION
          description: "Sales region: North America, Europe, Asia Pacific, or Latin America"
          data_type: VARCHAR
        - name: customer_segment
          expr: CUSTOMER_SEGMENT
          description: "Customer type: Enterprise, SMB, or Consumer"
          data_type: VARCHAR
        - name: order_date
          expr: ORDER_DATE
          description: "Date of the order"
          data_type: DATE
      measures:
        - name: total_revenue
          expr: SUM(TOTAL_AMOUNT)
          description: "Total revenue in dollars"
          data_type: FLOAT
        - name: total_quantity
          expr: SUM(QUANTITY)
          description: "Total units sold"
          data_type: NUMBER
        - name: order_count
          expr: COUNT(DISTINCT ORDER_ID)
          description: "Number of orders"
          data_type: NUMBER
        - name: avg_order_value
          expr: AVG(TOTAL_AMOUNT)
          description: "Average order value in dollars"
          data_type: FLOAT
  $$;

-- ────────────────────────────────────────────────────────────
-- Unstructured data: Product documentation
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE TABLE PRODUCT_DOCS (
    ID          NUMBER AUTOINCREMENT,
    TITLE       VARCHAR,
    CATEGORY    VARCHAR,
    BODY        VARCHAR,
    UPDATED_AT  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CHANGE_TRACKING = TRUE;

INSERT INTO PRODUCT_DOCS (TITLE, CATEGORY, BODY) VALUES
    ('Laptop Pro Specifications', 'product',
     'The Laptop Pro features a 15.6-inch Retina display, M3 Pro chip, 16GB unified memory, and 512GB SSD. Battery life up to 18 hours. Includes Thunderbolt 4 ports, Wi-Fi 6E, and a 1080p FaceTime camera. Weight: 3.5 lbs. Available in Silver and Space Black.'),
    ('Return Policy', 'policy',
     'Items may be returned within 30 days of purchase for a full refund. Electronics have a 15-day return window. Opened laptops are subject to a 10% restocking fee. Items must be in original packaging. Gift cards are non-refundable.'),
    ('Warranty Information', 'policy',
     'All electronics carry a 1-year manufacturer warranty covering defects in materials and workmanship. Extended warranties available: 2-year ($49.99) and 3-year ($79.99). Accidental damage voids the warranty. File claims with order number within 48 hours.'),
    ('Shipping Options', 'policy',
     'Standard shipping: 5-7 business days (free over $50). Express: 2-3 business days ($12.99). Next-day: order by 2 PM ($24.99). International shipping available to 40+ countries. Tracking numbers emailed within 4 hours.'),
    ('Wireless Mouse Setup Guide', 'support',
     'To set up your Wireless Mouse: 1) Insert the USB receiver into any USB-A port. 2) Turn on the mouse using the switch on the bottom. 3) The LED should blink blue then turn solid. 4) If not connecting, press the pairing button for 3 seconds. Compatible with Windows 10+, macOS 12+, and Linux.'),
    ('Monitor Troubleshooting', 'support',
     'If your Monitor 27in displays no signal: 1) Check cable connections (HDMI/DisplayPort). 2) Try a different port on your computer. 3) Reset monitor to factory settings via OSD menu > Settings > Reset. 4) Update graphics drivers. If flickering occurs, change refresh rate to 60Hz in display settings.'),
    ('Enterprise Volume Pricing', 'sales',
     'Orders of 50+ units qualify for volume discounts: 50-99 units (10% off), 100-499 units (15% off), 500+ units (25% off). Contact enterprise@example.com for custom quotes. NET-30 terms available for approved accounts. Dedicated account manager assigned for orders over $100K.'),
    ('Keyboard Mechanical Features', 'product',
     'The Keyboard Mech uses Cherry MX Brown switches rated for 100M keystrokes. Features per-key RGB backlighting, USB-C connection, N-key rollover, and a detachable wrist rest. Includes keycap puller and extra switches. Compatible with Windows and macOS.');

-- ────────────────────────────────────────────────────────────
-- Cortex Search Service for unstructured data
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE CORTEX SEARCH SERVICE DOC_SEARCH_SERVICE
    ON body
    ATTRIBUTES title, category
    WAREHOUSE = {{WAREHOUSE}}
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (
        SELECT id, title, category, body, updated_at
        FROM PRODUCT_DOCS
    );

-- ────────────────────────────────────────────────────────────
-- Verify setup
-- ────────────────────────────────────────────────────────────

SELECT 'SALES' AS object, COUNT(*) AS row_count FROM SALES
UNION ALL
SELECT 'PRODUCT_DOCS', COUNT(*) FROM PRODUCT_DOCS;

SHOW CORTEX SEARCH SERVICES IN SCHEMA {{DATABASE}}.{{SCHEMA}};
