import { graphql } from "@octokit/graphql";
import { Octokit } from "@octokit/rest";

const MAX_DIFF_SIZE = 50_000;

export interface PRData {
  title: string;
  body: string;
  author: string;
  headBranch: string;
  baseBranch: string;
  state: string;
  comments: CommentData[];
  changedFiles: ChangedFileData[];
  diff?: string;
}

export interface IssueData {
  title: string;
  body: string;
  author: string;
  state: string;
  comments: CommentData[];
}

export interface CommentData {
  id: number;
  author: string;
  body: string;
  createdAt: string;
}

export interface ChangedFileData {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  patch?: string;
}

const PR_QUERY = `
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $number) {
        title
        body
        author { login }
        headRefName
        baseRefName
        state
        comments(first: 100) {
          nodes {
            databaseId
            author { login }
            body
            createdAt
          }
        }
        files(first: 100) {
          nodes {
            path
            additions
            deletions
            changeType
          }
        }
      }
    }
  }
`;

const ISSUE_QUERY = `
  query($owner: String!, $repo: String!, $number: Int!) {
    repository(owner: $owner, name: $repo) {
      issue(number: $number) {
        title
        body
        author { login }
        state
        comments(first: 100) {
          nodes {
            databaseId
            author { login }
            body
            createdAt
          }
        }
      }
    }
  }
`;

export async function fetchPRData(
  token: string,
  owner: string,
  repo: string,
  number: number,
): Promise<PRData> {
  const graphqlWithAuth = graphql.defaults({
    headers: { authorization: `token ${token}` },
  });

  const result: any = await graphqlWithAuth(PR_QUERY, { owner, repo, number });
  const pr = result.repository.pullRequest;

  let diff: string | undefined;
  try {
    const restClient = new Octokit({ auth: token });
    const { data: diffData } = await restClient.pulls.get({
      owner,
      repo,
      pull_number: number,
      mediaType: { format: "diff" },
    });
    const rawDiff = diffData as unknown as string;
    diff =
      rawDiff.length > MAX_DIFF_SIZE
        ? rawDiff.slice(0, MAX_DIFF_SIZE) + "\n... [diff truncated]"
        : rawDiff;
  } catch {
    // Best effort — diff may be unavailable for very large PRs
  }

  return {
    title: pr.title,
    body: pr.body ?? "",
    author: pr.author?.login ?? "unknown",
    headBranch: pr.headRefName,
    baseBranch: pr.baseRefName,
    state: pr.state,
    comments: (pr.comments.nodes ?? []).map((c: any) => ({
      id: c.databaseId,
      author: c.author?.login ?? "unknown",
      body: c.body,
      createdAt: c.createdAt,
    })),
    changedFiles: (pr.files.nodes ?? []).map((f: any) => ({
      filename: f.path,
      status: f.changeType.toLowerCase(),
      additions: f.additions,
      deletions: f.deletions,
    })),
    diff,
  };
}

export async function fetchIssueData(
  token: string,
  owner: string,
  repo: string,
  number: number,
): Promise<IssueData> {
  const graphqlWithAuth = graphql.defaults({
    headers: { authorization: `token ${token}` },
  });

  const result: any = await graphqlWithAuth(ISSUE_QUERY, {
    owner,
    repo,
    number,
  });
  const issue = result.repository.issue;

  return {
    title: issue.title,
    body: issue.body ?? "",
    author: issue.author?.login ?? "unknown",
    state: issue.state,
    comments: (issue.comments.nodes ?? []).map((c: any) => ({
      id: c.databaseId,
      author: c.author?.login ?? "unknown",
      body: c.body,
      createdAt: c.createdAt,
    })),
  };
}

export function filterCommentsByTime(
  comments: CommentData[],
  triggerTime: string,
  triggerCommentId: number | null,
): CommentData[] {
  return comments.filter((c) => {
    if (triggerCommentId && c.id === triggerCommentId) return true;
    return new Date(c.createdAt) <= new Date(triggerTime);
  });
}
