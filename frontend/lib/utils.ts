// lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { IncidentClass, EscalationRecommendation } from "@/types/triage";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 85) return "text-emerald-700";
  if (confidence >= 60) return "text-amber-700";
  return "text-rose-700";
}

export function confidenceBg(confidence: number): string {
  if (confidence >= 85) return "bg-emerald-600";
  if (confidence >= 60) return "bg-amber-500";
  return "bg-rose-600";
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 85) return "High";
  if (confidence >= 60) return "Medium";
  return "Low";
}

export function escalationColor(rec: EscalationRecommendation): string {
  switch (rec) {
    case "escalate_now":        return "text-rose-700 border-rose-200 bg-rose-50";
    case "omc_attempt":         return "text-amber-700 border-amber-200 bg-amber-50";
    case "ask_more_information":return "text-sky-700 border-sky-200 bg-sky-50";
  }
}

export function classColor(cls: IncidentClass): string {
  switch (cls) {
    case "wan_upstream":                return "text-blue-700 border-blue-200 bg-blue-50";
    case "wireless":                    return "text-cyan-700 border-cyan-200 bg-cyan-50";
    case "auth_802_1x":                 return "text-amber-700 border-amber-200 bg-amber-50";
    case "routing_switching":           return "text-slate-700 border-slate-300 bg-slate-100";
    case "circuit_carrier":             return "text-orange-700 border-orange-200 bg-orange-50";
    case "change_induced_config_drift": return "text-rose-700 border-rose-200 bg-rose-50";
    case "insufficient_information":    return "text-slate-600 border-slate-200 bg-white";
  }
}

export function formatMs(ms: number): string {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}
