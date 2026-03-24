-- Silver Layer: Join and enrich
-- TARGET_LAG = DOWNSTREAM (controlled by gold layer)

CREATE OR REPLACE DYNAMIC TABLE SILVER_ORDER_DETAILS
    TARGET_LAG = 'DOWNSTREAM'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        o.order_id,
        o.customer_id,
        c.first_name || ' ' || c.last_name AS customer_name,
        c.email AS customer_email,
        c.region,
        o.order_date,
        o.status,
        o.total_amount AS order_total,
        COUNT(i.order_item_id) AS item_count,
        SUM(i.line_total) AS items_subtotal,
        CASE
            WHEN o.total_amount >= 200 THEN 'HIGH'
            WHEN o.total_amount >= 50 THEN 'MEDIUM'
            ELSE 'LOW'
        END AS order_tier,
        DATEDIFF('day', o.order_date, CURRENT_TIMESTAMP()) AS days_since_order
    FROM BRONZE_ORDERS o
    JOIN BRONZE_CUSTOMERS c ON o.customer_id = c.customer_id
    LEFT JOIN BRONZE_ORDER_ITEMS i ON o.order_id = i.order_id
    GROUP BY
        o.order_id, o.customer_id, c.first_name, c.last_name,
        c.email, c.region, o.order_date, o.status, o.total_amount;
