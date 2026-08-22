import { NextResponse, NextRequest } from "next/server";

// minimal JWT decode without verification (edge safe)
function decodePayload(token: string): any | null {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    // pad
    const padded = b64.padEnd(b64.length + ((4 - (b64.length % 4)) % 4), "=");
    const json = atob(padded);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isMaintenanceRole(role: string): boolean {
  const r = (role || "").toUpperCase();
  return r === "MAINTENANCE" || r.startsWith("MAINTENANCE_");
}
function canAccess(pathname: string, role: string): boolean {
  const r = (role || "").toUpperCase();
  if (pathname.startsWith("/admin")) {
    return r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/operator")) {
    return r === "OPERATOR" || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/maintenance")) {
    return isMaintenanceRole(r) || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  if (pathname.startsWith("/plant-head")) {
    return r === "PLANT_HEAD" || r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN";
  }
  return true;
}

function roleToDashboard(role: string): string {
  const r = (role || "").toUpperCase();
  if (r === "OPERATOR") return "/operator";
  if (r.startsWith("MAINTENANCE") || r === "MAINTENANCE") return "/maintenance";
  if (r === "PLANT_HEAD") return "/plant-head";
  if (r === "ORG_ADMIN" || r === "OWNER" || r === "ADMIN") return "/admin/users";
  // fallback for unknown privileged roles
  if (r) return "/operator";
  return "/login";
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // handle root "/" — redirect to role dashboard when authenticated, else show landing
  if (pathname === "/") {
    const token =
      request.cookies.get("tantu_access")?.value ||
      request.cookies.get("access_token")?.value ||
      request.cookies.get("token")?.value ||
      null;
    if (token) {
      const payload = decodePayload(token);
      if (payload) {
        // check not expired
        if (!(payload.exp && payload.exp * 1000 < Date.now() - 5_000)) {
          const role = (payload.role || payload.Role || "") as string;
          const dest = roleToDashboard(role);
          const url = request.nextUrl.clone();
          url.pathname = dest;
          // preserve search? typically not needed for root
          return NextResponse.redirect(url);
        }
      }
    }
    // check refresh token present — let client refresh; do not redirect blindly
    return NextResponse.next();
  }

  // public routes — always allow (except root handled above)
  if (
    pathname.startsWith("/login") ||
    pathname.startsWith("/signup") ||
    pathname.startsWith("/invite") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    pathname.startsWith("/favicon") ||
    pathname.match(/\.(png|jpg|jpeg|svg|ico|webp|css|js)$/)
  ) {
    return NextResponse.next();
  }

  const protectedPrefixes = ["/operator", "/maintenance", "/plant-head", "/admin"];
  const isProtected = protectedPrefixes.some((p) => pathname === p || pathname.startsWith(p + "/") || pathname.startsWith(p));

  if (!isProtected) {
    return NextResponse.next();
  }

  // try to get token from cookies
  const token =
    request.cookies.get("tantu_access")?.value ||
    request.cookies.get("access_token")?.value ||
    request.cookies.get("token")?.value ||
    null;

  const refreshToken =
    request.cookies.get("tantu_refresh")?.value ||
    request.cookies.get("refresh_token")?.value ||
    null;

  if (!token && !refreshToken) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }

  // if we have token, check RBAC and exp
  if (token) {
    const payload = decodePayload(token);
    if (payload) {
      // check exp
      if (payload.exp && payload.exp * 1000 < Date.now() - 5_000) {
        // expired — if we have refresh cookie, allow to pass through (client will refresh)
        // otherwise redirect to login
        if (!refreshToken) {
          const url = request.nextUrl.clone();
          url.pathname = "/login";
          url.searchParams.set("next", pathname + search);
          url.searchParams.set("reason", "expired");
          return NextResponse.redirect(url);
        }
        // allow through with refresh cookie
        return NextResponse.next();
      }
      const role = (payload.role || payload.Role || "") as string;
      if (!canAccess(pathname, role)) {
        // forbidden — redirect to login with error or to home
        const url = request.nextUrl.clone();
        url.pathname = "/login";
        url.searchParams.set("error", "forbidden");
        url.searchParams.set("required", pathname.split("/")[1] || "");
        url.searchParams.set("role", role);
        return NextResponse.redirect(url);
      }
    } else {
      // malformed token -> redirect to login unless refresh exists
      if (!refreshToken) {
        const url = request.nextUrl.clone();
        url.pathname = "/login";
        url.searchParams.set("next", pathname + search);
        return NextResponse.redirect(url);
      }
    }
  }

  // token missing but refresh exists -> allow, client will refresh
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/operator/:path*",
    "/maintenance/:path*",
    "/plant-head/:path*",
    "/admin/:path*",
    // also match root for completeness but middleware skips
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
