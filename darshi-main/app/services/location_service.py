"""
Location Service
Handles geospatial logic for finding nearest municipalities and validation.
Uses Nominatim for reverse geocoding (GPS → city/district/state).
"""
import math
import httpx
from typing import Optional, Dict, List, Tuple
from app.services import postgres_service as db
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class LocationService:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
    
    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees) in kilometers.
        """
        # Convert decimal degrees to radians 
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a)) 
        r = 6371 # Radius of earth in kilometers
        return c * r

    async def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Reverse geocode GPS coordinates to get district, state using Nominatim.
        
        Returns:
            {
                "district": "Ranchi",
                "district_code": 339,
                "state": "Jharkhand",
                "country": "India",
                "address": "Full formatted address"
            }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    self.NOMINATIM_URL,
                    params={
                        "lat": lat,
                        "lon": lng,
                        "format": "json",
                        "addressdetails": 1,
                        "zoom": 10  # District level
                    },
                    headers={
                        "User-Agent": "Darshi/1.0 (civic platform)"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Nominatim error: {response.status_code}")
                    return None
                
                data = response.json()
                address = data.get("address", {})
                
                # Extract district (primary field from Nominatim)
                district = (
                    address.get("state_district") or
                    address.get("county") or
                    address.get("district") or
                    address.get("city") or
                    address.get("town")
                )
                
                # Extract state
                state = address.get("state")
                
                # Country
                country = address.get("country")
                
                # Full address
                full_address = data.get("display_name")
                
                if not district or not state:
                    logger.warning(f"Incomplete geocoding for ({lat}, {lng}): {address}")
                    return None
                
                # Look up district code from LGD data
                district_code = await self.get_district_code(district, state)
                
                result = {
                    "district": district,
                    "district_code": district_code,
                    "state": state,
                    "country": country,
                    "address": full_address
                }
                
                logger.info(f"Geocoded ({lat}, {lng}) → {district} District, {state}")
                return result
                
        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return None

    async def get_nearest_municipality(self, lat: float, lng: float) -> Optional[Dict]:
        """
        Finds the nearest municipality to the given coordinates.
        Uses a simple distance check against all active municipalities.
        For production with thousands of entries, PostGIS would be better, 
        but for <500 items, in-memory calculation is fast enough.
        """
        try:
            # TODO: Cache this list in memory or Redis for performance
            municipalities = await db.get_municipalities(include_inactive=False)
            
            nearest_muni = None
            min_dist = float('inf')
            
            for muni in municipalities:
                m_lat = muni.get('latitude')
                m_lng = muni.get('longitude')
                radius = muni.get('radius_km', 20) or 20
                
                if m_lat is None or m_lng is None:
                    continue
                    
                dist = self.haversine_distance(lat, lng, m_lat, m_lng)
                
                # Check if within coverage radius
                if dist <= radius:
                    # If we found one, we check if it's closer than previous matches
                    # This handles overlapping circles by picking center proximity
                    if dist < min_dist:
                        min_dist = dist
                        nearest_muni = muni
                        
            if nearest_muni:
                logger.info(f"Location ({lat}, {lng}) matched to {nearest_muni['name']} ({min_dist:.2f}km away)")
                return nearest_muni
                
            logger.warning(f"No municipality found covering ({lat}, {lng})")
            return None
            
        except Exception as e:
            logger.error(f"Error finding nearest municipality: {e}")
            return None
    
    async def get_district_code(self, district_name: str, state_name: str) -> Optional[int]:
        """
        Find LGD district code by district and state name.
        Returns None if district not found in LGD data.
        """
        from app.services.postgres_service import get_db
        
        db = await get_db()
        
        result = await db.fetchrow("""
            SELECT district_code FROM districts
            WHERE LOWER(district_name) = LOWER($1)
            AND LOWER(state_name) = LOWER($2)
        """, district_name, state_name)
        
        return result['district_code'] if result else None
    
    async def get_municipality_for_district(self, district: str, state: str) -> Optional[Dict]:
        """
        Find municipality by district name and state.
        Returns None if district doesn't have a municipality.
        """
        from app.services.postgres_service import get_db
        
        db = await get_db()
        
        # Try to find municipality in this district
        result = await db.fetchrow("""
            SELECT m.id, m.name, m.latitude, m.longitude, m.radius_km
            FROM municipalities m
            JOIN districts d ON m.district_code = d.district_code
            WHERE LOWER(d.district_name) = LOWER($1)
            AND LOWER(d.state_name) = LOWER($2)
            LIMIT 1
        """, district, state)
        
        return dict(result) if result else None
    
    async def get_municipality_for_city(self, city: str, state: str) -> Optional[Dict]:
        """
        Find municipality by city name and state.
        Returns None if city doesn't have a municipality yet.
        """
        try:
            municipalities = await db.get_municipalities(include_inactive=False)
            
            # Normalize for comparison
            city_lower = city.lower().strip()
            state_lower = state.lower().strip()
            
            for muni in municipalities:
                muni_name = muni.get('name', '').lower()
                # Match if municipality name contains city name
                # e.g., "Ranchi Municipal Corporation" matches "Ranchi"
                if city_lower in muni_name:
                    logger.info(f"Found municipality for {city}: {muni['name']}")
                    return muni
            
            logger.info(f"No municipality found for {city}, {state}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding municipality for city: {e}")
            return None

location_service = LocationService()

