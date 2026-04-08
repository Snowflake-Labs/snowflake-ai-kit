import React from 'react';
import './ArchitectureDiagram.css';

export function ArchitectureDiagram() {
  return (
    <div className="arch-diagram">
      <div className="arch-row">
        <div className="arch-box">
          <div className="arch-box-label">React Frontend</div>
          <div className="arch-tags">
            <span>Agent Selector</span>
            <span>Chat UI</span>
            <span>SQL Display</span>
            <span>Charts</span>
          </div>
        </div>
        <div className="arch-connector-h">
          <span>SSE</span>
        </div>
        <div className="arch-box">
          <div className="arch-box-label">FastAPI Backend</div>
          <div className="arch-tags">
            <span>/api/agents</span>
            <span>/api/chat</span>
            <span>/api/conversations</span>
          </div>
        </div>
        <div className="arch-connector-h">
          <span>REST</span>
        </div>
        <div className="arch-box arch-box-highlight">
          <div className="arch-box-label">Cortex Agents API</div>
          <div className="arch-tags">
            <span>Analyst</span>
            <span>Search</span>
            <span>Charts</span>
          </div>
        </div>
      </div>
      <div className="arch-subtitle">
        No external API keys — runs entirely on Snowflake
      </div>
    </div>
  );
}
