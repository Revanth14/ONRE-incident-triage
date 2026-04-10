"use client";

import { useEffect, useState } from "react";

import { getTaxonomy } from "@/lib/api";
import { IncidentClass, TaxonomyResponse } from "@/types/triage";
import { classColor } from "@/lib/utils";

export default function TaxonomyPage() {
  const [taxonomy, setTaxonomy] = useState<TaxonomyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getTaxonomy()
      .then(setTaxonomy)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load taxonomy.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500 shadow-sm">
        Loading taxonomy...
      </div>
    );
  }

  if (!taxonomy || error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
        {error || "Failed to load taxonomy."}
      </div>
    );
  }

  const classes = Object.entries(taxonomy.taxonomy || {});

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
          Reference
        </p>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">Incident Taxonomy</h1>
        <p className="mt-1 text-sm text-slate-600">
          Ground-truth definitions used by the classifier, retrieval layer, and reporting workflow.
        </p>
      </div>

      <div className="space-y-4">
        {classes.map(([key, cls]) => {
          const omcSelfResolve = cls.omc_self_resolve === true;

          return (
            <div key={key} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span
                      className={`inline-flex items-center rounded-md border px-3 py-1 text-sm font-medium ${classColor(key as IncidentClass)}`}
                    >
                      {cls.label}
                    </span>
                    <span className="font-mono text-xs text-slate-500">{key}</span>
                  </div>
                  <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-600">{cls.description}</p>
                </div>

                <div className="flex flex-wrap gap-2 text-xs">
                  <span
                    className={`rounded-md border px-2.5 py-1 ${
                      omcSelfResolve
                        ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                        : "border-slate-200 bg-slate-50 text-slate-600"
                    }`}
                  >
                    {omcSelfResolve ? "OMC can resolve" : "Tier 3 required"}
                  </span>
                  <span className="rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-slate-600">
                    {cls.typical_blast_radius}
                  </span>
                </div>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Subtypes
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(cls.subtypes || []).map((subtype) => (
                      <span
                        key={subtype}
                        className="rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-600"
                      >
                        {subtype.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Signal Keywords
                  </div>
                  <ul className="mt-3 space-y-2">
                    {(cls.signal_keywords || []).map((signal) => (
                      <li key={signal} className="flex gap-2 text-sm text-slate-600">
                        <span className="mt-2 h-1.5 w-1.5 rounded-full bg-slate-400 shrink-0" />
                        <span>{signal}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {cls.typical_tier3_reason ? (
                <div className="mt-5 border-t border-slate-200 pt-4 text-sm text-slate-600">
                  <span className="font-medium text-slate-700">Typical Tier 3 reason:</span>{" "}
                  {cls.typical_tier3_reason}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
