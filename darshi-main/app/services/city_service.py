from typing import List, Dict, Any, Optional
from app.services import postgres_service
from app.core.exceptions import NotFoundError, ValidationError

async def get_all_cities() -> List[Dict[str, Any]]:
    """Get all supported cities."""
    return await postgres_service.get_cities(active_only=True)

async def get_city(city_id: str) -> Dict[str, Any]:
    """Get a specific city."""
    city = await postgres_service.get_city_by_id(city_id)
    if not city:
        raise NotFoundError("City not found")
    return city

async def find_nearest_city(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Find nearest supported city."""
    # Validate coordinates
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise ValidationError("Invalid coordinates")
        
    return await postgres_service.find_nearest_city_db(lat, lng)
