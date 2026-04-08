/**
 * Hook for consuming SSE streams from the Cortex Agent API.
 */

import { useCallback, useRef, useState } from 'react';
import type { AgentEvent } from '../types/agent';

interface UseSSEStreamReturn {
  events: AgentEvent[];
  isStreaming: boolean;
  error: string | null;
  startStream: (response: Response) => void;
  reset: () => void;
}

export function useSSEStream(): UseSSEStreamReturn {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setEvents([]);
    setError(null);
    abortRef.current?.abort();
  }, []);

  const startStream = useCallback((response: Response) => {
    if (!response.body) {
      setError('No response body');
      return;
    }

    setIsStreaming(true);
    setError(null);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const read = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              try {
                const parsed: AgentEvent = JSON.parse(data);
                if (parsed.type === 'done') {
                  setIsStreaming(false);
                  return;
                }
                // Skip metadata events from display
                if (parsed.type === 'metadata' || parsed.type === 'status') {
                  continue;
                }
                setEvents((prev) => [...prev, parsed]);
              } catch {
                // Skip malformed JSON
              }
            }
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message);
        }
      } finally {
        setIsStreaming(false);
      }
    };

    read();
  }, []);

  return { events, isStreaming, error, startStream, reset };
}
