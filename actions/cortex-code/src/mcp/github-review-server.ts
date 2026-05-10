#!/usr/bin/env bun
/**
 * MCP server that exposes tools for creating inline PR review comments
 * via the GitHub Pull Request Reviews API.
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { Octokit } from "@octokit/rest";

const GITHUB_TOKEN = process.env.GITHUB_TOKEN!;
const REPO_OWNER = process.env.REPO_OWNER!;
const REPO_NAME = process.env.REPO_NAME!;
const PR_NUMBER = parseInt(process.env.PR_NUMBER!, 10);

const octokit = new Octokit({ auth: GITHUB_TOKEN });

interface ReviewComment {
  path: string;
  line: number;
  body: string;
  side?: "LEFT" | "RIGHT";
}

let pendingComments: ReviewComment[] = [];

const server = new Server(
  {
    name: "github-review-server",
    version: "1.0.0",
  },
  {
    capabilities: { tools: {} },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "post_review_comment",
      description:
        "Add an inline review comment on a specific file and line in the PR. Comments are batched until submit_review is called.",
      inputSchema: {
        type: "object" as const,
        properties: {
          path: {
            type: "string",
            description: "File path relative to the repository root.",
          },
          line: {
            type: "number",
            description:
              "Line number in the file to comment on (in the new version of the file).",
          },
          body: {
            type: "string",
            description: "The review comment body in markdown.",
          },
          side: {
            type: "string",
            enum: ["LEFT", "RIGHT"],
            description:
              "Which side of the diff to comment on. LEFT = old file, RIGHT = new file. Defaults to RIGHT.",
          },
        },
        required: ["path", "line", "body"],
      },
    },
    {
      name: "submit_review",
      description:
        "Submit all pending inline comments as a single PR review. Call this after adding all comments with post_review_comment.",
      inputSchema: {
        type: "object" as const,
        properties: {
          event: {
            type: "string",
            enum: ["COMMENT", "APPROVE", "REQUEST_CHANGES"],
            description:
              "The review action: COMMENT (neutral), APPROVE, or REQUEST_CHANGES.",
          },
          body: {
            type: "string",
            description: "Overall review summary body in markdown.",
          },
        },
        required: ["event", "body"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "post_review_comment") {
    const { path, line, body, side } = args as {
      path: string;
      line: number;
      body: string;
      side?: "LEFT" | "RIGHT";
    };

    pendingComments.push({ path, line, body, side: side ?? "RIGHT" });

    return {
      content: [
        {
          type: "text",
          text: `Queued inline comment on ${path}:${line} (${pendingComments.length} total pending).`,
        },
      ],
    };
  }

  if (name === "submit_review") {
    const { event, body } = args as { event: string; body: string };

    try {
      const comments = pendingComments.map((c) => ({
        path: c.path,
        line: c.line,
        body: c.body,
        side: c.side,
      }));

      await octokit.pulls.createReview({
        owner: REPO_OWNER,
        repo: REPO_NAME,
        pull_number: PR_NUMBER,
        event: event as "COMMENT" | "APPROVE" | "REQUEST_CHANGES",
        body,
        comments,
      });

      const count = pendingComments.length;
      pendingComments = [];

      return {
        content: [
          {
            type: "text",
            text: `Review submitted with ${count} inline comment(s) and event "${event}".`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Failed to submit review: ${error instanceof Error ? error.message : String(error)}`,
          },
        ],
        isError: true,
      };
    }
  }

  return {
    content: [{ type: "text", text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("MCP review server fatal error:", error);
  process.exit(1);
});
