# Cloud Agents MCP

Standalone MCP server that exposes Snowflake CoCo Cloud Agents as non-blocking subagent-like tools. Any MCP-compatible client (Claude Code, CoCo Desktop, Codex, Cursor) can spawn remote Cloud Agents via this server.

## Quick Start

```bash
cd mcp-servers/cloud-agents

# Run unit tests (no network)
npm test

# Start the server (uses your CoCo CLI connection)
npm start

# Or target a specific connection/host
CLOUD_AGENTS_CONNECTION=my_connection npm start
CLOUD_AGENTS_HOST=https://myaccount.snowflakecomputing.com npm start
```

## MCP Client Configuration

Add to your IDE's MCP config (see `examples/` for full snippets):

```json
{
  "mcpServers": {
    "cloud-agents": {
      "type": "stdio",
      "command": "node",
      "args": ["/path/to/mcp-servers/cloud-agents/src/server.mjs"],
      "env": {
        "CLOUD_AGENTS_HOST": "https://your-account.snowflakecomputing.com"
      }
    }
  }
}
```

## Tools

| Tool | Blocking | Purpose |
|------|:--------:|---------|
| `cloud_agent_spawn` | no | Start a Cloud Agent run, get handle back |
| `cloud_agent_send_input` | no | Follow-up turn on same thread |
| `cloud_agent_output` | no | Read buffered text/tool events |
| `cloud_agent_wait` | **yes** | Block until terminal/turn_complete/next_event |
| `cloud_agent_status` | no | Status for one or more agents |
| `cloud_agent_list` | no | List local handles |
| `cloud_agent_close` | no | Close + optional cancel/delete |
| `cloud_agent_resume` | no | Reactivate closed handle or attach to thread |

## Authentication

Priority order:
1. `CLOUD_AGENTS_SESSION_TOKEN` / `SNOWFLAKE_TOKEN` env var
2. CoCo CLI connection (set `CLOUD_AGENTS_CONNECTION` to pick one)
3. PAT fallback (`PAT_SNOWHOUSE`, `CLOUD_AGENTS_PAT`, `SNOWFLAKE_PAT`)

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLOUD_AGENTS_HOST` | `https://snowhouse.snowflakecomputing.com` | Target Snowflake account |
| `CLOUD_AGENTS_CONNECTION` | CoCo default | Snowflake connection name |
| `CLOUD_AGENTS_AUTH_MODE` | `auto` | Auth mode: auto, coco, env, pat |
| `CLOUD_AGENTS_MCP_STATE_DIR` | `~/.snowflake/cloud-agents-mcp` | Local state |
| `CLOUD_AGENTS_COCO_REPO` | auto-discovered | Path to CoCo checkout |

## Smoke Test

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}' | node src/server.mjs
```

## End-to-End Test

```bash
# Spawn a cloud agent (requires valid auth)
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}\n{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cloud_agent_spawn","arguments":{"prompt":"echo hello world","workspace":{"mode":"none"}}}}\n' | node src/server.mjs
```
