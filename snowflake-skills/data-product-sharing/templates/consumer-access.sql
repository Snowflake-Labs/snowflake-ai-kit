-- =============================================================================
-- Consumer-Side: Access Shared Data
-- =============================================================================
-- Run these commands in the CONSUMER account to mount and verify shared data.
--
-- Replace these placeholders:
--   {{PROVIDER_ACCOUNT}} — Provider's account (ORG.ACCOUNT format)
--   {{SHARE_NAME}}       — Name of the share from the provider
--   {{CONSUMER_DB}}      — Local database name for the shared data
--   {{CONSUMER_ROLE}}    — Role that should have access
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- =============================================================================
-- OPTION A: Access a Direct Share
-- =============================================================================

-- 1. See available shares
SHOW SHARES;

-- 2. Inspect what's in the share
DESCRIBE SHARE {{PROVIDER_ACCOUNT}}.{{SHARE_NAME}};

-- 3. Create a database from the share
CREATE OR REPLACE DATABASE {{CONSUMER_DB}}
  FROM SHARE {{PROVIDER_ACCOUNT}}.{{SHARE_NAME}};

-- 4. Grant access to consumer roles
GRANT IMPORTED PRIVILEGES ON DATABASE {{CONSUMER_DB}} TO ROLE {{CONSUMER_ROLE}};

-- 5. Query the shared data
USE ROLE {{CONSUMER_ROLE}};
SHOW SCHEMAS IN DATABASE {{CONSUMER_DB}};
SHOW VIEWS IN SCHEMA {{CONSUMER_DB}}.{{SCHEMA}};
SELECT * FROM {{CONSUMER_DB}}.{{SCHEMA}}.PRODUCTS_PUBLIC LIMIT 10;
SELECT * FROM {{CONSUMER_DB}}.{{SCHEMA}}.PRODUCT_SUMMARY;

-- =============================================================================
-- OPTION B: Access a Listing (Private or Marketplace)
-- =============================================================================

-- 1. See available listings
SHOW AVAILABLE LISTINGS;

-- 2. Get the listing from Snowsight:
--    Navigate to Marketplace (or Data > Shared With Me)
--    Find the listing and click "Get" / "Install"
--    Snowflake creates a database automatically

-- Or via SQL (for organization listings):
-- CREATE DATABASE {{CONSUMER_DB}} FROM LISTING {{LISTING_NAME}};

-- 3. Grant access to roles
-- GRANT IMPORTED PRIVILEGES ON DATABASE {{CONSUMER_DB}} TO ROLE {{CONSUMER_ROLE}};

-- 4. Query
-- USE ROLE {{CONSUMER_ROLE}};
-- SELECT * FROM {{CONSUMER_DB}}.{{SCHEMA}}.{{TABLE}} LIMIT 10;

-- =============================================================================
-- OPTION C: Access an Organization Listing (Internal Marketplace)
-- =============================================================================

-- Query directly via Universal Listing Locator (ULL) — no install needed:
-- SELECT * FROM ORGDATACLOUD${{PROFILE}}${{LISTING_NAME}}.{{SCHEMA}}.{{TABLE}};

-- =============================================================================
-- Troubleshooting
-- =============================================================================

-- "Share not found":
--   - Verify the share name: SHOW SHARES;
--   - Ensure your account was added: contact the provider

-- "Insufficient privileges":
--   - Need ACCOUNTADMIN or: CREATE DATABASE + IMPORT SHARE privileges
--   - GRANT CREATE DATABASE ON ACCOUNT TO ROLE {{CONSUMER_ROLE}};
--   - GRANT IMPORT SHARE ON ACCOUNT TO ROLE {{CONSUMER_ROLE}};

-- "Listing not available":
--   - Check region: cross-region shares need auto-fulfillment enabled
--   - Check listing status: it may be pending approval (marketplace)

-- Data seems stale (cross-region):
--   - Auto-fulfillment has a refresh interval (default: 1 hour)
--   - Contact provider to check replication schedule
