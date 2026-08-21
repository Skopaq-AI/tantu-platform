"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/lib/toast";
import { Building2, User, Mail, Lock, Eye, EyeOff } from "lucide-react";

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const handle = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName || !email || !password) {
      toast.error("Please fill in all required fields");
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
      const u = await signup({ orgName, email, password, name: name || email.split("@")[0] });
      toast.success(`Org "${orgName}" created`, { description: `Welcome, ${u.name} (${u.role})` });
      router.push("/admin/users");
    } catch (err: any) {
      toast.error(err.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="px-4 sm:px-6 py-8 flex justify-center">
      <div className="w-full max-w-md space-y-4">
        <div className="text-center space-y-2">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold shadow">T</div>
          <h1 className="text-2xl font-bold tracking-tight">Create your organization</h1>
          <p className="text-sm text-slate-500">You’ll be the OWNER — invite your team after. 90-day pilot · Rs 18K/cluster/mo</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Building2 className="h-4 w-4 text-sky-600" /> Org creation
            </CardTitle>
            <CardDescription className="text-xs">Creates org + OWNER user · JWT issued · plant assigned to plant-demo-01</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handle} className="space-y-3">
              <div>
                <label className="text-xs font-semibold">Organization name *</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input placeholder="Acme Manufacturing Pvt Ltd" value={orgName} onChange={(e) => setOrgName(e.target.value)} required className="pl-9" aria-label="Organization name" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">Your name</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input placeholder="Arjun Shah" value={name} onChange={(e) => setName(e.target.value)} className="pl-9" aria-label="Your name" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">Work email *</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                  <Input type="email" placeholder="you@acme.co.in" value={email} onChange={(e) => setEmail(e.target.value)} required className="pl-9" aria-label="Email" />
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">Password *</label>
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

              <div className="text-[11px] text-slate-500 bg-slate-50 dark:bg-slate-800 rounded-lg p-2.5 border dark:border-slate-700">
                By creating an org you agree to DPDP 2023 terms · data_residency=IN · 90-day hot retention · OWNER can invite users and manage plants.
              </div>

              <Button type="submit" variant="primary" className="w-full" disabled={loading}>
                {loading ? "Creating…" : "Create org & continue"}
              </Button>

              <div className="text-center text-xs text-slate-500">
                Already have an account?{" "}
                <Link href="/login" className="text-sky-600 hover:underline font-medium">
                  Sign in
                </Link>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
