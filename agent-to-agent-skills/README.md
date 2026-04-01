# Agent-to-Agent Skills

Skills that enable AI coding agents to delegate work to other AI agents — routing, orchestration, and multi-agent collaboration patterns.

## Available Skills

<!-- BEGIN_SKILLS_TABLE -->
| Skill | What it does |
|-------|-------------|
| [claude-cortex-code-router](claude-cortex-code-router/) | Route Snowflake operations from Claude Code to Cortex Code CLI for specialized expertise |
| [cortex-code-mcp-bridge](cortex-code-mcp-bridge/) | Connect any MCP-compatible AI agent to Snowflake via Cortex Code's built-in MCP server |
<!-- END_SKILLS_TABLE -->

## How It Works

Agent-to-agent skills define protocols for one AI agent to invoke another. The delegating agent discovers the target agent's capabilities, selects an appropriate security envelope, builds a prompt, and parses the structured response.

```
┌──────────────┐      prompt + envelope      ┌──────────────┐
│  Claude Code │  ─────────────────────────>  │  Cortex Code │
│  (delegator) │  <─────────────────────────  │  (specialist) │
└──────────────┘      NDJSON event stream     └──────────────┘
```

## Custom Skills

Create your own agent-to-agent skill by following the structure in any existing skill directory:

```
my-agent-bridge/
├── SKILL.md          # Agent entry point — YAML metadata + instructions
├── README.md         # Human-facing docs
└── scripts/          # Helper scripts for discovery, execution, parsing
```

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full guide.
