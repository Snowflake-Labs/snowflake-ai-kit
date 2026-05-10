import * as core from "@actions/core";

export async function installCortexCLI(): Promise<string> {
  // The CLI is installed in the composite action step via the install script.
  // This function verifies it's accessible and returns the path.
  const cliPath = process.env.CORTEX_CODE_CLI_PATH ?? "cortex";

  try {
    const proc = Bun.spawn([cliPath, "--version"], {
      stdout: "pipe",
      stderr: "pipe",
    });
    const exitCode = await proc.exited;
    if (exitCode !== 0) {
      throw new Error(`cortex --version exited with code ${exitCode}`);
    }
    const version = await new Response(proc.stdout).text();
    core.info(`Cortex Code CLI version: ${version.trim()}`);
    return cliPath;
  } catch (error) {
    throw new Error(
      `Cortex Code CLI not found or not functional. ` +
        `Ensure it's installed: curl -LsS https://ai.snowflake.com/static/cc-scripts/install.sh | sh\n` +
        `Error: ${error}`,
    );
  }
}
