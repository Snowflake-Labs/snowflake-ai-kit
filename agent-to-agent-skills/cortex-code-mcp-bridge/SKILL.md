---
name: cortex-code-mcp-bridge
description: "Connect any MCP-compatible AI agent to Snowflake via Cortex Code's built-in MCP server. Use for: MCP bridge, connect agent to Snowflake, Cortex Code as MCP server, Snowflake tools for Cursor, Snowflake tools for Claude, Snowflake tools for Windsurf, agent-to-agent Snowflake. Triggers: mcp bridge, cortex mcp serve, connect to snowflake, snowflake mcp tools, add snowflake to cursor, add snowflake to claude, add snowflake to windsurf, cortex code mcp."
---

# Cortex Code MCP Bridge

Connect any MCP-compatible AI agent (Cursor, VS Code Copilot, Claude Desktop, Windsurf, or another Cortex Code instance) to Snowflake by running Cortex Code CLI as a local MCP server.

## When to Use

- User wants to give their AI agent (Cursor, Claude Desktop, VS Code Copilot, Windsurf) access to Snowflake tools
- User asks about connecting an external agent to Snowflake via MCP
- User mentions `cortex mcp serve` or running Cortex Code as an MCP server
- User wants Snowflake SQL execution, data diff, Cortex Analyst, or object search in a non-Cortex agent

**Do NOT use when:**
- User wants to create a Snowflake-managed MCP server (`CREATE MCP SERVER` SQL) — use the `cortex-mcp-server` snowflake-skill instead
- User wants to delegate a full task to Cortex Code with prompt + security envelope — use `claude-cortex-code-router` instead
- User is already in Cortex Code and has native Snowflake tools

## Tools Used

- `bash` — Run validation script, install MCP config
- `ask_user_question` — Detect target client, confirm connection name
- `read` / `write` — Generate client-specific config from templates

## Bundled Files

```
cortex-code-mcp-bridge/
├── SKILL.md                              # This file (agent instructions)
├── README.md                             # Human-facing docs
├── scripts/
│   └── validate_bridge.py                # Test MCP connection end-to-end
└── templates/
    ├── cursor-mcp.json                   # Cursor config template
    ├── vscode-mcp.json                   # VS Code Copilot config template
    ├── windsurf-mcp.json                 # Windsurf config template
    ├── claude-desktop-config.json        # Claude Desktop config template
    └── cortex-mcp-add.sh                 # Cortex Code one-liner
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms which AI client to connect and which Snowflake connection to use
- Step 3: User confirms config file location before writing

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex Code MCP Bridge — What This Skill Does
>
> I'll configure your AI agent to use Snowflake tools by running Cortex Code
> as a local MCP server. This gives your agent direct access to Snowflake
> without prompt delegation or security envelopes.
>
> **How it works:**
> ```
> Your AI Agent (Cursor, VS Code, Claude Desktop, Windsurf)
>     → MCP Protocol (stdio)
>     → Cortex Code CLI (cortex mcp serve)
>     → Snowflake (SQL, Analyst, Search, data_diff, etc.)
> ```
>
> **What your agent gets:**
> - `snowflake_sql_execute` — Run SQL queries against Snowflake
> - `data_diff` — Compare two tables row-by-row
> - `cortex analyst query` — Natural language to SQL via semantic views
> - `snowflake_object_search` — Search for database objects
> - All other Cortex Code tools exposed over MCP
>
> **Requires:** Cortex Code CLI installed and a configured Snowflake connection
>
> **How it differs from `cortex-mcp-server` skill:** That skill creates a
> Snowflake-managed MCP server object (`CREATE MCP SERVER` SQL). This skill
> runs the Cortex Code CLI itself as a local MCP server on your machine.

**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.

---

## Step 1: Gather Configuration

Ask the user two things:

**1. Which AI client are you connecting?**

| Client | Config File | Format |
|--------|------------|--------|
| Cursor | `.cursor/mcp.json` (project) or `~/.cursor/mcp.json` (global) | `mcpServers` key |
| VS Code Copilot | `.vscode/mcp.json` (project) | `servers` key |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) | `mcpServers` key |
| Windsurf | `.windsurf/mcp.json` (project) or `~/.windsurf/mcp.json` (global) | `mcpServers` key |
| Cortex Code | `~/.snowflake/cortex/mcp.json` | `mcpServers` key |

**2. Which Snowflake connection should the bridge use?**

Run `cortex connections list` to show available connections. If the user doesn't specify, use the default connection.

**⚠️ MANDATORY STOPPING POINT**: Confirm both choices before proceeding.

---

## Step 2: Validate Prerequisites

Before generating config, check prerequisites:

```bash
# 1. Cortex CLI installed
cortex --version

