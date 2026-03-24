-- ============================================================
-- Cortex Agents — Create Agent
-- Defines agent with Analyst + Search tools
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Create the agent
-- ────────────────────────────────────────────────────────────

CREATE OR REPLACE AGENT {{AGENT_NAME}}
  COMMENT = 'Business assistant — routes to Analyst for metrics, Search for docs'
  PROFILE = '{"display_name": "{{DISPLAY_NAME}}"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: claude-4-sonnet

  orchestration:
    budget:
      seconds: 30
      tokens: 16000

  instructions:
    system: "You are a helpful business assistant for a technology products company. You can answer questions about sales data and product documentation."
    orchestration: "Use Analyst for any question about sales, revenue, quantities, orders, or metrics. Use Search for product documentation, policies, troubleshooting, or how-to questions."
    response: "Be concise. Include specific numbers from Analyst queries. Cite document titles from Search results."
    sample_questions:
      - question: "What was total revenue last quarter?"
      - question: "Which region had the most sales?"
      - question: "What is the return policy for electronics?"
      - question: "How do I set up the wireless mouse?"

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "Analyst"
        description: "Queries structured sales data by converting natural language questions to SQL. Use for revenue, quantities, orders, and business metrics."
    - tool_spec:
        type: "cortex_search"
        name: "Search"
        description: "Searches product documentation, company policies, and troubleshooting guides."

  tool_resources:
    Analyst:
      semantic_view: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      execution_environment:
        type: "warehouse"
        warehouse: "{{WAREHOUSE}}"
    Search:
      name: "{{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE"
      max_results: "5"
  $$;

-- ────────────────────────────────────────────────────────────
-- Verify agent creation
-- ────────────────────────────────────────────────────────────

SHOW AGENTS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

DESCRIBE AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}};

-- ────────────────────────────────────────────────────────────
-- Grant access (for other users/roles)
-- ────────────────────────────────────────────────────────────

-- GRANT USAGE ON DATABASE {{DATABASE}} TO ROLE {{CONSUMER_ROLE}};
-- GRANT USAGE ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{CONSUMER_ROLE}};
-- GRANT USAGE ON AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}} TO ROLE {{CONSUMER_ROLE}};
