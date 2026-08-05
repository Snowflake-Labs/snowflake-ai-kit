export function toolDefinitions() {
  return [
    {
      name: "cloud_agent_spawn",
      description:
        "Start a Snowflake CoCo Cloud Agent run and return immediately with an agent handle.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["prompt"],
        properties: commonRunProperties({
          prompt: { type: "string", minLength: 1 },
        }),
      },
    },
    {
      name: "cloud_agent_send_input",
      description:
        "Queue or start a follow-up turn on an open Cloud Agent handle. Non-blocking by default.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["agent_id", "prompt"],
        properties: {
          agent_id: { type: "string" },
          prompt: { type: "string", minLength: 1 },
          interrupt: { type: "boolean", default: false },
        },
      },
    },
    {
      name: "cloud_agent_output",
      description: "Read buffered Cloud Agent output without blocking.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["agent_id"],
        properties: {
          agent_id: { type: "string" },
          since_sequence: { type: "integer", minimum: 0, default: 0 },
          limit: { type: "integer", minimum: 1, maximum: 1000, default: 200 },
          include_raw_events: { type: "boolean", default: false },
        },
      },
    },
    {
      name: "cloud_agent_wait",
      description:
        "Block until one or more Cloud Agents reaches a condition. This is the intentionally blocking tool.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["agent_ids"],
        properties: {
          agent_ids: {
            type: "array",
            minItems: 1,
            items: { type: "string" },
          },
          condition: {
            type: "string",
            enum: ["terminal", "next_event", "turn_complete", "queue_drained"],
            default: "terminal",
          },
          timeout_ms: {
            type: "integer",
            minimum: 1,
            maximum: 3600000,
            default: 30000,
          },
          include_output: { type: "boolean", default: true },
          mode: { type: "string", enum: ["any", "all"], default: "any" },
          since_sequence: { type: "integer", minimum: 0, default: 0 },
        },
      },
    },
    {
      name: "cloud_agent_status",
      description: "Return current status for Cloud Agents without blocking.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: {
          agent_ids: {
            type: "array",
            items: { type: "string" },
          },
        },
      },
    },
    {
      name: "cloud_agent_list",
      description: "List known local Cloud Agent handles without blocking.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: {
          status: { type: "string" },
          limit: { type: "integer", minimum: 1, maximum: 500, default: 50 },
        },
      },
    },
    {
      name: "cloud_agent_close",
      description:
        "Close a local Cloud Agent handle and optionally request cancellation or thread deletion.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        required: ["agent_id"],
        properties: {
          agent_id: { type: "string" },
          cancel_active_run: { type: "boolean", default: true },
          delete_thread: { type: "boolean", default: false },
          wait_for_cancel_ms: {
            type: "integer",
            minimum: 0,
            maximum: 60000,
            default: 0,
          },
        },
      },
    },
    {
      name: "cloud_agent_resume",
      description:
        "Reactivate a closed Cloud Agent handle by agent_id, or create a fresh handle from a known thread_id.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: {
          agent_id: { type: "string" },
          thread_id: { type: "integer" },
          parent_message_id: {
            type: "integer",
            description:
              "Optional. When resuming by thread_id, the last assistant message id.",
          },
        },
      },
    },
  ];
}

export async function callTool(manager, name, args = {}) {
  switch (name) {
    case "cloud_agent_spawn":
      return manager.spawn(args);
    case "cloud_agent_send_input":
      return manager.sendInput(args);
    case "cloud_agent_output":
      return manager.output(args);
    case "cloud_agent_wait":
      return manager.wait(args);
    case "cloud_agent_status":
      return manager.status(args);
    case "cloud_agent_list":
      return manager.list(args);
    case "cloud_agent_close":
      return manager.close(args);
    case "cloud_agent_resume":
      return manager.resume(args);
    default:
      throw new Error(`unknown tool: ${name}`);
  }
}

function commonRunProperties(extra) {
  return {
    ...extra,
    model: { type: "string", default: "auto" },
    workspace: {
      type: "object",
      additionalProperties: false,
      properties: {
        mode: { type: "string", enum: ["default", "none", "stage"] },
        stage_name: { type: "string" },
      },
    },
    mcp_servers: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["name"],
        properties: {
          name: { type: "string" },
          type: { type: "string", enum: ["EXTERNAL_MCP", "CUSTOM_MCP"] },
        },
      },
    },
    system_prompt: { type: "string" },
    metadata: { type: "object" },
  };
}
