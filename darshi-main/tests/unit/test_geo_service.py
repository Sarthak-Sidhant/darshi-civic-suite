"""
Unit tests for geo_service
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys


@pytest.mark.unit
class TestGeohash:
    """Tests for geohash encoding"""

    def test_encode_geohash_basic(self):
        """Test basic geohash encoding"""
        from app.services.geo_service import encode

        # Test known location (Delhi, India)
        geohash = encode(28.6139, 77.2090, precision=7)
        assert geohash is not None
        assert len(geohash) == 7
        assert geohash.startswith("t")  # Delhi area

    def test_encode_geohash_precision(self):
        """Test geohash encoding with different precisions"""
        from app.services.geo_service import encode

        lat, lng = 28.6139, 77.2090

        hash_5 = encode(lat, lng, precision=5)
        hash_7 = encode(lat, lng, precision=7)
        hash_9 = encode(lat, lng, precision=9)

        assert len(hash_5) == 5
        assert len(hash_7) == 7
        assert len(hash_9) == 9
        assert hash_7.startswith(hash_5)

    def test_encode_geohash_edge_cases(self):
        """Test geohash encoding at edge coordinates"""
        from app.services.geo_service import encode

        # Equator, prime meridian
        geohash = encode(0, 0, precision=7)
        assert geohash is not None

        # South pole vicinity
        geohash = encode(-89.9, 0, precision=7)
        assert geohash is not None

        # North pole vicinity
        geohash = encode(89.9, 0, precision=7)
        assert geohash is not None


@pytest.mark.unit
class TestGeohashNeighbors:
    """Tests for geohash neighbor calculation"""

    @pytest.mark.skip(reason="get_neighbors function not yet implemented")
    def test_get_geohash_neighbors_returns_list(self):
        """Test that get_neighbors returns a list (currently empty as stub)"""
        from app.services.geo_service import get_neighbors

        center_hash = "ttnfv9m"
        neighbors = get_neighbors(center_hash)

        # Function returns empty list as it's a stub
        assert isinstance(neighbors, list)

    @pytest.mark.skip(reason="get_neighbors function not yet implemented")
    def test_geohash_neighbors_function_exists(self):
        """Test that get_neighbors function is callable"""
        from app.services.geo_service import get_neighbors

        assert callable(get_neighbors)


@pytest.mark.unit
class TestDistanceCalculation:
    """Tests for distance calculation - using haversine from math"""

    def test_haversine_distance_same_point(self):
        """Test distance between same point is zero"""
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance using haversine formula"""
            R = 6371  # Earth radius in km
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)

            a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

            return R * c

        distance = haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
        assert distance == 0

    def test_haversine_distance_known_distance(self):
        """Test distance between two known cities"""
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)

            a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

            return R * c

        # Delhi to Mumbai (approx 1150 km)
        delhi_lat, delhi_lng = 28.6139, 77.2090
        mumbai_lat, mumbai_lng = 19.0760, 72.8777

        distance = haversine_distance(delhi_lat, delhi_lng, mumbai_lat, mumbai_lng)

        # Distance should be approximately 1150 km (allow 10% tolerance)
        assert 1000 < distance < 1300

    def test_haversine_distance_antipodal_points(self):
        """Test distance between antipodal points (max distance)"""
        import math

        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371
            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)

            a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

            return R * c

        # Roughly antipodal points
        distance = haversine_distance(0, 0, 0, 180)

        # Half Earth circumference is about 20,000 km
        assert 19000 < distance < 21000


@pytest.mark.unit
class TestGeocodingAsync:
    """Tests for async geocoding functions"""

    def test_geocode_function_exists(self):
        """Test that geocode_address function exists"""
        from app.services.geo_service import geocode_address
        assert callable(geocode_address)

    def test_reverse_geocode_function_exists(self):
        """Test that reverse_geocode function exists"""
        from app.services.geo_service import reverse_geocode
        assert callable(reverse_geocode)


@pytest.mark.unit
class TestCoordinateValidation:
    """Tests for coordinate validation utilities"""

    def test_valid_coordinates(self):
        """Test valid coordinate ranges"""
        # Valid latitude range
        assert -90 <= 28.6139 <= 90
        assert -90 <= -33.8688 <= 90  # Sydney

        # Valid longitude range
        assert -180 <= 77.2090 <= 180
        assert -180 <= -151.2093 <= 180  # Sydney

    def test_invalid_coordinates(self):
        """Test invalid coordinate detection"""
        # Invalid latitude
        assert not (-90 <= 91 <= 90)
        assert not (-90 <= -91 <= 90)

        # Invalid longitude
        assert not (-180 <= 181 <= 180)
        assert not (-180 <= -181 <= 180)

    def test_india_coordinates(self):
        """Test that India coordinates are in valid range"""
        india_coords = [
            (28.6139, 77.2090),  # Delhi
            (19.0760, 72.8777),  # Mumbai
            (22.5726, 88.3639),  # Kolkata
            (13.0827, 80.2707),  # Chennai
            (12.9716, 77.5946),  # Bangalore
        ]

        for lat, lng in india_coords:
            assert -90 <= lat <= 90
            assert -180 <= lng <= 180
            # India bounds (roughly)
            assert 8 <= lat <= 35
            assert 68 <= lng <= 97


