-- Iceberg Tables -- External Volume and Database Setup
-- Replace all {{PLACEHOLDER}} values with your actual configuration

-- Step 1: Create external volume (S3 example)
-- After creating, you MUST update the IAM trust policy (see Step 2 output)
CREATE OR REPLACE EXTERNAL VOLUME {{EXTERNAL_VOLUME_NAME}}
    STORAGE_LOCATIONS = (
        (
            NAME = 'primary'
            STORAGE_BASE_URL = 's3://{{BUCKET_NAME}}/{{PATH}}/'
            STORAGE_PROVIDER = 'S3'
            STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::{{AWS_ACCOUNT_ID}}:role/{{IAM_ROLE_NAME}}'
        )
    )
    ALLOW_WRITES = TRUE;

-- GCS alternative:
-- CREATE OR REPLACE EXTERNAL VOLUME {{EXTERNAL_VOLUME_NAME}}
--     STORAGE_LOCATIONS = (
--         (
--             NAME = 'primary'
--             STORAGE_BASE_URL = 'gcs://{{BUCKET_NAME}}/{{PATH}}/'
--             STORAGE_PROVIDER = 'GCS'
--         )
--     )
--     ALLOW_WRITES = TRUE;

-- Azure alternative:
-- CREATE OR REPLACE EXTERNAL VOLUME {{EXTERNAL_VOLUME_NAME}}
--     STORAGE_LOCATIONS = (
--         (
--             NAME = 'primary'
--             STORAGE_BASE_URL = 'azure://{{ACCOUNT_NAME}}.blob.core.windows.net/{{CONTAINER_NAME}}/{{PATH}}/'
--             STORAGE_PROVIDER = 'AZURE'
--             AZURE_TENANT_ID = '{{TENANT_ID}}'
--         )
--     )
--     ALLOW_WRITES = TRUE;

-- Step 2: Get Snowflake's IAM user ARN and external ID
-- You need these values to update your cloud IAM trust policy
DESCRIBE EXTERNAL VOLUME {{EXTERNAL_VOLUME_NAME}};
-- For S3: Look for STORAGE_AWS_IAM_USER_ARN and STORAGE_AWS_EXTERNAL_ID
-- For GCS: Look for STORAGE_GCP_SERVICE_ACCOUNT
-- For Azure: Look for AZURE_CONSENT_URL and AZURE_MULTI_TENANT_APP_NAME

-- Step 3: Create database and schema for Iceberg tables
CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};

USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};
