"use client";
import { TriageResponse } from "@/types/triage";
import { CLASS_LABELS, IncidentClass } from "@/types/triage";
import { cn, classColor } from "@/lib/utils";

export function DiagnosticPathCard({ data }: { data: TriageResponse }) {
  if (!data.diagnostic_path.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-blue-600" />
        <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
          Diagnostic Path
        </span>
        <span className="ml-auto text-[11px] text-slate-500">In order</span>
      </div>
      <ol className="space-y-2">
        {data.diagnostic_path.map((step, i) => (
          <li key={i} className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 font-mono text-[11px] text-slate-600">
              {i + 1}
            </span>
            <span className="pt-0.5 text-sm leading-6 text-slate-700">{step}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function SimilarIncidentsCard({ data }: { data: TriageResponse }) {
  if (!data.similar_incidents.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
        <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
          Similar Past Incidents
        </span>
      </div>
      <div className="space-y-3">
        {data.similar_incidents.map((inc) => (
          <div key={inc.incident_id}
            className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-slate-500">{inc.incident_id}</span>
              <span className={cn(
                "rounded-md border px-2 py-0.5 text-[11px] font-medium",
                classColor(inc.incident_class as IncidentClass)
              )}>
                {CLASS_LABELS[inc.incident_class as keyof typeof CLASS_LABELS] ?? inc.incident_class}
              </span>
              {inc.change_induced && (
                <span className="rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] text-rose-700">
                  change
                </span>
              )}
              <span className="ml-auto font-mono text-[11px] text-slate-500">
                {Math.round(inc.similarity_score * 100)}% match
              </span>
            </div>

            <p className="line-clamp-2 text-sm leading-6 text-slate-700">
              {inc.summary}
            </p>

            <div className="space-y-2 border-t border-slate-200 pt-3 text-sm">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Root cause · </span>
                <span className="text-slate-700">{inc.root_cause}</span>
              </div>
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Resolution · </span>
                <span className="text-slate-600">{inc.resolution}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function OmcGapCard({ data }: { data: TriageResponse }) {
  if (!data.omc_gap_type_candidate) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-600" />
        <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
          OMC Capability Gap
        </span>
      </div>
      <div className="text-sm text-slate-700">
        Why OMC could not self-resolve:{" "}
        <span className="font-semibold text-slate-900">
          {data.omc_gap_type_candidate.replace(/_/g, " ")}
        </span>
      </div>
      <p className="text-sm leading-6 text-slate-600">
        This signal is tracked weekly to identify where runbook coverage,
        tooling, or training investments will reduce future escalations.
      </p>
    </div>
  );
}