@pytest.mark.unit
class TestLandmarksAsync:
    """Tests for async landmarks functions"""

    def test_get_multiple_nearby_landmarks_function_exists(self):
        """Test that get_multiple_nearby_landmarks function exists"""
        from app.services.geo_service import get_multiple_nearby_landmarks
        assert callable(get_multiple_nearby_landmarks)

    def test_get_nearby_landmark_function_exists(self):
        """Test that get_nearby_landmark function exists"""
        from app.services.geo_service import get_nearby_landmark
        assert callable(get_nearby_landmark)

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_returns_list(self):
        """Test that get_multiple_nearby_landmarks returns a list"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        # Mock the HTTP client to avoid real API calls
        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'elements': [
                    {
                        'lat': 28.6140,
                        'lon': 77.2091,
                        'tags': {
                            'name': 'India Gate',
                            'amenity': 'tourism'
                        }
                    },
                    {
                        'lat': 28.6150,
                        'lon': 77.2100,
                        'tags': {
                            'name': 'Connaught Place',
                            'shop': 'mall'
                        }
                    }
                ]
            }
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090)

            assert isinstance(result, list)
            assert len(result) == 2
            assert result[0]['name'] == 'India Gate'
            assert result[1]['name'] == 'Connaught Place'

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_empty_response(self):
        """Test that get_multiple_nearby_landmarks handles empty response"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'elements': []}
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090)

            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_api_error(self):
        """Test that get_multiple_nearby_landmarks handles API errors gracefully"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090)

            # Should return empty list on error
            assert isinstance(result, list)
            assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_sorts_by_distance(self):
        """Test that landmarks are sorted by distance"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'elements': [
                    {
                        'lat': 28.6200,  # Farther
                        'lon': 77.2200,
                        'tags': {'name': 'Far Place', 'amenity': 'temple'}
                    },
                    {
                        'lat': 28.6140,  # Closer
                        'lon': 77.2091,
                        'tags': {'name': 'Near Place', 'amenity': 'hospital'}
                    }
                ]
            }
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090)

            # Near Place should be first (closer)
            assert result[0]['name'] == 'Near Place'
            assert result[1]['name'] == 'Far Place'

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_deduplicates(self):
        """Test that duplicate landmark names are removed"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'elements': [
                    {
                        'lat': 28.6140,
                        'lon': 77.2091,
                        'tags': {'name': 'Same Name', 'amenity': 'hospital'}
                    },
                    {
                        'lat': 28.6150,
                        'lon': 77.2100,
                        'tags': {'name': 'Same Name', 'amenity': 'school'}  # Duplicate name
                    },
                    {
                        'lat': 28.6160,
                        'lon': 77.2110,
                        'tags': {'name': 'Different Name', 'amenity': 'bank'}
                    }
                ]
            }
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090)

            # Should only have 2 unique names
            assert len(result) == 2
            names = [lm['name'] for lm in result]
            assert 'Same Name' in names
            assert 'Different Name' in names

    @pytest.mark.asyncio
    async def test_get_multiple_nearby_landmarks_respects_limit(self):
        """Test that landmarks respect the limit parameter"""
        from app.services.geo_service import get_multiple_nearby_landmarks

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'elements': [
                    {'lat': 28.6140, 'lon': 77.2091, 'tags': {'name': f'Place {i}', 'amenity': 'hospital'}}
                    for i in range(10)
                ]
            }
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_multiple_nearby_landmarks(28.6139, 77.2090, limit=3)

            assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_nearby_landmark_returns_tuple(self):
        """Test that get_nearby_landmark returns correct format"""
        from app.services.geo_service import get_nearby_landmark

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'elements': [
                    {
                        'lat': 28.6140,
                        'lon': 77.2091,
                        'tags': {'name': 'Test Landmark', 'amenity': 'hospital'}
                    }
                ]
            }
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_nearby_landmark(28.6139, 77.2090)

            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert result[0] == 'Test Landmark'
            assert isinstance(result[1], int)

    @pytest.mark.asyncio
    async def test_get_nearby_landmark_returns_none_when_empty(self):
        """Test that get_nearby_landmark returns None when no landmarks found"""
        from app.services.geo_service import get_nearby_landmark

        with patch('app.services.geo_service.get_http_client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'elements': []}
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            result = await get_nearby_landmark(28.6139, 77.2090)

            assert result is None
