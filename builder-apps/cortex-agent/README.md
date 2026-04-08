# Cortex Agent App

A chat UI for [Snowflake Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents). Users ask questions in natural language, and the agent uses Cortex Analyst (text-to-SQL), Cortex Search (RAG), and custom tools to answer them.

- **No external API key** — runs entirely on Snowflake compute with models like `claude-4-sonnet` and `llama3.3-70b`.
- **Thread-based conversations** — each conversation gets its own Cortex thread for multi-turn context.
- **Agent selector** — pick from any Cortex Agent in your account.
- **SSE streaming** — responses stream in real-time via Server-Sent Events.
- **Sample data included** — `setup.sql` creates a demo agent with sales data, a semantic view, and a Cortex Search service.

## Architecture

```
┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────┐
│  React Frontend      │ SSE  │  FastAPI Backend      │ REST │  Snowflake   │
│  (Vite + TypeScript) │◄────►│  (proxy)              │◄────►│  Cortex      │
│                      │      │                       │      │  Agents API  │
│  - Agent selector    │      │  - /api/agents        │      │              │
│  - Chat UI           │      │  - /api/chat (SSE)    │      │  - Analyst   │
│  - SQL display       │      │  - /api/conversations │      │  - Search    │
│  - Chart display     │      │  - Thread management  │      │  - Charts    │
└──────────────────────┘      └──────────────────────┘      └──────────────┘
```

## Project Structure

```
builder-apps/cortex-agent/
├── client/                          # React frontend
│   ├── src/
│   │   ├── App.tsx                  # Main app layout
│   │   ├── components/
│   │   │   ├── AgentSelector.tsx    # Agent picker dropdown
│   │   │   ├── ChatInput.tsx        # Message input
│   │   │   ├── ChatMessage.tsx      # Message display (text, SQL, charts)
│   │   │   └── ConversationList.tsx # Conversation sidebar
│   │   ├── hooks/useSSEStream.ts    # SSE stream consumer
│   │   ├── services/api.ts          # API client
│   │   └── types/agent.ts           # TypeScript types
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── server/
│   ├── main.py                      # FastAPI endpoints
│   ├── cortex_agent.py              # Cortex Agents REST API client
│   ├── config.py                    # Snowflake connection config
│   └── models.py                    # Pydantic models
├── scripts/
│   ├── setup.sh                     # Install dependencies
│   └── dev.sh                       # Start dev servers
├── setup.sql                        # Sample data + agent creation
├── requirements.txt
├── .env.example
└── README.md
```

## Quick Start

### 1. Create a Cortex Agent in Snowflake

Run `setup.sql` in a Snowflake worksheet. This creates:
- `CORTEX_AGENT_DEMO.DATA.SALES` — sample sales data
- `CORTEX_AGENT_DEMO.DATA.PRODUCT_DOCS` — sample product documentation
- `CORTEX_AGENT_DEMO.DATA.SALES_SEMANTIC_VIEW` — semantic view for Cortex Analyst
- `CORTEX_AGENT_DEMO.DATA.PRODUCT_DOCS_SEARCH` — Cortex Search service
- `CORTEX_AGENT_DEMO.DATA.SALES_AGENT` — Cortex Agent wired to all of the above

### 2. Configure credentials

```bash
cd builder-apps/cortex-agent
cp .env.example .env.local
```

Edit `.env.local` with your Snowflake credentials. You need:
- A [Programmatic Access Token (PAT)](https://docs.snowflake.com/en/user-guide/programmatic-access-tokens)
- `SNOWFLAKE_HOST`, `SNOWFLAKE_USER`, `SNOWFLAKE_PAT`

Or set `SNOWFLAKE_CONNECTION_NAME` to use a connection from `~/.snowflake/connections.toml`.

The app discovers all agents your role can access via `SHOW AGENTS IN ACCOUNT` — no database or schema configuration needed.

### 3. Install and run

```bash
./scripts/setup.sh
./scripts/dev.sh
```

Open http://localhost:5174. Select your agent from the dropdown and start chatting.

## How It Works

### Cortex Agents REST API

The backend proxies to the [Cortex Agents REST API](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-rest-api):

```
POST /api/v2/databases/{db}/schemas/{schema}/agents/{name}:run
```

The response is an SSE stream with these event types:

| Event | Description |
|---|---|
| `message.delta` | Incremental content (text, tool use, tool results) |
| `response.text` | Final aggregated text |
| `response.chart` | Vega-Lite chart specification |
| `metadata` | Message ID for thread continuity |
| `response` | Final event marker |

### Threads

Each conversation maps to a [Cortex thread](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-threads). The backend tracks thread IDs and parent message IDs automatically so each follow-up message has full context.

### Bring Your Own Agent

This app works with any Cortex Agent. The sample `setup.sql` is just a starting point. To use your own agent:

1. [Create an agent](https://docs.snowflake.com/en/sql-reference/sql/create-agent) in any database/schema
2. The app runs `SHOW AGENTS IN ACCOUNT` on startup and populates the dropdown with every agent your role can see


