#!/usr/bin/env node

// Snowflake AI Kit — npx entry point
// Detects platform and delegates to install.sh or install.ps1

import { spawnSync } from "child_process";
import { mkdtempSync, realpathSync, writeFileSync } from "fs";
import { platform, tmpdir } from "os";
import { join } from "path";
import { pathToFileURL } from "url";

const REPO_RAW =
  "https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main";

// Installer flags and their install.ps1 switches. Anything else is rejected.
const FLAGS = {
  "--check": "-Check",
  "--with-claude": "-WithClaude",
  "--with-codex": "-WithCodex",
  "--include-aim": "-IncludeAim",
  "--help": "-Help",
};

export function installPlan(os, argv) {
  for (const arg of argv) {
    if (!(arg in FLAGS)) {
      throw new Error(`Unknown option: ${arg}. Use one of: ${Object.keys(FLAGS).join(", ")}`);
    }
  }
  if (os === "win32") {
    return { file: "install.ps1", args: argv.map((arg) => FLAGS[arg]) };
  }
  return { file: "install.sh", args: argv };
}

async function main() {
  let plan;
  try {
    plan = installPlan(platform(), process.argv.slice(2));
  } catch (e) {
    console.error(e.message);
    process.exit(2);
  }

  const response = await fetch(`${REPO_RAW}/${plan.file}`);
  if (!response.ok) {
    console.error(`Could not download ${plan.file}: HTTP ${response.status}`);
    process.exit(1);
  }
  const script = join(mkdtempSync(join(tmpdir(), "snowflake-ai-kit-")), plan.file);
  writeFileSync(script, await response.text());

  const windows = plan.file === "install.ps1";
  console.log(`Detected ${windows ? "Windows" : "Unix"} — running ${plan.file}...`);
  const result = windows
    ? spawnSync("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, ...plan.args], { stdio: "inherit" })
    : spawnSync("bash", [script, ...plan.args], { stdio: "inherit" });
  process.exit(result.status ?? 1);
}

// npx runs bins through a symlink, so compare real paths.
function isEntryPoint() {
  try {
    return import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href;
  } catch {
    return false;
  }
}

if (isEntryPoint()) {
  main();
}
