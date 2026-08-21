import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, Shield, Factory, Eye, Cpu, MessageSquare, Clock, Gauge, Users, Lock, Database, Check, ChevronRight, Play, FileText, Phone, Mail, Brain, Sparkles, Bot, ScanEye, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* HERO — split, left text right visual, no centered pill+headline trap, no purple */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-10 pb-12 sm:pt-14 sm:pb-16 grid lg:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
        <div>
          <div className="inline-flex items-center gap-2 text-[11px] font-semibold tracking-wide text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 rounded-full px-3 py-1 bg-slate-50 dark:bg-slate-900">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live in 3 plants · Hyderabad · Frames never leave
          </div>
          <h1 className="mt-4 text-[32px] sm:text-[42px] font-bold tracking-tight leading-[1.05]">
            Factory AI
            <br />
            <span className="text-slate-600 dark:text-slate-400 font-semibold">without the factory risk.</span>
          </h1>
          <p className="mt-3 text-[15px] leading-6 text-slate-600 dark:text-slate-400 max-w-[52ch]">
            TANTU unifies OPC-UA, Modbus, MQTT, MTConnect and camera-as-adapter into one schema, one answer — on the operator’s line, in their language. Raw frames stay on-prem. Derived events only to cloud.
          </p>
          <div className="mt-5 flex flex-wrap gap-2.5">
            <Link href="/signup"><Button size="lg" className="h-11 px-6 bg-slate-900 hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 text-white">Start pilot — Rs 18K/mo <ArrowRight className="ml-1.5 h-4 w-4" /></Button></Link>
            <Link href="/login"><Button variant="outline" size="lg" className="h-11 px-6 border-slate-300 dark:border-slate-700">Sign in</Button></Link>
            <a href="#demo" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 px-3"><Play className="h-4 w-4" /> Watch 60s</a>
          </div>
          <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5" /> DPDP 2023</span>
            <span className="h-3 w-px bg-slate-200 dark:bg-slate-800" />
            <span>SOC2 patterns</span>
            <span className="h-3 w-px bg-slate-200 dark:bg-slate-800" />
            <span>data_residency=IN</span>
          </div>
          <div className="mt-6 flex items-center gap-4 border-t dark:border-slate-800 pt-4">
            <div className="text-xs">
              <div className="font-semibold">Trusted by</div>
              <div className="text-slate-500">Auto · Bearings · Pharma · 3 live clusters</div>
            </div>
            <div className="ml-auto flex items-center gap-2 text-[11px] font-mono">
              <span className="border dark:border-slate-800 rounded px-2 py-1 bg-slate-50 dark:bg-slate-900">OPC-UA</span>
              <span className="border dark:border-slate-800 rounded px-2 py-1 bg-slate-50 dark:bg-slate-900">MTConnect</span>
              <span className="border dark:border-slate-800 rounded px-2 py-1 bg-slate-50 dark:bg-slate-900">Modbus</span>
            </div>
          </div>
        </div>

        {/* Right — product shell, not aurora/blur, single subtle border */}
        <div id="demo" className="relative border dark:border-slate-800 rounded-xl overflow-hidden bg-slate-900 shadow-lg">
          <div className="h-8 flex items-center gap-1.5 px-3 bg-slate-800 border-b border-slate-700">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
            <span className="ml-2 text-[11px] font-mono text-slate-400">tantu.local — operator console</span>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-emerald-500 text-white font-semibold">● LIVE</span>
          </div>
          <div className="p-4 grid gap-3 bg-slate-50 dark:bg-slate-900">
            <div className="rounded-lg bg-white dark:bg-slate-800 border dark:border-slate-700 p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-7 w-7 rounded bg-amber-100 dark:bg-amber-900 grid place-items-center text-amber-700 dark:text-amber-300 text-xs font-bold">!</span>
                <div>
                  <div className="text-xs font-semibold">Bearing vibration high — line 2</div>
                  <div className="text-[11px] text-slate-500">pressure_drift · camera · 92% · 22ms</div>
                </div>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-900 text-white">ACK</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">Walk reads / day</div><div className="font-bold text-sm">48 → 6 <span className="text-emerald-600 font-normal">-87%</span></div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">MTTD</div><div className="font-bold text-sm">22 → 3 min</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">Opex / cluster</div><div className="font-bold text-sm">Rs 18K</div></div>
            </div>
            <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
              <div className="text-[11px] font-semibold text-slate-600">Vernacular — 5 languages</div>
              <div className="mt-1 text-sm font-bold">“Line 2 pressure jaasti — valve 3 check karo”</div>
              <div className="text-xs text-slate-500">hi · ta · te · kn · en + code-switch · 85dB · gloved</div>
            </div>
          </div>
          <div className="px-3 py-2 bg-white dark:bg-slate-800 border-t dark:border-slate-700 flex items-center justify-between text-xs">
            <span className="text-slate-500">p95 &lt;40ms edge · Nemotron-9B on-prem</span>
            <Link href="/login" className="font-medium text-sky-700 hover:underline inline-flex items-center gap-1">Try login <ChevronRight className="h-3 w-3" /></Link>
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF — dark strip with numbers, not 3 equal cards */}
      <section className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6">
          <div><div className="text-2xl font-bold">3</div><div className="text-xs text-slate-400">clusters live (Hyderabad)</div></div>
          <div><div className="text-2xl font-bold">99.2%</div><div className="text-xs text-slate-400">uptime · p95 38ms edge</div></div>
          <div><div className="text-2xl font-bold">12h</div><div className="text-xs text-slate-400">shifts · 85dB · gloved</div></div>
          <div><div className="text-2xl font-bold">5</div><div className="text-xs text-slate-400">languages · vernacular ACK</div></div>
        </div>
      </section>

      {/* HOW IT WORKS — horizontal line, not bento */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-bold tracking-tight">From sensor to decision</h2>
          <span className="text-xs text-slate-500">Frames never leave plant · derived events only</span>
        </div>
        <div className="mt-6 grid sm:grid-cols-4 gap-4 relative">
          <div className="hidden sm:block absolute top-[22px] left-[8%] right-[8%] h-px bg-slate-200 dark:bg-slate-800" />
          {[
            { n: "01", t: "Connect", d: "OPC-UA · Modbus · MQTT · MTConnect · EtherNet/IP · camera-as-adapter. One schema: DefectEvent / NormalizedReading.", icon: Factory },
            { n: "02", t: "Perceive", d: "Tiered edge: Pi5+Hailo-8L / Jetson Orin. <40ms, dust/glare compensated.", icon: Eye },
            { n: "03", t: "Reason", d: "Dual GENAI: Nemotron-9B on-prem + Gemini ER2 cloud on derived events only. Grounded RAG.", icon: Cpu },
            { n: "04", t: "Act", d: "Vernacular alert in operator language, one-button ACK, audit trail, NATS→SSE.", icon: MessageSquare },
          ].map((s) => (
            <div key={s.n} className="relative bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-800 p-4">
              <div className="h-7 w-7 rounded bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center text-[11px] font-bold">{s.n}</div>
              <div className="mt-3 font-semibold text-sm flex items-center gap-1.5"><s.icon className="h-4 w-4 text-slate-500" />{s.t}</div>
              <div className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">{s.d}</div>
            </div>
          ))}
        </div>
      </section>

      {/* AI DRIVEN — dual brain, edge, grounded RAG — make AI unmissable */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-3 py-1 text-[11px] font-bold tracking-wide">
          <Sparkles className="h-3.5 w-3.5" /> AI-DRIVEN · Dual brain · Grounded · Air-gapped option
        </div>
        <div className="mt-3 flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-[22px] sm:text-[26px] font-bold tracking-tight leading-none">Factory intelligence, <span className="text-sky-600">not just dashboards.</span></h2>
          <span className="text-xs text-slate-500">Nemotron-9B on-prem + Gemini ER2 cloud · Qdrant RAG · &lt;40ms edge</span>
        </div>
        <div className="mt-6 grid lg:grid-cols-3 gap-4">
          <div className="rounded-xl border dark:border-slate-800 bg-gradient-to-br from-slate-900 to-slate-800 text-white p-5 relative overflow-hidden">
            <div className="absolute -right-6 -top-6 h-20 w-20 rounded-full bg-sky-500/20 blur-2xl" />
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-sky-300"><Brain className="h-4 w-4" /> On-prem brain — air-gapped</div>
            <div className="mt-2 font-bold leading-tight">Nemotron-9B on your box</div>
            <div className="mt-1 text-sm leading-5 text-slate-300">Runs on Orin/Jetson, no internet needed. Answers “why did line 2 slow?” from derived events only — raw frames never leave plant. DPDP 2023 safe.</div>
            <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] font-mono">
              <span className="px-2 py-1 rounded bg-white/10 border border-white/15">VLLM</span><span className="px-2 py-1 rounded bg-white/10 border border-white/15">Qdrant RAG 5 docs</span><span className="px-2 py-1 rounded bg-white/10 border border-white/15">Grounded citations</span>
            </div>
          </div>
          <div className="rounded-xl border dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-500"><ScanEye className="h-4 w-4" /> Edge perception — &lt;40ms</div>
            <div className="mt-2 font-bold leading-tight">Pi5+Hailo-8L / Orin Nano / Thor</div>
            <div className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-400">Camera-as-adapter, FFT vibration, thermal, CT, gauge OCR. Dust/glare compensated, 85dB proof. <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border dark:border-slate-700">p95 38ms</span> on Hailo-8L.</div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Vision</div><div className="font-bold">YOLOv8-seg</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Vibration</div><div className="font-bold">FFT 1kHz</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Gauge</div><div className="font-bold">OCR 96%</div></div>
            </div>
          </div>
          <div className="rounded-xl border dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-500"><Bot className="h-4 w-4" /> Cloud brain — grounded</div>
            <div className="mt-2 font-bold leading-tight">Gemini ER2 on derived events</div>
            <div className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-400">Only `DefectEvent` (no image) leaves plant. RAG over Qdrant, grounded answers, vernacular `hi/ta/te/kn/en` + code-switch, one-button ACK.</div>
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"><Zap className="h-3 w-3" /> 22 → 3 min MTTD</span>
              <span className="text-slate-500">Mode A/B token opt</span>
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
          <span className="px-2.5 py-1 rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 font-semibold inline-flex items-center gap-1.5"><Sparkles className="h-3 w-3" /> Robotics: Fanuc · ABB · Kuka via EtherNet/IP</span>
          <span className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-900 border dark:border-slate-700">OPC-UA auto-discover (mDNS)</span>
          <span className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-900 border dark:border-slate-700">MTConnect · PROFINET · Modbus scan</span>
          <span className="px-2.5 py-1 rounded-full bg-white dark:bg-slate-900 border dark:border-slate-700">NATS → SSE · Timescale · Qdrant</span>
        </div>
      </section>

      {/* PERSONA BENEFITS — 3 columns with lists, not identical icon cards */}
      <section className="bg-slate-50 dark:bg-slate-900 border-y dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <h2 className="text-lg font-bold tracking-tight">Built for the floor, not the deck</h2>
          <div className="mt-6 grid lg:grid-cols-3 gap-6">
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Users className="h-4 w-4" /> Operator — 85dB, gloved, 12h</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> One-button ACK, haptics, optimistic update</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Voice in hi/ta/te/kn/en + code-switch</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> No menus, no scroll — 72px touch target</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">Open Operator →</Link>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Factory className="h-4 w-4" /> Maintenance — mixed-fleet</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Single grid: OPC-UA/Modbus/MQTT/camera unified</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> FFT, walk-reads before/after (Recharts), MTConnect</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Grounded copilot: ask “why did line 2 slow?”</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">Open Maintenance →</Link>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Gauge className="h-4 w-4" /> Plant Head — opex</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Rs 18K / cluster / mo, no capex</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Walk-reads 48→6 (-87%), MTTR 45→18min</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> 90-day pilot, reversible, exportable</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">Open Plant Head →</Link>
            </div>
          </div>
        </div>
      </section>

      {/* INTEGRATIONS — mono tags, not icon grid */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-slate-700 dark:text-slate-300">Adapters:</span>
          {["OPC-UA","Modbus","MQTT","MTConnect","EtherNet/IP","PROFINET","Camera-as-adapter (Hailo-8L)","NATS → SSE","Timescale","Qdrant"].map((k) => (
            <span key={k} className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border dark:border-slate-700 font-mono text-[11px]">{k}</span>
          ))}
        </div>
      </section>

      {/* SECURITY */}
      <section className="bg-slate-900 text-white rounded-xl mx-4 sm:mx-6 max-w-7xl lg:mx-auto p-6 sm:p-7 grid lg:grid-cols-[1.2fr_0.8fr] gap-6">
        <div>
          <div className="text-xs font-semibold tracking-wide text-slate-400 flex items-center gap-1.5"><Lock className="h-4 w-4" /> Security by default</div>
          <h3 className="mt-2 font-bold text-lg leading-tight">Frames impossible to exfil by type.</h3>
          <p className="mt-1 text-sm text-slate-300 leading-6">No image field in `DefectEvent`. JWT RS256, RBAC+ABAC (org→plant→line), Postgres RLS, TLS 1.3, Vault, gitleaks, pip-audit, signed images. OT network stays OT.</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-300">
            <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-400 mt-0.5" /> DPDP 2023 · SOC2 patterns · OWASP ASVS · data_residency=IN</li>
            <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-400 mt-0.5" /> Dual reasoning: Nemotron-9B on-prem, Gemini ER2 cloud on derived events only</li>
          </ul>
        </div>
        <div className="rounded-lg bg-white text-slate-900 p-4">
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5"><Database className="h-4 w-4" /> Tenancy</div>
          <div className="mt-2 text-sm font-mono">org_id → plant_ids → line_ids</div>
          <div className="mt-1 text-xs text-slate-600">Org Owner → Org Admin → Plant Head → Lead/Tech → Operator → Viewer + Bot. Invite with plant scope, audit every ack.</div>
          <Link href="/signup" className="mt-3 inline-flex text-sm font-medium text-sky-700 hover:underline">Create org <ArrowRight className="h-4 w-4 ml-1" /></Link>
        </div>
      </section>

      {/* PRICING — simple table, one highlighted, not 3 identical cards */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <h2 className="text-lg font-bold tracking-tight">Pilot pricing — no capex</h2>
        <div className="mt-6 border dark:border-slate-800 rounded-xl overflow-hidden">
          <div className="grid grid-cols-12 text-xs font-semibold tracking-wide bg-slate-50 dark:bg-slate-900 px-4 py-2.5 border-b dark:border-slate-800">
            <div className="col-span-5">Scope</div><div className="col-span-2 text-center">Clusters</div><div className="col-span-2 text-center">/ cluster</div><div className="col-span-3 text-right">Total / mo</div>
          </div>
          {[
            { name: "Pilot (recommended)", clusters: "3", per: "Rs 18K", total: "Rs 54K", hi: true },
            { name: "Rollout", clusters: "12", per: "Rs 16K", total: "Rs 1.92L", hi: false },
            { name: "At scale", clusters: "50+", per: "Rs 14K", total: "Custom", hi: false },
          ].map((r) => (
            <div key={r.name} className={`grid grid-cols-12 items-center px-4 py-3 text-sm ${r.hi ? "bg-sky-50 dark:bg-sky-950/30 font-semibold" : "bg-white dark:bg-slate-950"}`}>
              <div className="col-span-5 flex items-center gap-2">{r.name} {r.hi && <Badge className="bg-slate-900 text-white dark:bg-white dark:text-slate-900 text-[10px]">Recommended</Badge>}</div>
              <div className="col-span-2 text-center">{r.clusters}</div>
              <div className="col-span-2 text-center">{r.per}</div>
              <div className="col-span-3 text-right font-bold">{r.total}</div>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">Hardware on loan for pilot · 90 days · hardware amortized 36mo · includes edge (Pi5+Hailo-8L/Orin), platform, RAG, support · Exit: PG export, frames stay on-prem.</p>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-12">
        <div className="rounded-xl bg-slate-900 text-white p-6 sm:p-7 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="font-bold">Start with 3 clusters, 90 days.</div>
            <div className="text-sm text-slate-300">We’ll ship edge, wire 2 lines, and hand you vernacular ACK in week 1.</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/signup"><Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100">Create org <ArrowRight className="ml-1.5 h-4 w-4" /></Button></Link>
            <a href="mailto:hello@skopaq.ai" className="inline-flex items-center gap-1.5 text-sm px-4 py-2.5 rounded-lg border border-white/20 hover:bg-white/10"><Mail className="h-4 w-4" /> hello@skopaq.ai</a>
            <a href="tel:+910000000000" className="inline-flex items-center gap-1.5 text-sm px-4 py-2.5 rounded-lg border border-white/20 hover:bg-white/10"><Phone className="h-4 w-4" /> Talk</a>
          </div>
        </div>
        <div className="mt-3 text-center text-xs text-slate-500">By starting you agree to pilot terms · SOC2 audit trail · <Link href="/login" className="underline">Sign in</Link> if you have an account</div>
      </section>
    </div>
  );
}
