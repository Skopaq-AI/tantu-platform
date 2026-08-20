"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, LineChart, Line, AreaChart, Area } from "recharts";

function genFFT() {
  const bins = 32;
  const out = [];
  for (let i = 0; i < bins; i++) {
    const freq = Math.round((i * 2000) / bins);
    let amp = Math.random() * 0.3;
    if (i === 6) amp = 1.8; // bearing fault peak
    if (i === 14) amp = 1.2;
    if (i === 22) amp = 0.6;
    out.push({ freq: `${freq}Hz`, amp: Number(amp.toFixed(2)), freqN: freq });
  }
  return out;
}

const fftData = genFFT();

export function FFTChart() {
  return (
    <div className="h-[200px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={fftData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="freq" tick={{ fontSize: 9 }} interval={3} />
          <YAxis tick={{ fontSize: 11 }} label={{ value: "mm/s", angle: -90, position: "insideLeft", fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="amp" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <p className="text-[11px] text-slate-500 mt-1 text-center">FFT · bearing fault at 375Hz (harmonic at 875Hz) · normalized</p>
    </div>
  );
}

function genWalkTrend() {
  const arr = [];
  const base = Date.now() - 7 * 24 * 3600 * 1000;
  for (let i = 0; i < 14; i++) {
    const day = i;
    const before = i < 7 ? 45 + Math.round(Math.random() * 8) : 6 + Math.round(Math.random() * 3);
    arr.push({ day: `D${i + 1}`, walk: before });
  }
  return arr;
}

export function WalkTrendChart() {
  const data = genWalkTrend();
  return (
    <div className="h-[160px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="day" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip />
          <Area type="monotone" dataKey="walk" stroke="#0ea5e9" fill="#e0f2fe" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
