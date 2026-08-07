import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const DEFAULT_PAT_ENV = "SNOWFLAKE_PAT";
const SESSION_TOKEN_ENV_NAMES = ["CLOUD_AGENTS_SESSION_TOKEN", "SNOWFLAKE_TOKEN"];
const PAT_ENV_NAMES = ["CLOUD_AGENTS_PAT", "SNOWFLAKE_PAT"];
const AUTH_MODES = new Set(["auto", "coco", "env", "pat"]);
const INTERACTIVE_AUTHENTICATORS = new Set([
  "EXTERNALBROWSER",
  "OAUTH_AUTHORIZATION_CODE",
]);

const noopLogger = {
  debug() {},
  info() {},
  warning() {},
  warn() {},
  error() {},
};

const noopMetrics = {
  trackConnectionEstablish() {},
  trackConnectionError() {},
  trackConnectionTokenRefresh() {},
  trackConnectionSwitch() {},
};

export async function resolveCloudAgentsAuth(options = {}) {
  const authMode = normalizeAuthMode(options.authMode);
  const failures = [];

  if (options.sessionToken) {
    return sessionAuth(options.sessionToken, options.host, "explicit session token");
  }

  if (options.pat) {
    return patAuth(options.pat, options.host, "explicit PAT");
  }

  if (authMode !== "pat") {
    const envSession = resolveEnvSessionAuth(options);
    if (envSession) {
      return envSession;
    }
  }

  if (authMode === "auto" || authMode === "coco") {
    try {
      const cocoAuth = await resolveCocoConnectionAuth(options);
      if (cocoAuth) {
        return cocoAuth;
      }
    } catch (err) {
      const message = safeErrorMessage(err);
      if (authMode === "coco") {
        throw new Error(`CoCo connection auth failed: ${message}`);
      }
      failures.push(`CoCo connection auth failed: ${message}`);
    }
  }

  if (authMode !== "coco") {
    const envPat = resolveEnvPatAuth(options);
    if (envPat) {
      return envPat;
    }
  }

  throw missingAuthError(options, failures);
}

export function resolveEnvSessionAuth({ host } = {}) {
  const found = firstEnv(SESSION_TOKEN_ENV_NAMES);
  if (!found) {
    return null;
  }
  return sessionAuth(found.value, host, `env:${found.name}`);
}

export function resolveEnvPatAuth({ host, patEnv } = {}) {
  const envNames = unique([
    patEnv || process.env.CLOUD_AGENTS_PAT_ENV || DEFAULT_PAT_ENV,
    ...PAT_ENV_NAMES,
  ]);
  const found = firstEnv(envNames);
  if (!found) {
    return null;
  }
  return patAuth(found.value, host, `env:${found.name}`);
}

export async function resolveCocoConnectionAuth(options = {}) {
  if (isTruthy(process.env.CLOUD_AGENTS_DISABLE_COCO_CONNECTION)) {
    return null;
  }

  const modules = await loadCocoModules(options);
  if (!modules) {
    return null;
  }

  const connectionName = resolveConnectionName(options.connectionName);
  const core = modules.core;
  core.resetConnectionManager?.();

  const manager = core.initializeConnectionManager({
    activeConnectionName: connectionName,
    defaultApplication: "cortex_code_cli",
    logger: noopLogger,
    metrics: noopMetrics,
    sdk: modules.snowflakeSdk,
    ...(modules.credentialManager
      ? { credentialManager: modules.credentialManager }
      : {}),
    openExternalBrowserCallback: async () => {
      throw new Error(
        "interactive Snowflake auth is not supported by cloud-agents-mcp; " +
          "run CoCo once for this connection or set CLOUD_AGENTS_SESSION_TOKEN/SNOWFLAKE_TOKEN",
      );
    },
  });

  const conn = manager.createDedicatedConnection
    ? manager.createDedicatedConnection(connectionName)
    : manager.getConnection(connectionName);

  if (!conn) {
    return null;
  }

  assertNoUnsafeInteractiveCache(conn, modules.credentialManager);

  const timeoutMs = Number(process.env.CLOUD_AGENTS_COCO_CONNECT_TIMEOUT_MS || 30_000);
  await withTimeout(
    conn.connect(),
    timeoutMs,
    `timed out connecting to CoCo Snowflake connection '${conn.name}'`,
  );

  const token = conn.token;
  if (!token) {
    throw new Error(`CoCo Snowflake connection '${conn.name}' did not produce a session token`);
  }

  return sessionAuth(
    token,
    toHttpOrigin(conn.restUrl, conn.protocol || conn.config?.protocol),
    `coco:${conn.name}`,
    { connection: conn },
  );
}

