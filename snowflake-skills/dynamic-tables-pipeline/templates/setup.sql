-- Dynamic Tables Pipeline -- Demo Setup
-- Creates raw source tables and seeds sample e-commerce data

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- Raw source tables (simulating landing zone)
CREATE OR REPLACE TABLE RAW_CUSTOMERS (
    customer_id NUMBER,
    first_name VARCHAR,
    last_name VARCHAR,
    email VARCHAR,
    region VARCHAR,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE RAW_ORDERS (
    order_id NUMBER,
    customer_id NUMBER,
    order_date TIMESTAMP_NTZ,
    status VARCHAR,
    total_amount NUMBER(12,2),
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE RAW_ORDER_ITEMS (
    order_item_id NUMBER,
    order_id NUMBER,
    product_name VARCHAR,
    category VARCHAR,
    quantity NUMBER,
    unit_price NUMBER(12,2),
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Seed data: 100 customers
INSERT INTO RAW_CUSTOMERS (customer_id, first_name, last_name, email, region)
SELECT
    SEQ4() + 1,
    'First_' || (SEQ4() + 1),
    'Last_' || (SEQ4() + 1),
    'user' || (SEQ4() + 1) || '@example.com',
    CASE MOD(SEQ4(), 4)
        WHEN 0 THEN 'AMER'
        WHEN 1 THEN 'EMEA'
        WHEN 2 THEN 'APAC'
        ELSE 'LATAM'
    END
FROM TABLE(GENERATOR(ROWCOUNT => 100));

-- Seed data: 1000 orders
INSERT INTO RAW_ORDERS (order_id, customer_id, order_date, status, total_amount)
SELECT
    SEQ4() + 1,
    UNIFORM(1, 100, RANDOM()),
    DATEADD('day', -UNIFORM(0, 90, RANDOM()), CURRENT_TIMESTAMP()),
    CASE MOD(SEQ4(), 5)
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'shipped'
        WHEN 2 THEN 'delivered'
        WHEN 3 THEN 'cancelled'
        ELSE 'returned'
    END,
    ROUND(UNIFORM(10, 500, RANDOM())::NUMBER(12,2), 2)
FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- Seed data: ~3000 order items (avg 3 per order)
INSERT INTO RAW_ORDER_ITEMS (order_item_id, order_id, product_name, category, quantity, unit_price)
SELECT
    SEQ4() + 1,
    UNIFORM(1, 1000, RANDOM()),
    'Product_' || UNIFORM(1, 50, RANDOM()),
    CASE MOD(SEQ4(), 5)
        WHEN 0 THEN 'Electronics'
        WHEN 1 THEN 'Clothing'
        WHEN 2 THEN 'Home'
        WHEN 3 THEN 'Sports'
        ELSE 'Books'
    END,
    UNIFORM(1, 5, RANDOM()),
    ROUND(UNIFORM(5, 200, RANDOM())::NUMBER(12,2), 2)
FROM TABLE(GENERATOR(ROWCOUNT => 3000));
