// triage.ts
// Mirrors backend/app/schemas/triage.py exactly.
// If you change one, change the other.

export type IncidentClass =
  | "wan_upstream"
  | "wireless"
  | "auth_802_1x"
  | "routing_switching"
  | "circuit_carrier"
  | "change_induced_config_drift"
  | "insufficient_information";

export type EscalationRecommendation =
  | "escalate_now"
  | "omc_attempt"
  | "ask_more_information";

export type OmcGapType =
  | "missing_runbook"
  | "missing_telemetry"
  | "missing_permissions"
  | "insufficient_training"
  | "cross_team_dependency"
  | "poor_incident_data_quality"
  | "tool_limitation"
  | "known_bug_no_workaround";

// ── Request ──────────────────────────────────────────────────────────────────

export interface TriageRequest {
  raw_summary: string;
  sites_affected?: string[];
  change_window?: boolean;
  severity?: "sev1" | "sev2" | "sev3";
  region?: "AMER" | "EMEA" | "APAC";
}

// ── Sub-models ───────────────────────────────────────────────────────────────

export interface AffectedScope {
  sites_count: number;
  users_estimate: number;
  scope_label: "single_site" | "multi_site" | "unknown";
}

export interface SimilarIncident {
  incident_id: string;
  summary: string;
  incident_class: string;
  root_cause: string;
  resolution: string;
  similarity_score: number;
  change_induced: boolean;
}

export interface EscalationDetail {
  recommendation: EscalationRecommendation;
  reasoning: string;
  time_limit_minutes?: number;
  sev1_triggered: boolean;
}

export interface IncidentRecord {
  incident_id: string;
  raw_summary: string;
  region?: string;
  sites_affected_count: number;
  user_impact_estimate: number;
  incident_class: string;
  subtype?: string;
  confidence: number;
  change_window_flag: boolean;
  change_induced: boolean;
  ambiguous: boolean;
  escalation_path: string;
  final_root_cause?: string;
  final_resolution?: string;
  prevented_by_omc: boolean;
  omc_gap_type?: string;
  created_at: string;
  resolved_at?: string;
  split?: string;
}

export interface WeeklyReportClassRow {
  class: string;
  count: number;
  pct: number;
}

export interface WeeklyReportGapRow {
  gap: string;
  count: number;
}

export interface WeeklyReport {
  period: {
    start: string;
    end: string;
  };
  total_escalations: number;
  by_class: WeeklyReportClassRow[];
  by_gap_type: WeeklyReportGapRow[];
  change_induced_count: number;
  omc_self_resolved: number;
  recurring_sites: string[];
  top_recommendation: string;
  runbook_gaps: string[];
}

export interface TaxonomyClassDefinition {
  label: string;
  description: string;
  subtypes?: string[];
  signal_keywords?: string[];
  correlated_layers?: string[];
  typical_blast_radius: string;
  change_sensitivity?: string;
  omc_self_resolve?: boolean | string;
  typical_tier3_reason?: string;
}

export interface TaxonomyResponse {
  taxonomy: Record<string, TaxonomyClassDefinition>;
  omc_gap_types?: string[];
}

// ── Response ─────────────────────────────────────────────────────────────────

export interface TriageResponse {
  incident_id: string;
  primary_class: IncidentClass;
  subtype?: string;
  confidence: number;
  change_induced: boolean;
  suspected_contributing_factor?: string;
  ambiguity_notes?: string;
  reasoning: string;
  affected_scope: AffectedScope;
  symptoms: string[];
  missing_facts: string[];
  diagnostic_path: string[];
  similar_incidents: SimilarIncident[];
  escalation: EscalationDetail;
  omc_gap_type_candidate?: OmcGapType;
  latency_ms: number;
  mock: boolean;
}

// ── Display helpers ───────────────────────────────────────────────────────────

export const CLASS_LABELS: Record<IncidentClass, string> = {
  wan_upstream:                "WAN / Upstream",
  wireless:                    "Wireless Infrastructure",
  auth_802_1x:                 "Auth / 802.1X / RADIUS",
  routing_switching:           "Routing / Switching",
  circuit_carrier:             "Circuit / Carrier",
  change_induced_config_drift: "Change-Induced / Config Drift",
  insufficient_information:    "Insufficient Information",
};

export const GAP_LABELS: Record<OmcGapType, string> = {
  missing_runbook:            "Missing Runbook",
  missing_telemetry:          "Missing Telemetry",
  missing_permissions:        "Missing Permissions",
  insufficient_training:      "Insufficient Training",
  cross_team_dependency:      "Cross-Team Dependency",
  poor_incident_data_quality: "Poor Incident Data Quality",
  tool_limitation:            "Tool Limitation",
  known_bug_no_workaround:    "Known Bug / No Workaround",
};

export const ESCALATION_LABELS: Record<EscalationRecommendation, string> = {
  escalate_now:         "Escalate to Tier 3 Now",
  omc_attempt:          "OMC Can Attempt",
  ask_more_information: "Ask for More Information",
};
