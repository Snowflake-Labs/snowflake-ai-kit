#!/usr/bin/env node

import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { parseArgs, splitRawArgumentString } from "./lib/args.mjs";
import { binaryAvailable, runCommand, terminateProcessTree } from "./lib/process.mjs";
import { resolveWorkspaceRoot } from "./lib/workspace.mjs";
import { ensureGitRepository, resolveReviewTarget, collectReviewDiff, getGitStatus, getDiffStat } from "./lib/git.mjs";
import {
  generateJobId, getConfig, setConfig, listJobs, upsertJob, writeJobFile, readJobFile,
  resolveJobFile, resolveJobLogFile, loadState, ensureStateDir
} from "./lib/state.mjs";

const SESSION_ID_ENV = process.env.CORTEX_SESSION_ID ? "CORTEX_SESSION_ID" : "CODEX_COMPANION_SESSION_ID";

function printUsage() {
  console.log([
    "Usage:",
    "  cortex-companion setup [--json]",
    "  cortex-companion review [--base <ref>] [--scope auto|working-tree|branch] [-c connection]",
    "  cortex-companion adversarial-review [--base <ref>] [--scope auto|working-tree|branch] [-c connection] [focus text]",
    "  cortex-companion task [--write] [--background] [-c connection] [--model model] [--effort effort] [prompt]",
    "  cortex-companion status [job-id] [--all] [--json]",
    "  cortex-companion result [job-id] [--json]",
    "  cortex-companion cancel [job-id] [--json]",
  ].join("\n"));
}

function nowIso() { return new Date().toISOString(); }

function outputResult(value, asJson) {
  if (asJson) console.log(JSON.stringify(value, null, 2));
  else process.stdout.write(typeof value === "string" ? value : JSON.stringify(value, null, 2));
}

function normalizeArgv(argv) {
  if (argv.length === 1 && argv[0]?.trim()) return splitRawArgumentString(argv[0]);
  return argv;
}

function parseCommandInput(argv, config = {}) {
  return parseArgs(normalizeArgv(argv), { ...config, aliasMap: { C: "cwd", c: "connection", m: "model", ...config.aliasMap } });
}

function resolveCwd(options) {
  return options.cwd ? path.resolve(process.cwd(), options.cwd) : process.cwd();
}

function shorten(text, limit = 96) {
  const s = String(text ?? "").trim().replace(/\s+/g, " ");
  return s.length <= limit ? s : `${s.slice(0, limit - 3)}...`;
}

// --- Cortex CLI invocation ---

function findCortexBinary() {
  for (const name of ["cortex"]) {
    // First try which/where to check existence
    const which = runCommand("which", [name], { timeout: 5000 });
    if (which.status === 0 && which.stdout) {
      const check = binaryAvailable(name, ["--version"]);
      return { binary: name, version: check.available ? check.detail : which.stdout };
    }
  }
  return null;
}

function buildCortexArgs(options = {}) {
  const args = [];
  if (options.connection) args.push("-c", options.connection);
  if (options.workdir) args.push("-w", options.workdir);
  if (options.model) args.push("-m", options.model);
  if (options.effort) args.push("--effort", options.effort);
  if (options.maxTurns) args.push("--max-turns", String(options.maxTurns));
  if (options.allowedTools) {
    for (const tool of options.allowedTools) args.push("--allowed-tools", tool);
  }
  if (options.bypass) args.push("--dangerously-allow-all-tool-calls");
  return args;
}

function runCortex(prompt, options = {}) {
  const binary = findCortexBinary();
  if (!binary) throw new Error("Cortex Code CLI not found. Install it first.");

  const args = ["-p", prompt, "--output-format", "stream-json", ...buildCortexArgs(options)];
  if (options.jsonSchema) args.push("--json-schema", JSON.stringify(options.jsonSchema));

  const cwd = options.workdir || process.cwd();
  process.stderr.write(`[cortex] Running: ${binary.binary} -p "..." --output-format stream-json ${buildCortexArgs(options).join(" ")}\n`);

  const result = runCommand(binary.binary, args, {
    cwd,
    timeout: options.timeout || 600000,
  });

  return parseStreamJsonOutput(result);
}

