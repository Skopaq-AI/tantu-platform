"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

const TabsContext = React.createContext<{ value: string; onValueChange: (v: string) => void } | null>(null);

export function Tabs({ defaultValue, value, onValueChange, children, className }: { defaultValue?: string; value?: string; onValueChange?: (v: string) => void; children: React.ReactNode; className?: string }) {
  const [inner, setInner] = React.useState(defaultValue || "");
  const current = value ?? inner;
  const handle = (v: string) => { setInner(v); onValueChange?.(v); };
  return <TabsContext.Provider value={{ value: current, onValueChange: handle }}><div className={cn(className)}>{children}</div></TabsContext.Provider>;
}

export function TabsList({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("inline-flex h-10 items-center justify-center rounded-lg bg-slate-100 p-1", className)}>{children}</div>;
}

export function TabsTrigger({ value, children, className }: { value: string; children: React.ReactNode; className?: string }) {
  const ctx = React.useContext(TabsContext);
  const active = ctx?.value === value;
  return (
    <button onClick={() => ctx?.onValueChange(value)} className={cn("inline-flex items-center justify-center whitespace-nowrap rounded-md px-4 py-1.5 text-sm font-medium transition-all", active ? "bg-white shadow-sm text-slate-900" : "text-slate-600 hover:text-slate-900", className)}>
      {children}
    </button>
  );
}

export function TabsContent({ value, children, className }: { value: string; children: React.ReactNode; className?: string }) {
  const ctx = React.useContext(TabsContext);
  if (ctx?.value !== value) return null;
  return <div className={cn("mt-4 ring-offset-white focus-visible:outline-none", className)}>{children}</div>;
}
