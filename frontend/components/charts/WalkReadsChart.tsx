"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend, CartesianGrid } from "recharts";

const data = [
  { name: "Line 1", before: 52, after: 7 },
  { name: "Line 2", before: 48, after: 6 },
  { name: "Line 3", before: 44, after: 5 },
  { name: "Fab-A", before: 36, after: 4 },
];

export function WalkReadsChart() {
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} barGap={8}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip />
          <Legend />
          <Bar dataKey="before" name="Before (manual)" fill="#94a3b8" radius={[6, 6, 0, 0]} />
          <Bar dataKey="after" name="After (TANTU)" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function WalkReadsInline() {
  return (
    <div className="h-[140px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data.slice(0, 2)} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" hide />
          <YAxis dataKey="name" type="category" width={60} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="before" fill="#94a3b8" />
          <Bar dataKey="after" fill="#0ea5e9" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
