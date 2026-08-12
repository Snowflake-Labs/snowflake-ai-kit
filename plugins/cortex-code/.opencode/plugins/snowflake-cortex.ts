/**
 * Snowflake Cortex Code plugin for opencode.
 *
 * Exposes a `cortex_run` custom tool that routes Snowflake-related prompts to
 * Cortex Code CLI, plus a `tool.execute.before` hook that intercepts direct
 * Snowflake CLI (snow/snowsql) bash commands and redirects them through cortex.
 *
 * Install via: bash install.sh --with-opencode
 * Docs: https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-cli
 */

import { type Plugin, tool } from "@opencode-ai/plugin"
import { existsSync } from "fs"
import path from "path"

// ---------------------------------------------------------------------------
// Script directory resolution — works in repo dev AND after install.sh
// ---------------------------------------------------------------------------

function findScriptDir(): string {
  const candidates = [
    // Repo dev: plugin lives at plugins/cortex-code/.opencode/plugins/
    path.join(import.meta.dir, "../../scripts/router"),
    // After install.sh --with-opencode (global):
    // ~/.config/opencode/plugins/cortex-code-router/scripts/router/
    path.join(import.meta.dir, "cortex-code-router/scripts/router"),
    // Absolute fallback
    path.join(process.env.HOME ?? "~", ".config", "opencode", "plugins", "cortex-code-router", "scripts", "router"),
  ]
  return candidates.find(existsSync) ?? candidates[0]
}

const SCRIPT_DIR = findScriptDir()

// ---------------------------------------------------------------------------
// Snowflake CLI pattern — used by the tool.execute.before hook
// ---------------------------------------------------------------------------

// Matches direct Snowflake CLI invocations that should go through cortex instead
const DIRECT_SNOW_CLI = /\b(snow\s+(sql|object|warehouse|database|schema|table|stage|task|streamlit|connection\s+test)|snowsql)\b/i

// ---------------------------------------------------------------------------
// Plugin export
// ---------------------------------------------------------------------------

export const SnowflakeCortexCode: Plugin = async () => ({
  // -------------------------------------------------------------------------
  // Custom tool: cortex_run
  // -------------------------------------------------------------------------
  tool: {
    cortex_run: tool({
      description:
        "Execute Snowflake work via Cortex Code CLI. " +
        "Use for ANY Snowflake-related request: SQL queries, databases, warehouses, schemas, " +
        "tables, data governance, dynamic tables, Cortex AI, machine learning, streaming, " +
        "cost analysis, semantic views, Snowpark, native apps, Streamlit in Snowflake, " +
        "iceberg tables, and more. " +
        "To force routing, prefix the prompt with '$cortex-run'.",
      args: {
        prompt: tool.schema.string().describe("The Snowflake request to execute via Cortex Code"),
        envelope: tool.schema
          .enum(["RO", "RW", "RESEARCH", "DEPLOY"])
          .default("RW")
          .describe(
            "Security envelope: RO=read-only (SELECT/SHOW/DESCRIBE), " +
            "RW=read-write (default, DDL/DML allowed), " +
            "RESEARCH=read+web, DEPLOY=full access"
          ),
        resume_last: tool.schema
          .boolean()
          .default(false)
          .describe("Resume the previous Cortex session for multi-turn continuation"),
        connection: tool.schema
          .string()
          .optional()
          .describe("Snowflake connection name from connections.toml (uses default if omitted)"),
      },
      async execute(args) {
        const scriptPath = path.join(SCRIPT_DIR, "execute_cortex.py")
        const cmdArgs: string[] = [
          "--prompt", args.prompt,
          "--envelope", args.envelope ?? "RW",
          "--codex",
        ]
        if (args.resume_last) cmdArgs.push("--resume-last")
        if (args.connection) cmdArgs.push("--connection", args.connection)

        const result = await Bun.$`python3 ${scriptPath} ${cmdArgs}`
          .env({ ...process.env, OPENCODE: "1" })
          .text()
        return result.trim()
      },
    }),
  },

  // -------------------------------------------------------------------------
  // Hook: redirect direct Snowflake CLI bash calls through cortex
  // -------------------------------------------------------------------------
  "tool.execute.before": async (input, output) => {
    if (input.tool !== "bash") return
    const command: string = (output as { args?: { command?: string } }).args?.command ?? ""
    if (!DIRECT_SNOW_CLI.test(command)) return

    throw new Error(
      "[Snowflake Cortex Plugin] Direct Snowflake CLI commands bypass Cortex Code skills and security envelopes. " +
      "Use the cortex_run tool instead — it provides 55+ built-in Snowflake skills, " +
      "envelope-based permission control, and proper session management. " +
      "Example: call cortex_run with your prompt and envelope='RO' for read-only operations."
    )
  },
})