function parseStreamJsonOutput(result) {
  const lines = result.stdout.split("\n").filter(Boolean);
  let finalText = "";
  let structured = null;
  let sessionId = null;
  let isError = false;
  let numTurns = 0;
  let durationMs = 0;
  const toolCalls = [];

  for (const line of lines) {
    try {
      const msg = JSON.parse(line);

      if (msg.type === "system" && msg.subtype === "init") {
        sessionId = msg.session_id;
      } else if (msg.type === "result") {
        finalText = msg.result || finalText;
        isError = Boolean(msg.is_error);
        numTurns = msg.num_turns || 0;
        durationMs = msg.duration_ms || 0;
        if (msg.structured_output) structured = msg.structured_output;
      } else if (msg.type === "assistant" && msg.message?.content) {
        for (const block of msg.message.content) {
          if (block.type === "text") finalText = block.text;
          if (block.type === "tool_use") toolCalls.push({ name: block.name, input: block.input });
        }
      }
    } catch { /* skip non-json lines */ }
  }

  return {
    status: result.status,
    stdout: finalText || result.stdout,
    stderr: result.stderr,
    structured,
    sessionId,
    isError,
    numTurns,
    durationMs,
    toolCalls,
    error: result.error,
  };
}

// --- Setup ---

function handleSetup(argv) {
  const { options } = parseCommandInput(argv, { booleanOptions: ["json"], valueOptions: ["cwd"] });
  const cortex = findCortexBinary();
  const node = binaryAvailable("node", ["--version"]);

  const report = {
    ready: Boolean(cortex),
    node,
    cortex: cortex ? { available: true, detail: cortex.version } : { available: false, detail: "cortex CLI not found" },
    nextSteps: [],
  };

  if (!cortex) {
    report.nextSteps.push("Install Cortex Code CLI.");
  }

  outputResult(options.json ? report : renderSetupReport(report), options.json);
}

function renderSetupReport(report) {
  const lines = ["# Cortex Code Setup\n"];
  lines.push(`- Node: ${report.node.available ? report.node.detail : "not found"}`);
  lines.push(`- Cortex CLI: ${report.cortex.available ? report.cortex.detail : "not found"}`);
  lines.push(`- Ready: ${report.ready ? "yes" : "no"}`);
  if (report.nextSteps.length) {
    lines.push("\nNext steps:");
    for (const s of report.nextSteps) lines.push(`  - ${s}`);
  }
  return lines.join("\n") + "\n";
}

// --- Review ---

