"use client";
import { useEffect, useState } from "react";

import { getIncidents } from "@/lib/api";
import { IncidentRecord, CLASS_LABELS, IncidentClass } from "@/types/triage";
import { classColor } from "@/lib/utils";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    getIncidents({limit:70})
      .then(setIncidents)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load incidents.");
      })
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter ? incidents.filter((incident) => incident.incident_class === filter) : incidents;

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              Incident Register
            </p>
            <h1 className="mt-1 text-xl font-semibold text-slate-900">Incidents</h1>
            <p className="mt-1 text-sm text-slate-600">
              Review stored incident records and filter by classified failure domain.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {incidents.length} records
            </div>
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
            >
              <option value="">All classes</option>
              {Object.entries(CLASS_LABELS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && !loading ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500 shadow-sm">
          Loading incidents...
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <div className="min-w-[900px]">
              <div className="grid grid-cols-[130px_220px_minmax(0,1fr)_180px_120px] gap-4 border-b border-slate-200 bg-slate-50 px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                <span>Incident ID</span>
                <span>Class</span>
                <span>Summary</span>
                <span>OMC Gap</span>
                <span>Status</span>
              </div>

              <div className="divide-y divide-slate-200">
                {filtered.map((incident) => (
                  <div
                    key={incident.incident_id}
                    className="grid grid-cols-[130px_220px_minmax(0,1fr)_180px_120px] gap-4 px-4 py-3 text-sm"
                  >
                    <span className="font-mono text-xs text-slate-500">{incident.incident_id}</span>
                    <span
                      className={`inline-flex w-fit items-center rounded-md border px-2 py-0.5 text-xs font-medium ${classColor(incident.incident_class as IncidentClass)}`}
                    >
                      {CLASS_LABELS[incident.incident_class as IncidentClass] ?? incident.incident_class}
                    </span>
                    <p className="line-clamp-2 text-sm leading-6 text-slate-700">{incident.raw_summary}</p>
                    <span className="text-xs text-slate-500">
                      {incident.omc_gap_type ? incident.omc_gap_type.replace(/_/g, " ") : "Not set"}
                    </span>
                    <span className="text-xs font-medium text-slate-600">
                      {incident.prevented_by_omc ? "Self-resolved" : "Escalated"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
