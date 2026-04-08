# Snowflake AI Kit

Install the **Snowflake CLI** (`snow`) and **Cortex Code CLI** (`cortex`) in one command, then start building on Snowflake.

## Quick Install

### macOS / Linux

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh)
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 | iex
```

### npx (any platform)

```bash
npx @snowflake-labs/ai-kit
```

The installer checks if each CLI is already installed and skips it if so. It also verifies your Snowflake connection configuration.

## What Gets Installed

| Tool | What it does | Docs |
|---|---|---|
| [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) (`snow`) | Manage Snowflake objects, deploy apps, run SQL from the terminal | [CLI Guide](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) |
| [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) (`cortex`) | AI coding assistant for Snowflake — generate code, explore data, build apps | [Cortex Code Docs](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code) |

Both tools share the same Snowflake connection config (`~/.snowflake/connections.toml`). Set one up with:

```bash
snow connection add
```

## Check Installation Status

```bash
# macOS / Linux
bash <(curl -sSL https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.sh) --check

# Windows
irm https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/install.ps1 -OutFile install.ps1; .\install.ps1 -Check
```

## Builder Apps

### Cortex Agent App

A chat UI for [Snowflake Cortex Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents). Ask questions in natural language — the agent uses Cortex Analyst (text-to-SQL), Cortex Search (RAG), and custom tools to answer them. Runs entirely on Snowflake compute, no external API key needed.

See [`builder-apps/cortex-agent/`](builder-apps/cortex-agent/) for setup and usage.

## Repo Structure

```
snowflake-ai-kit/
├── install.sh              # CLI installer (macOS/Linux)
├── install.ps1             # CLI installer (Windows)
├── bin/install.mjs         # npx entry point
├── builder-apps/
│   └── cortex-agent/       # Cortex Agent chat UI (React + FastAPI)
├── package.json
├── LICENSE
├── SECURITY.md
└── VERSION
```

## Troubleshooting

| Problem | Fix |
|---|---|
| `snow: command not found` | Make sure `~/.local/bin` (pipx) or your Python scripts dir is in `$PATH`. Try opening a new terminal. |
| `cortex: command not found` | Re-run the installer. If it still fails, install manually from [ai.snowflake.com](https://ai.snowflake.com). |
| `pip`/`pipx` not found | Install Python 3.10+ first: [python.org](https://www.python.org/downloads/) |
| Connection errors | Run `snow connection add` to create `~/.snowflake/connections.toml`. Docs: [Specify credentials](https://docs.snowflake.com/en/developer-guide/snowflake-cli/connecting/specify-credentials) |
| Installer hangs on Windows | Run PowerShell as Administrator, or download and run the script manually. |

## License

Apache 2.0 — see [LICENSE](LICENSE).
