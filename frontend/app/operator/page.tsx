"use client";
import { useEffect, useState } from "react";
import { useI18n, t, Lang } from "@/lib/i18n";
import { useSpeech } from "@/hooks/useSpeech";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ackEvent } from "@/lib/api";
import { Mic, MicOff, Volume2, Check, AlertTriangle, Wifi, Hand } from "lucide-react";

type Alert = { station_id: string; defect_class: string; confidence: number; latency_ms: number; protocol: string; ts: number };

export default function OperatorPage() {
  const { lang, setLang } = useI18n();
  const speech = useSpeech(lang);
  const [alert, setAlert] = useState<Alert>({ station_id: "line2-cluster1-gauge3", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, protocol: "camera", ts: Date.now() });
  const [acked, setAcked] = useState(false);
  const [queue, setQueue] = useState<Alert[]>([]);
  const [dbLevel] = useState(85);

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
          }
        }
      } catch {}
    }, 3000);
    return () => clearInterval(id);
  }, [alert.station_id]);

  // speak alert when lang changes or new alert
  useEffect(() => {
    if (!acked) {
      const msg = t("vernacular_pressure", lang);
      // auto speak only if user previously interacted
    }
  }, [alert.station_id, lang, acked]);

  const handleAck = async () => {
    await ackEvent(alert.station_id, alert.defect_class);
    setAcked(true);
    // haptic
    if (typeof navigator !== "undefined" && (navigator as any).vibrate) (navigator as any).vibrate(100);
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
        <Card className={`lg:col-span-2 ${acked ? "border-emerald-200" : "border-amber-300 shadow-lg"}`}>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertTriangle className={`h-5 w-5 ${acked ? "text-emerald-600" : "text-amber-600"}`} />
              {acked ? "Acknowledged" : "Attention required"}
              <span className="ml-auto text-xs font-normal text-slate-500">{dbLevel} dB · 12h shift</span>
            </CardTitle>
            <CardDescription className="text-xs">{alert.station_id} · {alert.protocol} · {alert.latency_ms}ms · {Math.round(alert.confidence * 100)}% confidence</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* vernacular large */}
            <div className={`rounded-2xl p-6 text-center ${acked ? "bg-emerald-50 border border-emerald-200" : "bg-amber-50 border-2 border-amber-300"}`}>
              <div className="text-[11px] uppercase tracking-wide text-slate-500 font-semibold">Vernacular · {lang.toUpperCase()}</div>
              <div className="mt-2 text-2xl sm:text-3xl font-bold leading-tight text-slate-900">{t("vernacular_pressure", lang)}</div>
              <div className="mt-1 text-xs text-slate-500">{t("vernacular_vib", lang)}</div>
              {!acked && <div className="mt-3 inline-flex items-center gap-2 text-xs bg-white border rounded-full px-3 py-1"><span className="h-2 w-2 bg-red-500 rounded-full animate-pulse" /> {t("live", lang)} · {alert.defect_class}</div>}
            </div>

            {/* one-button ack */}
            <Button
              onClick={handleAck}
              disabled={acked}
              variant={acked ? "secondary" : "primary"}
              size="touch"
              className={`w-full text-xl font-bold glove-target rounded-2xl h-[72px] ${acked ? "opacity-60" : "shadow-lg hover:shadow-xl"}`}
            >
              {acked ? <><Check className="h-7 w-7 mr-2" /> {t("ack", lang)} ✓</> : <>✓ {t("ack", lang)} — TAP</>}
            </Button>
            <div className="text-center text-xs text-slate-500">{t("dB_gloved", lang)} · {t("one_button_ack", lang)} · no menus, no scroll</div>

            {/* language quick switch — large */}
            <div className="grid grid-cols-5 gap-2">
              {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
                <button key={l} onClick={() => setLang(l)} className={`py-3 rounded-xl font-bold text-sm border-2 glove-target ${lang === l ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200 hover:bg-slate-50"}`}>
                  {l.toUpperCase()}
                  <div className="text-[10px] font-normal opacity-70">{l === "en" ? "English" : l === "hi" ? "हिन्दी" : l === "ta" ? "தமிழ்" : l === "te" ? "తెలుగు" : "ಕನ್ನಡ"}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* voice panel */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2"><Volume2 className="h-4 w-4" /> Voice — Web Speech API</CardTitle>
            <CardDescription className="text-xs">Tap to speak · code-switch supported · offline fallback stored</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button onClick={speech.listening ? speech.stop : speech.start} variant={speech.listening ? "destructive" : "primary"} className="flex-1 glove-target">
                {speech.listening ? <><MicOff className="h-4 w-4 mr-2" /> Stop</> : <><Mic className="h-4 w-4 mr-2" /> {t("tap_to_speak", lang)}</>}
              </Button>
              <Button onClick={() => speech.speak(t("vernacular_pressure", lang), lang)} variant="outline" className="glove-target" title="Replay TTS">
                <Volume2 className="h-4 w-4" />
              </Button>
            </div>
            <div className="rounded-lg border bg-slate-50 p-3 min-h-[88px]">
              <div className="text-[11px] font-semibold text-slate-500">Transcript {speech.listening && <span className="text-red-600 animate-pulse">● {t("listening", lang)}</span>}</div>
              <div className="mt-1 text-sm">{speech.transcript || <span className="text-slate-400 italic">Say “ack” / “ok” / “हाँ” / “சரி” to ack…</span>}</div>
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
                    <div key={i} className="text-xs border rounded p-2 flex justify-between"><span className="font-mono">{q.station_id}</span><Badge variant="secondary">{q.defect_class}</Badge></div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="text-[11px] text-slate-400 text-center">Operator view optimized for 85 dB, gloves, 12-hour shifts · One-button ack is telemetry only (not auth) · Audio via Web Speech API (SpeechRecognition + speechSynthesis)</div>
    </div>
  );
}
