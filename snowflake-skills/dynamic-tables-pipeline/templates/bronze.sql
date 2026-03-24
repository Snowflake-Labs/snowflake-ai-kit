-- Bronze Layer: Clean and validate raw data
-- TARGET_LAG = DOWNSTREAM (controlled by gold layer)

CREATE OR REPLACE DYNAMIC TABLE BRONZE_ORDERS
    TARGET_LAG = 'DOWNSTREAM'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        order_id,
        customer_id,
        order_date,
        UPPER(TRIM(status)) AS status,
        total_amount,
        loaded_at
    FROM RAW_ORDERS
    WHERE order_id IS NOT NULL
      AND customer_id IS NOT NULL
      AND total_amount > 0;

CREATE OR REPLACE DYNAMIC TABLE BRONZE_CUSTOMERS
    TARGET_LAG = 'DOWNSTREAM'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        customer_id,
        INITCAP(TRIM(first_name)) AS first_name,
        INITCAP(TRIM(last_name)) AS last_name,
        LOWER(TRIM(email)) AS email,
        UPPER(TRIM(region)) AS region,
        created_at
    FROM RAW_CUSTOMERS
    WHERE customer_id IS NOT NULL
      AND email IS NOT NULL;

CREATE OR REPLACE DYNAMIC TABLE BRONZE_ORDER_ITEMS
    TARGET_LAG = 'DOWNSTREAM'
    WAREHOUSE = {{WAREHOUSE}}
    REFRESH_MODE = AUTO
    INITIALIZE = ON_CREATE
    AS
    SELECT
        order_item_id,
        order_id,
        TRIM(product_name) AS product_name,
        UPPER(TRIM(category)) AS category,
        quantity,
        unit_price,
        quantity * unit_price AS line_total,
        loaded_at
    FROM RAW_ORDER_ITEMS
    WHERE order_item_id IS NOT NULL
      AND quantity > 0
      AND unit_price > 0;
