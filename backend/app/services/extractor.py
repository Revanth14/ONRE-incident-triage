import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional, TypedDict

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

CITY_PATTERN = (
    r"(?:austin|seattle|chicago|new(?:\s|-)?york|london|singapore|bangalore|"
    r"dublin|sydney|amsterdam|toronto|vancouver|mumbai)"
)

CHANGE_WINDOW_PATTERNS = [
    r"after.{0,30}(change|maintenance|window|update|upgrade|deployment|rollout)",
    r"(change|maintenance|window|upgrade|deployment).{0,30}(tonight|last night|this morning|yesterday)",
    r"started.{0,20}(after|during|following)",
    r"(post|post-)(change|maintenance|upgrade|deployment)",
    r"within.{0,15}(change|maintenance) window",
]

MULTI_SITE_PATTERNS = [
    r"\b(all|both|multiple|several|three|four|five|\d+)\s+(offices|sites|locations|buildings|branches|floors)\b",
    rf"\ball\s+{CITY_PATTERN}\s+(offices|sites|locations|buildings|branches)\b",
    r"\b(across|affecting)\b.{0,30}\b(offices|sites|locations)\b",
    rf"\b{CITY_PATTERN}\b.{0,50}\b{CITY_PATTERN}\b",
]

WIRED_UNAFFECTED_PATTERNS = [
    r"wired\s+(users?\s+)?(are\s+)?(fine|ok|unaffected|working)",
    r"(wired|ethernet).{0,20}(not affected|fine|working|unaffected)",
]

WIRELESS_HEALTHY_PATTERNS = [
    r"wireless appears fine",
    r"wifi appears fine",
    r"wireless works",
    r"wifi works",
]

WIRELESS_AFFECTED_PATTERNS = [
    r"wifi\s+(is\s+)?(down|not working|broken|affected)",
    r"wireless\s+(is\s+)?(down|not working|broken|affected)",
    r"cannot connect to wifi",
    r"ssid\s+(missing|not visible|gone)",
]

AUTH_PATTERNS = [
    r"\b(802\.1[xX]|radius|ise|certificate|cert|authentication|authenticat|dot1x)\b",
    r"(bouncing|keeps disconnecting|reconnect loop)",
    r"(cannot get|not getting|failed to get).{0,20}ip.{0,10}address",
]

CHANGE_INDUCED_PATTERNS = [
    r"(worked|working).{0,20}(yesterday|last week|before|previously)",
    r"(started after|since).{0,30}(change|maintenance|update|upgrade|deployment)",
    r"(issue|problem).{0,20}(appeared|started|began).{0,20}(after|when|following)",
    r"\brollback\b",
]

TIMING_PATTERNS = [
    r"(\d+)\s*(minutes?|mins?|hours?|hrs?)\s*ago",
    r"started\s+(at|around|about)\s+(\d{1,2}[:\.]?\d{0,2}\s*(?:am|pm)?)",
    r"(this morning|this afternoon|last night|tonight|yesterday)",
    r"(\d{1,2}:\d{2})\s*(am|pm)?",
]

USER_COUNT_PATTERNS = [
    r"\babout\s+(\d+)\s+users?\b",
    r"\baround\s+(\d+)\s+users?\b",
    r"\broughly\s+(\d+)\s+users?\b",
    r"\b(\d+)\s+users?\s+(?:affected|impacted)\b",
]


def _compile_patterns(patterns: list[str]) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.I) for pattern in patterns)


COMPILED_CHANGE_WINDOW_PATTERNS = _compile_patterns(CHANGE_WINDOW_PATTERNS)
COMPILED_MULTI_SITE_PATTERNS = _compile_patterns(MULTI_SITE_PATTERNS)
COMPILED_WIRED_UNAFFECTED_PATTERNS = _compile_patterns(WIRED_UNAFFECTED_PATTERNS)
COMPILED_WIRELESS_HEALTHY_PATTERNS = _compile_patterns(WIRELESS_HEALTHY_PATTERNS)
COMPILED_WIRELESS_AFFECTED_PATTERNS = _compile_patterns(WIRELESS_AFFECTED_PATTERNS)
COMPILED_AUTH_PATTERNS = _compile_patterns(AUTH_PATTERNS)
COMPILED_CHANGE_INDUCED_PATTERNS = _compile_patterns(CHANGE_INDUCED_PATTERNS)
COMPILED_TIMING_PATTERNS = _compile_patterns(TIMING_PATTERNS)
COMPILED_USER_COUNT_PATTERNS = _compile_patterns(USER_COUNT_PATTERNS)


