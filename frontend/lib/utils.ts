import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatLatency(ms: number): string {
  return `${Math.round(ms)}ms`;
}

export function formatConfidence(c: number): string {
  return `${Math.round(c * 100)}%`;
}

export function defectLabel(c: string): string {
  const map: Record<string, string> = {
    none: "Normal",
    pressure_drift: "Pressure drift",
    vib_high: "Vib high",
    thermal_high: "Thermal high",
    solder_void: "Solder void",
    alignment_drift: "Alignment drift",
  };
  return map[c] || c;
}

export function protocolColor(p: string): string {
  const m: Record<string, string> = {
    opcua: "bg-sky-100 text-sky-800 border-sky-200",
    modbus: "bg-amber-100 text-amber-800 border-amber-200",
    camera: "bg-violet-100 text-violet-800 border-violet-200",
    mqtt: "bg-emerald-100 text-emerald-800 border-emerald-200",
    mtconnect: "bg-orange-100 text-orange-800 border-orange-200",
    ethernet_ip: "bg-slate-100 text-slate-800 border-slate-200",
  };
  return m[p] || "bg-slate-100 text-slate-700 border-slate-200";
}
