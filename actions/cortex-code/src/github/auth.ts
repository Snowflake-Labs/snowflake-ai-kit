import { Octokit } from "@octokit/rest";
import * as core from "@actions/core";

export function createOctokit(token: string): Octokit {
  return new Octokit({ auth: token });
}

export function getGitHubToken(): string {
  const token = process.env.GITHUB_TOKEN;
  if (!token) {
    throw new Error(
      "GITHUB_TOKEN is required. Provide it via the github_token input.",
    );
  }
  return token;
}

export async function checkWritePermissions(
  octokit: Octokit,
  owner: string,
  repo: string,
  username: string,
): Promise<boolean> {
  try {
    const { data } = await octokit.repos.getCollaboratorPermissionLevel({
      owner,
      repo,
      username,
    });
    const level = data.permission;
    return level === "admin" || level === "write";
  } catch (error) {
    core.warning(`Could not check permissions for ${username}: ${error}`);
    return false;
  }
}
