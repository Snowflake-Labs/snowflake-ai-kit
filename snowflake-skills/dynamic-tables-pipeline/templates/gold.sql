-- Gold Layer: Business metrics and aggregations
-- These are the "leaf" tables -- set explicit TARGET_LAG here to drive the pipeline

CREATE OR REPLACE DYNAMIC TABLE GOLD_DAILY_REVENUE
    TARGET_LAG = '10 minutes'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        DATE_TRUNC('day', order_date) AS revenue_date,
        region,
        COUNT(DISTINCT order_id) AS total_orders,
        COUNT(DISTINCT customer_id) AS unique_customers,
        SUM(order_total) AS gross_revenue,
        SUM(CASE WHEN status IN ('CANCELLED', 'RETURNED') THEN order_total ELSE 0 END) AS lost_revenue,
        SUM(CASE WHEN status NOT IN ('CANCELLED', 'RETURNED') THEN order_total ELSE 0 END) AS net_revenue,
        AVG(order_total) AS avg_order_value
    FROM SILVER_ORDER_DETAILS
    GROUP BY 1, 2;

CREATE OR REPLACE DYNAMIC TABLE GOLD_CUSTOMER_SEGMENTS
    TARGET_LAG = '10 minutes'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        customer_id,
        customer_name,
        region,
        COUNT(order_id) AS lifetime_orders,
        SUM(order_total) AS lifetime_revenue,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,
        DATEDIFF('day', MAX(order_date), CURRENT_TIMESTAMP()) AS days_since_last_order,
        CASE
            WHEN SUM(order_total) >= 1000 AND COUNT(order_id) >= 5 THEN 'VIP'
            WHEN SUM(order_total) >= 500 THEN 'LOYAL'
            WHEN COUNT(order_id) >= 3 THEN 'REPEAT'
            WHEN DATEDIFF('day', MAX(order_date), CURRENT_TIMESTAMP()) > 60 THEN 'AT_RISK'
            ELSE 'NEW'
        END AS customer_segment
    FROM SILVER_ORDER_DETAILS
    WHERE status NOT IN ('CANCELLED', 'RETURNED')
    GROUP BY customer_id, customer_name, region;
