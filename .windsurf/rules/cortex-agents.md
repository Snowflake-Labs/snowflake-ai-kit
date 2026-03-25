---
name: cortex-agents
description: "Create Cortex Agents that orchestrate across structured and unstructured data using Cortex Analyst, Cortex Search, and custom tools. Use for: building AI agents, CREATE AGENT, agent orchestration, multi-tool agents, natural language Q&A over data, combining structured and unstructured search. Triggers: cortex agent, create agent, ai agent, agent orchestration, analyst and search, multi-tool agent, data agent, agent specification, agent tools."
---

# Cortex Agents

Create a Cortex Agent that orchestrates across your data — routing questions to Cortex Analyst (structured/SQL), Cortex Search (unstructured/semantic), and custom tools (UDFs/stored procedures) automatically.

## When to Use

- User wants to build an AI agent that answers questions across multiple data sources
- User mentions `CREATE AGENT`, Cortex Agents, or agent orchestration
- User wants a natural language interface over both structured and unstructured data
- User needs to combine Cortex Analyst (text-to-SQL) with Cortex Search (RAG)
- User wants to add custom tools (UDFs/stored procedures) to an agent

## Tools Used

- `snowflake_sql_execute` — Create semantic views, search services, agents, test queries
- `ask_user_question` — Confirm architecture, tool selection, instructions
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
cortex-agents/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── templates/
    ├── setup.sql                   # Create DB, schema, sample data, semantic view, search service
    ├── create-agent.sql            # CREATE AGENT with Analyst + Search + custom tools
    └── invoke-agent.sql            # Call agent via REST API and SNOWFLAKE.CORTEX.AGENT()
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects and data sources
- Step 3: User reviews agent specification before creation
- Step 5: User tests agent and reviews answers

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex Agents — What This Skill Does
>
> I'll build a Cortex Agent — an AI orchestrator that automatically routes questions
> to the right tool and synthesizes answers from your data.
>
> **How agents work:**
> ```
> User Question → Agent (LLM plans & routes)
>     → Cortex Analyst (structured data → SQL → results)
>     → Cortex Search (unstructured data → semantic search → context)
>     → Custom Tools (UDFs/stored procedures)
>     → Agent synthesizes final answer
> ```
>
> **What gets created:**
> 1. A semantic view (for structured data via Cortex Analyst)
> 2. A Cortex Search Service (for unstructured data)
> 3. A Cortex Agent object with tools and instructions
>
> **Key features:**
> - Automatic tool routing — agent decides which tool to call
> - Multi-step reasoning — splits complex questions into subtasks
> - Custom tools — add UDFs/stored procedures as tools
> - Budget controls — limit execution time and tokens
>
> **Models available:** claude-4-sonnet, claude-3-7-sonnet, openai-gpt-5, openai-gpt-4-1, llama3.1-70b
>
> Ready to proceed?

**⚠️ MANDATORY STOPPING POINT**: Wait for user approval before continuing.

---

## Step 1: Gather Targets

Ask the user:

```
Where should I create the agent?

- Database: (e.g., AGENTS_DB)
- Schema: (e.g., AGENTS)
- Agent name: (e.g., MY_BUSINESS_AGENT)
- Warehouse: (e.g., COMPUTE_WH)
- Role: (must have CREATE AGENT privilege)
- Data sources: Demo data or your own?

If your own data:
- Structured data: Which tables/views contain queryable metrics?
- Unstructured data: Which tables contain searchable text?
```

**STOP** — Wait for response.

---

## Step 2: Create Prerequisites

An agent needs tools. The two core tools are:

### Cortex Analyst (Structured Data)

Requires a **semantic view** that defines business meanings for your tables:

```sql
CREATE OR REPLACE SEMANTIC VIEW {{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW
  AS (
    -- Define tables, dimensions, measures, metrics
    -- See the cortex-search-rag skill or Snowflake docs for semantic view syntax
  );
```

If the user doesn't have a semantic view, use demo data from `templates/setup.sql` which creates one.

### Cortex Search (Unstructured Data)

Requires a **Cortex Search Service** on a text column:

```sql
CREATE OR REPLACE CORTEX SEARCH SERVICE {{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE
    ON body
    ATTRIBUTES title, category
    WAREHOUSE = {{WAREHOUSE}}
    TARGET_LAG = '1 hour'
    EMBEDDING_MODEL = 'snowflake-arctic-embed-l-v2.0'
    AS (SELECT id, title, category, body FROM DOCUMENTS);
```

Read `templates/setup.sql` and substitute placeholders. Execute to create the demo data, semantic view, and search service.

---

## Step 3: Create the Agent

Read `templates/create-agent.sql` and substitute placeholders.

The core command:

```sql
CREATE OR REPLACE AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}
  COMMENT = '{{AGENT_DESCRIPTION}}'
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
    system: "You are a helpful business assistant."
    orchestration: "Use Analyst for metrics and numbers. Use Search for policies and documentation."
    response: "Be concise and cite your sources."
    sample_questions:
      - question: "What was total revenue last quarter?"
      - question: "What is our return policy for electronics?"

  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "Analyst"
        description: "Queries structured business data by converting questions to SQL"
    - tool_spec:
        type: "cortex_search"
        name: "Search"
        description: "Searches company documentation and policies"

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
```