async function loadCocoModules(options = {}) {
  const repos = candidateCocoRepos(options);
  const core = await importFirst(coreCandidates(options, repos));
  if (!core) {
    return null;
  }

  const snowflakeModule = await importFirst(snowflakeSdkCandidates(options, repos));
  if (!snowflakeModule) {
    throw new Error("found CoCo SDK but could not load snowflake-sdk");
  }

  const credentialManager = await loadCredentialManager(options, repos);
  const snowflakeSdk = snowflakeModule.module.default || snowflakeModule.module;
  configureSnowflakeSdk(snowflakeSdk, credentialManager);

  return {
    core: core.module,
    snowflakeSdk,
    credentialManager,
  };
}

async function loadCredentialManager(options, repos) {
  const imported = await importFirst(secretManagerCandidates(options, repos));
  if (!imported?.module?.getSecretsCredentialManager) {
    return undefined;
  }
  try {
    return imported.module.getSecretsCredentialManager() || undefined;
  } catch {
    return undefined;
  }
}

function coreCandidates(options, repos) {
  const candidates = [];
  pushCandidate(candidates, options.cocoSdkModule);
  pushCandidate(candidates, process.env.CLOUD_AGENTS_COCO_SDK_MODULE);

  for (const repo of repos) {
    pushCandidate(
      candidates,
      path.join(repo, "node_modules", "@coco-sdk", "core", "dist", "index.js"),
    );
    pushCandidate(
      candidates,
      path.resolve(repo, "..", "..", "cortexcode", "packages", "sdk", "dist", "index.js"),
    );
  }

  pushCandidate(candidates, "@coco-sdk/core");
  return candidates;
}

function snowflakeSdkCandidates(options, repos) {
  const candidates = [];
  pushCandidate(candidates, options.snowflakeSdkModule);
  pushCandidate(candidates, process.env.CLOUD_AGENTS_SNOWFLAKE_SDK_MODULE);

  for (const repo of repos) {
    pushCandidate(candidates, path.join(repo, "node_modules", "snowflake-sdk", "dist", "index.js"));
  }

  pushCandidate(candidates, "snowflake-sdk");
  return candidates;
}

function secretManagerCandidates(options, repos) {
  const candidates = [];
  pushCandidate(candidates, options.cocoSecretsModule);
  pushCandidate(candidates, process.env.CLOUD_AGENTS_COCO_SECRETS_MODULE);

  for (const repo of repos) {
    pushCandidate(candidates, path.join(repo, "dist", "services", "secretsCredentialManager.js"));
  }

  return candidates;
}

function candidateCocoRepos(options) {
  const candidates = [];
  pushCandidate(candidates, options.cocoRepo);
  for (const name of ["CLOUD_AGENTS_COCO_REPO", "COCO_REPO", "CORTEX_CODE_CLI_REPO"]) {
    for (const value of splitPathEnv(process.env[name])) {
      pushCandidate(candidates, value);
    }
  }

  // Common checkout locations
  pushCandidate(
    candidates,
    path.join(os.homedir(), "Documents", "Code", "cortex", "cortexagent", "codingagent", "coco"),
  );
  pushCandidate(
    candidates,
    path.join(os.homedir(), "Documents", "Code", "cortex-master", "cortexagent", "codingagent", "coco"),
  );

  return unique(candidates.map(expandTilde));
}

async function importFirst(candidates) {
  for (const candidate of unique(candidates.filter(Boolean))) {
    const specifier = toImportSpecifier(candidate);
    if (!specifier) {
      continue;
    }
    try {
      return { module: await import(specifier), specifier };
    } catch {
      // Keep trying
    }
  }
  return null;
}

function toImportSpecifier(candidate) {
  if (!candidate) {
    return null;
  }
  if (candidate.startsWith("file://")) {
    return candidate;
  }
  if (candidate.startsWith(".") || candidate.startsWith("/") || candidate.startsWith("~")) {
    const fullPath = expandTilde(candidate);
    if (!fs.existsSync(fullPath)) {
      return null;
    }
    const stat = fs.statSync(fullPath);
    const filePath = stat.isDirectory() ? path.join(fullPath, "dist", "index.js") : fullPath;
    if (!fs.existsSync(filePath)) {
      return null;
    }
    return pathToFileURL(filePath).href;
  }
  return candidate;
}

