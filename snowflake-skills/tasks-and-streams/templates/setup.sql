-- Tasks and Streams -- Demo Setup
-- Creates source and target tables with seed data

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- Source table (simulates external system or landing zone)
CREATE OR REPLACE TABLE SOURCE_ORDERS (
    order_id NUMBER PRIMARY KEY,
    customer_id NUMBER,
    product_name VARCHAR,
    amount NUMBER(12,2),
    order_date DATE,
    status VARCHAR DEFAULT 'NEW',
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Target table (data warehouse)
CREATE OR REPLACE TABLE DWH_ORDERS (
    order_id NUMBER PRIMARY KEY,
    customer_id NUMBER,
    product_name VARCHAR,
    amount NUMBER(12,2),
    order_date DATE,
    status VARCHAR,
    loaded_at TIMESTAMP_NTZ,
    updated_at TIMESTAMP_NTZ
);

-- History table for SCD Type 2 tracking
CREATE OR REPLACE TABLE DWH_ORDERS_HISTORY (
    order_id NUMBER,
    customer_id NUMBER,
    product_name VARCHAR,
    amount NUMBER(12,2),
    order_date DATE,
    status VARCHAR,
    change_type VARCHAR,
    valid_from TIMESTAMP_NTZ,
    valid_to TIMESTAMP_NTZ DEFAULT '9999-12-31'::TIMESTAMP_NTZ,
    is_current BOOLEAN DEFAULT TRUE
);

-- Seed source data (500 orders)
INSERT INTO SOURCE_ORDERS (order_id, customer_id, product_name, amount, order_date)
SELECT
    SEQ4() + 1,
    UNIFORM(1, 100, RANDOM()),
    'Product_' || UNIFORM(1, 20, RANDOM()),
    ROUND(UNIFORM(10, 500, RANDOM())::NUMBER(12,2), 2),
    DATEADD('day', -UNIFORM(0, 30, RANDOM()), CURRENT_DATE())
FROM TABLE(GENERATOR(ROWCOUNT => 500));

-- Uncomment if the role does not already have EXECUTE TASK privilege:
-- GRANT EXECUTE TASK ON ACCOUNT TO ROLE {{ROLE}};
