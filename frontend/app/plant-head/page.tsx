"use client";
import { useI18n, t } from "@/lib/i18n";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { WalkReadsChart } from "@/components/charts/WalkReadsChart";
import { WalkTrendChart, FFTChart } from "@/components/charts/FFTChart";
import { Gauge, TrendingDown, Clock, Shield, Banknote, Calendar, ArrowUpRight, Check } from "lucide-react";
import { useEffect, useState } from "react";

export default function PlantHeadPage() {
  const { lang } = useI18n();
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/metrics`, { cache: "no-store" })
      .then((r) => r.json())
      .then(setMetrics)
      .catch(() => setMetrics({ walk_reads: { before: 48, after: 6 }, opex: 18000, uptime: 99.2 }));
  }, []);

  return (
    <div className="px-4 sm:px-6 py-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2"><Gauge className="h-5 w-5 text-emerald-600" /> {t("plant_head", lang)} <Badge variant="emerald">{t("opex_title", lang)}</Badge></h1>
        <Badge variant="outline" className="gap-1"><Calendar className="h-3 w-3" /> 90-day pilot · reversible</Badge>
      </div>

      {/* KPI row */}
      <div className="grid sm:grid-cols-3 gap-4">
        <Card className="border-emerald-200">
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1"><Banknote className="h-3 w-3" /> Opex / cluster / month</CardDescription>
            <CardTitle className="text-3xl">Rs 18K <span className="text-sm font-normal text-slate-500">/ mo</span></CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-slate-500">Hardware amortized over 36 mo · includes edge + support · no capex board approval</div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <div className="border rounded p-2"><div className="text-slate-500">Edge HW</div><div className="font-semibold">Rs 6.5K</div></div>
              <div className="border rounded p-2"><div className="text-slate-500">Platform + RAG</div><div className="font-semibold">Rs 8K</div></div>
              <div className="border rounded p-2"><div className="text-slate-500">Support</div><div className="font-semibold">Rs 3.5K</div></div>
              <div className="border rounded p-2 bg-emerald-50 border-emerald-200"><div className="text-slate-500">Vs manual</div><div className="font-semibold text-emerald-700">- Rs 42K</div></div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1"><TrendingDown className="h-3 w-3" /> Walk-reads / day</CardDescription>
            <CardTitle className="text-3xl">48 → 6 <span className="text-sm font-normal text-emerald-600">−87%</span></CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-slate-500">Operator hours saved: 3.2 h/shift · reallocated to value-add</div>
            <div className="mt-3 flex items-center gap-2 text-xs"><Check className="h-4 w-4 text-emerald-600" /> Before: manual gauge rounds · After: camera-as-adapter (Hailo-8L) + OPC-UA, derived events only</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="flex items-center gap-1"><Clock className="h-3 w-3" /> MTTD / MTTR · Uptime</CardDescription>
            <CardTitle className="text-3xl">99.2% <span className="text-sm font-normal text-slate-500">uptime</span></CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-slate-500">MTTD 22 min → 3 min · MTTR 45 min → 18 min · p95 edge latency &lt;40ms</div>
            <div className="mt-3 h-[80px]">
              <WalkTrendChart />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* charts row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">{t("walk_reads_title", lang)} — {t("pilot_before_after", lang)}</CardTitle>
            <CardDescription className="text-xs">Shift handover · pilot plants: demo-01, demo-02 · 90 days</CardDescription>
          </CardHeader>
          <CardContent>
            <WalkReadsChart />
            <div className="mt-2 text-[11px] text-slate-500 text-center">Derived telemetry only · raw frames never leave plant · DPDP 2023 compliant</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cost → Value · 18-month projection</CardTitle>
            <CardDescription className="text-xs">Transparent pilot → rollout · reversible · no vendor lock-in</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="border rounded-lg p-3 text-center"><div className="text-slate-500">Pilot (3 clusters)</div><div className="font-bold text-lg">Rs 54K</div><div className="text-slate-500">/ mo</div></div>
                <div className="border rounded-lg p-3 text-center bg-sky-50 border-sky-200"><div className="text-slate-500">Rollout (12)</div><div className="font-bold text-lg">Rs 2.16L</div><div className="text-slate-500">/ mo</div></div>
                <div className="border rounded-lg p-3 text-center"><div className="text-slate-500">Savings (12)</div><div className="font-bold text-lg text-emerald-600">Rs 5L</div><div className="text-slate-500">/ mo</div></div>
              </div>
              <div className="border rounded-lg p-3 bg-slate-50 text-xs space-y-1">
                <div className="font-semibold">Pilot terms</div>
                <div className="text-slate-600">• 90 days · 3 clusters · hardware on loan · full feature parity with production</div>
                <div className="text-slate-600">• Exit: keep data (Postgres/Timescale export) · no lock-in · frames remain on-prem</div>
                <div className="text-slate-600">• Success: walk-reads ↓80%, MTTD ↓70%, vernacular ack &gt;90%</div>
              </div>
              <Button variant="primary" className="w-full">Download pilot one-pager <ArrowUpRight className="h-4 w-4 ml-1" /></Button>
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

      {/* raw frames never leave */}
      <div className="rounded-xl bg-slate-900 text-white p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm font-medium">Raw frames never leave plant — enforced by type (DefectEvent has no image field)</div>
        <Badge variant="secondary" className="bg-white text-slate-900">Auditable · SOC2-ready</Badge>
      </div>
    </div>
  );
}
