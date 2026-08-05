import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { Readable } from "node:stream";
import { handleJsonRpcMessage } from "../src/server.mjs";

// Minimal mock manager for protocol tests
const mockManager = {
  async init() {},
  async spawn() { return { agent_id: "ca_mock", status: "running" }; },
  async sendInput() { return { queued: true }; },
  async output() { return { events: [] }; },
  async wait() { return { condition_met: true }; },
  async status() { return { agents: [] }; },
  async list() { return { agents: [] }; },
  async close() { return { closed: true }; },
  async resume() { return { resumed: true }; },
};

describe("MCP server protocol", () => {
  it("responds to initialize", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2024-11-05" } },
      mockManager,
    );
    assert.equal(resp.id, 1);
    assert.equal(resp.result.serverInfo.name, "cloud-agents-mcp");
    assert.equal(resp.result.protocolVersion, "2024-11-05");
  });

  it("responds to ping", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", id: 2, method: "ping" },
      mockManager,
    );
    assert.deepEqual(resp.result, {});
  });

  it("returns tool list", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", id: 3, method: "tools/list" },
      mockManager,
    );
    assert.ok(resp.result.tools.length >= 8);
    const names = resp.result.tools.map((t) => t.name);
    assert.ok(names.includes("cloud_agent_spawn"));
    assert.ok(names.includes("cloud_agent_wait"));
    assert.ok(names.includes("cloud_agent_close"));
  });

  it("calls a tool", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "cloud_agent_list", arguments: {} } },
      mockManager,
    );
    assert.ok(resp.result.content[0].text.includes("agents"));
  });

  it("returns error for unknown method", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", id: 5, method: "unknown/method" },
      mockManager,
    );
    assert.equal(resp.error.code, -32601);
  });

  it("returns error for invalid request", async () => {
    const resp = await handleJsonRpcMessage(null, mockManager);
    assert.equal(resp.error.code, -32600);
  });

  it("ignores notifications (no id)", async () => {
    const resp = await handleJsonRpcMessage(
      { jsonrpc: "2.0", method: "notifications/initialized" },
      mockManager,
    );
    assert.equal(resp, null);
  });
});
