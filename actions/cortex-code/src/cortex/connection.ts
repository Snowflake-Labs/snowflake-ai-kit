import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export interface ConnectionConfig {
  account: string;
  user: string;
  privateKey?: string;
  apiKey?: string;
}

let cleanupRegistered = false;

function registerCleanupHandlers(): void {
  if (cleanupRegistered) return;
  cleanupRegistered = true;

  const emergencyCleanup = () => {
    cleanupConnection();
    process.exit(1);
  };

  process.on("SIGTERM", emergencyCleanup);
  process.on("SIGINT", emergencyCleanup);
}

export function setupSnowflakeConnection(config: ConnectionConfig): string {
  const connectionName = "cortex-code-action";
  const connectionsDir = path.join(os.homedir(), ".snowflake");
  const connectionsFile = path.join(connectionsDir, "connections.toml");

  fs.mkdirSync(connectionsDir, { recursive: true });

  let tomlContent: string;

  if (config.privateKey) {
    const keyPath = path.join(connectionsDir, "action_key.p8");
    fs.writeFileSync(keyPath, config.privateKey, { mode: 0o600 });

    tomlContent = `[${connectionName}]
account = "${config.account}"
user = "${config.user}"
authenticator = "SNOWFLAKE_JWT"
private_key_path = "${keyPath}"
`;
  } else if (config.apiKey) {
    tomlContent = `[${connectionName}]
account = "${config.account}"
user = "${config.user}"
token = "${config.apiKey}"
authenticator = "oauth"
`;
  } else {
    throw new Error(
      "Either snowflake_private_key or snowflake_api_key must be provided.",
    );
  }

  tomlContent += `\n[default]\ndefault_connection_name = "${connectionName}"\n`;

  fs.writeFileSync(connectionsFile, tomlContent, { mode: 0o600 });

  registerCleanupHandlers();

  return connectionName;
}

export function cleanupConnection(): void {
  const connectionsDir = path.join(os.homedir(), ".snowflake");
  const connectionsFile = path.join(connectionsDir, "connections.toml");
  const keyPath = path.join(connectionsDir, "action_key.p8");

  try {
    if (fs.existsSync(keyPath)) fs.unlinkSync(keyPath);
    if (fs.existsSync(connectionsFile)) fs.unlinkSync(connectionsFile);
  } catch {
    // Best effort cleanup
  }
}
