from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
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
    escalation_path: str = "omc_attempt"
    final_root_cause: Optional[str] = None
    final_resolution: Optional[str] = None
    prevented_by_omc: bool = False
    omc_gap_type: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None
    split: Optional[str] = None
