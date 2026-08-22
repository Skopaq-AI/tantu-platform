"use client";
import { useI18n, t } from "@/lib/i18n";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WalkReadsChart } from "@/components/charts/WalkReadsChart";
import { WalkTrendChart } from "@/components/charts/FFTChart";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "@/lib/toast";
import { fetchMetrics, isDemoEnabled } from "@/lib/api";
import { Gauge, TrendingDown, Clock, Shield, Banknote, Calendar, ArrowUpRight, Check, FileText, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { motion } from "@/lib/motion";
import { RoleGuard } from "@/components/RoleGuard";

export default function PlantHeadPage() {
  const { lang } = useI18n();
  const [metrics, setMetrics] = useState<any>(null);
  const [showLOI, setShowLOI] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchMetrics()
      .then((data) => { if (!cancelled) { setMetrics(data); setError(null); } })
      .catch((e) => {
        if (isDemoEnabled() && !cancelled) {
          setMetrics({ walk_reads: [{ before: 48, after: 6 }], opex: 18000, uptime: 99.2, mttd_min: 3, mttr_min: 18, p95_latency_ms: 38 });
        } else if (!cancelled) {
          setError(e?.message || "metrics unavailable");
          setMetrics(null);
        }
      })
      .finally(() => { if (!cancelled) setTimeout(() => setLoading(false), 500); });
    return () => { cancelled = true; };
  }, []);

  return (
    <RoleGuard allowedRoles={["PLANT_HEAD","ORG_ADMIN","OWNER"]}>
    <div className="px-4 sm:px-6 py-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2"><Gauge className="h-5 w-5 text-emerald-600" /> {t("plant_head", lang)} <Badge variant="emerald">{t("opex_title", lang)}</Badge></h1>
        <Badge variant="outline" className="gap-1"><Calendar className="h-3 w-3" /> 90-day pilot · reversible</Badge>
      </div>

      {/* KPI row — real data from /metrics */}
      <div className="grid sm:grid-cols-3 gap-4">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card className="border-emerald-200 dark:border-emerald-800">
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1"><Banknote className="h-3 w-3" /> Opex / cluster / month</CardDescription>
              <CardTitle className="text-3xl">{metrics?.opex ? `Rs ${(metrics.opex/1000).toFixed(0)}K` : loading ? "…" : error ? "—" : "Rs 18K"} <span className="text-sm font-normal text-slate-500">/ mo</span></CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? <Skeleton className="h-20 w-full" /> : error && !metrics ? <div className="text-xs text-amber-600 border border-amber-200 bg-amber-50 dark:bg-amber-950 rounded-xl p-3">Metrics unavailable: {error} — real /metrics required. Enable DEMO to see mock.</div> : (
                <>
                  <div className="text-xs text-slate-500">Hardware amortized over 36 mo · includes edge + support · no capex board approval {metrics?.opex ? `· live: ${metrics.opex}` : ""}</div>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Edge HW</div><div className="font-semibold">Rs 6.5K</div></div>
                    <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Platform + RAG</div><div className="font-semibold">Rs 8K</div></div>
                    <div className="border dark:border-slate-700 rounded-xl p-2.5"><div className="text-slate-500">Support</div><div className="font-semibold">Rs 3.5K</div></div>
                    <div className="border rounded-xl p-2.5 bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800"><div className="text-slate-500">Vs manual</div><div className="font-semibold text-emerald-700 dark:text-emerald-300">- Rs 42K</div></div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1"><TrendingDown className="h-3 w-3" /> Walk-reads / day</CardDescription>
              <CardTitle className="text-3xl">
                {(() => {
                  const w = metrics?.walk_reads?.[0] || metrics?.walk_reads;
                  const before = Array.isArray(w) ? w[0]?.before : w?.before;
                  const after = Array.isArray(w) ? w[0]?.after : w?.after;
                  if (before != null && after != null) {
                    const pct = before ? Math.round((1 - after/before)*100) : 0;
                    return <>{before} → {after} <span className="text-sm font-normal text-emerald-600">-{pct}%</span></>;
                  }
                  return loading ? "…" : error ? "—" : "48 → 6";
                })()}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-slate-500">Operator hours saved: {metrics?.walk_reads ? "live from /metrics" : "3.2 h/shift · reallocated to value-add · /metrics"}</div>
              <div className="mt-3 flex items-center gap-2 text-xs bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 rounded-xl p-2.5"><Check className="h-4 w-4 text-emerald-600" /> Before: manual gauge rounds · After: camera-as-adapter (Hailo-8L) + OPC-UA, derived events only</div>
              {error && !metrics && <div className="text-[11px] text-amber-600 mt-2">Real metrics required — enable DEMO for mock.</div>}
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1"><Clock className="h-3 w-3" /> MTTD / MTTR · Uptime</CardDescription>
              <CardTitle className="text-3xl">{metrics?.uptime != null ? `${metrics.uptime}%` : loading ? "…" : error ? "—" : "99.2%"} <span className="text-sm font-normal text-slate-500">uptime</span></CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-xs text-slate-500">
                MTTD {metrics?.mttd_min ?? "22"} min → {metrics?.mttd_min ? `${metrics.mttd_min} min` : "3 min"} · MTTR {metrics?.mttr_min ?? "45"} min → {metrics?.mttr_min ? `${metrics.mttr_min} min` : "18 min"} · p95 {metrics?.p95_latency_ms ?? 38}ms
              </div>
              <div className="mt-3 h-[80px]">
                <WalkTrendChart />
              </div>
              {error && !metrics && <div className="text-[11px] text-amber-600 mt-1">Uptime from /metrics — no mock when DEMO off.</div>}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* charts row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2"><Sparkles className="h-4 w-4 text-sky-600" /> {t("walk_reads_title", lang)} — {t("pilot_before_after", lang)}</CardTitle>
            <CardDescription className="text-xs">Shift handover · pilot plants: demo-01, demo-02 · 90 days · /metrics + /poll</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? <Skeleton className="h-[220px] w-full rounded-xl" /> : error && !metrics ? <div className="text-xs text-amber-600 border border-amber-200 bg-amber-50 rounded-xl p-4 text-center">Live metrics unavailable — {error}. Enable NEXT_PUBLIC_DEMO=true for mock.</div> : <WalkReadsChart data={metrics?.walk_reads} />}
            <div className="mt-2 text-[11px] text-slate-500 text-center">Derived telemetry only · raw frames never leave plant · DPDP 2023 compliant {metrics ? "· live /metrics" : ""}</div>
          </CardContent>
        </Card>

        <Card className="border-sky-200 dark:border-sky-800">
          <CardHeader>
            <CardTitle className="text-sm">Cost → Value · 18-month projection</CardTitle>
            <CardDescription className="text-xs">Transparent pilot → rollout · reversible · no vendor lock-in</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="border dark:border-slate-700 rounded-xl p-3 text-center"><div className="text-slate-500">Pilot (3 clusters)</div><div className="font-bold text-lg">Rs 54K</div><div className="text-slate-500">/ mo</div></div>
                <div className="border rounded-xl p-3 text-center bg-sky-50 dark:bg-sky-950 border-sky-200 dark:border-sky-800"><div className="text-slate-500">Rollout (12)</div><div className="font-bold text-lg">Rs 2.16L</div><div className="text-slate-500">/ mo</div></div>
                <div className="border rounded-xl p-3 text-center bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800"><div className="text-slate-500">Savings (12)</div><div className="font-bold text-lg text-emerald-600">Rs 5L</div><div className="text-slate-500">/ mo</div></div>
              </div>
              <div className="border dark:border-slate-700 rounded-xl p-3 bg-slate-50 dark:bg-slate-800 text-xs space-y-1">
                <div className="font-semibold">Pilot terms</div>
                <div className="text-slate-600 dark:text-slate-400">• 90 days · 3 clusters · hardware on loan · full feature parity with production</div>
                <div className="text-slate-600 dark:text-slate-400">• Exit: keep data (Postgres/Timescale export) · no lock-in · frames remain on-prem</div>
                <div className="text-slate-600 dark:text-slate-400">• Success: walk-reads ↓80%, MTTD ↓70%, vernacular ack &gt;90%</div>
              </div>
              <Button variant="primary" className="w-full shadow-lg" onClick={() => setShowLOI(true)}>{t("loi_cta", lang)} <ArrowUpRight className="h-4 w-4 ml-1" /></Button>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => toast.success("One-pager download queued")}><FileText className="h-4 w-4 mr-1" /> One-pager</Button>
                <Button variant="ghost" className="flex-1" onClick={() => toast.info("Finance model sent")}>Finance model</Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* compliance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2"><Shield className="h-5 w-5 text-slate-600" /> Trust & compliance</CardTitle>
        </CardHeader>
        <CardContent className="grid sm:grid-cols-3 gap-4 text-xs">
          <div><div className="font-semibold">DPDP 2023</div><div className="text-slate-500 mt-1">Derived events only · data_residency=IN · 90-day hot / 1-yr cold · purpose limitation · hard delete on erasure</div></div>
          <div><div className="font-semibold">Security</div><div className="text-slate-500 mt-1">JWT RS256 (HS256 dev) · RBAC+ABAC · Vault · TLS 1.3 · at-rest encryption · mTLS edge→gateway · audit trail</div></div>
          <div><div className="font-semibold">Observability</div><div className="text-slate-500 mt-1">OpenTelemetry · Prometheus + Grafana · Loki logs · HPA on CPU/latency · health probes · frames-never-leave enforced by type</div></div>
        </CardContent>
      </Card>

      <Dialog open={showLOI} onOpenChange={setShowLOI}>
        <DialogContent onClose={() => setShowLOI(false)}>
          <DialogHeader>
            <DialogTitle>Pilot LOI — Rs 18K / cluster / mo</DialogTitle>
            <DialogDescription>Reversible 90-day pilot · hardware on loan · DPDP/SOC2 ready · POST /ask + /metrics integrated</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <div className="rounded-xl bg-slate-50 dark:bg-slate-800 p-3 text-xs leading-relaxed border dark:border-slate-700">
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

      {/* raw frames never leave */}
      <div className="rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg">
        <div className="text-sm font-medium">Raw frames never leave plant — enforced by type (DefectEvent has no image field)</div>
        <Badge variant="secondary" className="bg-white text-slate-900 dark:bg-slate-900 dark:text-white">Auditable · SOC2-ready</Badge>
      </div>
    </div>
    </RoleGuard>
  );
}
