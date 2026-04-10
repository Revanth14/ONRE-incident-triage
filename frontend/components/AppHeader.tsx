"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/triage", label: "Triage" },
  { href: "/incidents", label: "Incidents" },
  { href: "/reports/weekly", label: "Weekly Report" },
  { href: "/taxonomy", label: "Taxonomy" },
];

function isActive(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/";
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppHeader() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-6 px-6 py-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            ONRE Internal Tool
          </p>
          <div className="mt-1 flex items-center gap-3">
            <span className="text-sm font-semibold text-slate-900">
              Incident Triage Console
            </span>
            <span className="rounded border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-600">
              Internal Use
            </span>
          </div>
        </div>

        <nav className="flex items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
          {NAV.map((item) => {
            const active = isActive(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  active
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:bg-white hover:text-slate-900",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
