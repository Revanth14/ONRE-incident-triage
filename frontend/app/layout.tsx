import type { Metadata } from "next";

import { AppHeader } from "@/components/AppHeader";

import "./globals.css";

export const metadata: Metadata = {
  title: "ONRE Incident Triage",
  description: "Office Network Reliability Engineering — OMC Escalation Triage Assistant",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[var(--page-bg)] text-slate-900">
        <AppHeader />
        <main className="mx-auto max-w-[1440px] px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
