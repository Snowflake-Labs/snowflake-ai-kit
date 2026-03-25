---
name: cortex-mcp-server
description: "Create Snowflake-managed MCP servers to expose Cortex tools (Analyst, Search, Agents, SQL, UDFs) to any MCP client. Use for: MCP server, model context protocol, expose Snowflake tools, connect AI agents to Snowflake, MCP integration, tool serving. Triggers: mcp server, model context protocol, create mcp server, expose tools, mcp client, mcp integration, tool serving, snowflake mcp, connect agent to snowflake."
---

# Cortex MCP Server

Create a Snowflake-managed MCP (Model Context Protocol) server that exposes your Snowflake tools — Cortex Analyst, Cortex Search, Cortex Agents, SQL execution, and custom UDFs — to any MCP-compatible AI client.

## When to Use

- User wants to expose Snowflake tools to external AI agents via MCP
- User mentions MCP, Model Context Protocol, or tool serving
- User wants to connect AI clients (Claude, Cursor, etc.) to Snowflake data
- User needs a standardized interface for AI tool discovery and invocation
- User asks about `CREATE MCP SERVER`

## Tools Used

- `snowflake_sql_execute` — Create MCP server, UDFs, verify
- `ask_user_question` — Confirm tools to expose, authentication method
- `read` / `write` / `edit` — Configure SQL templates with user-specific values

## Bundled Files

```
cortex-mcp-server/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── templates/
    ├── setup.sql                   # Prerequisites: search service, semantic view, UDFs
    ├── create-mcp-server.sql       # CREATE MCP SERVER with various tool types
    └── connect-client.sql          # Client connection, auth setup, RBAC
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms which tools to expose
- Step 3: User reviews MCP server specification before creation
- Step 5: User configures client connection

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex MCP Server — What This Skill Does
>
> I'll create a Snowflake-managed MCP server — a standardized endpoint that lets
> any MCP-compatible AI agent discover and invoke your Snowflake tools.
>
> **What MCP enables:**
> ```
> External AI Client (Claude, Cursor, etc.)
>     → MCP Protocol (tool discovery + invocation)
>     → Snowflake MCP Server
>         → Cortex Analyst (text-to-SQL)
>         → Cortex Search (semantic search)
>         → Cortex Agent (multi-tool orchestration)
>         → SQL Execution
>         → Custom Tools (UDFs/stored procedures)
> ```
>
> **What gets created:**
> 1. An MCP SERVER object in Snowflake
> 2. Tool configurations for each exposed capability
> 3. Authentication setup (OAuth recommended)
> 4. RBAC grants for tool-level access control
>
> **Key features:**
> - Standardized MCP protocol (revision 2025-06-18)
> - Built-in OAuth authentication
> - Role-based access control per tool
> - No external infrastructure needed
>
> Ready to proceed?

**STOP** — Wait for user approval before continuing.

---

## Step 1: Choose Tools to Expose

Ask the user:

```
Which tools should the MCP server expose?

1. Cortex Analyst — Natural language to SQL via semantic views
2. Cortex Search — Semantic search over documents
3. Cortex Agent — Multi-tool AI agent
4. SQL Execution — Direct SQL queries
5. Custom Tools — Your UDFs or stored procedures

Which combination? (e.g., 1, 2, and 4)

Also:
- Database: (e.g., MCP_DB)
- Schema: (e.g., TOOLS)
- MCP Server name: (e.g., MY_MCP_SERVER)
```

**STOP** — Wait for response.

---

## Step 2: Create Prerequisites

Depending on which tools the user selected, ensure prerequisites exist:

**Cortex Analyst** → Requires a semantic view:
```sql
-- User must have an existing semantic view, or create one
-- See the cortex-agents skill for semantic view creation
```

**Cortex Search** → Requires a Cortex Search Service:
```sql
-- User must have an existing search service, or create one
-- See the cortex-search-rag skill for search service creation
```

**Cortex Agent** → Requires an existing agent:
```sql
-- User must have an existing agent
-- See the cortex-agents skill for agent creation
```

**Custom Tools** → Create UDFs or stored procedures:

Read `templates/setup.sql` for example UDF creation patterns.

---

## Step 3: Create MCP Server

Read `templates/create-mcp-server.sql` and substitute placeholders.

The core command:

```sql
CREATE OR REPLACE MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}}
  FROM SPECIFICATION
  $$
  tools:
    - name: "revenue-analyst"
      type: "CORTEX_ANALYST_MESSAGE"
      identifier: "{{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW"
      description: "Query revenue and sales metrics using natural language"
      title: "Revenue Analyst"

    - name: "doc-search"
      type: "CORTEX_SEARCH_SERVICE_QUERY"
      identifier: "{{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE"
      description: "Search product documentation and company policies"
      title: "Document Search"

    - name: "sql-exec"
      type: "SYSTEM_EXECUTE_SQL"
      title: "SQL Execution"
      name: "sql_exec"
      description: "Execute SQL queries against Snowflake"

    - name: "business-agent"
      type: "CORTEX_AGENT_RUN"
      identifier: "{{DATABASE}}.{{SCHEMA}}.MY_AGENT"
      description: "AI agent that routes questions to appropriate data sources"
      title: "Business Agent"
  $$;
