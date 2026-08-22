export const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://8.233.79.240";

export function isDemoEnabled(): boolean {
  return process.env.NEXT_PUBLIC_DEMO === "true";
}

// ---------- auth token helpers ----------
// Reads access token from memory via localStorage + cookie sync.
// Used to attach Authorization: Bearer to all fetches and to handle 401 refresh.
function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const t = localStorage.getItem("tantu_access") || localStorage.getItem("access_token");
    if (t) return t;
    // fallback: try cookie (tantu_access)
    const m = document.cookie.match(/(?:^|;\s*)tantu_access=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    const m2 = document.cookie.match(/(?:^|;\s*)access_token=([^;]+)/);
    if (m2) return decodeURIComponent(m2[1]);
  } catch {}
  return null;
}

function authHeaders(): Record<string, string> {
  const tok = getAuthToken();
  if (tok) return { Authorization: `Bearer ${tok}` };
  return {};
}

export function getStoredAccessToken(): string | null {
  return getAuthToken();
}

export async function refreshAccessToken(): Promise<string | null> {
  try {
    const cur = getAuthToken();
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...(cur ? { Authorization: `Bearer ${cur}` } : {}) },
    });
    if (!res.ok) return null;
    const data = await res.json().catch(() => ({}));
    const tok = data.access_token || data.accessToken || data.token;
    if (tok) {
      try {
        localStorage.setItem("tantu_access", tok);
        document.cookie = `tantu_access=${tok}; path=/; max-age=3600; SameSite=Lax`;
        document.cookie = `access_token=${tok}; path=/; max-age=3600; SameSite=Lax`;
      } catch {}
      return tok as string;
    }
    return cur;
  } catch {
    return null;
  }
}

// try fetch once, on 401 attempt refresh and retry once
async function fetchWithAuth(input: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> | undefined) };
  const tokHeaders = authHeaders();
  for (const [k, v] of Object.entries(tokHeaders)) {
    if (!headers[k] && !headers[k.toLowerCase()]) headers[k] = v;
  }
  const res = await fetch(input, { ...init, headers, credentials: (init.credentials as any) || "include" });
  if (res.status === 401 && retry) {
    const newTok = await refreshAccessToken();
    if (newTok) {
      const retryHeaders: Record<string, string> = { ...(init.headers as Record<string, string> | undefined), Authorization: `Bearer ${newTok}` };
      return fetch(input, { ...init, headers: retryHeaders, credentials: (init.credentials as any) || "include" });
    }
  }
  return res;
}

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
    const r = await fetchWithAuth(url, { cache: "no-store", ...opts }, true);
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

/** GET /events?limit= — demo fallback gated behind NEXT_PUBLIC_DEMO */
export async function fetchEvents(limit = 20): Promise<DefectEvent[]> {
  const fallback = isDemoEnabled() ? demoEvents().slice(0, limit) : undefined;
  return safeFetch<DefectEvent[]>(`${API_URL}/events?limit=${limit}`, undefined, fallback as any);
}

/** GET /poll — normalized telemetry poll (OPC-UA / Modbus / MQTT unified) — demo synthesis gated behind DEMO */
export async function pollTelemetry(limit = 20): Promise<PollResponse> {
  try {
    const r = await fetchWithAuth(`${API_URL}/poll?limit=${limit}`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as PollResponse;
  } catch {}
  try {
    const r = await fetchWithAuth(`${API_URL}/telemetry/poll?limit=${limit}`, { cache: "no-store" });
    if (r.ok) return (await r.json()) as PollResponse;
  } catch {}
  if (!isDemoEnabled()) throw new Error("poll telemetry unavailable");
  // demo fallback: synthesize from demo events as TelemetryReading
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

/** POST /ask — grounded RAG copilot — demo stub gated behind DEMO */
export async function askCopilot(question: string, plant_id = "plant-demo-01", lang = "en"): Promise<AskResponse> {
  const fallback = isDemoEnabled()
    ? {
        answer: `Grounded stub for '${question}' → check valve 3, bearing vibration up 12% in last 5 min (NATS: camera/thermal_high, source: tag-map line2).`,
        vernacular: { en: "Check valve 3" },
        sources: [{ id: "tag-map:line2", title: "Line 2 tag map" }],
        grounded: true,
      }
    : undefined;
  return safeFetch<AskResponse>(
    `${API_URL}/ask`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question, plant_id, lang } satisfies AskRequest),
    },
    fallback as any
  );
}

/** POST /ack — one-button ack (optimistic) */
export async function ackEvent(station_id: string, defect_class: string, operator_id = "op-01"): Promise<AckResponse> {
  try {
    const r = await fetchWithAuth(`${API_URL}/ack`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
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

/** GET /metrics — demo fallback gated behind DEMO */
export async function fetchMetrics(): Promise<MetricsResponse> {
  const fallback = isDemoEnabled()
    ? {
        walk_reads: [{ before: 48, after: 6 }],
        opex: 18000,
        uptime: 99.2,
        mttd_min: 3,
        mttr_min: 18,
        p95_latency_ms: 38,
      }
    : undefined;
  return safeFetch<MetricsResponse>(
    `${API_URL}/metrics`,
    { headers: { ...authHeaders() } },
    fallback as any
  );
}

/** GET /events/stream — SSE (EventSource) helper URL */
export function getSSEUrl(): string {
  // SSE via EventSource cannot send Authorization header; token is sent as query param fallback
  const tok = getAuthToken();
  const base = `${API_URL}/events/stream`;
  if (tok && typeof window !== "undefined") {
    // attach as query for backends that accept it
    return `${base}?token=${encodeURIComponent(tok)}`;
  }
  return base;
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
      await fetchWithAuth(`${API_URL}/ack`, { method: "POST", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(a) });
      flushed++;
    } catch {}
  }
  if (flushed) {
    const remaining = q.slice(flushed);
    localStorage.setItem("tantu_ack_queue", JSON.stringify(remaining));
  }
  return flushed;
}

// ---- auth-related API helpers (used by auth context & pages) ----
export async function apiLogin(email: string, password: string): Promise<{ access_token: string; user?: any }> {
  const r = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || e.message || `Login failed (${r.status})`);
  }
  return r.json();
}
export async function apiSignup(payload: { orgName: string; email: string; password: string; name?: string }) {
  const r = await fetch(`${API_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ org_name: payload.orgName, email: payload.email, password: payload.password, name: payload.name }),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(e.detail || e.message || `Signup failed (${r.status})`);
  }
  return r.json();
}
export async function apiMe(token?: string) {
  const h: Record<string, string> = {};
  const t = token || getAuthToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  const r = await fetch(`${API_URL}/auth/me`, { headers: h, credentials: "include", cache: "no-store" });
  if (!r.ok) throw new Error(`me ${r.status}`);
  return r.json();
}
