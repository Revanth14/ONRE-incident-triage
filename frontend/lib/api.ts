// lib/api.ts
import {
  IncidentRecord,
  TaxonomyResponse,
  TriageRequest,
  TriageResponse,
  WeeklyReport,
} from "@/types/triage";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}

export async function submitTriage(req: TriageRequest): Promise<TriageResponse> {
  return apiFetch<TriageResponse>("/api/triage", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function getIncidents(params?: {
  incident_class?: string;
  omc_gap_type?: string;
  region?: string;
  limit?: number;
}): Promise<IncidentRecord[]> {
  const qs = new URLSearchParams(
    Object.entries(params || {})
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return apiFetch<IncidentRecord[]>(`/api/incidents${qs ? `?${qs}` : ""}`);
}

export async function getIncident(id: string): Promise<IncidentRecord> {
  return apiFetch<IncidentRecord>(`/api/incidents/${id}`);
}

export async function getWeeklyReport(): Promise<WeeklyReport> {
  return apiFetch<WeeklyReport>("/api/reports/weekly");
}

export async function getTaxonomy(): Promise<TaxonomyResponse> {
  return apiFetch<TaxonomyResponse>("/api/taxonomy");
}

export async function seedDatabase() {
  return apiFetch("/api/seed", { method: "POST" });
}
