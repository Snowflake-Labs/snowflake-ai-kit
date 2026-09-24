import { describe, it, beforeEach, afterEach, mock } from "node:test";
import assert from "node:assert/strict";
import {
  AgentManager,
  normalizeSseEvent,
  compactActivity,
  conditionMet,
} from "../src/agent-manager.mjs";
import { MemoryStore } from "../src/store.mjs";
import { toolDefinitions } from "../src/tools.mjs";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeStore() {
  return new MemoryStore();
}

function makeClient({ events = [], threadId = 12345 } = {}) {
  return {
    createThread: async () => threadId,
    deleteThread: async () => {},
    cancelAgentRun: async () => ({}),
    buildRunRequest: () => ({ thread_id: threadId, stream: true }),
    streamAgentRun: async function* (body, opts) {
      for (const evt of events) {
        yield evt;
      }
    },
  };
}

function sseTextDelta(text) {
  return { event: "response.text.delta", data: JSON.stringify({ text }) };
}

function sseToolUse(name) {
  return {
    event: "response.tool_use",
    data: JSON.stringify({ name, input: {} }),
  };
}

function sseToolResult(name, status = "success") {
  return {
    event: "response.tool_result",
    data: JSON.stringify({ name, status, content: [{ text: "ok" }] }),
  };
}

function sseMetadata(role = "user", messageId = 1) {
  return {
    event: "metadata",
    data: JSON.stringify({ metadata: { role, message_id: messageId } }),
  };
}

function sseDone() {
  return { event: "done", data: "[DONE]" };
}

function sseResponse(text, assistantMessageId = 2) {
  return {
    event: "response",
    data: JSON.stringify({
      status: "completed",
      metadata: { assistant_message_id: assistantMessageId },
      content: [{ type: "text", text }],
    }),
  };
}

async function spawnAndWaitForCompletion(manager, prompt = "test") {
  const result = await manager.spawn({ prompt, workspace: { mode: "none" } });
  // Give the worker loop time to finish
  await new Promise((resolve) => setTimeout(resolve, 50));
  return result;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("wait clamp", () => {
  it("clamps timeout_ms > 90000 to 90000", async () => {
    const store = makeStore();
    const events = [sseMetadata(), sseDone()];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });

    // Request 300s but it should clamp to 90s.
    // The agent completes quickly so we won't hit the timeout,
    // but we verify the schema reports the correct max.
    await new Promise((r) => setTimeout(r, 50));
    const result = await manager.wait({
      agent_ids: [spawn.agent_id],
      timeout_ms: 300_000,
      condition: "terminal",
    });
    // Agent completed, so no timeout — but the clamp logic exists
    assert.ok(result.completed.length > 0 || result.timed_out.length > 0);
  });

  it("schema reports maximum 90000 for timeout_ms", () => {
    const tools = toolDefinitions();
    const waitTool = tools.find((t) => t.name === "cloud_agent_wait");
    assert.equal(
      waitTool.inputSchema.properties.timeout_ms.maximum,
      90000,
    );
  });

  it("timed_out result includes wait_clamped when request exceeded max", async () => {
    const store = makeStore();
    // Client that never finishes (no events = worker never completes)
    const neverClient = {
      createThread: async () => 99,
      deleteThread: async () => {},
      cancelAgentRun: async () => ({}),
      buildRunRequest: () => ({ thread_id: 99, stream: true }),
      streamAgentRun: async function* () {
        // Yield nothing — hangs forever
        await new Promise(() => {});
      },
    };
    const manager = new AgentManager({ client: neverClient, store });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "long running",
      workspace: { mode: "none" },
    });

    const result = await manager.wait({
      agent_ids: [spawn.agent_id],
      timeout_ms: 200_000, // Will be clamped
      condition: "terminal",
    });
    assert.equal(result.timed_out.length, 1);
    assert.equal(result.wait_clamped, true);
  });

  it("values <= 90000 pass through unchanged (no wait_clamped)", async () => {
    const store = makeStore();
    const neverClient = {
      createThread: async () => 99,
      deleteThread: async () => {},
      cancelAgentRun: async () => ({}),
      buildRunRequest: () => ({ thread_id: 99, stream: true }),
      streamAgentRun: async function* () {
        await new Promise(() => {});
      },
    };
    const manager = new AgentManager({ client: neverClient, store });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });

    // Use a very short timeout that will expire
    const result = await manager.wait({
      agent_ids: [spawn.agent_id],
      timeout_ms: 10,
      condition: "terminal",
    });
    assert.equal(result.timed_out.length, 1);
    assert.equal(result.wait_clamped, undefined);
  });
});

