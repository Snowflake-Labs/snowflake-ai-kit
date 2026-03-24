-- ============================================================
-- Cortex Agents — Invoke Agent
-- Call the agent via SQL and REST API patterns
-- ============================================================

USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Method 1: REST API (recommended for applications)
--
-- Use this from Streamlit, Python apps, or any HTTP client.
-- Supports streaming (SSE) for real-time responses.
-- ────────────────────────────────────────────────────────────

-- REST API call (run from curl, Python requests, etc.):
--
-- curl -X POST "https://{{ACCOUNT_URL}}/api/v2/cortex/agent:run" \
--   --header "Authorization: Bearer $PAT" \
--   --header "Content-Type: application/json" \
--   --data '{
--     "agent_name": "{{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}",
--     "messages": [
--       {
--         "role": "user",
--         "content": [{"type": "text", "text": "What was total revenue last quarter?"}]
--       }
--     ],
--     "stream": true
--   }'

-- ────────────────────────────────────────────────────────────
-- Method 2: Python (Streamlit app pattern)
-- ────────────────────────────────────────────────────────────

-- import requests
-- import sseclient
-- import json
--
-- def call_agent(question, account_url, token, agent_fqn):
--     payload = {
--         "agent_name": agent_fqn,
--         "messages": [{
--             "role": "user",
--             "content": [{"type": "text", "text": question}]
--         }],
--         "stream": True
--     }
--     resp = requests.post(
--         f"https://{account_url}/api/v2/cortex/agent:run",
--         json=payload,
--         headers={
--             "Authorization": f'Snowflake Token="{token}"',
--             "Content-Type": "application/json"
--         }
--     )
--     client = sseclient.SSEClient(resp)
--     for event in client.events():
--         parsed = json.loads(event.data)
--         delta = parsed.get("delta", {}).get("content", {})
--         if delta.get("type") == "text":
--             yield delta["text"]
--         elif delta.get("type") == "tool_use":
--             results = delta.get("tool_results", {}).get("content", {}).get("json", {})
--             yield results.get("text", "")
--             if results.get("sql"):
--                 yield f"\n\n```sql\n{results['sql']}\n```"

-- ────────────────────────────────────────────────────────────
-- Test questions for the demo agent
-- ────────────────────────────────────────────────────────────

-- Structured (should route to Analyst):
-- "What was total revenue last quarter?"
-- "Which region had the highest sales?"
-- "What are the top 3 products by quantity sold?"
-- "Show me monthly revenue trends"
-- "What's the average order value for Enterprise customers?"

-- Unstructured (should route to Search):
-- "What is the return policy for electronics?"
-- "How do I set up the wireless mouse?"
-- "What does the laptop warranty cover?"
-- "What are the shipping options and costs?"
-- "Tell me about enterprise volume pricing"

-- Mixed (agent should use both tools):
-- "What are our best-selling products and what warranty do they come with?"
-- "Which region generates the most revenue and what's the return policy there?"

-- ────────────────────────────────────────────────────────────
-- Agent management
-- ────────────────────────────────────────────────────────────

-- Update agent specification
-- ALTER AGENT {{AGENT_NAME}} MODIFY LIVE VERSION SET SPECIFICATION = $$ ... $$;

-- Drop agent
-- DROP AGENT IF EXISTS {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}};

-- Monitor in Snowsight: AI & ML > Agents > select agent > Traces
