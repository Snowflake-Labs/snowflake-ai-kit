import { EventEmitter } from "node:events";
import crypto from "node:crypto";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled", "closed"]);
const ACTIVE_STATUSES = new Set(["starting", "running", "queued", "cancel_requested"]);

export class AgentManager {
  constructor({ client, store, maxEventsPerAgent = 10_000 } = {}) {
    if (!client) {
      throw new Error("client is required");
    }
    if (!store) {
      throw new Error("store is required");
    }
    this.client = client;
    this.store = store;
    this.maxEventsPerAgent = maxEventsPerAgent;
    this.agents = new Map();
    this.eventBuffers = new Map();
    this.runtimes = new Map();
    this.emitter = new EventEmitter();
    this.emitter.setMaxListeners(1000);
  }

  async init() {
    await this.store.init();
    for (const record of await this.store.loadRecords()) {
      const restored = { ...record };
      if (ACTIVE_STATUSES.has(restored.status)) {
        restored.status = "unknown";
        restored.updated_at = nowIso();
        await this.store.upsertRecord(restored);
      }
      this.agents.set(restored.agent_id, restored);
      this.eventBuffers.set(
        restored.agent_id,
        await this.store.loadEvents(restored.agent_id),
      );
    }
  }

  async spawn(input) {
    requirePrompt(input?.prompt);
    const agentId = `ca_${crypto.randomUUID().replaceAll("-", "").slice(0, 24)}`;
    const timestamp = nowIso();
    const record = {
      agent_id: agentId,
      status: "starting",
      thread_id: null,
      parent_message_id: 0,
      run_id: null,
      created_at: timestamp,
      updated_at: timestamp,
      model: input.model || "auto",
      workspace: normalizeWorkspace(input.workspace),
      mcp_servers: normalizeMcpServers(input.mcp_servers),
      system_prompt: input.system_prompt || "",
      metadata: input.metadata ?? {},
      prompt_preview: preview(input.prompt),
      queued_inputs: [],
      last_sequence: 0,
    };
    this.agents.set(agentId, record);
    this.eventBuffers.set(agentId, []);
    await this.store.upsertRecord(record);
    this.#emitChange();
    this.#startWorker(agentId, input.prompt);
    return this.#publicRecord(record, { non_blocking: true });
  }

  async sendInput(input) {
    const record = this.#getAgent(input?.agent_id);
    requirePrompt(input?.prompt);
    if (record.status === "closed") {
      throw new Error(`agent ${record.agent_id} is closed`);
    }

    const runtime = this.runtimes.get(record.agent_id);
    const item = {
      prompt: input.prompt,
      created_at: nowIso(),
    };

    if (runtime) {
      if (input.interrupt) {
        record.queued_inputs.unshift(item);
        record.status = "cancel_requested";
        runtime.interrupted = true;
        void this.#cancelRemoteRun(record);
        runtime.abortController?.abort();
      } else {
        record.queued_inputs.push(item);
      }
      record.updated_at = nowIso();
      await this.store.upsertRecord(record);
      this.#emitChange();
      return {
        agent_id: record.agent_id,
        queued: true,
        status: record.status,
        non_blocking: true,
      };
    }

    record.status = "queued";
    record.updated_at = nowIso();
    await this.store.upsertRecord(record);
    this.#emitChange();
    this.#startWorker(record.agent_id, input.prompt);
    return {
      agent_id: record.agent_id,
      queued: false,
      status: record.status,
      non_blocking: true,
    };
  }

  async output({
    agent_id: agentId,
    since_sequence: sinceSequence = 0,
    limit = 200,
    include_raw_events: includeRawEvents = false,
  } = {}) {
    const record = this.#getAgent(agentId);
    const events = (this.eventBuffers.get(agentId) ?? [])
      .filter((event) => event.sequence > sinceSequence)
      .slice(0, limit)
      .map((event) => (includeRawEvents ? event : stripRaw(event)));
    const deltaText = events
      .filter((event) => event.type === "text_delta")
      .map((event) => event.text)
      .join("");
    const finalText = events
      .filter((event) => event.type === "response" && event.text)
      .map((event) => event.text)
      .join("");
    return {
      agent_id: agentId,
      status: record.status,
      thread_id: record.thread_id,
      parent_message_id: record.parent_message_id ?? 0,
      next_sequence:
        events.length > 0 ? events[events.length - 1].sequence : sinceSequence,
      events,
      text: deltaText || finalText,
      non_blocking: true,
    };
  }