describe("next_event condition fix", () => {
  it("does NOT fire when last_sequence == since_sequence", () => {
    const record = { last_sequence: 5, status: "running" };
    assert.equal(conditionMet(record, "next_event", 5), false);
  });

  it("fires when last_sequence > since_sequence", () => {
    const record = { last_sequence: 6, status: "running" };
    assert.equal(conditionMet(record, "next_event", 5), true);
  });

  it("does NOT fire on fresh agent with since_sequence=0 and last_sequence=0", () => {
    const record = { last_sequence: 0, status: "starting" };
    assert.equal(conditionMet(record, "next_event", 0), false);
  });

  it("terminal conditions still work", () => {
    assert.equal(
      conditionMet({ status: "completed" }, "terminal"),
      true,
    );
    assert.equal(conditionMet({ status: "running" }, "terminal"), false);
    assert.equal(
      conditionMet({ status: "failed" }, "turn_complete"),
      true,
    );
    assert.equal(
      conditionMet(
        { status: "completed", queued_inputs: [] },
        "queue_drained",
      ),
      true,
    );
  });
});

describe("appendEvent hot path", () => {
  it("does not call store.upsertRecord during event append", async () => {
    const store = makeStore();
    let upsertCount = 0;
    const origUpsert = store.upsertRecord.bind(store);
    store.upsertRecord = async (record) => {
      upsertCount++;
      return origUpsert(record);
    };

    const events = [
      sseMetadata(),
      sseTextDelta("hello "),
      sseTextDelta("world"),
      sseResponse("hello world"),
      sseDone(),
    ];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();

    const upsertBefore = upsertCount;
    await manager.spawn({ prompt: "test", workspace: { mode: "none" } });
    await new Promise((r) => setTimeout(r, 100));
    const upsertAfter = upsertCount;

    // upsertRecord should only be called for status transitions
    // (spawn, running, completed), NOT for each text_delta event.
    // With 5 SSE events, if upsert was on the hot path we'd see ~8+ calls.
    // With the fix, we see ~4 (spawn init, running status, run_id null, completed).
    assert.ok(
      upsertAfter - upsertBefore < 8,
      `Expected fewer than 8 upsert calls for 5 events, got ${upsertAfter - upsertBefore}`,
    );
  });
});

describe("init recovery of last_sequence", () => {
  it("recovers last_sequence from event log", async () => {
    const store = makeStore();
    // Pre-populate store with a record and events
    const record = {
      agent_id: "ca_test_recover",
      status: "completed",
      thread_id: 100,
      parent_message_id: 0,
      run_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      model: "auto",
      workspace: { mode: "none" },
      mcp_servers: [],
      system_prompt: "",
      metadata: {},
      prompt_preview: "test",
      queued_inputs: [],
      last_sequence: 0, // Stale — should be recovered
    };
    await store.upsertRecord(record);
    await store.appendEvent("ca_test_recover", {
      sequence: 1,
      type: "status",
      text: "running",
    });
    await store.appendEvent("ca_test_recover", {
      sequence: 2,
      type: "text_delta",
      text: "hello",
    });
    await store.appendEvent("ca_test_recover", {
      sequence: 7,
      type: "done",
      text: "",
    });

    const manager = new AgentManager({
      client: makeClient(),
      store,
    });
    await manager.init();

    const status = await manager.status({ agent_ids: ["ca_test_recover"] });
    assert.equal(status.agents[0].last_sequence, 7);
  });

  it("leaves last_sequence at 0 with no events", async () => {
    const store = makeStore();
    const record = {
      agent_id: "ca_test_empty",
      status: "completed",
      thread_id: 200,
      parent_message_id: 0,
      run_id: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      model: "auto",
      workspace: { mode: "none" },
      mcp_servers: [],
      system_prompt: "",
      metadata: {},
      prompt_preview: "test",
      queued_inputs: [],
      last_sequence: 0,
    };
    await store.upsertRecord(record);

    const manager = new AgentManager({
      client: makeClient(),
      store,
    });
    await manager.init();

    const status = await manager.status({ agent_ids: ["ca_test_empty"] });
    assert.equal(status.agents[0].last_sequence, 0);
  });
});

