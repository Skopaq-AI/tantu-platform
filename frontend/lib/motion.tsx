"use client";
import * as React from "react";

// shim that proxies to framer-motion if available, otherwise falls back to plain div with no animation
let motionProxy: any = null;
let AnimatePresenceProxy: any = null;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fm: any = require("framer-motion");
  motionProxy = fm.motion;
  AnimatePresenceProxy = fm.AnimatePresence;
} catch (e) {
  const Fallback = React.forwardRef<any, any>(({ children, initial, animate, exit, transition, whileHover, whileTap, ...props }: any, ref: any) =>
    React.createElement("div", { ref, ...props }, children)
  );
  Fallback.displayName = "FallbackMotion";
  motionProxy = {
    div: Fallback,
    span: Fallback,
    button: Fallback,
  };
  AnimatePresenceProxy = ({ children }: { children: React.ReactNode }) => <>{children}</>;
}

export const motion = motionProxy;
export const AnimatePresence = AnimatePresenceProxy;
