import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { parseSseString, createSseParser, feedSseParser } from "../src/sse.mjs";

describe("SSE parser", () => {
  it("parses a simple event", () => {
    const events = parseSseString("event: metadata\ndata: {\"run_id\":\"abc\"}\n\n");
    assert.equal(events.length, 1);
    assert.equal(events[0].event, "metadata");
    assert.equal(events[0].data, '{"run_id":"abc"}');
  });

  it("parses multiple events", () => {
    const input = [
      "event: response.text.delta",
      'data: {"text":"hello"}',
      "",
      "event: done",
      "data: {}",
      "",
    ].join("\n");
    const events = parseSseString(input);
    assert.equal(events.length, 2);
    assert.equal(events[0].event, "response.text.delta");
    assert.equal(events[1].event, "done");
  });

  it("handles multi-line data", () => {
    const input = "event: message\ndata: line1\ndata: line2\n\n";
    const events = parseSseString(input);
    assert.equal(events.length, 1);
    assert.equal(events[0].data, "line1\nline2");
  });

  it("ignores comments", () => {
    const input = ": this is a comment\nevent: ping\ndata: {}\n\n";
    const events = parseSseString(input);
    assert.equal(events.length, 1);
    assert.equal(events[0].event, "ping");
  });

  it("defaults event type to message", () => {
    const events = parseSseString("data: hello\n\n");
    assert.equal(events[0].event, "message");
  });

  it("handles CRLF line endings", () => {
    const events = parseSseString("event: test\r\ndata: ok\r\n\r\n");
    assert.equal(events.length, 1);
    assert.equal(events[0].event, "test");
    assert.equal(events[0].data, "ok");
  });

  it("handles incremental feeding", () => {
    const state = createSseParser();
    let events = feedSseParser(state, "event: met");
    assert.equal(events.length, 0);
    events = feedSseParser(state, "adata\ndata: hi\n\n");
    assert.equal(events.length, 1);
    assert.equal(events[0].event, "metadata");
    assert.equal(events[0].data, "hi");
  });
});
