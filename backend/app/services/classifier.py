import json
import logging
import re
from typing import Any, Optional, TypedDict

import yaml
from openai import OpenAI

from app.core.config import settings
from app.services.extractor import ExtractedFacts, LlmExtractedFacts

logger = logging.getLogger(__name__)


def _load_taxonomy() -> dict[str, Any]:
    with open(settings.taxonomy_path) as handle:
        return yaml.safe_load(handle)


TAXONOMY = _load_taxonomy()
TAXONOMY_CLASSES: dict[str, dict[str, Any]] = TAXONOMY.get("taxonomy", {})
VALID_CLASSES = set(TAXONOMY_CLASSES)

TIE_BREAK_RULES = [
    "Prefer auth_802_1x when explicit 802.1X, RADIUS, ISE, certificate, or authentication failures are mentioned.",
    "Prefer wireless only when wireless is affected and wired is explicitly unaffected.",
    "Prefer wan_upstream for simultaneous multi-site reachability failures that hit both wired and wireless users.",
    "Prefer change_induced_config_drift only when a recent change window or config change is part of the incident story.",
    "Primary class should represent the technical failure domain, not just temporal correlation.",
    "A recent change may be a contributing factor without being the primary class.",
    "Do not choose change_induced_config_drift as the primary class solely because the incident occurred after a change window.",
    "Use insufficient_information when the text is vague or conflicting and confidence should be below 60.",
]

FEW_SHOT_EXAMPLES = [
    {
        "input": "Three offices in Austin and Seattle reporting complete inability to reach internal tools. Wireless appears to be connecting fine. Wired users also affected.",
        "output": {
            "primary_class": "wan_upstream",
            "subtype": "bgp_session_drop",
            "confidence": 88,
            "change_induced": False,
            "suspected_contributing_factor": "shared upstream dependency across sites",
            "ambiguity_notes": None,
            "missing_facts": ["edge router BGP state", "circuit alarms", "carrier notifications"],
            "diagnostic_path": [
                "verify edge router reachability and BGP neighbor state",
                "check route withdrawals or upstream loss",
                "confirm carrier status",
            ],
            "reasoning": "Simultaneous multi-site reachability loss across wired and wireless users points to a shared WAN dependency.",
        },
    },
    {
        "input": "Three offices in Austin reporting inability to access internal systems. Wireless appears fine. Issue started 40 minutes after tonight's change window closed.",
        "output": {
            "primary_class": "wan_upstream",
            "subtype": "edge_path_blackhole",
            "confidence": 72,
            "change_induced": True,
            "suspected_contributing_factor": "recent edge or routing policy change",
            "ambiguity_notes": "A recent change is a plausible contributing cause, but simultaneous multi-site reachability loss points to a shared WAN or upstream dependency as the primary failure domain.",
            "missing_facts": [
                "exact edge devices changed",
                "BGP neighbor state on affected sites",
                "internet versus internal reachability at each site",
                "carrier alarms or maintenance notices",
                "route table deltas before and after the change",
            ],
            "diagnostic_path": [
                "review edge and routing changes from the maintenance window",
                "check BGP neighbor state and route withdrawals on affected sites",
                "verify whether impacted sites share the same upstream dependency",
                "confirm carrier status and circuit alarms",
                "compare pre-change and post-change route state",
            ],
            "reasoning": "The outage is simultaneous across multiple sites, which indicates a shared WAN or upstream dependency. The recent change is more likely a contributing factor than the primary technical failure domain.",
        },
    },
    {
        "input": "Floor 7 users cannot see the SSID and wired users on the same floor are working normally.",
        "output": {
            "primary_class": "wireless",
            "subtype": "ssid_missing",
            "confidence": 90,
            "change_induced": False,
            "suspected_contributing_factor": "wireless infrastructure issue isolated from the wired network",
            "ambiguity_notes": None,
            "missing_facts": ["affected AP or controller alarms", "SSID scope", "recent AP changes"],
            "diagnostic_path": [
                "check controller and AP health for the affected floor",
                "verify SSID is being broadcast",
                "confirm DHCP is healthy for the wireless VLAN",
            ],
            "reasoning": "Wireless-only impact with wired users unaffected strongly points to the wireless domain.",
        },
    },
    {
        "input": "Users across two offices cannot authenticate to the network. RADIUS alarms are firing and devices keep reconnecting.",
        "output": {
            "primary_class": "auth_802_1x",
            "subtype": "radius_server_down",
            "confidence": 91,
            "change_induced": False,
            "suspected_contributing_factor": "centralized authentication dependency failure",
            "ambiguity_notes": None,
            "missing_facts": ["RADIUS server health", "ISE alarms", "certificate validity"],
            "diagnostic_path": [
                "check RADIUS or ISE server availability",
                "verify recent AAA policy or certificate changes",
                "confirm clients are failing during authentication",
            ],
            "reasoning": "Explicit RADIUS and authentication failure signals outweigh other classes.",
        },
    },
    {
        "input": "Chicago office complete outage after a spanning tree loop. Switch CPU is pinned and the floor is flooded with broadcasts.",
        "output": {
            "primary_class": "routing_switching",
            "subtype": "spanning_tree_loop",
            "confidence": 93,
            "change_induced": False,
            "suspected_contributing_factor": "layer 2 control-plane instability",
            "ambiguity_notes": None,
            "missing_facts": ["switch topology state", "impacted VLANs", "port flap history"],
            "diagnostic_path": [
                "identify the looping segment or STP topology change",
                "isolate the unstable switch or trunk",
                "verify VLAN and port-channel health after containment",
            ],
            "reasoning": "Spanning tree and broadcast-storm language is specific to campus routing and switching failures.",
        },
    },
    {
        "input": "Video calls are degraded with packet loss and jitter. The circuit is still up but carrier maintenance alerts are present.",
        "output": {
            "primary_class": "circuit_carrier",
            "subtype": "carrier_maintenance",
            "confidence": 86,
            "change_induced": False,
            "suspected_contributing_factor": "provider-side circuit degradation",
            "ambiguity_notes": None,
            "missing_facts": ["interface errors", "carrier maintenance notice", "latency and packet-loss history"],
            "diagnostic_path": [
                "check circuit and interface error counters",
                "confirm whether carrier maintenance is active",
                "compare loss and jitter against baseline",
            ],
            "reasoning": "The incident describes degradation rather than a full routing outage and includes explicit carrier signals.",
        },
    },
    {
        "input": "Users lost access shortly after the maintenance window. A rollback restored service.",
        "output": {
            "primary_class": "change_induced_config_drift",
            "subtype": "rollback_required",
            "confidence": 89,
            "change_induced": True,
            "suspected_contributing_factor": "recent configuration change introduced the failure",
            "ambiguity_notes": None,
            "missing_facts": ["exact change list", "diff against golden config", "rollback status"],
            "diagnostic_path": [
                "identify the recent change touching the affected path",
                "compare device state to known-good config",
                "confirm rollback or remediation outcome",
            ],
            "reasoning": "The timing is tightly coupled to a recent change and rollback restored service.",
        },
    },
    {
        "input": "Network is slow.",
        "output": {
            "primary_class": "insufficient_information",
            "subtype": "vague_description",
            "confidence": 18,
            "change_induced": False,
            "suspected_contributing_factor": None,
            "ambiguity_notes": None,
            "missing_facts": ["scope of impact", "wired vs wireless", "apps affected", "timing", "recent changes"],
            "diagnostic_path": [
                "determine whether the issue is local, site-wide, or multi-site",
                "identify whether wired, wireless, or both are affected",
                "capture a concrete symptom such as packet loss, auth failure, or outage",
            ],
            "reasoning": "The description is too vague to classify safely.",
        },
    },
]

