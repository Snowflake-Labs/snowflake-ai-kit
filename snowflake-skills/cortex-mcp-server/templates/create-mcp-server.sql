-- ============================================================
-- Cortex MCP Server — Create MCP Server
-- Defines the MCP server with tool configurations
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Option A: Full MCP server with all tool types
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE MCP SERVER {{MCP_SERVER_NAME}}
  FROM SPECIFICATION
  $$
  tools:
    - name: "revenue-analyst"
      type: "CORTEX_ANALYST_MESSAGE"
      identifier: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      description: "Query revenue and sales metrics using natural language. Converts questions to SQL."
      title: "Revenue Analyst"

    - name: "doc-search"
      type: "CORTEX_SEARCH_SERVICE_QUERY"
      identifier: "{{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE"
      description: "Search product documentation, policies, and troubleshooting guides."
      title: "Document Search"

    - name: "sql-exec"
      type: "SYSTEM_EXECUTE_SQL"
      title: "SQL Execution"
      name: "sql_exec"
      description: "Execute SQL queries directly against the Snowflake database."

    - name: "business-agent"
      type: "CORTEX_AGENT_RUN"
      identifier: "{{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}"
      description: "AI agent that routes questions to Analyst or Search automatically."
      title: "Business Agent"
  $$;

-- ────────────────────────────────────────────────────────────
-- Option B: MCP server with custom UDF tools
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE MCP SERVER {{MCP_SERVER_NAME}}_WITH_TOOLS
  FROM SPECIFICATION
  $$
  tools:
    - name: "revenue-analyst"
      type: "CORTEX_ANALYST_MESSAGE"
      identifier: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      description: "Query revenue and sales metrics using natural language"
      title: "Revenue Analyst"

    - name: "calculate-metrics"
      type: "GENERIC"
      title: "Metrics Calculator"
      description: "Calculate profit and margin from revenue and cost inputs"
      identifier: "{{DATABASE}}.{{SCHEMA}}.CALCULATE_METRICS"
      config:
        type: "function"
        warehouse: "{{WAREHOUSE}}"
        input_schema:
          type: "object"
          properties:
            revenue:
              type: "number"
              description: "Total revenue amount"
            cost:
              type: "number"
              description: "Total cost amount"
          required: ["revenue", "cost"]

    - name: "generate-report"
      type: "GENERIC"
      title: "Report Generator"
      description: "Generate a sales report for a specific region"
      identifier: "{{DATABASE}}.{{SCHEMA}}.GENERATE_REPORT"
      config:
        type: "procedure"
        warehouse: "{{WAREHOUSE}}"
        input_schema:
          type: "object"
          properties:
            region:
              type: "string"
              description: "Sales region (North America, Europe, Asia Pacific, Latin America)"
          required: ["region"]
  $$;

-- ────────────────────────────────────────────────────────────
-- Option C: Minimal MCP server (Analyst + Search only)
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE MCP SERVER {{MCP_SERVER_NAME}}_MINIMAL
  FROM SPECIFICATION
  $$
  tools:
    - name: "analyst"
      type: "CORTEX_ANALYST_MESSAGE"
      identifier: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      description: "Query structured data using natural language"
      title: "Data Analyst"

    - name: "search"
      type: "CORTEX_SEARCH_SERVICE_QUERY"
      identifier: "{{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE"
      description: "Search documentation and policies"
      title: "Doc Search"
  $$;

-- ────────────────────────────────────────────────────────────
-- Verify
-- ────────────────────────────────────────────────────────────

SHOW MCP SERVERS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

DESCRIBE MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}};
