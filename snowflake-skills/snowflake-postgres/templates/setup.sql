-- =============================================================
-- Snowflake Postgres — Instance Setup
-- =============================================================
-- Creates a network policy and Postgres instance.
-- Run this in a Snowflake worksheet (not psql).
-- Requires ACCOUNTADMIN or CREATE POSTGRES INSTANCE privilege.
-- =============================================================

-- 1. Set your role
USE ROLE ACCOUNTADMIN;

-- 2. Create a network rule for Postgres ingress
--    Replace <YOUR_IP> with your public IP (e.g., 203.0.113.42)
CREATE OR REPLACE NETWORK RULE my_pg_rule
  MODE = POSTGRES_INGRESS
  TYPE = IPV4
  VALUE_LIST = ('<YOUR_IP>/32');

-- 3. Create a network policy using the rule
CREATE OR REPLACE NETWORK POLICY my_pg_policy
  ALLOWED_NETWORK_RULE_LIST = ('my_pg_rule');

-- 4. Create the Postgres instance
--    Adjust name, compute, storage, and version as needed
CREATE POSTGRES INSTANCE my_postgres
  COMPUTE_POOL = 'BURSTABLE_1'
  STORAGE_SIZE_GB = 10
  POSTGRES_VERSION = '18'
  NETWORK_POLICY = 'my_pg_policy'
  AUTHENTICATION_AUTHORITY = POSTGRES
  AUTO_SUSPEND_SECS = 3600;

-- 5. View instance details and credentials
--    IMPORTANT: Save the password now — it's shown only once
DESCRIBE POSTGRES INSTANCE my_postgres;

-- 6. Verify instance is running
SHOW POSTGRES INSTANCES;
