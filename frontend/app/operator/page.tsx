"use client";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "@/lib/motion";
import { toast } from "@/lib/toast";
import { useI18n, t, Lang } from "@/lib/i18n";
import { useSpeech } from "@/hooks/useSpeech";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ackEvent } from "@/lib/api";
import { Mic, MicOff, Volume2, Check, AlertTriangle, Wifi, Hand, Sparkles, Activity } from "lucide-react";

type Alert = { station_id: string; defect_class: string; confidence: number; latency_ms: number; protocol: string; ts: number };

export default function OperatorPage() {
  const { lang, setLang } = useI18n();
  const speech = useSpeech(lang);
  const [alert, setAlert] = useState<Alert>({ station_id: "line2-cluster1-gauge3", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, protocol: "camera", ts: Date.now() });
  const [acked, setAcked] = useState(false);
  const [queue, setQueue] = useState<Alert[]>([]);
  const [dbLevel] = useState(85);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(t);
  }, []);

  // poll for live alerts (SSE fallback via poll)
  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/events?limit=1`, { cache: "no-store" });
        if (r.ok) {
          const arr = await r.json();
          if (arr[0] && arr[0].defect_class !== "none" && arr[0].station_id !== alert.station_id) {
            setQueue((q) => [alert, ...q].slice(0, 5));
            setAlert({ station_id: arr[0].station_id, defect_class: arr[0].defect_class, confidence: arr[0].confidence, latency_ms: arr[0].latency_ms, protocol: arr[0].protocol, ts: Date.now() });
            setAcked(false);
            toast.info(`New alert: ${arr[0].station_id}`);
          }
        }
      } catch {}
    }, 3000);
    return () => clearInterval(id);
  }, [alert.station_id]);

  const handleAck = async () => {
    // optimistic
    setAcked(true);
    toast.success(t("vernacular_ack_done", lang), { description: alert.station_id });
    if (navigator.vibrate) navigator.vibrate(80);
    await ackEvent(alert.station_id, alert.defect_class);
  };

  const handleSpeakAck = () => {
    const transcript = (speech.transcript + " " + speech.interim).toLowerCase();
    if (transcript.includes("ack") || transcript.includes("ok") || transcript.includes("हाँ") || transcript.includes("சரி") || transcript.includes("సరే") || transcript.includes("ಸರಿ")) {
      handleAck();
    }
  };

  useEffect(() => {
    if (speech.transcript) handleSpeakAck();
  }, [speech.transcript, speech.interim]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 py-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid lg:grid-cols-3 gap-4">
          <Skeleton className="h-[420px] lg:col-span-2 rounded-2xl" />
          <Skeleton className="h-[420px] rounded-2xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="px-4 sm:px-6 py-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2"><Mic className="h-5 w-5 text-amber-600" /> {t("operator", lang)} <Badge variant="amber">Voice-first</Badge></h1>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1"><Wifi className="h-3 w-3" /> Edge &lt;40ms</Badge>
          <Badge variant="outline" className="gap-1"><Hand className="h-3 w-3" /> Gloved</Badge>
          <Badge variant={acked ? "emerald" : "amber"}>{acked ? "ACKED" : "ALERT"}</Badge>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* main alert — large touch targets */}
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="lg:col-span-2">
          <Card className={`${acked ? "border-emerald-200 dark:border-emerald-800" : "border-amber-300 dark:border-amber-700 shadow-lg"}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg flex items-center gap-2">
                <motion.span animate={!acked ? { scale: [1, 1.1, 1] } : {}} transition={{ repeat: Infinity, duration: 1.5 }}>
                  <AlertTriangle className={`h-5 w-5 ${acked ? "text-emerald-600" : "text-amber-600"}`} />
                </motion.span>
                {acked ? t("vernacular_ack_done", lang) : "Attention required"}
                <span className="ml-auto text-xs font-normal text-slate-500 flex items-center gap-1">{dbLevel} dB · 12h shift <Activity className="h-3 w-3 ml-1" /></span>
              </CardTitle>
              <CardDescription className="text-xs flex flex-wrap gap-2">
                <span>{alert.station_id} · {alert.protocol} · {alert.latency_ms}ms · {Math.round(alert.confidence * 100)}%</span>
                <Badge variant="outline" className="text-[10px]">Web Speech API · 5-lang</Badge>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* vernacular large */}
              <motion.div layout className={`rounded-2xl p-6 text-center ${acked ? "bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800" : "bg-amber-50 dark:bg-amber-950 border-2 border-amber-300 dark:border-amber-700"}`}>
                <div className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold flex items-center justify-center gap-1"><Volume2 className="h-3 w-3" /> Vernacular · {lang.toUpperCase()} · Framer Motion</div>
                <AnimatePresence mode="wait">
                  <motion.div key={lang + alert.station_id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} className="mt-2 text-2xl sm:text-3xl font-bold leading-tight text-slate-900 dark:text-slate-100">
                    {t("vernacular_pressure", lang)}
                  </motion.div>
                </AnimatePresence>
                <div className="mt-1 text-xs text-slate-500">{t("vernacular_vib", lang)}</div>
                {!acked && <motion.div initial={{ scale: 0.9 }} animate={{ scale: 1 }} className="mt-3 inline-flex items-center gap-2 text-xs bg-white dark:bg-slate-900 border dark:border-slate-700 rounded-full px-3 py-1"><span className="h-2 w-2 bg-red-500 rounded-full animate-pulse" /> {t("live", lang)} · {alert.defect_class} <Sparkles className="h-3 w-3 text-amber-500" /></motion.div>}
              </motion.div>

              {/* one-button ack */}
              <motion.div whileTap={{ scale: 0.98 }}>
                <Button
                  onClick={handleAck}
                  disabled={acked}
                  variant={acked ? "secondary" : "primary"}
                  size="touch"
                  className={`w-full text-xl font-bold glove-target rounded-2xl h-[72px] ${acked ? "opacity-60" : "shadow-lg hover:shadow-xl"}`}
                  aria-label={`Acknowledge ${alert.station_id}`}
                >
                  {acked ? <><Check className="h-7 w-7 mr-2" /> {t("ack", lang)} ✓</> : <>✓ {t("ack", lang)} — TAP</>}
                </Button>
              </motion.div>
              <div className="text-center text-xs text-slate-500">{t("dB_gloved", lang)} · {t("one_button_ack", lang)} · no menus, no scroll · haptics · optimistic</div>

              {/* language quick switch — large */}
              <div className="grid grid-cols-5 gap-2" role="group" aria-label="Language selector">
                {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
                  <motion.button
                    key={l}
                    whileHover={{ y: -1 }}
                    whileTap={{ scale: 0.96 }}
                    onClick={() => { setLang(l); toast.success(`Language: ${l.toUpperCase()}`); }}
                    aria-pressed={lang === l}
                    className={`py-3 rounded-xl font-bold text-sm border-2 glove-target transition ${lang === l ? "bg-slate-900 text-white border-slate-900 dark:bg-white dark:text-slate-900 dark:border-white shadow" : "bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:bg-slate-50"}`}
                  >
                    {l.toUpperCase()}
                    <div className="text-[10px] font-normal opacity-70">{l === "en" ? "English" : l === "hi" ? "हिन्दी" : l === "ta" ? "தமிழ்" : l === "te" ? "తెలుగు" : "ಕನ್ನಡ"}</div>
                  </motion.button>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* voice panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2"><Volume2 className="h-4 w-4" /> Voice — Web Speech API</CardTitle>
            <CardDescription className="text-xs">Tap to speak · code-switch supported · offline fallback stored</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button onClick={speech.listening ? speech.stop : () => { speech.start(); toast.info("Listening…"); }} variant={speech.listening ? "destructive" : "primary"} className="flex-1 glove-target">
                {speech.listening ? <><MicOff className="h-4 w-4 mr-2" /> Stop</> : <><Mic className="h-4 w-4 mr-2" /> {t("tap_to_speak", lang)}</>}
              </Button>
              <Button onClick={() => { speech.speak(t("vernacular_pressure", lang), lang); toast.info("Speaking vernacular"); }} variant="outline" className="glove-target" title="Replay TTS" aria-label="Replay text to speech">
                <Volume2 className="h-4 w-4" />
              </Button>
            </div>
            <div className="rounded-xl border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-3 min-h-[88px]">
              <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">Transcript {speech.listening && <span className="text-red-600 animate-pulse">● {t("listening", lang)}</span>}</div>
              <div className="mt-1 text-sm dark:text-slate-200">{speech.transcript || <span className="text-slate-400 italic">Say “ack” / “ok” / “हाँ” / “சரி” to ack…</span>}</div>
              {speech.interim && <div className="text-sm text-slate-400 italic">{speech.interim}</div>}
              {speech.error && <div className="text-xs text-red-600 mt-1">{speech.error}</div>}
              {!speech.supported && <div className="text-xs text-amber-600">Web Speech not supported — use ACK button.</div>}
            </div>
            <div className="text-[11px] text-slate-500">Also accepts: “ack”, “ok”, “done”, “हाँ”, “சரி”, “సరే”, “ಸರಿ”. Offline acks queued in localStorage.</div>

            {queue.length > 0 && (
              <div>
                <div className="text-xs font-semibold mb-1">Recent</div>
                <div className="space-y-1">
                  {queue.map((q, i) => (
                    <div key={i} className="text-xs border dark:border-slate-700 rounded-lg p-2 flex justify-between bg-white dark:bg-slate-900"><span className="font-mono truncate">{q.station_id}</span><Badge variant="secondary" className="text-[10px]">{q.defect_class}</Badge></div>
                  ))}
                </div>
              </div>
            )}
            <div className="rounded-lg bg-sky-50 dark:bg-sky-950 border border-sky-200 dark:border-sky-800 p-2.5 text-xs">
              <div className="font-semibold flex items-center gap-1"><Sparkles className="h-3 w-3 text-sky-600" /> Glass & micro-interactions</div>
              <div className="text-slate-600 dark:text-slate-400 mt-1">Framer Motion pulses, tap scaling, and 85dB-optimized contrast. Dark mode supported.</div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="text-[11px] text-slate-400 text-center">Operator view optimized for 85 dB, gloves, 12-hour shifts · One-button ack is telemetry only (not auth) · Audio via Web Speech API (SpeechRecognition + speechSynthesis) · a11y: keyboard, focus ring, aria</div>
    </div>
  );
}
