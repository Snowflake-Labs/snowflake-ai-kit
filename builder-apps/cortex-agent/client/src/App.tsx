import React, { useState, useCallback, useRef, useEffect } from 'react';
import { AgentSelector, agentFQN } from './components/AgentSelector';
import { ChatInput } from './components/ChatInput';
import { ChatMessage } from './components/ChatMessage';
import { ArchitectureDiagram } from './components/ArchitectureDiagram';
import { useSSEStream } from './hooks/useSSEStream';
import { fetchAgents, fetchAgentDescription, sendMessage } from './services/api';
import type { ChatMessage as ChatMsg, AgentInfo } from './types/agent';

export default function App() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [selectedFQN, setSelectedFQN] = useState<string | null>(null);
  const [activeConversation, setActiveConversation] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [sampleQuestions, setSampleQuestions] = useState<string[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const { events, isStreaming, error, startStream, reset: resetStream } = useSSEStream();

  // Resolve the selected agent object from FQN
  const selectedAgent = agents.find((a) => agentFQN(a) === selectedFQN) || null;

  // Load agents on mount
  useEffect(() => {
    fetchAgents()
      .then((result) => {
        setAgents(result);
        if (result.length > 0) {
          setSelectedFQN(agentFQN(result[0]));
        }
      })
      .catch((err) => console.error('Failed to load agents:', err))
      .finally(() => setAgentsLoading(false));
  }, []);

  // Fetch sample questions when selected agent changes
  useEffect(() => {
    if (!selectedAgent) {
      setSampleQuestions([]);
      return;
    }
    fetchAgentDescription(selectedAgent.database, selectedAgent.schema_name, selectedAgent.name)
      .then((desc) => setSampleQuestions(desc.sample_questions || []))
      .catch(() => setSampleQuestions([]));
  }, [selectedAgent]);

  // Auto-scroll on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, events]);

  // Accumulate streaming events into assistant message
  useEffect(() => {
    if (events.length === 0) return;

    const textEvents = events.filter((e) => e.type === 'text');
    const content = textEvents.map((e) => e.content).join('');

    const convId = events.find((e) => e.conversation_id)?.conversation_id;
    if (convId && !activeConversation) {
      setActiveConversation(convId);
    }

    setMessages((prev) => {
      const copy = [...prev];
      const lastIdx = copy.length - 1;
      if (lastIdx >= 0 && copy[lastIdx].role === 'assistant') {
        copy[lastIdx] = { ...copy[lastIdx], content, events: [...events] };
      }
      return copy;
    });
  }, [events, activeConversation]);

  const handleSend = useCallback(
    async (message: string) => {
      if (!selectedAgent) return;

      const userMsg: ChatMsg = {
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };

      const assistantMsg: ChatMsg = {
        role: 'assistant',
        content: '',
        events: [],
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      resetStream();

      try {
        const response = await sendMessage(
          message,
          selectedAgent.name,
          selectedAgent.database,
          selectedAgent.schema_name,
          activeConversation || undefined,
        );
        if (!response.ok) {
          const err = await response.text();
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { ...copy[copy.length - 1], content: `Error: ${err}` };
            return copy;
          });
          return;
        }
        startStream(response);
      } catch (err) {
        setMessages((prev) => {
          const copy = [...prev];
          copy[copy.length - 1] = {
            ...copy[copy.length - 1],
            content: `Connection error: ${err instanceof Error ? err.message : String(err)}`,
          };
          return copy;
        });
      }
    },
    [selectedAgent, activeConversation, startStream, resetStream],
  );

  return (
    <div className="app-layout">
      <div className="sidebar">
        <AgentSelector
          agents={agents}
          selectedFQN={selectedFQN}
          onSelect={setSelectedFQN}
          loading={agentsLoading}
        />
      </div>
      <div className="main-content">
        <div className="header">
          <div className="header-title">
            <h1>Snowflake Cortex Agent</h1>
            <a
              className="app-readme-link"
              href="https://github.com/Snowflake-Labs/snowflake-ai-kit/tree/main/builder-apps/cortex-agent"
              target="_blank"
              rel="noopener noreferrer"
            >
              Learn more about the app ↗
            </a>
          </div>
          {isStreaming && (
            <div className="streaming-indicator">
              <div className="dot" />
              <div className="dot" />
              <div className="dot" />
            </div>
          )}
        </div>
        <div className="chat-container">
          {messages.length === 0 && (
            <div className="empty-state">
              <h2>Snowflake Cortex Agent App</h2>
              <p>
                Ask questions about your data using natural language.
              </p>
              <ArchitectureDiagram />
              {selectedFQN ? (
                sampleQuestions.length > 0 ? (
                  <div className="sample-questions">
                    <span style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>Try asking:</span>
                    {sampleQuestions.map((q, i) => (
                      <button
                        key={i}
                        className="sample-question"
                        onClick={() => handleSend(q)}
                        disabled={isStreaming}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>
                    Agent: {selectedAgent?.name ?? selectedFQN}
                  </div>
                )
              ) : (
                <div style={{ color: 'var(--sf-text-muted)', fontSize: 13 }}>
                  Select an agent to get started
                </div>
              )}
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} message={msg} />
          ))}
          {error && (
            <div style={{ color: 'var(--sf-red)', padding: '8px 24px', fontSize: 14 }}>
              Stream error: {error}
            </div>
          )}
          <div ref={chatEndRef} />
        </div>
        <ChatInput onSend={handleSend} disabled={isStreaming || !selectedAgent} />
      </div>
    </div>
  );
}
