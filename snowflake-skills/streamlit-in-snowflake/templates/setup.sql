-- =============================================================================
-- Streamlit in Snowflake — Infrastructure Setup
-- =============================================================================
-- Creates the stage, warehouse, and grants needed to deploy a Streamlit app.
--
-- Replace these placeholders:
--   {{DATABASE}}     — Target database
--   {{SCHEMA}}       — Target schema
--   {{WAREHOUSE}}    — Warehouse for the app
--   {{COMPUTE_POOL}} — Compute pool (container runtime only)
--   {{STAGE_NAME}}   — Name for the internal stage (default: STREAMLIT_STAGE)
-- =============================================================================

USE ROLE SYSADMIN;

-- 1. Database and schema
CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};

-- 2. Internal stage to hold app source files
CREATE STAGE IF NOT EXISTS {{DATABASE}}.{{SCHEMA}}.{{STAGE_NAME}}
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');

-- 3. Warehouse (if it doesn't exist)
CREATE WAREHOUSE IF NOT EXISTS {{WAREHOUSE}}
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- 4. (Container runtime only) Verify compute pool exists
-- SHOW COMPUTE POOLS LIKE '{{COMPUTE_POOL}}';
-- If you need to create one:
-- CREATE COMPUTE POOL IF NOT EXISTS {{COMPUTE_POOL}}
--   MIN_NODES = 1
--   MAX_NODES = 1
--   INSTANCE_FAMILY = CPU_X64_XS;

-- 5. (Container runtime only) External access integration for PyPI
-- Required to install packages from pip in container runtime.
-- CREATE OR REPLACE NETWORK RULE pypi_network_rule
--   MODE = EGRESS
--   TYPE = HOST_PORT
--   VALUE_LIST = ('pypi.org', 'files.pythonhosted.org');
--
-- CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION pypi_access
--   ALLOWED_NETWORK_RULES = (pypi_network_rule)
--   ENABLED = TRUE;

-- 6. Grant privileges to the deployer role
USE ROLE SECURITYADMIN;

-- The role deploying the app needs these:
-- GRANT CREATE STREAMLIT ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{DEPLOYER_ROLE}};
-- GRANT READ ON STAGE {{DATABASE}}.{{SCHEMA}}.{{STAGE_NAME}} TO ROLE {{DEPLOYER_ROLE}};
-- GRANT USAGE ON WAREHOUSE {{WAREHOUSE}} TO ROLE {{DEPLOYER_ROLE}};

-- For viewers of the app:
-- GRANT USAGE ON STREAMLIT {{DATABASE}}.{{SCHEMA}}.{{APP_NAME}} TO ROLE {{VIEWER_ROLE}};
