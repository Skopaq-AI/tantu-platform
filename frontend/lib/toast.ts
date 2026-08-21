"use client";
// sonner shim — uses real sonner if available, otherwise console + no-op Toaster
let realToast: any = null;
let RealToaster: any = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const s: any = require("sonner");
  realToast = s.toast;
  RealToaster = s.Toaster;
} catch {}

import * as React from "react";

export const toast: {
  success: (msg: string, opts?: any) => void;
  error: (msg: string, opts?: any) => void;
  info: (msg: string, opts?: any) => void;
  message: (msg: string, opts?: any) => void;
} = realToast || {
  success: (m: string) => { if (typeof window !== "undefined") console.log("[toast success]", m); },
  error: (m: string) => { if (typeof window !== "undefined") console.log("[toast error]", m); },
  info: (m: string) => console.log("[toast info]", m),
  message: (m: string) => console.log("[toast]", m),
};

export function Toaster(props: any) {
  if (RealToaster) return React.createElement(RealToaster, props);
  return null;
}
