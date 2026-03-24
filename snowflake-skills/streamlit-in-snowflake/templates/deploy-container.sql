-- =============================================================================
-- Deploy Streamlit App — Container Runtime
-- =============================================================================
-- Deploys a Streamlit app using the container runtime (SPCS).
-- Full pip access, GPU support, custom packages.
--
-- Replace these placeholders:
--   {{DATABASE}}     — Target database
--   {{SCHEMA}}       — Target schema
--   {{WAREHOUSE}}    — Warehouse for SQL queries
--   {{COMPUTE_POOL}} — Compute pool to run the app
--   {{STAGE_NAME}}   — Internal stage name (from setup.sql)
--   {{APP_NAME}}     — Name for the Streamlit object
-- =============================================================================

USE ROLE SYSADMIN;
USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- 1. Upload app files to stage
-- From SnowSQL or Snowflake CLI:
--   PUT file://streamlit_app.py @{{STAGE_NAME}}/app AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--   PUT file://pyproject.toml @{{STAGE_NAME}}/app AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Verify files are staged
LIST @{{STAGE_NAME}}/app;

-- 2. Create the Streamlit object (container runtime)
CREATE OR REPLACE STREAMLIT {{APP_NAME}}
  FROM @{{STAGE_NAME}}/app
  MAIN_FILE = 'streamlit_app.py'
  RUNTIME_NAME = 'SYSTEM$ST_CONTAINER_RUNTIME_PY3_11'
  COMPUTE_POOL = {{COMPUTE_POOL}}
  QUERY_WAREHOUSE = {{WAREHOUSE}};

-- Note: Container runtime needs external access for PyPI packages.
-- If you have an external access integration:
-- ALTER STREAMLIT {{APP_NAME}} SET
--   EXTERNAL_ACCESS_INTEGRATIONS = (pypi_access);

-- 3. Activate the live version
ALTER STREAMLIT {{APP_NAME}} ADD LIVE VERSION FROM LAST;

-- 4. Verify deployment
DESCRIBE STREAMLIT {{APP_NAME}};
SHOW STREAMLITS LIKE '{{APP_NAME}}';

-- 5. Grant access to viewers
-- GRANT USAGE ON STREAMLIT {{DATABASE}}.{{SCHEMA}}.{{APP_NAME}} TO ROLE {{VIEWER_ROLE}};

-- =============================================================================
-- Migrating from warehouse to container runtime
-- =============================================================================
-- ALTER STREAMLIT {{APP_NAME}} SET
--   RUNTIME_NAME = 'SYSTEM$ST_CONTAINER_RUNTIME_PY3_11'
--   COMPUTE_POOL = {{COMPUTE_POOL}}
--   EXTERNAL_ACCESS_INTEGRATIONS = (pypi_access);

-- =============================================================================
-- Adding secrets (container runtime uses SQL functions, not SECRETS param)
-- For warehouse runtime secrets, see deploy-warehouse.sql
-- =============================================================================
-- In your Streamlit app code (container runtime):
--   import _snowflake
--   api_key = _snowflake.get_generic_secret_string('api_key')
