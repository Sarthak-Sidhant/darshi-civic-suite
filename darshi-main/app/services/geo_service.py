import httpx
from typing import List, Dict
from app.core.logging_config import get_logger
from app.core.http_client import get_http_client
from app.core.exceptions import (
    GeocodingError,
    GeocodingServiceUnavailableError,
    GeocodingTimeoutError,
    InvalidCoordinatesError,
    GeohashError
)
from app.core.error_handling import (
    retry_external_api,
    circuit_breaker,
    ErrorContext
)
from app.core.cache import cached

logger = get_logger(__name__)

try:
    import pygeohash as geohash
except ImportError:
    logger.warning("pygeohash not installed, geohashing features will be disabled")
    geohash = None

# --- GEOHASHING ---
def encode(lat: float, lng: float, precision: int = 9) -> str:
    """
    Encode lat/lng into a geohash.

    Args:
        lat: Latitude
        lng: Longitude
        precision: Geohash precision level (default 9 = ~4.8m × 4.8m grid, building-level accuracy)

    Returns:
        Geohash string

    Raises:
        GeohashError: If encoding fails
        InvalidCoordinatesError: If coordinates are invalid
    """
    if not geohash:
        raise GeohashError(
            message="Geohash library not available",
            latitude=lat,
            longitude=lng
        )

    # Validate coordinates
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise InvalidCoordinatesError(
            message="Coordinates must be numeric",
            latitude=lat,
            longitude=lng
        )

    if not -90 <= lat <= 90:
        raise InvalidCoordinatesError(
            message=f"Latitude {lat} out of range [-90, 90]",
            latitude=lat,
            longitude=lng
        )

    if not -180 <= lng <= 180:
        raise InvalidCoordinatesError(
            message=f"Longitude {lng} out of range [-180, 180]",
            latitude=lat,
            longitude=lng
        )

    try:
        result = geohash.encode(lat, lng, precision)
        logger.debug(f"Encoded location ({lat},{lng}) to geohash: {result}")
        return result
    except Exception as e:
        raise GeohashError(
            message="Failed to encode geohash",
            latitude=lat,
            longitude=lng,
            details=str(e)
        ) from e


