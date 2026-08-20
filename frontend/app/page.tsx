"use client";
import Link from "next/link";
import { useI18n, t } from "@/lib/i18n";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { WalkReadsChart } from "@/components/charts/WalkReadsChart";
import { FFTChart } from "@/components/charts/FFTChart";
import { Mic, LayoutGrid, Gauge, ArrowRight, Shield, Zap, Languages } from "lucide-react";
import { useEffect, useState } from "react";

export default function Home() {
  const { lang } = useI18n();
  const [events, setEvents] = useState<any[]>([]);
  const [answer, setAnswer] = useState("");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/events`)
      .then((r) => r.json())
      .then(setEvents)
      .catch(() => setEvents([{ station_id: "line2-cluster1-gauge3", defect_class: "pressure_drift", confidence: 0.92, latency_ms: 22, protocol: "camera" }]));
  }, []);

  async function ask(q: string) {
    const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    try {
      const r = await fetch(`${API}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, plant_id: "plant-demo-01" }) });
      const j = await r.json();
      setAnswer(j.answer || j.vernacular?.[lang] || JSON.stringify(j));
    } catch {
      setAnswer("Offline — stub answer: check valve 3, vibration up 12% (grounded from tag map).");
    }
  }

  return (
    <div className="px-4 sm:px-6 py-6 space-y-6">
      {/* hero */}
      <div className="rounded-2xl bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900 text-white p-6 sm:p-8">
        <div className="flex flex-col lg:flex-row gap-6 justify-between">
          <div className="max-w-2xl">
            <Badge variant="secondary" className="bg-white/10 text-white border-white/20 mb-3">Production-grade · Hexagonal · Event-driven</Badge>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">Every machine speaks one language.</h1>
            <p className="mt-3 text-slate-300 text-sm leading-relaxed">TANTU orchestrates mixed-vendor floors — OPC-UA · Modbus · MQTT · MTConnect · EtherNet/IP · camera-as-adapter — into one schema, one answer, in the operator&apos;s language. Raw frames never leave plant.</p>
            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <Badge variant="outline" className="bg-white/10 text-white border-white/20"><Shield className="h-3 w-3 mr-1" /> DPDP & SOC2</Badge>
              <Badge variant="outline" className="bg-white/10 text-white border-white/20"><Zap className="h-3 w-3 mr-1" /> &lt;40ms edge</Badge>
              <Badge variant="outline" className="bg-white/10 text-white border-white/20"><Languages className="h-3 w-3 mr-1" /> hi/ta/te/kn + code-switch</Badge>
            </div>
          </div>
          <div className="lg:w-[380px] bg-white rounded-xl p-4 text-slate-900 shadow-xl">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Live fleet · NATS → SSE</div>
            <div className="mt-2 space-y-2">
              {events.slice(0, 3).map((e: any, i: number) => (
                <div key={i} className="flex items-center justify-between border rounded-lg p-2.5 text-xs">
                  <div><div className="font-mono text-[11px]">{e.station_id}</div><div className="text-slate-500">{e.protocol} · {e.defect_class} · {Math.round(e.confidence * 100)}% · {e.latency_ms}ms</div></div>
                  <Badge variant={e.defect_class === "none" ? "secondary" : "amber"}>{e.defect_class === "none" ? "OK" : "ALERT"}</Badge>
                </div>
              ))}
            </div>
            <Link href="/maintenance" className="mt-3 inline-flex items-center text-xs font-medium text-sky-600 hover:underline">Open Maintenance grid <ArrowRight className="h-3 w-3 ml-1" /></Link>
          </div>
        </div>
      </div>

      {/* three roles */}
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="border-amber-200">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Mic className="h-5 w-5 text-amber-600" /> Operator — Voice-first</CardTitle>
            <CardDescription>{t("dB_gloved", lang)} · {t("one_button_ack", lang)}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
              <div className="text-sm font-medium">🔊 {t("vernacular_pressure", lang)}</div>
              <div className="text-xs text-slate-500 mt-1">Confidence 92% · camera · 22ms · station line2-cluster1-gauge3</div>
              <Button size="touch" variant="primary" className="w-full mt-3 text-base font-bold glove-target">✓ {t("ack", lang)}</Button>
              <div className="text-[11px] text-slate-500 text-center mt-2">Gloved · 85 dB · one-button — no menus</div>
            </div>
            <div className="flex gap-2">
              <Link href="/operator" className="flex-1"><Button variant="outline" className="w-full">Open Operator view <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><LayoutGrid className="h-5 w-5 text-sky-600" /> Maintenance — One schema, mixed fleet</CardTitle>
            <CardDescription>OPC-UA · Modbus · MQTT · MTConnect · EtherNet/IP · camera — normalized to one DefectEvent/NormalizedReading</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <div className="grid grid-cols-1 gap-2 text-xs">
                  {events.map((e: any, i: number) => (
                    <div key={i} className="border rounded-lg p-2.5 flex justify-between items-center">
                      <div><div className="font-mono text-[11px]">{e.station_id}</div><div className="text-slate-500">{e.protocol} · {e.defect_class}</div></div>
                      <Badge variant="outline">{Math.round(e.confidence * 100)}%</Badge>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-3">
                <div className="border rounded-lg p-3">
                  <div className="text-xs font-semibold mb-2">FFT · vibration (edge &lt;40ms)</div>
                  <FFTChart />
                </div>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <input id="q-home" placeholder="why did line 2 slow down?" className="flex-1 border rounded-lg px-3 py-2 text-sm" />
              <Button variant="primary" onClick={() => { const el = document.getElementById("q-home") as HTMLInputElement; if (el?.value) ask(el.value); }}>{t("ask_copilot", lang)}</Button>
            </div>
            {answer && <div className="mt-3 bg-sky-50 border border-sky-200 rounded-lg p-3 text-sm">{answer}</div>}
            <Link href="/maintenance" className="mt-3 inline-block text-sm font-medium text-sky-600 hover:underline">Open full fleet grid →</Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Gauge className="h-5 w-5 text-emerald-600" /> Plant Head — Opex, reversible</CardTitle>
            <CardDescription>{t("pilot_before_after", lang)}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">Rs 18K <span className="text-sm font-normal text-slate-500">/cluster/mo</span></div>
            <div className="text-xs text-slate-500">Hardware amortized · 90-day pilot · reversible</div>
            <div className="mt-4">
              <div className="text-xs font-semibold mb-2">{t("walk_reads_title", lang)} — 48 → 6 / day</div>
              <WalkReadsChart />
            </div>
            <Link href="/plant-head"><Button variant="outline" className="w-full mt-3">Open Opex dashboard <ArrowRight className="h-4 w-4 ml-1" /></Button></Link>
          </CardContent>
        </Card>
      </div>

      {/* trust bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid sm:grid-cols-3 gap-6 text-sm">
            <div><div className="font-semibold">Architecture — 3 layers</div><div className="text-slate-500 text-xs mt-1">CONNECT (adapter fabric) → PERCEIVE (edge, tiered, on-prem) → REASON (dual GENAI: Nemotron-9B on-prem + Gemini ER2 cloud on derived events only)</div></div>
            <div><div className="font-semibold">Security by default</div><div className="text-slate-500 text-xs mt-1">JWT RS256 + RBAC+ABAC · Vault · TLS 1.3 · gitleaks · pip-audit · signed images · frames impossible to exfil by type</div></div>
            <div><div className="font-semibold">API docs</div><div className="text-xs mt-1 flex flex-wrap gap-2"><a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/docs`} className="text-sky-600 underline">/docs (Swagger)</a><a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/redoc`} className="text-sky-600 underline">/redoc</a><a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`} className="text-sky-600 underline">/health</a><a href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/metrics`} className="text-sky-600 underline">/metrics</a></div></div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