DEFAULT_MISSING_FACTS = {
    "wan_upstream": ["edge router BGP state", "circuit alarms", "carrier notifications"],
    "wireless": ["affected AP or controller alarms", "SSID scope", "DHCP health for wireless clients"],
    "auth_802_1x": ["RADIUS or ISE server health", "authentication failure reason", "certificate validity"],
    "routing_switching": ["impacted VLAN or subnet", "switch or route state", "topology or port-change history"],
    "circuit_carrier": ["interface errors", "latency or packet-loss trend", "carrier maintenance status"],
    "change_induced_config_drift": ["recent change list", "config diff from known-good state", "rollback status"],
    "insufficient_information": ["scope of impact", "wired vs wireless", "recent changes", "specific symptoms", "timing"],
}

DEFAULT_DIAGNOSTIC_PATH = {
    "wan_upstream": [
        "verify edge router and upstream reachability",
        "check BGP neighbors and route withdrawals",
        "confirm circuit or carrier status",
    ],
    "wireless": [
        "check wireless controller and AP health",
        "verify the affected SSID is available",
        "confirm DHCP and client onboarding on the wireless path",
    ],
    "auth_802_1x": [
        "check RADIUS or ISE service health",
        "verify whether clients are failing during authentication",
        "review recent AAA policy or certificate changes",
    ],
    "routing_switching": [
        "inspect switch and routing adjacencies in the impacted area",
        "check for VLAN, STP, or trunk issues",
        "contain unstable ports or loops before wider recovery",
    ],
    "circuit_carrier": [
        "inspect circuit and interface error counters",
        "compare latency, jitter, and packet loss with baseline",
        "confirm carrier-side maintenance or degradation",
    ],
    "change_induced_config_drift": [
        "identify the recent change touching the affected path",
        "compare current device state with known-good config",
        "validate rollback or targeted remediation",
    ],
    "insufficient_information": [
        "determine scope of impact",
        "confirm whether wired, wireless, or both are affected",
        "capture one concrete symptom before classifying",
    ],
}

