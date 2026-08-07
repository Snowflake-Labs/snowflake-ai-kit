# Cloud Agents MCP — Testing Guide

## What This Is

An MCP server that routes Snowflake prompts in Claude Code to a remote **CoCo Cloud Agent**. Instead of executing locally via Cortex CLI, your queries run in a cloud sandbox with full tool access.

## Prerequisites

- **Node.js 20+** — `node --version`
- **Python 3.10+** with `snowflake-connector-python` — `pip3 install snowflake-connector-python`
- **Claude Code** — `claude --version`
- **Snowflake account with Cloud Agents API access**

## Getting Started

```bash
git clone -b feature/cloud-agents-mcp https://github.com/Snowflake-Labs/snowflake-ai-kit.git
cd snowflake-ai-kit/mcp-servers/cloud-agents
./test-setup.sh
```

If you already cloned, pull latest changes first:
```bash
cd snowflake-ai-kit
git pull
cd mcp-servers/cloud-agents
./test-setup.sh
```

The script will ask for your Snowflake account and username, then open your browser for SSO. Approve it. Then open a **new terminal** from the repo directory:

```bash
cd snowflake-ai-kit
claude
```

Ask any Snowflake question:
- "Show me my snowflake databases"
- "Which warehouses do I have access to?"
- "Create a table called test_cloud_agent"

Approve the MCP tool permission once when prompted.

## Teardown

```bash
cd path/to/snowflake-ai-kit/mcp-servers/cloud-agents
./test-setup.sh --teardown
```

Restores your original Claude Code configuration.

---

## How It Works

1. A `UserPromptSubmit` hook detects Snowflake keywords in your prompt
2. If the `cloud-agents` MCP server is configured, the hook injects a routing instruction
3. Claude calls `cloud_agent_spawn` (starts a remote Cloud Agent)
4. Claude calls `cloud_agent_wait` (blocks until the agent finishes)
5. The agent's output is presented to you

The Cloud Agent runs in a sandboxed environment with access to bash, file tools, and your Snowflake account.

## What `test-setup.sh` Does

- Checks prerequisites (Node 20+, Python, Claude Code, snowflake-connector)
- Runs 23 unit tests (offline, no network)
- Starts a background token provider (keeps the Snowflake session alive)
- Adds `cloud-agents` MCP server to `~/.claude.json`
- Installs a user-level hook in `~/.claude/hooks.json` (auto-routes Snowflake prompts)
- Disables the marketplace Cortex Code plugin if installed (avoids duplicate routing)
- Verifies the MCP server responds

## What `test-setup.sh --teardown` Does

- Stops the token provider
- Removes `cloud-agents` from `~/.claude.json`
- Removes the user-level hook from `~/.claude/hooks.json`
- Re-enables the marketplace plugin if it was installed

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLOUD_AGENTS_HOST` | — | Snowflake account URL |
| `CLOUD_AGENTS_ACCOUNT` | — | Snowflake account identifier |
| `CLOUD_AGENTS_CONNECTION` | (auto) | Cortex CLI connection name |
| `CLOUD_AGENTS_AUTH_MODE` | `auto` | Auth mode: auto, coco, env, pat |
| `CLOUD_AGENTS_SESSION_TOKEN` | — | Explicit session token |
| `SNOWFLAKE_PAT` | — | Programmatic Access Token |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Token expired mid-session | Restart provider: `python3 token_provider.py &` |
| Routes to local Cortex CLI | Run `./test-setup.sh` again |
| `cloud_agent_spawn` not available | Check `~/.claude.json` has `cloud-agents` entry |
| Permission prompt every time | Approve once — it persists for the session |
| Slow first response | Expected: ~10-20s (agent sandbox boot + execution) |

If you run into any issues, reach out to Dash.
