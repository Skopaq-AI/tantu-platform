"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n, LANG_NATIVE, Lang } from "@/lib/i18n";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Mic, LayoutGrid, Gauge, Activity, Moon, Sun, Menu } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "@/lib/toast";

const nav = [
  { href: "/operator", label: "Operator", icon: Mic, langKey: "operator", desc: "Voice · 85dB" },
  { href: "/maintenance", label: "Maintenance", icon: LayoutGrid, langKey: "maintenance", desc: "Fleet · NATS" },
  { href: "/plant-head", label: "Plant Head", icon: Gauge, langKey: "plant_head", desc: "Opex · Pilot" },
];

export function Header() {
  const pathname = usePathname();
  const { lang, setLang } = useI18n();
  const [health, setHealth] = useState<"ok" | "offline" | "loading">("loading");
  const [dark, setDark] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const d = localStorage.getItem("tantu_dark") === "1" || (window.matchMedia("(prefers-color-scheme: dark)").matches && !localStorage.getItem("tantu_dark"));
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`)
      .then((r) => (r.ok ? setHealth("ok") : setHealth("offline")))
      .catch(() => setHealth("offline"));
    const id = setInterval(() => {
      fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`, { cache: "no-store" })
        .then((r) => setHealth(r.ok ? "ok" : "offline"))
        .catch(() => setHealth("offline"));
    }, 15000);
    return () => clearInterval(id);
  }, []);

  const toggleDark = () => {
    const n = !dark;
    setDark(n);
    document.documentElement.classList.toggle("dark", n);
    localStorage.setItem("tantu_dark", n ? "1" : "0");
  };

  return (
    <header className="sticky top-0 z-40 glass border-b dark:border-slate-800">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-slate-900 text-white px-3 py-1 rounded text-xs">Skip to content</a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2.5 group" aria-label="TANTU home">
          <div className="h-9 w-9 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold text-[13px] tracking-tight shadow-sm group-hover:shadow-md transition-all group-active:scale-95">
            T
          </div>
          <div className="hidden sm:block">
            <div className="font-bold tracking-tight leading-none text-sm">TANTU <span className="text-sky-600 font-medium">Mixed-Fleet</span></div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">Raw frames never leave plant · Dual reasoning</div>
          </div>
          <div className="sm:hidden font-bold text-sm">TANTU</div>
        </Link>

        <nav className="hidden md:flex items-center gap-1" aria-label="Primary">
          {nav.map((n) => {
            const active = pathname === n.href;
            return (
              <Link
                key={n.href}
                href={n.href}
                className={cn(
                  "px-3.5 py-2 rounded-xl text-sm font-medium flex items-center gap-1.5 transition-all",
                  active ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                )}
                aria-current={active ? "page" : undefined}
              >
                <n.icon className="h-4 w-4" /> {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-1.5 sm:gap-2">
          <div className="hidden lg:flex items-center gap-1 rounded-full border bg-white dark:bg-slate-900 dark:border-slate-700 p-1">
            {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
              <button
                key={l}
                onClick={() => {
                  setLang(l);
                  toast.success(`Language: ${l.toUpperCase()}`);
                }}
                aria-label={`Switch to ${l}`}
                aria-pressed={lang === l}
                className={cn("px-2.5 py-1 rounded-full text-xs font-bold border transition", lang === l ? "bg-sky-600 text-white border-sky-600 shadow-sm" : "bg-transparent text-slate-600 dark:text-slate-300 border-transparent hover:bg-slate-100 dark:hover:bg-slate-800")}
              >
                {LANG_NATIVE[l]}
              </button>
            ))}
          </div>
          <Badge variant={health === "ok" ? "emerald" : health === "offline" ? "red" : "secondary"} className="hidden sm:inline-flex gap-1">
            <Activity className={cn("h-3 w-3", health === "ok" && "animate-pulse")} /> {health === "ok" ? "API OK" : health === "offline" ? "Offline" : "…"}
          </Badge>
          <Button variant="ghost" size="icon" aria-label="Toggle theme" onClick={toggleDark} className="h-9 w-9 rounded-full">
            {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon" className="md:hidden h-9 w-9" aria-label="Menu" onClick={() => setMobileOpen(!mobileOpen)}>
            <Menu className="h-4 w-4" />
          </Button>
        </div>
      </div>
      {/* mobile lang + nav */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-white dark:bg-slate-900 px-4 py-3 space-y-3">
          <div className="flex gap-1 flex-wrap">
            {(["en", "hi", "ta", "te", "kn"] as Lang[]).map((l) => (
              <button key={l} onClick={() => setLang(l)} className={cn("px-3 py-1.5 rounded-full text-xs font-bold border", lang === l ? "bg-sky-600 text-white border-sky-600" : "bg-white dark:bg-slate-800 dark:border-slate-700")}>
                {LANG_NATIVE[l]} <span className="font-normal opacity-70 hidden sm:inline">{l}</span>
              </button>
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2">
            {nav.map((n) => {
              const active = pathname === n.href;
              return (
                <Link key={n.href} href={n.href} onClick={() => setMobileOpen(false)} className={cn("rounded-xl border p-3 text-center flex flex-col items-center gap-1", active ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-slate-50 dark:bg-slate-800")}>
                  <n.icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{n.label}</span>
                  <span className="text-[10px] opacity-60">{n.desc}</span>
                </Link>
              );
            })}
          </div>
        </div>
      )}
      <div className="md:hidden border-t bg-white dark:bg-slate-900 flex">
        {nav.map((n) => {
          const active = pathname === n.href;
          return (
            <Link key={n.href} href={n.href} className={cn("flex-1 py-2.5 text-center text-xs font-medium flex flex-col items-center gap-1 border-r last:border-0 dark:border-slate-800", active ? "text-sky-600 bg-sky-50 dark:bg-sky-950 dark:text-sky-300" : "text-slate-500 dark:text-slate-400")}>
              <n.icon className="h-4 w-4" /> {n.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
