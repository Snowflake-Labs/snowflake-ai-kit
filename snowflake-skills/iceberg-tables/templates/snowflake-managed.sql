-- Snowflake-Managed Iceberg Table
-- Snowflake owns the catalog -- full read-write support

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- Create Iceberg table with Snowflake as catalog
CREATE OR REPLACE ICEBERG TABLE PRODUCT_REVIEWS (
    review_id INT,
    product_id INT,
    product_name STRING,
    reviewer_name STRING,
    review_date DATE,
    rating INT,
    review_text STRING
)
CATALOG = 'SNOWFLAKE'
EXTERNAL_VOLUME = '{{EXTERNAL_VOLUME_NAME}}'
BASE_LOCATION = 'product_reviews/';

-- Insert sample data
INSERT INTO PRODUCT_REVIEWS VALUES
    (1, 101, 'Wireless Headphones', 'Alice', '2024-01-15', 5, 'Great sound quality'),
    (2, 102, 'USB-C Hub', 'Bob', '2024-01-16', 4, 'Works well with my laptop'),
    (3, 101, 'Wireless Headphones', 'Charlie', '2024-01-17', 3, 'Battery could be better'),
    (4, 103, 'Mechanical Keyboard', 'Diana', '2024-01-18', 5, 'Best keyboard I have owned'),
    (5, 102, 'USB-C Hub', 'Eve', '2024-01-19', 2, 'One port stopped working');

-- Verify data
SELECT * FROM PRODUCT_REVIEWS ORDER BY review_id;

-- Show Iceberg metadata
SHOW ICEBERG TABLES LIKE 'PRODUCT_REVIEWS';

-- Enable change tracking for streams (optional)
ALTER ICEBERG TABLE PRODUCT_REVIEWS SET CHANGE_TRACKING = TRUE;

-- Dynamic Iceberg Table example (optional)
-- Aggregates review data automatically with 10-minute freshness
CREATE OR REPLACE DYNAMIC ICEBERG TABLE PRODUCT_REVIEW_SUMMARY
    TARGET_LAG = '10 minutes'
    WAREHOUSE = {{WAREHOUSE}}
    EXTERNAL_VOLUME = '{{EXTERNAL_VOLUME_NAME}}'
    CATALOG = 'SNOWFLAKE'
    BASE_LOCATION = 'product_review_summary/'
    AS
    SELECT
        product_id,
        product_name,
        COUNT(*) AS review_count,
        AVG(rating) AS avg_rating,
        MIN(review_date) AS first_review,
        MAX(review_date) AS last_review
    FROM PRODUCT_REVIEWS
    GROUP BY product_id, product_name;
