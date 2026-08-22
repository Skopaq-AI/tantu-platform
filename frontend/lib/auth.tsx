"use client";
import React, { createContext, useContext, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_URL, isDemoEnabled } from "@/lib/api";

export type Role =
  | "OPERATOR"
  | "MAINTENANCE"
  | "MAINTENANCE_TECH"
  | "MAINTENANCE_LEAD"
  | "MAINTENANCE_MANAGER"
  | "PLANT_HEAD"
  | "ORG_ADMIN"
  | "OWNER"
  | "ADMIN"
  | string;

export type User = {
  id: string;
  email: string;
  name: string;
  role: Role;
  orgId: string;
  orgName?: string;
  plantId?: string;
  plantIds?: string[];
  avatar?: string;
};

export type JWTPayload = {
  sub: string;
  email?: string;
  name?: string;
  role: Role;
  org_id?: string;
  orgId?: string;
  org_name?: string;
  orgName?: string;
  plant_id?: string;
  plantId?: string;
  plant_ids?: string[];
  exp?: number;
  iat?: number;
};

export type Org = { id: string; name: string };

const ACCESS_KEY = "tantu_access";
const ORGS_KEY = "tantu_orgs";
const CURRENT_ORG_KEY = "tantu_current_org";

// ---------- jwt decode ----------
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const payload = parts[1];
    const padded = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = typeof window !== "undefined" ? atob(padded) : Buffer.from(padded, "base64").toString("utf-8");
    return JSON.parse(json) as JWTPayload;
  } catch {
    return null;
  }
}

function payloadToUser(payload: JWTPayload, fallbackEmail?: string): User {
  const orgId = (payload.orgId || payload.org_id || "org-demo-01") as string;
  const plantId = (payload.plantId || payload.plant_id || "plant-demo-01") as string;
  return {
    id: payload.sub || payload.email || fallbackEmail || "user-01",
    email: payload.email || fallbackEmail || `${payload.sub || "user"}@tantu.local`,
    name: payload.name || payload.email?.split("@")[0] || payload.sub || "User",
    role: (payload.role || "OPERATOR") as Role,
    orgId,
    orgName: payload.orgName || payload.org_name || "Tantu Demo Org",
    plantId,
    plantIds: payload.plant_ids || (plantId ? [plantId] : []),
  };
}