async function handleReview(argv, reviewName = "Review") {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["base", "scope", "connection", "model", "cwd"],
    booleanOptions: ["json", "background", "wait"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  ensureGitRepository(cwd);

  const cortex = findCortexBinary();
  if (!cortex) throw new Error("Cortex Code CLI not found.");

  const target = resolveReviewTarget(cwd, { base: options.base, scope: options.scope });
  const focusText = positionals.join(" ").trim();
  const diff = collectReviewDiff(cwd, target);

  if (!diff && !getGitStatus(cwd)) {
    outputResult("Nothing to review -- working tree is clean and no branch diff found.\n", false);
    return;
  }

  const reviewPrompt = buildReviewPrompt(reviewName, target, diff, focusText);
  const jobId = generateJobId("review");

  upsertJob(workspaceRoot, {
    id: jobId, kind: reviewName === "Review" ? "review" : "adversarial-review",
    title: `Cortex ${reviewName}`, jobClass: "review",
    status: "running", summary: `${reviewName} ${target.label}`,
    startedAt: nowIso(),
  });

  process.stderr.write(`[cortex] Running ${reviewName} on ${target.label}...\n`);

  const result = runCortex(reviewPrompt, {
    connection: options.connection,
    model: options.model,
    workdir: cwd,
    timeout: 600000,
  });

  const completedAt = nowIso();
  const status = result.status === 0 ? "completed" : "failed";

  upsertJob(workspaceRoot, {
    id: jobId, status, completedAt,
    summary: result.status === 0 ? shorten(result.stdout) : "Review failed",
  });

  writeJobFile(workspaceRoot, jobId, {
    id: jobId, status, kind: reviewName === "Review" ? "review" : "adversarial-review",
    target, result: result.stdout, stderr: result.stderr, completedAt,
  });

  if (result.status !== 0) {
    process.stderr.write(`[cortex] Review failed: ${result.stderr}\n`);
    process.exitCode = result.status;
  }

  outputResult(options.json ? { jobId, status, target, result: result.stdout } : result.stdout + "\n", options.json);
}

const REVIEW_PRESETS = {
  "Review": {
    system: "Review the following code changes. Identify bugs, security issues, performance problems, and suggest improvements.",
  },
  "Adversarial Review": {
    system: "You are performing an adversarial code review. Your job is to break confidence in the change, not to validate it.\nFind the strongest reasons this change should NOT ship yet.\nPrioritize: auth/permissions issues, data loss/corruption, race conditions, rollback safety, missing error handling, observability gaps.\nReport only material findings with file paths and line numbers. Do not include style feedback.",
  },
  "Data Review": {
    system: [
      "You are a Snowflake data engineering expert reviewing code changes.",
      "Focus on:",
      "- Snowflake SQL correctness, query performance, and warehouse sizing",
      "- Data pipeline reliability: idempotency, retry handling, partial failure recovery",
      "- Schema evolution safety: backward compatibility, migration risks",
      "- Data quality: missing validations, type coercions, NULL handling",
      "- Cost: unnecessary full table scans, missing clustering keys, warehouse auto-suspend",
      "- Snowflake-specific anti-patterns: SELECT *, COPY INTO without error handling, missing QUALIFY",
      "Report findings with file paths and line numbers.",
    ].join("\n"),
  },
  "dbt Review": {
    system: [
      "You are a dbt and Snowflake expert reviewing dbt model changes.",
      "Focus on:",
      "- Model materialization strategy: table vs incremental vs view, when each is appropriate",
      "- Incremental model correctness: merge keys, unique key handling, late-arriving data",
      "- Ref/source usage: hardcoded table names, missing refs, circular dependencies",
      "- Testing coverage: missing not_null, unique, relationships, accepted_values tests",
      "- Documentation: missing descriptions on models and columns",
      "- Performance: unnecessary CTEs, N+1 patterns, missing cluster keys in config",
      "- Snowflake-specific: VARIANT column handling, FLATTEN usage, TIME_TRAVEL considerations",
      "- Lineage impact: downstream model breakage, column renames without downstream updates",
      "Report findings with file paths and line numbers.",
    ].join("\n"),
  },
  "SQL Review": {
    system: [
      "You are a Snowflake SQL optimization expert reviewing SQL changes.",
      "Focus on:",
      "- Query performance: missing filters, unnecessary JOINs, Cartesian products",
      "- Snowflake best practices: QUALIFY over subqueries, LATERAL FLATTEN, MERGE correctness",
      "- Anti-patterns: SELECT *, UNION vs UNION ALL, unnecessary ORDER BY in subqueries",
      "- Cost optimization: warehouse sizing, query pruning, clustering alignment",
      "- Data correctness: implicit type casting, timezone handling, NULL propagation",
      "- Security: SQL injection in dynamic SQL, RBAC considerations, row-access policies",
      "Report findings with file paths and line numbers.",
    ].join("\n"),
  },
  "Security Review": {
    system: [
      "You are a Snowflake security expert reviewing code changes.",
      "Focus on:",
      "- Authentication: credential handling, token storage, connection security",
      "- Authorization: RBAC enforcement, role hierarchy, privilege escalation risks",
      "- Data governance: PII exposure, masking policy gaps, data classification",
      "- Row/column access policies: missing policies, policy bypass risks",
      "- Network security: network policy gaps, private link considerations",
      "- Secrets management: hardcoded credentials, key rotation, secret scoping",
      "- Audit: missing audit trails, share security, cross-account access",
      "Report only material security findings with file paths and line numbers.",
    ].join("\n"),
  },
};

const MAX_DIFF_CHARS = 500000; // ~500KB cap for prompt

function truncateDiff(diff) {
  if (!diff || diff.length <= MAX_DIFF_CHARS) return diff;
  const truncated = diff.slice(0, MAX_DIFF_CHARS);
  const lastNewline = truncated.lastIndexOf("\n");
  return (lastNewline > 0 ? truncated.slice(0, lastNewline) : truncated) +
    `\n\n[... diff truncated at ${MAX_DIFF_CHARS} chars, ${diff.length - MAX_DIFF_CHARS} chars omitted ...]`;
}

function buildReviewPrompt(reviewName, target, diff, focusText) {
  const preset = REVIEW_PRESETS[reviewName] || REVIEW_PRESETS["Review"];
  const parts = [preset.system];
  parts.push("Target: " + target.label);
  if (focusText) parts.push("Focus area: " + focusText);
  parts.push("\n--- Diff ---\n" + (truncateDiff(diff) || "(no diff available)"));
  return parts.join("\n");
}

// --- Task ---

async function handleTask(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["connection", "model", "effort", "cwd", "max-turns"],
    booleanOptions: ["json", "write", "background", "resume", "fresh"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const prompt = positionals.join(" ").trim();

  if (!prompt) throw new Error("Provide a prompt for the task.");

  const cortex = findCortexBinary();
  if (!cortex) throw new Error("Cortex Code CLI not found.");

  const jobId = generateJobId("task");
  const title = shorten(prompt);

  upsertJob(workspaceRoot, {
    id: jobId, kind: "task", title: `Cortex Task`, jobClass: "task",
    status: "running", summary: title, startedAt: nowIso(),
  });

  if (options.background) {
    const scriptPath = path.resolve(fileURLToPath(import.meta.url));
    const child = spawn(process.execPath, [scriptPath, "task-worker", "--cwd", cwd, "--job-id", jobId, "--prompt", prompt,
      ...(options.connection ? ["-c", options.connection] : []),
      ...(options.model ? ["-m", options.model] : []),
      ...(options.effort ? ["--effort", options.effort] : []),
      ...(options.write ? ["--write"] : []),
    ], { cwd, env: process.env, detached: true, stdio: "ignore", windowsHide: true });
    child.unref();

    upsertJob(workspaceRoot, { id: jobId, status: "queued", pid: child.pid });
    const payload = { jobId, status: "queued", title, summary: title };
    outputResult(options.json ? payload : `Cortex Task started in background as ${jobId}. Check /cortex-code:status for progress.\n`, options.json);
    return;
  }

  process.stderr.write(`[cortex] Running task...\n`);

  const cortexOptions = {
    connection: options.connection,
    model: options.model,
    effort: options.effort,
    workdir: cwd,
    timeout: 600000,
  };

  if (options.write) {
    cortexOptions.bypass = true;
  }

  const result = runCortex(prompt, cortexOptions);
  const completedAt = nowIso();
  const status = result.status === 0 ? "completed" : "failed";

  upsertJob(workspaceRoot, { id: jobId, status, completedAt, summary: shorten(result.stdout) });
  writeJobFile(workspaceRoot, jobId, {
    id: jobId, status, kind: "task", result: result.stdout, stderr: result.stderr, completedAt,
  });

  if (result.status !== 0) {
    process.stderr.write(`[cortex] Task failed: ${result.stderr}\n`);
    process.exitCode = result.status;
  }

  outputResult(options.json ? { jobId, status, result: result.stdout } : result.stdout + "\n", options.json);
}

async function handleTaskWorker(argv) {
  const { options } = parseCommandInput(argv, {
    valueOptions: ["cwd", "job-id", "prompt", "connection", "model", "effort"],
    booleanOptions: ["write"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const jobId = options["job-id"];
  const prompt = options.prompt;

  if (!jobId || !prompt) throw new Error("Missing --job-id or --prompt for task-worker.");

  upsertJob(workspaceRoot, { id: jobId, status: "running", startedAt: nowIso(), pid: process.pid });

  const cortexOptions = {
    connection: options.connection,
    model: options.model,
    effort: options.effort,
    workdir: cwd,
    timeout: 600000,
  };
  if (options.write) cortexOptions.bypass = true;

  const result = runCortex(prompt, cortexOptions);
  const completedAt = nowIso();
  const status = result.status === 0 ? "completed" : "failed";

  upsertJob(workspaceRoot, { id: jobId, status, completedAt, pid: null, summary: shorten(result.stdout) });
  writeJobFile(workspaceRoot, jobId, {
    id: jobId, status, kind: "task", result: result.stdout, stderr: result.stderr, completedAt,
  });
}

// --- Status ---

function handleStatus(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd"], booleanOptions: ["json", "all"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const jobs = listJobs(workspaceRoot);
  const reference = positionals[0];

  if (reference) {
    const job = jobs.find((j) => j.id === reference);
    if (!job) throw new Error(`Job ${reference} not found.`);
    outputResult(options.json ? job : renderJobDetail(job), options.json);
    return;
  }

  const running = jobs.filter((j) => j.status === "running" || j.status === "queued");
  const recent = jobs.filter((j) => j.status !== "running" && j.status !== "queued").slice(0, 5);

  const report = { running, recent };
  outputResult(options.json ? report : renderStatusReport(running, recent), options.json);
}

function renderJobDetail(job) {
  return [
    `# ${job.title || job.kind || "Job"} (${job.id})`,
    `Status: ${job.status}`,
    `Summary: ${job.summary || ""}`,
    job.startedAt ? `Started: ${job.startedAt}` : null,
    job.completedAt ? `Completed: ${job.completedAt}` : null,
  ].filter(Boolean).join("\n") + "\n";
}

function renderStatusReport(running, recent) {
  const lines = ["# Cortex Code Status\n"];

  if (running.length) {
    lines.push("Active jobs:");
    for (const j of running) lines.push(`  - ${j.id} | ${j.kind} | ${j.status} | ${j.summary || ""}`);
  } else {
    lines.push("No active jobs.");
  }

  if (recent.length) {
    lines.push("\nRecent:");
    for (const j of recent) lines.push(`  - ${j.id} | ${j.kind} | ${j.status} | ${j.summary || ""}`);
  }

  return lines.join("\n") + "\n";
}

// --- Result ---

function handleResult(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd"], booleanOptions: ["json"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const reference = positionals[0];
  const jobs = listJobs(workspaceRoot);

  let job;
  if (reference) {
    job = jobs.find((j) => j.id === reference);
  } else {
    job = jobs.find((j) => j.status === "completed" || j.status === "failed");
  }

  if (!job) throw new Error(reference ? `Job ${reference} not found.` : "No completed jobs found.");

  const jobFile = resolveJobFile(workspaceRoot, job.id);
  let stored = null;
  try { stored = readJobFile(jobFile); } catch { /* no stored data */ }

  const payload = { job, result: stored?.result || null, stderr: stored?.stderr || null };
  outputResult(options.json ? payload : (stored?.result || "No result stored.") + "\n", options.json);
}

// --- Cancel ---

function handleCancel(argv) {
  const { options, positionals } = parseCommandInput(argv, {
    valueOptions: ["cwd"], booleanOptions: ["json"],
  });

  const cwd = resolveCwd(options);
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  const reference = positionals[0];
  const jobs = listJobs(workspaceRoot);

  let job;
  if (reference) {
    job = jobs.find((j) => j.id === reference);
  } else {
    job = jobs.find((j) => j.status === "running" || j.status === "queued");
  }

  if (!job) throw new Error(reference ? `Job ${reference} not found.` : "No active jobs to cancel.");

  terminateProcessTree(job.pid);

  upsertJob(workspaceRoot, {
    id: job.id, status: "cancelled", pid: null, completedAt: nowIso(),
    errorMessage: "Cancelled by user.",
  });

  const payload = { jobId: job.id, status: "cancelled", title: job.title };
  outputResult(options.json ? payload : `Cancelled ${job.id} (${job.title || job.kind}).\n`, options.json);
}

// --- Main ---

async function main() {
  const [subcommand, ...argv] = process.argv.slice(2);
  if (!subcommand || subcommand === "help" || subcommand === "--help") { printUsage(); return; }

  switch (subcommand) {
    case "setup": handleSetup(argv); break;
    case "review": await handleReview(argv, "Review"); break;
    case "adversarial-review": await handleReview(argv, "Adversarial Review"); break;
    case "data-review": await handleReview(argv, "Data Review"); break;
    case "dbt-review": await handleReview(argv, "dbt Review"); break;
    case "sql-review": await handleReview(argv, "SQL Review"); break;
    case "security-review": await handleReview(argv, "Security Review"); break;
    case "task": await handleTask(argv); break;
    case "task-worker": await handleTaskWorker(argv); break;
    case "status": handleStatus(argv); break;
    case "result": handleResult(argv); break;
    case "cancel": handleCancel(argv); break;
    default: throw new Error(`Unknown subcommand: ${subcommand}`);
  }
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