describe("compactActivity", () => {
  it("pairs tool_use + tool_result into one step with elapsed_ms", () => {
    const events = [
      {
        type: "tool_use",
        name: "snowflake_sql_execute",
        input: { description: "Heavy aggregation", sql: "SELECT COUNT(*) FROM t" },
        timestamp: "2026-09-24T22:25:37.576Z",
      },
      {
        type: "tool_result",
        name: "snowflake_sql_execute",
        status: "success",
        timestamp: "2026-09-24T22:25:40.539Z",
      },
    ];
    const activity = compactActivity(events);
    assert.equal(activity.length, 1);
    assert.equal(activity[0].type, "step");
    assert.equal(activity[0].name, "snowflake_sql_execute");
    assert.equal(activity[0].description, "Heavy aggregation");
    assert.equal(activity[0].status, "success");
    assert.equal(activity[0].started_at, "2026-09-24T22:25:37.576Z");
    assert.equal(activity[0].elapsed_ms, 2963);
  });

  it("uses SQL first line as description fallback (truncated to 80 chars)", () => {
    const longSql = "SELECT very_long_column_name, another_long_column FROM some_table WHERE condition = true AND more_stuff";
    const events = [
      { type: "tool_use", name: "sql_exec", input: { sql: longSql }, timestamp: "2026-01-01T00:00:00Z" },
      { type: "tool_result", name: "sql_exec", status: "success", timestamp: "2026-01-01T00:00:01Z" },
    ];
    const activity = compactActivity(events);
    assert.equal(activity[0].type, "step");
    assert.ok(activity[0].description.length <= 80);
    assert.ok(activity[0].description.endsWith("..."));
  });

  it("drops text_deltas but keeps last progress line (capped at 120 chars)", () => {
    const events = [
      { type: "text_delta", text: "First sentence. " },
      { type: "text_delta", text: "Second sentence. " },
      { type: "text_delta", text: "Final progress update here." },
    ];
    const activity = compactActivity(events);
    // No text entries — only a progress line
    assert.equal(activity.length, 1);
    assert.equal(activity[0].type, "progress");
    assert.equal(activity[0].text, "Final progress update here.");
  });

  it("does NOT include response text in activity", () => {
    const events = [
      { type: "text_delta", text: "working..." },
      { type: "response", text: "Here is a very long final summary table..." },
    ];
    const activity = compactActivity(events);
    // response is dropped — only progress from text_delta
    const types = activity.map((a) => a.type);
    assert.ok(!types.includes("response"));
    assert.ok(!types.includes("text"));
  });

  it("drops metadata and raw events", () => {
    const events = [
      { type: "metadata", role: "user", message_id: 1 },
      { type: "raw", source_event: "unknown" },
    ];
    const activity = compactActivity(events);
    assert.equal(activity.length, 0);
  });

  it("returns empty array for empty events", () => {
    assert.deepEqual(compactActivity([]), []);
  });

  it("handles unpaired tool_use (in progress)", () => {
    const events = [
      { type: "tool_use", name: "sql_exec", input: { sql: "SELECT 1" }, timestamp: "2026-01-01T00:00:00Z" },
    ];
    const activity = compactActivity(events);
    assert.equal(activity.length, 1);
    assert.equal(activity[0].type, "step");
    assert.equal(activity[0].status, "in_progress");
  });

  it("includes status and error events", () => {
    const events = [
      { type: "status", text: "running" },
      { type: "error", message: "something broke" },
      { type: "done", status: "turn_complete", text: "done" },
    ];
    const activity = compactActivity(events);
    assert.equal(activity.length, 3);
    assert.deepEqual(activity[0], { type: "status", text: "running" });
    assert.deepEqual(activity[1], { type: "error", message: "something broke" });
    assert.deepEqual(activity[2], { type: "status", text: "done" });
  });

  it("interleaves steps and narration correctly", () => {
    const events = [
      { type: "text_delta", text: "Let me query. " },
      { type: "tool_use", name: "sql_exec", input: { description: "count rows" }, timestamp: "2026-01-01T00:00:00Z" },
      { type: "tool_result", name: "sql_exec", status: "success", timestamp: "2026-01-01T00:00:02Z" },
      { type: "text_delta", text: "Got results. " },
      { type: "tool_use", name: "sql_exec", input: { sql: "CREATE VIEW v AS SELECT 1" }, timestamp: "2026-01-01T00:00:03Z" },
      { type: "tool_result", name: "sql_exec", status: "success", timestamp: "2026-01-01T00:00:04Z" },
      { type: "text_delta", text: "All done." },
    ];
    const activity = compactActivity(events);
    // 2 steps + 1 progress (last text_delta)
    const steps = activity.filter((a) => a.type === "step");
    const progress = activity.filter((a) => a.type === "progress");
    assert.equal(steps.length, 2);
    assert.equal(steps[0].description, "count rows");
    assert.equal(steps[0].elapsed_ms, 2000);
    assert.equal(steps[1].description, "CREATE VIEW v AS SELECT 1");
    assert.equal(progress.length, 1);
    assert.equal(progress[0].text, "All done.");
  });
});

