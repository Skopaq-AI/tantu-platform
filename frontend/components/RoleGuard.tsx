"use client";
import { useEffect, useMemo } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth, canAccessPath, roleLabel } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Shield, LogIn } from "lucide-react";
import Link from "next/link";

export function RoleGuard({
  children,
  allowedRoles,
  requireAuth = true,
}: {
  children: React.ReactNode;
  allowedRoles: string[];
  requireAuth?: boolean;
}) {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const userRole = user?.role ? (user.role as string) : "";
  const normalizedAllowed = useMemo(() => allowedRoles.map((r) => r.toUpperCase()), [allowedRoles]);

  const isAllowed = useMemo(() => {
    if (!userRole) return false;
    const ru = userRole.toUpperCase();
    // wildcard MAINTENANCE_*
    for (const ar of normalizedAllowed) {
      if (ar.endsWith("_*") || ar.endsWith("*")) {
        const prefix = ar.replace(/\*$/, "").replace(/_$/, "");
        // e.g., MAINTENANCE_* -> MAINTENANCE
        if (ar === "MAINTENANCE_*" || ar === "MAINTENANCE*") {
          if (ru === "MAINTENANCE" || ru.startsWith("MAINTENANCE_")) return true;
        } else if (ru.startsWith(prefix)) return true;
      } else if (ar === ru) return true;
      // allow ORG_ADMIN/OWNER to bypass? but allowedRoles explicitly lists them where needed
    }
    // also check path-based helper for consistency
    // if role is ORG_ADMIN/OWNER and allowed includes admin, already handled
    // final fallback: check canAccessPath if pathname matches allowed semantics
    return false;
  }, [userRole, normalizedAllowed]);

  // also compute path check: ensures user canAccess current pathname at all
  const canAccessCurrent = useMemo(() => {
    if (!userRole || !pathname) return true;
    return canAccessPath(pathname, userRole);
  }, [pathname, userRole]);

  useEffect(() => {
    if (loading) return;
    if (requireAuth && !isAuthenticated) {
      router.replace(`/login?next=${encodeURIComponent(pathname || "/")}`);
      return;
    }
    if (isAuthenticated && userRole && !isAllowed) {
      // do not auto-redirect loop, just stay to show forbidden
    }
  }, [loading, isAuthenticated, isAllowed, pathname, router, requireAuth, userRole]);

  if (loading) {
    return (
      <div className="px-4 sm:px-6 py-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <div className="grid lg:grid-cols-3 gap-4">
          <Skeleton className="h-[420px] lg:col-span-2 rounded-2xl" />
          <Skeleton className="h-[420px] rounded-2xl" />
        </div>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) {
    return (
      <div className="px-4 sm:px-6 py-12 flex justify-center">
        <Card className="max-w-md w-full text-center">
          <CardContent className="pt-6 space-y-4">
            <div className="mx-auto h-12 w-12 rounded-2xl bg-slate-100 dark:bg-slate-800 grid place-items-center">
              <Shield className="h-6 w-6 text-slate-500" />
            </div>
            <h2 className="font-semibold">Authentication required</h2>
            <p className="text-sm text-slate-500">Please sign in to access this workspace. Your session may have expired.</p>
            <Link href={`/login?next=${encodeURIComponent(pathname || "/")}`}>
              <Button variant="primary" className="w-full mt-2">
                <LogIn className="h-4 w-4 mr-2" /> Sign in
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!isAllowed || !canAccessCurrent) {
    return (
      <div className="px-4 sm:px-6 py-12 flex justify-center">
        <Card className="max-w-lg w-full text-center border-amber-200 dark:border-amber-800">
          <CardContent className="pt-6 space-y-4">
            <div className="mx-auto h-12 w-12 rounded-2xl bg-amber-100 dark:bg-amber-900 grid place-items-center">
              <Shield className="h-6 w-6 text-amber-600" />
            </div>
            <h2 className="font-semibold">Access denied</h2>
            <p className="text-sm text-slate-500">
              Your role <Badge variant="outline" className="mx-1">{roleLabel(userRole) || "Unknown"}</Badge> does not have access to{" "}
              <span className="font-mono text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded">{pathname}</span>.
            </p>
            <p className="text-xs text-slate-400">
              Required: {allowedRoles.join(", ")} · If you believe this is an error, contact your org admin.
            </p>
            <div className="flex gap-2 justify-center pt-2">
              <Link href="/">
                <Button variant="outline">Go to landing</Button>
              </Link>
              <Link href="/login">
                <Button variant="primary">Switch account</Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
}

export default RoleGuard;
