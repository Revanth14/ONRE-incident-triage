"use client";

import { useEffect, useState } from "react";

import { getWeeklyReport } from "@/lib/api";
import { WeeklyReport } from "@/types/triage";

export default function WeeklyReportPage() {
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWeeklyReport()
      .then(setReport)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load report.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500 shadow-sm">
        Loading report...
      </div>
    );
  }

  if (!report || error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error || "Failed to load report."}
      </div>
    );
  }

  const top = report.total_escalations || 1;
  const summaryCards = [
    { label: "Total Escalations", value: report.total_escalations },
    { label: "OMC Self-Resolved", value: report.omc_self_resolved },
    { label: "Change-Induced", value: report.change_induced_count },
    { label: "Recurring Sites", value: report.recurring_sites?.length ?? 0 },
  ];

  return (
    <div className="max-w-5xl space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          Weekly Review
        </p>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">
          Weekly Escalation Report
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Summary of current escalation mix and the capability gaps driving Tier
          3 involvement.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {summaryCards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="text-2xl font-semibold text-slate-900">
              {card.value}
            </div>
            <div className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">
              {card.label}
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">
          By Incident Class
        </h2>
        <div className="mt-4 space-y-3">
          {report.by_class.map((row) => (
            <div key={row.class} className="flex items-center gap-3">
              <span className="w-52 shrink-0 text-sm text-slate-600">
                {row.class.replace(/_/g, " ")}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-blue-600"
                  style={{ width: `${Math.round((row.count / top) * 100)}%` }}
                />
              </div>
              <span className="w-20 text-right font-mono text-xs text-slate-500">
                {row.count} / {row.pct}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">
            OMC Capability Gaps
          </h2>
          <div className="mt-4 space-y-3">
            {report.by_gap_type.map((row) => (
              <div
                key={row.gap}
                className="flex items-center justify-between border-b border-slate-100 pb-2 text-sm"
              >
                <span className="text-slate-600">
                  {row.gap.replace(/_/g, " ")}
                </span>
                <span className="font-mono text-xs text-slate-500">
                  {row.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Top Recommendation
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-700">
            {report.top_recommendation}
          </p>
          <div className="mt-4 rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              Period
            </div>
            <p className="mt-2 text-sm text-slate-600">
              {new Date(report.period.start).toLocaleString()} to{" "}
              {new Date(report.period.end).toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
