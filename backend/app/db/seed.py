import json
from pathlib import Path
from sqlmodel import Session, select
from app.db.database import Incident
from app.core.config import settings


def seed_incidents(session: Session) -> int:
    existing = session.exec(select(Incident)).first()
    if existing:
        return 0

    with open(settings.INCIDENTS_PATH) as f:
        records = json.load(f)

    count = 0
    for r in records:
        inc = Incident(
            incident_id=r["incident_id"],
            raw_summary=r["raw_summary"],
            region=r.get("region"),
            sites_affected_count=r.get("sites_affected_count", 1),
            user_impact_estimate=r.get("user_impact_estimate", 150),
            incident_class=r["incident_class"],
            subtype=r.get("subtype"),
            confidence=r.get("confidence_expected", 0),
            change_window_flag=r.get("change_window_flag", False),
            change_induced=r.get("change_window_flag", False),
            ambiguous=r.get("ambiguous", False),
            final_root_cause=r.get("final_root_cause"),
            final_resolution=r.get("final_resolution"),
            prevented_by_omc=r.get("prevented_by_omc", False),
            omc_gap_type=r.get("omc_gap_type"),
            split=r.get("split"),
        )
        session.add(inc)
        count += 1

    session.commit()
    return count