# 2. Connection exists and works
cortex connections list
```

If either fails, stop and help the user fix the issue:
- **CLI not found:** `curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh`
- **No connections:** `cortex connections create`

---

## Step 3: Generate and Install Config

Read the appropriate template from `templates/` and substitute `{{CONNECTION_NAME}}` with the user's chosen connection.

### For Cursor

Read `templates/cursor-mcp.json`, substitute the connection name, and write to the target location:

- **Project scope:** `.cursor/mcp.json` in the project root
- **Global scope:** `~/.cursor/mcp.json`

If the file already exists, merge the `cortex-code` entry into the existing `mcpServers` object — do not overwrite other servers.

### For VS Code Copilot

Read `templates/vscode-mcp.json`, substitute, and write to `.vscode/mcp.json`.

### For Claude Desktop

Read `templates/claude-desktop-config.json`, substitute, and merge into the existing config at `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows).

### For Windsurf

Read `templates/windsurf-mcp.json`, substitute, and write to `.windsurf/mcp.json` (project) or `~/.windsurf/mcp.json` (global).

### For Cortex Code

Run the one-liner from `templates/cortex-mcp-add.sh`:

```bash
cortex mcp add cortex-code-bridge cortex -- mcp serve --connection {{CONNECTION_NAME}}
```

**⚠️ MANDATORY STOPPING POINT**: Show the generated config to the user and confirm the file path before writing.

---

## Step 4: Validate the Bridge

Run the validation script to test the MCP connection:

```bash
python3 <skill_dir>/scripts/validate_bridge.py --connection {{CONNECTION_NAME}}
```

The script:
1. Spawns `cortex mcp serve --connection <name>` as a subprocess
2. Sends a JSON-RPC `initialize` request
3. Sends a `tools/list` request
4. Prints the list of available tools
5. Exits with 0 (success) or 1 (failure)

If validation passes, tell the user:
- Restart their AI client (or reload MCP servers) to pick up the new config
- Try a test query like: "Run `SELECT CURRENT_TIMESTAMP()` on Snowflake"

If validation fails, check the Common Issues table below.

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `cortex: command not found` | Install Cortex Code CLI: `curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh \| sh` |
| `No Snowflake connection configured` | Run `cortex connections create` to set up a connection |
| MCP server starts but tools/list is empty | Check Cortex Code version: `cortex --version` (needs v1.0.42+) |
| Client shows "server disconnected" | The stdio process may have crashed — check `cortex mcp serve` runs without errors manually |
| Cursor/VS Code not detecting the server | Restart the editor. For Cursor, check Settings > Tools & MCP for the green indicator |
| `--bypass` flag needed | Some tool calls require auto-approval. Add `"--bypass"` to the args array in the config. Use cautiously — this auto-approves all tool calls |
| Permission denied on Snowflake | Verify the connection's role has access to the target databases. Run `cortex connections list` to check the active role |

## Security Considerations

- **Without `--bypass`:** Cortex Code's MCP server may prompt for tool approval on certain operations. This is the safer default.
- **With `--bypass`:** All tool calls are auto-approved. Use only in trusted environments where the calling agent is controlled.
- **Connection scoping:** Each bridge instance is scoped to one Snowflake connection. Use separate bridge configs for different environments (dev/staging/prod).
- **No credentials in config:** The MCP config only contains the `cortex` command and connection name. Snowflake credentials are stored separately in Cortex Code's connection manager.

## Output

- MCP client config file installed in the correct location for the user's AI agent
- Validated MCP connection with tool list enumerated
- The user's AI agent can now call Snowflake tools (SQL execution, data diff, Cortex Analyst, object search) natively via MCP

## References

- [Cortex Code CLI docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli)
- [Cortex Code extensibility — MCP](https://docs.snowflake.com/en/user-guide/cortex-code/extensibility)
- [MCP Protocol specification](https://modelcontextprotocol.io/)