  async status({ agent_ids: agentIds } = {}) {
    const ids = agentIds?.length ? agentIds : [...this.agents.keys()];
    return {
      agents: ids.map((id) => this.#publicRecord(this.#getAgent(id))),
      non_blocking: true,
    };
  }

  async list({ status, limit = 50 } = {}) {
    const agents = [...this.agents.values()]
      .filter((agent) => !status || agent.status === status)
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .slice(0, limit)
      .map((agent) => this.#publicRecord(agent));
    return { agents, non_blocking: true };
  }

  async wait({
    agent_ids: agentIds,
    condition = "terminal",
    timeout_ms: timeoutMs = 30_000,
    include_output: includeOutput = true,
    mode = "any",
    since_sequence: sinceSequence = 0,
  } = {}) {
    if (!Array.isArray(agentIds) || agentIds.length === 0) {
      throw new Error("agent_ids must be a non-empty array");
    }
    const deadline = Date.now() + timeoutMs;
    while (true) {
      const matched = agentIds
        .map((id) => this.#getAgent(id))
        .filter((record) => conditionMet(record, condition));
      const satisfied = mode === "all" ? matched.length === agentIds.length : matched.length > 0;
      if (satisfied) {
        return {
          completed: includeOutput
            ? await Promise.all(
                matched.map(async (record) => ({
                  ...this.#publicRecord(record),
                  output: await this.output({
                    agent_id: record.agent_id,
                    since_sequence: sinceSequence,
                    limit: 1_000,
                  }),
                })),
              )
            : matched.map((record) => this.#publicRecord(record)),
          timed_out: [],
          blocked: true,
        };
      }

      const remaining = deadline - Date.now();
      if (remaining <= 0) {
        return {
          completed: [],
          timed_out: agentIds.map((id) => this.#publicRecord(this.#getAgent(id))),
          blocked: true,
        };
      }
      await this.#waitForChange(Math.min(remaining, 1_000));
    }
  }

  async close({
    agent_id: agentId,
    cancel_active_run: cancelActiveRun = true,
    delete_thread: deleteThread = false,
    wait_for_cancel_ms: waitForCancelMs = 0,
  } = {}) {
    const record = this.#getAgent(agentId);
    const previousStatus = record.status;
    record.status = "closing";
    record.status_before_close = ACTIVE_STATUSES.has(previousStatus)
      ? "cancelled"
      : previousStatus;
    record.updated_at = nowIso();
    await this.store.upsertRecord(record);
    if (cancelActiveRun) {
      const runtime = this.runtimes.get(agentId);
      await this.#cancelRemoteRun(record);
      runtime?.abortController?.abort();
    }
    if (deleteThread && record.thread_id) {
      // The remote thread is gone, so this handle can never be reactivated.
      record.thread_deleted = true;
      void this.client.deleteThread(record.thread_id).catch((err) => {
        void this.#appendEvent(record, {
          type: "error",
          category: "delete_thread_error",
          message: redactError(err),
        });
      });
    }
    if (waitForCancelMs > 0) {
      await this.wait({
        agent_ids: [agentId],
        condition: "terminal",
        timeout_ms: waitForCancelMs,
        include_output: false,
      });
    }
    record.status = "closed";
    record.updated_at = nowIso();
    await this.store.upsertRecord(record);
    this.#emitChange();
    return {
      agent_id: agentId,
      previous_status: previousStatus,
      status: record.status,
      non_blocking: waitForCancelMs <= 0,
    };
  }

  async resume({
    agent_id: agentId,
    thread_id: threadId,
    parent_message_id: parentMessageId,
  } = {}) {
    if (agentId && this.agents.has(agentId)) {
      const existing = this.agents.get(agentId);
      if (existing.status !== "closed") {
        return this.#publicRecord(existing, { resumed: true, reactivated: false });
      }

      // A closed handle whose remote thread was deleted cannot be continued.
      // Fail loudly instead of reporting a success that leaves it unusable.
      if (existing.thread_deleted || !existing.thread_id) {
        throw new Error(
          `agent ${agentId} was closed with delete_thread and cannot be resumed; ` +
            "its remote thread no longer exists. Spawn a new agent instead.",
        );
      }

      existing.status = existing.status_before_close ?? "completed";
      existing.run_id = null;
      existing.updated_at = nowIso();
      await this.store.upsertRecord(existing);
      await this.#appendEvent(existing, {
        type: "status",
        status: existing.status,
        text: `Handle reactivated on thread ${existing.thread_id}; accepting input again.`,
      });
      this.#emitChange();
      return this.#publicRecord(existing, { resumed: true, reactivated: true });
    }
    if (!threadId) {
      throw new Error("thread_id is required when agent_id is unknown");
    }
    const newAgentId =
      agentId || `ca_${crypto.randomUUID().replaceAll("-", "").slice(0, 24)}`;
    const timestamp = nowIso();
    const record = {
      agent_id: newAgentId,
      status: "unknown",
      thread_id: Number(threadId),
      // Without a parent id the next turn branches from the thread root, so
      // let callers supply the last assistant message id to continue in place.
      parent_message_id: Number(parentMessageId ?? 0),
      run_id: null,
      created_at: timestamp,
      updated_at: timestamp,
      model: "auto",
      workspace: { mode: "unknown" },
      mcp_servers: [],
      system_prompt: "",
      metadata: {},
      prompt_preview: "",
      queued_inputs: [],
      last_sequence: 0,
    };
    this.agents.set(newAgentId, record);
    this.eventBuffers.set(newAgentId, []);
    await this.store.upsertRecord(record);
    this.#emitChange();
    return this.#publicRecord(record, { resumed: true, reactivated: false });
  }

  #startWorker(agentId, prompt) {
    if (this.runtimes.has(agentId)) {
      this.agents.get(agentId).queued_inputs.push({ prompt, created_at: nowIso() });
      return;
    }
    const runtime = {
      abortController: null,
      interrupted: false,
    };
    this.runtimes.set(agentId, runtime);
    void this.#workerLoop(agentId, prompt, runtime).finally(() => {
      this.runtimes.delete(agentId);
      this.#emitChange();
    });
  }

  async #workerLoop(agentId, firstPrompt, runtime) {
    const record = this.#getAgent(agentId);
    let nextPrompt = firstPrompt;

    while (nextPrompt) {
      runtime.abortController = new AbortController();
      runtime.interrupted = false;
      try {
        await this.#runOneTurn(record, nextPrompt, runtime.abortController.signal);
      } catch (err) {
        if (record.status === "closing" || record.status === "closed") {
          return;
        }
        if (isAbortError(err)) {
          if (runtime.interrupted && record.queued_inputs.length > 0) {
            await this.#appendEvent(record, {
              type: "status",
              status: "interrupted",
              text: "Interrupted active run before queued input.",
            });
          } else {
            record.status = "cancelled";
            await this.#appendEvent(record, {
              type: "status",
              status: "cancelled",
              text: "Run was cancelled locally.",
            });
            await this.store.upsertRecord(record);
            return;
          }
        } else {
          record.status = "failed";
          await this.#appendEvent(record, {
            type: "error",
            category: "agent_run_error",
            message: redactError(err),
          });
          await this.store.upsertRecord(record);
          return;
        }
      }

      const queued = record.queued_inputs.shift();
      nextPrompt = queued?.prompt;
      if (nextPrompt) {
        record.status = "queued";
        record.updated_at = nowIso();
        await this.store.upsertRecord(record);
      }
    }

    if (!TERMINAL_STATUSES.has(record.status) && record.status !== "closed") {
      record.status = "completed";
      record.updated_at = nowIso();
      await this.store.upsertRecord(record);
      this.#emitChange();
    }
  }

  async #runOneTurn(record, prompt, signal) {
    if (!record.thread_id) {
      record.thread_id = await this.client.createThread();
      record.updated_at = nowIso();
      await this.store.upsertRecord(record);
    }

    record.status = "running";
    record.updated_at = nowIso();
    await this.store.upsertRecord(record);
    await this.#appendEvent(record, {
      type: "status",
      status: "running",
      text: "Cloud Agent run started.",
    });

    const body = this.client.buildRunRequest({
      agentId: record.agent_id,
      threadId: record.thread_id,
      parentMessageId: record.parent_message_id ?? 0,
      prompt,
      model: record.model,
      workspace: record.workspace,
      mcpServers: record.mcp_servers,
      systemPrompt: record.system_prompt,
    });

    for await (const event of this.client.streamAgentRun(body, { signal })) {
      const normalized = normalizeSseEvent(event);
      if (normalized) {
        if (normalized.run_id) {
          record.run_id = normalized.run_id;
        } else if (
          !record.run_id &&
          normalized.type === "metadata" &&
          normalized.role === "user" &&
          normalized.message_id
        ) {
          // The API only reports run_id on the final response, which is too
          // late to cancel. Per the docs the ID is {thread_id}-{user_message_id},
          // so derive it from the first user metadata event.
          record.run_id = `${record.thread_id}-${normalized.message_id}`;
        }
        if (normalized.assistant_message_id) {
          record.parent_message_id = Number(normalized.assistant_message_id);
        }
        await this.#appendEvent(record, normalized);
        if (normalized.type === "error") {
          throw new Error(normalized.message || "remote agent error");
        }
      }
    }

    record.run_id = null;
    await this.store.upsertRecord(record);

    await this.#appendEvent(record, {
      type: "done",
      status: "turn_complete",
      text: "Cloud Agent turn completed.",
    });
  }

  async #appendEvent(record, partial) {
    const events = this.eventBuffers.get(record.agent_id) ?? [];
    const event = {
      sequence: (record.last_sequence ?? 0) + 1,
      timestamp: nowIso(),
      ...partial,
    };
    record.last_sequence = event.sequence;
    record.updated_at = event.timestamp;
    events.push(event);
    if (events.length > this.maxEventsPerAgent) {
      events.splice(0, events.length - this.maxEventsPerAgent);
    }
    this.eventBuffers.set(record.agent_id, events);
    await this.store.appendEvent(record.agent_id, event);
    await this.store.upsertRecord(record);
    this.#emitChange();
    return event;
  }

  #getAgent(agentId) {
    if (!agentId || !this.agents.has(agentId)) {
      throw new Error(`unknown agent_id: ${agentId}`);
    }
    return this.agents.get(agentId);
  }

  async #cancelRemoteRun(record) {
    if (!record.run_id || typeof this.client.cancelAgentRun !== "function") {
      return;
    }
    const runId = record.run_id;
    try {
      const response = await this.client.cancelAgentRun(runId);
      const assistantMessageId = response?.metadata?.assistant_message_id;
      if (assistantMessageId) {
        record.parent_message_id = Number(assistantMessageId);
      }
      record.run_id = null;
      await this.store.upsertRecord(record);
      await this.#appendEvent(record, {
        type: "status",
        status: "cancel_requested",
        text: `Requested server-side cancel for run ${runId}.`,
      });
    } catch (err) {
      record.run_id = null;
      await this.store.upsertRecord(record);
      // Snowflake returns 409 for runs it no longer tracks as active. On this
      // deployment that is every synchronous streaming run, so treat it as a
      // no-op rather than an error. Cancel is only effective for runs started
      // with `background: true`.
      if (err?.status === 409) {
        await this.#appendEvent(record, {
          type: "status",
          status: "cancel_noop",
          text: `Run ${runId} was not cancellable server-side; aborting the stream locally.`,
        });
        return;
      }
      await this.#appendEvent(record, {
        type: "error",
        category: "cancel_run_error",
        message: redactError(err),
      });
    }
  }

  #publicRecord(record, extra = {}) {
    return {
      agent_id: record.agent_id,
      status: record.status,
      thread_id: record.thread_id,
      parent_message_id: record.parent_message_id ?? 0,
      run_id: record.run_id ?? null,
      created_at: record.created_at,
      updated_at: record.updated_at,
      model: record.model,
      workspace: record.workspace,
      mcp_servers: record.mcp_servers,
      queued_inputs: record.queued_inputs?.length ?? 0,
      last_sequence: record.last_sequence ?? 0,
      prompt_preview: record.prompt_preview,
      ...extra,
    };
  }

  #emitChange() {
    this.emitter.emit("change");
  }

  #waitForChange(timeoutMs) {
    return new Promise((resolve) => {
      const done = () => {
        clearTimeout(timer);
        this.emitter.off("change", onChange);
        resolve();
      };
      const timer = setTimeout(done, timeoutMs);
      const onChange = () => done();
      this.emitter.once("change", onChange);
    });
  }
}

