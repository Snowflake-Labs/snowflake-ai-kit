#!/usr/bin/env node

// Snowflake AI Kit — npx entry point
// Detects platform and delegates to install.sh or install.ps1

import { execSync } from "child_process";
import { platform } from "os";

const REPO_RAW =
  "https://raw.githubusercontent.com/Snowflake-Labs/snowflake-ai-kit/main";

const os = platform();
const args = process.argv.slice(2).join(" ");

try {
  if (os === "win32") {
    console.log("Detected Windows — running PowerShell installer...");
    execSync(
      `powershell -Command "irm ${REPO_RAW}/install.ps1 | iex" ${args}`,
      { stdio: "inherit" }
    );
  } else {
    console.log("Detected Unix — running bash installer...");
    execSync(
      `bash <(curl -sSL ${REPO_RAW}/install.sh) ${args}`,
      { stdio: "inherit", shell: "/bin/bash" }
    );
  }
} catch (e) {
  process.exit(e.status || 1);
}
