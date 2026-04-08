import { useEffect, useRef } from 'react';
import embed from 'vega-embed';

interface Props {
  spec: string;
}

export function VegaChart({ spec }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !spec) return;

    let parsed: Record<string, unknown>;
    try {
      // The spec may be double-JSON-encoded (string within a string).
      // Unwrap until we get an actual object.
      let result: unknown = spec;
      while (typeof result === 'string') {
        result = JSON.parse(result);
      }
      parsed = result as Record<string, unknown>;
    } catch {
      return;
    }

    // Force responsive width, keep aspect ratio reasonable
    parsed.width = 'container';
    parsed.autosize = { type: 'fit', contains: 'padding' };

    const el = containerRef.current;
    embed(el, parsed as never, {
      actions: { export: true, source: false, compiled: false, editor: false },
      theme: 'dark',
      renderer: 'svg',
    }).catch((err) => console.warn('Vega render error:', err));

    return () => {
      // Clean up on unmount
      el.innerHTML = '';
    };
  }, [spec]);

  return <div ref={containerRef} className="vega-chart-container" />;
}
