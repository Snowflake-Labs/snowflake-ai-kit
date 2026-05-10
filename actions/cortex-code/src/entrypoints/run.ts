/**
 * Main entry point for cortex-code-action.
 *
 * Orchestration phases:
 * 1. Parse GitHub context and validate trigger
 * 2. Set up authentication and permissions
 * 3. Fetch PR/issue data and construct prompt
 * 4. Configure MCP servers
 * 5. Run Cortex Code via SDK
 * 6. Post-run cleanup and comment updates
 */
import * as core from "@actions/core";
import * as github from "@actions/github";
import {
  parseGitHubContext,
  containsTrigger,
  isHumanActor,
  createOctokit,
  getGitHubToken,
  checkWritePermissions,
  checkForActiveRun,
  createTrackingComment,
  updateTrackingComment,
} from "../github";
import {
  fetchPRData,
  fetchIssueData,
  filterCommentsByTime,
} from "../github/data";
import { createPrompt, createAgentPrompt } from "../create-prompt";
import {
  setupSnowflakeConnection,
  cleanupConnection,
  installCortexCLI,
  runCortexCode,
} from "../cortex";
import { prepareMcpConfig } from "../mcp/install-mcp";
import { generateBranchName } from "../utils";
import { sanitizeContent } from "../utils/sanitize";

