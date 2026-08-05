const UTF8 = new TextDecoder("utf-8");

export function createSseParser() {
  return {
    buffer: "",
    eventType: "",
    dataLines: [],
  };
}

export function feedSseParser(state, chunk, { final = false } = {}) {
  state.buffer += chunk;
  const events = [];

  while (true) {
    const line = takeLine(state, final);
    if (line === null) {
      break;
    }
    const event = processSseLine(state, line);
    if (event) {
      events.push(event);
    }
  }

  if (final && state.dataLines.length > 0) {
    events.push(dispatchEvent(state));
  }

  return events;
}

export async function* parseSseStream(readable) {
  const state = createSseParser();
  const reader = readable.getReader();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        for (const event of feedSseParser(state, "", { final: true })) {
          yield event;
        }
        return;
      }
      const text = UTF8.decode(value, { stream: true });
      for (const event of feedSseParser(state, text)) {
        yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function parseSseString(input) {
  const state = createSseParser();
  return feedSseParser(state, input, { final: true });
}

function takeLine(state, final) {
  const buffer = state.buffer;
  for (let i = 0; i < buffer.length; i += 1) {
    const ch = buffer[i];
    if (ch === "\n" || ch === "\r") {
      const line = buffer.slice(0, i);
      const terminatorLength = ch === "\r" && buffer[i + 1] === "\n" ? 2 : 1;
      state.buffer = buffer.slice(i + terminatorLength);
      return line;
    }
  }
  if (final && buffer.length > 0) {
    state.buffer = "";
    return buffer;
  }
  return null;
}

function processSseLine(state, line) {
  if (line === "") {
    if (state.dataLines.length === 0) {
      state.eventType = "";
      return null;
    }
    return dispatchEvent(state);
  }

  if (line.startsWith(":")) {
    return null;
  }

  const colon = line.indexOf(":");
  const field = colon === -1 ? line : line.slice(0, colon);
  let value = colon === -1 ? "" : line.slice(colon + 1);
  if (value.startsWith(" ")) {
    value = value.slice(1);
  }

  if (field === "event") {
    state.eventType = value;
  } else if (field === "data") {
    state.dataLines.push(value);
  }
  return null;
}

function dispatchEvent(state) {
  const event = {
    event: state.eventType || "message",
    data: state.dataLines.join("\n").replace(/\n$/, ""),
  };
  state.eventType = "";
  state.dataLines = [];
  return event;
}
