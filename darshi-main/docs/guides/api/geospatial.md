---
title: Geospatial API
tags: [api, geospatial, geocoding, postgis, maps, nominatim, location, coordinates, proximity, hotspots]
related:
  - "[[reports]]"
  - "[[../architecture/data-models#PostGIS Functions]]"
  - "[[../architecture/backend-architecture#Database Layer]]"
---

# Geospatial API

← Back to [[overview|API Overview]]

Geocoding, reverse geocoding, and hotspot alert endpoints powered by PostGIS, Nominatim, and BigQuery analytics.

## Endpoints

- `GET /geocode` - Convert address to coordinates
- `GET /reverse-geocode` - Convert coordinates to address
- `GET /alerts` - Get hotspot alerts

---

## GET /api/v1/geocode

**Convert address to coordinates (forward geocoding)**

- **Authentication**: None
- **Rate Limit**: 100/hour
- **Response**: 200 OK
- **Provider**: Nominatim API (OpenStreetMap)

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Address query (limited to India) |

### Response

```json
{
  "latitude": 28.7041,
  "longitude": 77.1025,
  "address": "Connaught Place, New Delhi, Delhi, India"
}
```

### Behavior

- Uses Nominatim API with India filter (`countrycodes=in`)
- Circuit breaker: 3 failures / 60s recovery
- Results cached for 24 hours (Redis)
- Returns most relevant match

### Example

```bash
# By address
curl "https://api.darshi.app/api/v1/geocode?q=Connaught+Place,+Delhi"

# By landmark
curl "https://api.darshi.app/api/v1/geocode?q=India+Gate"
```

---

## GET /api/v1/reverse-geocode

**Convert coordinates to human-readable address**

- **Authentication**: None
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `lat` | float | Yes | Latitude (-90 to 90) |
| `lng` | float | Yes | Longitude (-180 to 180) |

### Response

```json
{
  "address": "Block A, Connaught Place, New Delhi, Delhi 110001, India"
}
```

### Behavior

- Uses Nominatim reverse geocoding
- Results cached for 24 hours
- Returns closest match

### Example

```bash
curl "https://api.darshi.app/api/v1/reverse-geocode?lat=28.7041&lng=77.1025"
```

---

## GET /api/v1/alerts

**Get hotspot alerts from BigQuery analytics**

- **Authentication**: None
- **Rate Limit**: 100/hour
- **Response**: 200 OK
- **Cache**: 5 minutes (server-side)

### Response

```json
[
  {
    "location": "Connaught Place, Delhi",
    "geohash": "ttkv",
    "severity": 8,
    "count": 5,
    "category": "Road Damage",
    "timestamp": "2025-12-28T10:00:00Z",
    "reports": [
      "report_uuid_1",
      "report_uuid_2",
      "report_uuid_3"
    ]
  },
  {
    "location": "Karol Bagh, Delhi",
    "geohash": "ttkr",
    "severity": 7,
    "count": 4,
    "category": "Garbage",
    "timestamp": "2025-12-28T09:30:00Z",
    "reports": [
      "report_uuid_4",
      "report_uuid_5"
    ]
  }
]
```

### Hotspot Criteria

An area is flagged as a hotspot if:
- **3 or more** severe issues (severity > 7) within **24 hours**
- Within same geohash (precision 5 = ~4.9km × 4.9km)
- Status: VERIFIED or IN_PROGRESS

### Behavior

- Queries PostgreSQL with PostGIS aggregation
- Results cached for 5 minutes (Redis)
- Sorted by severity (descending)
- Maximum 10 hotspots returned

### Example

```bash
curl https://api.darshi.app/api/v1/alerts
```

---

## Geospatial Concepts

### Geohashing

Darshi uses geohashing for efficient proximity queries:

| Precision | Cell Size | Use Case |
|-----------|-----------|----------|
| 5 | ~4.9km × 4.9km | Hotspot detection, broad area filtering |
| 7 | ~153m × 153m | Duplicate detection, nearby reports |

**Example geohash**: `ttkv` (precision 5) → Delhi area

### PostGIS Queries

Proximity search using PostGIS:

```sql
SELECT *
FROM reports
WHERE ST_DWithin(
  geom,
  ST_SetSRID(ST_MakePoint(77.1025, 28.7041), 4326)::geography,
  5000  -- 5km radius in meters
)
AND status = 'VERIFIED'
ORDER BY created_at DESC
LIMIT 50;
```

### Geocoding Provider

**Nominatim** (OpenStreetMap):
- Free, no API key required
- Rate limited: 1 request/second
- Results cached for 24 hours
- Limited to India (`countrycodes=in`)

---

← Back to [[overview|API Overview]] | Next: [[users|Users API]] →

**Last Updated**: December 28, 2025
