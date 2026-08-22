"use client";
import { useEffect, useState, useMemo } from "react";
import { motion } from "@/lib/motion";
import { toast } from "@/lib/toast";
import { useI18n, t } from "@/lib/i18n";
import { useSSE } from "@/hooks/useSSE";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, protocolColor } from "@/lib/utils";
import { askCopilot, ackEvent, DefectEvent, getSSEUrl, API_URL, isDemoEnabled } from "@/lib/api";
import { FFTChart, WalkTrendChart } from "@/components/charts/FFTChart";
import { RoleGuard } from "@/components/RoleGuard";
import { LayoutGrid, Activity, AlertTriangle, Check, Search, Filter, Radio, Sparkles, Copy } from "lucide-react";

export default function MaintenancePage() {
  const { lang } = useI18n();
  const SSE_URL = getSSEUrl();
  const sse = useSSE(SSE_URL, true);
  const [pollEvents, setPollEvents] = useState<DefectEvent[]>([]);
  const [query, setQuery] = useState("");
  const [protocolFilter, setProtocolFilter] = useState<string>("all");
  const [selected, setSelected] = useState<DefectEvent | null>(null);
  const [copilotQ, setCopilotQ] = useState("why did line 2 slow down?");
  const [copilotA, setCopilotA] = useState("");
  const [ackedIds, setAckedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 700);
    return () => clearTimeout(t);
  }, []);

  // fallback poll if SSE not connected — fetch real /events
  useEffect(() => {
    if (sse.connected && sse.events.length > 0) return;
    const id = setInterval(async () => {
      try {
        const r = await fetch(`${API_URL}/events?limit=12`, { cache: "no-store" });
        if (r.ok) setPollEvents(await r.json());
      } catch {}
    }, 2500);
    return () => clearInterval(id);
  }, [sse.connected, sse.events.length]);

  const events: DefectEvent[] = useMemo(() => {
    const merged = sse.events.length ? sse.events : pollEvents;
    if (merged.length) return merged;
    if (!isDemoEnabled()) return [];
    // demo fallback gated behind DEMO flag
    const now = Date.now() / 1000;
    return [
      { station_id: "line2-cluster1-gauge3", track: "line", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, timestamp: now, protocol: "camera", adapter_id: "cam-01" },
      { station_id: "line1-press-04", track: "line", defect_class: "vib_high", confidence: 0.87, latency_ms: 31, timestamp: now, protocol: "opcua", adapter_id: "opc-01" },
      { station_id: "line3-molder-02", track: "line", defect_class: "none", confidence: 0.96, latency_ms: 18, timestamp: now, protocol: "modbus", adapter_id: "mod-01" },
      { station_id: "line2-conveyor-11", track: "line", defect_class: "thermal_high", confidence: 0.81, latency_ms: 27, timestamp: now, protocol: "mqtt", adapter_id: "mqtt-01" },
      { station_id: "fab-etch-07", track: "fab", defect_class: "solder_void", confidence: 0.89, latency_ms: 35, timestamp: now, protocol: "mtconnect", adapter_id: "mtc-01" },
      { station_id: "line1-robot-03", track: "line", defect_class: "none", confidence: 0.98, latency_ms: 14, timestamp: now, protocol: "ethernet_ip", adapter_id: "eip-01" },
    ];
  }, [sse.events, pollEvents]);

  const filtered = events.filter((e) => {
    if (protocolFilter !== "all" && e.protocol !== protocolFilter) return false;
    if (query && !`${e.station_id} ${e.defect_class} ${e.protocol}`.toLowerCase().includes(query.toLowerCase())) return false;
    return true;
  });

  const handleAck = async (e: DefectEvent) => {
    setAckedIds((s) => new Set([...s, e.station_id]));
    toast.success(t("vernacular_ack_done", lang), { description: e.station_id });
    if (navigator.vibrate) navigator.vibrate(40);
    await ackEvent(e.station_id, e.defect_class);
  };

  const handleAsk = async () => {
    if (!copilotQ.trim()) return;
    setAsking(true);
    setCopilotA("");
    try {
      const r = await askCopilot(copilotQ, "plant-demo-01", lang);
      setCopilotA(r.answer);
      toast.success("Copilot answered");
    } catch {
      toast.error("Copilot offline");
    } finally { setAsking(false); }
  };

  return (
    <RoleGuard allowedRoles={["MAINTENANCE","MAINTENANCE_TECH","MAINTENANCE_LEAD","MAINTENANCE_MANAGER","ORG_ADMIN","OWNER"]}>
    <div className="px-4 sm:px-6 py-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2"><LayoutGrid className="h-5 w-5 text-sky-600" /> {t("maintenance", lang)} <Badge variant="sky">One schema, mixed fleet</Badge></h1>
        <div className="flex items-center gap-2">
          <Badge variant={sse.connected ? "emerald" : "amber"} className="gap-1"><Radio className="h-3 w-3" /> {sse.connected ? "NATS → SSE LIVE" : "Polling /poll"}</Badge>
          <Badge variant="outline">{filtered.length} stations</Badge>
        </div>
      </div>

      {/* filters */}
      <Card>
        <CardContent className="pt-4 flex flex-wrap gap-3 items-center">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input placeholder="Filter station, defect, protocol… (MTConnect, OPC-UA…)" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9" aria-label="Filter fleet" />
          </div>
          <div className="flex items-center gap-1 flex-wrap">
            <Filter className="h-4 w-4 text-slate-400" />
            {["all", "opcua", "modbus", "camera", "mqtt", "mtconnect", "ethernet_ip"].map((p) => (
              <button key={p} onClick={() => setProtocolFilter(p)} aria-pressed={protocolFilter === p} className={cn("px-2.5 py-1.5 rounded-full text-xs font-medium border transition", protocolFilter === p ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900" : "bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 dark:border-slate-700")}>
                {p}
              </button>
            ))}
          </div>
          {sse.error && <span className="text-xs text-amber-600">{sse.error}</span>}
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* fleet grid */}
        <div className="lg:col-span-2">
          {loading ? (
            <div className="grid sm:grid-cols-2 gap-3">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}</div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-3">
              {filtered.map((e, i) => {
                const acked = ackedIds.has(e.station_id);
                const isAlert = e.defect_class !== "none";
                return (
                  <motion.div key={`${e.station_id}-${i}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }} whileHover={{ y: -2 }}>
                    <Card className={cn("cursor-pointer hover:shadow-md transition", isAlert && !acked ? "border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20" : "", acked ? "opacity-60" : "")} onClick={() => setSelected(e)}>
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <div className="font-mono text-xs font-semibold truncate">{e.station_id}</div>
                            <div className="flex items-center gap-1 mt-1 flex-wrap">
                              <Badge variant="outline" className={cn("text-[10px] px-1.5 py-0", protocolColor(e.protocol))}>{e.protocol}</Badge>
                              <Badge variant={isAlert ? "amber" : "secondary"} className="text-[10px]">{isAlert ? e.defect_class : "OK"}</Badge>
                              <span className="text-[11px] text-slate-500">{Math.round(e.confidence * 100)}% · {Math.round(e.latency_ms)}ms</span>
                            </div>
                            <div className="text-[11px] text-slate-500 mt-1">{e.track} · {e.adapter_id || "—"} · {new Date(e.timestamp * 1000).toLocaleTimeString()}</div>
                          </div>
                          <div className="flex flex-col gap-1 items-center">
                            {isAlert ? <AlertTriangle className="h-4 w-4 text-amber-600" /> : <Activity className="h-4 w-4 text-emerald-600" />}
                            {isAlert && !acked && <Button size="sm" variant="primary" className="h-7 text-xs px-2" onClick={(ev) => { ev.stopPropagation(); handleAck(e); }}><Check className="h-3 w-3 mr-1" /> Ack</Button>}
                            {acked && <Badge variant="emerald" className="text-[10px]">ACKED</Badge>}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          )}
          {!loading && filtered.length === 0 && <div className="text-sm text-slate-500 text-center py-12 border border-dashed rounded-2xl mt-3">No stations match “{query}” · try clearing filters — empty state, not error.</div>}
        </div>

        {/* right rail — charts + copilot */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Vibration FFT — edge &lt;40ms</CardTitle>
              <CardDescription className="text-xs">Pi5+Hailo-8L / Orin · dust/glare compensated · Recharts</CardDescription>
            </CardHeader>
            <CardContent>
              <FFTChart />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Walk-reads trend (pilot)</CardTitle>
              <CardDescription className="text-xs">Before/after TANTU · derived events only · /metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <WalkTrendChart />
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2"><Sparkles className="h-3 w-3 text-sky-600" /> Ask copilot · grounded RAG</CardTitle>
              <CardDescription className="text-xs">POST /ask · Qdrant · tag maps + runbooks · cites sources</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-2">
                <Input value={copilotQ} onChange={(e) => setCopilotQ(e.target.value)} placeholder="why did line 2 slow down?" className="text-sm" aria-label="Copilot question" />
                <Button onClick={handleAsk} variant="primary" disabled={asking}>{asking ? "…" : t("ask_copilot", lang)}</Button>
              </div>
              {asking && <div className="rounded-xl border dark:border-slate-700 p-3"><Skeleton className="h-4 w-full" /></div>}
              {copilotA && !asking && (
                <div className="bg-sky-50 dark:bg-sky-950 border border-sky-200 dark:border-sky-800 rounded-xl p-3 text-sm">
                  <div className="flex justify-between items-start gap-2">
                    <span>{copilotA}</span>
                    <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(copilotA); toast.success("Copied"); }}><Copy className="h-3 w-3" /></Button>
                  </div>
                </div>
              )}
              <div className="text-[11px] text-slate-500">Air-gapped → Nemotron-9B on-prem · cloud → Gemini ER2 · never sends frames</div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* detail drawer */}
      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        {selected && (
          <DialogContent onClose={() => setSelected(null)}>
            <DialogHeader>
              <DialogTitle className="font-mono text-sm flex items-center gap-2">{selected.station_id} <Badge variant="outline" className={protocolColor(selected.protocol)}>{selected.protocol}</Badge></DialogTitle>
              <DialogDescription>{selected.protocol} · {selected.defect_class} · {Math.round(selected.confidence * 100)}% · {Math.round(selected.latency_ms)}ms · MTConnect adapter fabric</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Track</div><div className="font-medium">{selected.track}</div></div>
                <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Adapter</div><div className="font-medium">{selected.adapter_id || "—"}</div></div>
                <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Latency</div><div className="font-medium">{selected.latency_ms}ms (edge p95 &lt;40ms)</div></div>
                <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Quality</div><div className="font-medium">{selected.confidence >= 0.9 ? "good" : selected.confidence >= 0.7 ? "uncertain" : "bad"}</div></div>
              </div>
              <div className="rounded-xl border dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-800">
                <div className="font-semibold text-xs flex items-center gap-1"><Sparkles className="h-3 w-3" /> Normalized reading (one schema)</div>
                <pre className="text-[11px] mt-1 overflow-auto max-h-48">{JSON.stringify(selected, null, 2)}</pre>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => { handleAck(selected); toast.success("Acked"); }} variant="primary" className="flex-1"><Check className="h-4 w-4 mr-1" /> {t("ack", lang)}</Button>
                <Button variant="outline" onClick={() => setSelected(null)}>Close</Button>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
    </RoleGuard>
  );
}
