-- CDC Pipeline: Stream + Task + MERGE
-- Captures changes from source and applies to target incrementally

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

----------------------------------------------------------------------
-- Basic CDC: Stream + MERGE Task
----------------------------------------------------------------------

-- Create stream on source table
CREATE OR REPLACE STREAM SOURCE_ORDERS_STREAM
    ON TABLE SOURCE_ORDERS;

-- Create task that processes changes via MERGE
CREATE OR REPLACE TASK PROCESS_ORDER_CHANGES
    WAREHOUSE = {{WAREHOUSE}}
    SCHEDULE = '5 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('SOURCE_ORDERS_STREAM')
AS
    MERGE INTO DWH_ORDERS target
    USING (
        SELECT
            order_id,
            customer_id,
            product_name,
            amount,
            order_date,
            status,
            METADATA$ACTION AS action,
            METADATA$ISUPDATE AS is_update
        FROM SOURCE_ORDERS_STREAM
    ) source
    ON target.order_id = source.order_id
    -- Handle deletes (DELETE action that is NOT part of an update)
    WHEN MATCHED AND source.action = 'DELETE' AND NOT source.is_update THEN
        DELETE
    -- Handle updates and new data (INSERT action covers both new rows and update pairs)
    WHEN MATCHED AND source.action = 'INSERT' THEN
        UPDATE SET
            target.customer_id = source.customer_id,
            target.product_name = source.product_name,
            target.amount = source.amount,
            target.order_date = source.order_date,
            target.status = source.status,
            target.updated_at = CURRENT_TIMESTAMP()
    -- Handle new inserts
    WHEN NOT MATCHED AND source.action = 'INSERT' THEN
        INSERT (order_id, customer_id, product_name, amount, order_date, status, loaded_at, updated_at)
        VALUES (source.order_id, source.customer_id, source.product_name, source.amount,
                source.order_date, source.status, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());

----------------------------------------------------------------------
-- SCD Type 2: History Tracking (Optional)
----------------------------------------------------------------------

-- Separate stream for history (each stream is consumed independently)
CREATE OR REPLACE STREAM SOURCE_ORDERS_HISTORY_STREAM
    ON TABLE SOURCE_ORDERS;

CREATE OR REPLACE TASK TRACK_ORDER_HISTORY
    WAREHOUSE = {{WAREHOUSE}}
    SCHEDULE = '5 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('SOURCE_ORDERS_HISTORY_STREAM')
AS
BEGIN
    -- Close existing current records for changed orders
    UPDATE DWH_ORDERS_HISTORY
    SET valid_to = CURRENT_TIMESTAMP(), is_current = FALSE
    WHERE order_id IN (
        SELECT order_id FROM SOURCE_ORDERS_HISTORY_STREAM
    ) AND is_current = TRUE;

    -- Insert new version of changed records
    INSERT INTO DWH_ORDERS_HISTORY
        (order_id, customer_id, product_name, amount, order_date, status,
         change_type, valid_from, is_current)
    SELECT
        order_id, customer_id, product_name, amount, order_date, status,
        CASE
            WHEN METADATA$ACTION = 'INSERT' AND NOT METADATA$ISUPDATE THEN 'INSERT'
            WHEN METADATA$ACTION = 'INSERT' AND METADATA$ISUPDATE THEN 'UPDATE'
            WHEN METADATA$ACTION = 'DELETE' AND NOT METADATA$ISUPDATE THEN 'DELETE'
            ELSE 'UPDATE'
        END,
        CURRENT_TIMESTAMP(),
        CASE WHEN METADATA$ACTION = 'DELETE' AND NOT METADATA$ISUPDATE THEN FALSE ELSE TRUE END
    FROM SOURCE_ORDERS_HISTORY_STREAM
    WHERE METADATA$ACTION = 'INSERT'
       OR (METADATA$ACTION = 'DELETE' AND NOT METADATA$ISUPDATE);
END;

----------------------------------------------------------------------
-- Resume tasks (history task first since it is independent)
----------------------------------------------------------------------

ALTER TASK TRACK_ORDER_HISTORY RESUME;
ALTER TASK PROCESS_ORDER_CHANGES RESUME;

----------------------------------------------------------------------
-- Test: Make changes to source, then wait ~5 minutes and verify
----------------------------------------------------------------------

-- INSERT INTO SOURCE_ORDERS (order_id, customer_id, product_name, amount, order_date)
--     VALUES (9001, 42, 'New Product', 99.99, CURRENT_DATE());
-- UPDATE SOURCE_ORDERS SET amount = 149.99, status = 'UPDATED' WHERE order_id = 1;
-- DELETE FROM SOURCE_ORDERS WHERE order_id = 2;

-- Verify (after task runs):
-- SELECT COUNT(*) FROM DWH_ORDERS;
-- SELECT * FROM DWH_ORDERS WHERE order_id IN (1, 2, 9001);
-- SELECT * FROM DWH_ORDERS_HISTORY WHERE order_id = 1 ORDER BY valid_from;
