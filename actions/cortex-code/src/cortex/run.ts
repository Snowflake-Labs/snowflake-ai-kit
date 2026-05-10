import { query } from "cortex-code-agent-sdk";
import * as core from "@actions/core";
import type { McpServerConfig } from "./types";

export interface RunCortexOptions {
  prompt: string;
  cwd: string;
  connection: string;
  model: string;
  allowedTools: string[];
  disallowedTools: string[];
  systemPromptAppend: string;
  maxTurns?: number;
  mcpServers: Record<string, McpServerConfig>;
  cliPath?: string;
}

export interface RunResult {
  success: boolean;
  sessionId: string;
  output: string;
  error?: string;
}

export async function runCortexCode(
  options: RunCortexOptions,
): Promise<RunResult> {
  const {
    prompt,
    cwd,
    connection,
    model,
    allowedTools,
    disallowedTools,
    systemPromptAppend,
    maxTurns,
    mcpServers,
    cliPath,
  } = options;

  let sessionId = "";
  let output = "";
  let success = true;

  try {
    const queryOptions: Record<string, any> = {
      cwd,
      connection,
      model,
      permissionMode: "bypassPermissions" as const,
      allowDangerouslySkipPermissions: true,
      allowedTools,
      systemPrompt: {
        type: "preset" as const,
        append: systemPromptAppend,
      },
    };

    if (disallowedTools.length > 0) {
      queryOptions.disallowedTools = disallowedTools;
    }
    if (maxTurns) {
      queryOptions.maxTurns = maxTurns;
    }
    if (Object.keys(mcpServers).length > 0) {
      queryOptions.mcpServers = mcpServers;
    }
    if (cliPath) {
      queryOptions.cliPath = cliPath;
    }

    // Log stderr from the CLI for debugging
    queryOptions.stderr = (line: string) => {
      core.debug(`[cortex stderr] ${line}`);
    };

    core.info("Starting Cortex Code agent...");

    for await (const message of query({
      prompt,
      options: queryOptions,
    })) {
      if (message.type === "assistant") {
        for (const block of message.content) {
          if (block.type === "text") {
            output += block.text;
            core.info(block.text);
          } else if (block.type === "tool_use") {
            core.info(`Tool: ${block.name}`);
          }
        }
      } else if (message.type === "user") {
        // Tool results - log errors for debugging
        const content = (message as any).message?.content;
        if (Array.isArray(content)) {
          for (const block of content) {
            if (block.type === "tool_result" && block.is_error) {
              core.warning(`Tool error: ${block.content}`);
            }
          }
        }
      } else if (message.type === "result") {
        sessionId = (message as any).session_id ?? "";
        if ((message as any).is_error) {
          success = false;
          const errors = (message as any).errors;
          const result = (message as any).result;
          const errorDetail = errors
            ? Array.isArray(errors)
              ? errors.join("; ")
              : String(errors)
            : (result ?? "Unknown error");
          output += `\nError: ${errorDetail}`;
          core.error(`Agent error: ${errorDetail}`);
        }
        core.info(`Agent finished: ${(message as any).subtype}`);
      }
    }
  } catch (error) {
    success = false;
    const errMsg = error instanceof Error ? error.message : String(error);
    output += `\nFatal error: ${errMsg}`;
    core.error(`Cortex Code execution failed: ${errMsg}`);
  }

  return { success, sessionId, output, error: success ? undefined : output };
}
