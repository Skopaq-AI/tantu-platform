"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useI18n, LANG_NATIVE, Lang } from "@/lib/i18n";
import { useAuth, roleBadgeVariant, roleLabel } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Mic, LayoutGrid, Gauge, Activity, Moon, Sun, Menu, LogIn, LogOut, Shield, ChevronDown, Users, Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "@/lib/toast";
import { API_URL } from "@/lib/api";

const nav = [
  { href: "/operator", label: "Operator", icon: Mic, langKey: "operator", desc: "Voice · 85dB", roles: ["OPERATOR", "ORG_ADMIN", "OWNER"] },
  { href: "/maintenance", label: "Maintenance", icon: LayoutGrid, langKey: "maintenance", desc: "Fleet · NATS", roles: ["MAINTENANCE", "MAINTENANCE_TECH", "MAINTENANCE_LEAD", "ORG_ADMIN", "OWNER"] },
  { href: "/plant-head", label: "Plant Head", icon: Gauge, langKey: "plant_head", desc: "Opex · Pilot", roles: ["PLANT_HEAD", "ORG_ADMIN", "OWNER"] },
];

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const { lang, setLang } = useI18n();
  const { user, isAuthenticated, logout, orgs, currentOrg, switchOrg } = useAuth();
  const [health, setHealth] = useState<"ok" | "offline" | "loading">("loading");
  const [dark, setDark] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showOrgMenu, setShowOrgMenu] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  useEffect(() => {
    const d = localStorage.getItem("tantu_dark") === "1" || (window.matchMedia("(prefers-color-scheme: dark)").matches && !localStorage.getItem("tantu_dark"));
    setDark(d);
    document.documentElement.classList.toggle("dark", d);
    fetch(`${API_URL}/health`)
      .then((r) => (r.ok ? setHealth("ok") : setHealth("offline")))
      .catch(() => setHealth("offline"));
    const id = setInterval(() => {
      fetch(`${API_URL}/health`, { cache: "no-store" })
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

  const handleLogout = async () => {
    await logout();
    toast.success("Signed out");
    router.push("/login");
    setShowUserMenu(false);
  };

  const visibleNav = nav.filter((n) => {
    if (!isAuthenticated || !user) return true; // show all when not logged in, but RoleGuard will enforce
    const ru = (user.role || "").toUpperCase();
    if (ru === "ORG_ADMIN" || ru === "OWNER" || ru === "ADMIN") return true;
    if (n.href === "/operator") return ru === "OPERATOR";
    if (n.href === "/maintenance") return ru === "MAINTENANCE" || ru.startsWith("MAINTENANCE_");
    if (n.href === "/plant-head") return ru === "PLANT_HEAD";
    return false;
  });

  const displayNav = visibleNav.length ? visibleNav : nav;

  return (
    <header className="sticky top-0 z-40 glass border-b dark:border-slate-800">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-slate-900 text-white px-3 py-1 rounded text-xs">
        Skip to content
      </a>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
        <Link href="/" className="flex items-center gap-2.5 group" aria-label="TANTU home">
          <div className="h-9 w-9 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold text-[13px] tracking-tight shadow-sm group-hover:shadow-md transition-all group-active:scale-95">
            T
          </div>
          <div className="hidden sm:block">
            <div className="font-bold tracking-tight leading-none text-sm">
              TANTU <span className="text-sky-600 font-medium">Mixed-Fleet</span>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400">Raw frames never leave plant · Dual reasoning</div>
          </div>
          <div className="sm:hidden font-bold text-sm">TANTU</div>
        </Link>

        <nav className="hidden md:flex items-center gap-1" aria-label="Primary">
          {displayNav.map((n) => {
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
          {/* admin link for ORG_ADMIN/OWNER */}
          {isAuthenticated && user && (user.role === "ORG_ADMIN" || user.role === "OWNER" || user.role === "ADMIN") && (
            <Link
              href="/admin/users"
              className={cn(
                "px-3.5 py-2 rounded-xl text-sm font-medium flex items-center gap-1.5 transition-all",
                pathname.startsWith("/admin") ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900 shadow-sm" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              )}
            >
              <Users className="h-4 w-4" /> Admin
            </Link>
          )}
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

          {/* org switcher — visible when authenticated and multiple orgs or single */}
          {isAuthenticated && currentOrg && (
            <div className="relative hidden sm:block">
              <button
                onClick={() => setShowOrgMenu(!showOrgMenu)}
                className="flex items-center gap-1.5 border dark:border-slate-700 rounded-full px-3 py-1.5 bg-white dark:bg-slate-900 text-xs font-medium hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                aria-label="Switch organization"
              >
                <Building2 className="h-3.5 w-3.5 text-slate-500" />
                <span className="max-w-[100px] truncate">{currentOrg.name}</span>
                <ChevronDown className={cn("h-3 w-3 text-slate-400 transition", showOrgMenu && "rotate-180")} />
              </button>
              {showOrgMenu && (
                <div className="absolute right-0 mt-2 w-56 rounded-xl border dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl py-1 z-50">
                  <div className="px-3 py-2 text-[11px] font-semibold text-slate-500 uppercase tracking-wide">Organizations</div>
                  {orgs.map((o) => (
                    <button
                      key={o.id}
                      onClick={() => {
                        switchOrg(o.id);
                        toast.success(`Switched to ${o.name}`);
                        setShowOrgMenu(false);
                      }}
                      className={cn("w-full text-left px-3 py-2 text-sm flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800", currentOrg.id === o.id && "bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300")}
                    >
                      <span className="truncate">{o.name}</span>
                      {currentOrg.id === o.id && <span className="h-2 w-2 bg-sky-600 rounded-full" />}
                    </button>
                  ))}
                  {orgs.length <= 1 && <div className="px-3 py-2 text-xs text-slate-400">Single org · create more in Admin</div>}
                </div>
              )}
            </div>
          )}

          {/* auth area */}
          {isAuthenticated && user ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 border dark:border-slate-700 rounded-full pl-1 pr-2 py-1 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 transition"
                aria-label="User menu"
              >
                <div className="h-7 w-7 rounded-full bg-gradient-to-br from-sky-600 to-violet-600 text-white grid place-items-center text-xs font-bold">
                  {(user.name || user.email || "U").charAt(0).toUpperCase()}
                </div>
                <div className="hidden sm:block text-left">
                  <div className="text-xs font-semibold leading-none truncate max-w-[100px]">{user.name}</div>
                  <div className="text-[10px] text-slate-500 leading-none truncate max-w-[100px]">{user.email}</div>
                </div>
                <Badge variant={roleBadgeVariant(user.role)} className="hidden lg:inline-flex text-[10px] px-1.5 py-0">
                  <Shield className="h-3 w-3 mr-1" /> {roleLabel(user.role)}
                </Badge>
                <ChevronDown className={cn("h-3 w-3 text-slate-400 hidden sm:block transition", showUserMenu && "rotate-180")} />
              </button>
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-64 rounded-xl border dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl p-2 z-50">
                  <div className="px-3 py-2 border-b dark:border-slate-700 mb-2">
                    <div className="text-sm font-semibold">{user.name}</div>
                    <div className="text-xs text-slate-500 truncate">{user.email}</div>
                    <div className="mt-1 flex gap-1">
                      <Badge variant={roleBadgeVariant(user.role)} className="text-[10px]">
                        {roleLabel(user.role)}
                      </Badge>
                      <Badge variant="outline" className="text-[10px]">
                        {user.plantId || "—"}
                      </Badge>
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="px-2 py-1 text-[11px] text-slate-500 flex items-center gap-1">
                      <Building2 className="h-3 w-3" /> {user.orgName || currentOrg?.name || user.orgId}
                    </div>
                    {(user.role === "ORG_ADMIN" || user.role === "OWNER" || user.role === "ADMIN") && (
                      <Link href="/admin/users" onClick={() => setShowUserMenu(false)} className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 text-sm">
                        <Users className="h-4 w-4" /> User management
                      </Link>
                    )}
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-950 text-sm text-red-600 dark:text-red-400"
                    >
                      <LogOut className="h-4 w-4" /> Sign out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-1">
              <Link href="/login" className="hidden sm:inline-flex">
                <Button variant="ghost" size="sm" className="gap-1.5">
                  <LogIn className="h-4 w-4" /> Login
                </Button>
              </Link>
              <Link href="/signup">
                <Button variant="primary" size="sm" className="hidden sm:inline-flex">
                  Sign up
                </Button>
              </Link>
              <Link href="/login" className="sm:hidden">
                <Button variant="primary" size="sm">
                  <LogIn className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          )}

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
              <button
                key={l}
                onClick={() => setLang(l)}
                className={cn("px-3 py-1.5 rounded-full text-xs font-bold border", lang === l ? "bg-sky-600 text-white border-sky-600" : "bg-white dark:bg-slate-800 dark:border-slate-700")}
              >
                {LANG_NATIVE[l]} <span className="font-normal opacity-70 hidden sm:inline">{l}</span>
              </button>
            ))}
          </div>
          {isAuthenticated && user && (
            <div className="flex items-center gap-3 p-3 rounded-xl border dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
              <div className="h-10 w-10 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold">{(user.name || "U").charAt(0).toUpperCase()}</div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{user.name}</div>
                <div className="text-xs text-slate-500 truncate">{user.email}</div>
                <Badge variant={roleBadgeVariant(user.role)} className="mt-1 text-[10px]">
                  {roleLabel(user.role)}
                </Badge>
              </div>
              <Button variant="ghost" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4" />
              </Button>
            </div>
          )}
          <div className="grid grid-cols-3 gap-2">
            {displayNav.map((n) => {
              const active = pathname === n.href;
              return (
                <Link
                  key={n.href}
                  href={n.href}
                  onClick={() => setMobileOpen(false)}
                  className={cn("rounded-xl border p-3 text-center flex flex-col items-center gap-1", active ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-slate-50 dark:bg-slate-800")}
                >
                  <n.icon className="h-5 w-5" />
                  <span className="text-xs font-medium">{n.label}</span>
                  <span className="text-[10px] opacity-60">{n.desc}</span>
                </Link>
              );
            })}
            {isAuthenticated && user && (user.role === "ORG_ADMIN" || user.role === "OWNER") && (
              <Link href="/admin/users" onClick={() => setMobileOpen(false)} className={cn("rounded-xl border p-3 text-center flex flex-col items-center gap-1", pathname.startsWith("/admin") ? "bg-slate-900 text-white dark:bg-white dark:text-slate-900" : "bg-slate-50 dark:bg-slate-800")}>
                <Users className="h-5 w-5" />
                <span className="text-xs font-medium">Admin</span>
                <span className="text-[10px] opacity-60">Users</span>
              </Link>
            )}
          </div>
          {!isAuthenticated && (
            <div className="flex gap-2">
              <Link href="/login" className="flex-1" onClick={() => setMobileOpen(false)}>
                <Button variant="outline" className="w-full">
                  Login
                </Button>
              </Link>
              <Link href="/signup" className="flex-1" onClick={() => setMobileOpen(false)}>
                <Button variant="primary" className="w-full">
                  Sign up
                </Button>
              </Link>
            </div>
          )}
        </div>
      )}
      <div className="md:hidden border-t bg-white dark:bg-slate-900 flex">
        {displayNav.map((n) => {
          const active = pathname === n.href;
          return (
            <Link
              key={n.href}
              href={n.href}
              className={cn("flex-1 py-2.5 text-center text-xs font-medium flex flex-col items-center gap-1 border-r last:border-0 dark:border-slate-800", active ? "text-sky-600 bg-sky-50 dark:bg-sky-950 dark:text-sky-300" : "text-slate-500 dark:text-slate-400")}
            >
              <n.icon className="h-4 w-4" /> {n.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
}
