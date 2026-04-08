import React from 'react';
import type { AgentInfo } from '../types/agent';

/** Build a fully qualified agent identifier. */
export function agentFQN(a: AgentInfo): string {
  return `${a.database}.${a.schema_name}.${a.name}`;
}

interface Props {
  agents: AgentInfo[];
  selectedFQN: string | null;
  onSelect: (fqn: string) => void;
  loading: boolean;
}

export function AgentSelector({ agents, selectedFQN, onSelect, loading }: Props) {
  if (loading) {
    return (
      <div className="agent-selector">
        <label>Agent</label>
        <select disabled>
          <option>Loading agents...</option>
        </select>
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className="agent-selector">
        <label>Agent</label>
        <select disabled>
          <option>No agents found</option>
        </select>
        <div className="agent-hint">
          Create a Cortex Agent in your account, or run setup.sql
        </div>
      </div>
    );
  }

  const selected = agents.find((a) => agentFQN(a) === selectedFQN);

  return (
    <div className="agent-selector">
      <label>Agent</label>
      <select value={selectedFQN || ''} onChange={(e) => onSelect(e.target.value)}>
        {!selectedFQN && <option value="">Select an agent...</option>}
        {agents.map((a) => {
          const fqn = agentFQN(a);
          return (
            <option key={fqn} value={fqn}>
              {a.name}
            </option>
          );
        })}
      </select>
    </div>
  );
}
