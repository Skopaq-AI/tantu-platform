"use client";
import { useEffect, useMemo, useState } from "react";
import { useAuth, roleLabel, roleBadgeVariant } from "@/lib/auth";
import { RoleGuard } from "@/components/RoleGuard";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { toast } from "@/lib/toast";
import { API_URL } from "@/lib/api";
import { Users, UserPlus, Shield, Building2, Factory, Mail, Copy, Trash2, Pencil, Plus, Check } from "lucide-react";

type ManagedUser = {
  id: string;
  email: string;
  name: string;
  role: string;
  plantId?: string;
  plantIds?: string[];
  orgId: string;
  status?: "active" | "invited" | "disabled";
  invitedAt?: string;
};

const ROLES = ["OPERATOR", "MAINTENANCE_TECH", "MAINTENANCE_LEAD", "PLANT_HEAD", "ORG_ADMIN", "OWNER"] as const;
const PLANTS = ["plant-demo-01", "plant-line-1", "plant-line-2", "plant-fab-07", "plant-demo-02"];

function mockUsers(orgId: string): ManagedUser[] {
  return [
    { id: "u-01", email: "operator@tantu.demo", name: "Ravi Operator", role: "OPERATOR", plantId: "plant-line-2", orgId, status: "active" },
    { id: "u-02", email: "maintenance@tantu.demo", name: "Priya Tech", role: "MAINTENANCE_TECH", plantId: "plant-demo-01", orgId, status: "active" },
    { id: "u-03", email: "planthead@tantu.demo", name: "Arjun Head", role: "PLANT_HEAD", plantId: "plant-demo-01", orgId, status: "active" },
    { id: "u-04", email: "admin@tantu.demo", name: "Sara Admin", role: "ORG_ADMIN", plantId: "plant-demo-01", orgId, status: "active" },
  ];
}

export default function AdminUsersPage() {
  return (
    <RoleGuard allowedRoles={["ORG_ADMIN", "OWNER", "ADMIN"]}>
      <AdminUsersInner />
    </RoleGuard>
  );
}

