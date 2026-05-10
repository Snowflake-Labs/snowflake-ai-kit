import * as path from "path";
import type { McpServerConfig } from "../cortex/types";

export interface McpInstallOptions {
  githubToken: string;
  owner: string;
  repo: string;
  commentId: number;
  headSha?: string;
  isPR: boolean;
  actionPath: string;
  prNumber?: number;
}

export function prepareMcpConfig(
  options: McpInstallOptions,
): Record<string, McpServerConfig> {
  const {
    githubToken,
    owner,
    repo,
    commentId,
    headSha,
    isPR,
    actionPath,
    prNumber,
  } = options;

  const servers: Record<string, McpServerConfig> = {};

  // Always include the comment server for updating progress
  servers["github_comment"] = {
    command: "bun",
    args: ["run", path.join(actionPath, "src/mcp/github-comment-server.ts")],
    env: {
      GITHUB_TOKEN: githubToken,
      REPO_OWNER: owner,
      REPO_NAME: repo,
      CORTEX_COMMENT_ID: String(commentId),
    },
  };

  // Include CI server only for PRs with a head SHA
  if (isPR && headSha) {
    servers["github_ci"] = {
      command: "bun",
      args: ["run", path.join(actionPath, "src/mcp/github-actions-server.ts")],
      env: {
        GITHUB_TOKEN: githubToken,
        REPO_OWNER: owner,
        REPO_NAME: repo,
        HEAD_SHA: headSha,
      },
    };
  }

  // Include review server for PRs
  if (isPR && prNumber) {
    servers["github_review"] = {
      command: "bun",
      args: ["run", path.join(actionPath, "src/mcp/github-review-server.ts")],
      env: {
        GITHUB_TOKEN: githubToken,
        REPO_OWNER: owner,
        REPO_NAME: repo,
        PR_NUMBER: String(prNumber),
      },
    };
  }

  return servers;
}
