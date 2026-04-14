import { execSync } from "node:child_process";
import process from "node:process";

export function resolveWorkspaceRoot(cwd) {
  try {
    return execSync("git rev-parse --show-toplevel", { cwd: cwd || process.cwd(), encoding: "utf8" }).trim();
  } catch {
    return cwd || process.cwd();
  }
}