class LlmExtractedFacts(TypedDict):
    symptoms: list[str]
    affected_services: list[str]
    scope_qualifier: Optional[str]
    severity_language: Optional[str]
    explicit_layer: Optional[str]


@dataclass
class ExtractedFacts:
    sites_count_estimate: int = 1
    users_count_estimate: Optional[int] = None
    is_multi_site: bool = False
    is_wireless_only: bool = False
    has_auth_signals: bool = False
    has_change_signals: bool = False
    has_timing_reference: bool = False

    change_window_mentioned: bool = False
    wired_unaffected: bool = False
    wireless_healthy: bool = False
    internal_unreachable: bool = False
    internet_affected: bool = False

    symptoms: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    scope_qualifier: Optional[str] = None
    timing_clue: Optional[str] = None
    raw_site_names: list[str] = field(default_factory=list)


def _empty_llm_facts() -> LlmExtractedFacts:
    return {
        "symptoms": [],
        "affected_services": [],
        "scope_qualifier": None,
        "severity_language": None,
        "explicit_layer": None,
    }


def _has_match(text: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def _dedupe(items: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
        if limit is not None and len(ordered) >= limit:
            break
    return ordered


def _extract_cities(text: str) -> list[str]:
    matches = re.findall(CITY_PATTERN, text, re.I)
    normalized = [re.sub(r"[-\s]+", " ", match).strip().title() for match in matches]
    return _dedupe(normalized)


def _extract_user_count(text: str) -> Optional[int]:
    for pattern in COMPILED_USER_COUNT_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def _count_sites(text: str) -> int:
    number_match = re.search(
        r"\b(two|three|four|five|six|seven|eight|nine|ten|\d+)\s+"
        r"(offices|sites|locations|buildings|branches|floors)\b",
        text,
        re.I,
    )
    if number_match:
        word_map = {
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        raw_value = number_match.group(1).lower()
        return word_map.get(raw_value, int(raw_value) if raw_value.isdigit() else 1)

    city_count = len(_extract_cities(text))
    if city_count >= 2:
        return city_count

    if re.search(
        rf"\ball\s+{CITY_PATTERN}\s+(offices|sites|locations|buildings|branches)\b",
        text,
        re.I,
    ):
        return 3

    if re.search(r"\b(all|multiple|several)\s+(offices|sites|locations|branches)\b", text, re.I):
        return 5

    return 1


def _extract_site_names(text: str) -> list[str]:
    hyphenated_sites = re.findall(r"\b[A-Z][a-z]+-[A-Za-z0-9]+\b", text)
    return _dedupe(hyphenated_sites + _extract_cities(text), limit=5)


def _strip_code_fences(raw: str) -> str:
    if raw.startswith("```"):
        return re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    return raw


def _normalize_optional_text(value: object) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_text_list(value: object, limit: int = 5) -> list[str]:
    if not isinstance(value, list):
        return []
    strings = [item for item in value if isinstance(item, str)]
    return _dedupe(strings, limit=limit)


def _normalize_llm_facts(payload: object) -> LlmExtractedFacts:
    if not isinstance(payload, dict):
        return _empty_llm_facts()

    return {
        "symptoms": _normalize_text_list(payload.get("symptoms")),
        "affected_services": _normalize_text_list(payload.get("affected_services")),
        "scope_qualifier": _normalize_optional_text(payload.get("scope_qualifier")),
        "severity_language": _normalize_optional_text(payload.get("severity_language")),
        "explicit_layer": _normalize_optional_text(payload.get("explicit_layer")),
    }


def regex_extract(text: str) -> ExtractedFacts:
    facts = ExtractedFacts()
    lower = text.lower()

    facts.sites_count_estimate = _count_sites(text)
    facts.users_count_estimate = _extract_user_count(text)
    facts.is_multi_site = _has_match(lower, COMPILED_MULTI_SITE_PATTERNS) or facts.sites_count_estimate > 1

    wireless_affected = _has_match(lower, COMPILED_WIRELESS_AFFECTED_PATTERNS)
    facts.wired_unaffected = _has_match(lower, COMPILED_WIRED_UNAFFECTED_PATTERNS)
    facts.wireless_healthy = _has_match(lower, COMPILED_WIRELESS_HEALTHY_PATTERNS)
    facts.is_wireless_only = wireless_affected and facts.wired_unaffected

    facts.has_auth_signals = _has_match(lower, COMPILED_AUTH_PATTERNS)

    facts.change_window_mentioned = _has_match(lower, COMPILED_CHANGE_WINDOW_PATTERNS)
    facts.has_change_signals = facts.change_window_mentioned or _has_match(
        lower, COMPILED_CHANGE_INDUCED_PATTERNS
    )

    facts.has_timing_reference = _has_match(lower, COMPILED_TIMING_PATTERNS)
    timing_match = re.search(
        r"(\d+\s*(?:minutes?|mins?|hours?|hrs?)\s*ago|this morning|this afternoon|last night|tonight|yesterday)",
        lower,
    )
    if timing_match:
        facts.timing_clue = timing_match.group(0)

    facts.internal_unreachable = bool(
        re.search(r"(internal|intranet|corporate).{0,30}(unreachable|down|not working|cannot reach)", lower)
    )
    facts.internet_affected = bool(
        re.search(r"(internet|external|web browsing).{0,20}(down|not working|affected)", lower)
    )

    facts.raw_site_names = _extract_site_names(text)

    if facts.is_wireless_only:
        facts.symptoms.append("wireless users affected while wired appears unaffected")
    if facts.wireless_healthy:
        facts.symptoms.append("wireless appears healthy")
    if facts.has_auth_signals:
        facts.symptoms.append("authentication failures reported")
    if facts.internal_unreachable:
        facts.symptoms.append("internal systems unreachable")
    if facts.internet_affected:
        facts.symptoms.append("internet access affected")
    if facts.users_count_estimate is not None:
        facts.symptoms.append(f"about {facts.users_count_estimate} users impacted")

    return facts


def llm_extract(text: str, regex_facts: ExtractedFacts) -> LlmExtractedFacts:
    if len(text.strip()) < 30:
        return _empty_llm_facts()

    client = OpenAI(api_key=settings.openai_api_key)

    signal_hints = [
        f"- multi-site detected: {'yes' if regex_facts.is_multi_site else 'no'}",
        f"- wireless-only signal: {'yes' if regex_facts.is_wireless_only else 'no'}",
        f"- wireless appears healthy: {'yes' if regex_facts.wireless_healthy else 'no'}",
        f"- authentication signal: {'yes' if regex_facts.has_auth_signals else 'no'}",
    ]
    if regex_facts.timing_clue:
        signal_hints.append(f"- timing clue already detected: {regex_facts.timing_clue}")
    if regex_facts.raw_site_names:
        signal_hints.append(f"- site names seen in text: {', '.join(regex_facts.raw_site_names)}")
    if regex_facts.users_count_estimate is not None:
        signal_hints.append(f"- approximate user count already detected: {regex_facts.users_count_estimate}")

    prompt = f"""Extract structured facts from this network incident description.
Return ONLY valid JSON, no explanation, no markdown.

Known signals from deterministic parsing:
{chr(10).join(signal_hints)}

Incident: {text}

Return this exact JSON structure:
{{
  "symptoms": ["list of specific observable symptoms, max 5"],
  "affected_services": ["list of affected applications or services mentioned"],
  "scope_qualifier": "one phrase describing scope: e.g. 'floor 3 only', 'all wired users', 'single conference room'",
  "severity_language": "any urgency words used: e.g. 'urgently', 'critical', 'complete outage'",
  "explicit_layer": "if user explicitly mentions a protocol or layer: e.g. 'BGP', 'DHCP', 'RADIUS', 'spanning tree', or null"
}}

Rules:
- symptoms must be observable facts, not diagnoses
- if a field has no content, return empty list or null
- do not infer or guess
- use the deterministic signals only as hints, and do not contradict the original text"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=400,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = _strip_code_fences((response.choices[0].message.content or "").strip())
        return _normalize_llm_facts(json.loads(raw))
    except Exception as exc:
        logger.warning("LLM extraction failed; falling back to regex-only facts: %s", exc)
        return _empty_llm_facts()


def extract(text: str) -> tuple[ExtractedFacts, LlmExtractedFacts]:
    regex_facts = regex_extract(text)

    if settings.openai_api_key and settings.openai_api_key != "your-key-here":
        llm_facts = llm_extract(text, regex_facts)
    else:
        llm_facts = _empty_llm_facts()

    return regex_facts, llm_facts