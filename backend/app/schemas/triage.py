from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class IncidentClass(str, Enum):
    wan_upstream = "wan_upstream"
    wireless = "wireless"
    auth_802_1x = "auth_802_1x"
    routing_switching = "routing_switching"
    circuit_carrier = "circuit_carrier"
    change_induced_config_drift = "change_induced_config_drift"
    insufficient_information = "insufficient_information"


class EscalationRecommendation(str, Enum):
    escalate_now = "escalate_now"
    omc_attempt = "omc_attempt"
    ask_more_information = "ask_more_information"


class OmcGapType(str, Enum):
    missing_runbook = "missing_runbook"
    missing_telemetry = "missing_telemetry"
    missing_permissions = "missing_permissions"
    insufficient_training = "insufficient_training"
    cross_team_dependency = "cross_team_dependency"
    poor_incident_data_quality = "poor_incident_data_quality"
    tool_limitation = "tool_limitation"
    known_bug_no_workaround = "known_bug_no_workaround"


class ScopeLabel(str, Enum):
    single_site = "single_site"
    multi_site = "multi_site"
    unknown = "unknown"


class TriageRequest(BaseModel):
    raw_summary: str = Field(..., min_length=5)
    sites_affected: Optional[list[str]] = None
    change_window: Optional[bool] = None
    severity: Optional[str] = None
    region: Optional[str] = None


class AffectedScope(BaseModel):
    sites_count: int = Field(default=1, ge=0)
    users_estimate: int = Field(default=150, ge=0)
    scope_label: ScopeLabel = ScopeLabel.single_site


class SimilarIncident(BaseModel):
    incident_id: str
    summary: str
    incident_class: str
    root_cause: str
    resolution: str
    similarity_score: float
    change_induced: bool


class EscalationDetail(BaseModel):
    recommendation: EscalationRecommendation
    reasoning: str
    time_limit_minutes: Optional[int] = None
    sev1_triggered: bool = False


class TriageResponse(BaseModel):
    incident_id: str
    primary_class: IncidentClass
    subtype: Optional[str] = None
    confidence: int = Field(..., ge=0, le=100)
    change_induced: bool = False
    suspected_contributing_factor: Optional[str] = None
    ambiguity_notes: Optional[str] = None
    reasoning: str
    affected_scope: AffectedScope
    symptoms: list[str] = Field(default_factory=list)
    missing_facts: list[str] = Field(default_factory=list)
    diagnostic_path: list[str] = Field(default_factory=list)
    similar_incidents: list[SimilarIncident] = Field(default_factory=list)
    escalation: EscalationDetail
    omc_gap_type_candidate: Optional[OmcGapType] = None
    latency_ms: int = Field(default=0, ge=0)
    mock: bool = False


class IncidentResolveRequest(BaseModel):
    root_cause: str
    resolution: str
    omc_gap_type: OmcGapType
    prevented_by_omc: bool