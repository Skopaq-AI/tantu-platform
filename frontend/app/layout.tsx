import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { I18nProvider } from "@/components/I18nProvider";
import { Toaster } from "@/lib/toast";

export const metadata: Metadata = {
  title: "TANTU \u2014 Mixed-Fleet Intelligence",
  description: "Operator voice-first (85dB, 5-lang, one-button ACK) \u00b7 Maintenance mixed-fleet (SSE/NATS, FFT, MTConnect) \u00b7 Plant-head opex Rs18K \u2014 raw frames never leave plant",
  viewport: "width=device-width, initial-scale=1, viewport-fit=cover",
  themeColor: "#0ea5e9",
};

// Offline-safe font: sandbox proxy blocks fonts.googleapis.com, so load Inter only if available
let interVar = "";
let interClass = "";
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Inter } = require("next/font/google");
  const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });
  interVar = inter.variable;
  interClass = inter.className;
} catch {}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className={interVar}>
      <body className={`min-h-screen bg-slate-50 dark:bg-slate-950 font-sans antialiased ${interClass}`}>
        <I18nProvider>
          <Header />
          <main id="main" className="max-w-7xl mx-auto">
            {children}
          </main>
          <footer className="text-center text-[11px] text-slate-400 dark:text-slate-500 py-8 px-4 border-t mt-8 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur">
            <div className="max-w-3xl mx-auto">
              Skopaq AI \u00b7 Hyderabad \u00b7 Codename TANTU uncleared \u00b7 Frames never leave plant \u00b7 Dual reasoning: Nemotron-9B on-prem + Gemini ER2 cloud on derived events only
            </div>
            <div className="mt-1">DPDP 2023 \u00b7 SOC2 patterns \u00b7 OWASP ASVS \u00b7 data_residency=IN \u00b7 p95 &lt;40ms edge</div>
          </footer>
          <Toaster richColors position="top-right" closeButton expand={false} />
        </I18nProvider>
      </body>
    </html>
  );
}
