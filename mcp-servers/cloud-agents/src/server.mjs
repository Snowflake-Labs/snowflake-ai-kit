#!/usr/bin/env node
import readline from "node:readline";
import { pathToFileURL } from "node:url";
import { AgentManager } from "./agent-manager.mjs";
import { SnowflakeAgentClient } from "./client.mjs";
import { FileStore } from "./store.mjs";
import { callTool, toolDefinitions } from "./tools.mjs";

const SERVER_INFO = {
  name: "cloud-agents-mcp",
  version: "0.1.0",
};

export async function createDefaultManager() {
  const store = new FileStore();
  const client = new SnowflakeAgentClient();
  const manager = new AgentManager({ client, store });
  await manager.init();
  return manager;
}

export async function handleJsonRpcMessage(message, manager) {
  if (!message || typeof message !== "object") {
    return errorResponse(null, -32600, "Invalid Request");
  }

  if (message.id === undefined) {
    return null;
  }

  try {
    switch (message.method) {
      case "initialize":
        return resultResponse(message.id, {
          protocolVersion: message.params?.protocolVersion ?? "2024-11-05",
          capabilities: { tools: {} },
          serverInfo: SERVER_INFO,
        });
      case "ping":
        return resultResponse(message.id, {});
      case "tools/list":
        return resultResponse(message.id, { tools: toolDefinitions() });
      case "tools/call": {
        const name = message.params?.name;
        const args = message.params?.arguments ?? {};
        const result = await callTool(manager, name, args);
        return resultResponse(message.id, {
          content: [
            {
              type: "text",
              text: `${JSON.stringify(result, null, 2)}\n`,
            },
          ],
        });
      }
      default:
        return errorResponse(
          message.id,
          -32601,
          `Method not found: ${message.method}`,
        );
    }
  } catch (err) {
    return errorResponse(message.id, -32000, err.message ?? String(err));
  }
}

export async function runStdio({ input = process.stdin, output = process.stdout } = {}) {
  const manager = await createDefaultManager();
  const rl = readline.createInterface({
    input,
    crlfDelay: Infinity,
  });

  for await (const line of rl) {
    if (!line.trim()) {
      continue;
    }
    let message;
    try {
      message = JSON.parse(line);
    } catch (err) {
      writeJson(output, errorResponse(null, -32700, `Parse error: ${err.message}`));
      continue;
    }
    const response = await handleJsonRpcMessage(message, manager);
    if (response) {
      writeJson(output, response);
    }
  }
}

function resultResponse(id, result) {
  return { jsonrpc: "2.0", id, result };
}

function errorResponse(id, code, message) {
  return {
    jsonrpc: "2.0",
    id,
    error: { code, message },
  };
}

function writeJson(output, payload) {
  output.write(`${JSON.stringify(payload)}\n`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  runStdio().catch((err) => {
    process.stderr.write(`cloud-agents-mcp fatal: ${err.stack || err.message}\n`);
    process.exitCode = 1;
  });
}
