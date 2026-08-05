import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { buildRunRequest } from "../src/request-builder.mjs";

describe("buildRunRequest", () => {
  it("throws without agentId", () => {
    assert.throws(() => buildRunRequest({ threadId: 1, prompt: "hi" }), /agentId/);
  });

  it("throws without threadId", () => {
    assert.throws(() => buildRunRequest({ agentId: "a", prompt: "hi" }), /threadId/);
  });

  it("throws without prompt", () => {
    assert.throws(() => buildRunRequest({ agentId: "a", threadId: 1 }), /prompt/);
  });

  it("builds a minimal request", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 123,
      prompt: "hello",
    });
    assert.equal(body.thread_id, 123);
    assert.equal(body.messages[0].content[0].text, "hello");
    assert.equal(body.models.orchestration, "auto");
    assert.equal(body.stream, true);
    assert.equal(body.experimental.codingAgent.SandboxEnable, true);
    assert.ok(body.experimental.VStages);
  });

  it("respects workspace mode none", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 1,
      prompt: "hi",
      workspace: { mode: "none" },
    });
    assert.equal(body.experimental.VStages, undefined);
  });

  it("respects workspace mode stage", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 1,
      prompt: "hi",
      workspace: { mode: "stage", stage_name: "MY_DB.PUBLIC.MY_STAGE" },
    });
    assert.equal(body.experimental.VStages[0].stage_name, "MY_DB.PUBLIC.MY_STAGE");
  });

  it("includes mcp_servers when provided", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 1,
      prompt: "hi",
      mcpServers: [{ name: "SNOWFLAKE_INTELLIGENCE.MCP.SLACK" }],
    });
    assert.equal(body.mcp_servers[0].server_spec.name, "SNOWFLAKE_INTELLIGENCE.MCP.SLACK");
    assert.equal(body.mcp_servers[0].server_spec.type, "EXTERNAL_MCP");
  });

  it("includes instructions when provided", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 1,
      prompt: "hi",
      instructions: { orchestration: "be helpful", response: "be brief" },
    });
    assert.equal(body.instructions.orchestration, "be helpful");
    assert.equal(body.instructions.response, "be brief");
  });

  it("sets parentMessageId", () => {
    const body = buildRunRequest({
      agentId: "ca_test",
      threadId: 1,
      prompt: "follow up",
      parentMessageId: 42,
    });
    assert.equal(body.parent_message_id, 42);
  });
});