```

**STOP** — Show spec to user. Ask: "MCP server spec looks good?"

---

## Step 4: Configure Access Control

MCP server access is separate from tool access — both must be granted:

```sql
-- Grant access to the MCP server itself
GRANT USAGE ON MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}}
    TO ROLE {{CONSUMER_ROLE}};

-- Grant access to individual tools (users can only discover/invoke granted tools)
-- For Analyst tool:
GRANT USAGE ON SEMANTIC VIEW {{DATABASE}}.{{SCHEMA}}.SALES_SEMANTIC_VIEW
    TO ROLE {{CONSUMER_ROLE}};

-- For Search tool:
GRANT USAGE ON CORTEX SEARCH SERVICE {{DATABASE}}.{{SCHEMA}}.DOC_SEARCH_SERVICE
    TO ROLE {{CONSUMER_ROLE}};

-- For Agent tool:
GRANT USAGE ON AGENT {{DATABASE}}.{{SCHEMA}}.MY_AGENT
    TO ROLE {{CONSUMER_ROLE}};
```

---

## Step 5: Connect a Client

Read `templates/connect-client.sql` for connection patterns.

### MCP Client Connection URL

The MCP server endpoint follows this pattern:
```
https://<account_identifier>.snowflakecomputing.com/api/v2/databases/<db>/schemas/<schema>/mcp-servers/<server_name>/sse
```

### Authentication Options

**OAuth (recommended):**
```sql
-- Create a security integration for OAuth
CREATE OR REPLACE SECURITY INTEGRATION mcp_oauth_integration
    TYPE = OAUTH
    OAUTH_CLIENT = CUSTOM
    OAUTH_CLIENT_TYPE = 'CONFIDENTIAL'
    OAUTH_REDIRECT_URI = 'http://localhost:8080/callback'
    ENABLED = TRUE;
```

**Programmatic Access Token (PAT):**
Use the least-privileged role when creating the PAT.

### Example: Connect from Cortex Code

```bash
cortex mcp add my-snowflake-tools \
    https://<account>.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse \
    --transport http
```

### Example: Connect from Claude Desktop

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "snowflake": {
      "url": "https://<account>.snowflakecomputing.com/api/v2/databases/{{DATABASE}}/schemas/{{SCHEMA}}/mcp-servers/{{MCP_SERVER_NAME}}/sse",
      "transport": "sse"
    }
  }
}
```

**STOP** — Help user connect their MCP client and test tool discovery.

---

## Tool Types Reference

| Type | Purpose | Requires |
|------|---------|----------|
| `CORTEX_ANALYST_MESSAGE` | Text-to-SQL via semantic view | Semantic view |
| `CORTEX_SEARCH_SERVICE_QUERY` | Semantic search | Cortex Search Service |
| `CORTEX_AGENT_RUN` | Multi-tool agent | Cortex Agent |
| `SYSTEM_EXECUTE_SQL` | Direct SQL execution | Warehouse |
| `GENERIC` | Custom UDF or stored procedure | UDF/SP + config |

### Custom Tool Configuration

For UDFs:
```yaml
tools:
  - name: "multiply"
    type: "GENERIC"
    title: "Multiply Tool"
    description: "Multiplies a number by ten"
    config:
      type: "function"
      warehouse: "{{WAREHOUSE}}"
      input_schema:
        type: "object"
        properties:
          x:
            type: "number"
            description: "Number to multiply"
        required: ["x"]
```

For stored procedures:
```yaml
tools:
  - name: "run_report"
    type: "GENERIC"
    title: "Report Runner"
    description: "Generates a sales report"
    config:
      type: "procedure"
      warehouse: "{{WAREHOUSE}}"
      input_schema:
        type: "object"
        properties:
          region:
            type: "string"
            description: "Region to report on"
        required: ["region"]
```

## Security Recommendations

- Use **OAuth** instead of hardcoded tokens for authentication
- Use **least-privilege roles** for PATs
- Use **hyphens** (not underscores) in hostnames for MCP connections
- **Verify third-party MCP servers** before using them
- Grant tool access **individually** — MCP server access alone doesn't grant tool access

## MCP Server Management

```sql
-- List MCP servers
SHOW MCP SERVERS IN SCHEMA {{DATABASE}}.{{SCHEMA}};

-- Describe server
DESCRIBE MCP SERVER {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}};

-- Drop server
DROP MCP SERVER IF EXISTS {{DATABASE}}.{{SCHEMA}}.{{MCP_SERVER_NAME}};
```
