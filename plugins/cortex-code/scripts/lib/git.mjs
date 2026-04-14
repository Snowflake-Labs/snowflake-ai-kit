import { execSync } from "node:child_process";

function gitRoot(cwd) {
  try {
    return execSync("git rev-parse --show-toplevel", { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
  } catch {
    return cwd;
  }
}

export function ensureGitRepository(cwd) {
  try {
    execSync("git rev-parse --is-inside-work-tree", { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  } catch {
    throw new Error("Not inside a git repository.");
  }
}

export function resolveReviewTarget(cwd, options = {}) {
  const root = gitRoot(cwd);
  const base = options.base;
  const scope = options.scope || "auto";

  if (scope === "branch" || base) {
    const baseRef = base || getDefaultBranch(root);
    return { mode: "branch", baseRef, label: `branch diff against ${baseRef}` };
  }

  if (scope === "working-tree") {
    return { mode: "working-tree", label: "working tree diff" };
  }

  // auto: use branch if there are commits, otherwise working tree
  const defaultBranch = getDefaultBranch(root);
  try {
    const log = execSync(`git log ${defaultBranch}..HEAD --oneline`, { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
    if (log) return { mode: "branch", baseRef: defaultBranch, label: `branch diff against ${defaultBranch}` };
  } catch { /* fall through */ }

  return { mode: "working-tree", label: "working tree diff" };
}

function getDefaultBranch(cwd) {
  // Prefer origin/ refs to avoid stale local branches (common in worktree setups)
  try {
    const ref = execSync("git symbolic-ref refs/remotes/origin/HEAD", { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }).trim();
    return ref.replace("refs/remotes/", "");  // returns "origin/main" or "origin/master"
  } catch { /* no symbolic ref */ }

  // Check if origin/main or origin/master exist
  for (const candidate of ["origin/master", "origin/main"]) {
    try {
      execSync(`git rev-parse --verify ${candidate}`, { cwd, encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
      return candidate;
    } catch { /* not found */ }
  }

  return "main";
}

const MAX_DIFF_BYTES = 50 * 1024 * 1024; // 50MB buffer

export function collectReviewDiff(cwd, target) {
  const root = gitRoot(cwd);
  try {
    if (target.mode === "branch") {
      // Use two-dot (..) not three-dot (...) -- we want commits on HEAD not on base
      return execSync(`git diff ${target.baseRef}..HEAD`, { cwd: root, encoding: "utf8", maxBuffer: MAX_DIFF_BYTES }).trim();
    }
    // working tree: staged + unstaged
    const staged = execSync("git diff --cached", { cwd: root, encoding: "utf8", maxBuffer: MAX_DIFF_BYTES }).trim();
    const unstaged = execSync("git diff", { cwd: root, encoding: "utf8", maxBuffer: MAX_DIFF_BYTES }).trim();
    return [staged, unstaged].filter(Boolean).join("\n");
  } catch (err) {
    process.stderr.write(`[cortex] Warning: diff collection failed: ${err.message?.split("\n")[0] || err}\n`);
    return "";
  }
}

export function getGitStatus(cwd) {
  const root = gitRoot(cwd);
  try {
    return execSync("git status --short", { cwd: root, encoding: "utf8" }).trim();
  } catch { return ""; }
}

export function getDiffStat(cwd, target) {
  const root = gitRoot(cwd);
  try {
    if (target.mode === "branch") {
      return execSync(`git diff --shortstat ${target.baseRef}...HEAD`, { cwd: root, encoding: "utf8" }).trim();
    }
    const staged = execSync("git diff --shortstat --cached", { cwd: root, encoding: "utf8" }).trim();
    const unstaged = execSync("git diff --shortstat", { cwd: root, encoding: "utf8" }).trim();
    return [staged, unstaged].filter(Boolean).join("; ");
  } catch { return ""; }
}
