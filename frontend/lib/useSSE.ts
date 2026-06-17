"use client";

import { useEffect, useRef, useCallback } from "react";

export interface SSEEvent {
  event: string;
  data: Record<string, unknown>;
}

export function useSSE(
  url: string | null,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Event) => void
) {
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;

  const connect = useCallback((streamUrl: string) => {
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (e) => {
      try {
        const parsed: SSEEvent = JSON.parse(e.data);
        onEventRef.current(parsed);
      } catch {
        // ignore malformed events
      }
    };

    eventSource.onerror = (e) => {
      onErrorRef.current?.(e);
      eventSource.close();
    };

    return eventSource;
  }, []);

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!url) return;

    eventSourceRef.current?.close();
    const es = connect(url);
    eventSourceRef.current = es;

    return () => {
      es.close();
    };
  }, [url, connect]);

  return eventSourceRef;
}
