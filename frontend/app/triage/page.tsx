"use client";
import { useState } from "react";
import { submitTriage } from "@/lib/api";
import { TriageRequest, TriageResponse } from "@/types/triage";
import { ClassificationCard } from "@/components/ClassificationCard";
import { ScopeCard, SymptomsCard, MissingFactsCard, AmbiguityCard } from "@/components/ScopeCards";
import { DiagnosticPathCard, SimilarIncidentsCard, OmcGapCard } from "@/components/DiagnosticCards";
import { formatMs } from "@/lib/utils";

const EXAMPLES = [
  "Three offices in Austin reporting inability to access internal systems. Wireless appears fine. Issue started 40 minutes after tonight's change window closed.",
  "All London offices reporting users unable to authenticate. Both wired and wireless affected. RADIUS server alarms firing.",
  "Chicago-Loop floor 7 — complete network outage. Severe broadcast storm. Switch CPU at 100%. Started 10 minutes ago.",
  "Seattle-Beacon — new laptops from this week's hardware refresh cannot connect to wired network. Previous model works fine. Wireless works.",
  "Network is slow.",
];

export default function TriagePage() {
  const [summary, setSummary] = useState("");
  const [changeWindow, setChangeWindow] = useState<boolean | undefined>();
  const [severity, setSeverity] = useState<TriageRequest["severity"] | "">("");
  const [region, setRegion] = useState<TriageRequest["region"] | "">("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TriageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!summary.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const req: TriageRequest = {
        raw_summary: summary.trim(),
        change_window: changeWindow,
        severity: severity || undefined,
        region: region || undefined,
      };
      const res = await submitTriage(req);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to run triage.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white px-6 py-5 shadow-sm">
        <div className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
            Triage Workspace
          </p>
          <h1 className="text-xl font-semibold text-slate-900">Incident Triage</h1>
          <p className="text-sm text-slate-600">
            Paste an OMC escalation summary. The system will classify the failure domain,
            identify missing facts, and recommend next steps.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[400px_1fr]">
        <div className="space-y-4">
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <h2 className="text-sm font-semibold text-slate-900">Input</h2>
              <p className="mt-1 text-xs text-slate-500">
                Provide the operator summary and any known metadata before running triage.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Incident Summary
                </label>
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  placeholder="Paste OMC escalation text here..."
                  rows={8}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Change Window
                  </label>
                  <select
                    value={changeWindow === undefined ? "" : changeWindow ? "yes" : "no"}
                    onChange={(e) =>
                      setChangeWindow(e.target.value === "" ? undefined : e.target.value === "yes")
                    }
                    className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="">Unknown</option>
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Severity
                  </label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity((e.target.value || "") as TriageRequest["severity"] | "")}
                    className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="">Unknown</option>
                    <option value="sev1">Sev 1</option>
                    <option value="sev2">Sev 2</option>
                    <option value="sev3">Sev 3</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Region
                  </label>
                  <select
                    value={region}
                    onChange={(e) => setRegion((e.target.value || "") as TriageRequest["region"] | "")}
                    className="w-full rounded-lg border border-slate-300 bg-white px-2.5 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="">Any</option>
                    <option value="AMER">AMER</option>
                    <option value="EMEA">EMEA</option>
                    <option value="APAC">APAC</option>
                  </select>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !summary.trim()}
                className="w-full rounded-lg border border-blue-600 bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:border-slate-300 disabled:bg-slate-200 disabled:text-slate-500"
              >
                {loading ? "Running Triage..." : "Run Triage"}
              </button>
            </form>
          </div>

          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-3">
              <h2 className="text-sm font-semibold text-slate-900">Example Inputs</h2>
              <p className="mt-1 text-xs text-slate-500">
                Use one of the sample summaries to validate the triage flow.
              </p>
            </div>

            <div className="space-y-2">
              {EXAMPLES.map((ex, i) => (
                <button
                  key={i}
                  onClick={() => setSummary(ex)}
                  className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-left text-sm text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900"
                >
                  <span className="mr-2 font-mono text-xs text-slate-400">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  {ex}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          {loading && (
            <div className="space-y-3">
              {[152, 112, 132, 168, 208].map((height, i) => (
                <div
                  key={i}
                  className="animate-pulse rounded-xl border border-slate-200 bg-white"
                  style={{ height }}
                />
              ))}
            </div>
          )}

          {result && !loading && (
            <>
              <div className="flex items-center justify-between px-1">
                <span className="font-mono text-xs text-slate-500">{result.incident_id}</span>
                <span className="text-xs text-slate-500">
                  {formatMs(result.latency_ms)} · {result.mock ? "mock response" : "live response"}
                </span>
              </div>

              <ClassificationCard data={result} />
              <ScopeCard data={result} />
              <MissingFactsCard data={result} />
              <DiagnosticPathCard data={result} />
              <SymptomsCard data={result} />
              <AmbiguityCard data={result} />
              <SimilarIncidentsCard data={result} />
              <OmcGapCard data={result} />
            </>
          )}

          {!result && !loading && !error && (
            <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">No triage run yet</h2>
              <p className="mt-2 text-sm text-slate-500">
                Submit an incident summary to view classification, scope, similar
                incidents, and escalation guidance.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
