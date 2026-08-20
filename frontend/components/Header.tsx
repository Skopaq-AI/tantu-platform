"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n, LANG_NATIVE, Lang } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Mic, LayoutGrid, Gauge, Activity } from "lucide-react";
import { useEffect, useState } from "react";

const nav = [
  { href: "/operator", label: "Operator", icon: Mic, langKey: "operator" },
  { href: "/maintenance", label: "Maintenance", icon: LayoutGrid, langKey: "maintenance" },
  { href: "/plant-head", label: "Plant Head", icon: Gauge, langKey: "plant_head" },
];

export function Header() {
  const pathname = usePathname();
  const { lang, setLang } = useI18n();
  const [health, setHealth] = useState<"ok" | "offline" | "loading">("loading");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`)
      .then((r) => (r.ok ? setHealth("ok") : setHealth("offline")))
      .catch(() => setHealth("offline"));
  }, []);

  return (
    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-slate-900 text-white grid place-items-center font-bold text-sm">T</div>
          <div>
            <div className="font-bold tracking-tight leading-none">TANTU <span className="text-sky-600 font-medium">Mixed-Fleet</span></div>
            <div className="text-[11px] text-slate-500 hidden sm:block">Raw frames never leave plant · Dual reasoning</div>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {nav.map((n) => {
            const active = pathname === n.href;
            return (
              <Link key={n.href} href={n.href} className={cn("px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition", active ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100")}>
                <n.icon className="h-4 w-4" /> {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1">
            {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
              <button key={l} onClick={() => setLang(l)} className={cn("px-2 py-1 rounded text-xs font-medium border", lang === l ? "bg-sky-600 text-white border-sky-600" : "bg-white text-slate-600 hover:bg-slate-50")}>
                {LANG_NATIVE[l]}
              </button>
            ))}
          </div>
          <Badge variant={health === "ok" ? "emerald" : health === "offline" ? "red" : "secondary"} className="hidden sm:inline-flex">
            <Activity className="h-3 w-3 mr-1" /> {health === "ok" ? "API OK" : health === "offline" ? "Offline" : "…"}
          </Badge>
        </div>
      </div>
      {/* mobile nav */}
      <div className="md:hidden border-t bg-white flex">
        {nav.map((n) => {
          const active = pathname === n.href;
          return (
            <Link key={n.href} href={n.href} className={cn("flex-1 py-2.5 text-center text-xs font-medium flex flex-col items-center gap-1", active ? "text-sky-600 bg-sky-50" : "text-slate-500")}>
              <n.icon className="h-4 w-4" /> {n.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