WAN_HINT_PATTERNS = (
    re.compile(r"\bbgp\b", re.I),
    re.compile(r"\bupstream\b", re.I),
    re.compile(r"\bedge router\b", re.I),
    re.compile(r"\bcarrier outage\b", re.I),
    re.compile(r"\bwan\b", re.I),
    re.compile(r"\btraceroute\b", re.I),
)
WIRELESS_HINT_PATTERNS = (
    re.compile(r"\bwifi\b", re.I),
    re.compile(r"\bwireless\b", re.I),
    re.compile(r"\bssid\b", re.I),
    re.compile(r"\baccess point\b|\bap\b", re.I),
    re.compile(r"\broaming\b", re.I),
    re.compile(r"\bcontroller\b", re.I),
)
AUTH_HINT_PATTERNS = (
    re.compile(r"\b802\.1x\b", re.I),
    re.compile(r"\bradius\b", re.I),
    re.compile(r"\bise\b", re.I),
    re.compile(r"\bauth(?:entication)?\b", re.I),
    re.compile(r"\bcertificate\b", re.I),
    re.compile(r"\bcannot get\b.{0,20}\bip\b", re.I),
)
ROUTING_HINT_PATTERNS = (
    re.compile(r"\bospf\b", re.I),
    re.compile(r"\bspanning tree\b|\bstp\b", re.I),
    re.compile(r"\bvlan\b", re.I),
    re.compile(r"\btrunk\b", re.I),
    re.compile(r"\bbroadcast storm\b|\bnetwork loop\b|\bloop\b", re.I),
    re.compile(r"\broute(?:ing)? table\b", re.I),
    re.compile(r"\bport-?channel\b", re.I),
    re.compile(r"\bswitch cpu\b", re.I),
)
CIRCUIT_HINT_PATTERNS = (
    re.compile(r"\bpacket loss\b", re.I),
    re.compile(r"\bhigh latency\b|\blatency\b", re.I),
    re.compile(r"\bjitter\b", re.I),
    re.compile(r"\bcrc errors?\b", re.I),
    re.compile(r"\binterface flapping\b|\bflapping\b", re.I),
    re.compile(r"\bcircuit\b", re.I),
    re.compile(r"\bcarrier maintenance\b|\bprovider maintenance\b", re.I),
)
CHANGE_HINT_PATTERNS = (
    re.compile(r"\bworked (?:yesterday|before|previously)\b", re.I),
    re.compile(r"\bstarted after\b", re.I),
    re.compile(r"\bafter (?:the )?(?:change|maintenance|deployment|rollout|upgrade)\b", re.I),
    re.compile(r"\brollback\b", re.I),
    re.compile(r"\bconfig(?:uration)?\b.{0,20}\b(?:drift|mismatch|change)\b", re.I),
    re.compile(r"\bfirmware\b", re.I),
)
VAGUE_PATTERNS = (
    re.compile(r"^\s*network is slow\.?\s*$", re.I),
    re.compile(r"^\s*internet not working\.?\s*$", re.I),
    re.compile(r"^\s*something is wrong\.?\s*$", re.I),
    re.compile(r"^\s*cannot connect\.?\s*$", re.I),
)

