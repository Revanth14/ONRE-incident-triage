from sqlmodel import SQLModel, create_engine, Session, Field
from typing import Optional
from datetime import datetime
from app.core.config import settings
import json

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    incident_id: str = Field(index=True, unique=True)
    raw_summary: str
    region: Optional[str] = None
    sites_affected_count: int = 1
    user_impact_estimate: int = 150
    incident_class: str
    subtype: Optional[str] = None
    confidence: int = 0
    change_window_flag: bool = False
    change_induced: bool = False
    ambiguous: bool = False
    diagnostic_steps: str = "[]"     # JSON array stored as string
    escalation_path: str = "omc_attempt"
    final_root_cause: Optional[str] = None
    final_resolution: Optional[str] = None
    prevented_by_omc: bool = False
    omc_gap_type: Optional[str] = None
    triage_response: Optional[str] = None  # full JSON response
    embedding: Optional[bytes] = None      # serialized numpy array
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    split: Optional[str] = None            # train | eval


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
