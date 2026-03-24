-- =============================================================================
-- Create a Secure Share
-- =============================================================================
-- Shares data directly with specific Snowflake accounts.
-- The consumer gets a read-only database from the share.
--
-- Replace these placeholders:
--   {{DATABASE}}        — Source database containing the objects to share
--   {{SCHEMA}}          — Source schema
--   {{SHARE_NAME}}      — Name for the share
--   {{CONSUMER_ACCOUNT}} — Target account (ORG.ACCOUNT format)
-- =============================================================================

USE ROLE ACCOUNTADMIN;

-- 1. Create an empty share
CREATE OR REPLACE SHARE {{SHARE_NAME}}
  COMMENT = 'Product catalog data shared with partners';

-- 2. Grant access to the database (required — share needs a database context)
GRANT USAGE ON DATABASE {{DATABASE}} TO SHARE {{SHARE_NAME}};

-- 3. Grant access to the schema
GRANT USAGE ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO SHARE {{SHARE_NAME}};

-- 4. Grant SELECT on specific objects
-- Share a secure view (recommended over raw tables)
GRANT SELECT ON VIEW {{DATABASE}}.{{SCHEMA}}.PRODUCTS_PUBLIC TO SHARE {{SHARE_NAME}};
GRANT SELECT ON VIEW {{DATABASE}}.{{SCHEMA}}.PRODUCT_SUMMARY TO SHARE {{SHARE_NAME}};

-- Or share a table directly:
-- GRANT SELECT ON TABLE {{DATABASE}}.{{SCHEMA}}.PRODUCTS TO SHARE {{SHARE_NAME}};

-- 5. Add consumer accounts
ALTER SHARE {{SHARE_NAME}} ADD ACCOUNTS = {{CONSUMER_ACCOUNT}};

-- Add multiple consumers:
-- ALTER SHARE {{SHARE_NAME}} ADD ACCOUNTS = org1.account1, org2.account2;

-- 6. Verify the share
DESCRIBE SHARE {{SHARE_NAME}};
SHOW GRANTS TO SHARE {{SHARE_NAME}};

-- =============================================================================
-- Managing the share
-- =============================================================================

-- Add more objects later:
-- GRANT SELECT ON VIEW {{DATABASE}}.{{SCHEMA}}.new_view TO SHARE {{SHARE_NAME}};

-- Remove an object:
-- REVOKE SELECT ON VIEW {{DATABASE}}.{{SCHEMA}}.old_view FROM SHARE {{SHARE_NAME}};

-- Remove a consumer:
-- ALTER SHARE {{SHARE_NAME}} REMOVE ACCOUNTS = org1.account1;

-- See all shares:
-- SHOW SHARES;

-- Delete the share:
-- DROP SHARE {{SHARE_NAME}};