SUBTYPE_HINTS: dict[str, tuple[tuple[re.Pattern[str], str], ...]] = {
    "wan_upstream": (
        (re.compile(r"\bbgp\b|\bneighbor down\b", re.I), "bgp_session_drop"),
        (re.compile(r"\bcircuit down\b|\boutage\b", re.I), "circuit_down"),
        (re.compile(r"\bupstream\b|\bprovider\b", re.I), "upstream_provider_fault"),
        (re.compile(r"\bmpls\b", re.I), "mpls_path_failure"),
        (re.compile(r"\brouting loop\b", re.I), "routing_loop"),
        (re.compile(r"\bblackhole\b|\broute withdrawals?\b|\bedge policy\b", re.I), "edge_path_blackhole"),
    ),
    "wireless": (
        (re.compile(r"\bssid\b.{0,20}(missing|not visible)", re.I), "ssid_missing"),
        (re.compile(r"\bcontroller\b", re.I), "wireless_controller_unreachable"),
        (re.compile(r"\bdhcp\b", re.I), "dhcp_scope_exhausted"),
        (re.compile(r"\broaming\b", re.I), "roaming_failure"),
        (re.compile(r"\bap\b|\baccess point\b", re.I), "ap_down"),
    ),
    "auth_802_1x": (
        (re.compile(r"\bradius\b", re.I), "radius_server_down"),
        (re.compile(r"\bcertificate\b|\bcert\b", re.I), "certificate_expired"),
        (re.compile(r"\bise\b", re.I), "ise_policy_failure"),
        (re.compile(r"\b802\.1x\b|\bdot1x\b", re.I), "dot1x_negotiation_failure"),
    ),
    "routing_switching": (
        (re.compile(r"\bbroadcast storm\b|\bnetwork loop\b|\bspanning tree\b", re.I), "spanning_tree_loop"),
        (re.compile(r"\bospf\b", re.I), "ospf_adjacency_drop"),
        (re.compile(r"\bvlan\b", re.I), "vlan_missing"),
        (re.compile(r"\bport-?channel\b", re.I), "port_channel_failure"),
    ),
    "circuit_carrier": (
        (re.compile(r"\bcrc errors?\b", re.I), "crc_errors"),
        (re.compile(r"\bcarrier maintenance\b", re.I), "carrier_maintenance"),
        (re.compile(r"\bjitter\b|\blatency\b", re.I), "latency_jitter"),
        (re.compile(r"\bpacket loss\b", re.I), "packet_loss_intermittent"),
        (re.compile(r"\bflapping\b", re.I), "interface_flapping"),
    ),
    "change_induced_config_drift": (
        (re.compile(r"\brollback\b", re.I), "rollback_required"),
        (re.compile(r"\bfirmware\b", re.I), "firmware_regression"),
        (re.compile(r"\bmismatch\b", re.I), "interface_config_mismatch"),
        (re.compile(r"\bpolicy\b|\bfirewall rule\b|\bacl\b", re.I), "routing_policy_error"),
    ),
}


class ClassifierResult(TypedDict):
    primary_class: str
    subtype: Optional[str]
    confidence: int
    change_induced: bool
    suspected_contributing_factor: Optional[str]
    ambiguity_notes: Optional[str]
    missing_facts: list[str]
    diagnostic_path: list[str]
    reasoning: str
    symptoms: list[str]


def _strip_code_fences(raw: str) -> str:
    if raw.startswith("```"):
        return re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return raw


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _coerce_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return default