export function normalizeSseEvent({ event, data }) {
  if (event === "done" && data.trim() === "[DONE]") {
    return { type: "done", source_event: event, text: "" };
  }

  let payload;
  try {
    payload = JSON.parse(data);
  } catch {
    return {
      type: "raw",
      source_event: event,
      text: data,
      raw: data,
    };
  }

  if (event === "response.text.delta") {
    return {
      type: "text_delta",
      source_event: event,
      text: payload.text ?? payload.delta ?? "",
      raw: payload,
    };
  }
  if (event === "response.tool_use") {
    return {
      type: "tool_use",
      source_event: event,
      name: payload.name ?? "?",
      input: payload.input ?? {},
      raw: payload,
    };
  }
  if (event === "response.tool_result") {
    return {
      type: "tool_result",
      source_event: event,
      name: payload.name ?? "?",
      status: payload.status ?? "?",
      text: extractToolResultText(payload),
      raw: payload,
    };
  }
  if (event === "metadata") {
    const meta = payload.metadata ?? {};
    return {
      type: "metadata",
      source_event: event,
      role: meta.role ?? null,
      message_id: meta.message_id ?? null,
      run_id: meta.run_id ?? null,
      assistant_message_id:
        meta.assistant_message_id ??
        (meta.role === "assistant" ? meta.message_id : null) ??
        null,
      raw: payload,
    };
  }
  if (event === "response") {
    return {
      type: "response",
      source_event: event,
      status: payload.status ?? "completed",
      run_id: payload.metadata?.run_id ?? null,
      assistant_message_id: payload.metadata?.assistant_message_id ?? null,
      text: extractResponseText(payload),
      raw: payload,
    };
  }
  if (event === "response.error" || event === "error") {
    return {
      type: "error",
      source_event: event,
      category: "remote_agent_error",
      message: payload.message ?? JSON.stringify(payload).slice(0, 500),
      raw: payload,
    };
  }
  return {
    type: "raw",
    source_event: event,
    raw: payload,
  };
}

