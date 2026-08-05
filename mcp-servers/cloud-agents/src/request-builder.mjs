export const DEFAULT_HOST = "https://snowhouse.snowflakecomputing.com";
export const DEFAULT_MODEL = "auto";
export const DEFAULT_WORKSPACE_STAGE = "USER$.PUBLIC.DEFAULT$";

export function buildRunRequest({
  agentId,
  threadId,
  prompt,
  model = DEFAULT_MODEL,
  workspace = { mode: "default" },
  mcpServers = [],
  systemPrompt = "",
  instructions = null,
  parentMessageId = 0,
  originApplication = "coding_agent",
  nestedOriginApplication = "cortex-code-cli",
} = {}) {
  if (!agentId) {
    throw new Error("agentId is required");
  }
  if (!threadId) {
    throw new Error("threadId is required");
  }
  if (!prompt || typeof prompt !== "string") {
    throw new Error("prompt is required");
  }

  const workspaceMode = workspace?.mode ?? "default";
  const mountWorkspace = workspaceMode !== "none";
  const stageName =
    workspaceMode === "stage"
      ? requireNonEmpty(workspace.stage_name, "workspace.stage_name")
      : DEFAULT_WORKSPACE_STAGE;

  const experimental = {
    canary: true,
    enableStepTrace: true,
    enableSSEAsString: true,
    useLegacyAnswersToolNames: false,
    reasoningAgentFlowType: "simple",
    responseSchemaVersion: "v2",
    SandboxComputePool: "CODE_SANDBOX",
    SandboxExternalAccessIntegrations: "allow_all_access_integration",
    codingAgent: {
      SandboxEnable: true,
      SandboxTools: "*",
      UseZNSforCNGSandbox: true,
      HeadlessSandboxClient: true,
      originApplication: nestedOriginApplication,
      sessionId: `cloud-agent-mcp:${agentId}`,
      systemPromptInternal: {
        version: "v2",
        prompt: systemPrompt,
        attributes: {
          WorkingDirectory: "/workspace",
          Platform: "snowflake workspace",
          OS: "snowflake workspace",
          IsGitRepo: mountWorkspace ? "Yes." : "No.",
        },
      },
      summarizationTriggerThreshold: 0,
      disabledServerTools: ["system_instructions", "system_sql_reflection"],
    },
    EnableSandboxPermissionSystem: false,
    EnableToolPermissionSystem: false,
  };

  if (mountWorkspace) {
    experimental.VStages = [
      {
        stage_name: stageName,
        vstage_namespace: "workspace",
        mount_path: "/workspace",
      },
    ];
  }

  const body = {
    models: {
      orchestration: model,
    },
    stream: true,
    origin_application: originApplication,
    thread_id: threadId,
    parent_message_id: parentMessageId,
    messages: [
      {
        role: "user",
        content: [{ type: "text", text: prompt }],
      },
    ],
    experimental,
  };

  if (instructions && typeof instructions === "object") {
    const agentInstructions = {};
    if (instructions.orchestration) {
      agentInstructions.orchestration = instructions.orchestration;
    }
    if (instructions.response) {
      agentInstructions.response = instructions.response;
    }
    if (Object.keys(agentInstructions).length > 0) {
      body.instructions = agentInstructions;
    }
  }

  if (mcpServers.length > 0) {
    body.mcp_servers = mcpServers.map((server) => ({
      server_spec: {
        name: requireNonEmpty(server.name, "mcp_servers[].name"),
        type: server.type ?? "EXTERNAL_MCP",
      },
    }));
  }

  return body;
}

function requireNonEmpty(value, label) {
  if (!value || typeof value !== "string") {
    throw new Error(`${label} is required`);
  }
  return value;
}
