from fastapi import APIRouter
from typing import List, Optional
from app.services import postgres_service as db_service
from app.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/api/v1/public/alerts", response_model=List[dict])
async def get_public_alerts(
    geohash: Optional[str] = None,
    district_code: Optional[int] = None,
    district: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Public feed of active alerts.
    
    Filter options (choose one):
    - district_code: LGD district code (most efficient)
    - district + state: Text-based matching (fallback)
    - geohash: Geohash prefix for hyper-local filtering
    """
    return await db_service.get_alerts(
        geohash=geohash, 
        district_code=district_code,
        district_name=district,
        state_name=state,
        status='ACTIVE', 
        limit=50
    )