function extractToolResultText(payload) {
  const first = Array.isArray(payload.content) ? payload.content[0] : undefined;
  return first?.json?.text ?? first?.text ?? "";
}

function extractResponseText(payload) {
  if (!Array.isArray(payload.content)) {
    return "";
  }
  return payload.content
    .filter((item) => item?.type === "text" && typeof item.text === "string")
    .map((item) => item.text)
    .join("");
}

function conditionMet(record, condition) {
  if (condition === "terminal") {
    return TERMINAL_STATUSES.has(record.status);
  }
  if (condition === "turn_complete") {
    return TERMINAL_STATUSES.has(record.status) || record.status === "completed";
  }
  if (condition === "queue_drained") {
    return TERMINAL_STATUSES.has(record.status) && (record.queued_inputs?.length ?? 0) === 0;
  }
  if (condition === "next_event") {
    return (record.last_sequence ?? 0) > 0;
  }
  throw new Error(`unknown wait condition: ${condition}`);
}

function requirePrompt(prompt) {
  if (!prompt || typeof prompt !== "string") {
    throw new Error("prompt is required");
  }
}

function normalizeWorkspace(workspace) {
  if (!workspace) {
    return { mode: "default" };
  }
  if (!["default", "none", "stage"].includes(workspace.mode)) {
    throw new Error("workspace.mode must be default, none, or stage");
  }
  if (workspace.mode === "stage" && !workspace.stage_name) {
    throw new Error("workspace.stage_name is required for stage workspace mode");
  }
  return {
    mode: workspace.mode,
    ...(workspace.stage_name ? { stage_name: workspace.stage_name } : {}),
  };
}

function normalizeMcpServers(servers) {
  if (!servers) {
    return [];
  }
  if (!Array.isArray(servers)) {
    throw new Error("mcp_servers must be an array");
  }
  return servers.map((server) => ({
    name: server.name,
    type: server.type ?? "EXTERNAL_MCP",
  }));
}

function stripRaw(event) {
  const { raw, ...rest } = event;
  return rest;
}

function preview(prompt) {
  return prompt.length <= 120 ? prompt : `${prompt.slice(0, 117)}...`;
}

function nowIso() {
  return new Date().toISOString();
}

function redactError(err) {
  return String(err?.message ?? err).replace(
    /(Bearer|Snowflake Token=)"?[^"\s]+/gi,
    "$1<redacted>",
  );
}

function isAbortError(err) {
  return err?.name === "AbortError" || /abort/i.test(String(err?.message ?? ""));
}
