export interface McpServerConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

export type CortexModel =
  | "auto"
  | "claude-opus-4-6"
  | "claude-sonnet-4-6"
  | "claude-opus-4-5"
  | "claude-sonnet-4-5"
  | "claude-4-sonnet"
  | "openai-gpt-5.2"
  | (string & {});
