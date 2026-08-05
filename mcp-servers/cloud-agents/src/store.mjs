import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const DEFAULT_STATE_DIR = path.join(os.homedir(), ".snowflake", "cloud-agents-mcp");

export class MemoryStore {
  constructor() {
    this.records = new Map();
    this.events = new Map();
  }

  async init() {}

  async loadRecords() {
    return [...this.records.values()].map(clone);
  }

  async loadEvents(agentId) {
    return [...(this.events.get(agentId) ?? [])].map(clone);
  }

  async upsertRecord(record) {
    this.records.set(record.agent_id, clone(record));
  }

  async appendEvent(agentId, event) {
    const events = this.events.get(agentId) ?? [];
    events.push(clone(event));
    this.events.set(agentId, events);
  }
}

export class FileStore extends MemoryStore {
  constructor({
    stateDir = process.env.CLOUD_AGENTS_MCP_STATE_DIR || DEFAULT_STATE_DIR,
  } = {}) {
    super();
    this.stateDir = stateDir;
    this.eventsDir = path.join(stateDir, "events");
    this.recordsPath = path.join(stateDir, "records.json");
    this.writeChain = Promise.resolve();
  }

  async init() {
    await fs.mkdir(this.eventsDir, { recursive: true });
    await this.#loadRecordsFromDisk();
    await this.#loadEventsFromDisk();
  }

  async upsertRecord(record) {
    await super.upsertRecord(record);
    await this.#enqueueWrite(async () => {
      const tmp = `${this.recordsPath}.tmp`;
      await fs.writeFile(
        tmp,
        `${JSON.stringify([...this.records.values()], null, 2)}\n`,
      );
      await fs.rename(tmp, this.recordsPath);
    });
  }

  async appendEvent(agentId, event) {
    await super.appendEvent(agentId, event);
    await fs.mkdir(this.eventsDir, { recursive: true });
    const line = `${JSON.stringify(event)}\n`;
    await fs.appendFile(this.#eventsPath(agentId), line);
  }

  async #loadRecordsFromDisk() {
    try {
      const raw = await fs.readFile(this.recordsPath, "utf8");
      const records = JSON.parse(raw);
      for (const record of records) {
        if (record?.agent_id) {
          this.records.set(record.agent_id, record);
        }
      }
    } catch (err) {
      if (err.code !== "ENOENT") {
        throw err;
      }
    }
  }

  async #loadEventsFromDisk() {
    let names = [];
    try {
      names = await fs.readdir(this.eventsDir);
    } catch (err) {
      if (err.code !== "ENOENT") {
        throw err;
      }
    }
    for (const name of names) {
      if (!name.endsWith(".jsonl")) {
        continue;
      }
      const agentId = name.slice(0, -".jsonl".length);
      const raw = await fs.readFile(path.join(this.eventsDir, name), "utf8");
      const events = raw
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line));
      this.events.set(agentId, events);
    }
  }

  #eventsPath(agentId) {
    const safeId = agentId.replace(/[^a-zA-Z0-9_.-]/g, "_");
    return path.join(this.eventsDir, `${safeId}.jsonl`);
  }

  #enqueueWrite(fn) {
    this.writeChain = this.writeChain.then(fn, fn);
    return this.writeChain;
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}
