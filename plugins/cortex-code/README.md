# Cortex Code plugin for Claude Code, OpenAI Codex, and Devin CLI

Route Snowflake work from Claude Code, OpenAI Codex, or Devin CLI to Cortex Code automatically. Ask about your data naturally — the plugin detects Snowflake intent and delegates to Cortex Code where 55+ built-in skills handle the work. Non-Snowflake prompts stay in your current agent.

## How It Works

**Two ways to route prompts to Cortex Code:**

### Auto-routing (default)

A lightweight keyword filter (`prompt_filter.py`) runs on every prompt as a `UserPromptSubmit` hook. When it detects Snowflake-related patterns, it tells your agent how to hand the prompt to Cortex Code:

- **Claude Code** loads the `cortex-router` skill, which runs the routing check and then Cortex Code.
- **OpenAI Codex** and **Devin CLI** get the same steps as direct commands with the plugin's script paths filled in.

Examples that auto-route:
- "Show me my Snowflake warehouses"
- "What databases do I have access to?"
- "List all tables in my current schema"

Examples that stay in your agent:
- "Read the config.json file"
- "Fix the bug in auth.py"
- "Write a Python unit test"

### Explicit invocation (`$cortex-run`)

Type `$cortex-run` followed by your prompt to force routing to Cortex Code, bypassing the keyword filter. Useful when:

- Auto-routing didn't pick up your prompt
- You want to be explicit about using Cortex Code
- Your prompt mixes Snowflake and non-Snowflake work

```
$cortex-run analyze query performance for the last 7 days
```

In Devin CLI, the command is `/snowflake-cortex-code:cortex-run`.

## Requirements

