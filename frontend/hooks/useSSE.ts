"use client";
import { useEffect, useRef, useState } from "react";
import type { DefectEvent } from "@/lib/api";

export function useSSE(url: string | null, enabled = true) {
  const [events, setEvents] = useState<DefectEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const fallbackRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled || !url) return;
    let closed = false;

    const connect = () => {
      if (closed) return;
      try {
        const es = new EventSource(url);
        esRef.current = es;
        es.onopen = () => { setConnected(true); setError(null); };
        es.onerror = () => {
          setConnected(false);
          setError("SSE disconnected — retrying via polling fallback");
          es.close();
          // fallback poll every 2s
          if (fallbackRef.current) window.clearInterval(fallbackRef.current);
          fallbackRef.current = window.setInterval(async () => {
            try {
              const r = await fetch(url.replace("/stream", ""), { cache: "no-store" });
              if (r.ok) {
                const data: DefectEvent[] = await r.json();
                if (data.length) setEvents((prev) => [...data.slice(0, 3), ...prev].slice(0, 50));
              }
            } catch {}
          }, 2000);
          // retry SSE after 5s
          setTimeout(() => { if (!closed) connect(); }, 5000);
        };
        es.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            const ev: DefectEvent = Array.isArray(data) ? data[0] : data;
            if (ev && ev.station_id) {
              setEvents((prev) => [ev, ...prev].slice(0, 50));
            }
          } catch {}
        };
        // custom event: defect
        (es as any).addEventListener?.("defect", (e: MessageEvent) => {
          try {
            const ev = JSON.parse(e.data);
            setEvents((prev) => [ev, ...prev].slice(0, 50));
          } catch {}
        });
      } catch (e: any) {
        setError(e.message);
      }
    };

    connect();
    return () => {
      closed = true;
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      if (fallbackRef.current) { window.clearInterval(fallbackRef.current); fallbackRef.current = null; }
      setConnected(false);
    };
  }, [url, enabled]);

  return { events, connected, error, setEvents };
}
