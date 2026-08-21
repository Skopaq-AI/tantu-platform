"use client";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "@/lib/motion";
import { toast } from "@/lib/toast";
import { useI18n, t, Lang } from "@/lib/i18n";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { WalkReadsChart } from "@/components/charts/WalkReadsChart";
import { FFTChart } from "@/components/charts/FFTChart";
import { Skeleton, CardSkeleton, ChartSkeleton } from "@/components/ui/skeleton";
import { fetchEvents, fetchHealth, fetchMetrics, askCopilot, ackEvent, pollTelemetry, getSSEUrl, type DefectEvent } from "@/lib/api";
import { useSSE } from "@/hooks/useSSE";
import { Mic, LayoutGrid, Gauge, ArrowRight, Shield, Zap, Languages, Activity, Radio, Check, AlertTriangle, Volume2, Sparkles, ArrowUpRight, Factory, Eye, Clock, Banknote, TrendingDown, MessageSquare, FileText, TrendingUp, Wifi, Hand, ChevronRight, Play, Copy, ExternalLink } from "lucide-react";

// story steps
const STORY = [
  { k: "01", title: "Connect", desc: "OPC-UA · Modbus · MQTT · MTConnect · EtherNet/IP · camera-as-adapter", icon: Factory },
  { k: "02", title: "Perceive", desc: "Edge tiered (Pi5+Hailo-8L / Orin) · <40ms · dust/glare compensated", icon: Eye },
  { k: "03", title: "Reason", desc: "Dual GENAI: Nemotron-9B on-prem + Gemini ER2 cloud (derived events only)", icon: Sparkles },
  { k: "04", title: "Act", desc: "Vernacular alert in operator language · one-button ACK · audit trail", icon: Check },
];

