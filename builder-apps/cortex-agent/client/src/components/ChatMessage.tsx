import React from 'react';
import type { ChatMessage as ChatMessageType } from '../types/agent';
import { VegaChart } from './VegaChart';

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  const toolEvents = message.events?.filter((e) => e.type === 'tool_use') || [];
  const sqlEvents = message.events?.filter((e) => e.type === 'sql') || [];
  const chartEvents = message.events?.filter((e) => e.type === 'chart') || [];

  return (
    <div className={`chat-message ${message.role}`}>
      <div className="role-label">{message.role === 'user' ? 'You' : 'Agent'}</div>

      {/* Tool calls */}
      {toolEvents.map((e, i) => (
        <div key={`tool-${i}`} className="tool-output">
          <div className="tool-name">{e.tool_name || 'Tool'}</div>
          {e.tool_input && (
            <pre>{e.tool_input}</pre>
          )}
        </div>
      ))}

      {/* SQL results */}
      {sqlEvents.map((e, i) => (
        <div key={`sql-${i}`} className="sql-block">
          <div className="sql-label">SQL</div>
          <pre><code>{e.sql}</code></pre>
        </div>
      ))}

      {/* Text content */}
      <div dangerouslySetInnerHTML={{ __html: simpleMarkdown(message.content) }} />

      {/* Charts */}
      {chartEvents.map((e, i) => (
        <div key={`chart-${i}`} className="chart-block">
          <div className="chart-label">Chart</div>
          {e.chart_spec && <VegaChart spec={e.chart_spec} />}
        </div>
      ))}
    </div>
  );
}

/** Minimal markdown to HTML (code blocks, bold, inline code). */
function simpleMarkdown(text: string): string {
  return text
    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br/>');
}
