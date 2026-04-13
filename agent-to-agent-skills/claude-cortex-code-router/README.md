# Claude Code Skill: Cortex Code Integration

Route Snowflake operations from [Claude Code](https://docs.anthropic.com/en/docs/claude-code) to [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) for specialized Snowflake expertise. Claude Code orchestrates the conversation; Cortex Code handles Snowflake work autonomously and streams results back.

> **Credit:** Based on [sfc-gh-tjia/claude_skill_cortexcode](https://github.com/sfc-gh-tjia/claude_skill_cortexcode).

## How It Works

```
User Request → Claude Code (routing) → Snowflake-related? → YES → Cortex Code CLI
                                                          → NO  → Claude Code
```

The skill discovers Cortex capabilities at session start, routes Snowflake prompts via LLM-based semantic analysis, wraps execution in a configurable security layer, and streams results back to Claude Code.

**SKILL.md** is the canonical reference — it contains the full workflow, routing logic, examples, and troubleshooting that Claude Code reads as its prompt.

## Installation

### Via the AI Kit installer (recommended)

From the [repo root](../../):

```bash
bash install.sh --with-claude
```

This installs Snowflake CLI, Cortex Code CLI, Claude Code CLI, and copies the skill to `~/.claude/skills/cortex-code/`.

### Manual setup

Prerequisites: [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli) (v1.0.42+), [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code), Python 3.8+, a configured [Snowflake connection](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials).

```bash
cp -r agent-to-agent-skills/claude-cortex-code-router ~/.claude/skills/cortex-code
```

Optionally copy and edit the config:

```bash
cp ~/.claude/skills/cortex-code/config.yaml.example ~/.claude/skills/cortex-code/config.yaml
```

## What Gets Routed

| Route to Cortex | Stay in Claude Code |
|---|---|
| Snowflake databases, warehouses, schemas, tables | Local file operations |
| SQL queries for Snowflake | General programming (non-Snowpark) |
| Cortex AI (Search, Analyst, ML functions) | Non-Snowflake databases |
| Snowpark, dynamic tables, streams, tasks | Web development, frontend |
| Data governance, data quality in Snowflake | Git, GitHub, DevOps |

## Security

Three approval modes balance security and convenience:

| Mode | Default | Description |
|---|---|---|
| **prompt** | Yes | User approves predicted tools before execution |
| **auto** | | Auto-approve with mandatory audit logging (v1.x compat) |
| **envelope_only** | | Auto-approve, no tool prediction (fastest) |

Built-in protections: PII sanitization, credential path blocking, SHA256-validated caching, JSONL audit logs, organization policy override.

Configure in `~/.claude/skills/cortex-code/config.yaml` — see [config.yaml.example](config.yaml.example) for all options.

Full threat model and security policy: [SECURITY.md](SECURITY.md).

## Security Envelopes

| Envelope | Use Case | Blocked Tools |
|---|---|---|
| **RO** | Queries and reads | Edit, Write, destructive Bash |
| **RW** | Data modifications | Destructive operations (rm -rf, sudo) |
| **RESEARCH** | Exploratory work | Write operations |
| **DEPLOY** | Full access | None (use cautiously) |
| **NONE** | Custom | Specify via --disallowed-tools |

## File Structure

```
cortex-code/
├── SKILL.md                    # Skill definition (Claude Code prompt)
├── README.md                   # This file
├── SECURITY.md                 # Security policy and threat model
├── config.yaml.example         # Configuration template
├── scripts/
│   ├── discover_cortex.py      # Discover Cortex capabilities
│   ├── route_request.py        # Routing logic
│   ├── execute_cortex.py       # Headless Cortex execution
│   ├── read_cortex_sessions.py # Session history reader
│   ├── predict_tools.py        # Tool prediction
│   └── security_wrapper.py     # Security orchestrator
├── security/                   # Security modules
│   ├── config_manager.py       # 3-layer config (org > user > defaults)
│   ├── audit_logger.py         # JSONL audit logging
│   ├── cache_manager.py        # SHA256 cache validation
│   ├── prompt_sanitizer.py     # PII removal + injection detection
│   ├── approval_handler.py     # Tool approval flow
│   └── policies/default_policy.yaml
├── references/
│   ├── cortex-cli-reference.md # CLI event stream format
│   └── routing-examples.md     # Routing decision examples
└── tests/                      # 209 tests
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `cortex: command not found` | Check `which cortex`. Re-run installer or install from [ai.snowflake.com](https://ai.snowflake.com). |
| Unexpected approval prompts | Check `approval_mode` in config.yaml and org policy at `~/.snowflake/cortex/claude-skill-policy.yaml` |
| "Prompt contains credential file path" | Remove credential references from prompt, or customize `credential_file_allowlist` in config.yaml |
| Routing sends Snowflake query to Claude | Mention "Snowflake" explicitly. Check `scripts/route_request.py` patterns. |
| Permission denied despite auto mode | Tool is in the envelope blocklist. Switch to less restrictive envelope or use NONE with custom blocklist. |

See SKILL.md for the full troubleshooting section.

## References

- [SKILL.md](SKILL.md) — Full skill definition (Claude Code prompt)
- [SECURITY.md](SECURITY.md) — Security policy and threat model
- [config.yaml.example](config.yaml.example) — Configuration template
- [Cortex CLI Reference](references/cortex-cli-reference.md)
- [Routing Examples](references/routing-examples.md)

## License

Apache 2.0 — see [LICENSE](../../LICENSE).
