#!/usr/bin/env bun
/**
 * MCP server that exposes a tool to update the Cortex Code tracking comment
 * on a GitHub PR or issue.
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Octokit } from "@octokit/rest";
import { sanitizeContent } from "../utils/sanitize";

const GITHUB_TOKEN = process.env.GITHUB_TOKEN!;
const REPO_OWNER = process.env.REPO_OWNER!;
const REPO_NAME = process.env.REPO_NAME!;
const COMMENT_ID = parseInt(process.env.CORTEX_COMMENT_ID!, 10);

const octokit = new Octokit({ auth: GITHUB_TOKEN });

const server = new Server(
  {
    name: "github-comment-server",
    version: "1.0.0",
  },
  {
    capabilities: { tools: {} },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "update_cortex_comment",
      description:
        "Update the Cortex Code tracking comment on the current PR/issue with a progress update or final result.",
      inputSchema: {
        type: "object" as const,
        properties: {
          body: {
            type: "string",
            description:
              "The full markdown body to set on the tracking comment. Include a summary of work done so far.",
          },
        },
        required: ["body"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name !== "update_cortex_comment") {
    return {
      content: [{ type: "text", text: `Unknown tool: ${request.params.name}` }],
      isError: true,
    };
  }

  const { body } = request.params.arguments as { body: string };
  const sanitizedBody = sanitizeContent(body);

  try {
    await octokit.issues.updateComment({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      comment_id: COMMENT_ID,
      body: sanitizedBody,
    });

    return {
      content: [{ type: "text", text: "Comment updated successfully." }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Failed to update comment: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("MCP server fatal error:", error);
  process.exit(1);
});
