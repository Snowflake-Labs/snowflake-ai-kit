#!/usr/bin/env bun
/**
 * MCP server that exposes tools for inspecting GitHub Actions CI status.
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
const HEAD_SHA = process.env.HEAD_SHA!;

const octokit = new Octokit({ auth: GITHUB_TOKEN });

const server = new Server(
  {
    name: "github-actions-server",
    version: "1.0.0",
  },
  {
    capabilities: { tools: {} },
  },
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "get_ci_status",
      description:
        "Get the CI/workflow status for the current PR's head commit. Returns a summary of all workflow runs.",
      inputSchema: {
        type: "object" as const,
        properties: {
          status_filter: {
            type: "string",
            description:
              "Optional filter: 'completed', 'in_progress', 'queued', or 'all' (default: 'all')",
          },
        },
      },
    },
    {
      name: "get_workflow_run_details",
      description:
        "Get detailed information about a specific workflow run, including jobs and their steps.",
      inputSchema: {
        type: "object" as const,
        properties: {
          run_id: {
            type: "number",
            description: "The workflow run ID to inspect",
          },
        },
        required: ["run_id"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  switch (name) {
    case "get_ci_status":
      return await handleGetCIStatus(args as { status_filter?: string });
    case "get_workflow_run_details":
      return await handleGetRunDetails(args as { run_id: number });
    default:
      return {
        content: [{ type: "text", text: `Unknown tool: ${name}` }],
        isError: true,
      };
  }
});

async function handleGetCIStatus(args: { status_filter?: string }) {
  try {
    const { data } = await octokit.actions.listWorkflowRunsForRepo({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      head_sha: HEAD_SHA,
      per_page: 30,
    });

    const runs = data.workflow_runs.map((run) => ({
      id: run.id,
      name: run.name,
      status: run.status,
      conclusion: run.conclusion,
      url: run.html_url,
    }));

    const filter = args.status_filter ?? "all";
    const filtered =
      filter === "all"
        ? runs
        : runs.filter((r) => r.status === filter || r.conclusion === filter);

    const summary = {
      total: filtered.length,
      success: filtered.filter((r) => r.conclusion === "success").length,
      failure: filtered.filter((r) => r.conclusion === "failure").length,
      in_progress: filtered.filter((r) => r.status === "in_progress").length,
      runs: filtered,
    };

    return {
      content: [{ type: "text", text: JSON.stringify(summary, null, 2) }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Failed to get CI status: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

async function handleGetRunDetails(args: { run_id: number }) {
  try {
    const { data } = await octokit.actions.listJobsForWorkflowRun({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      run_id: args.run_id,
    });

    const jobs = data.jobs.map((job) => ({
      id: job.id,
      name: job.name,
      status: job.status,
      conclusion: job.conclusion,
      steps: job.steps?.map((step) => ({
        name: step.name,
        status: step.status,
        conclusion: step.conclusion,
      })),
    }));

    return {
      content: [{ type: "text", text: JSON.stringify(jobs, null, 2) }],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Failed to get run details: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
}

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("MCP server fatal error:", error);
  process.exit(1);
});
