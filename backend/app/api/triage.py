"""
Triage endpoint — orchestrates the full pipeline:
  extractor → classifier → retrieval → recommender → response
"""

import time
import uuid
import json
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.schemas.triage import (
    TriageRequest, TriageResponse,
    IncidentClass, SimilarIncident,
)
from app.db.database import Incident, get_session
from app.services import extractor, classifier, retrieval, recommender

router = APIRouter()


@router.post("/triage", response_model=TriageResponse)
async def triage(req: TriageRequest, session: Session = Depends(get_session)):
    t0 = time.monotonic()
    incident_id = f"INC-{str(uuid.uuid4())[:8].upper()}"

    # ── Stage 1: Extract ──────────────────────────────────────────────────
    regex_facts, llm_facts = extractor.extract(req.raw_summary)

    # Merge change_window signal from request metadata
    change_window = req.change_window
    if regex_facts.change_window_mentioned and change_window is None:
        change_window = True

    # ── Stage 2: Classify ─────────────────────────────────────────────────
    clf = classifier.classify(
        text=req.raw_summary,
        regex_facts=regex_facts,
        llm_facts=llm_facts,
        change_window=change_window,
    )

    primary_class = clf.get("primary_class", "insufficient_information")
    confidence = int(clf.get("confidence", 20))
    change_induced = bool(clf.get("change_induced", False)) or bool(change_window)

    # Merge symptoms from LLM extractor + classifier
    symptoms = list(dict.fromkeys(
        llm_facts.get("symptoms", []) + clf.get("symptoms", [])
    ))[:6]

    # ── Stage 3: Retrieve similar incidents ───────────────────────────────
    similar_raw = retrieval.find_similar(
        query_text=req.raw_summary,
        query_class=primary_class,
        session=session,
        top_k=3,
        change_window=change_window,
        region=req.region,
        is_multi_site=regex_facts.is_multi_site,
    )

    similar_incidents = [
        SimilarIncident(
            incident_id=s["incident_id"],
            summary=s["summary"],
            incident_class=s["incident_class"],
            root_cause=s["root_cause"],
            resolution=s["resolution"],
            similarity_score=s["similarity_score"],
            change_induced=s["change_induced"],
        )
        for s in similar_raw
    ]

    # ── Stage 4: Rules engine ─────────────────────────────────────────────
    blast = recommender.compute_blast_radius(
        primary_class=primary_class,
        sites_count=len(req.sites_affected) if req.sites_affected else 1,
        is_multi_site=regex_facts.is_multi_site,
        regex_sites_count=regex_facts.sites_count_estimate,
    )

    escalation = recommender.compute_escalation(
        primary_class=primary_class,
        confidence=confidence,
        sites_count=blast.sites_count,
        users_estimate=blast.users_estimate,
        severity_override=req.severity,
    )

    omc_gap = recommender.infer_omc_gap(
        primary_class=primary_class,
        confidence=confidence,
        change_induced=change_induced,
    )

    # ── Persist to DB ─────────────────────────────────────────────────────
    inc = Incident(
        incident_id=incident_id,
        raw_summary=req.raw_summary,
        region=req.region,
        sites_affected_count=blast.sites_count,
        user_impact_estimate=blast.users_estimate,
        incident_class=primary_class,
        subtype=clf.get("subtype"),
        confidence=confidence,
        change_window_flag=bool(change_window),
        change_induced=change_induced,
        similar_incident_ids=json.dumps([s.incident_id for s in similar_incidents]),
        diagnostic_steps=json.dumps(clf.get("diagnostic_path", [])),
        escalation_path=escalation.recommendation.value,
        omc_gap_type=omc_gap.value if omc_gap else None,
    )
    session.add(inc)
    session.commit()

    latency_ms = int((time.monotonic() - t0) * 1000)

    # ── Build response ────────────────────────────────────────────────────
    return TriageResponse(
        incident_id=incident_id,
        primary_class=IncidentClass(primary_class),
        subtype=clf.get("subtype"),
        confidence=confidence,
        change_induced=change_induced,
        suspected_contributing_factor=clf.get("suspected_contributing_factor"),
        ambiguity_notes=clf.get("ambiguity_notes"),
        reasoning=clf.get("reasoning", ""),
        affected_scope=blast,
        symptoms=symptoms,
        missing_facts=clf.get("missing_facts", [])[:5],
        diagnostic_path=clf.get("diagnostic_path", [])[:5],
        similar_incidents=similar_incidents,
        escalation=escalation,
        omc_gap_type_candidate=omc_gap,
        latency_ms=latency_ms,
        mock=False,
    )