def _normalize_optional_text(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_text_list(value: object, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(cleaned)
        if len(items) >= limit:
            break
    return items


def _looks_vague(text: str, regex_facts: ExtractedFacts, llm_facts: LlmExtractedFacts) -> bool:
    stripped = text.strip()
    if not stripped:
        return True

    if any(pattern.match(stripped) for pattern in VAGUE_PATTERNS):
        return True

    signal_count = sum(
        [
            regex_facts.is_multi_site,
            regex_facts.is_wireless_only,
            regex_facts.has_auth_signals,
            regex_facts.has_change_signals,
            regex_facts.internal_unreachable,
            regex_facts.internet_affected,
            bool(llm_facts.get("explicit_layer")),
        ]
    )
    return len(stripped.split()) < 5 and signal_count == 0


def _match_count(text: str, patterns: tuple[re.Pattern[str], ...]) -> int:
    return sum(1 for pattern in patterns if pattern.search(text))


def _score_classes(
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
) -> dict[str, int]:
    lower = text.lower()
    scores = {
        "wan_upstream": 0,
        "wireless": 0,
        "auth_802_1x": 0,
        "routing_switching": 0,
        "circuit_carrier": 0,
        "change_induced_config_drift": 0,
    }

    scores["wan_upstream"] += _match_count(lower, WAN_HINT_PATTERNS) * 2
    scores["wireless"] += _match_count(lower, WIRELESS_HINT_PATTERNS) * 2
    scores["auth_802_1x"] += _match_count(lower, AUTH_HINT_PATTERNS) * 2
    scores["routing_switching"] += _match_count(lower, ROUTING_HINT_PATTERNS) * 2
    scores["circuit_carrier"] += _match_count(lower, CIRCUIT_HINT_PATTERNS) * 2
    scores["change_induced_config_drift"] += _match_count(lower, CHANGE_HINT_PATTERNS) * 2

    if regex_facts.has_auth_signals:
        scores["auth_802_1x"] += 6
    if regex_facts.is_wireless_only:
        scores["wireless"] += 7
    if regex_facts.wired_unaffected:
        scores["wireless"] += 3
    if regex_facts.has_change_signals:
        scores["change_induced_config_drift"] += 4
    if change_window:
        scores["change_induced_config_drift"] += 1
    if regex_facts.is_multi_site:
        scores["wan_upstream"] += 6
        scores["auth_802_1x"] += 2
    if regex_facts.internal_unreachable:
        scores["wan_upstream"] += 4
    if regex_facts.internet_affected:
        scores["wan_upstream"] += 2
        scores["circuit_carrier"] += 2
    if regex_facts.has_timing_reference and regex_facts.has_change_signals:
        scores["change_induced_config_drift"] += 1

    explicit_layer = (llm_facts.get("explicit_layer") or "").lower()
    if any(token in explicit_layer for token in ("radius", "ise", "802.1x", "dot1x", "certificate")):
        scores["auth_802_1x"] += 5
    if "bgp" in explicit_layer:
        scores["wan_upstream"] += 4
    if any(token in explicit_layer for token in ("ospf", "spanning tree", "vlan")):
        scores["routing_switching"] += 5
    if "dhcp" in explicit_layer:
        scores["wireless"] += 2
    if any(token in explicit_layer for token in ("carrier", "circuit")):
        scores["circuit_carrier"] += 4

    return scores


def _fallback_symptoms(text: str, regex_facts: ExtractedFacts, llm_facts: LlmExtractedFacts) -> list[str]:
    lower = text.lower()
    symptoms = list(llm_facts.get("symptoms", [])) + list(regex_facts.symptoms)

    keyword_symptoms = [
        ("packet loss", "packet loss observed"),
        ("jitter", "jitter reported"),
        ("latency", "latency degradation reported"),
        ("broadcast storm", "broadcast storm reported"),
        ("cannot authenticate", "users cannot authenticate"),
        ("cannot connect to wifi", "users cannot connect to wifi"),
        ("ssid", "SSID visibility issue reported"),
        ("internal systems", "internal systems unreachable"),
        ("wireless appears fine", "wireless appears fine"),
    ]

    for keyword, label in keyword_symptoms:
        if keyword in lower:
            symptoms.append(label)

    deduped: list[str] = []
    seen: set[str] = set()
    for symptom in symptoms:
        cleaned = symptom.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
        if len(deduped) >= 5:
            break

    return deduped


def _pick_subtype(primary_class: str, text: str) -> Optional[str]:
    if primary_class == "insufficient_information":
        return "vague_description"

    for pattern, subtype in SUBTYPE_HINTS.get(primary_class, ()):
        if pattern.search(text):
            return subtype
    return None


def _suspected_factor(
    primary_class: str,
    change_induced: bool,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
) -> Optional[str]:
    explicit_layer = llm_facts.get("explicit_layer")
    if primary_class == "wan_upstream" and change_induced:
        return "recent change may have impacted a shared WAN or edge dependency"
    if change_induced and primary_class == "change_induced_config_drift":
        return "recent configuration or maintenance activity likely introduced the issue"

    factors = {
        "wan_upstream": "shared upstream dependency across affected sites",
        "wireless": "wireless infrastructure fault isolated from the wired path",
        "auth_802_1x": "centralized authentication dependency failure",
        "routing_switching": "campus switching or routing instability",
        "circuit_carrier": "provider-side circuit degradation",
        "change_induced_config_drift": "recent configuration drift or rollback candidate",
    }

    if explicit_layer:
        return f"{factors.get(primary_class, 'network domain issue')} with explicit {explicit_layer} signals"
    if primary_class == "wan_upstream" and regex_facts.is_multi_site:
        return "multi-site impact suggests a shared WAN dependency"
    return factors.get(primary_class)


def _build_reasoning(
    primary_class: str,
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
) -> str:
    explicit_layer = llm_facts.get("explicit_layer")
    evidence: list[str] = []

    if primary_class == "wan_upstream":
        if regex_facts.is_multi_site:
            evidence.append(f"impact spans about {regex_facts.sites_count_estimate} sites")
        if regex_facts.internal_unreachable or regex_facts.internet_affected:
            evidence.append("shared reachability loss is present")
    elif primary_class == "wireless":
        if regex_facts.is_wireless_only:
            evidence.append("wireless is affected while wired appears unaffected")
        if "ssid" in text.lower():
            evidence.append("SSID-specific symptoms are mentioned")
    elif primary_class == "auth_802_1x":
        if regex_facts.has_auth_signals:
            evidence.append("authentication and RADIUS signals are explicit")
        if regex_facts.is_multi_site:
            evidence.append("multi-site scope fits a centralized AAA dependency")
    elif primary_class == "routing_switching":
        if re.search(r"\b(spanning tree|broadcast storm|vlan|ospf|trunk)\b", text, re.I):
            evidence.append("campus L2/L3 failure signals are present")
    elif primary_class == "circuit_carrier":
        if re.search(r"\b(packet loss|latency|jitter|crc|carrier)\b", text, re.I):
            evidence.append("the issue looks like degradation on a live circuit")
    elif primary_class == "change_induced_config_drift":
        if regex_facts.has_change_signals or change_window:
            evidence.append("the incident is tightly coupled to a recent change window")

    if explicit_layer:
        evidence.append(f"the text explicitly mentions {explicit_layer}")

    if not evidence:
        if primary_class == "insufficient_information":
            return "The description does not contain enough concrete scope or symptom detail to classify safely."
        return f"The available signals align best with {primary_class.replace('_', ' ')}."

    lead = "; ".join(evidence[:2])
    if primary_class == "insufficient_information":
        return f"{lead.capitalize()}, but the overall description is still too ambiguous to classify safely."
    return f"{lead.capitalize()}, so {primary_class.replace('_', ' ')} is the best fit."


def _build_ambiguity_note(
    primary_class: str,
    secondary_class: str,
    score_gap: int,
    regex_facts: ExtractedFacts,
) -> Optional[str]:
    if score_gap > 1 or secondary_class == "insufficient_information":
        return None

    if primary_class == "wan_upstream" and secondary_class == "auth_802_1x" and regex_facts.has_auth_signals:
        return "There are both multi-site and auth signals; auth_802_1x remained a close alternative."
    if primary_class == "wan_upstream" and secondary_class == "change_induced_config_drift":
        return "Recent change correlation is plausible, but the primary technical failure domain still appears to be a shared WAN or upstream dependency."
    if primary_class == "change_induced_config_drift":
        return f"{secondary_class.replace('_', ' ')} remains a close alternative if the change signal is incidental."
    return f"{secondary_class.replace('_', ' ')} was also plausible, but the stronger signal set favored {primary_class.replace('_', ' ')}."


def _filter_known_missing_facts(
    facts: list[str],
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
) -> list[str]:
    lower = text.lower()
    filtered: list[str] = []

    for fact in facts:
        f = fact.lower()

        if ("wired" in f or "wireless" in f) and regex_facts.is_wireless_only:
            if "wired" in f:
                continue

        if ("recent change" in f or "change window" in f or "time correlation" in f) and (
            regex_facts.change_window_mentioned or regex_facts.has_change_signals
        ):
            continue

        if ("radius" in f or "authentication" in f) and regex_facts.has_auth_signals:
            if "health" not in f and "logs" not in f and "reason" not in f and "server" not in f:
                continue

        if ("site" in f or "scope" in f) and (regex_facts.is_multi_site or regex_facts.raw_site_names):
            continue

        if "internal" in f and regex_facts.internal_unreachable:
            continue

        if "internet" in f and regex_facts.internet_affected:
            continue

        if f in lower:
            continue

        filtered.append(fact)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in filtered:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 5:
            break

    return deduped


def _build_result(
    primary_class: str,
    confidence: int,
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
    ambiguity_notes: Optional[str] = None,
) -> ClassifierResult:
    clamped_confidence = max(0, min(100, confidence))
    if clamped_confidence < 60:
        primary_class = "insufficient_information"

    change_induced = bool(regex_facts.has_change_signals or (primary_class == "change_induced_config_drift"))
    subtype = _pick_subtype(primary_class, text)
    symptoms = _fallback_symptoms(text, regex_facts, llm_facts)

    missing_facts = _filter_known_missing_facts(
        DEFAULT_MISSING_FACTS[primary_class][:5],
        text,
        regex_facts,
        llm_facts,
    )
    if not missing_facts:
        missing_facts = DEFAULT_MISSING_FACTS[primary_class][:5]

    return {
        "primary_class": primary_class,
        "subtype": subtype,
        "confidence": clamped_confidence,
        "change_induced": change_induced,
        "suspected_contributing_factor": _suspected_factor(primary_class, change_induced, regex_facts, llm_facts),
        "ambiguity_notes": ambiguity_notes,
        "missing_facts": missing_facts,
        "diagnostic_path": DEFAULT_DIAGNOSTIC_PATH[primary_class][:5],
        "reasoning": _build_reasoning(primary_class, text, regex_facts, llm_facts, change_window),
        "symptoms": symptoms,
    }


def _heuristic_classify(
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
) -> ClassifierResult:
    if _looks_vague(text, regex_facts, llm_facts):
        return _build_result("insufficient_information", 25, text, regex_facts, llm_facts, change_window)

    scores = _score_classes(text, regex_facts, llm_facts, change_window)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    primary_class, top_score = ranked[0]
    secondary_class, secondary_score = ranked[1]

    if top_score < 4:
        ambiguity = _build_ambiguity_note(primary_class, secondary_class, top_score - secondary_score, regex_facts)
        return _build_result("insufficient_information", 40, text, regex_facts, llm_facts, change_window, ambiguity)

    confidence = min(92, 56 + (top_score * 4))
    score_gap = top_score - secondary_score
    if score_gap <= 1:
        confidence -= 10
    if primary_class == "change_induced_config_drift" and not (regex_facts.has_change_signals or change_window):
        confidence -= 8
    if primary_class == "change_induced_config_drift" and regex_facts.is_multi_site:
        confidence -= 8
    if primary_class == "wireless" and regex_facts.is_wireless_only:
        confidence += 4

    ambiguity = _build_ambiguity_note(primary_class, secondary_class, score_gap, regex_facts)
    return _build_result(primary_class, confidence, text, regex_facts, llm_facts, change_window, ambiguity)


def _build_system_prompt() -> str:
    taxonomy_summary: list[str] = []
    for key, cls in TAXONOMY_CLASSES.items():
        signal_keywords = "; ".join(cls.get("signal_keywords", [])[:4]) or "none"
        subtypes = ", ".join(cls.get("subtypes", [])[:4]) or "none"
        taxonomy_summary.append(
            "\n".join(
                [
                    f"  {key}: {cls['label']}",
                    f"    Description: {cls['description'][:220].strip()}",
                    f"    Signal keywords: {signal_keywords}",
                    f"    Example subtypes: {subtypes}",
                    f"    Typical Tier 3 reason: {cls.get('typical_tier3_reason', 'unknown')}",
                ]
            )
        )

    return f"""You are a network incident classifier for Amazon's Office Network Reliability Engineering (ONRE) team.

You classify free-text OMC escalation summaries into one of 7 failure domains.

TAXONOMY:
{chr(10).join(taxonomy_summary)}

TIE-BREAK RULES:
{chr(10).join(f"  - {rule}" for rule in TIE_BREAK_RULES)}

OUTPUT REQUIREMENTS:
- Return ONLY valid JSON. No markdown, no explanation, no preamble.
- confidence: integer 0-100 reflecting how certain you are
- If confidence < 60, set primary_class to "insufficient_information"
- missing_facts: what the OMC engineer should gather next (max 5 items)
- Do not include facts already present in the incident text or extracted context in missing_facts.
- diagnostic_path: ordered first checks for this failure class (max 5 steps, operationally specific)
- reasoning: one or two sentences explaining why you chose this class

Return this exact JSON structure:
{{
  "primary_class": "one of the 7 taxonomy keys",
  "subtype": "specific subtype or null",
  "confidence": 0-100,
  "change_induced": true or false,
  "suspected_contributing_factor": "one phrase or null",
  "ambiguity_notes": "if you considered another class, say which and why you rejected it, or null",
  "missing_facts": ["list", "of", "missing", "facts"],
  "diagnostic_path": ["step 1", "step 2", "step 3"],
  "reasoning": "one or two sentences"
}}"""


def _build_user_prompt(
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
) -> str:
    context_lines = []

    if regex_facts.is_multi_site:
        context_lines.append(f"- Multi-site impact detected (estimated {regex_facts.sites_count_estimate} sites)")
    if regex_facts.wired_unaffected:
        context_lines.append("- Wired users appear unaffected")
    if regex_facts.is_wireless_only:
        context_lines.append("- Wireless-specific outage signal is present")
    if regex_facts.has_auth_signals:
        context_lines.append("- Authentication or RADIUS signals detected in text")
    if regex_facts.change_window_mentioned or change_window:
        context_lines.append("- A recent change window is likely relevant")
    if regex_facts.has_change_signals:
        context_lines.append("- Change-induced language detected")
    if regex_facts.internal_unreachable:
        context_lines.append("- Internal systems appear unreachable")
    if regex_facts.internet_affected:
        context_lines.append("- Internet or external access appears affected")
    if regex_facts.timing_clue:
        context_lines.append(f"- Timing clue: {regex_facts.timing_clue}")
    if regex_facts.raw_site_names:
        context_lines.append(f"- Site names mentioned: {', '.join(regex_facts.raw_site_names)}")
    if llm_facts.get("explicit_layer"):
        context_lines.append(f"- Explicit protocol or layer mentioned: {llm_facts['explicit_layer']}")
    if llm_facts.get("affected_services"):
        context_lines.append(f"- Affected services: {', '.join(llm_facts['affected_services'][:3])}")
    if llm_facts.get("scope_qualifier"):
        context_lines.append(f"- Scope qualifier: {llm_facts['scope_qualifier']}")
    if llm_facts.get("symptoms"):
        context_lines.append(f"- Observable symptoms: {', '.join(llm_facts['symptoms'][:4])}")

    context_block = "\n".join(context_lines) if context_lines else "No additional context extracted."

    few_shot_block = ""
    for example in FEW_SHOT_EXAMPLES:
        few_shot_block += (
            f'\nIncident: "{example["input"]}"\n'
            f'Output: {json.dumps(example["output"])}\n'
        )

    return f"""Classify this incident:

Incident text: "{text}"

Pre-extracted context:
{context_block}

Examples of correct classification:
{few_shot_block}

Now classify the incident above. Return only JSON."""


def _call_llm_classifier(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        max_tokens=800,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = _strip_code_fences((response.choices[0].message.content or "").strip())
    return json.loads(raw)


def _normalize_result(
    payload: dict[str, Any],
    fallback: ClassifierResult,
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None,
) -> ClassifierResult:
    result: ClassifierResult = {
        "primary_class": fallback["primary_class"],
        "subtype": fallback["subtype"],
        "confidence": fallback["confidence"],
        "change_induced": fallback["change_induced"],
        "suspected_contributing_factor": fallback["suspected_contributing_factor"],
        "ambiguity_notes": fallback["ambiguity_notes"],
        "missing_facts": list(fallback["missing_facts"]),
        "diagnostic_path": list(fallback["diagnostic_path"]),
        "reasoning": fallback["reasoning"],
        "symptoms": list(fallback["symptoms"]),
    }

    primary_class = payload.get("primary_class")
    if isinstance(primary_class, str) and primary_class in VALID_CLASSES:
        result["primary_class"] = primary_class

    result["confidence"] = max(0, min(100, _coerce_int(payload.get("confidence"), result["confidence"])))
    result["change_induced"] = _coerce_bool(payload.get("change_induced"), result["change_induced"]) or fallback["change_induced"]
    result["suspected_contributing_factor"] = (
        _normalize_optional_text(payload.get("suspected_contributing_factor"))
        or result["suspected_contributing_factor"]
    )
    result["ambiguity_notes"] = _normalize_optional_text(payload.get("ambiguity_notes")) or result["ambiguity_notes"]

    candidate_missing_facts = _normalize_text_list(payload.get("missing_facts")) or result["missing_facts"]
    filtered_missing_facts = _filter_known_missing_facts(
        candidate_missing_facts,
        text,
        regex_facts,
        llm_facts,
    )
    result["missing_facts"] = filtered_missing_facts or result["missing_facts"]

    result["diagnostic_path"] = _normalize_text_list(payload.get("diagnostic_path")) or result["diagnostic_path"]
    result["reasoning"] = _normalize_optional_text(payload.get("reasoning")) or result["reasoning"]

    candidate_subtype = _normalize_optional_text(payload.get("subtype"))
    valid_subtypes = set(TAXONOMY_CLASSES.get(result["primary_class"], {}).get("subtypes", []))
    if candidate_subtype and (not valid_subtypes or candidate_subtype in valid_subtypes):
        result["subtype"] = candidate_subtype
    elif result["primary_class"] == "insufficient_information":
        result["subtype"] = "vague_description"
    elif result["primary_class"] != fallback["primary_class"]:
        result["subtype"] = _pick_subtype(result["primary_class"], text)

    if result["confidence"] < 60:
        result["primary_class"] = "insufficient_information"
        result["subtype"] = "vague_description"

    result["reasoning"] = result["reasoning"] or _build_reasoning(
        result["primary_class"], text, regex_facts, llm_facts, change_window
    )
    return result


def classify(
    text: str,
    regex_facts: ExtractedFacts,
    llm_facts: LlmExtractedFacts,
    change_window: bool | None = None,
) -> ClassifierResult:
    fallback = _heuristic_classify(text, regex_facts, llm_facts, change_window)

    if not settings.openai_api_key or settings.openai_api_key == "your-key-here":
        return fallback

    try:
        result = _call_llm_classifier(
            _build_system_prompt(),
            _build_user_prompt(text, regex_facts, llm_facts, change_window),
        )
        return _normalize_result(result, fallback, text, regex_facts, llm_facts, change_window)
    except Exception as exc:
        logger.warning("LLM classification failed; using heuristic fallback: %s", exc)
        return fallback