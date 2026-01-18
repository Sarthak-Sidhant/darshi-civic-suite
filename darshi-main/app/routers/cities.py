from fastapi import APIRouter, Depends, Query, Path
from typing import List, Dict, Any, Optional
from app.services import city_service

router = APIRouter(
    prefix="/api/v1/cities",
    tags=["cities"]
)

@router.get("", response_model=List[Dict[str, Any]])
async def list_cities():
    """List all supported cities."""
    return await city_service.get_all_cities()

@router.get("/nearest", response_model=Dict[str, Any])
async def get_nearest_city(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude")
):
    """Find the nearest supported city to a location."""
    city = await city_service.find_nearest_city(lat, lng)
    if not city:
        return {"found": False, "message": "No supported city found nearby"}
    return {"found": True, "city": city}

@router.get("/{city_id}", response_model=Dict[str, Any])
async def get_city_details(
    city_id: str = Path(..., description="City ID")
):
    """Get details for a specific city."""
    return await city_service.get_city(city_id)
