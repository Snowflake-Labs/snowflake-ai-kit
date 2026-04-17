# Integrations

Route Snowflake operations from any coding agent to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) — with smart routing, security envelopes, and headless execution.

## Quick Install

| Agent | Install method | Details |
|---|---|---|
| **Claude Code** | `bash install.sh --with-claude` | Skill-based routing via `~/.claude/skills/cortex-code/` |
| **Cursor** | `bash install.sh --with-cursor` | Skill + `.mdc` auto-routing rule |
| **Windsurf** | `bash install.sh --with-claude` | Uses same skill path; Cascade auto-discovers it |
| **Codex** | `bash install.sh --with-codex` | CLI-based (`cortexcode-tool`); no skill dir — runs headless |
| **VSCode / terminal** | `bash integrations/cli-tool/setup.sh` | Standalone `cortexcode-tool` CLI |
| **All agents** | `bash install.sh --with-all` | Installs everything above |

**Prerequisite**: Cortex Code CLI installed and configured.

```bash
which cortex                # must return a path
cortex connections list     # must show an active connection
```

## How it works

```
User Request
     ↓
[Your Coding Agent — Routing Layer]
     ↓
  Is Snowflake-related?
     ↓                ↓
    YES               NO
     ↓                ↓
[Cortex Code CLI]   [Your Coding Agent]
     ↓                ↓
Snowflake Execution  General Tasks
```

**Routing Principle**: ONLY Snowflake operations go to Cortex Code. Everything else stays with your coding agent.

## Integration details

- [**Cursor**](cursor/) — Skill + `.mdc` routing rule for automatic Snowflake detection
- [**Codex**](codex/) — `cortexcode-tool` CLI for sandbox-safe headless execution
- [**CLI tool**](cli-tool/) — Standalone `cortexcode-tool` for VSCode, Windsurf, terminal, and any environment

Claude Code uses the [router skill](../agent-to-agent-skills/claude-cortex-code-router/) (auto-routing) or the [plugin](../plugins/cortex-code/) (slash commands). See the [root README](../README.md) for details.

## Security

All integrations share the same security model:

- **Approval modes**: `prompt` (default, interactive), `auto` (CI/CD), `envelope_only` (trusted)
- **Security envelopes**: `RO` (read-only), `RW` (read-write), `RESEARCH` (exploratory), `DEPLOY` (full access)
- **Built-in protections**: PII sanitization, credential path blocking, audit logging