function assertNoUnsafeInteractiveCache(conn, credentialManager) {
  if (credentialManager || isTruthy(process.env.CLOUD_AGENTS_ALLOW_SDK_FILE_CREDENTIAL_CACHE)) {
    return;
  }

  const authenticator = conn.config?.authenticator?.toUpperCase();
  if (INTERACTIVE_AUTHENTICATORS.has(authenticator)) {
    throw new Error(
      `CoCo connection '${conn.name}' uses ${authenticator}, but the CoCo keychain credential manager is unavailable. ` +
        "Set CLOUD_AGENTS_COCO_REPO to a built CoCo checkout, set CLOUD_AGENTS_SESSION_TOKEN/SNOWFLAKE_TOKEN, or set SNOWFLAKE_PAT.",
    );
  }
}

function configureSnowflakeSdk(snowflakeSdk, credentialManager) {
  if (!snowflakeSdk?.configure) {
    return;
  }
  try {
    snowflakeSdk.configure({
      logLevel: "OFF",
      ...(credentialManager ? { customCredentialManager: credentialManager } : {}),
    });
  } catch {
    // Don't write errors to stdout — stdio MCP uses stdout for JSON-RPC frames
  }
}

function sessionAuth(token, host, source, extra = {}) {
  return { kind: "session", token, host, source, ...extra };
}

function patAuth(pat, host, source) {
  return { kind: "pat", pat, host, source };
}

function missingAuthError(options, failures) {
  const patEnv = options.patEnv || process.env.CLOUD_AGENTS_PAT_ENV || DEFAULT_PAT_ENV;
  const parts = [
    "No Snowflake auth available.",
    "Tried CLOUD_AGENTS_SESSION_TOKEN/SNOWFLAKE_TOKEN, the CoCo CLI connection, and PAT env fallback.",
    `Set CLOUD_AGENTS_CONNECTION to choose a CoCo connection, or set ${patEnv}, CLOUD_AGENTS_PAT, or SNOWFLAKE_PAT.`,
  ];
  if (failures.length) {
    parts.push(`Last auth detail: ${failures.at(-1)}`);
  }
  return new Error(parts.join(" "));
}

function firstEnv(names) {
  for (const name of unique(names)) {
    if (name && process.env[name]) {
      return { name, value: process.env[name] };
    }
  }
  return null;
}

function normalizeAuthMode(value) {
  const mode = (value || process.env.CLOUD_AGENTS_AUTH_MODE || "auto").toLowerCase();
  if (!AUTH_MODES.has(mode)) {
    throw new Error(
      `Invalid CLOUD_AGENTS_AUTH_MODE '${mode}'. Expected one of: ${[...AUTH_MODES].join(", ")}`,
    );
  }
  return mode;
}

function resolveConnectionName(value) {
  return (
    value ||
    process.env.CLOUD_AGENTS_CONNECTION ||
    process.env.CORTEX_CONNECTION ||
    process.env.SNOWFLAKE_CONNECTION ||
    undefined
  );
}

function toHttpOrigin(host, protocol = "https") {
  if (!host) {
    return undefined;
  }
  const value = host.replace(/\/+$/, "");
  if (/^https?:\/\//i.test(value)) {
    return value;
  }
  return `${protocol}://${value}`;
}

function withTimeout(promise, timeoutMs, message) {
  let timeout;
  const timeoutPromise = new Promise((_, reject) => {
    timeout = setTimeout(() => reject(new Error(message)), timeoutMs);
  });
  return Promise.race([promise, timeoutPromise]).finally(() => clearTimeout(timeout));
}

function splitPathEnv(value) {
  return value ? value.split(path.delimiter).filter(Boolean) : [];
}

function pushCandidate(candidates, value) {
  if (value) {
    candidates.push(value);
  }
}

function expandTilde(value) {
  return value?.startsWith("~") ? path.join(os.homedir(), value.slice(1)) : value;
}

function unique(values) {
  return [...new Set(values.filter(Boolean))];
}

function isTruthy(value) {
  return /^(1|true|yes|on)$/i.test(String(value || ""));
}

function safeErrorMessage(err) {
  const raw = err?.message ? String(err.message) : String(err);
  return raw
    .replace(/Snowflake Token="[^"]+"/g, 'Snowflake Token="<redacted>"')
    .replace(/Bearer\s+[A-Za-z0-9._~+/-]+=*/g, "Bearer <redacted>")
    .replace(/token[=:]\s*[A-Za-z0-9._~+/-]+=*/gi, "token=<redacted>");
}
