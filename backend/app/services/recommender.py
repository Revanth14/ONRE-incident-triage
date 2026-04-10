"""
Recommender — Stage 4 of the pipeline (deterministic rules).

All escalation decisions, blast radius estimates, and Sev1 routing
are handled here with deterministic code — NOT the LLM.

Why deterministic:
  The LLM can misclassify. If escalation decisions were LLM-driven,
  a wrong classification could give incorrect operational guidance.
  Code rules are predictable, auditable, and safe.

Rule priority order (matches taxonomy escalation_rules):
  1. Sev1 conditions → escalate_now immediately
  2. confidence < 60 → ask_more_information
  3. confidence 60-84 → omc_attempt_with_monitoring
  4. confidence >= 85 and omc_self_resolve=true → omc_attempt
  5. confidence >= 85 and omc_self_resolve=false → escalate_now
"""

import yaml
from app.core.config import settings
from app.schemas.triage import (
    AffectedScope, EscalationDetail,
    EscalationRecommendation, OmcGapType, IncidentClass
)

with open(settings.taxonomy_path) as f:
    TAXONOMY = yaml.safe_load(f)

# Classes where OMC can typically self-resolve
OMC_SELF_RESOLVE_CLASSES = {
    k for k, v in TAXONOMY.get("taxonomy", {}).items()
    if v.get("omc_self_resolve") is True
}

# Classes that are always multi-site
MULTI_SITE_CLASSES = {
    k for k, v in TAXONOMY.get("taxonomy", {}).items()
    if v.get("typical_blast_radius") == "multi_site"
}

# Time limits (minutes) for OMC to attempt before escalating
OMC_TIME_LIMITS = {
    "wan_upstream":                30,
    "wireless":                    20,
    "auth_802_1x":                 25,
    "routing_switching":           20,
    "circuit_carrier":             30,
    "change_induced_config_drift": 20,
    "insufficient_information":    None,
}

# Typical OMC gap by class (heuristic for new incidents)
TYPICAL_GAP_BY_CLASS = {
    "wan_upstream":                OmcGapType.cross_team_dependency,
    "wireless":                    OmcGapType.missing_runbook,
    "auth_802_1x":                 OmcGapType.missing_permissions,
    "routing_switching":           OmcGapType.missing_runbook,
    "circuit_carrier":             OmcGapType.cross_team_dependency,
    "change_induced_config_drift": OmcGapType.missing_runbook,
    "insufficient_information":    OmcGapType.poor_incident_data_quality,
}

USERS_PER_SITE = 150


def compute_blast_radius(
    primary_class: str,
    sites_count: int,
    is_multi_site: bool,
    regex_sites_count: int,
) -> AffectedScope:
    """
    Deterministic blast radius estimate.
    Uses taxonomy metadata + regex-extracted site count.
    """
    if primary_class == "insufficient_information":
        return AffectedScope(
            sites_count=0,
            users_estimate=0,
            scope_label="unknown",
        )

    if is_multi_site or primary_class in MULTI_SITE_CLASSES:
        effective_sites = max(sites_count, regex_sites_count, 2)
    else:
        effective_sites = max(sites_count, 1)

    users = effective_sites * USERS_PER_SITE
    scope_label = "multi_site" if effective_sites > 1 else "single_site"

    return AffectedScope(
        sites_count=effective_sites,
        users_estimate=users,
        scope_label=scope_label,
    )

def is_sev1(
    primary_class: str,
    sites_count: int,
    users_estimate: int,
    severity_override: str | None,
) -> bool:
    """
    Hard Sev1 detection. These conditions bypass all other routing.
    Matches taxonomy escalation_rules.sev1_conditions.
    """
    if severity_override == "sev1":
        return True
    if sites_count >= 5:
        return True
    if users_estimate >= 500:
        return True
    if primary_class == "wan_upstream" and sites_count >= 3:
        return True
    if primary_class == "auth_802_1x" and sites_count >= 3:
        return True
    return False


def compute_escalation(
    primary_class: str,
    confidence: int,
    sites_count: int,
    users_estimate: int,
    severity_override: str | None = None,
) -> EscalationDetail:
    """
    Deterministic escalation recommendation.
    Priority order is enforced in code, not prompted.
    """
    # Rule 1: Sev1 hard override
    if is_sev1(primary_class, sites_count, users_estimate, severity_override):
        return EscalationDetail(
            recommendation=EscalationRecommendation.escalate_now,
            reasoning=(
                f"Sev1 threshold exceeded: {sites_count} sites, "
                f"~{users_estimate} users affected. "
                "Escalate to Tier 3 immediately regardless of confidence."
            ),
            time_limit_minutes=None,
            sev1_triggered=True,
        )

    # Rule 2: Low confidence — need more info
    if confidence < 60:
        return EscalationDetail(
            recommendation=EscalationRecommendation.ask_more_information,
            reasoning=(
                f"Confidence is {confidence}% — insufficient to classify reliably. "
                "Gather the listed missing facts before attempting diagnosis."
            ),
            time_limit_minutes=None,
            sev1_triggered=False,
        )

    # Rule 3: Medium confidence — OMC attempts with time limit
    if confidence < 85:
        time_limit = OMC_TIME_LIMITS.get(primary_class, 20)
        return EscalationDetail(
            recommendation=EscalationRecommendation.omc_attempt,
            reasoning=(
                f"Confidence is {confidence}% — OMC can attempt the diagnostic path. "
                f"Escalate to Tier 3 if unresolved within {time_limit} minutes or "
                "if the issue requires config changes beyond OMC authority."
            ),
            time_limit_minutes=time_limit,
            sev1_triggered=False,
        )

    # Rule 4 & 5: High confidence
    can_self_resolve = primary_class in OMC_SELF_RESOLVE_CLASSES

    if can_self_resolve:
        time_limit = OMC_TIME_LIMITS.get(primary_class, 20)
        return EscalationDetail(
            recommendation=EscalationRecommendation.omc_attempt,
            reasoning=(
                f"High confidence ({confidence}%) and this class is typically "
                f"resolvable by OMC. Follow the diagnostic path. "
                f"Escalate if not resolved within {time_limit} minutes."
            ),
            time_limit_minutes=time_limit,
            sev1_triggered=False,
        )
    else:
        return EscalationDetail(
            recommendation=EscalationRecommendation.escalate_now,
            reasoning=(
                f"High confidence ({confidence}%) but this failure class "
                f"({primary_class.replace('_', ' ')}) typically requires "
                "Tier 3 intervention — carrier coordination, BGP config access, "
                "or ISE admin permissions beyond OMC authority."
            ),
            time_limit_minutes=None,
            sev1_triggered=False,
        )


def infer_omc_gap(
    primary_class: str,
    confidence: int,
    change_induced: bool,
) -> OmcGapType | None:
    """
    Heuristic inference of why OMC could not self-resolve.
    This is a candidate — confirmed when incident is closed.
    """
    if confidence < 40:
        return OmcGapType.poor_incident_data_quality
    if change_induced:
        return OmcGapType.missing_runbook
    return TYPICAL_GAP_BY_CLASS.get(primary_class)
