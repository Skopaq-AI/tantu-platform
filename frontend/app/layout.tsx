import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";
import { I18nProvider } from "@/components/I18nProvider";

export const metadata: Metadata = {
  title: "TANTU — Mixed-Fleet Intelligence",
  description: "Operator voice-first · Maintenance mixed-fleet · Plant-head opex — raw frames never leave plant",
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-50">
        <I18nProvider>
          <Header />
          <main className="max-w-7xl mx-auto">{children}</main>
          <footer className="text-center text-[11px] text-slate-400 py-8 px-4">
            <div>Skopaq AI · Hyderabad · Codename TANTU uncleared · Frames never leave plant · Dual reasoning: Nemotron-9B on-prem + Gemini ER2 cloud on derived events only</div>
            <div className="mt-1">DPDP 2023 · SOC2 patterns · OWASP ASVS · data_residency=IN</div>
          </footer>
        </I18nProvider>
      </body>
    </html>
  );
}
