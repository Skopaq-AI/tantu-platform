import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { ArrowRight, Shield, Factory, Eye, Cpu, MessageSquare, Clock, Gauge, Users, Lock, Database, Check, ChevronRight, Play, FileText, Phone, Mail, Brain, Sparkles, Bot, ScanEye, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      {/* HERO — child-simple: what we do in one sentence */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-10 pb-12 sm:pt-14 sm:pb-16 grid lg:grid-cols-[1.05fr_0.95fr] gap-8 items-center">
        <div>
          <div className="inline-flex items-center gap-2 text-[11px] font-semibold tracking-wide text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800 rounded-full px-3 py-1 bg-slate-50 dark:bg-slate-900">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live in 3 factories near Hyderabad · Your photos never leave your factory
          </div>
          <h1 className="mt-4 text-[32px] sm:text-[42px] font-bold tracking-tight leading-[1.05]">
            Your factory tells you
            <br />
            <span className="text-sky-600">what&apos;s wrong — before it breaks.</span>
          </h1>
          <p className="mt-3 text-[15px] leading-6 text-slate-600 dark:text-slate-400 max-w-[52ch]">
            Think of your factory like a body. Machines are the heart, cameras & sensors are eyes and ears. <span className="font-semibold text-slate-800 dark:text-slate-200">TANTU is the doctor who lives inside your factory</span> — watches day and night and shouts <span className="font-semibold">“Line 2 is shaking — check valve 3”</span> in Hindi, Tamil, Telugu, Kannada or English. Your videos stay inside. Only a short text goes out, like an SMS.
          </p>
          <div className="mt-5 flex flex-wrap gap-2.5">
            <Link href="/signup"><Button size="lg" className="h-11 px-6 bg-slate-900 hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100 text-white">Try in your factory — Rs 18K/mo <ArrowRight className="ml-1.5 h-4 w-4" /></Button></Link>
            <Link href="/login"><Button variant="outline" size="lg" className="h-11 px-6 border-slate-300 dark:border-slate-700">Sign in</Button></Link>
            <a href="#demo" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:text-slate-900 px-3"><Play className="h-4 w-4" /> See in 60 seconds</a>
          </div>
          <div className="mt-4 flex items-center gap-3 text-xs text-slate-500">
            <span className="flex items-center gap-1.5"><Shield className="h-3.5 w-3.5" /> Made for Indian data rules</span>
            <span className="h-3 w-px bg-slate-200 dark:bg-slate-800" />
            <span>Trusted for factory privacy</span>
            <span className="h-3 w-px bg-slate-200 dark:bg-slate-800" />
            <span>Works with old & new machines</span>
          </div>
          <div className="mt-6 flex items-center gap-4 border-t dark:border-slate-800 pt-4">
            <div className="text-xs">
              <div className="font-semibold">Who uses it</div>
              <div className="text-slate-500">Auto · Bearings · Medicine · 3 factories live</div>
            </div>
            <div className="ml-auto flex items-center gap-2 text-[11px] font-semibold">
              <span className="border dark:border-slate-800 rounded-full px-2.5 py-1 bg-slate-50 dark:bg-slate-900">Any machine</span>
              <span className="border dark:border-slate-800 rounded-full px-2.5 py-1 bg-slate-50 dark:bg-slate-900">Any camera</span>
              <span className="border dark:border-slate-800 rounded-full px-2.5 py-1 bg-slate-50 dark:bg-slate-900">Any sensor</span>
            </div>
          </div>
        </div>

        {/* Right — product shell: what the worker actually sees */}
        <div id="demo" className="relative border dark:border-slate-800 rounded-xl overflow-hidden bg-slate-900 shadow-lg">
          <div className="h-8 flex items-center gap-1.5 px-3 bg-slate-800 border-b border-slate-700">
            <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
            <span className="ml-2 text-[11px] font-mono text-slate-400">factory floor — worker screen</span>
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-emerald-500 text-white font-semibold">● LIVE</span>
          </div>
          <div className="p-4 grid gap-3 bg-slate-50 dark:bg-slate-900">
            <div className="rounded-lg bg-white dark:bg-slate-800 border dark:border-slate-700 p-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="h-7 w-7 rounded bg-amber-100 dark:bg-amber-900 grid place-items-center text-amber-700 dark:text-amber-300 text-xs font-bold">!</span>
                <div>
                  <div className="text-xs font-semibold">Line 2 is shaking too much!</div>
                  <div className="text-[11px] text-slate-500">camera saw it · 92% sure · in 1 second</div>
                </div>
              </div>
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-slate-900 text-white">Got it</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">Walking to check</div><div className="font-bold text-sm">48 → 6 <span className="text-emerald-600 font-normal">-87%</span></div><div className="text-[10px] text-slate-500">less walking, more fixing</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">Time to notice</div><div className="font-bold text-sm">22 → 3 min</div><div className="text-[10px] text-slate-500">catch problem early</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-2.5"><div className="text-slate-500 text-[11px]">Cost per line</div><div className="font-bold text-sm">Rs 18K/mo</div><div className="text-[10px] text-slate-500">no big machine to buy</div></div>
            </div>
            <div className="rounded-lg border dark:border-slate-700 bg-white dark:bg-slate-800 p-3">
              <div className="text-[11px] font-semibold text-slate-600">Speaks your team&apos;s language</div>
              <div className="mt-1 text-sm font-bold">“Line 2 pressure jaasti — valve 3 check karo”</div>
              <div className="text-xs text-slate-500">Hindi · Tamil · Telugu · Kannada · English · mix also ok · loud room ok · with gloves ok</div>
            </div>
          </div>
          <div className="px-3 py-2 bg-white dark:bg-slate-800 border-t dark:border-slate-700 flex items-center justify-between text-xs">
            <span className="text-slate-500">Answers in under 1 second · works even without internet</span>
            <Link href="/login" className="font-medium text-sky-700 hover:underline inline-flex items-center gap-1">Try it <ChevronRight className="h-3 w-3" /></Link>
          </div>
        </div>
      </section>

      {/* SOCIAL PROOF — plain words */}
      <section className="bg-slate-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid grid-cols-2 sm:grid-cols-4 gap-6">
          <div><div className="text-2xl font-bold">3</div><div className="text-xs text-slate-400">factories running it now (Hyderabad)</div></div>
          <div><div className="text-2xl font-bold">99.2%</div><div className="text-xs text-slate-400">always on · answers in 1 sec</div></div>
          <div><div className="text-2xl font-bold">12h</div><div className="text-xs text-slate-400">works in noise, dust, with gloves</div></div>
          <div><div className="text-2xl font-bold">5</div><div className="text-xs text-slate-400">languages your team already uses</div></div>
        </div>
      </section>

      {/* HOW IT WORKS — 4 steps a child can follow */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="flex items-baseline justify-between gap-4">
          <h2 className="text-lg font-bold tracking-tight">How it works — in 4 simple steps</h2>
          <span className="text-xs text-slate-500">Your photos never leave the factory — only a short note does</span>
        </div>
        <div className="mt-6 grid sm:grid-cols-4 gap-4 relative">
          <div className="hidden sm:block absolute top-[22px] left-[8%] right-[8%] h-px bg-slate-200 dark:bg-slate-800" />
          {[
            { n: "01", t: "Plug in", d: "We connect to whatever you already have — old machines, new machines, cameras, sensors. One plug for all.", icon: Factory },
            { n: "02", t: "Watch", d: "A small computer on your floor watches night and day. Dust, bright light, loud noise — it still sees. No internet needed.", icon: Eye },
            { n: "03", t: "Understand", d: "Two smart helpers: one lives inside your factory (no internet), one in the cloud for hard questions. Both learn only from YOUR factory.", icon: Cpu },
            { n: "04", t: "Tell", d: "Worker gets a clear message: “Line 2 pressure high — check valve 3” — one big button to say Done. Full record saved.", icon: MessageSquare },
          ].map((s) => (
            <div key={s.n} className="relative bg-white dark:bg-slate-900 rounded-lg border dark:border-slate-800 p-4">
              <div className="h-7 w-7 rounded bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center text-[11px] font-bold">{s.n}</div>
              <div className="mt-3 font-semibold text-sm flex items-center gap-1.5"><s.icon className="h-4 w-4 text-slate-500" />{s.t}</div>
              <div className="mt-1 text-xs leading-5 text-slate-600 dark:text-slate-400">{s.d}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-lg bg-sky-50 dark:bg-sky-950/30 border border-sky-200 dark:border-sky-900 p-3 flex gap-3 items-start">
          <span className="text-lg">💡</span>
          <div className="text-xs leading-5 text-slate-700 dark:text-slate-300"><span className="font-semibold">For a child:</span> If factory = body, machines = heart, cameras = eyes, sensors = ears, TANTU = doctor who shouts “Fever! Check here!” before you feel sick.</div>
        </div>
      </section>

      {/* AI DRIVEN — still prominent, but child-simple */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <div className="inline-flex items-center gap-2 rounded-full bg-slate-900 text-white dark:bg-white dark:text-slate-900 px-3 py-1 text-[11px] font-bold tracking-wide">
          <Sparkles className="h-3.5 w-3.5" /> AI-DRIVEN · Two brains · Shows proof · Can work without internet
        </div>
        <div className="mt-3 flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-[22px] sm:text-[26px] font-bold tracking-tight leading-none">Not just charts. <span className="text-sky-600">Real help to fix faster.</span></h2>
          <span className="text-xs text-slate-500">Lives inside your factory + a bigger helper in the cloud · Learns from your manuals</span>
        </div>
        <div className="mt-6 grid lg:grid-cols-3 gap-4">
          <div className="rounded-xl border dark:border-slate-800 bg-gradient-to-br from-slate-900 to-slate-800 text-white p-5 relative overflow-hidden">
            <div className="absolute -right-6 -top-6 h-20 w-20 rounded-full bg-sky-500/20 blur-2xl" />
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-sky-300"><Brain className="h-4 w-4" /> Brain #1 — lives INSIDE your factory</div>
            <div className="mt-2 font-bold leading-tight">Works even without internet</div>
            <div className="mt-1 text-sm leading-5 text-slate-300">Like a teacher who lives on your shop floor. Knows YOUR machines and YOUR manuals. Answers “why did Line 2 slow down?” and shows proof — but never sends your photos outside.</div>
            <div className="mt-3 flex flex-wrap gap-1.5 text-[11px] font-semibold">
              <span className="px-2 py-1 rounded bg-white/10 border border-white/15">Works offline</span><span className="px-2 py-1 rounded bg-white/10 border border-white/15">Learns your manuals</span><span className="px-2 py-1 rounded bg-white/10 border border-white/15">Shows proof</span>
            </div>
          </div>
          <div className="rounded-xl border dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-500"><ScanEye className="h-4 w-4" /> Eyes that never blink — in under 1 second</div>
            <div className="mt-2 font-bold leading-tight">Cameras + sensors that never get tired</div>
            <div className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-400">They spot cracks, heat, shaking and meter readings — even in dust, glare and 85dB noise. Like a guard who never looks away. <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded border dark:border-slate-700">answers in 1 sec</span></div>
            <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Finds</div><div className="font-bold">Cracks</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Feels</div><div className="font-bold">Shakes</div></div>
              <div className="rounded-lg border dark:border-slate-700 bg-slate-50 dark:bg-slate-800 p-2"><div className="text-slate-500 text-[11px]">Reads</div><div className="font-bold">Meters</div></div>
            </div>
          </div>
          <div className="rounded-xl border dark:border-slate-800 bg-white dark:bg-slate-900 p-5">
            <div className="flex items-center gap-2 text-xs font-semibold tracking-wide text-slate-500"><Bot className="h-4 w-4" /> Brain #2 — bigger helper in the cloud</div>
            <div className="mt-2 font-bold leading-tight">For the hard “why?” questions</div>
            <div className="mt-1 text-sm leading-5 text-slate-600 dark:text-slate-400">Only a tiny text note goes to the cloud — never your photos. It reads your past notes and manuals and answers with proof, in your language — Hindi, Tamil, Telugu, Kannada, English.</div>
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800"><Zap className="h-3 w-3" /> 22 → 3 min to notice</span>
              <span className="text-slate-500">Fix faster, walk less</span>
            </div>
          </div>
        </div>
        <details className="mt-4 rounded-lg border dark:border-slate-800 bg-slate-50 dark:bg-slate-900 px-4 py-3">
          <summary className="text-xs font-semibold cursor-pointer list-none flex items-center justify-between">For engineers — what’s inside? <span className="text-slate-500 font-normal">click to see</span></summary>
          <div className="mt-2 flex flex-wrap gap-1.5 text-[11px] font-mono">
            <span className="px-2 py-1 rounded bg-white dark:bg-slate-800 border dark:border-slate-700">OPC-UA auto-find (mDNS)</span>
            <span className="px-2 py-1 rounded bg-white dark:bg-slate-800 border dark:border-slate-700">Modbus / MQTT / MTConnect / EtherNet-IP</span>
            <span className="px-2 py-1 rounded bg-white dark:bg-slate-800 border dark:border-slate-700">Pi5+Hailo-8L / Jetson Orin / Thor &lt;1s</span>
            <span className="px-2 py-1 rounded bg-white dark:bg-slate-800 border dark:border-slate-700">Nemotron-9B on-prem + Gemini in cloud</span>
            <span className="px-2 py-1 rounded bg-white dark:bg-slate-800 border dark:border-slate-700">Qdrant search + NATS live stream</span>
          </div>
        </details>
      </section>

      {/* PERSONA BENEFITS — plain jobs */}
      <section className="bg-slate-50 dark:bg-slate-900 border-y dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
          <h2 className="text-lg font-bold tracking-tight">Made for the people on the floor, not just the boss in the office</h2>
          <div className="mt-6 grid lg:grid-cols-3 gap-6">
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Users className="h-4 w-4" /> For the worker on the machine</div>
              <div className="text-[11px] text-slate-500">Loud (85dB), wearing gloves, 12-hour shift</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> One big button to say “Got it” — no tiny menus</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Hears and speaks your language — Hindi, Tamil, Telugu, Kannada, English</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> No scrolling, no typing — just tap</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">See worker screen →</Link>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Factory className="h-4 w-4" /> For the fixer (maintenance)</div>
              <div className="text-[11px] text-slate-500">Many different machines, one headache</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> One screen for all machines — old or new</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> See shake, heat, and camera photo side-by-side</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Ask in plain words: “Why did Line 2 slow?” — get answer with proof</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">See fixer screen →</Link>
            </div>
            <div className="rounded-lg bg-white dark:bg-slate-950 border dark:border-slate-800 p-5">
              <div className="text-xs font-semibold tracking-wide text-slate-500 flex items-center gap-1.5"><Gauge className="h-4 w-4" /> For the boss (factory head)</div>
              <div className="text-[11px] text-slate-500">Cost, time, and proof</div>
              <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700 dark:text-slate-300">
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Rs 18K per line per month — no big machine to buy</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Walk-checks 48→6 (-87%), fix time 45→18 min</li>
                <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" /> Try 90 days — if you don’t like it, take your data and leave</li>
              </ul>
              <Link href="/login" className="mt-4 inline-flex text-sm font-medium text-sky-700 hover:underline">See boss screen →</Link>
            </div>
          </div>
        </div>
      </section>

      {/* INTEGRATIONS — plain: works with what you have */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-slate-700 dark:text-slate-300">Works with what you already have:</span>
          {["Old & new machines (Siemens, Fanuc, ABB, Kuka...)", "Every sensor & meter", "Every camera", "Your screens — live updates", "Your manuals — AI reads them"].map((k) => (
            <span key={k} className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 border dark:border-slate-700 text-[11px]">{k}</span>
          ))}
        </div>
        <div className="mt-2 text-[11px] text-slate-500">Worried about names like OPC-UA or Modbus? We handle it. One plug talks to all of them.</div>
      </section>

      {/* SECURITY — child-simple */}
      <section className="bg-slate-900 text-white rounded-xl mx-4 sm:mx-6 max-w-7xl lg:mx-auto p-6 sm:p-7 grid lg:grid-cols-[1.2fr_0.8fr] gap-6">
        <div>
          <div className="text-xs font-semibold tracking-wide text-slate-400 flex items-center gap-1.5"><Lock className="h-4 w-4" /> Safe by design</div>
          <h3 className="mt-2 font-bold text-lg leading-tight">Your photos can never leave your factory — by design.</h3>
          <p className="mt-1 text-sm text-slate-300 leading-6">There is no “send photo” button in the code. Like sending an SMS instead of your whole photo album — only tiny text like “Line 2 is hot” leaves. Photos and videos stay on the small computer inside your factory. Even if someone taps wrong, photos can’t go out.</p>
          <ul className="mt-3 space-y-1.5 text-sm text-slate-300">
            <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-400 mt-0.5" /> Made for Indian data rules · Every tap is recorded — who did what, when</li>
            <li className="flex gap-2"><Check className="h-4 w-4 text-emerald-400 mt-0.5" /> Two helpers: one inside your factory (no internet needed), one in cloud — photos stay inside</li>
          </ul>
        </div>
        <div className="rounded-lg bg-white text-slate-900 p-4">
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5"><Database className="h-4 w-4" /> Who can see what? You decide.</div>
          <div className="mt-2 text-sm">Boss → Factory head → Team lead → Worker</div>
          <div className="mt-1 text-xs text-slate-600">Each person only sees their factory and their line. Invite by phone/ email, pick what they can see. Every “Got it” is saved.</div>
          <Link href="/signup" className="mt-3 inline-flex text-sm font-medium text-sky-700 hover:underline">Create your factory <ArrowRight className="h-4 w-4 ml-1" /></Link>
        </div>
      </section>

      {/* PRICING — plain */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-10">
        <h2 className="text-lg font-bold tracking-tight">Simple pricing — no big machine to buy</h2>
        <div className="mt-6 border dark:border-slate-800 rounded-xl overflow-hidden">
          <div className="grid grid-cols-12 text-xs font-semibold tracking-wide bg-slate-50 dark:bg-slate-900 px-4 py-2.5 border-b dark:border-slate-800">
            <div className="col-span-5">Try how many lines?</div><div className="col-span-2 text-center">Lines</div><div className="col-span-2 text-center">Per line</div><div className="col-span-3 text-right">Total / month</div>
          </div>
          {[
            { name: "Start here (most factories)", clusters: "3", per: "Rs 18K", total: "Rs 54K", hi: true },
            { name: "Grow", clusters: "12", per: "Rs 16K", total: "Rs 1.92L", hi: false },
            { name: "Big factory", clusters: "50+", per: "Rs 14K", total: "Ask us", hi: false },
          ].map((r) => (
            <div key={r.name} className={`grid grid-cols-12 items-center px-4 py-3 text-sm ${r.hi ? "bg-sky-50 dark:bg-sky-950/30 font-semibold" : "bg-white dark:bg-slate-950"}`}>
              <div className="col-span-5 flex items-center gap-2">{r.name} {r.hi && <Badge className="bg-slate-900 text-white dark:bg-white dark:text-slate-900 text-[10px]">Recommended</Badge>}</div>
              <div className="col-span-2 text-center">{r.clusters}</div>
              <div className="col-span-2 text-center">{r.per}</div>
              <div className="col-span-3 text-right font-bold">{r.total}</div>
            </div>
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">We lend you the small computers for the trial — 90 days. After that, small monthly fee includes the box, the app, and help. Don’t like it? Take your data and leave — your photos were always with you.</p>
      </section>

      {/* CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pb-12">
        <div className="rounded-xl bg-slate-900 text-white p-6 sm:p-7 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="font-bold">Start with 3 lines, 90 days.</div>
            <div className="text-sm text-slate-300">We’ll bring the boxes, connect 2 lines, and your team will get “Got it” alerts in their language in week one.</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link href="/signup"><Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100">Create your factory <ArrowRight className="ml-1.5 h-4 w-4" /></Button></Link>
            <a href="mailto:hello@skopaq.ai" className="inline-flex items-center gap-1.5 text-sm px-4 py-2.5 rounded-lg border border-white/20 hover:bg-white/10"><Mail className="h-4 w-4" /> hello@skopaq.ai</a>
            <a href="tel:+910000000000" className="inline-flex items-center gap-1.5 text-sm px-4 py-2.5 rounded-lg border border-white/20 hover:bg-white/10"><Phone className="h-4 w-4" /> Talk to us</a>
          </div>
        </div>
        <div className="mt-3 text-center text-xs text-slate-500">If you already have an account, <Link href="/login" className="underline">sign in here</Link>.</div>
      </section>
    </div>
  );
}