# --- GEOCODING (Nominatim) ---
@cached(key_prefix="geocode", ttl=3600, key_builder=lambda args, kwargs: args[0] if args else kwargs.get('query', ''))
@circuit_breaker(name="nominatim_geocode", failure_threshold=3, recovery_timeout=60, expected_exception=GeocodingError)
@retry_external_api(max_attempts=3)
async def geocode_address(query: str) -> List[Dict]:
    """
    Search OSM Nominatim for an address.

    Args:
        query: Address query string

    Returns:
        List of geocoding results

    Raises:
        GeocodingError: If geocoding fails
        GeocodingServiceUnavailableError: If service is unavailable
        GeocodingTimeoutError: If request times out
    """
    if not query or not query.strip():
        raise GeocodingError(
            message="Geocoding query cannot be empty",
            query=query
        )

    with ErrorContext("geocoding", "geocode_address", GeocodingError, query=query):
        logger.debug(f"Geocoding address query: {query}")
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "addressdetails": 1,
            "limit": 5,
            "countrycodes": "in"  # Limit to India
        }
        headers = {"User-Agent": "Darshi-Civic-App/1.0"}

        try:
            client = get_http_client()
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)

            if resp.status_code == 200:
                results = resp.json()
                formatted_results = [{
                    "display_name": r['display_name'],
                    "lat": float(r['lat']),
                    "lng": float(r['lon']),
                    "type": r.get('type')
                } for r in results]
                logger.debug(f"Geocoding successful: found {len(formatted_results)} results for '{query}'")
                return formatted_results
            elif resp.status_code == 429:
                raise GeocodingError(
                    message="Geocoding rate limit exceeded",
                    query=query,
                    details="Too many requests to Nominatim"
                )
            elif resp.status_code >= 500:
                raise GeocodingServiceUnavailableError(
                    message=f"Geocoding service unavailable (HTTP {resp.status_code})",
                    query=query
                )
            else:
                raise GeocodingError(
                    message=f"Geocoding failed with HTTP {resp.status_code}",
                    query=query
                )

        except httpx.TimeoutException as e:
            raise GeocodingTimeoutError(
                message="Geocoding request timed out",
                query=query
            ) from e
        except httpx.ConnectError as e:
            raise GeocodingServiceUnavailableError(
                message="Failed to connect to geocoding service",
                query=query,
                details=str(e)
            ) from e
        except httpx.HTTPError as e:
            raise GeocodingError(
                message="HTTP error during geocoding",
                query=query,
                details=str(e)
            ) from e
        except (GeocodingError, GeocodingServiceUnavailableError, GeocodingTimeoutError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            raise GeocodingError(
                message="Unexpected error during geocoding",
                query=query,
                details=str(e)
            ) from e

@cached(key_prefix="landmarks", ttl=1800, key_builder=lambda args, kwargs: f"{kwargs.get('lat', args[0] if args else 0):.4f},{kwargs.get('lng', args[1] if len(args)>1 else 0):.4f},{kwargs.get('radius_m', 1000)},{kwargs.get('limit', 5)}")
@circuit_breaker(name="overpass_api", failure_threshold=5, recovery_timeout=120, expected_exception=Exception)
async def get_multiple_nearby_landmarks(lat: float, lng: float, radius_m: int = 1000, limit: int = 5) -> list[dict]:
    """
    Get multiple nearby landmarks for display on report page.

    Args:
        lat: Latitude
        lng: Longitude
        radius_m: Search radius in meters
        limit: Maximum number of landmarks to return

    Returns:
        List of landmark dicts with name, type, distance, and category
    """
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"

        # Expanded query - includes nodes AND ways for buildings/roads with names
        # Also includes more POI types for better coverage in rural areas
        overpass_query = f"""
        [out:json][timeout:15];
        (
          // Named amenities (nodes and ways)
          node["amenity"~"hospital|clinic|school|university|college|temple|place_of_worship|bank|atm|post_office|police|fire_station|fuel|pharmacy|restaurant|cafe|fast_food|library|community_centre|town_hall|government|cinema|theatre|marketplace|bus_station|railway_station"](around:{radius_m},{lat},{lng});
          way["amenity"~"hospital|clinic|school|university|college|temple|place_of_worship|bank|post_office|police|fire_station|marketplace|bus_station|railway_station"](around:{radius_m},{lat},{lng});
          
          // Shops
          node["shop"~"mall|supermarket|department_store|convenience|general"](around:{radius_m},{lat},{lng});
          way["shop"~"mall|supermarket|department_store"](around:{radius_m},{lat},{lng});
          
          // Tourism and leisure
          node["tourism"](around:{radius_m},{lat},{lng});
          node["leisure"~"park|garden|sports_centre|stadium"](around:{radius_m},{lat},{lng});
          
          // Transport
          node["highway"~"bus_stop"](around:{radius_m},{lat},{lng});
          node["railway"~"station|halt"](around:{radius_m},{lat},{lng});
          
          // Named buildings and landmarks
          way["building"]["name"](around:{radius_m},{lat},{lng});
          node["historic"](around:{radius_m},{lat},{lng});
          
          // Named roads as fallback (only first-class roads)
          way["highway"~"primary|secondary|tertiary"]["name"](around:{radius_m},{lat},{lng});
        );
        out center body;
        """


        client = get_http_client()
        # Increased timeout for expanded query with ways
        resp = await client.post(overpass_url, data=overpass_query, timeout=15.0)

        if resp.status_code == 200:
            data = resp.json()
            elements = data.get('elements', [])

            landmarks = []
            for element in elements:
                tags = element.get('tags', {})
                name = tags.get('name', '') or tags.get('ref', '')  # Include highway refs like "NH333"
                if name:
                    # Handle both nodes (lat/lon) and ways (center.lat/center.lon)
                    if 'center' in element:
                        elem_lat = element['center'].get('lat', lat)
                        elem_lon = element['center'].get('lon', lng)
                    else:
                        elem_lat = element.get('lat', lat)
                        elem_lon = element.get('lon', lng)

                    # Calculate distance
                    distance = ((elem_lat - lat)**2 + (elem_lon - lng)**2)**0.5
                    distance_m = int(distance * 111000)

                    # Determine category
                    amenity = tags.get('amenity', '')
                    shop = tags.get('shop', '')
                    tourism = tags.get('tourism', '')
                    highway = tags.get('highway', '')
                    building = tags.get('building', '')

                    category = amenity or shop or tourism or highway or building or 'other'

                    landmarks.append({
                        'name': name,
                        'type': category,
                        'distance': distance,
                        'distance_m': distance_m,
                        'amenity': amenity,
                    })

            if landmarks:
                # Sort by distance
                landmarks.sort(key=lambda x: x['distance'])

                # Deduplicate by name (keep closest occurrence)
                seen_names = set()
                unique_landmarks = []
                for lm in landmarks:
                    if lm['name'] not in seen_names:
                        seen_names.add(lm['name'])
                        unique_landmarks.append(lm)
                        if len(unique_landmarks) >= limit:
                            break

                return unique_landmarks

        return []
    except Exception as e:
        logger.debug(f"Failed to get multiple nearby landmarks: {e}")
        return []


@cached(key_prefix="landmark", ttl=1800, key_builder=lambda args, kwargs: f"{args[0]:.4f},{args[1]:.4f},{kwargs.get('radius_m', 500)}")
@circuit_breaker(name="overpass_api", failure_threshold=5, recovery_timeout=120, expected_exception=Exception)
async def get_nearby_landmark(lat: float, lng: float, radius_m: int = 500) -> tuple[str, int] | None:
    """
    Find the nearest significant landmark using Overpass API.

    Args:
        lat: Latitude
        lng: Longitude
        radius_m: Search radius in meters (default 500m for single landmark)

    Returns:
        Tuple of (landmark_name, distance_in_meters) if found, None otherwise
    """
    try:
        overpass_url = "https://overpass-api.de/api/interpreter"

        # Expanded query - nodes and ways for better coverage
        overpass_query = f"""
        [out:json][timeout:10];
        (
          node["amenity"~"hospital|school|university|temple|place_of_worship|bank|post_office|police|railway_station|bus_station"](around:{radius_m},{lat},{lng});
          way["amenity"~"hospital|school|university|temple|place_of_worship|bank"](around:{radius_m},{lat},{lng});
          node["shop"~"mall|supermarket"](around:{radius_m},{lat},{lng});
          node["tourism"](around:{radius_m},{lat},{lng});
          way["building"]["name"](around:{radius_m},{lat},{lng});
          node["railway"~"station|halt"](around:{radius_m},{lat},{lng});
        );
        out center body;
        """

        client = get_http_client()
        resp = await client.post(overpass_url, data=overpass_query, timeout=10.0)

        if resp.status_code == 200:
            data = resp.json()
            elements = data.get('elements', [])

            # Find closest named landmark
            landmarks = []
            for element in elements:
                tags = element.get('tags', {})
                name = tags.get('name', '')
                if name:
                    # Handle both nodes (lat/lon) and ways (center.lat/center.lon)
                    if 'center' in element:
                        elem_lat = element['center'].get('lat', lat)
                        elem_lon = element['center'].get('lon', lng)
                    else:
                        elem_lat = element.get('lat', lat)
                        elem_lon = element.get('lon', lng)

                    # Simple Euclidean distance (rough approximation)
                    distance = ((elem_lat - lat)**2 + (elem_lon - lng)**2)**0.5

                    landmarks.append({
                        'name': name,
                        'distance': distance,
                        'amenity': tags.get('amenity', ''),
                    })

            if landmarks:
                # Sort by distance and return closest
                landmarks.sort(key=lambda x: x['distance'])
                closest = landmarks[0]

                # Convert distance to meters (rough approximation: 1 degree ≈ 111km)
                distance_m = int(closest['distance'] * 111000)

                logger.debug(f"Found nearby landmark: {closest['name']} (distance: ~{distance_m}m)")
                return (closest['name'], distance_m)

        return None
    except Exception as e:
        logger.debug(f"Failed to get nearby landmark: {e}")
        return None


async def reverse_geocode(lat: float, lng: float) -> str:
    """
    Get address from lat/lng with nearby landmark if available.

    Args:
        lat: Latitude
        lng: Longitude

    Returns:
        Address string with optional landmark prefix

    Raises:
        GeocodingError: If reverse geocoding fails
        InvalidCoordinatesError: If coordinates are invalid
    """
    # Validate coordinates
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise InvalidCoordinatesError(
            message="Coordinates must be numeric",
            latitude=lat,
            longitude=lng
        )

    if not -90 <= lat <= 90:
        raise InvalidCoordinatesError(
            message=f"Latitude {lat} out of range [-90, 90]",
            latitude=lat,
            longitude=lng
        )

    if not -180 <= lng <= 180:
        raise InvalidCoordinatesError(
            message=f"Longitude {lng} out of range [-180, 180]",
            latitude=lat,
            longitude=lng
        )

    with ErrorContext("geocoding", "reverse_geocode", GeocodingError, latitude=lat, longitude=lng, raise_on_exit=False):
        logger.debug(f"Reverse geocoding coordinates: ({lat},{lng})")
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lng,
            "format": "json",
            "zoom": 18,  # Building-level detail (18 = ~10m accuracy)
            "addressdetails": 1,  # Get detailed address components
        }
        headers = {"User-Agent": "Darshi-Civic-App/1.0"}

        try:
            client = get_http_client()
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)

            if resp.status_code == 200:
                data = resp.json()

                # Extract detailed address components from OSM
                address_parts = data.get('address', {})
                osm_type = data.get('osm_type', '')
                name = data.get('name', '')

                # Build human-readable address with landmarks
                address_components = []

                # Try to get nearby landmark first (non-blocking)
                landmark_info = None
                try:
                    landmark_info = await get_nearby_landmark(lat, lng, radius_m=300)
                except Exception as e:
                    logger.debug(f"Landmark lookup failed: {e}")

                # Priority 1: Nearby landmark with distance (if found and different from OSM name)
                if landmark_info:
                    landmark_name, distance_m = landmark_info
                    if landmark_name != name:
                        # Format distance nicely
                        if distance_m == 0:
                            address_components.append(f"At {landmark_name}")
                        elif distance_m < 1000:
                            address_components.append(f"{distance_m}m from {landmark_name}")
                        else:
                            # Convert to km if >= 1km
                            distance_km = distance_m / 1000
                            address_components.append(f"{distance_km:.1f}km from {landmark_name}")

                # Priority 2: Named features (landmarks, buildings, amenities)
                if name and osm_type in ['node', 'way', 'relation']:
                    address_components.append(name)

                # Priority 3: Road/Street name
                road = (address_parts.get('road') or
                       address_parts.get('street') or
                       address_parts.get('footway') or
                       address_parts.get('pedestrian') or
                       address_parts.get('path'))
                if road and road != name:
                    address_components.append(road)

                # Priority 4: Suburb/Neighbourhood
                suburb = (address_parts.get('suburb') or
                         address_parts.get('neighbourhood') or
                         address_parts.get('quarter'))
                if suburb:
                    address_components.append(suburb)

                # Priority 5: City/Town/Village
                city = (address_parts.get('city') or
                       address_parts.get('town') or
                       address_parts.get('village') or
                       address_parts.get('municipality'))
                if city:
                    address_components.append(city)

                # Priority 6: State/District
                state = (address_parts.get('state') or
                        address_parts.get('state_district') or
                        address_parts.get('county'))
                if state:
                    address_components.append(state)

                # Build final address string
                if address_components:
                    address = ", ".join(address_components)
                    logger.debug(f"Reverse geocoding successful: {address}")
                    return address
                else:
                    # Fallback to display_name if no components found
                    address = data.get('display_name', f"{lat}, {lng}")
                    logger.debug(f"Reverse geocoding (display_name): {address}")
                    return address

            elif resp.status_code == 429:
                logger.warning(f"Reverse geocoding rate limit for ({lat},{lng})")
                # Fall back to coordinates
                return f"{lat}, {lng}"
            elif resp.status_code >= 500:
                logger.warning(f"Reverse geocoding service unavailable for ({lat},{lng})")
                return f"{lat}, {lng}"
            else:
                logger.warning(f"Reverse geocoding failed with status {resp.status_code} for ({lat},{lng})")
                return f"{lat}, {lng}"

        except httpx.TimeoutException as e:
            logger.warning(f"Reverse geocoding timed out for ({lat},{lng}): {e}")
            return f"{lat}, {lng}"
        except httpx.HTTPError as e:
            logger.warning(f"Reverse geocoding HTTP error for ({lat},{lng}): {e}")
            return f"{lat}, {lng}"
        except Exception as e:
            logger.warning(f"Reverse geocoding failed for ({lat},{lng}): {e}")
            return f"{lat}, {lng}"