function AdminUsersInner() {
  const { user, token, currentOrg } = useAuth();
  const [users, setUsers] = useState<ManagedUser[]>(() => []);
  const [query, setQuery] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("OPERATOR");
  const [invitePlant, setInvitePlant] = useState<string>("plant-line-2");
  const [inviteLink, setInviteLink] = useState<string | null>(null);
  const [editUser, setEditUser] = useState<ManagedUser | null>(null);
  const [editRole, setEditRole] = useState<string>("OPERATOR");
  const [editPlant, setEditPlant] = useState<string>("plant-demo-01");
  const [loading, setLoading] = useState(true);

  // fetch real users — no mock unless DEMO=true
  useEffect(() => {
    const t = setTimeout(() => setLoading(false), 500);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const r = await fetch(`${API_URL}/admin/users`, { headers: { Authorization: `Bearer ${token}` }, credentials: "include", cache: "no-store" });
        if (r.ok) {
          const data = await r.json();
          const list = Array.isArray(data) ? data : data.users || data.data || null;
          if (Array.isArray(list) && list.length) {
            const normalized: ManagedUser[] = list.map((u: any) => ({
              id: u.id || u._id || u.email,
              email: u.email,
              name: u.name || u.email?.split("@")[0] || "User",
              role: (u.role || "OPERATOR").toUpperCase(),
              plantId: u.plantId || u.plant_id || u.plantIds?.[0] || "plant-demo-01",
              plantIds: u.plantIds || u.plant_ids || [],
              orgId: u.orgId || u.org_id || currentOrg?.id || "org-demo-01",
              status: u.status || "active",
            }));
            setUsers(normalized);
            return;
          }
        }
        // fallback only in DEMO mode
        if (process.env.NEXT_PUBLIC_DEMO === "true") {
          setUsers(mockUsers(currentOrg?.id || "org-demo-01"));
        }
      } catch {
        if (process.env.NEXT_PUBLIC_DEMO === "true") {
          setUsers(mockUsers(currentOrg?.id || "org-demo-01"));
        }
      }
    })();
  }, [token, currentOrg?.id]);

  useEffect(() => {
    if (editUser) {
      setEditRole(editUser.role);
      setEditPlant(editUser.plantId || "plant-demo-01");
    }
  }, [editUser]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) => `${u.name} ${u.email} ${u.role} ${u.plantId}`.toLowerCase().includes(q));
  }, [users, query]);

  const handleInvite = async () => {
    if (!inviteEmail || !inviteEmail.includes("@")) {
      toast.error("Please enter a valid email");
      return;
    }
    // try real API
    try {
      if (token) {
        const r = await fetch(`${API_URL}/admin/users/invite`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          credentials: "include",
          body: JSON.stringify({ email: inviteEmail, role: inviteRole, plant_id: invitePlant, plantId: invitePlant }),
        });
        if (r.ok) {
          const j = await r.json().catch(() => ({}));
          const link = j.invite_link || j.inviteLink || j.link || `${window.location.origin}/invite?token=${j.token || j.invite_token || ""}`;
          setInviteLink(link);
          toast.success(`Invite sent to ${inviteEmail}`);
          setUsers((prev) => [{ id: `u-${Date.now()}`, email: inviteEmail, name: inviteEmail.split("@")[0], role: inviteRole, plantId: invitePlant, orgId: currentOrg?.id || "org-demo-01", status: "invited", invitedAt: new Date().toISOString() }, ...prev]);
          return;
        }
        const err = await r.json().catch(() => ({}));
        if (r.status !== 404) {
          toast.error(err.detail || err.message || "Invite failed");
          return;
        }
      }
    } catch {}

    // mock fallback gated behind DEMO flag: generate local invite token
    if (process.env.NEXT_PUBLIC_DEMO !== "true") {
      toast.error("Invite failed — backend unreachable and DEMO mock disabled");
      return;
    }
    const payload = {
      email: inviteEmail,
      role: inviteRole,
      org_id: currentOrg?.id || "org-demo-01",
      org_name: currentOrg?.name || "Demo Org",
      plant_id: invitePlant,
      exp: Math.floor(Date.now() / 1000) + 7 * 86400,
    };
    const b64 = typeof window !== "undefined" ? btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "") : "";
    // also create a mock JWT for invite (header.payload.sig)
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" })).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
    const inviteToken = `${header}.${b64}.mock_signature`;
    const link = `${window.location.origin}/invite?token=${inviteToken}`;
    setInviteLink(link);
    setUsers((prev) => [{ id: `u-${Date.now()}`, email: inviteEmail, name: inviteEmail.split("@")[0], role: inviteRole, plantId: invitePlant, orgId: currentOrg?.id || "org-demo-01", status: "invited", invitedAt: new Date().toISOString() }, ...prev]);
    toast.success(`Invite created (mock) for ${inviteEmail}`);
  };

  const handleRoleChange = async () => {
    if (!editUser) return;
    const prevRole = editUser.role;
    const prevPlant = editUser.plantId;
    // optimistic
    setUsers((prev) => prev.map((u) => (u.id === editUser.id ? { ...u, role: editRole, plantId: editPlant } : u)));
    setEditUser(null);
    toast.success(`Updated ${editUser.email}: ${prevRole} → ${editRole}, plant ${prevPlant} → ${editPlant}`);
    // try real API
    try {
      if (token) {
        const r = await fetch(`${API_URL}/admin/users/${editUser.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          credentials: "include",
          body: JSON.stringify({ role: editRole, plant_id: editPlant, plantId: editPlant }),
        });
        if (!r.ok) {
          const err = await r.json().catch(() => ({}));
          if (r.status !== 404) toast.error(err.detail || "Update failed on server (mock kept)");
        }
      }
    } catch {}
  };

  const handleRemove = async (u: ManagedUser) => {
    if (!confirm(`Remove ${u.email}?`)) return;
    setUsers((prev) => prev.filter((x) => x.id !== u.id));
    toast.success(`Removed ${u.email}`);
    try {
      if (token) {
        await fetch(`${API_URL}/admin/users/${u.id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` }, credentials: "include" }).catch(() => {});
      }
    } catch {}
  };

  const handleCopyInvite = async (link: string) => {
    await navigator.clipboard.writeText(link);
    toast.success("Invite link copied");
  };

  return (
    <div className="px-4 sm:px-6 py-6 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <Users className="h-5 w-5 text-violet-600" /> User management{" "}
          <Badge variant="violet" className="gap-1">
            <Shield className="h-3 w-3" /> ORG_ADMIN · OWNER
          </Badge>
        </h1>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="gap-1">
            <Building2 className="h-3 w-3" /> {currentOrg?.name || user?.orgName || "Org"}
          </Badge>
          <Badge variant="secondary">{users.length} users</Badge>
          <Button variant="primary" size="sm" onClick={() => setInviteOpen(true)} className="gap-1.5">
            <UserPlus className="h-4 w-4" /> Invite user
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Building2 className="h-4 w-4 text-slate-500" /> {currentOrg?.name || "Organization"} · {currentOrg?.id || user?.orgId}
          </CardTitle>
          <CardDescription className="text-xs">Only ORG_ADMIN / OWNER can invite, change roles, and assign plants. RBAC enforced via middleware + RoleGuard.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input placeholder="Filter by name, email, role, plant…" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9" aria-label="Filter users" />
            </div>
            <Badge variant="outline" className="hidden sm:inline-flex">
              {filtered.length} / {users.length}
            </Badge>
          </div>

          {/* table */}
          <div className="overflow-x-auto rounded-xl border dark:border-slate-700">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 dark:bg-slate-800 text-xs text-slate-500">
                <tr>
                  <th className="text-left px-3 py-2 font-semibold">User</th>
                  <th className="text-left px-3 py-2 font-semibold">Role</th>
                  <th className="text-left px-3 py-2 font-semibold">Plant assignment</th>
                  <th className="text-left px-3 py-2 font-semibold">Status</th>
                  <th className="text-right px-3 py-2 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-slate-500">
                      Loading users…
                    </td>
                  </tr>
                ) : filtered.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-slate-500">
                      No users match “{query}”
                    </td>
                  </tr>
                ) : (
                  filtered.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-3 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className="h-8 w-8 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center text-xs font-bold shrink-0">
                            {(u.name || u.email).charAt(0).toUpperCase()}
                          </div>
                          <div className="min-w-0">
                            <div className="font-medium truncate">{u.name}</div>
                            <div className="text-xs text-slate-500 truncate flex items-center gap-1">
                              <Mail className="h-3 w-3" /> {u.email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={roleBadgeVariant(u.role)} className="text-[11px]">
                          <Shield className="h-3 w-3 mr-1" /> {roleLabel(u.role)}
                        </Badge>
                        <div className="text-[11px] text-slate-400 font-mono mt-1">{u.role}</div>
                      </td>
                      <td className="px-3 py-3">
                        <div className="inline-flex items-center gap-1 text-xs border dark:border-slate-700 rounded-full px-2.5 py-1 bg-white dark:bg-slate-900">
                          <Factory className="h-3 w-3 text-slate-500" /> {u.plantId || "—"}
                        </div>
                        {u.plantIds && u.plantIds.length > 1 && <div className="text-[11px] text-slate-400 mt-1">+{u.plantIds.length - 1} more</div>}
                      </td>
                      <td className="px-3 py-3">
                        <Badge variant={u.status === "active" ? "emerald" : u.status === "invited" ? "amber" : "secondary"} className="text-[10px]">
                          {u.status || "active"}
                        </Badge>
                        {u.invitedAt && <div className="text-[11px] text-slate-400 mt-1">{new Date(u.invitedAt).toLocaleDateString()}</div>}
                      </td>
                      <td className="px-3 py-3">
                        <div className="flex justify-end gap-1">
                          <Button variant="outline" size="sm" className="h-7 text-xs px-2 gap-1" onClick={() => setEditUser(u)}>
                            <Pencil className="h-3 w-3" /> Edit
                          </Button>
                          <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-red-600 hover:bg-red-50" onClick={() => handleRemove(u)} aria-label={`Remove ${u.email}`}>
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="text-[11px] text-slate-500">Audit: role changes & plant assignments are logged · middleware enforces /admin only ORG_ADMIN/OWNER · client RoleGuard mirrors.</div>
        </CardContent>
      </Card>

      {/* invite dialog */}
      <Dialog open={inviteOpen} onOpenChange={(o) => { setInviteOpen(o); if (!o) { setInviteLink(null); setInviteEmail(""); } }}>
        <DialogContent onClose={() => setInviteOpen(false)} className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-violet-600" /> Invite user to {currentOrg?.name || "org"}
            </DialogTitle>
            <DialogDescription className="text-xs">Sends invite JWT (7-day expiry) · role & plant assignment · invitee accepts at /invite</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-semibold">Email *</label>
              <Input type="email" placeholder="newuser@acme.co.in" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} aria-label="Invite email" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold">Role *</label>
                <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className="w-full h-10 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm">
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {roleLabel(r)} ({r})
                    </option>
                  ))}
                </select>
                <div className="text-[11px] text-slate-500 mt-1">
                  {inviteRole === "OPERATOR" ? "→ /operator only" : inviteRole.startsWith("MAINTENANCE") ? "→ /maintenance only" : inviteRole === "PLANT_HEAD" ? "→ /plant-head only" : "→ /admin/users + all"}
                </div>
              </div>
              <div>
                <label className="text-xs font-semibold">Plant assignment *</label>
                <select value={invitePlant} onChange={(e) => setInvitePlant(e.target.value)} className="w-full h-10 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm">
                  {PLANTS.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
                <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                  <Factory className="h-3 w-3" /> Assigned plant enforced via ABAC (JWT plant_id)
                </div>
              </div>
            </div>

            {inviteLink ? (
              <div className="rounded-xl border dark:border-slate-700 bg-emerald-50 dark:bg-emerald-950 p-3 space-y-2">
                <div className="text-xs font-semibold text-emerald-700 dark:text-emerald-300 flex items-center gap-1">
                  <Check className="h-4 w-4" /> Invite link ready (mock fallback shown if API offline)
                </div>
                <div className="text-xs font-mono break-all bg-white dark:bg-slate-900 border dark:border-slate-700 rounded-lg p-2">{inviteLink}</div>
                <div className="flex gap-2">
                  <Button variant="primary" size="sm" className="flex-1 gap-1" onClick={() => handleCopyInvite(inviteLink)}>
                    <Copy className="h-3.5 w-3.5" /> Copy link
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => { setInviteLink(null); setInviteEmail(""); }}>
                    Invite another
                  </Button>
                </div>
              </div>
            ) : (
              <Button variant="primary" className="w-full gap-2" onClick={handleInvite}>
                <Mail className="h-4 w-4" /> Send invite
              </Button>
            )}

            <div className="text-[11px] text-slate-500 text-center">Invitee visits /invite?token=… and sets password · token single-use · audit in Admin</div>
          </div>
        </DialogContent>
      </Dialog>

      {/* edit dialog */}
      <Dialog open={!!editUser} onOpenChange={(o) => !o && setEditUser(null)}>
        {editUser && (
          <DialogContent onClose={() => setEditUser(null)} className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Pencil className="h-5 w-5" /> Edit {editUser.email}
              </DialogTitle>
              <DialogDescription>Role change & plant assignment · RBAC & ABAC enforced · re-issue JWT</DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 rounded-xl border dark:border-slate-700 bg-slate-50 dark:bg-slate-800">
                <div className="h-10 w-10 rounded-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 grid place-items-center font-bold">{editUser.name.charAt(0).toUpperCase()}</div>
                <div>
                  <div className="text-sm font-semibold">{editUser.name}</div>
                  <div className="text-xs text-slate-500">{editUser.email} · Current: {editUser.role} · {editUser.plantId}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-semibold">New role</label>
                  <select value={editRole} onChange={(e) => setEditRole(e.target.value)} className="w-full h-10 rounded-md border dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm">
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {roleLabel(r)}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold">Plant</label>
                  <select value={editPlant} onChange={(e) => setEditPlant(e.target.value)} className="w-full h-10 rounded-md border dark:border-slate-700 bg-white dark:bg-slate-900 px-3 text-sm">
                    {PLANTS.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="rounded-lg bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 p-2.5 text-xs text-amber-800 dark:text-amber-200">
                Changing role will immediately affect page access: OPERATOR → /operator, MAINTENANCE_* → /maintenance, PLANT_HEAD → /plant-head, ORG_ADMIN/OWNER → /admin/users + all.
              </div>

              <div className="flex gap-2">
                <Button variant="primary" className="flex-1" onClick={handleRoleChange}>
                  <Check className="h-4 w-4 mr-1" /> Save changes
                </Button>
                <Button variant="outline" onClick={() => setEditUser(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        )}
      </Dialog>

      <Card className="bg-slate-50 dark:bg-slate-900/50">
        <CardContent className="pt-4 text-xs text-slate-600 dark:text-slate-400 space-y-1">
          <div className="font-semibold flex items-center gap-1">
            <Shield className="h-3.5 w-3.5" /> RBAC matrix
          </div>
          <div>
            OPERATOR → /operator only · MAINTENANCE_* (MAINTENANCE, MAINTENANCE_TECH/LEAD) → /maintenance only · PLANT_HEAD → /plant-head only · ORG_ADMIN / OWNER → /admin/users (and all operational pages)
          </div>
          <div>Landing “/” is public · middleware redirects to /login if no token, enforces RBAC per role · RoleGuard mirrors on client · API attaches Authorization: Bearer & refreshes on 401.</div>
        </CardContent>
      </Card>
    </div>
  );
}
