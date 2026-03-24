# Cortex MCP Server

Create Snowflake-managed MCP (Model Context Protocol) servers to expose Cortex tools to any MCP-compatible AI client.

## What It Does

This skill guides your AI coding agent through creating an MCP server on Snowflake:

1. **Choose Tools** — Select which capabilities to expose (Analyst, Search, Agents, SQL, custom)
2. **Create Server** — Define the MCP server with `CREATE MCP SERVER`
3. **Configure Access** — Set up RBAC and authentication
4. **Connect Client** — Wire up MCP clients (Cortex Code, Claude, Cursor, etc.)

## Prerequisites

- Snowflake account with MCP server support
- Existing tools to expose (semantic views, search services, agents, UDFs)
- MCP-compatible client for testing

## Quick Start

Ask your AI coding agent:

> "Create an MCP server that exposes my Cortex Analyst and Search tools"

Or for a demo:

> "Set up a demo MCP server with Analyst, Search, and SQL tools"

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Create prerequisite UDFs and demo tools |
| `templates/create-mcp-server.sql` | CREATE MCP SERVER with tool configurations |
| `templates/connect-client.sql` | Client connection, OAuth setup, RBAC grants |
