# Cortex Code Skill

[![npm skills](https://img.shields.io/badge/skills-cortex--code-blue)](https://www.npmjs.com/package/skills)

This skill routes Snowflake-related operations to Cortex Code CLI, enabling coding agents to leverage specialized Snowflake expertise in headless mode.

## Quick Install

Choose your coding agent:

| Agent | Install method | Details |
|-------|---------------|---------|
| **Cursor** | `npx skills add snowflake-labs/subagent-cortex-code --copy --global` + copy routing rule | [→ Cursor](#cursor) |
| **Windsurf** | `npx skills add snowflake-labs/subagent-cortex-code --copy --global` | [→ Windsurf](#windsurf) |
| **Codex** | `bash integrations/codex/install.sh` (**not** npx — uses `cortexcode-tool`) | [→ Codex](#codex) |
| **GitHub Copilot** | `npx skills add snowflake-labs/subagent-cortex-code --copy --global` | [→ GitHub Copilot](#github-copilot) |
| **VSCode / terminal** | `bash integrations/cli-tool/setup.sh` | [→ CLI tool](#vscode--terminal) |

**Prerequisite for all**: Cortex Code CLI installed and configured.
```bash
which cortex          # must return a path
cortex connections list   # must show an active connection
```

### Also works out of the box with many other agents

When you run `npx skills add snowflake-labs/subagent-cortex-code --copy --global`, the skill is automatically installed for every "universal" agent the `skills` CLI knows about. No extra steps required — just restart the agent.

**Universal agents (installed to `~/.agents/skills/cortex-code/`, always included):**

- Amp
- Antigravity
- Cline
- Deep Agents
- Firebender
- Gemini CLI
- Kimi Code CLI
- OpenCode
- Warp

For the full list of 40+ supported agents (including optional opt-in ones like Continue, Goose, OpenHands, Roo Code, etc.) see the [`skills` CLI agents catalog](https://github.com/vercel-labs/skills). The interactive `npx` prompt lets you select additional targets per install.

---

## Cursor

**Step 1 — Install the skill:**
```bash
npx skills add snowflake-labs/subagent-cortex-code --copy --global
```

This installs `skills/cortex-code/` to `~/.cursor/skills/cortex-code/`.

**Step 2 — Activate the auto-routing rule:**
```bash
mkdir -p ~/.cursor/rules
cp ~/.cursor/skills/cortex-code/cortex-snowflake-routing.mdc ~/.cursor/rules/
```

**Step 3 — Restart Cursor.**

Without the routing rule you type `/cortex-code your question`. With it, Cursor detects Snowflake queries automatically and invokes the skill.

**Verify:**
```bash
ls ~/.cursor/skills/cortex-code/SKILL.md
ls ~/.cursor/rules/cortex-snowflake-routing.mdc
```

See [`integrations/cursor/README.md`](integrations/cursor/README.md) for full details.

---

## Windsurf

Install the skill via `npx`:

```bash
npx skills add snowflake-labs/subagent-cortex-code --copy --global
```

This installs `skills/cortex-code/` to `~/.codeium/windsurf/skills/cortex-code/`.

**Verify:**
```bash
ls ~/.codeium/windsurf/skills/cortex-code/SKILL.md
```

Restart Windsurf — Cascade auto-discovers the skill by name and description. Mention anything Snowflake-related and it activates automatically. No routing rule needed.

**Optional: configure security mode**
```bash
cp ~/.codeium/windsurf/skills/cortex-code/config.yaml.example \
   ~/.codeium/windsurf/skills/cortex-code/config.yaml
# edit as needed — default is "prompt" (asks before executing)
```

---

## Codex

Codex uses the `cortexcode-tool` CLI directly — no skill directory needed.

> **Important:** Do NOT run `npx skills add` for Codex. Codex uses the `cortexcode-tool` CLI so the agent can request sandbox/network approval in chat, then run the approved command with `--yes`. Use the CLI install below instead.

```bash
git clone https://github.com/Snowflake-Labs/subagent-cortex-code.git
cd subagent-cortex-code
bash integrations/codex/install.sh
```

The script:
1. Installs the `cortexcode-tool` CLI to `~/.local/bin/`
2. Auto-detects your active Cortex connection
3. Writes config to `~/.local/lib/cortexcode-tool/config.yaml` (auto-detected, no `--config` flag needed)

**Verify:**
```bash
cortexcode-tool --version
cortexcode-tool "How many databases do I have in Snowflake?" --envelope RO
```

The second command is a direct terminal smoke test and may ask for approval in
the terminal. Inside a Codex chat, Codex should first ask you to approve the
planned Cortex Code execution, then retry the approved foreground command with
`--yes`.

**Usage from Codex sessions:**

First time — paste into a Codex session to confirm the tool is discoverable:
```
which cortexcode-tool
cortexcode-tool --help
```

Once discovered, Codex invokes `cortexcode-tool` for Snowflake questions automatically. For read-only Snowflake questions, the approved command should look like this:
```
cortexcode-tool --yes "How many databases do I have in Snowflake?" --envelope RO
```

Implicit prompts also work — Codex detects Snowflake intent, asks for approval,
and calls `cortexcode-tool` on your behalf:
```
How many databases do I have in Snowflake?
```

See [`integrations/codex/README.md`](integrations/codex/README.md) for full details.

---

## GitHub Copilot

Install the skill via `npx`:

```bash
npx skills add snowflake-labs/subagent-cortex-code --copy --global
```

This installs `skills/cortex-code/` to `~/.agents/skills/cortex-code/` — the universal skills directory that GitHub Copilot CLI reads from automatically.

**Verify:**
```bash
ls ~/.agents/skills/cortex-code/SKILL.md
```

Start a GitHub Copilot CLI session — it auto-discovers the skill by name and description. Mention anything Snowflake-related and it activates automatically. No routing rule needed.

**Optional: configure security mode**
```bash
cp ~/.agents/skills/cortex-code/config.yaml.example \
   ~/.agents/skills/cortex-code/config.yaml
# edit as needed — default is "prompt" (asks before executing)
```

---

## VSCode / terminal

For VSCode task runners, Windsurf, or any terminal environment:

```bash
git clone https://github.com/Snowflake-Labs/subagent-cortex-code.git
cd subagent-cortex-code/integrations/cli-tool
bash setup.sh
```

**Verify:**
```bash
cortexcode-tool --version
cortexcode-tool "your question"
```

See [`integrations/cli-tool/README.md`](integrations/cli-tool/README.md) for full details.

---

## Overview

The Cortex Code Integration Skill bridges coding agents and Cortex Code CLI, allowing seamless delegation of Snowflake-specific tasks while the agent handles everything else.

**Key Features:**
- **Smart Routing**: LLM-based semantic routing automatically detects Snowflake operations
- **Security Envelopes**: Configurable permission models (RO, RW, RESEARCH, DEPLOY); `NONE` is rejected for managed Cortex execution
- **Approval Modes**: Three security modes (prompt/auto/envelope_only) for different trust levels
- **Prompt Sanitization**: Automatic PII removal and injection attempt detection
- **Context Enrichment**: Passes conversation history to Cortex for informed execution
- **Audit Logging**: Structured JSONL logs for compliance and monitoring
- **Enterprise Ready**: Organization policy override for centralized security management

## Architecture

```
User Request
    ↓
[Your Coding Agent — Routing Layer]
    ↓
  Is Snowflake-related?
    ↓ YES                      ↓ NO
[Cortex Code CLI]    [Your Coding Agent]
    ↓                          ↓
Snowflake Execution       General Tasks
```

**Routing Principle**: ONLY Snowflake operations → Cortex Code. Everything else → your coding agent.

### What Gets Routed to Cortex Code?

✅ **Routes to Cortex:**
- Snowflake databases, warehouses, schemas, tables
- SQL queries specifically for Snowflake
- Cortex AI features (Cortex Search, Cortex Analyst, ML functions)
- Snowpark, dynamic tables, streams, tasks
- Data governance, data quality in Snowflake
- Snowflake security, roles, policies
- User explicitly mentions "Cortex" or "Snowflake"

❌ **Stays with your agent:**
- Local file operations (reading, writing, editing local files)
- General programming (Python, JavaScript, etc. not Snowflake-specific)
- Non-Snowflake databases (PostgreSQL, MySQL, MongoDB, etc.)
- Web development, frontend work
- Infrastructure/DevOps unrelated to Snowflake
- Git operations, GitHub, version control

## Security

### Three Approval Modes

| Mode | Security | Use Case |
|------|----------|----------|
| **prompt** (default) | High | Interactive sessions, production |
| **auto** | Medium | Automated workflows, CI/CD |
| **envelope_only** | Medium | Trusted environments, faster |

Configure in `config.yaml` in the skill's install directory (for skill-based agents) or `~/.local/lib/cortexcode-tool/config.yaml` (for CLI-based agents):
```yaml
security:
  approval_mode: "prompt"  # or "auto" or "envelope_only"
```

### Security Envelopes

| Envelope | Use Case | Blocked Tools |
|----------|----------|---------------|
| **RO** (Read-Only) | Queries and reads | Edit, Write, Bash |
| **RW** (Read-Write) | Data modifications | Bash and destructive shell patterns |
| **RESEARCH** | Exploratory work | Edit, Write, Bash |
| **DEPLOY** | Deployment operations | Requires explicit confirmation; blocks Bash/destructive shell |
| **NONE** | No managed execution | Rejected before Cortex execution |

### Built-in Protections

1. **Prompt Sanitization**: Automatic removal of PII (emails, SSN, credit cards)
2. **Credential Blocking**: Prevents routing when paths like `~/.ssh/`, `.env` are detected
3. **Secure Caching**: HMAC-signed capability cache under `~/.cache/cortex-skill/`
4. **Audit Logging**: Tamper-evident JSONL logs with hash chaining, including prompt-mode approval requests
5. **Envelope Gate**: Requested envelopes must be present in `security.allowed_envelopes` before routing, approval, or Cortex execution
6. **Organization Policy**: Enterprise admins can enforce settings via `~/.snowflake/cortex/claude-skill-policy.yaml`; relaxed approval/envelope settings must be explicitly authorized
7. **Private Installs**: Installers use private permissions (`0700` directories, `0600` sensitive config/log files)

See [SECURITY.md](SECURITY.md) and [SECURITY_GUIDE.md](SECURITY_GUIDE.md) for full details.

## How It Works

### Dynamic Skill Discovery

The integration automatically discovers Cortex Code's native capabilities at session start:

1. Runs `cortex skill list` to enumerate all available skills (32+ bundled in v1.0.42)
2. Reads each skill's `SKILL.md` from `~/.local/share/cortex/{version}/bundled_skills/`
3. Extracts trigger patterns ("data quality", "semantic view", "DMF", etc.)
4. Caches results with `CacheManager` in the configured cache directory
5. Uses discovered triggers to boost routing score for matching requests

This is **future-proof**: new Cortex releases with additional skills work automatically.

### Headless Execution

Cortex is invoked with stream JSON output for non-TTY execution:
```bash
cortex -p "ENRICHED_PROMPT" --output-format stream-json
```
Security is enforced via `--disallowed-tools` blocklists controlled by the chosen envelope. Requested envelopes are checked against `security.allowed_envelopes` before routing, approval, or Cortex execution. Auto and envelope-only modes are trusted, opt-in modes: user config cannot enable them unless an organization policy explicitly permits the relaxed field/value, `NONE` is rejected before Cortex execution, and `DEPLOY` requires explicit confirmation.

## Real-World Example

**Scenario:** Build a Cortex Agent for macroeconomic analysis

```
User: "Analyze FINANCE__ECONOMICS. Create a Cortex agent with Cortex Analyst
that can answer macro economic questions. Put assets in DB_STOCK."
```

- **Minutes 0-2**: Explores 56 views, identifies 5 key tables (GDP, unemployment, inflation, interest rates, indicators)
- **Minutes 2-8**: Generates semantic model, deploys to `DB_STOCK.CURATED.MACRO_ECONOMICS_INDICATORS`
- **Minutes 8-12**: Creates `DB_STOCK.CURATED.MACRO_ECONOMICS_ANALYST` with Cortex Analyst
- **Minutes 12-15**: Runs 5 test queries — UK 3.03%, US 2.39%, Germany 2.08%, Japan 2.08%, France 0.79%

Production-ready Cortex Agent deployed in one conversation, tested and immediately queryable.

## Repo Structure

```
subagent-cortex-code/
├── skills/
│   └── cortex-code/           # Installable skill (npx skills add)
│       ├── SKILL.md            # Skill definition — loaded by Claude Code, Cursor, etc.
│       ├── cortex-snowflake-routing.mdc   # Cursor auto-routing rule
│       ├── config.yaml.example
│       ├── scripts/            # Routing, execution, discovery, context
│       └── security/           # Approval, audit, cache, sanitization modules
│
├── integrations/
│   ├── claude-code/            # Claude Code-specific notes and uninstall script
│   ├── cursor/                 # Cursor-specific notes and uninstall script
│   ├── codex/                  # Codex install script (cortexcode-tool + config)
│   └── cli-tool/               # cortexcode-tool Python package + setup script
│
└── shared/                     # Canonical source for scripts/ and security/
    ├── scripts/                # (copied into skills/cortex-code/ by install process)
    └── security/
```

## Troubleshooting

**Cortex CLI not found:**
```bash
which cortex
# If missing: curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh
```

**No active connection:**
```bash
cortex connections list
cortex connections create   # to add one
```

**Skill not loading (Claude Code / Cursor):**
```bash
ls ~/.claude/skills/cortex-code/SKILL.md                    # Claude Code
ls ~/.cursor/skills/cortex-code/SKILL.md             # Cursor
ls ~/.codeium/windsurf/skills/cortex-code/SKILL.md          # Windsurf
# If missing, re-run: npx skills add snowflake-labs/subagent-cortex-code --copy --global
```

**Codex command waits or needs network approval:**
```bash
# Verify cortexcode-tool config exists and check approval mode
cat ~/.local/lib/cortexcode-tool/config.yaml | grep approval_mode
# Interactive installs should prefer: approval_mode: "prompt"
```
Approve the planned Cortex Code execution in Codex chat, then retry the same foreground command with `--yes`.

**cortexcode-tool not found (Codex / CLI):**
```bash
which cortexcode-tool
# If missing: re-run the install script
```

## References

- [SECURITY.md](SECURITY.md) — Security policy and threat model
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md) — Best practices for personal/team/enterprise
- [integrations/claude-code/README.md](integrations/claude-code/README.md) — Claude Code setup
- [integrations/cursor/README.md](integrations/cursor/README.md) — Cursor setup
- [integrations/codex/README.md](integrations/codex/README.md) — Codex setup
- [integrations/cli-tool/README.md](integrations/cli-tool/README.md) — CLI tool setup

## License

Copyright (c) Snowflake Inc. All rights reserved.
Licensed under the [Snowflake Skills License](LICENSE).

For issues: [GitHub Issues](https://github.com/Snowflake-Labs/subagent-cortex-code/issues)
