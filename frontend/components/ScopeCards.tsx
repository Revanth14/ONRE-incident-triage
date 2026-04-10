"use client";
import { TriageResponse } from "@/types/triage";

export function ScopeCard({ data }: { data: TriageResponse }) {
  const isUnknown =
    data.affected_scope.scope_label === "unknown" ||
    data.affected_scope.sites_count === 0 ||
    data.affected_scope.users_estimate === 0;

  const sitesValue = isUnknown
    ? "Unknown"
    : String(data.affected_scope.sites_count);
  const usersValue = isUnknown
    ? "Unknown"
    : `~${data.affected_scope.users_estimate.toLocaleString()}`;
  const scopeValue = isUnknown
    ? "Unknown"
    : data.affected_scope.scope_label.replace("_", " ");

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
      <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
        Blast Radius
      </span>
      <div className="grid grid-cols-2 gap-3">
        <Stat label="Sites Affected" value={sitesValue} />
        <Stat label="Est. Users" value={usersValue} />
        <Stat label="Scope" value={scopeValue} />
        <Stat label="Incident ID" value={data.incident_id} mono />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 space-y-1">
      <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
        {label}
      </div>
      <div
        className={`text-sm text-slate-900 ${mono ? "font-mono" : "font-medium"}`}
      >
        {value}
      </div>
    </div>
  );
}

export function SymptomsCard({ data }: { data: TriageResponse }) {
  if (!data.symptoms.length) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
        Detected Symptoms
      </span>
      <ul className="space-y-1.5">
        {data.symptoms.map((s, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
            <span className="mt-2 h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0" />
            {s}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MissingFactsCard({ data }: { data: TriageResponse }) {
  if (!data.missing_facts.length) return null;
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-600" />
        <span className="text-xs font-semibold tracking-[0.16em] text-amber-700 uppercase">
          Missing Facts
        </span>
      </div>
      <ul className="space-y-1.5">
        {data.missing_facts.map((f, i) => (
          <li key={i} className="flex items-start gap-3 text-sm text-slate-700">
            <span className="mt-0.5 font-mono text-xs text-amber-700">
              {String(i + 1).padStart(2, "0")}
            </span>
            {f}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AmbiguityCard({ data }: { data: TriageResponse }) {
  if (!data.ambiguity_notes && !data.suspected_contributing_factor) return null;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3">
      <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">
        Analyst Notes
      </span>
      {data.suspected_contributing_factor && (
        <div className="space-y-0.5">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
            Contributing Factor
          </div>
          <div className="text-sm text-slate-700">
            {data.suspected_contributing_factor}
          </div>
        </div>
      )}
      {data.ambiguity_notes && (
        <p className="text-sm leading-6 text-slate-600">
          {data.ambiguity_notes}
        </p>
      )}
    </div>
  );
}
