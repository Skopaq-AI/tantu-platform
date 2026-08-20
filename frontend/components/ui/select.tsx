"use client";
import * as React from "react";
import { cn } from "@/lib/utils";

export function Select({ value, onValueChange, children }: { value: string; onValueChange: (v: string) => void; children: React.ReactNode }) {
  return <div data-select-value={value}>{React.Children.map(children, (c: any) => React.cloneElement(c, { value, onValueChange }))}</div>;
}

export function SelectTrigger({ value, onValueChange, children, className }: any) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className={cn("flex h-10 w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm", className)}>
        <span>{children}</span>
      </button>
      {open && <div className="absolute z-10 mt-1 w-full rounded-md border bg-white shadow-lg">{React.Children.map(children, (c: any) => c.type?.displayName === "SelectContent" ? React.cloneElement(c, { onValueChange, setOpen }) : null)}</div>}
    </div>
  );
}

export function SelectContent({ children, onValueChange, setOpen }: any) {
  SelectContent.displayName = "SelectContent";
  return <div className="p-1">{React.Children.map(children, (c: any) => React.cloneElement(c, { onValueChange, setOpen }))}</div>;
}

export function SelectItem({ value, children, onValueChange, setOpen }: any) {
  return <button onClick={() => { onValueChange?.(value); setOpen?.(false); }} className="w-full text-left px-2 py-1.5 text-sm hover:bg-slate-100 rounded">{children}</button>;
}

export function SelectValue({ children }: any) { return <span>{children}</span>; }
