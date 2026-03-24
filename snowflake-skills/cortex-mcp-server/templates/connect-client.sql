-- ============================================================
-- Cortex MCP Server — Client Connection & Access Control
-- Authentication, RBAC, and client configuration
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- RBAC: Grant access to MCP server and tools
-- ────────────────────────────────────────────────────────────

-- MCP server access (required to discover tools)
GRANT USAGE ON MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}}
    TO ROLE {{CONSUMER_ROLE}};

-- Tool-level access (required to invoke each tool)
-- Analyst tool: grant semantic view access
GRANT USAGE ON SEMANTIC VIEW {{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW
    TO ROLE {{CONSUMER_ROLE}};

-- Search tool: grant search service access
GRANT USAGE ON CORTEX SEARCH SERVICE {{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE
    TO ROLE {{CONSUMER_ROLE}};

-- Agent tool: grant agent access
-- GRANT USAGE ON AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}
--     TO ROLE {{CONSUMER_ROLE}};

-- Custom tool: grant function/procedure access
GRANT USAGE ON FUNCTION {{DATABASE}}.{{SCHEMA}}.CALCULATE_METRICS(FLOAT, FLOAT)
    TO ROLE {{CONSUMER_ROLE}};

-- Cortex user role (for AI function access)
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{CONSUMER_ROLE}};

-- Warehouse for SQL execution and custom tools
GRANT USAGE ON WAREHOUSE {{WAREHOUSE}} TO ROLE {{CONSUMER_ROLE}};

-- ────────────────────────────────────────────────────────────
-- Authentication: OAuth (recommended)
-- ────────────────────────────────────────────────────────────

-- Create OAuth security integration for MCP clients
-- CREATE OR REPLACE SECURITY INTEGRATION mcp_oauth_integration
--     TYPE = OAUTH
--     OAUTH_CLIENT = CUSTOM
--     OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
--     OAUTH_REDIRECT_URI = 'http://localhost:8080/callback'
--     ENABLED = TRUE;

-- ────────────────────────────────────────────────────────────
-- Client connection URLs
-- ────────────────────────────────────────────────────────────

-- MCP SSE endpoint:
-- https://{{ACCOUNT_IDENTIFIER}}.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse
--
-- Important: Use hyphens (-) not underscores (_) in hostnames.

-- ────────────────────────────────────────────────────────────
-- Connect from Cortex Code CLI
-- ────────────────────────────────────────────────────────────

-- cortex mcp add snowflake-tools \
--     https://{{ACCOUNT_IDENTIFIER}}.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse \
--     --transport http

-- ────────────────────────────────────────────────────────────
-- Connect from Claude Desktop
-- ────────────────────────────────────────────────────────────

-- Add to claude_desktop_config.json:
-- {
--   "mcpServers": {
--     "snowflake": {
--       "url": "https://{{ACCOUNT_IDENTIFIER}}.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse",
--       "transport": "sse"
--     }
--   }
-- }

-- ────────────────────────────────────────────────────────────
-- Connect from Cursor
-- ────────────────────────────────────────────────────────────

-- Add to .cursor/mcp.json:
-- {
--   "mcpServers": {
--     "snowflake": {
--       "url": "https://{{ACCOUNT_IDENTIFIER}}.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse",
--       "transport": "sse"
--     }
--   }
-- }

-- ────────────────────────────────────────────────────────────
-- Server management
-- ────────────────────────────────────────────────────────────

SHOW MCP SERVERS IN SCHEMA {{DATABASE}}.{{SCHEMA}};
DESCRIBE MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}};

-- Drop: DROP MCP SERVER IF EXISTS {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}};
