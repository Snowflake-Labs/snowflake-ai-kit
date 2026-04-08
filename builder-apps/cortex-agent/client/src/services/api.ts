/**
 * API client for the Cortex Agent App backend.
 */

import type { AgentInfo, AgentDescription, Conversation } from '../types/agent';

const BASE = '/api';

export async function fetchAgents(): Promise<AgentInfo[]> {
  const res = await fetch(`${BASE}/agents`);
  if (!res.ok) throw new Error(`Failed to fetch agents: ${res.statusText}`);
  return res.json();
}

export async function fetchAgentDescription(
  database: string,
  schema: string,
  name: string,
): Promise<AgentDescription> {
  const res = await fetch(`${BASE}/agents/${database}/${schema}/${name}/describe`);
  if (!res.ok) throw new Error(`Failed to describe agent: ${res.statusText}`);
  return res.json();
}

export async function fetchConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/conversations`);
  if (!res.ok) throw new Error(`Failed to fetch conversations: ${res.statusText}`);
  return res.json();
}

/**
 * Send a message to a Cortex Agent. Returns a readable SSE stream.
 */
export async function sendMessage(
  message: string,
  agentName: string,
  database: string,
  schemaName: string,
  conversationId?: string,
): Promise<Response> {
  return fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      agent_name: agentName,
      database,
      schema_name: schemaName,
      conversation_id: conversationId,
    }),
  });
}
