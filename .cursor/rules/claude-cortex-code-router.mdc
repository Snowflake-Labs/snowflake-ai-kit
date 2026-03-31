---
name: claude-cortex-code-router
description: "Route Snowflake operations from Claude Code to Cortex Code CLI for specialized expertise. Use for: Snowflake queries via Cortex, delegate to Cortex Code, Cortex Code headless, multi-agent Snowflake workflow. Triggers: cortex code, delegate to cortex, route to cortex, use cortex for snowflake, snowflake specialist."
---

# Claude-to-Cortex Code Router

Delegate Snowflake-specific operations from Claude Code to Cortex Code CLI, which has deep Snowflake expertise (dynamic tables, semantic views, data quality, Cortex AI, cost optimization, and 30+ specialized skills).

## When to Use

- User explicitly asks to delegate a task to Cortex Code
- User wants Snowflake-specific expertise that Cortex Code excels at (semantic views, data quality DMFs, Cortex Agents, cost analysis, ML pipelines)
- User is in Claude Code but needs Cortex Code's specialized Snowflake skills
- User mentions "use Cortex Code" or "route to Cortex"

**Do NOT use when:**
- Task is general programming (Python, JS, web dev)
- Task involves non-Snowflake databases
- Task is local file editing, git operations, or infrastructure work
- User hasn't indicated they want Cortex Code involvement

## Tools Used

- `bash` — Run `cortex` CLI and helper scripts
- `ask_user_question` — Confirm security envelope and connection
- `read` — Load script files from this skill's `scripts/` directory

## Bundled Files

```
claude-cortex-code-router/
├── SKILL.md                        # This file (agent instructions)
├── README.md                       # Human-facing docs
└── scripts/
    ├── execute_cortex.py           # Headless Cortex CLI invocation
    └── discover_cortex.py          # Enumerate available Cortex skills
```

## Stopping Points

- Phase 0: User approves the delegation workflow
- Step 2: User confirms security envelope before execution

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### Cortex Code Router — What This Skill Does
>
> I'll delegate your Snowflake task to Cortex Code, which runs as a
> specialized agent with deep Snowflake expertise.
>
> **How it works:**
> ```
> Your request → Claude Code (this session)
>     → Cortex Code CLI (headless, auto-approval)
>     → Snowflake execution (SQL, tools, skills)
>     → Results returned here
> ```
>
> **What Cortex Code brings:**
> - 30+ specialized Snowflake skills (data quality, semantic views, cost intelligence, etc.)
> - Native `snowflake_sql_execute` and `data_diff` tools
> - Snowflake-specific training and documentation awareness
>
> **Requires:** Cortex Code CLI installed and a configured Snowflake connection
>
> **Security:** You choose a security envelope (read-only, read-write, etc.)
> that controls what tools Cortex can use.

**⚠️ MANDATORY STOPPING POINT**: Do NOT proceed until user explicitly approves.

---

## Step 1: Discover Cortex Capabilities (Optional)

Run the discovery script to enumerate what Cortex Code can do:

```bash
python3 <skill_dir>/scripts/discover_cortex.py
```

This caches Cortex's bundled skills to `/tmp/cortex-capabilities.json`. If it fails
(Cortex not installed, etc.), continue without it — the skill still works.

Use the discovered capabilities to inform the user what Cortex can help with.

---

## Step 2: Choose Security Envelope

Ask the user which security envelope to use:

| Envelope | What Cortex Can Do | Blocked Tools |
|----------|-------------------|---------------|
| **RO** (Read-Only) | Queries, reads, exploration | Edit, Write, destructive Bash |
| **RW** (Read-Write) | SQL DDL/DML, file creation | Destructive Bash (rm -rf, sudo) |
| **RESEARCH** | Read + web search | Write operations |
| **DEPLOY** | Full access | Nothing (use cautiously) |

Default to **RW** for most Snowflake operations. Use **RO** for pure queries.

**⚠️ MANDATORY STOPPING POINT**: Confirm envelope with the user before executing.

---

## Step 3: Build Enriched Prompt

Construct a prompt for Cortex that includes:

1. **The user's request** — the Snowflake task to perform
2. **Relevant context** — any database, schema, table names, or constraints from the current conversation
3. **Specific instructions** — e.g., "Use the data-quality skill" or "Run this SQL"

Format:
```
# Context from Current Session
[Relevant conversation details — database names, schemas, prior results]

# Task
[User's original request, rephrased for clarity if needed]
```

Keep context concise — Cortex starts a fresh session each invocation.

---

## Step 4: Execute via Cortex Code

Run the execution script:

```bash
python3 <skill_dir>/scripts/execute_cortex.py \
  --prompt "ENRICHED_PROMPT_HERE" \
  --envelope RW \
  --connection CONNECTION_NAME
```

Arguments:
- `--prompt` (required): The enriched prompt from Step 3
- `--envelope` (default: RW): Security envelope from Step 2
- `--connection` (optional): Snowflake connection name (uses default if omitted)

The script:
1. Invokes `cortex -p "..." --output-format stream-json --input-format stream-json`
2. The `--input-format stream-json` flag enables programmatic mode (auto-approval of tool calls)
3. Security is enforced via `--disallowed-tools` based on the chosen envelope
4. Parses the NDJSON event stream and returns structured results

---

## Step 5: Return Results

Parse the JSON output from `execute_cortex.py` and present to the user:

- **Text responses**: Display Cortex's analysis or explanation
- **SQL results**: Format query output as tables
- **Errors**: Surface any failures with actionable guidance
- **Tool calls**: Summarize what Cortex did (which tools it used, what SQL it ran)

If the result is incomplete or needs follow-up, you can run Step 4 again with additional context.

---

## Common Issues

| Issue | Solution |
|-------|----------|
| `cortex: command not found` | Install Cortex Code CLI: `curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh \| sh` |
| `No Snowflake connection configured` | Run `cortex connections create` to set up a connection |
| Permission denied despite correct envelope | Check that `--disallowed-tools` isn't blocking the needed tool; try a less restrictive envelope |
| Cortex hangs or times out | The `--input-format stream-json` flag auto-approves tools; if it still hangs, check network connectivity to Snowflake |
| `python3: No module found` | Scripts use stdlib only — ensure Python 3.8+ is installed |

## Output

- Cortex Code execution results (SQL output, analysis, generated code) surfaced in Claude Code
- Full transparency of tool calls made by Cortex
- Structured JSON for programmatic consumption

## References

- [Cortex Code CLI docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli)
- [Original inspiration: sfc-gh-tjia/claude_skill_cortexcode](https://github.com/sfc-gh-tjia/claude_skill_cortexcode) — the multi-agent routing pattern this skill is based on
