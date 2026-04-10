from fastapi import APIRouter
import yaml
from app.core.config import settings

router = APIRouter()

@router.get("/taxonomy")
def get_taxonomy():
    with open(settings.taxonomy_path) as f:
        return yaml.safe_load(f)
