import { execSync, spawnSync } from "node:child_process";

export function binaryAvailable(name, args = ["--version"], options = {}) {
  try {
    const result = spawnSync(name, args, {
      cwd: options.cwd || process.cwd(),
      encoding: "utf8",
      timeout: 10000,
      stdio: ["ignore", "pipe", "pipe"],
    });
    if (result.status === 0) {
      return { available: true, detail: (result.stdout || "").trim().split("\n")[0] };
    }
    return { available: false, detail: (result.stderr || result.stdout || "").trim().split("\n")[0] };
  } catch {
    return { available: false, detail: `${name} not found` };
  }
}

export function runCommand(cmd, args, options = {}) {
  const result = spawnSync(cmd, args, {
    cwd: options.cwd || process.cwd(),
    encoding: "utf8",
    timeout: options.timeout || 600000,
    env: options.env || process.env,
    stdio: ["pipe", "pipe", "pipe"],
    input: options.input || undefined,
  });
  return {
    status: result.status ?? 1,
    stdout: (result.stdout || "").trim(),
    stderr: (result.stderr || "").trim(),
    error: result.error || null,
  };
}

export function terminateProcessTree(pid) {
  if (!pid || isNaN(pid)) return;
  try {
    process.kill(-pid, "SIGTERM");
  } catch {
    try {
      process.kill(pid, "SIGTERM");
    } catch {
      // already dead
    }
  }
}