- **Cortex Code CLI** (`cortex`) installed and on your PATH, with a Snowflake connection
- **Python 3.9 or later** on your PATH as `python3` or `python` (`py -3` on Windows)
- **Bash**: on Windows, [Git Bash](https://git-scm.com/download/win), which hooks and skill commands run in

## Install

### Claude Code

```bash
claude plugin install snowflake-cortex-code@claude-plugins-official
```

To update: `claude plugin update snowflake-cortex-code`

### OpenAI Codex

```bash
codex plugin marketplace add Snowflake-Labs/snowflake-ai-kit
codex plugin add snowflake-cortex-code@snowflake-ai-kit
```

Or inside Codex, open `/plugins` and install "Snowflake Cortex Code" from the Snowflake AI Kit marketplace.

### Devin CLI

Devin CLI loads this plugin as-is, including the prompt hook. Install it from this repo:

```bash
devin plugins install Snowflake-Labs/snowflake-ai-kit#plugins/cortex-code --local
```

`--local` installs it on this machine only. Without it, Devin also adds it to your personal Devin Cloud plugins, where there is no local Cortex Code CLI to route to. To install from a clone instead: `devin plugins install --local ./plugins/cortex-code`.

Check it with `devin plugins info snowflake-cortex-code`. Skills are namespaced: use `/snowflake-cortex-code:cortex-run` for explicit invocation and `/snowflake-cortex-code:cortex-setup` to install the CLI. Routed prompts run with the same enforced security envelopes as Claude Code, and Cortex Code records the entrypoint as "Devin CLI Plugin". Devin asks for approval before running the plugin's scripts, depending on your permission mode.

On Windows, installing from a local folder fails with `os error 1314` unless Developer Mode is on (Settings → System → For developers), because Devin links the plugin into its cache.

**This plugin or `snowflake-mcp-devin`?** Both connect Devin to Snowflake:

- Use this plugin in Devin CLI when the Cortex Code CLI is installed on your machine and you want its bundled skills, local connections, and security envelopes.
- Use [`snowflake-mcp-devin`](../snowflake-mcp-devin/) in Devin Cloud, Desktop, or CLI when the Cortex Code CLI isn't installed, connecting through a Snowflake Managed MCP Server.

Use one at a time. The prompt hook can't see MCP servers that come from installed plugins, so with `snowflake-mcp-devin` installed Devin may answer with its tools instead of routing to Cortex Code. Check `devin plugins list` and remove it before using this one: it's installed as `snowflake`, so run `devin plugins remove snowflake`.

**MCP conflicts.** The prompt hook stops when a Snowflake MCP server is active for Devin, because its tools duplicate Cortex Code's and confuse auth. It checks Devin's own MCP config (`~/.config/devin/mcp_config.json`, `.devin/mcp_config.json`, `.devin/mcp_config.local.json`) and the Cursor, Windsurf, Claude Code, OpenCode, and Zed config that Devin imports. If it stops on a Snowflake server you configured for another tool, run `devin mcp list` to see where it comes from, then either disable that server or stop Devin importing from that tool in `~/.config/devin/config.json` (`%APPDATA%\devin\config.json` on Windows):

```json
{ "read_config_from": { "cursor": false } }
```

## Security Model

The router wraps Cortex execution with a security layer. Three approval modes:

| Mode | Behavior | Audit | Best For |
|------|----------|-------|----------|
| `prompt` (default) | Ask user before execution | Optional | Interactive, production |
| `auto` | Auto-approve | Required | Automated workflows |
| `envelope_only` | Auto-approve, no tool prediction | Required | Low latency, trusted envs |

**Security envelopes** control what Cortex can do:
- **RO**: Read-only — blocks Edit, Write, destructive Bash
- **RW**: Read-write — blocks destructive operations
- **RESEARCH**: Read + web access
- **DEPLOY**: Full access (use cautiously)

Built-in protections: PII sanitization, credential path blocking, SHA256-validated cache, structured audit logging.

## Configuration

Hooks and skill commands use `scripts/run_python.sh` in Bash (Git Bash on Windows).
The launcher prefers `python3` and accepts `python` only after verifying Python 3.
It preserves stdin and arguments and never retries a failed script with another interpreter.

The router config file lives at `scripts/router/config.yaml.example`. To customize:

```bash
cp plugins/cortex-code/scripts/router/config.yaml.example ~/.claude/skills/cortex-code/config.yaml
```

Edit the config to change approval mode, allowed envelopes, audit settings, and sanitization options.

YAML configuration requires **PyYAML in the interpreter selected by the launcher**.
From the repository root, install it in that environment with:

```bash
bash plugins/cortex-code/scripts/run_python.sh -m pip install PyYAML
```

If Python is externally managed, create and activate a virtual environment, install
PyYAML there, and start the host from that environment. Restart the host after
changing its PATH. Do not use `--break-system-packages`.

Without configuration files, built-in defaults work without PyYAML. If a user
config or `~/.snowflake/cortex/claude-skill-policy.yaml` exists, missing PyYAML,
unreadable files, invalid YAML, and invalid setting types **stop routing/execution**
with an error identifying the file. Empty files must be replaced with an explicit
mapping such as `{}`. Paths explicitly supplied through flags or
`CORTEX_SKILL_CONFIG` / `CORTEX_SKILL_ORG_POLICY` must exist; missing default paths
remain optional. An empty `allowed_envelopes` list permits no execution.

This validation does not implement approval-mode behavior: the live executor still
uses envelope decisions; the approval-mode wrapper remains a simulation.
The existing Codex execution path still auto-approves individual tool calls; this
change validates configuration and the selected envelope before launching it,
but does not add per-tool envelope enforcement to that path.

Skill discovery runs automatically on session start. To force a re-discovery, start a new session.

## Testing

Tests live in `tests/run-tests.sh` at the repo root. Two tiers:

```bash
# Structural + unit tests (no network, runs in CI)
bash tests/run-tests.sh

# Include integration tests (requires cortex CLI + Snowflake connection)
bash tests/run-tests.sh --integration
```

**Structural tests** (always run): file existence checks, config validation, Python syntax, and unit tests for `envelope_policy.py`, `prompt_filter.py`, and plugin hooks. `scripts/router/test_hosts.py` pins the exact routing output for Claude Code and Codex and covers Devin CLI detection, instructions, and MCP conflict scans.

CI tests macOS and Windows with and without PyYAML. Launcher/configuration regressions
are in `scripts/router/test_launcher_config.py`; they do not invoke Cortex or Snowflake.
Parsing-specific tests are skipped when PyYAML is absent; missing-dependency and
fail-closed tests still run.

**Integration tests** (`--integration` flag): spawn real Cortex CLI sessions against a live Snowflake connection. Located at `scripts/router/test_integration.py`. Verifies:

- Credential path blocking (prompts referencing `.ssh/`, `.env`, etc. are rejected pre-flight)
- End-to-end query flow (RO envelope, permission protocol, result event)
- Envelope enforcement (RO blocks DDL — via hard gate denial or LLM self-policing)
- Process cleanup (no orphaned `cortex` processes after execution)

Set `CORTEX_TEST_CONNECTION` env var to test against a specific Snowflake connection (defaults to your CLI default).

**Devin CLI end-to-end** (`--devin-e2e` flag): installs a temporary copy of this plugin into Devin CLI, sends real prompts with `devin -p`, and checks the audit log for envelope-enforced Cortex sessions. Needs the `devin` and `cortex` CLIs and a Snowflake connection. It skips if `snowflake-cortex-code` is already installed in Devin or a Snowflake MCP server is active for Devin, and removes the copy afterwards. Located at `tests/test_devin_e2e.py`.

## License

Copyright (c) Snowflake Inc. All rights reserved.

The skills in this project are licensed under the [Snowflake Skills License](../../LICENSE-SKILLS.md).
