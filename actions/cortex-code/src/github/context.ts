import * as github from "@actions/github";
import type { WebhookPayload } from "@actions/github/lib/interfaces";

export type EventType =
  | "issue_comment"
  | "issues"
  | "pull_request"
  | "pull_request_review_comment"
  | "pull_request_review";

export interface GitHubContext {
  eventName: EventType;
  owner: string;
  repo: string;
  entityNumber: number;
  isPR: boolean;
  triggerActor: string;
  triggerCommentBody: string;
  triggerCommentId: number | null;
  payload: WebhookPayload;
}

export function parseGitHubContext(): GitHubContext {
  const { context } = github;
  const eventName = context.eventName as EventType;
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  let entityNumber: number;
  let isPR = false;
  let triggerActor = context.actor;
  let triggerCommentBody = "";
  let triggerCommentId: number | null = null;

  switch (eventName) {
    case "issue_comment": {
      const comment = context.payload.comment!;
      entityNumber = context.payload.issue!.number;
      isPR = !!context.payload.issue?.pull_request;
      triggerActor = comment.user?.login ?? context.actor;
      triggerCommentBody = comment.body ?? "";
      triggerCommentId = comment.id;
      break;
    }
    case "pull_request_review_comment": {
      const comment = context.payload.comment!;
      entityNumber = context.payload.pull_request!.number;
      isPR = true;
      triggerActor = comment.user?.login ?? context.actor;
      triggerCommentBody = comment.body ?? "";
      triggerCommentId = comment.id;
      break;
    }
    case "pull_request_review": {
      const review = context.payload.review!;
      entityNumber = context.payload.pull_request!.number;
      isPR = true;
      triggerActor = review.user?.login ?? context.actor;
      triggerCommentBody = review.body ?? "";
      triggerCommentId = review.id;
      break;
    }
    case "issues": {
      entityNumber = context.payload.issue!.number;
      isPR = false;
      triggerCommentBody = context.payload.issue?.body ?? "";
      break;
    }
    case "pull_request": {
      entityNumber = context.payload.pull_request!.number;
      isPR = true;
      triggerCommentBody = context.payload.pull_request?.body ?? "";
      break;
    }
    default:
      throw new Error(`Unsupported event type: ${eventName}`);
  }

  return {
    eventName,
    owner,
    repo,
    entityNumber,
    isPR,
    triggerActor,
    triggerCommentBody,
    triggerCommentId,
    payload: context.payload,
  };
}

export function containsTrigger(body: string, triggerPhrase: string): boolean {
  return body.toLowerCase().includes(triggerPhrase.toLowerCase());
}

export function isHumanActor(actor: string): boolean {
  return !actor.endsWith("[bot]");
}
