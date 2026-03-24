-- External Catalog Iceberg Tables
-- For tables managed by REST catalog or existing files in object storage

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

----------------------------------------------------------------------
-- Option A: REST Catalog (Polaris / Snowflake Open Catalog)
----------------------------------------------------------------------

-- Create catalog integration for REST catalog
CREATE OR REPLACE CATALOG INTEGRATION {{CATALOG_INTEGRATION_NAME}}
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT = ICEBERG
    CATALOG_URI = '{{CATALOG_URI}}'
    WAREHOUSE = '{{CATALOG_WAREHOUSE}}'
    CATALOG_NAMESPACE = '{{CATALOG_NAMESPACE}}'
    ENABLED = TRUE;

-- Create Iceberg table from REST catalog
CREATE OR REPLACE ICEBERG TABLE EXTERNAL_PRODUCTS
    EXTERNAL_VOLUME = '{{EXTERNAL_VOLUME_NAME}}'
    CATALOG = '{{CATALOG_INTEGRATION_NAME}}'
    CATALOG_TABLE_NAME = '{{REMOTE_TABLE_NAME}}'
    AUTO_REFRESH = TRUE;

-- Verify
SELECT COUNT(*) FROM EXTERNAL_PRODUCTS;

----------------------------------------------------------------------
-- Option B: Iceberg files in object storage (read-only)
----------------------------------------------------------------------

-- Create catalog integration for object store files
CREATE OR REPLACE CATALOG INTEGRATION {{FILES_CATALOG_INTEGRATION}}
    CATALOG_SOURCE = OBJECT_STORE
    TABLE_FORMAT = ICEBERG
    ENABLED = TRUE;

-- Create Iceberg table from metadata file
CREATE OR REPLACE ICEBERG TABLE ARCHIVED_SALES
    EXTERNAL_VOLUME = '{{EXTERNAL_VOLUME_NAME}}'
    CATALOG = '{{FILES_CATALOG_INTEGRATION}}'
    METADATA_FILE_PATH = '{{METADATA_FILE_PATH}}';

-- Refresh from updated metadata file
-- ALTER ICEBERG TABLE ARCHIVED_SALES REFRESH '{{NEW_METADATA_FILE_PATH}}';

-- Verify
SELECT COUNT(*) FROM ARCHIVED_SALES;

----------------------------------------------------------------------
-- Option C: Delta files in object storage
----------------------------------------------------------------------

-- Create catalog integration for Delta format
-- CREATE OR REPLACE CATALOG INTEGRATION {{DELTA_CATALOG_INTEGRATION}}
--     CATALOG_SOURCE = OBJECT_STORE
--     TABLE_FORMAT = DELTA
--     ENABLED = TRUE;

-- Create Iceberg table from Delta files
-- CREATE OR REPLACE ICEBERG TABLE DELTA_ORDERS
--     EXTERNAL_VOLUME = '{{EXTERNAL_VOLUME_NAME}}'
--     CATALOG = '{{DELTA_CATALOG_INTEGRATION}}'
--     BASE_LOCATION = '{{DELTA_TABLE_PATH}}/'
--     AUTO_REFRESH = TRUE;

----------------------------------------------------------------------
-- Common operations
----------------------------------------------------------------------

SHOW ICEBERG TABLES IN SCHEMA {{DATABASE}}.{{SCHEMA}};