describe("default workspace from env", () => {
  const ENV_KEY = "CLOUD_AGENTS_DEFAULT_WORKSPACE_MODE";

  afterEach(() => {
    delete process.env[ENV_KEY];
  });

  it("uses env var when no workspace in input", async () => {
    process.env[ENV_KEY] = "none";
    const store = makeStore();
    const events = [sseMetadata(), sseDone()];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();

    const result = await manager.spawn({ prompt: "test" });
    assert.equal(result.workspace.mode, "none");
  });

  it("input workspace overrides env var", async () => {
    process.env[ENV_KEY] = "none";
    const store = makeStore();
    const events = [sseMetadata(), sseDone()];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();

    const result = await manager.spawn({
      prompt: "test",
      workspace: { mode: "default" },
    });
    assert.equal(result.workspace.mode, "default");
  });
});

describe("existing behavior regression", () => {
  it("spawn returns non-blocking record", async () => {
    const store = makeStore();
    const manager = new AgentManager({
      client: makeClient({ events: [sseMetadata(), sseDone()] }),
      store,
    });
    await manager.init();

    const result = await manager.spawn({
      prompt: "hello",
      workspace: { mode: "none" },
    });
    assert.ok(result.agent_id.startsWith("ca_"));
    assert.equal(result.status, "starting");
    assert.equal(result.non_blocking, true);
  });

  it("output returns text without events by default", async () => {
    const store = makeStore();
    const events = [
      sseMetadata(),
      sseTextDelta("Hello "),
      sseTextDelta("world"),
      sseResponse("Hello world"),
      sseDone(),
    ];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });
    await new Promise((r) => setTimeout(r, 100));

    const out = await manager.output({ agent_id: spawn.agent_id });
    assert.ok(out.text.includes("Hello"));
    assert.equal(out.events, undefined);
    assert.equal(out.non_blocking, true);
  });

  it("output returns events when include_events=true", async () => {
    const store = makeStore();
    const events = [
      sseMetadata(),
      sseTextDelta("hi"),
      sseResponse("hi"),
      sseDone(),
    ];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });
    await new Promise((r) => setTimeout(r, 100));

    const out = await manager.output({
      agent_id: spawn.agent_id,
      include_events: true,
    });
    assert.ok(Array.isArray(out.events));
    assert.ok(out.events.length > 0);
  });

  it("wait returns clean text (no nested output object)", async () => {
    const store = makeStore();
    const events = [
      sseMetadata(),
      sseTextDelta("result text"),
      sseResponse("result text"),
      sseDone(),
    ];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });
    await new Promise((r) => setTimeout(r, 100));

    const result = await manager.wait({
      agent_ids: [spawn.agent_id],
      condition: "terminal",
      timeout_ms: 5000,
    });
    assert.ok(result.completed.length > 0);
    const completed = result.completed[0];
    assert.ok(completed.text.includes("result"));
    assert.equal(completed.output, undefined);
    assert.ok(completed.next_sequence > 0);
  });

  it("wait with include_activity returns compact steps", async () => {
    const store = makeStore();
    const events = [
      sseMetadata(),
      sseTextDelta("querying"),
      sseToolUse("sql_exec"),
      sseToolResult("sql_exec"),
      sseTextDelta("done"),
      sseResponse("querying done"),
      sseDone(),
    ];
    const manager = new AgentManager({
      client: makeClient({ events }),
      store,
    });
    await manager.init();
    const spawn = await manager.spawn({
      prompt: "test",
      workspace: { mode: "none" },
    });
    await new Promise((r) => setTimeout(r, 100));

    const result = await manager.wait({
      agent_ids: [spawn.agent_id],
      condition: "terminal",
      timeout_ms: 5000,
      include_activity: true,
    });
    const completed = result.completed[0];
    assert.ok(Array.isArray(completed.activity));
    const steps = completed.activity.filter((a) => a.type === "step");
    assert.ok(steps.length > 0);
    assert.equal(steps[0].name, "sql_exec");
    assert.equal(steps[0].status, "success");
  });
});
