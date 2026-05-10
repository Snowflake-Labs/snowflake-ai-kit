import type { Octokit } from "@octokit/rest";

const DEBOUNCE_SECONDS = 60;

export async function checkForActiveRun(
  octokit: Octokit,
  owner: string,
  repo: string,
  issueNumber: number,
): Promise<boolean> {
  const { data: comments } = await octokit.issues.listComments({
    owner,
    repo,
    issue_number: issueNumber,
    per_page: 10,
    direction: "desc",
  });

  const now = Date.now();
  for (const comment of comments) {
    if (
      comment.body?.includes("Working on this...") &&
      comment.performed_via_github_app
    ) {
      const createdAt = new Date(comment.created_at).getTime();
      if (now - createdAt < DEBOUNCE_SECONDS * 1000) {
        return true;
      }
    }
  }
  return false;
}

export async function createTrackingComment(
  octokit: Octokit,
  owner: string,
  repo: string,
  issueNumber: number,
  botName: string,
): Promise<number> {
  const logoUrl =
    "https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/actions/cortex-code/assets/logo.png";
  const body = `## <img src="${logoUrl}" width="24" height="24" /> Cortex Code\n\n> 🔄 Working on this...\n\n_Processing your request. This comment will be updated with results._`;

  const { data } = await octokit.issues.createComment({
    owner,
    repo,
    issue_number: issueNumber,
    body,
  });

  return data.id;
}

export async function updateTrackingComment(
  octokit: Octokit,
  owner: string,
  repo: string,
  commentId: number,
  body: string,
): Promise<void> {
  await octokit.issues.updateComment({
    owner,
    repo,
    comment_id: commentId,
    body,
  });
}
