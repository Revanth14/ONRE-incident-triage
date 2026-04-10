from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.db.database import Incident, get_session
from app.schemas.incident import IncidentRead
from typing import Optional

router = APIRouter()

@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    incident_class: Optional[str] = None,
    omc_gap_type: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
    session: Session = Depends(get_session),
):
    q = select(Incident)
    if incident_class:
        q = q.where(Incident.incident_class == incident_class)
    if omc_gap_type:
        q = q.where(Incident.omc_gap_type == omc_gap_type)
    if region:
        q = q.where(Incident.region == region)
    q = q.order_by(Incident.created_at.desc()).limit(limit)
    return session.exec(q).all()


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: str, session: Session = Depends(get_session)):
    inc = session.exec(select(Incident).where(Incident.incident_id == incident_id)).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc
