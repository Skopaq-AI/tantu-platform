export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------- types (typed contracts for all backend APIs) ----------
export type DefectEvent = {
  station_id: string;
  track: string;
  defect_class: string;
  confidence: number;
  latency_ms: number;
  timestamp: number; // epoch seconds
  protocol: "opcua" | "modbus" | "mqtt" | "mtconnect" | "ethernet_ip" | "camera" | string;
  adapter_id?: string;
  quality?: string;
};

export type TelemetryReading = {
  station_id: string;
  metric: string;
  value: number;
  unit: string;
  timestamp: number;
  quality: "good" | "uncertain" | "bad" | string;
  protocol: string;
};

export type HealthResponse = {
  status: "ok" | "degraded" | "offline" | string;
  version?: string;
  uptime_s?: number;
  nats?: string;
  qdrant?: string;
};

export type MetricsResponse = {
  walk_reads: { before: number; after: number }[];
  opex: number;
  uptime: number;
  mttd_min?: number;
  mttr_min?: number;
  p95_latency_ms?: number;
};

export type PollResponse = {
  readings: TelemetryReading[];
  events: DefectEvent[];
};

export type AskRequest = { question: string; plant_id: string; lang: string };
export type AskResponse = {
  answer: string;
  vernacular?: Record<string, string>;
  sources?: { id: string; title: string; snippet?: string }[];
  grounded?: boolean;
};

export type AckRequest = { station_id: string; defect_class: string; operator_id: string; ts: number };
export type AckResponse = { ok: boolean; queued?: boolean };

// ---------- helpers ----------
async function safeFetch<T>(url: string, opts?: RequestInit, fallback?: T): Promise<T> {
  try {
    const r = await fetch(url, { cache: "no-store", ...opts });
    if (!r.ok) throw new Error(`${url} ${r.status}`);
    return (await r.json()) as T;
  } catch (e) {
    if (fallback !== undefined) return fallback;
    throw e;
  }
}

function demoEvents(): DefectEvent[] {
  const now = Date.now() / 1000;
  return [
    { station_id: "line2-cluster1-gauge3", track: "line", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, timestamp: now, protocol: "camera", adapter_id: "cam-01", quality: "good" },
    { station_id: "line1-press-04", track: "line", defect_class: "vib_high", confidence: 0.87, latency_ms: 31, timestamp: now, protocol: "opcua", adapter_id: "opc-01", quality: "good" },
    { station_id: "line3-molder-02", track: "line", defect_class: "none", confidence: 0.96, latency_ms: 18, timestamp: now, protocol: "modbus", adapter_id: "mod-01", quality: "good" },
    { station_id: "line2-conveyor-11", track: "line", defect_class: "thermal_high", confidence: 0.81, latency_ms: 27, timestamp: now, protocol: "mqtt", adapter_id: "mqtt-01", quality: "uncertain" },
    { station_id: "fab-etch-07", track: "fab", defect_class: "solder_void", confidence: 0.89, latency_ms: 35, timestamp: now, protocol: "mtconnect", adapter_id: "mtc-01", quality: "good" },
    { station_id: "line1-robot-03", track: "line", defect_class: "none", confidence: 0.98, latency_ms: 14, timestamp: now, protocol: "ethernet_ip", adapter_id: "eip-01", quality: "good" },
  ];
}

// ---------- API surface ----------

/** GET /health */
export async function fetchHealth(): Promise<HealthResponse> {
  return safeFetch<HealthResponse>(`${API_URL}/health`, undefined, { status: "offline" });
}

/** GET /events?limit= */
export async function fetchEvents(limit = 20): Promise<DefectEvent[]> {
  return safeFetch<DefectEvent[]>(`${API_URL}/events?limit=${limit}`, undefined, demoEvents().slice(0, limit));
}

/** GET /poll — normalized telemetry poll (OPC-UA / Modbus / MQTT unified) */
export async function pollTelemetry(limit = 20): Promise<PollResponse> {
  // try canonical /poll, fall back to /telemetry/poll or demo
  try {
    const r = await fetch(`${API_URL}/poll?limit=${limit}`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as PollResponse;
  } catch {}
  try {
    const r = await fetch(`${API_URL}/telemetry/poll?limit=${limit}`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as PollResponse;
  } catch {}
  // fallback: synthesize from demo events as TelemetryReading
  const evs = demoEvents().slice(0, limit);
  return {
    readings: evs.map((e) => ({
      station_id: e.station_id,
      metric: e.defect_class === "vib_high" ? "vibration" : e.defect_class === "pressure_drift" ? "pressure" : "temperature",
      value: e.defect_class === "none" ? 42 + Math.random() * 5 : 68 + Math.random() * 10,
      unit: e.defect_class === "vib_high" ? "mm/s" : e.defect_class === "pressure_drift" ? "bar" : "°C",
      timestamp: e.timestamp,
      quality: e.quality || "good",
      protocol: e.protocol,
    })),
    events: evs,
  };
}

/** POST /ask — grounded RAG copilot */
export async function askCopilot(question: string, plant_id = "plant-demo-01", lang = "en"): Promise<AskResponse> {
  return safeFetch<AskResponse>(
    `${API_URL}/ask`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, plant_id, lang } satisfies AskRequest),
    },
    {
      answer: `Grounded stub for '${question}' → check valve 3, bearing vibration up 12% in last 5 min (NATS: camera/thermal_high, source: tag-map line2).`,
      vernacular: { en: "Check valve 3" },
      sources: [{ id: "tag-map:line2", title: "Line 2 tag map" }],
      grounded: true,
    }
  );
}

/** POST /ack — one-button ack (optimistic) */
export async function ackEvent(station_id: string, defect_class: string, operator_id = "op-01"): Promise<AckResponse> {
  try {
    const r = await fetch(`${API_URL}/ack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ station_id, defect_class, operator_id, ts: Date.now() } satisfies AckRequest),
    });
    if (!r.ok) throw new Error(`ack ${r.status}`);
    const j = await r.json().catch(() => ({ ok: true }));
    return { ok: true, ...j };
  } catch {
    // offline queue — optimistic
    if (typeof window !== "undefined") {
      try {
        const q: AckRequest[] = JSON.parse(localStorage.getItem("tantu_ack_queue") || "[]");
        q.push({ station_id, defect_class, operator_id, ts: Date.now() });
        localStorage.setItem("tantu_ack_queue", JSON.stringify(q.slice(-50)));
      } catch {}
    }
    return { ok: true, queued: true };
  }
}

/** GET /metrics */
export async function fetchMetrics(): Promise<MetricsResponse> {
  return safeFetch<MetricsResponse>(
    `${API_URL}/metrics`,
    undefined,
    {
      walk_reads: [{ before: 48, after: 6 }],
      opex: 18000,
      uptime: 99.2,
      mttd_min: 3,
      mttr_min: 18,
      p95_latency_ms: 38,
    }
  );
}

/** GET /events/stream — SSE (EventSource) helper URL */
export function getSSEUrl(): string {
  return `${API_URL}/events/stream`;
}

/** Replay queued acks when back online */
export async function flushAckQueue(): Promise<number> {
  if (typeof window === "undefined") return 0;
  let q: AckRequest[] = [];
  try {
    q = JSON.parse(localStorage.getItem("tantu_ack_queue") || "[]");
  } catch { return 0; }
  if (!q.length) return 0;
  let flushed = 0;
  for (const a of q) {
    try {
      await fetch(`${API_URL}/ack`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(a) });
      flushed++;
    } catch {}
  }
  if (flushed) {
    const remaining = q.slice(flushed);
    localStorage.setItem("tantu_ack_queue", JSON.stringify(remaining));
  }
  return flushed;
}
