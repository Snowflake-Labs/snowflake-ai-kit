import { DEFAULT_HOST, buildRunRequest } from "./request-builder.mjs";
import { parseSseStream } from "./sse.mjs";
import { resolveCloudAgentsAuth } from "./auth.mjs";

export class CloudAgentHttpError extends Error {
  constructor(message, { status, body }) {
    super(message);
    this.name = "CloudAgentHttpError";
    this.status = status;
    this.body = body;
  }
}

export class SnowflakeAgentClient {
  constructor({
    host = process.env.CLOUD_AGENTS_HOST ||
      process.env.SNOWFLAKE_HOST ||
      DEFAULT_HOST,
    pat,
    patEnv = process.env.CLOUD_AGENTS_PAT_ENV || "PAT_SNOWHOUSE",
    fetchImpl = globalThis.fetch,
    sessionToken,
    authMode = process.env.CLOUD_AGENTS_AUTH_MODE || "auto",
    connectionName = process.env.CLOUD_AGENTS_CONNECTION,
    authResolver = resolveCloudAgentsAuth,
  } = {}) {
    if (!fetchImpl) {
      throw new Error("global fetch is not available; use Node 20+");
    }
    this.host = host.replace(/\/+$/, "");
    this.pat = pat;
    this.patEnv = patEnv;
    this.fetchImpl = fetchImpl;
    this.sessionToken = sessionToken;
    this.authMode = authMode;
    this.connectionName = connectionName;
    this.authResolver = authResolver;
  }

  async getSessionToken() {
    if (this.sessionToken) {
      return this.sessionToken;
    }

    const auth = await this.authResolver({
      authMode: this.authMode,
      connectionName: this.connectionName,
      host: this.host,
      pat: this.pat,
      patEnv: this.patEnv,
      sessionToken: this.sessionToken,
    });

    if (auth.host) {
      this.host = normalizeHost(auth.host);
    }

    if (auth.kind === "session") {
      this.sessionToken = auth.token;
      return this.sessionToken;
    }

    if (auth.kind !== "pat") {
      throw new Error(`Unsupported auth kind: ${auth.kind}`);
    }

    const resp = await this.fetchImpl(`${this.host}/api/v2/sessions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${auth.pat}`,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: "{}",
      signal: AbortSignal.timeout(30_000),
    });
    if (!resp.ok) {
      throw await httpError(resp, "PAT to session token exchange");
    }
    const payload = await resp.json();
    if (!payload.token) {
      throw new Error("session response did not include token");
    }
    this.sessionToken = payload.token;
    return this.sessionToken;
  }

  async createThread() {
    const token = await this.getSessionToken();
    const resp = await this.fetchImpl(`${this.host}/api/v2/cortex/threads`, {
      method: "POST",
      headers: authHeaders(token),
      body: "{}",
      signal: AbortSignal.timeout(30_000),
    });
    if (!resp.ok) {
      throw await httpError(resp, "create thread");
    }
    const payload = await resp.json();
    if (!payload.thread_id) {
      throw new Error("create thread response did not include thread_id");
    }
    return Number(payload.thread_id);
  }

  async deleteThread(threadId) {
    const token = await this.getSessionToken();
    const resp = await this.fetchImpl(
      `${this.host}/api/v2/cortex/threads/${threadId}`,
      {
        method: "DELETE",
        headers: authHeaders(token),
        signal: AbortSignal.timeout(30_000),
      },
    );
    if (!resp.ok) {
      throw await httpError(resp, "delete thread");
    }
  }

  async *streamAgentRun(body, { signal } = {}) {
    const token = await this.getSessionToken();
    const resp = await this.fetchImpl(`${this.host}/api/v2/cortex/agent:run`, {
      method: "POST",
      headers: {
        ...authHeaders(token),
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
      signal,
    });
    if (!resp.ok) {
      throw await httpError(resp, "agent:run");
    }
    if (!resp.body) {
      throw new Error("agent:run response did not include a stream body");
    }
    yield* parseSseStream(resp.body);
  }

  async cancelAgentRun(runId) {
    if (!runId) {
      return null;
    }
    const token = await this.getSessionToken();
    const resp = await this.fetchImpl(
      `${this.host}/api/v2/cortex/agent/runs/${encodeURIComponent(runId)}/cancel`,
      {
        method: "POST",
        headers: authHeaders(token),
        body: "{}",
        signal: AbortSignal.timeout(30_000),
      },
    );
    if (!resp.ok) {
      throw await httpError(resp, "cancel agent run");
    }
    return resp.json();
  }

  buildRunRequest(options) {
    return buildRunRequest(options);
  }
}

function authHeaders(token) {
  return {
    Authorization: `Snowflake Token="${token}"`,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

async function httpError(resp, label) {
  const body = truncate(await resp.text().catch(() => ""), 800);
  return new CloudAgentHttpError(
    `${label} failed: HTTP ${resp.status}: ${body}`,
    {
      status: resp.status,
      body,
    },
  );
}

function truncate(value, max) {
  return value.length > max ? `${value.slice(0, max)}...` : value;
}

function normalizeHost(host) {
  return host.replace(/\/+$/, "");
}