async function run(): Promise<void> {
  let commentId: number | null = null;
  let octokit: ReturnType<typeof createOctokit> | null = null;
  let owner = "";
  let repo = "";

  try {
    // ─── Phase 1: Parse Context & Validate ───
    core.info("Phase 1: Parsing GitHub context...");

    const ctx = parseGitHubContext();
    owner = ctx.owner;
    repo = ctx.repo;

    const triggerPhrase = process.env.INPUT_TRIGGER_PHRASE ?? "@cortex-code";
    const model = process.env.INPUT_MODEL ?? "auto";
    const branchPrefix = process.env.INPUT_BRANCH_PREFIX ?? "cortex-code/";
    const botName = process.env.INPUT_BOT_NAME ?? "cortex-code[bot]";
    const maxTurnsStr = process.env.INPUT_MAX_TURNS ?? "25";
    const maxTurns = maxTurnsStr ? parseInt(maxTurnsStr, 10) : 25;
    const timeoutMinutes = parseInt(
      process.env.INPUT_TIMEOUT_MINUTES ?? "10",
      10,
    );
    const customSystemPrompt = process.env.INPUT_SYSTEM_PROMPT ?? "";
    const allowedToolsStr = process.env.INPUT_ALLOWED_TOOLS ?? "";
    const disallowedToolsStr = process.env.INPUT_DISALLOWED_TOOLS ?? "";
    const directPrompt = process.env.INPUT_PROMPT ?? "";

    // Determine mode: agent mode (prompt provided) vs tag mode (@cortex-code mention)
    const isAgentMode = directPrompt.length > 0;
    const reviewMode =
      process.env.INPUT_REVIEW_MODE === "true" ||
      (isAgentMode &&
        directPrompt.toLowerCase().includes("review") &&
        process.env.INPUT_REVIEW_MODE !== "false");

    if (!isAgentMode) {
      // Tag mode: validate trigger phrase and human actor
      if (!containsTrigger(ctx.triggerCommentBody, triggerPhrase)) {
        core.info(
          `Trigger phrase "${triggerPhrase}" not found in comment. Skipping.`,
        );
        return;
      }

      if (!isHumanActor(ctx.triggerActor)) {
        core.info(`Actor ${ctx.triggerActor} is a bot. Skipping.`);
        return;
      }
    }

    core.info(
      `[${isAgentMode ? "Agent" : "Tag"} mode] Triggered on ${ctx.isPR ? "PR" : "issue"} #${ctx.entityNumber}`,
    );

    // ─── Phase 2: Authentication & Permissions ───
    core.info("Phase 2: Setting up authentication...");

    const githubToken = getGitHubToken();
    octokit = createOctokit(githubToken);

    const hasPermission = await checkWritePermissions(
      octokit,
      owner,
      repo,
      ctx.triggerActor,
    );
    if (!hasPermission) {
      core.warning(
        `User ${ctx.triggerActor} does not have write permissions. Skipping.`,
      );
      return;
    }

    // Debounce: skip if another run is already in progress
    if (!isAgentMode) {
      const activeRun = await checkForActiveRun(
        octokit,
        owner,
        repo,
        ctx.entityNumber,
      );
      if (activeRun) {
        core.info("Another Cortex Code run is already in progress. Skipping.");
        return;
      }
    }

    // Create tracking comment
    commentId = await createTrackingComment(
      octokit,
      owner,
      repo,
      ctx.entityNumber,
      botName,
    );
    core.info(`Created tracking comment: ${commentId}`);

    // Set up Snowflake connection
    const connectionName = setupSnowflakeConnection({
      account: process.env.SNOWFLAKE_ACCOUNT!,
      user: process.env.SNOWFLAKE_USER!,
      privateKey: process.env.SNOWFLAKE_PRIVATE_KEY,
      apiKey: process.env.SNOWFLAKE_API_KEY,
    });

    // ─── Phase 3: Fetch Data & Construct Prompt ───
    core.info("Phase 3: Fetching data and constructing prompt...");

    let data;
    if (ctx.isPR) {
      data = await fetchPRData(githubToken, owner, repo, ctx.entityNumber);
    } else {
      data = await fetchIssueData(githubToken, owner, repo, ctx.entityNumber);
    }

    // Filter comments by trigger time (TOCTOU protection)
    const triggerTime = new Date().toISOString();
    data.comments = filterCommentsByTime(
      data.comments,
      triggerTime,
      ctx.triggerCommentId,
    );

    const { systemPromptAppend, userPrompt } = isAgentMode
      ? createAgentPrompt(ctx, data, directPrompt, customSystemPrompt)
      : createPrompt(ctx, data, triggerPhrase, customSystemPrompt);

    // ─── Phase 4: Configure MCP Servers ───
    core.info("Phase 4: Configuring MCP servers...");

    const actionPath = process.env.GITHUB_ACTION_PATH ?? __dirname + "/../..";
    const headSha = ctx.isPR
      ? (ctx.payload.pull_request?.head?.sha ?? undefined)
      : undefined;

    const mcpServers = prepareMcpConfig({
      githubToken,
      owner,
      repo,
      commentId,
      headSha,
      isPR: ctx.isPR,
      actionPath,
      prNumber: ctx.isPR ? ctx.entityNumber : undefined,
    });

    // Build allowed tools list
    const baseTools = reviewMode
      ? ["Read", "Glob", "Grep", "mcp__github_comment__update_cortex_comment"]
      : [
          "Read",
          "Write",
          "Edit",
          "Bash",
          "Glob",
          "Grep",
          "mcp__github_comment__update_cortex_comment",
        ];
    if (ctx.isPR && headSha) {
      baseTools.push(
        "mcp__github_ci__get_ci_status",
        "mcp__github_ci__get_workflow_run_details",
      );
    }
    if (ctx.isPR) {
      baseTools.push(
        "mcp__github_review__post_review_comment",
        "mcp__github_review__submit_review",
      );
    }
    const userTools = allowedToolsStr
      ? allowedToolsStr.split(",").map((t) => t.trim())
      : [];
    const allowedTools = [...baseTools, ...userTools];
    const disallowedTools = disallowedToolsStr
      ? disallowedToolsStr.split(",").map((t) => t.trim())
      : [];

    // ─── Phase 5: Install & Run Cortex Code ───
    core.info("Phase 5: Running Cortex Code...");

    const timeoutMs = timeoutMinutes * 60 * 1000;
    const timeoutHandle = setTimeout(() => {
      core.setFailed(
        `Cortex Code Action timed out after ${timeoutMinutes} minutes`,
      );
      cleanupConnection();
      process.exit(1);
    }, timeoutMs);

    const cliPath = await installCortexCLI();

    const startTime = Date.now();
    const result = await runCortexCode({
      prompt: userPrompt,
      cwd: process.env.GITHUB_WORKSPACE ?? process.cwd(),
      connection: connectionName,
      model,
      allowedTools,
      disallowedTools,
      systemPromptAppend,
      maxTurns,
      mcpServers,
      cliPath,
    });

    // ─── Phase 6: Post-Run Cleanup ───
    clearTimeout(timeoutHandle);
    core.info("Phase 6: Cleanup and results...");

    const elapsedMs = Date.now() - startTime;
    const elapsedSec = Math.round(elapsedMs / 1000);
    const jobUrl = `${process.env.GITHUB_SERVER_URL ?? "https://github.com"}/${owner}/${repo}/actions/runs/${process.env.GITHUB_RUN_ID}`;

    // Set outputs
    core.setOutput("session_id", result.sessionId);
    core.setOutput("conclusion", result.success ? "success" : "failure");

    // Generate branch name for output
    const branchName = generateBranchName({
      prefix: branchPrefix,
      entityType: ctx.isPR ? "pr" : "issue",
      entityNumber: ctx.entityNumber,
    });
    core.setOutput("branch_name", branchName);

    // Update tracking comment with result (only if agent didn't already update it)
    // The agent is instructed to call update_cortex_comment with formatted results.
    // We only overwrite if the agent failed or didn't produce output.
    if (!result.success) {
      const logoUrl =
        "https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main/actions/cortex-code/assets/logo.png";
      const summaryBody = sanitizeContent(
        `## <img src="${logoUrl}" width="24" height="24" /> Cortex Code\n\n` +
          `Cortex Code finished task in ${elapsedSec}s — [View job](${jobUrl})\n\n` +
          `---\n\n` +
          `❌ Encountered an error.\n\n` +
          `**Session ID:** \`${result.sessionId}\`\n\n` +
          (result.output
            ? `<details><summary>Output</summary>\n\n\`\`\`\n${result.output.slice(0, 60000)}\n\`\`\`\n\n</details>`
            : "_No output captured._"),
      );
      await updateTrackingComment(octokit, owner, repo, commentId, summaryBody);
    } else {
      // Append timing footer to the agent's comment
      try {
        const { data: comment } = await octokit.issues.getComment({
          owner,
          repo,
          comment_id: commentId,
        });
        const existingBody = comment.body ?? "";
        const footer = `\n\n---\n_Cortex Code finished task in ${elapsedSec}s_ — [View job](${jobUrl})`;
        await updateTrackingComment(
          octokit,
          owner,
          repo,
          commentId,
          existingBody + footer,
        );
      } catch {
        // Best effort - don't fail if we can't append footer
      }
    }

    // Write step summary
    const statusText = result.success
      ? "completed successfully"
      : "encountered an error";
    await core.summary
      .addHeading("Cortex Code Action Results")
      .addRaw(`**Status:** ${statusText}\n\n`)
      .addRaw(`**Session ID:** \`${result.sessionId}\`\n\n`)
      .addRaw(
        `**Triggered by:** @${ctx.triggerActor} on ${ctx.isPR ? "PR" : "issue"} #${ctx.entityNumber}\n\n`,
      )
      .write();

    if (!result.success) {
      core.setFailed(`Cortex Code Action failed: ${result.error}`);
    }
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    core.setFailed(`cortex-code-action failed: ${errMsg}`);

    // Attempt to update tracking comment with error
    if (octokit && commentId) {
      try {
        await updateTrackingComment(
          octokit,
          owner,
          repo,
          commentId,
          `❌ **cortex-code[bot]** encountered a fatal error:\n\n\`\`\`\n${sanitizeContent(errMsg)}\n\`\`\``,
        );
      } catch {
        // Best effort
      }
    }
  } finally {
    cleanupConnection();
  }
}

run();
