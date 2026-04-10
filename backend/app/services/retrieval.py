"""
Retrieval — Stage 3 of the pipeline.

Two-stage retrieval:
  Stage 1: metadata pre-filter (fast, cheap)
    - same incident class (required)
    - resolved incidents only (has root cause + resolution)
    - optional: same region, change window match
  Stage 2: embedding similarity (accurate)
    - embed query with sentence-transformers
    - cosine similarity against pre-filtered candidates
    - re-rank with metadata boosts

Why two-stage:
  Doing cosine similarity against all 70 incidents is trivial at this
  scale. But at production scale (10,000+ incidents), the pre-filter
  reduces the candidate set dramatically before the expensive embedding
  comparison. Building it correctly now demonstrates production thinking.

Embedding model: all-MiniLM-L6-v2
  - 384 dimensions, runs on CPU, ~22MB
  - Strong semantic similarity for short texts
  - Free, no API calls, deterministic output
"""

import json
import pickle
import numpy as np
from typing import Optional
from sqlmodel import Session, select
from app.db.database import Incident
from app.core.config import settings

# Lazy-load the model — only import when first used
_embedder = None

def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embedder


def embed_text(text: str) -> np.ndarray:
    """Embed a single text string. Returns float32 numpy array."""
    embedder = _get_embedder()
    return embedder.encode(text, normalize_embeddings=True).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two unit-normalized vectors."""
    # Vectors are already L2-normalized by encode(normalize_embeddings=True)
    return float(np.dot(a, b))


def serialize_embedding(vec: np.ndarray) -> bytes:
    return pickle.dumps(vec)


def deserialize_embedding(data: bytes) -> np.ndarray:
    return pickle.loads(data)


def _metadata_boost(
    candidate: Incident,
    query_class: str,
    change_window: Optional[bool],
    region: Optional[str],
    is_multi_site: bool,
) -> float:
    """
    Deterministic re-ranking boost based on metadata match.
    Applied after cosine similarity to adjust final ranking.
    """
    boost = 0.0

    # Same class is required (pre-filtered), no boost needed

    # Change window match
    if change_window is not None and candidate.change_window_flag == change_window:
        boost += 0.15

    # Same region
    if region and candidate.region == region:
        boost += 0.10

    # Multi-site scope match
    candidate_is_multi = candidate.sites_affected_count > 1
    if is_multi_site == candidate_is_multi:
        boost += 0.08

    # OMC self-resolved incidents are more useful for OMC engineers
    if candidate.prevented_by_omc:
        boost += 0.05

    return boost


def find_similar(
    query_text: str,
    query_class: str,
    session: Session,
    top_k: int = 3,
    change_window: Optional[bool] = None,
    region: Optional[str] = None,
    is_multi_site: bool = False,
) -> list[dict]:
    """
    Main retrieval entry point.
    Returns top-k similar past incidents with resolution notes.
    """
    # Stage 1: metadata pre-filter
    # Only retrieve resolved incidents in the same class
    candidates = session.exec(
        select(Incident).where(
            Incident.incident_class == query_class,
            Incident.final_root_cause.isnot(None),  # resolved
        )
    ).all()

    if not candidates:
        # Fallback: broaden to all resolved incidents
        candidates = session.exec(
            select(Incident).where(Incident.final_root_cause.isnot(None))
        ).all()

    if not candidates:
        return []

    # Embed query
    query_vec = embed_text(query_text)

    # Stage 2: similarity scoring
    scored = []
    for candidate in candidates:
        if candidate.embedding:
            try:
                cand_vec = deserialize_embedding(candidate.embedding)
                similarity = cosine_similarity(query_vec, cand_vec)
            except Exception:
                similarity = 0.3  # fallback if embedding is corrupt
        else:
            # Embed on-the-fly if not pre-computed (fallback)
            cand_vec = embed_text(candidate.raw_summary)
            similarity = cosine_similarity(query_vec, cand_vec)

        boost = _metadata_boost(candidate, query_class, change_window, region, is_multi_site)
        final_score = min(1.0, similarity + boost)

        scored.append((final_score, candidate))

    # Sort descending by final score
    scored.sort(key=lambda x: x[0], reverse=True)

    results = []
    for score, inc in scored[:top_k]:
        results.append({
            "incident_id": inc.incident_id,
            "summary": inc.raw_summary[:200],
            "incident_class": inc.incident_class,
            "root_cause": inc.final_root_cause or "Unknown",
            "resolution": inc.final_resolution or "Not documented",
            "similarity_score": round(score, 3),
            "change_induced": inc.change_induced,
        })

    return results


def precompute_embeddings(session: Session) -> int:
    """
    Pre-compute and store embeddings for all incidents without one.
    Called at startup. Returns number of incidents embedded.
    """
    incidents = session.exec(
        select(Incident).where(Incident.embedding.is_(None))
    ).all()

    count = 0
    for inc in incidents:
        try:
            vec = embed_text(inc.raw_summary)
            inc.embedding = serialize_embedding(vec)
            session.add(inc)
            count += 1
        except Exception:
            pass

    if count > 0:
        session.commit()

    return count
