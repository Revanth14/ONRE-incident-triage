"use client";
import { TriageResponse } from "@/types/triage";
import { CLASS_LABELS, ESCALATION_LABELS } from "@/types/triage";
import { cn, classColor, confidenceColor, confidenceBg, confidenceLabel, escalationColor } from "@/lib/utils";

export function ClassificationCard({ data }: { data: TriageResponse }) {
  const confLabel = confidenceLabel(data.confidence);

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold tracking-[0.16em] text-slate-500 uppercase">Classification</span>
        {data.mock && (
          <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] text-slate-500">
            MOCK
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className={cn(
          "rounded-md border px-3 py-1 text-sm font-medium",
          classColor(data.primary_class)
        )}>
          {CLASS_LABELS[data.primary_class]}
        </span>
        {data.subtype && (
          <span className="text-sm text-slate-500">
            · {data.subtype.replace(/_/g, " ")}
          </span>
        )}
        {data.change_induced && (
          <span className="rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700">
            CHANGE-INDUCED
          </span>
        )}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-600">Confidence</span>
          <span className={cn("font-mono font-semibold", confidenceColor(data.confidence))}>
            {data.confidence}% · {confLabel}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-slate-200">
          <div
            className={cn("h-full rounded-full transition-all", confidenceBg(data.confidence))}
            style={{ width: `${data.confidence}%` }}
          />
        </div>
      </div>

      <div className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium",
        escalationColor(data.escalation.recommendation)
      )}>
        <EscalationDot rec={data.escalation.recommendation} />
        {ESCALATION_LABELS[data.escalation.recommendation]}
        {data.escalation.time_limit_minutes && (
          <span className="ml-auto text-xs font-normal opacity-80">
            {data.escalation.time_limit_minutes} min limit
          </span>
        )}
      </div>

      {data.reasoning && (
        <p className="border-t border-slate-200 pt-3 text-sm leading-6 text-slate-600">
          {data.reasoning}
        </p>
      )}
    </div>
  );
}

function EscalationDot({ rec }: { rec: string }) {
  const color =
    rec === "escalate_now" ? "bg-rose-600" :
    rec === "omc_attempt"  ? "bg-amber-600" :
                             "bg-sky-600";
  return <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", color)} />;
}