**STOP** — Show the spec to the user. Ask: "Agent spec looks good? Ready to create?"

---

## Step 4: Verify Agent

```sql
-- List agents
SHOW AGENTS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Describe the agent
DESCRIBE AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}};
```

---

## Step 5: Invoke the Agent

Read `templates/invoke-agent.sql` for examples.

### Via REST API (recommended for apps)

```bash
curl -X POST "https://{{ACCOUNT_URL}}/api/v2/cortex/agent:run" \
  --header "Authorization: Bearer $PAT" \
  --header "Content-Type: application/json" \
  --data '{
    "agent_name": "{{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}",
    "messages": [
      {
        "role": "user",
        "content": [{"type": "text", "text": "What was total revenue last quarter?"}]
      }
    ],
    "stream": false
  }'
```

### Via SQL

```sql
SELECT SNOWFLAKE.CORTEX.AGENT(
    '{{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}',
    OBJECT_CONSTRUCT(
        'messages', ARRAY_CONSTRUCT(
            OBJECT_CONSTRUCT(
                'role', 'user',
                'content', ARRAY_CONSTRUCT(
                    OBJECT_CONSTRUCT('type', 'text', 'text', 'What was total revenue last quarter?')
                )
            )
        )
    )
) AS response;
```

**STOP** — Show results. Ask the user to try different questions to test routing.

---

## Step 6: Add Custom Tools (Optional)

Add UDFs or stored procedures as agent tools:

```sql
-- Create a UDF
CREATE OR REPLACE FUNCTION {{DATABASE}}.{{SCHEMA}}.GET_WEATHER(city VARCHAR)
  RETURNS VARCHAR
  LANGUAGE PYTHON
  RUNTIME_VERSION = '3.8'
  HANDLER = 'get_weather'
  AS $$
def get_weather(city):
    return f"Weather for {city}: 72°F, sunny"
$$;

-- Add to agent via ALTER
ALTER AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}}
  MODIFY LIVE VERSION SET SPECIFICATION =
  $$
  -- ... (existing spec plus new tool)
  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "Analyst"
        description: "Queries structured business data"
    - tool_spec:
        type: "cortex_search"
        name: "Search"
        description: "Searches documentation"
    - tool_spec:
        type: "generic"
        name: "get_weather"
        description: "Gets current weather for a city"
        input_schema:
          type: "object"
          properties:
            city:
              type: "string"
              description: "City name"
          required: ["city"]
  tool_resources:
    Analyst:
      semantic_view: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      execution_environment:
        type: "warehouse"
        warehouse: "{{WAREHOUSE}}"
    Search:
      name: "{{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE"
      max_results: "5"
    get_weather:
      type: "function"
      execution_environment:
        type: "warehouse"
        warehouse: "{{WAREHOUSE}}"
      identifier: "{{DATABASE}}.{{SCHEMA}}.GET_WEATHER"
  $$;
```

---

## Tool Types Reference

| Type | Purpose | Resource Config |
|------|---------|----------------|
| `cortex_analyst_text_to_sql` | Text-to-SQL over semantic views | `semantic_view`, `execution_environment` |
| `cortex_search` | Semantic search over text | `name` (search service), `max_results`, `filter` |
| `data_to_chart` | Generate visualizations from data | (no resource config needed) |
| `web_search` | Search the web | `Function` (UDF identifier) |
| `generic` | Custom UDF or stored procedure | `type` (function/procedure), `identifier`, `execution_environment` |

## Model Choices

| Model | Best For |
|-------|----------|
| `auto` | Let Snowflake pick the best available (recommended) |
| `claude-4-sonnet` | Strong reasoning, good tool routing |
| `claude-3-7-sonnet` | Balanced performance |
| `openai-gpt-5` | Alternative strong reasoning |
| `openai-gpt-4-1` | Cost-effective |

## Access Control

```sql
-- Grant agent creation
GRANT CREATE AGENT ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{ROLE}};

-- Grant agent usage (for other users)
GRANT USAGE ON DATABASE {{DATABASE}} TO ROLE {{CONSUMER_ROLE}};
GRANT USAGE ON SCHEMA {{DATABASE}}.{{SCHEMA}} TO ROLE {{CONSUMER_ROLE}};
GRANT USAGE ON AGENT {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}} TO ROLE {{CONSUMER_ROLE}};

-- Required database role
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_USER TO ROLE {{ROLE}};
```

## Output

- A Cortex Agent object that routes natural language questions to the appropriate tool (Analyst, Search, or custom UDFs)
- Supporting prerequisites: a semantic view for structured data and a Cortex Search Service for unstructured data
- Tested agent responses demonstrating multi-tool orchestration across the user's data sources

## Agent Lifecycle

```sql
-- Update agent spec
ALTER AGENT {{AGENT_NAME}} MODIFY LIVE VERSION SET SPECIFICATION = $$ ... $$;

-- Drop agent
DROP AGENT IF EXISTS {{DATABASE}}.{{SCHEMA}}.{{AGENT_NAME}};

-- Monitor agent
-- Use Snowsight > AI & ML > Agents for traces and logs
```
