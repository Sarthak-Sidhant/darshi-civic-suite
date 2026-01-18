---
title: API Overview
tags: [api, rest, fastapi, documentation, http, endpoints, index]
version: v1
base_url: /api/v1
related:
  - "[[authentication]]"
  - "[[reports]]"
  - "[[geospatial]]"
  - "[[../architecture/backend-architecture]]"
---

# API Overview

Welcome to the Darshi API documentation. This REST API powers the civic grievance reporting platform.

## Quick Links

- [[authentication|Authentication & Security]] - JWT, OAuth, rate limiting
- [[reports|Reports API]] - CRUD operations for civic reports
- [[geospatial|Geospatial API]] - Geocoding, reverse geocoding, hotspot alerts
- [[users|Users API]] - User profile management
- [[notifications|Notifications API]] - Push notifications, in-app alerts
- [[admin|Admin API]] - Administrative operations

## API Information

**Base URL**: `/api/v1`
**Protocol**: HTTPS only (production)
**Authentication**: JWT Bearer tokens
**Response Format**: JSON
**Rate Limiting**: Yes (tiered by user type)

## Technology Stack

- **Framework**: FastAPI 0.115+
- **Database**: PostgreSQL 15 + PostGIS
- **Cache**: Redis 7
- **Storage**: Cloudflare R2 (S3-compatible)
- **AI**: Google Gemini 2.5 Flash

## Key Features

### 🔐 Security
- JWT token authentication (HS256)
- OAuth 2.0 integration (Google, GitHub, Facebook)
- Rate limiting (Redis-backed)
- Input validation and sanitization
- CORS protection

### 📊 Data Management
- PostgreSQL with asyncpg (async operations)
- PostGIS for geospatial queries
- Redis caching (5-15 min TTL)
- Cloudflare R2 for image storage

### 🎯 Performance
- Async/await throughout
- Connection pooling (20 max)
- Circuit breakers for external APIs
- Response caching with CDN headers
- GZip compression

## Endpoint Summary

| Category | Endpoints | Description |
|----------|-----------|-------------|
| [[reports\|Reports]] | 8 | Report CRUD, upvotes, comments |
| [[geospatial\|Geospatial]] | 3 | Geocoding, alerts, landmarks |
| [[authentication\|Authentication]] | 13 | Login, register, magic link, verify email/phone |
| [[authentication#OAuth\|OAuth]] | 6 | OAuth flows (Google, GitHub, Facebook) |
| [[users\|Users]] | 7 | Profile, settings, stats |
| [[notifications\|Notifications]] | 6 | Push subscriptions, in-app notifications |
| [[admin\|Admin]] | 12 | Status updates, analytics, audit logs |

**Total**: 65 endpoints

## Authentication Methods

### 1. JWT Bearer Token

```http
Authorization: Bearer <token>
```

**Token Lifetime**: 30 days (users), 1 hour (admin)

### 2. Username/Password

Traditional authentication with email/username and password.

### 3. Magic Link (Passwordless)

Send one-time login link via email:
- No password required
- Automatic account creation
- 15-minute expiry
- One-time use tokens

See [[authentication#Magic Link Authentication|Magic Link Documentation]] for implementation details.

### 4. OAuth 2.0

Supported providers:
- Google OAuth
- GitHub OAuth
- Facebook OAuth

See [[authentication#OAuth|OAuth Documentation]] for implementation details.

## Rate Limiting

Rate limits are tiered by authentication status:

| User Type | Report Creation | General Endpoints | Auth Endpoints |
|-----------|----------------|-------------------|----------------|
| Anonymous | 10/hour | 100-200/hour | 5-10/hour |
| Authenticated | 50/hour | 100-200/hour | 10/hour |
| Admin | Unlimited | 500/hour | 100/hour |

**Implementation**: SlowAPI with Redis backend

**Headers Returned**:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1735210800
```

## Error Responses

All errors follow a consistent structure:

```json
{
  "error": {
    "code": "ValidationError",
    "message": "Invalid coordinates",
    "details": "Latitude must be between -90 and 90",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123def456"
  }
}
```

### Common HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Successful GET/PUT request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid JWT token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 501 | Not Implemented | Feature not configured |

## Response Caching

Cached endpoints include cache-control headers:

| Endpoint | Client Cache | CDN Cache | Total TTL |
|----------|--------------|-----------|-----------|
| `GET /report/{id}` | 60s | 120s | 2 minutes |
| `GET /reports` | 30s | 60s | 1.5 minutes |
| `GET /alerts` | 300s | 300s | 5 minutes |

**Cache Headers**:
```http
Cache-Control: public, max-age=60, s-maxage=120
```

## Data Models

### Report Object

```json
{
  "report_id": "uuid",
  "username": "string",
  "title": "string",
  "description": "string",
  "location": "string",
  "latitude": "float",
  "longitude": "float",
  "geohash": "string",
  "status": "VERIFIED",
  "category": "string",
  "severity": "int (1-10)",
  "image_data": [
    {
      "webp_url": "string",
      "jpeg_url": "string"
    }
  ],
  "upvote_count": "int",
  "comment_count": "int",
  "created_at": "ISO 8601 datetime",
  "verified_at": "ISO 8601 datetime"
}
```

### User Object

```json
{
  "username": "string",
  "email": "string",
  "phone": "string",
  "full_name": "string",
  "role": "citizen",
  "email_verified": "boolean",
  "phone_verified": "boolean",
  "created_at": "ISO 8601 datetime"
}
```

## API Client Examples

### Python (httpx)

```python
import httpx

async with httpx.AsyncClient(base_url="https://api.darshi.app") as client:
    # Get reports
    response = await client.get("/api/v1/reports", params={"limit": 10})
    reports = response.json()

    # Create report (requires auth)
    headers = {"Authorization": f"Bearer {token}"}
    files = {"files": open("image.jpg", "rb")}
    data = {
        "title": "Pothole on Main Street",
        "description": "Large pothole",
        "location": "28.7041,77.1025"
    }
    response = await client.post(
        "/api/v1/report",
        headers=headers,
        files=files,
        data=data
    )
```

### JavaScript (Fetch)

```javascript
// Get reports
const reports = await fetch('https://api.darshi.app/api/v1/reports?limit=10')
  .then(res => res.json());

// Create report (requires auth)
const formData = new FormData();
formData.append('files', fileInput.files[0]);
formData.append('title', 'Pothole on Main Street');
formData.append('description', 'Large pothole');
formData.append('location', '28.7041,77.1025');

const response = await fetch('https://api.darshi.app/api/v1/report', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});
```

### cURL

```bash
# Get reports
curl https://api.darshi.app/api/v1/reports?limit=10

# Create report (requires auth)
curl -X POST https://api.darshi.app/api/v1/report \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@image.jpg" \
  -F "title=Pothole on Main Street" \
  -F "description=Large pothole" \
  -F "location=28.7041,77.1025"
```

## Interactive Documentation

FastAPI provides automatic interactive API documentation:

- **Swagger UI**: http://localhost:8080/docs (development)
- **ReDoc**: http://localhost:8080/redoc (development)

## Versioning

Current version: **v1**

API versioning is handled via URL prefix (`/api/v1/`). Breaking changes will result in a new version (`/api/v2/`).

## Support

- **Issues**: [GitHub Issues](https://github.com/Sarthak-Sidhant/darshi/issues)
- **Documentation**: This wiki
- **Live API**: https://api.darshi.app

---

**Last Updated**: December 28, 2025
**API Version**: 1.0.0
**Base URL**: https://api.darshi.app/api/v1
