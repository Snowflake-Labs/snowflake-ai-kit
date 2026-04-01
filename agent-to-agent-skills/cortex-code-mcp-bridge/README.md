# Cortex Code MCP Bridge

Give any MCP-compatible AI agent direct access to Snowflake tools by running [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) as a local MCP server.

## What It Does

This skill configures your AI agent (Cursor, VS Code Copilot, Claude Desktop, Windsurf, or another Cortex Code instance) to connect to Snowflake through Cortex Code's built-in MCP server mode (`cortex mcp serve`). Once connected, your agent gets native access to Snowflake tools — no prompt delegation, no security envelopes, just direct tool calls over MCP.

```
Your AI Agent (Cursor, VS Code, Claude Desktop, Windsurf)
    → MCP Protocol (stdio)
    → Cortex Code CLI (cortex mcp serve)
    → Snowflake (SQL, Analyst, Search, data_diff, etc.)
```

### How is this different from `cortex-mcp-server`?

| | This skill (`cortex-code-mcp-bridge`) | `cortex-mcp-server` skill |
|---|---|---|
| **What runs** | Cortex Code CLI on your machine | A Snowflake-managed MCP server object |
| **How it's created** | Config file + `cortex mcp serve` | `CREATE MCP SERVER` SQL |
| **Where it runs** | Local (stdio) | Snowflake cloud (SSE/HTTP) |
| **Auth** | Your local Cortex Code connection | OAuth or PAT |
| **Best for** | Developer workstations, local agents | Shared team access, production clients |

## Prerequisites

- [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) v1.0.42+ installed and in PATH
- A configured Snowflake connection (`cortex connections create`)
- Python 3.8+ (validation script uses stdlib only — no pip install needed)

Verify your setup:
```bash
cortex --version        # Should show v1.0.42+
cortex connections list # Should show at least one connection
```

## Quick Start

### Cursor

Add to `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "cortex-code": {
      "command": "cortex",
      "args": ["mcp", "serve", "--connection", "MY_CONNECTION"]
    }
  }
}
```

### VS Code Copilot

Add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "cortex-code": {
      "type": "stdio",
      "command": "cortex",
      "args": ["mcp", "serve", "--connection", "MY_CONNECTION"]
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "cortex-code": {
      "command": "cortex",
      "args": ["mcp", "serve", "--connection", "MY_CONNECTION"]
    }
  }
}
```

### Windsurf

Add to `.windsurf/mcp.json` (project) or `~/.windsurf/mcp.json` (global):

```json
{
  "mcpServers": {
    "cortex-code": {
      "command": "cortex",
      "args": ["mcp", "serve", "--connection", "MY_CONNECTION"]
    }
  }
}
```

### Cortex Code

```bash
cortex mcp add cortex-code-bridge cortex -- mcp serve --connection MY_CONNECTION
```

Replace `MY_CONNECTION` with your Snowflake connection name from `cortex connections list`.

## Validation

Test that the bridge works before restarting your editor:

```bash
python3 scripts/validate_bridge.py --connection MY_CONNECTION
```

This spawns `cortex mcp serve`, performs the MCP handshake, and lists all available tools. Expected output:

```
Starting MCP server: cortex mcp serve --connection MY_CONNECTION
Sending initialize request...
Connected to: cortex-code v1.x.x
Requesting tool list...

Available tools (N):
------------------------------------------------------------
  snowflake_sql_execute          Run SQL queries on Snowflake
  data_diff                      Compare two Snowflake tables
  ...
------------------------------------------------------------

Bridge validated successfully — N tools available.
```

## Usage with AI Agent

After installing the config, restart your editor/agent and try:

- "Run `SELECT CURRENT_TIMESTAMP()` on Snowflake"
- "Show me the tables in MY_DB.PUBLIC"
- "Compare TABLE_V1 and TABLE_V2"

## Security

- **Default (no `--bypass`):** Some tool calls may require approval. Safest option.
- **With `--bypass`:** Add `"--bypass"` to the args array to auto-approve all tool calls. Only use in trusted environments.
- **No credentials in config:** The config only references the `cortex` command and a connection name. Snowflake credentials are managed by Cortex Code's connection manager, not stored in MCP config files.

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `scripts/validate_bridge.py` | Test MCP connection end-to-end |
| `templates/cursor-mcp.json` | Cursor config template |
| `templates/vscode-mcp.json` | VS Code Copilot config template |
| `templates/claude-desktop-config.json` | Claude Desktop config template |
| `templates/windsurf-mcp.json` | Windsurf config template |
| `templates/cortex-mcp-add.sh` | Cortex Code one-liner |
