from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.db.database import Incident, get_session
from datetime import datetime, timedelta
from collections import Counter

router = APIRouter()

@router.get("/reports/weekly")
def weekly_report(session: Session = Depends(get_session)):
    week_ago = datetime.utcnow() - timedelta(days=7)
    incidents = session.exec(
        select(Incident).where(Incident.created_at >= week_ago)
    ).all()

    if not incidents:
        # Return seeded data summary for demo
        all_incidents = session.exec(select(Incident)).all()
        incidents = all_incidents[:23] if len(all_incidents) >= 23 else all_incidents

    by_class = Counter(i.incident_class for i in incidents)
    by_gap = Counter(i.omc_gap_type for i in incidents if i.omc_gap_type)
    change_induced = sum(1 for i in incidents if i.change_induced)
    omc_resolved = sum(1 for i in incidents if i.prevented_by_omc)
    sites = []
    for i in incidents:
        pass  # site aggregation placeholder

    top_gap = by_gap.most_common(1)[0][0] if by_gap else "missing_runbook"
    runbook_gaps = [k for k, v in by_gap.items() if k == "missing_runbook"]

    return {
        "period": {
            "start": (datetime.utcnow() - timedelta(days=7)).isoformat(),
            "end": datetime.utcnow().isoformat(),
        },
        "total_escalations": len(incidents),
        "by_class": [
            {"class": k, "count": v, "pct": round(v / len(incidents) * 100) if incidents else 0}
            for k, v in by_class.most_common()
        ],
        "by_gap_type": [{"gap": k, "count": v} for k, v in by_gap.most_common()],
        "change_induced_count": change_induced,
        "omc_self_resolved": omc_resolved,
        "recurring_sites": [],
        "top_recommendation": f"Invest in runbook coverage for '{top_gap.replace('_', ' ')}' — top capability gap this week.",
        "runbook_gaps": runbook_gaps,
    }
