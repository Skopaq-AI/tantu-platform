"use client";
import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/lib/toast";
import { Mail, Lock, User, Ticket, Eye, EyeOff, Check, Copy } from "lucide-react";

function InviteInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { acceptInvite } = useAuth();
  const tokenFromUrl = params.get("token") || params.get("invite") || "";
  const [token, setToken] = useState(tokenFromUrl);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [decoded, setDecoded] = useState<any>(null);

  useEffect(() => {
    if (tokenFromUrl) setToken(tokenFromUrl);
  }, [tokenFromUrl]);

  useEffect(() => {
    if (!token) {
      setDecoded(null);
      return;
    }
    // try decode for preview (payload may contain email/role/org)
    try {
      const parts = token.split(".");
      if (parts.length >= 2) {
        const p = parts[1].replace(/-/g, "+").replace(/_/g, "/");
        const json = atob(p.padEnd(p.length + ((4 - (p.length % 4)) % 4), "="));
        const payload = JSON.parse(json);
        setDecoded(payload);
      } else {
        // try plain base64 json
        try {
          const json = atob(token.replace(/-/g, "+").replace(/_/g, "/"));
          const j = JSON.parse(json);
          setDecoded(j);
        } catch {
          setDecoded(null);
        }
      }
    } catch {
      setDecoded(null);
    }
  }, [token]);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) {
      toast.error("Invite token is required");
      return;
    }
    if (password !== confirm) {
      toast.error("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    setLoading(true);
    try {
      const u = await acceptInvite(token, password, name);
      toast.success(`Invite accepted — welcome ${u.name}`, { description: `${u.role} · ${u.orgName}` });
      // role-aware redirect
      const r = (u.role || "").toUpperCase();
      const dest = r === "OPERATOR" ? "/operator" : r.startsWith("MAINTENANCE") ? "/maintenance" : r === "PLANT_HEAD" ? "/plant-head" : "/login";
      router.push(dest);
    } catch (err: any) {
      toast.error(err.message || "Failed to accept invite");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 sm:px-6 py-8 flex justify-center">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center space-y-2">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold shadow">T</div>
          <h1 className="text-2xl font-bold tracking-tight">Accept invite</h1>
          <p className="text-sm text-slate-500">You were invited to join an org on TANTU · set your password to continue</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Ticket className="h-4 w-4 text-sky-600" /> Invite token
            </CardTitle>
            <CardDescription className="text-xs">Paste the invite token from your email · JWT verified · role & plant assigned</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-xs font-semibold">Invite token *</label>
              <div className="flex gap-2">
                <Input value={token} onChange={(e) => setToken(e.target.value)} placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." className="font-mono text-xs" aria-label="Invite token" />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={async () => {
                    const t = await navigator.clipboard.readText().catch(() => "");
                    if (t) setToken(t.trim());
                  }}
                  title="Paste from clipboard"
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
              {decoded && (
                <div className="mt-2 rounded-lg bg-slate-50 dark:bg-slate-800 border dark:border-slate-700 p-2.5 text-xs space-y-1">
                  <div className="flex gap-2 flex-wrap">
                    {decoded.email && (
                      <span className="inline-flex items-center gap-1">
                        <Mail className="h-3 w-3" /> {decoded.email}
                      </span>
                    )}
                    {decoded.role && <Badge variant="outline" className="text-[10px]">{decoded.role}</Badge>}
                    {(decoded.org_name || decoded.orgName) && <Badge variant="secondary" className="text-[10px]">{decoded.org_name || decoded.orgName}</Badge>}
                    {(decoded.plant_id || decoded.plantId) && <Badge variant="outline" className="text-[10px]">{decoded.plant_id || decoded.plantId}</Badge>}
                  </div>
                  <div className="text-[11px] text-slate-500">Decoded from token · verify before accepting</div>
                </div>
              )}
            </div>

            <form onSubmit={handle} className="space-y-3">
              <div>
                <label className="text-xs font-semibold">Your name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input placeholder="Arjun Shah" value={name} onChange={(e) => setName(e.target.value)} className="pl-9" aria-label="Your name" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">New password *</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input type={show ? "text" : "password"} placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required className="pl-9 pr-10" aria-label="Password" />
                  <button type="button" onClick={() => setShow(!show)} className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full hover:bg-slate-100">
                    {show ? <EyeOff className="h-4 w-4 text-slate-500" /> : <Eye className="h-4 w-4 text-slate-500" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">Confirm password *</label>
                <Input type={show ? "text" : "password"} placeholder="••••••••" value={confirm} onChange={(e) => setConfirm(e.target.value)} required aria-label="Confirm password" />
              </div>

              <Button type="submit" variant="primary" className="w-full gap-2" disabled={loading}>
                <Check className="h-4 w-4" /> {loading ? "Accepting…" : "Accept invite & sign in"}
              </Button>
            </form>

            <div className="text-center text-xs text-slate-500">
              No invite?{" "}
              <Link href="/signup" className="text-sky-600 hover:underline font-medium">
                Create org
              </Link>{" "}
              ·{" "}
              <Link href="/login" className="text-sky-600 hover:underline font-medium">
                Sign in
              </Link>
            </div>
          </CardContent>
        </Card>

        <div className="text-[11px] text-slate-400 text-center">Invite links expire per org policy (default 7 days) · token is single-use · audit trail in Org Admin</div>
      </div>
    </div>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={<div className="px-4 sm:px-6 py-8 flex justify-center"><div className="w-full max-w-md p-6 border rounded-xl">Loading invite…</div></div>}>
      <InviteInner />
    </Suspense>
  );
}
