"use client";
import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/lib/toast";
import { LogIn, Eye, EyeOff, Building2, Shield, Sparkles } from "lucide-react";

function LoginInner() {
  const { login } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "";
  const error = params.get("error");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please fill in all fields");
      return;
    }
    setLoading(true);
    try {
      const u = await login(email, password);
      toast.success(`Welcome, ${u.name}`, { description: u.role });
      let dest = next || "/";
      if (!next) {
        const r = (u.role || "").toUpperCase();
        if (r === "OPERATOR") dest = "/operator";
        else if (r.startsWith("MAINTENANCE")) dest = "/maintenance";
        else if (r === "PLANT_HEAD") dest = "/plant-head";
        else if (r === "ORG_ADMIN" || r === "OWNER") dest = "/admin/users";
      }
      router.push(dest);
    } catch (err: any) {
      toast.error(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (role: string) => {
    const map: Record<string, string> = {
      operator: "operator@tantu.demo",
      maintenance: "maintenance@tantu.demo",
      plant: "planthead@tantu.demo",
      admin: "admin@tantu.demo",
    };
    setEmail(map[role] || map.operator);
    setPassword("Demo1234!");
  };

  return (
    <div className="px-4 sm:px-6 py-8 flex justify-center">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center space-y-2">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold shadow">T</div>
          <h1 className="text-2xl font-bold tracking-tight">Sign in to TANTU</h1>
          <p className="text-sm text-slate-500">Mixed-fleet intelligence · Raw frames never leave plant</p>
          {error === "forbidden" && <Badge variant="red" className="mt-2">Access denied — your role cannot access that page</Badge>}
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <LogIn className="h-4 w-4 text-sky-600" /> Login
            </CardTitle>
            <CardDescription className="text-xs">JWT access in memory + localStorage, refresh via HttpOnly cookie fallback</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handle} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Email</label>
                <Input type="email" placeholder="operator@tantu.demo" value={email} onChange={(e) => setEmail(e.target.value)} required aria-label="Email" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 dark:text-slate-300">Password</label>
                <div className="relative">
                  <Input type={show ? "text" : "password"} placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required className="pr-10" aria-label="Password" />
                  <button type="button" aria-label="Toggle password visibility" onClick={() => setShow(!show)} className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800">
                    {show ? <EyeOff className="h-4 w-4 text-slate-500" /> : <Eye className="h-4 w-4 text-slate-500" />}
                  </button>
                </div>
              </div>

              <Button type="submit" variant="primary" className="w-full" disabled={loading}>
                {loading ? "Signing in…" : "Sign in"}
              </Button>

              <div className="flex flex-wrap gap-2 text-xs justify-center">
                <button type="button" onClick={() => fillDemo("operator")} className="px-2.5 py-1 rounded-full border hover:bg-slate-50 dark:hover:bg-slate-800 text-xs">
                  operator
                </button>
                <button type="button" onClick={() => fillDemo("maintenance")} className="px-2.5 py-1 rounded-full border hover:bg-slate-50 dark:hover:bg-slate-800 text-xs">
                  maintenance
                </button>
                <button type="button" onClick={() => fillDemo("plant")} className="px-2.5 py-1 rounded-full border hover:bg-slate-50 dark:hover:bg-slate-800 text-xs">
                  plant-head
                </button>
                <button type="button" onClick={() => fillDemo("admin")} className="px-2.5 py-1 rounded-full border hover:bg-slate-50 dark:hover:bg-slate-800 text-xs">
                  admin/owner
                </button>
              </div>

              <div className="text-center text-xs text-slate-500">
                No account?{" "}
                <Link href="/signup" className="text-sky-600 hover:underline font-medium">
                  Create org
                </Link>{" "}
                ·{" "}
                <Link href="/invite" className="text-sky-600 hover:underline font-medium">
                  Have invite?
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card className="bg-slate-50 dark:bg-slate-900/50">
          <CardContent className="pt-4 text-xs space-y-2">
            <div className="font-semibold flex items-center gap-1">
              <Shield className="h-3.5 w-3.5 text-slate-500" /> Demo accounts (offline fallback)
            </div>
            <div className="grid grid-cols-1 gap-1 text-slate-600 dark:text-slate-400">
              <div className="flex justify-between">
                <span className="font-mono">operator@tantu.demo</span> <Badge variant="amber" className="text-[10px]">OPERATOR → /operator</Badge>
              </div>
              <div className="flex justify-between">
                <span className="font-mono">maintenance@tantu.demo</span> <Badge variant="sky" className="text-[10px]">MAINTENANCE_* → /maintenance</Badge>
              </div>
              <div className="flex justify-between">
                <span className="font-mono">planthead@tantu.demo</span> <Badge variant="emerald" className="text-[10px]">PLANT_HEAD → /plant-head</Badge>
              </div>
              <div className="flex justify-between">
                <span className="font-mono">admin@tantu.demo</span> <Badge variant="violet" className="text-[10px]">ORG_ADMIN/OWNER → /admin/users</Badge>
              </div>
              <div className="text-[11px] text-slate-500 pt-1">Password: Demo1234! (mock fallback accepts any ≥4 chars)</div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-2">
          <Building2 className="h-3 w-3" /> DPDP 2023 · SOC2 · Vault · TLS 1.3 · Frames never leave plant <Sparkles className="h-3 w-3" />
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="px-4 sm:px-6 py-8 flex justify-center"><div className="w-full max-w-md p-6 border rounded-xl">Loading…</div></div>}>
      <LoginInner />
    </Suspense>
  );
}
