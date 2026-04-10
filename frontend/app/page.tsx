import Link from "next/link";
const STATS = [
  { label: "Covered Offices", value: "400+" },
  { label: "Managed Devices", value: "76K" },
  { label: "Incident Classes", value: "7" },
  { label: "Weekly Review", value: "Enabled" },
];

const MODULES = [
  {
    title: "Triage Intake",
    desc: "Accepts free-text OMC escalations and normalizes them into a consistent incident record.",
  },
  {
    title: "Classification",
    desc: "Maps the escalation to a failure domain with confidence, supporting signals, and next checks.",
  },
  {
    title: "Incident Retrieval",
    desc: "Shows closed incidents with similar symptoms so operators can compare root cause and resolution.",
  },
  {
    title: "Escalation Routing",
    desc: "Uses deterministic rules to decide whether OMC should continue, gather detail, or escalate.",
  },
  {
    title: "Capability Reporting",
    desc: "Tracks why incidents were not self-resolved and summarizes recurring operational gaps each week.",
  },
  {
    title: "Taxonomy Reference",
    desc: "Publishes the current classification model so OMC and reviewers work from the same definitions.",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-6">
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-3xl space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              Console Overview
            </p>
            <h1 className="text-3xl font-semibold text-slate-900">
              Office Network Incident Triage
            </h1>
            <p className="text-sm leading-6 text-slate-600">
              Internal workflow for reviewing OMC escalations, identifying the likely
              network domain, and guiding the next action with consistent output.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Link
              href="/triage"
              className="rounded-lg border border-blue-600 bg-blue-600 px-4 py-3 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            >
              Open Triage Workspace
            </Link>
            <Link
              href="/reports/weekly"
              className="rounded-lg border border-slate-300 bg-white px-4 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
            >
              Review Weekly Report
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
          >
            <div className="text-2xl font-semibold text-slate-900">{stat.value}</div>
            <div className="mt-1 text-xs uppercase tracking-[0.14em] text-slate-500">
              {stat.label}
            </div>
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-6 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Workflow Modules</h2>
          <p className="mt-1 text-sm text-slate-600">
            The console combines structured extraction, classification, retrieval, and
            deterministic escalation guidance.
          </p>
        </div>
        <div className="grid gap-px bg-slate-200 md:grid-cols-2 xl:grid-cols-3">
          {MODULES.map((module) => (
            <div key={module.title} className="bg-white p-5">
              <h3 className="text-sm font-semibold text-slate-900">{module.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{module.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-slate-50 p-6">
        <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Operational Notes</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Triage output is intended to support OMC decision-making, not replace
              operator judgment. Similar incident matching and LLM-derived reasoning are
              paired with deterministic escalation thresholds for consistency.
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
              Current Capabilities
            </div>
            <ul className="mt-3 space-y-2 text-sm text-slate-600">
              <li>Failure-domain classification with confidence scoring</li>
              <li>Missing-facts prompts for low-information escalations</li>
              <li>Past-incident retrieval with root cause and resolution detail</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
