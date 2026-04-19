# Integrations

Route Snowflake operations from non-Claude-Code environments to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli).

> **Claude Code** users: use the [plugin](../plugins/cortex-code/) instead — it auto-routes via hooks, no CLI wrapper needed.

## Available integrations

| Environment | Install | Details |
|---|---|---|
| **Codex** | `bash integrations/codex/install.sh` | Standalone `cortexcode-tool` CLI with `approval_mode: auto` for Codex's sandbox |
| **Terminal / CI** | `bash integrations/cli-tool/setup.sh` | Same CLI, interactive approval by default |

**Prerequisite**: Cortex Code CLI installed and configured.

```bash
which cortex                # must return a path
cortex connections list     # must show an active connection
```

## How it works

```
User / Agent
     ↓
cortexcode-tool "your question"
     ↓
[Route → Cortex Code CLI → Snowflake]
     ↓
Result returned to caller
```

## Security

- **Approval modes**: `prompt` (default), `auto` (Codex/CI), `envelope_only` (trusted)
- **Security envelopes**: `RO` (read-only), `RW` (read-write), `RESEARCH` (exploratory), `DEPLOY` (full access)
- **Built-in protections**: PII sanitization, credential path blocking, audit logging
