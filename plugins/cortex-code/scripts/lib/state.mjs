import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

import { resolveWorkspaceRoot } from "./workspace.mjs";

const STATE_VERSION = 1;
const PLUGIN_DATA_ENV = "CLAUDE_PLUGIN_DATA";
const CORTEX_STATE_DIR = path.join(os.homedir(), ".snowflake", "cortex", "plugins", "cortex-code");
const FALLBACK_STATE_ROOT_DIR = path.join(os.tmpdir(), "cortex-code-companion");
const STATE_FILE_NAME = "state.json";
const JOBS_DIR_NAME = "jobs";
const MAX_JOBS = 50;

function nowIso() { return new Date().toISOString(); }

function defaultState() {
  return { version: STATE_VERSION, config: {}, jobs: [] };
}

export function resolveStateDir(cwd) {
  const workspaceRoot = resolveWorkspaceRoot(cwd);
  let canonicalRoot = workspaceRoot;
  try { canonicalRoot = fs.realpathSync.native(workspaceRoot); } catch { /* use original */ }

  const slug = (path.basename(workspaceRoot) || "workspace").replace(/[^a-zA-Z0-9._-]+/g, "-").replace(/^-+|-+$/g, "") || "workspace";
  const hash = createHash("sha256").update(canonicalRoot).digest("hex").slice(0, 16);
  const pluginDataDir = process.env[PLUGIN_DATA_ENV];
  const stateRoot = pluginDataDir ? path.join(pluginDataDir, "state") : path.join(CORTEX_STATE_DIR, "state");
  return path.join(stateRoot, `${slug}-${hash}`);
}

export function resolveJobsDir(cwd) { return path.join(resolveStateDir(cwd), JOBS_DIR_NAME); }
export function ensureStateDir(cwd) { fs.mkdirSync(resolveJobsDir(cwd), { recursive: true }); }

export function loadState(cwd) {
  const stateFile = path.join(resolveStateDir(cwd), STATE_FILE_NAME);
  if (!fs.existsSync(stateFile)) return defaultState();
  try {
    const parsed = JSON.parse(fs.readFileSync(stateFile, "utf8"));
    return { ...defaultState(), ...parsed, config: { ...defaultState().config, ...(parsed.config ?? {}) }, jobs: Array.isArray(parsed.jobs) ? parsed.jobs : [] };
  } catch { return defaultState(); }
}

export function saveState(cwd, state) {
  ensureStateDir(cwd);
  const nextJobs = [...(state.jobs ?? [])].sort((a, b) => String(b.updatedAt ?? "").localeCompare(String(a.updatedAt ?? ""))).slice(0, MAX_JOBS);
  const nextState = { version: STATE_VERSION, config: { ...defaultState().config, ...(state.config ?? {}) }, jobs: nextJobs };
  fs.writeFileSync(path.join(resolveStateDir(cwd), STATE_FILE_NAME), `${JSON.stringify(nextState, null, 2)}\n`, "utf8");
  return nextState;
}

export function updateState(cwd, mutate) {
  const state = loadState(cwd);
  mutate(state);
  return saveState(cwd, state);
}

export function generateJobId(prefix = "job") {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export function upsertJob(cwd, jobPatch) {
  return updateState(cwd, (state) => {
    const ts = nowIso();
    const idx = state.jobs.findIndex((j) => j.id === jobPatch.id);
    if (idx === -1) { state.jobs.unshift({ createdAt: ts, updatedAt: ts, ...jobPatch }); return; }
    state.jobs[idx] = { ...state.jobs[idx], ...jobPatch, updatedAt: ts };
  });
}

export function listJobs(cwd) { return loadState(cwd).jobs; }
export function getConfig(cwd) { return loadState(cwd).config; }
export function setConfig(cwd, key, value) { return updateState(cwd, (s) => { s.config = { ...s.config, [key]: value }; }); }

export function resolveJobFile(cwd, jobId) { ensureStateDir(cwd); return path.join(resolveJobsDir(cwd), `${jobId}.json`); }
export function resolveJobLogFile(cwd, jobId) { ensureStateDir(cwd); return path.join(resolveJobsDir(cwd), `${jobId}.log`); }

export function writeJobFile(cwd, jobId, payload) {
  ensureStateDir(cwd);
  const f = resolveJobFile(cwd, jobId);
  fs.writeFileSync(f, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  return f;
}

export function readJobFile(jobFile) { return JSON.parse(fs.readFileSync(jobFile, "utf8")); }
