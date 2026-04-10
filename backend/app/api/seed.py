from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db.database import Incident, get_session
from app.db.seed import seed_incidents

router = APIRouter()

@router.post("/seed")
def seed(session: Session = Depends(get_session)):
    count = seed_incidents(session)
    return {"seeded": count}
