export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type DefectEvent = {
  station_id: string;
  track: string;
  defect_class: string;
  confidence: number;
  latency_ms: number;
  timestamp: number;
  protocol: string;
  adapter_id?: string;
};

export type TelemetryReading = {
  station_id: string;
  metric: string;
  value: number;
  unit: string;
  timestamp: number;
  quality: string;
  protocol: string;
};

export async function fetchEvents(limit = 20): Promise<DefectEvent[]> {
  try {
    const r = await fetch(`${API_URL}/events?limit=${limit}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`events ${r.status}`);
    return await r.json();
  } catch {
    // fallback demo data
    return [
      { station_id: "line2-cluster1-gauge3", track: "line", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, timestamp: Date.now() / 1000, protocol: "camera" },
      { station_id: "line1-press-04", track: "line", defect_class: "vib_high", confidence: 0.87, latency_ms: 31, timestamp: Date.now() / 1000, protocol: "opcua" },
      { station_id: "line3-molder-02", track: "line", defect_class: "none", confidence: 0.96, latency_ms: 18, timestamp: Date.now() / 1000, protocol: "modbus" },
    ];
  }
}

export async function ackEvent(station_id: string, defect_class: string, operator_id = "op-01"): Promise<void> {
  try {
    await fetch(`${API_URL}/ack`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ station_id, defect_class, operator_id, ts: Date.now() }),
    });
  } catch {
    // offline: store locally
    if (typeof window !== "undefined") {
      const q = JSON.parse(localStorage.getItem("tantu_ack_queue") || "[]");
      q.push({ station_id, defect_class, operator_id, ts: Date.now() });
      localStorage.setItem("tantu_ack_queue", JSON.stringify(q));
    }
  }
}

export async function askCopilot(question: string, plant_id = "plant-demo-01", lang = "en"): Promise<{ answer: string; vernacular?: Record<string, string> }> {
  try {
    const r = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, plant_id, lang }),
    });
    if (!r.ok) throw new Error(`ask ${r.status}`);
    return await r.json();
  } catch {
    return { answer: `Stub: '${question}' → check valve 3, vibration up 12% (grounded).`, vernacular: { en: "Check valve 3" } };
  }
}

export async function fetchHealth(): Promise<{ status: string }> {
  try {
    const r = await fetch(`${API_URL}/health`, { cache: "no-store" });
    return await r.json();
  } catch {
    return { status: "offline" };
  }
}

export async function fetchMetrics(): Promise<{ walk_reads: { before: number; after: number }[]; opex: number; uptime: number }> {
  try {
    const r = await fetch(`${API_URL}/metrics`, { cache: "no-store" });
    if (!r.ok) throw new Error("metrics");
    return await r.json();
  } catch {
    return {
      walk_reads: [{ before: 48, after: 6 }],
      opex: 18000,
      uptime: 99.2,
    };
  }
}
