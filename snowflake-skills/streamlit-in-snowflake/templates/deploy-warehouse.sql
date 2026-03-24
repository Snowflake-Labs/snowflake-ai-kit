-- =============================================================================
-- Deploy Streamlit App — Warehouse Runtime
-- =============================================================================
-- Deploys a Streamlit app using the warehouse runtime (simpler, auto-scaled).
-- Each viewer gets their own personal instance of the app.
--
-- Replace these placeholders:
--   {{DATABASE}}   — Target database
--   {{SCHEMA}}     — Target schema
--   {{WAREHOUSE}}  — Warehouse for the app
--   {{STAGE_NAME}} — Internal stage name (from setup.sql)
--   {{APP_NAME}}   — Name for the Streamlit object
-- =============================================================================

USE ROLE SYSADMIN;
USE DATABASE {{DATABASE}};
USE SCHEMA {{SCHEMA}};

-- 1. Upload app files to stage
-- From SnowSQL or Snowflake CLI:
--   PUT file://streamlit_app.py @{{STAGE_NAME}}/app AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
--   PUT file://environment.yml @{{STAGE_NAME}}/app AUTO_COMPRESS=FALSE OVERWRITE=TRUE;

-- Verify files are staged
LIST @{{STAGE_NAME}}/app;

-- 2. Create the Streamlit object (warehouse runtime)
CREATE OR REPLACE STREAMLIT {{APP_NAME}}
  FROM @{{STAGE_NAME}}/app
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = {{WAREHOUSE}};

-- 3. Activate the live version (required for other roles to see the app)
ALTER STREAMLIT {{APP_NAME}} ADD LIVE VERSION FROM LAST;

-- 4. Verify deployment
DESCRIBE STREAMLIT {{APP_NAME}};
SHOW STREAMLITS LIKE '{{APP_NAME}}';

-- 5. Grant access to viewers
-- GRANT USAGE ON STREAMLIT {{DATABASE}}.{{SCHEMA}}.{{APP_NAME}} TO ROLE {{VIEWER_ROLE}};

-- =============================================================================
-- Alternative: Minimal deployment with default starter files
-- (Snowflake creates a basic app — edit in Snowsight afterward)
-- =============================================================================
-- CREATE STREAMLIT {{APP_NAME}}
--   QUERY_WAREHOUSE = {{WAREHOUSE}};
-- ALTER STREAMLIT {{APP_NAME}} ADD LIVE VERSION FROM LAST;

-- =============================================================================
-- Alternative: Deploy from a Git repository
-- =============================================================================
-- CREATE STREAMLIT {{APP_NAME}}
--   FROM @{{DATABASE}}.{{SCHEMA}}.my_git_repo/branches/main/
--   MAIN_FILE = 'streamlit_app.py'
--   QUERY_WAREHOUSE = {{WAREHOUSE}};
-- ALTER STREAMLIT {{APP_NAME}} ADD LIVE VERSION FROM LAST;
