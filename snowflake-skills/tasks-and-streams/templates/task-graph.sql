-- Task Graph (DAG): Multi-step pipeline with dependencies
-- Pattern: raw -> staged -> aggregated

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

----------------------------------------------------------------------
-- Supporting tables
----------------------------------------------------------------------

CREATE OR REPLACE TABLE STAGED_ORDERS (
    order_id NUMBER,
    customer_id NUMBER,
    product_name VARCHAR,
    amount NUMBER(12,2),
    order_date DATE,
    status VARCHAR,
    staged_at TIMESTAMP_NTZ
);

CREATE OR REPLACE TABLE ORDER_METRICS (
    metric_date DATE,
    total_orders NUMBER,
    total_revenue NUMBER(12,2),
    avg_order_value NUMBER(12,2),
    unique_customers NUMBER,
    calculated_at TIMESTAMP_NTZ
);

----------------------------------------------------------------------
-- Stream for the staging step
-- Reuses SOURCE_ORDERS_STREAM if it exists; otherwise create a new one
----------------------------------------------------------------------

CREATE STREAM IF NOT EXISTS SOURCE_ORDERS_STREAM ON TABLE SOURCE_ORDERS;
CREATE OR REPLACE STREAM STAGED_ORDERS_STREAM ON TABLE STAGED_ORDERS;

----------------------------------------------------------------------
-- Root task: Runs on schedule, stages raw data
----------------------------------------------------------------------

CREATE OR REPLACE TASK STAGE_RAW_ORDERS
    WAREHOUSE = {{WAREHOUSE}}
    SCHEDULE = '10 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('SOURCE_ORDERS_STREAM')
AS
    INSERT INTO STAGED_ORDERS
    SELECT
        order_id,
        customer_id,
        UPPER(TRIM(product_name)),
        amount,
        order_date,
        UPPER(TRIM(status)),
        CURRENT_TIMESTAMP()
    FROM SOURCE_ORDERS_STREAM
    WHERE amount > 0;

----------------------------------------------------------------------
-- Child task: Runs AFTER root, aggregates staged data
----------------------------------------------------------------------

CREATE OR REPLACE TASK AGGREGATE_ORDER_METRICS
    WAREHOUSE = {{WAREHOUSE}}
    AFTER STAGE_RAW_ORDERS
AS
    MERGE INTO ORDER_METRICS target
    USING (
        SELECT
            order_date AS metric_date,
            COUNT(*) AS total_orders,
            SUM(amount) AS total_revenue,
            AVG(amount) AS avg_order_value,
            COUNT(DISTINCT customer_id) AS unique_customers,
            CURRENT_TIMESTAMP() AS calculated_at
        FROM STAGED_ORDERS_STREAM
        GROUP BY order_date
    ) source
    ON target.metric_date = source.metric_date
    WHEN MATCHED THEN UPDATE SET
        target.total_orders = target.total_orders + source.total_orders,
        target.total_revenue = target.total_revenue + source.total_revenue,
        target.avg_order_value = (target.total_revenue + source.total_revenue) /
                                  NULLIF(target.total_orders + source.total_orders, 0),
        target.unique_customers = source.unique_customers,
        target.calculated_at = source.calculated_at
    WHEN NOT MATCHED THEN INSERT
        (metric_date, total_orders, total_revenue, avg_order_value, unique_customers, calculated_at)
        VALUES (source.metric_date, source.total_orders, source.total_revenue,
                source.avg_order_value, source.unique_customers, source.calculated_at);

----------------------------------------------------------------------
-- IMPORTANT: Resume in reverse dependency order (children first!)
----------------------------------------------------------------------

ALTER TASK AGGREGATE_ORDER_METRICS RESUME;
ALTER TASK STAGE_RAW_ORDERS RESUME;

----------------------------------------------------------------------
-- Monitoring
----------------------------------------------------------------------

-- Task run history
-- SELECT * FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
--     TASK_NAME => 'STAGE_RAW_ORDERS',
--     SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
-- )) ORDER BY SCHEDULED_TIME DESC;

-- View all tasks and their dependencies
-- SHOW TASKS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Check aggregated metrics
-- SELECT * FROM ORDER_METRICS ORDER BY metric_date DESC LIMIT 10;