// helpers for RBAC
export function isMaintenanceRole(role: string): boolean {
  const r = (role || "").toUpperCase();
  return r === "MAINTENANCE" || r.startsWith("MAINTENANCE_");
}
export function normalizeRole(role: string): string {
  return (role || "").toUpperCase();
}
export function canAccessPath(pathname: string, role: string): boolean {
  const r = normalizeRole(role);
  if (pathname.startsWith("/admin")) {
    return r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/operator")) {
    return r === "OPERATOR" || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/maintenance")) {
    return isMaintenanceRole(r) || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/plant-head") || pathname.startsWith("/plant_head")) {
    return r === "PLANT_HEAD" || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  return true;
}

export function roleBadgeVariant(role: string): "default" | "secondary" | "sky" | "amber" | "emerald" | "violet" | "outline" | "red" {
  const r = normalizeRole(role);
  if (r === "OWNER" || r === "ORG_ADMIN" || r === "ADMIN") return "violet";
  if (r === "PLANT_HEAD") return "emerald";
  if (isMaintenanceRole(r)) return "sky";
  if (r === "OPERATOR") return "amber";
  return "secondary";
}
export function roleLabel(role: string): string {
  const r = (role || "").toString();
  if (!r) return "—";
  // normalize display: MAINTENANCE_TECH -> Maintenance Tech
  return r
    .toLowerCase()
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// generate mock JWT for offline/demo fallback
function makeMockJWT(payload: JWTPayload): string {
  const header = { alg: "HS256", typ: "JWT" };
  const encode = (obj: any) => {
    const json = JSON.stringify(obj);
    const b64 = typeof window !== "undefined" ? btoa(json) : Buffer.from(json).toString("base64");
    return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  };
  const exp = Math.floor(Date.now() / 1000) + 3600;
  const fullPayload = { ...payload, exp: payload.exp || exp, iat: Math.floor(Date.now() / 1000) };
  const signature = "mock_signature";
  return `${encode(header)}.${encode(fullPayload)}.${signature}`;
}

function detectRoleFromEmail(email: string): Role {
  const e = email.toLowerCase();
  if (e.includes("owner")) return "OWNER";
  if (e.includes("admin")) return "ORG_ADMIN";
  if (e.includes("plant")) return "PLANT_HEAD";
  if (e.includes("maintenance") || e.includes("tech") || e.includes("maint")) return "MAINTENANCE_TECH";
  if (e.includes("operator")) return "OPERATOR";
  // default: operator for demo
  return "OPERATOR";
}

// cookie helper for middleware sync
function setAccessCookie(token: string | null) {
  if (typeof document === "undefined") return;
  if (!token) {
    document.cookie = `tantu_access=; path=/; max-age=0; SameSite=Lax`;
    document.cookie = `access_token=; path=/; max-age=0; SameSite=Lax`;
    return;
  }
  // 1h
  document.cookie = `tantu_access=${token}; path=/; max-age=3600; SameSite=Lax`;
  document.cookie = `access_token=${token}; path=/; max-age=3600; SameSite=Lax`;
}

type AuthContextValue = {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (data: { orgName: string; email: string; password: string; name?: string }) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<string | null>;
  me: () => Promise<User | null>;
  acceptInvite: (token: string, password: string, name?: string) => Promise<User>;
  orgs: Org[];
  currentOrg: Org | null;
  switchOrg: (orgId: string) => void;
  setUser: (u: User | null) => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [orgs, setOrgs] = useState<Org[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Org | null>(null);
  const tokenRef = useRef<string | null>(null);

  const setToken = useCallback((t: string | null) => {
    tokenRef.current = t;
    setTokenState(t);
    if (typeof window !== "undefined") {
      if (t) {
        try {
          localStorage.setItem(ACCESS_KEY, t);
        } catch {}
        setAccessCookie(t);
      } else {
        try {
          localStorage.removeItem(ACCESS_KEY);
          localStorage.removeItem("access_token");
        } catch {}
        setAccessCookie(null);
      }
    }
  }, []);

  // init from storage
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      try {
        const stored = typeof window !== "undefined" ? localStorage.getItem(ACCESS_KEY) || localStorage.getItem("access_token") : null;
        const storedOrgs = typeof window !== "undefined" ? localStorage.getItem(ORGS_KEY) : null;
        const storedCurrent = typeof window !== "undefined" ? localStorage.getItem(CURRENT_ORG_KEY) : null;

        if (storedOrgs) {
          try {
            const parsed = JSON.parse(storedOrgs) as Org[];
            if (Array.isArray(parsed) && parsed.length) setOrgs(parsed);
          } catch {}
        }

        if (stored) {
          const payload = decodeJWT(stored);
          // check exp
          if (payload && payload.exp && payload.exp * 1000 < Date.now() - 5000) {
            // expired, try refresh via cookie fallback
            try {
              const refreshed = await tryRefresh();
              if (refreshed && mounted) {
                const p2 = decodeJWT(refreshed);
                if (p2) setUser(payloadToUser(p2));
                setToken(refreshed);
                // also sync orgs
                if (p2?.org_id || p2?.orgId) {
                  const oid = (p2.orgId || p2.org_id) as string;
                  const oname = (p2.orgName || p2.org_name || "Tantu Demo Org") as string;
                  const o: Org = { id: oid, name: oname };
                  setOrgs((prev) => (prev.find((x) => x.id === oid) ? prev : [...prev, o]));
                  setCurrentOrg(o);
                  try {
                    localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(o));
                  } catch {}
                }
              } else {
                // gate mock_signature fallback behind DEMO flag
                if (isDemoEnabled() && stored.includes("mock_signature")) {
                  if (payload) setUser(payloadToUser(payload));
                  setToken(stored);
                } else {
                  setToken(null);
                }
              }
            } catch {
              if (isDemoEnabled() && payload && stored.includes("mock_signature")) {
                setUser(payloadToUser(payload));
                setToken(stored);
              } else {
                setToken(null);
              }
            }
          } else if (payload) {
            setUser(payloadToUser(payload));
            setToken(stored);
            // orgs
            const oid = (payload.orgId || payload.org_id) as string;
            const oname = (payload.orgName || payload.org_name || "Tantu Demo Org") as string;
            if (oid) {
              const o: Org = { id: oid, name: oname };
              setOrgs((prev) => {
                const exists = prev.find((x) => x.id === oid);
                const next = exists ? prev : [...prev, o];
                try {
                  localStorage.setItem(ORGS_KEY, JSON.stringify(next));
                } catch {}
                return next;
              });
              // set current org
              let cur: Org | null = null;
              if (storedCurrent) {
                try {
                  cur = JSON.parse(storedCurrent);
                } catch {}
              }
              if (!cur) cur = o;
              setCurrentOrg(cur);
            }
          } else {
            // token not decodable, clear
            setToken(null);
          }
        }

        // try me() if authenticated to hydrate server profile
        if (mounted && tokenRef.current) {
          try {
            await fetchMe(tokenRef.current);
          } catch {}
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };
    init();

    // keep storage sync across tabs
    const onStorage = (e: StorageEvent) => {
      if (e.key === ACCESS_KEY || e.key === "access_token") {
        const v = e.newValue;
        if (v) {
          tokenRef.current = v;
          setTokenState(v);
          const p = decodeJWT(v);
          if (p) setUser(payloadToUser(p));
        } else {
          tokenRef.current = null;
          setTokenState(null);
          setUser(null);
        }
      }
    };
    window.addEventListener("storage", onStorage);
    return () => {
      mounted = false;
      window.removeEventListener("storage", onStorage);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // persist orgs
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (orgs.length) localStorage.setItem(ORGS_KEY, JSON.stringify(orgs));
    } catch {}
  }, [orgs]);
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      if (currentOrg) localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(currentOrg));
    } catch {}
  }, [currentOrg]);

  // auto refresh 60s before expiry
  useEffect(() => {
    if (!token) return;
    const payload = decodeJWT(token);
    if (!payload?.exp) return;
    const msUntilRefresh = payload.exp * 1000 - Date.now() - 60_000;
    if (msUntilRefresh <= 0) {
      // refresh soon
      const id = setTimeout(() => {
        refresh().catch(() => {});
      }, 2000);
      return () => clearTimeout(id);
    }
    const id = setTimeout(() => {
      refresh().catch(() => {});
    }, msUntilRefresh);
    return () => clearTimeout(id);
  }, [token]);

  const tryRefresh = async (): Promise<string | null> => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}) },
      });
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        const newToken = data.access_token || data.accessToken || data.token;
        if (newToken) {
          setToken(newToken);
          const p = decodeJWT(newToken);
          if (p) setUser(payloadToUser(p));
          return newToken as string;
        }
        // if HttpOnly sets cookie but no body, we still consider refreshed via cookie - but frontend can't read HttpOnly, so no token update
        // fallback: if we had a refresh cookie, keep old token? We'll return old
        return tokenRef.current;
      }
    } catch {}
    return null;
  };

  const fetchMe = async (tok?: string): Promise<User | null> => {
    const t = tok || tokenRef.current;
    if (!t) return null;
    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
        credentials: "include",
        cache: "no-store",
      });
      if (res.ok) {
        const data = await res.json();
        // data may be {user} or direct user
        const uRaw = data.user || data;
        if (uRaw && (uRaw.email || uRaw.id)) {
          const u: User = {
            id: uRaw.id || uRaw.sub || uRaw.email,
            email: uRaw.email,
            name: uRaw.name || uRaw.email?.split("@")[0] || "User",
            role: (uRaw.role || decodeJWT(t)?.role || "OPERATOR") as Role,
            orgId: uRaw.orgId || uRaw.org_id || decodeJWT(t)?.orgId || decodeJWT(t)?.org_id || "org-demo-01",
            orgName: uRaw.orgName || uRaw.org_name || decodeJWT(t)?.orgName || "Tantu Demo Org",
            plantId: uRaw.plantId || uRaw.plant_id || decodeJWT(t)?.plantId || "plant-demo-01",
            plantIds: uRaw.plantIds || uRaw.plant_ids || [],
          };
          setUser(u);
          // sync orgs
          if (u.orgId) {
            const o: Org = { id: u.orgId, name: u.orgName || u.orgId };
            setOrgs((prev) => (prev.find((x) => x.id === o.id) ? prev : [...prev, o]));
            if (!currentOrg) setCurrentOrg(o);
          }
          return u;
        }
      }
    } catch {}
    // fallback to decoded
    const p = decodeJWT(t);
    if (p) {
      const u = payloadToUser(p);
      setUser(u);
      return u;
    }
    return null;
  };

  const login = useCallback(
    async (email: string, password: string): Promise<User> => {
      // try real API
      try {
        const res = await fetch(`${API_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ email, password }),
        });
        if (res.ok) {
          const data = await res.json().catch(() => ({}));
          const tok = data.access_token || data.accessToken || data.token;
          const userRaw = data.user;
          if (tok) {
            setToken(tok);
            const p = decodeJWT(tok);
            let u: User;
            if (userRaw) {
              u = {
                id: userRaw.id || userRaw.sub || email,
                email: userRaw.email || email,
                name: userRaw.name || email.split("@")[0],
                role: (userRaw.role || p?.role || detectRoleFromEmail(email)) as Role,
                orgId: userRaw.orgId || userRaw.org_id || p?.orgId || p?.org_id || "org-demo-01",
                orgName: userRaw.orgName || userRaw.org_name || p?.orgName || "Demo Org",
                plantId: userRaw.plantId || userRaw.plant_id || p?.plantId || p?.plant_id || "plant-demo-01",
                plantIds: userRaw.plantIds || [],
              };
            } else if (p) {
              u = payloadToUser(p, email);
            } else {
              u = {
                id: email,
                email,
                name: email.split("@")[0],
                role: detectRoleFromEmail(email),
                orgId: "org-demo-01",
                orgName: "Demo Org",
                plantId: "plant-demo-01",
              };
            }
            setUser(u);
            // orgs
            const o: Org = { id: u.orgId, name: u.orgName || u.orgId };
            setOrgs((prev) => (prev.find((x) => x.id === o.id) ? prev : [...prev, o]));
            setCurrentOrg(o);
            try {
              localStorage.setItem(ORGS_KEY, JSON.stringify([...orgs, o].filter((v, i, a) => a.findIndex((x) => x.id === v.id) === i)));
              localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(o));
            } catch {}
            await fetchMe(tok).catch(() => {});
            return u;
          }
        }
        // if not ok, fall through to mock unless 401 with message
        if (res && res.status === 401) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || errData.message || "Invalid credentials");
        }
      } catch (e: any) {
        // if it's an explicit auth error, rethrow
        if (e && e.message === "Invalid credentials") throw e;
        // otherwise fall through to mock only if DEMO flag enabled
        if (!isDemoEnabled()) throw e;
      }

      // --- DEMO MOCK FALLBACK (offline) gated behind DEMO flag ---
      if (!isDemoEnabled()) throw new Error("Login failed — DEMO mock disabled and backend unreachable");
      // For demo/offline: accept any password >=4 chars, infer role from email
      if (!email || !email.includes("@")) throw new Error("Please enter a valid email");
      if (!password || password.length < 4) throw new Error("Password must be at least 4 characters");
      const role = detectRoleFromEmail(email);
      const mockPayload: JWTPayload = {
        sub: email,
        email,
        name: email.split("@")[0],
        role,
        org_id: "org-demo-01",
        org_name: "Tantu Demo Org",
        plant_id: role === "PLANT_HEAD" ? "plant-demo-01" : role === "OPERATOR" ? "plant-line-2" : "plant-demo-01",
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      };
      const mockToken = makeMockJWT(mockPayload);
      setToken(mockToken);
      const u = payloadToUser(mockPayload, email);
      setUser(u);
      const o: Org = { id: u.orgId, name: u.orgName || "Tantu Demo Org" };
      setOrgs((prev) => (prev.find((x) => x.id === o.id) ? prev : [...prev, o]));
      setCurrentOrg(o);
      try {
        const allOrgs = [...orgs, o].filter((v, i, a) => a.findIndex((x) => x.id === v.id) === i);
        if (!orgs.length) localStorage.setItem(ORGS_KEY, JSON.stringify(allOrgs));
        localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(o));
      } catch {}
      return u;
    },
    [orgs, setToken]
  );

  const signup = useCallback(
    async (data: { orgName: string; email: string; password: string; name?: string }): Promise<User> => {
      const { orgName, email, password, name } = data;
      if (!orgName || !email || !password) throw new Error("orgName, email and password are required");
      try {
        const res = await fetch(`${API_URL}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ org_name: orgName, orgName, email, password, name }),
        });
        if (res.ok) {
          const j = await res.json().catch(() => ({}));
          const tok = j.access_token || j.accessToken || j.token;
          if (tok) {
            setToken(tok);
            const p = decodeJWT(tok);
            const u = p ? payloadToUser(p, email) : ({ id: email, email, name: name || email.split("@")[0], role: "OWNER" as Role, orgId: j.org_id || j.orgId || "org-" + Date.now(), orgName, plantId: "plant-demo-01" } as User);
            // override to OWNER for org creator
            u.role = "OWNER";
            u.orgName = orgName;
            setUser(u);
            const o: Org = { id: u.orgId, name: orgName };
            setOrgs((prev) => [...prev.filter((x) => x.id !== o.id), o]);
            setCurrentOrg(o);
            return u;
          }
        } else {
          const err = await res.json().catch(() => ({}));
          if (res.status !== 404 && res.status !== 500) {
            throw new Error(err.detail || err.message || `Signup failed (${res.status})`);
          }
        }
      } catch (e: any) {
        if (e && e.message && !e.message.includes("fetch") && !e.message.includes("Failed")) throw e;
        if (!isDemoEnabled()) throw e;
      }

      // mock fallback gated behind DEMO flag: create org + OWNER user
      if (!isDemoEnabled()) throw new Error("Signup failed — DEMO mock disabled and backend unreachable");
      const orgId = "org-" + Math.random().toString(36).slice(2, 8);
      const mockPayload: JWTPayload = {
        sub: email,
        email,
        name: name || email.split("@")[0],
        role: "OWNER",
        org_id: orgId,
        org_name: orgName,
        plant_id: "plant-demo-01",
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      };
      const tok = makeMockJWT(mockPayload);
      setToken(tok);
      const u = payloadToUser(mockPayload, email);
      u.role = "OWNER";
      u.orgName = orgName;
      setUser(u);
      const o: Org = { id: orgId, name: orgName };
      setOrgs((prev) => [...prev.filter((x) => x.id !== o.id), o]);
      setCurrentOrg(o);
      try {
        localStorage.setItem(ORGS_KEY, JSON.stringify([...orgs.filter((x) => x.id !== o.id), o]));
        localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(o));
      } catch {}
      return u;
    },
    [orgs, setToken]
  );

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_URL}/auth/logout`, { method: "POST", credentials: "include", headers: tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {} }).catch(() => {});
    } catch {}
    setToken(null);
    setUser(null);
    // keep orgs but clear current
    // optionally clear refresh cookie via backend; frontend cookie already cleared in setToken
    if (typeof window !== "undefined") {
      try {
        // clear HttpOnly refresh is backend's job, but try to clear mock
        document.cookie = `tantu_refresh=; path=/; max-age=0; SameSite=Lax`;
        document.cookie = `refresh_token=; path=/; max-age=0; SameSite=Lax`;
      } catch {}
    }
  }, [setToken]);

  const refresh = useCallback(async (): Promise<string | null> => {
    const t = await tryRefresh();
    if (t) return t;
    // if refresh failed and token expired, logout — keep mock tokens only if DEMO enabled
    const cur = tokenRef.current;
    if (cur) {
      const p = decodeJWT(cur);
      if (p?.exp && p.exp * 1000 < Date.now()) {
        if (!cur.includes("mock_signature") || !isDemoEnabled()) {
          await logout();
          return null;
        }
      }
    }
    return cur;
  }, [logout]);

  const me = useCallback(async (): Promise<User | null> => {
    const t = tokenRef.current;
    if (!t) return null;
    return fetchMe(t);
  }, []);

  const acceptInvite = useCallback(
    async (inviteToken: string, password: string, name?: string): Promise<User> => {
      if (!inviteToken) throw new Error("Invite token is required");
      if (!password || password.length < 4) throw new Error("Password must be at least 4 characters");
      try {
        const res = await fetch(`${API_URL}/auth/invite/accept`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ token: inviteToken, password, name }),
        });
        if (res.ok) {
          const j = await res.json().catch(() => ({}));
          const tok = j.access_token || j.accessToken || j.token;
          if (tok) {
            setToken(tok);
            const p = decodeJWT(tok);
            const u = p ? payloadToUser(p) : ({ id: j.email || inviteToken, email: j.email || "", name: name || "", role: j.role || "OPERATOR", orgId: j.org_id || "org-demo-01", orgName: j.org_name || "Demo Org", plantId: "plant-demo-01" } as User);
            setUser(u);
            return u;
          }
          if (j.user) {
            const uRaw = j.user;
            const u: User = {
              id: uRaw.id || uRaw.email,
              email: uRaw.email,
              name: uRaw.name || name || "",
              role: uRaw.role || "OPERATOR",
              orgId: uRaw.orgId || uRaw.org_id || "org-demo-01",
              orgName: uRaw.orgName || "Demo Org",
              plantId: uRaw.plantId || "plant-demo-01",
            };
            const mockPayload: JWTPayload = {
              sub: u.email,
              email: u.email,
              name: u.name,
              role: u.role,
              org_id: u.orgId,
              org_name: u.orgName,
              plant_id: u.plantId,
              exp: Math.floor(Date.now() / 1000) + 3600,
              iat: Math.floor(Date.now() / 1000),
            };
            const tok2 = makeMockJWT(mockPayload);
            setToken(tok2);
            setUser(u);
            return u;
          }
        } else {
          const err = await res.json().catch(() => ({}));
          if (res.status !== 404) throw new Error(err.detail || err.message || "Invalid or expired invite token");
        }
      } catch (e: any) {
        if (e && e.message && !e.message.includes("fetch") && !e.message.includes("Failed to fetch")) throw e;
        if (!isDemoEnabled()) throw e;
      }
      if (!isDemoEnabled()) throw new Error("Invite accept failed — DEMO mock disabled and backend unreachable");
      // mock fallback gated behind DEMO flag: decode invite token as base64 json if possible, else use role OPERATOR
      let role: Role = "OPERATOR";
      let orgId = "org-demo-01";
      let orgName = "Tantu Demo Org";
      let email = "";
      let invitedName = name || "";
      try {
        const p = decodeJWT(inviteToken);
        if (p && p.role) {
          role = p.role as Role;
          orgId = (p.orgId || p.org_id || orgId) as string;
          orgName = (p.orgName || p.org_name || orgName) as string;
          email = p.email || email;
        } else {
          // try plain base64 json
          const jsonStr = typeof window !== "undefined" ? atob(inviteToken.replace(/-/g, "+").replace(/_/g, "/")) : "";
          if (jsonStr) {
            const j = JSON.parse(jsonStr);
            role = j.role || role;
            orgId = j.orgId || j.org_id || orgId;
            orgName = j.orgName || j.org_name || orgName;
            email = j.email || email;
          }
        }
      } catch {}
      const finalEmail = email || `invited-${Date.now()}@tantu.local`;
      const mockPayload: JWTPayload = {
        sub: finalEmail,
        email: finalEmail,
        name: invitedName || finalEmail.split("@")[0],
        role,
        org_id: orgId,
        org_name: orgName,
        plant_id: "plant-demo-01",
        exp: Math.floor(Date.now() / 1000) + 3600,
        iat: Math.floor(Date.now() / 1000),
      };
      const tok = makeMockJWT(mockPayload);
      setToken(tok);
      const u = payloadToUser(mockPayload, finalEmail);
      if (name) u.name = name;
      setUser(u);
      const o: Org = { id: orgId, name: orgName };
      setOrgs((prev) => (prev.find((x) => x.id === o.id) ? prev : [...prev, o]));
      setCurrentOrg(o);
      return u;
    },
    [setToken]
  );

  const switchOrg = useCallback(
    (orgId: string) => {
      const target = orgs.find((o) => o.id === orgId);
      if (!target) return;
      setCurrentOrg(target);
      // optionally re-issue token with new org? For mock, patch token payload gated behind DEMO
      const cur = tokenRef.current;
      if (cur) {
        const p = decodeJWT(cur);
        if (p) {
          const updated: JWTPayload = { ...p, org_id: target.id, org_name: target.name };
          const newTok = cur.includes("mock_signature") && isDemoEnabled() ? makeMockJWT(updated) : cur;
          if (newTok !== cur) {
            setToken(newTok);
            setUser(payloadToUser(updated));
          }
        }
      }
      try {
        localStorage.setItem(CURRENT_ORG_KEY, JSON.stringify(target));
      } catch {}
    },
    [orgs, setToken]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: !!user && !!token,
      login,
      signup,
      logout,
      refresh,
      me,
      acceptInvite,
      orgs: orgs.length ? orgs : currentOrg ? [currentOrg] : user ? [{ id: user.orgId, name: user.orgName || user.orgId }] : [],
      currentOrg: currentOrg || (user ? { id: user.orgId, name: user.orgName || user.orgId } : null),
      switchOrg,
      setUser,
    }),
    [user, token, loading, login, signup, logout, refresh, me, acceptInvite, orgs, currentOrg, switchOrg]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export const ACCESS_TOKEN_KEY = ACCESS_KEY;