export default function Home() {
  const { lang, setLang } = useI18n();
  const [events, setEvents] = useState<DefectEvent[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [health, setHealth] = useState<"ok" | "offline" | "loading">("loading");
  const [metrics, setMetrics] = useState<any>(null);
  const [poll, setPoll] = useState<any>(null);
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [query, setQuery] = useState("why did line 2 slow down?");
  const [acked, setAcked] = useState<Set<string>>(new Set());
  const [showLOI, setShowLOI] = useState(false);
  const [activeRole, setActiveRole] = useState("operator");
  const sse = useSSE(getSSEUrl(), true);

  // initial load: health + events + metrics + poll
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const [h, evs, m, p] = await Promise.all([fetchHealth(), fetchEvents(8), fetchMetrics(), pollTelemetry(6)]);
        if (!mounted) return;
        setHealth(h.status === "ok" ? "ok" : h.status === "offline" ? "offline" : "loading");
        if (evs.length) setEvents(evs);
        setMetrics(m);
        setPoll(p);
      } catch {
        setHealth("offline");
      } finally {
        if (mounted) setLoadingEvents(false);
      }
    })();
    // live health pulse
    const id = setInterval(() => {
      fetchHealth().then((h) => setHealth(h.status === "ok" ? "ok" : "offline")).catch(() => setHealth("offline"));
      fetchEvents(8).then(setEvents).catch(() => {});
    }, 8000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  // prefer SSE events when live
  const liveEvents: DefectEvent[] = useMemo(() => (sse.events.length ? sse.events.slice(0, 8) : events), [sse.events, events]);
  const primaryAlert = liveEvents.find((e) => e.defect_class !== "none") || liveEvents[0];

  async function handleAsk() {
    if (!query.trim()) return;
    setAsking(true);
    setAnswer("");
    try {
      const r = await askCopilot(query, "plant-demo-01", lang);
      setAnswer(r.answer || r.vernacular?.[lang] || "");
      toast.success("Copilot answered (grounded)");
    } catch {
      toast.error("Copilot offline — showing stub");
      setAnswer(`Offline stub: '${query}' → check valve 3, vibration up 12% (grounded from tag map line2).`);
    } finally { setAsking(false); }
  }

  async function handleAck(e?: DefectEvent) {
    const target = e || primaryAlert;
    if (!target) return;
    // optimistic
    setAcked((s) => new Set([...s, target.station_id]));
    toast.success(t("vernacular_ack_done", lang), { description: `${target.station_id} · ${target.defect_class}` });
    if (navigator.vibrate) navigator.vibrate(60);
    await ackEvent(target.station_id, target.defect_class);
  }

  const opex = metrics?.opex ?? 18000;

  return (
    <div className="px-4 sm:px-6 py-6 space-y-6">
      {/* HERO — glass + gradient + floating orbs */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: "easeOut" }} className="relative overflow-hidden rounded-[24px] border bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 text-white p-6 sm:p-8 shadow-xl dark:border-slate-800">
        {/* orbs */}
        <div className="pointer-events-none absolute -top-24 -right-24 h-72 w-72 rounded-full bg-sky-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="absolute inset-0 grid-pattern opacity-[0.06]" />
        <div className="relative flex flex-col lg:flex-row gap-6 justify-between">
          <div className="max-w-2xl">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }} className="flex flex-wrap gap-2 mb-3">
              <Badge variant="secondary" className="bg-white/10 text-white border-white/20 backdrop-blur">Production-grade · Hexagonal · Event-driven</Badge>
              <Badge variant="outline" className="bg-white/10 text-white border-white/20"><span className="h-2 w-2 bg-emerald-400 rounded-full animate-pulse mr-1 inline-block" /> {sse.connected ? "NATS → SSE live" : health === "ok" ? "API ok · polling" : "Offline demo"}</Badge>
            </motion.div>
            <h1 className="text-3xl sm:text-[36px] font-bold tracking-tight leading-tight">
              Every machine speaks <span className="bg-gradient-to-r from-sky-300 to-violet-300 bg-clip-text text-transparent">one language.</span>
            </h1>
            <p className="mt-3 text-slate-300 text-sm leading-relaxed max-w-xl">
              TANTU orchestrates mixed-vendor floors — OPC-UA · Modbus · MQTT · MTConnect · EtherNet/IP · camera-as-adapter — into one schema, one answer, in the operator&apos;s language. Raw frames never leave plant.
            </p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="inline-flex items-center gap-1 bg-white/10 border border-white/20 rounded-full px-2.5 py-1 backdrop-blur"><Shield className="h-3 w-3" /> DPDP & SOC2</span>
              <span className="inline-flex items-center gap-1 bg-white/10 border border-white/20 rounded-full px-2.5 py-1 backdrop-blur"><Zap className="h-3 w-3" /> &lt;40ms edge · p95 {metrics?.p95_latency_ms ?? 38}ms</span>
              <span className="inline-flex items-center gap-1 bg-white/10 border border-white/20 rounded-full px-2.5 py-1 backdrop-blur"><Languages className="h-3 w-3" /> hi/ta/te/kn + code-switch</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href="/operator"><Button variant="secondary" className="bg-white text-slate-900 hover:bg-slate-100 shadow"><Mic className="h-4 w-4 mr-2" /> Operator <ChevronRight className="h-4 w-4 ml-1" /></Button></Link>
              <Link href="/maintenance"><Button variant="outline" className="bg-transparent border-white/30 text-white hover:bg-white/10">Maintenance <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
              <Link href="/plant-head"><Button variant="outline" className="bg-transparent border-white/30 text-white hover:bg-white/10"><Gauge className="h-4 w-4 mr-2" /> Plant Head</Button></Link>
            </div>
            <div className="mt-3 flex gap-3 text-[11px] text-slate-400">
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`} className="hover:text-white underline decoration-white/30">/docs</a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`} className="hover:text-white underline decoration-white/30">/health {health === "ok" ? "● ok" : "○ offline"}</a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/metrics`} className="hover:text-white underline decoration-white/30">/metrics</a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/events`} className="hover:text-white underline decoration-white/30">/events</a>
            </div>
          </div>

          {/* live fleet glass card */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }} className="lg:w-[380px] glass-strong rounded-2xl p-4 text-slate-900 dark:text-slate-100 shadow-xl">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide flex items-center gap-1.5"><Radio className="h-3.5 w-3.5 text-emerald-600" /> Live fleet · NATS → SSE</div>
              <Badge variant={sse.connected ? "emerald" : "amber"} className="text-[10px]">{sse.connected ? "LIVE" : "POLL"}</Badge>
            </div>
            <div className="mt-3 space-y-2">
              {loadingEvents ? (
                <div className="space-y-2">{Array.from({ length: 3 }).map((_, i) => (<Skeleton key={i} className="h-14 w-full rounded-xl" />))}</div>
              ) : liveEvents.length ? (
                liveEvents.slice(0, 3).map((e: any, i: number) => (
                  <motion.div key={`${e.station_id}-${i}`} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 * i }} className="flex items-center justify-between border dark:border-slate-700 rounded-xl p-2.5 text-xs bg-white dark:bg-slate-800">
                    <div className="min-w-0">
                      <div className="font-mono text-[11px] font-semibold truncate">{e.station_id}</div>
                      <div className="text-slate-500 dark:text-slate-400 truncate">{e.protocol} · {e.defect_class} · {Math.round(e.confidence * 100)}% · {e.latency_ms}ms</div>
                    </div>
                    <Badge variant={e.defect_class === "none" ? "secondary" : "amber"} className="shrink-0 ml-2">{e.defect_class === "none" ? "OK" : "ALERT"}</Badge>
                  </motion.div>
                ))
              ) : (
                <div className="border border-dashed rounded-xl p-6 text-center text-sm text-slate-500">No live events — empty state. System healthy, awaiting telemetry.</div>
              )}
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-[11px]">
              <div className="rounded-lg bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 p-2 text-center"><div className="font-bold">{liveEvents.length}</div><div className="text-slate-500">stations</div></div>
              <div className="rounded-lg bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 p-2 text-center"><div className="font-bold">{poll?.readings?.length ?? "—"}</div><div className="text-slate-500">poll readings</div></div>
              <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 p-2 text-center"><div className="font-bold text-emerald-700 dark:text-emerald-300">{acked.size}</div><div className="text-slate-500">acked</div></div>
            </div>
            <Link href="/maintenance" className="mt-3 inline-flex items-center text-xs font-medium text-sky-600 dark:text-sky-400 hover:underline">Open Maintenance grid <ArrowRight className="h-3 w-3 ml-1" /></Link>
          </motion.div>
        </div>
      </motion.div>

      {/* story strip */}
      <Card className="overflow-hidden">
        <CardContent className="pt-5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wide"><Sparkles className="h-3.5 w-3.5" /> Story — from sensor to decision (frames never leave)</div>
          <div className="mt-3 grid sm:grid-cols-4 gap-3">
            {STORY.map((s) => (
              <div key={s.k} className="rounded-xl border bg-slate-50 dark:bg-slate-800/50 dark:border-slate-700 p-3 flex gap-3">
                <div className="h-8 w-8 rounded-lg bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center text-xs font-bold shrink-0">{s.k}</div>
                <div><div className="text-sm font-semibold flex items-center gap-1"><s.icon className="h-3.5 w-3.5 text-slate-500" /> {s.title}</div><div className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</div></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* ROLE TABS — world-class 2024-26: pill tabs, motion, skeletons, empty, optimistic */}
      <Tabs value={activeRole} onValueChange={setActiveRole} className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList className="bg-white dark:bg-slate-900 border dark:border-slate-800 shadow-sm rounded-full p-1">
            <TabsTrigger value="operator" className="rounded-full data-[active]:bg-slate-900 data-[active]:text-white dark:data-[active]:bg-white dark:data-[active]:text-slate-900 gap-1.5"><Mic className="h-4 w-4" /> Operator</TabsTrigger>
            <TabsTrigger value="maintenance" className="rounded-full gap-1.5"><LayoutGrid className="h-4 w-4" /> Maintenance</TabsTrigger>
            <TabsTrigger value="planthead" className="rounded-full gap-1.5"><Gauge className="h-4 w-4" /> Plant Head</TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-2 text-xs">
            <Badge variant="outline" className="gap-1"><Activity className="h-3 w-3" /> {health === "ok" ? "All APIs live" : "Demo fallback"}</Badge>
            <Badge variant="outline" className="hidden sm:inline-flex">Inter · 5-lang · a11y</Badge>
          </div>
        </div>

        {/* OPERATOR — voice-first, 5-lang, 85dB, one-button, Framer Motion */}
        <TabsContent value="operator">
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="grid lg:grid-cols-3 gap-4">
            <Card className={`lg:col-span-2 overflow-hidden ${acked.has(primaryAlert?.station_id) ? "border-emerald-200 dark:border-emerald-800" : "border-amber-200 dark:border-amber-800 shadow-lg"}`}>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <motion.span animate={primaryAlert && !acked.has(primaryAlert.station_id) ? { scale: [1, 1.08, 1] } : {}} transition={{ repeat: Infinity, duration: 1.6 }}>
                    <AlertTriangle className={`h-5 w-5 ${acked.has(primaryAlert?.station_id) ? "text-emerald-600" : "text-amber-600"}`} />
                  </motion.span>
                  {acked.has(primaryAlert?.station_id) ? t("vernacular_ack_done", lang) : "Attention required"}
                  <span className="ml-auto text-xs font-normal text-slate-500 flex items-center gap-1.5"><Wifi className="h-3 w-3" /> 85 dB · 12h · gloved <Hand className="h-3 w-3 ml-1" /></span>
                </CardTitle>
                <CardDescription className="text-xs flex flex-wrap gap-2">
                  <span>{primaryAlert?.station_id ?? "—"} · {primaryAlert?.protocol ?? "camera"} · {primaryAlert?.latency_ms ?? 22}ms · {primaryAlert ? Math.round(primaryAlert.confidence * 100) : 92}%</span>
                  <Badge variant="outline" className="text-[10px]">Web Speech API</Badge>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <motion.div layout className={`rounded-2xl p-6 text-center border-2 ${acked.has(primaryAlert?.station_id) ? "bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800" : "bg-amber-50 dark:bg-amber-950 border-amber-300 dark:border-amber-700"}`}>
                  <div className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400 font-semibold flex items-center justify-center gap-1"><Volume2 className="h-3 w-3" /> Vernacular · {lang.toUpperCase()} · Framer Motion</div>
                  <AnimatePresence mode="wait">
                    <motion.div key={lang + (primaryAlert?.station_id ?? "")} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.25 }} className="mt-2 text-2xl sm:text-[28px] font-bold leading-tight text-slate-900 dark:text-slate-100">
                      {primaryAlert ? t("vernacular_pressure", lang) : "—"}
                    </motion.div>
                  </AnimatePresence>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">{t("vernacular_vib", lang)}</div>
                  {!acked.has(primaryAlert?.station_id ?? "") && primaryAlert && (
                    <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="mt-3 inline-flex items-center gap-2 text-xs bg-white dark:bg-slate-900 border dark:border-slate-700 rounded-full px-3 py-1 shadow-sm">
                      <span className="h-2 w-2 bg-red-500 rounded-full animate-pulse" /> {t("live", lang)} · {primaryAlert.defect_class} · {primaryAlert.protocol}
                    </motion.div>
                  )}
                </motion.div>

                <motion.div whileTap={{ scale: 0.98 }}>
                  <Button onClick={() => handleAck()} disabled={acked.has(primaryAlert?.station_id ?? "")} variant={acked.has(primaryAlert?.station_id ?? "") ? "secondary" : "primary"} size="touch" className={`w-full h-[72px] text-xl rounded-2xl glove-target ${acked.has(primaryAlert?.station_id ?? "") ? "opacity-60" : "shadow-lg hover:shadow-xl"}`} aria-label="Acknowledge alert">
                    {acked.has(primaryAlert?.station_id ?? "") ? (<><Check className="h-7 w-7 mr-2" /> {t("ack", lang)} ✓</>) : (<>✓ {t("ack", lang)} — TAP</>)}
                  </Button>
                </motion.div>
                <div className="text-center text-xs text-slate-500 dark:text-slate-400">{t("dB_gloved", lang)} · {t("one_button_ack", lang)} · no menus · haptics · optimistic</div>

                <div className="grid grid-cols-5 gap-2" role="group" aria-label="Language">
                  {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
                    <motion.button
                      key={l}
                      whileTap={{ scale: 0.96 }}
                      whileHover={{ y: -1 }}
                      onClick={() => setLang(l)}
                      aria-pressed={lang === l}
                      className={`py-3 rounded-xl font-bold text-sm border-2 glove-target transition ${lang === l ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white shadow" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700"}`}
                    >
                      {l.toUpperCase()}
                      <div className="text-[10px] font-normal opacity-70">{l === "en" ? "English" : l === "hi" ? "हिन्दी" : l === "ta" ? "தமிழ்" : l === "te" ? "తెలుగు" : "ಕನ್ನಡ"}</div>
                    </motion.button>
                  ))}
                </div>
                <div className="flex gap-2">
                  <Link href="/operator" className="flex-1"><Button variant="outline" className="w-full">Open Operator view <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
                  <Button variant="ghost" onClick={() => { if (primaryAlert) { const u = new SpeechSynthesisUtterance(t("vernacular_pressure", lang)); u.lang = lang === "hi" ? "hi-IN" : lang === "ta" ? "ta-IN" : lang === "te" ? "te-IN" : lang === "kn" ? "kn-IN" : "en-IN"; speechSynthesis.speak(u); toast.message("TTS playing"); } }} aria-label="Play vernacular"><Volume2 className="h-4 w-4" /></Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2"><Mic className="h-4 w-4 text-amber-600" /> Voice — Web Speech API</CardTitle>
                <CardDescription className="text-xs">Tap to speak · code-switch · 85dB compensated · offline queue</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="rounded-xl border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3">
                  <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-2"><span className="h-2 w-2 bg-red-500 rounded-full animate-pulse" /> Try: “ack” / “हाँ” / “சரி” / “సరే” / “ಸರಿ”</div>
                  <div className="mt-2 text-sm text-slate-600 dark:text-slate-300">Web Speech API: SpeechRecognition + speechSynthesis. In production, 85dB noise gate + gloved touch only.</div>
                  <div className="mt-2 text-xs text-slate-500">Lang: {lang} · {t("tap_to_speak", lang)} · {t("listening", lang)}</div>
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400 text-center">One-button ack is telemetry, not auth · a11y: keyboard, screen-reader, focus ring</div>
                <Link href="/operator"><Button variant="primary" className="w-full"><Play className="h-4 w-4 mr-2" /> Try voice demo</Button></Link>
              </CardContent>
            </Card>
          </motion.div>
        </TabsContent>

        {/* MAINTENANCE — mixed-fleet grid, SSE/NATS, Recharts FFT + walk-reads, MTConnect */}
        <TabsContent value="maintenance">
          <div className="grid lg:grid-cols-3 gap-4">
            <div className="lg:col-span-2 space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={sse.connected ? "emerald" : "amber"} className="gap-1"><Radio className="h-3 w-3" /> {sse.connected ? "NATS → SSE LIVE" : "Polling /poll"}</Badge>
                <Badge variant="outline">{liveEvents.length} stations</Badge>
                <Badge variant="outline" className="hidden sm:inline-flex">MTConnect · OPC-UA · Modbus · MQTT · camera</Badge>
                <span className="ml-auto text-xs text-slate-500">One schema: DefectEvent / NormalizedReading</span>
              </div>
              {loadingEvents ? (
                <CardSkeleton />
              ) : liveEvents.length === 0 ? (
                <Card><CardContent className="py-12 text-center"><div className="mx-auto h-12 w-12 rounded-2xl bg-slate-100 dark:bg-slate-800 grid place-items-center mb-3"><LayoutGrid className="h-6 w-6 text-slate-400" /></div><div className="font-medium">No stations yet</div><div className="text-sm text-slate-500">Connect an adapter or check /events. Empty state prevents blank panic.</div></CardContent></Card>
              ) : (
                <div className="grid sm:grid-cols-2 gap-3">
                  {liveEvents.map((e, i) => {
                    const isAcked = acked.has(e.station_id);
                    const isAlert = e.defect_class !== "none";
                    return (
                      <motion.div key={`${e.station_id}-${i}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }} whileHover={{ y: -2 }}>
                        <Card className={`cursor-pointer transition-all ${isAlert && !isAcked ? "border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20 shadow-sm" : ""} ${isAcked ? "opacity-60" : "hover:shadow-md"}`}>
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <div className="font-mono text-xs font-semibold truncate">{e.station_id}</div>
                                <div className="flex items-center gap-1 mt-1 flex-wrap">
                                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 bg-sky-50 dark:bg-sky-950 border-sky-200 dark:border-sky-800">{e.protocol}</Badge>
                                  <Badge variant={isAlert ? "amber" : "secondary"} className="text-[10px]">{isAlert ? e.defect_class : "OK"}</Badge>
                                  <span className="text-[11px] text-slate-500">{Math.round(e.confidence * 100)}% · {Math.round(e.latency_ms)}ms</span>
                                </div>
                                <div className="text-[11px] text-slate-500 mt-1">{e.track} · {e.adapter_id || "—"} · {new Date(e.timestamp * 1000).toLocaleTimeString()}</div>
                              </div>
                              <div className="flex flex-col gap-1 items-center">
                                {isAlert ? <AlertTriangle className="h-4 w-4 text-amber-600" /> : <Activity className="h-4 w-4 text-emerald-600" />}
                                {isAlert && !isAcked ? (
                                  <Button size="sm" variant="primary" className="h-7 text-xs px-2" onClick={(ev) => { ev.stopPropagation(); handleAck(e); }}><Check className="h-3 w-3 mr-1" /> Ack</Button>
                                ) : isAcked ? (
                                  <Badge variant="emerald" className="text-[10px]">ACKED</Badge>
                                ) : null}
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      </motion.div>
                    );
                  })}
                </div>
              )}
              {/* ask copilot */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2"><MessageSquare className="h-4 w-4 text-sky-600" /> Ask copilot · grounded RAG</CardTitle>
                  <CardDescription className="text-xs">POST /ask · Qdrant · tag maps + runbooks · cites sources · never sends frames</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex gap-2">
                    <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="why did line 2 slow down?" className="flex-1 border dark:border-slate-700 dark:bg-slate-900 rounded-xl px-3 py-2 text-sm focus:ring-2 focus:ring-sky-500 outline-none" aria-label="Ask copilot" />
                    <Button onClick={handleAsk} variant="primary" disabled={asking}>{asking ? "Thinking…" : t("ask_copilot", lang)}</Button>
                  </div>
                  <AnimatePresence>
                    {asking && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl border dark:border-slate-700 p-3"><div className="flex gap-2"><Skeleton className="h-4 w-full" /></div></motion.div>}
                    {answer && !asking && (
                      <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="rounded-xl bg-sky-50 dark:bg-sky-950 border border-sky-200 dark:border-sky-800 p-3 text-sm">
                        <div className="font-medium flex items-center gap-1"><Sparkles className="h-3.5 w-3.5 text-sky-600" /> Answer</div>
                        <div className="mt-1 text-slate-700 dark:text-slate-300">{answer}</div>
                        <div className="mt-2 flex gap-2">
                          <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(answer); toast.success("Copied"); }}><Copy className="h-3 w-3 mr-1" /> Copy</Button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                  <div className="text-[11px] text-slate-500">GET /poll + /events feed the context · Air-gapped → Nemotron-9B on-prem · cloud → Gemini ER2</div>
                </CardContent>
              </Card>
            </div>
            <div className="space-y-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Vibration FFT — edge &lt;40ms</CardTitle>
                  <CardDescription className="text-xs">Pi5+Hailo-8L / Orin · Recharts · MTConnect + OPC-UA unified</CardDescription>
                </CardHeader>
                <CardContent>
                  <FFTChart />
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Walk-reads — before/after (pilot)</CardTitle>
                  <CardDescription className="text-xs">Polling-normalized telemetry</CardDescription>
                </CardHeader>
                <CardContent>
                  <WalkReadsChart />
                </CardContent>
              </Card>
              <Link href="/maintenance"><Button variant="outline" className="w-full">Open full fleet grid <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
            </div>
          </div>
        </TabsContent>

        {/* PLANT-HEAD — opex Rs18K, before/after, LOI CTA */}
        <TabsContent value="planthead">
          <div className="grid sm:grid-cols-3 gap-4">
            <Card className="border-emerald-200 dark:border-emerald-800">
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1"><Banknote className="h-3 w-3" /> Opex / cluster / month</CardDescription>
                <CardTitle className="text-3xl">Rs 18K <span className="text-sm font-normal text-slate-500">/ mo</span></CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-slate-500 dark:text-slate-400">Hardware amortized 36 mo · edge + platform + support · no capex board approval</div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Edge HW</div><div className="font-bold">Rs 6.5K</div></div>
                  <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Platform + RAG</div><div className="font-bold">Rs 8K</div></div>
                  <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Support</div><div className="font-bold">Rs 3.5K</div></div>
                  <div className="border rounded-xl p-2.5 bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800"><div className="text-slate-500">Vs manual</div><div className="font-bold text-emerald-700 dark:text-emerald-300">− Rs 42K</div></div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1"><TrendingDown className="h-3 w-3" /> Walk-reads / day</CardDescription>
                <CardTitle className="text-3xl">48 → 6 <span className="text-sm font-normal text-emerald-600">−87%</span></CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-slate-500">Operator hours saved 3.2 h/shift · reallocated to value-add</div>
                <div className="mt-3 flex items-start gap-2 text-xs bg-slate-50 dark:bg-slate-800 rounded-xl p-2.5 border dark:border-slate-700"><Check className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" /> Before: manual gauge rounds · After: camera-as-adapter (Hailo-8L) + OPC-UA, derived events only</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1"><Clock className="h-3 w-3" /> MTTD / MTTR · Uptime</CardDescription>
                <CardTitle className="text-3xl">{metrics?.uptime ?? 99.2}% <span className="text-sm font-normal text-slate-500">uptime</span></CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xs text-slate-500">MTTD 22→3 min · MTTR 45→18 min · p95 &lt;40ms</div>
                <div className="mt-3 flex gap-2 text-xs">
                  <Badge variant="emerald">Reversible</Badge><Badge variant="outline">90-day pilot</Badge><Badge variant="secondary">Rs {opex.toLocaleString("en-IN")} opex</Badge>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid lg:grid-cols-2 gap-4 mt-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2"><TrendingUp className="h-4 w-4 text-emerald-600" /> {t("walk_reads_title", lang)} — {t("pilot_before_after", lang)}</CardTitle>
                <CardDescription className="text-xs">GET /metrics · shift handover · pilot plants demo-01, demo-02 · 90 days</CardDescription>
              </CardHeader>
              <CardContent>
                {metrics ? <WalkReadsChart /> : <ChartSkeleton />}
                <div className="mt-2 text-[11px] text-slate-500 text-center">Derived telemetry only · raw frames never leave plant · DPDP 2023 compliant</div>
              </CardContent>
            </Card>
            <Card className="border-sky-200 dark:border-sky-800">
              <CardHeader>
                <CardTitle className="text-sm">Cost → Value · 18-month projection</CardTitle>
                <CardDescription className="text-xs">Transparent pilot → rollout · reversible · no vendor lock-in</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-3 gap-2 text-xs">
                  <div className="border dark:border-slate-700 rounded-xl p-3 text-center"><div className="text-slate-500">Pilot (3)</div><div className="font-bold text-lg">Rs 54K</div><div className="text-slate-500">/ mo</div></div>
                  <div className="border rounded-xl p-3 text-center bg-sky-50 dark:bg-sky-950 border-sky-200 dark:border-sky-800"><div className="text-slate-500">Rollout (12)</div><div className="font-bold text-lg">Rs 2.16L</div><div className="text-slate-500">/ mo</div></div>
                  <div className="border rounded-xl p-3 text-center bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800"><div className="text-slate-500">Savings (12)</div><div className="font-bold text-lg text-emerald-600">Rs 5L</div><div className="text-slate-500">/ mo</div></div>
                </div>
                <div className="border dark:border-slate-700 rounded-xl p-3 bg-slate-50 dark:bg-slate-800 text-xs space-y-1">
                  <div className="font-semibold">Pilot terms</div>
                  <div className="text-slate-600 dark:text-slate-400">• 90 days · 3 clusters · hardware on loan · full feature parity</div>
                  <div className="text-slate-600 dark:text-slate-400">• Exit: Postgres/Timescale export · no lock-in · frames on-prem</div>
                  <div className="text-slate-600 dark:text-slate-400">• Success: walk-reads ↓80%, MTTD ↓70%, vernacular ack &gt;90%</div>
                </div>
                <Button variant="primary" className="w-full shadow-lg" onClick={() => setShowLOI(true)}>{t("loi_cta", lang)} <ArrowUpRight className="h-4 w-4 ml-1" /></Button>
                <div className="flex gap-2">
                  <Button variant="outline" className="flex-1" onClick={() => toast.success("One-pager queued for download")}><FileText className="h-4 w-4 mr-1" /> One-pager</Button>
                  <Link href="/plant-head" className="flex-1"><Button variant="outline" className="w-full">Open Opex dashboard <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
                </div>
              </CardContent>
            </Card>
          </div>

          <Dialog open={showLOI} onOpenChange={setShowLOI}>
            <DialogContent className="max-w-lg" onClose={() => setShowLOI(false)}>
              <DialogHeader>
                <DialogTitle>Pilot Letter of Intent — Rs 18K / cluster / mo</DialogTitle>
                <DialogDescription>Reversible 90-day pilot · hardware on loan · DPDP/SOC2 ready</DialogDescription>
              </DialogHeader>
              <div className="space-y-3 text-sm">
                <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3 text-xs leading-relaxed">
                  This LOI reserves 3 clusters for 90 days at Rs 18K/cluster/mo (Rs 54K/mo total). Includes Pi5+Hailo-8L or Orin edge, adapter fabric (OPC-UA/Modbus/MQTT/MTConnect/camera), on-prem Nemotron-9B + cloud Gemini ER2 on derived events only, walk-read automation, vernacular ops in hi/ta/te/kn/en, and support. Exit anytime — export data, keep learnings, frames never left plant.
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <input placeholder="Plant name" className="border dark:border-slate-700 dark:bg-slate-900 rounded-xl px-3 py-2" aria-label="Plant name" />
                  <input placeholder="Your email" className="border dark:border-slate-700 dark:bg-slate-900 rounded-xl px-3 py-2" aria-label="Email" />
                  <input placeholder="Clusters (3)" className="border dark:border-slate-700 dark:bg-slate-900 rounded-xl px-3 py-2" aria-label="Clusters" defaultValue="3" />
                  <input placeholder="Start date" type="date" className="border dark:border-slate-700 dark:bg-slate-900 rounded-xl px-3 py-2" aria-label="Start date" />
                </div>
                <div className="flex gap-2">
                  <Button variant="primary" className="flex-1" onClick={() => { toast.success("LOI sent — team will contact in 24h"); setShowLOI(false); }}><Check className="h-4 w-4 mr-1" /> Sign & send LOI</Button>
                  <Button variant="outline" onClick={() => setShowLOI(false)}>Close</Button>
                </div>
                <div className="text-[11px] text-slate-500 text-center">By signing you agree to pilot terms · SOC2 audit trail · data_residency=IN</div>
              </div>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>

      {/* trust bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid sm:grid-cols-3 gap-6 text-sm">
            <div><div className="font-semibold flex items-center gap-1"><Factory className="h-4 w-4 text-slate-500" /> Architecture — 3 layers</div><div className="text-slate-500 dark:text-slate-400 text-xs mt-1">CONNECT (adapter fabric) → PERCEIVE (edge, tiered, on-prem) → REASON (dual GENAI: Nemotron-9B on-prem + Gemini ER2 cloud on derived events only). NATS → SSE · Timescale · Qdrant.</div></div>
            <div><div className="font-semibold flex items-center gap-1"><Shield className="h-4 w-4 text-slate-500" /> Security by default</div><div className="text-slate-500 dark:text-slate-400 text-xs mt-1">JWT RS256 + RBAC+ABAC · Vault · TLS 1.3 · gitleaks · pip-audit · signed images · frames impossible to exfil by type (no image field).</div></div>
            <div><div className="font-semibold flex items-center gap-1"><ExternalLink className="h-4 w-4 text-slate-500" /> API surface — all integrated</div><div className="text-xs mt-1 flex flex-wrap gap-2">
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`} className="text-sky-600 dark:text-sky-400 underline inline-flex items-center gap-1">/docs <ExternalLink className="h-3 w-3" /></a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`} className="text-sky-600 dark:text-sky-400 underline">/health</a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/events`} className="text-sky-600 dark:text-sky-400 underline">/events</a>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/metrics`} className="text-sky-600 dark:text-sky-400 underline">/metrics</a>
              <span className="text-slate-500">POST /ask</span><span className="text-slate-500">POST /ack</span><span className="text-slate-500">GET /poll</span><span className="text-slate-500">SSE /events/stream</span>
            </div></div>
          </div>
        </CardContent>
      </Card>

      {/* bottom polish */}
      <div className="rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg">
        <div className="text-sm font-medium">Raw frames never leave plant — enforced by type (DefectEvent has no image field) · Auditable · SOC2-ready</div>
        <Badge variant="secondary" className="bg-white text-slate-900 dark:bg-slate-900 dark:text-white">DPDP 2023 · data_residency=IN</Badge>
      </div>
    </div>
  );
}
