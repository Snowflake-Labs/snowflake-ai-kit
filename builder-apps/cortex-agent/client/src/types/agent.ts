/**
 * TypeScript types for the Cortex Agent App.
 */

export interface AgentEvent {
  type: 'text' | 'sql' | 'chart' | 'tool_use' | 'status' | 'metadata' | 'error' | 'done';
  content: string;
  sql?: string;
  chart_spec?: string;
  tool_name?: string;
  tool_input?: string;
  conversation_id?: string;
  message_id?: string;
}

export interface AgentInfo {
  name: string;
  database: string;
  schema_name: string;
  comment: string | null;
  created_on: string | null;
}

export interface AgentDescription {
  sample_questions: string[];
}

export interface Conversation {
  id: string;
  agent_name: string;
  title: string;
  thread_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  events?: AgentEvent[];
  timestamp: string;
}
