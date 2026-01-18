---
title: Reports API
tags: [api, reports, crud, geospatial, civic-issues, images, upload, upvote, comments, ai-verification]
related:
  - "[[geospatial]]"
  - "[[users]]"
  - "[[admin]]"
  - "[[../architecture/data-models]]"
---

# Reports API

← Back to [[overview|API Overview]]

Complete documentation for managing civic grievance reports including creation, retrieval, upvoting, and commenting.

## Endpoints Overview

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/report` | POST | Create new report | Optional |
| `/report/{id}` | GET | Get single report | No |
| `/reports` | GET | List reports with filters | No |
| `/report/{id}` | PUT | Edit report | Yes |
| `/report/{id}` | DELETE | Delete report | Yes |
| `/report/{id}/upvote` | POST | Upvote a report | Yes |
| `/report/{id}/comment` | POST | Add comment | Yes |
| `/report/{id}/comments` | GET | Get all comments | No |
| `/report/{id}/nearby-landmarks` | GET | Get nearby landmarks | No |

---

## POST /api/v1/report

**Create a new civic grievance report with images**

- **Authentication**: Optional (JWT Bearer token recommended)
- **Rate Limit**: 10/hour (anonymous) | 50/hour (authenticated)
- **Response**: 201 Created
- **Content-Type**: `multipart/form-data`

### Request (multipart/form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | File[] | Yes | 1-5 image files (max 10MB each) - JPEG, PNG, WebP |
| `location` | string | Yes | Human-readable location or coordinates (e.g., '28.7041,77.1025' or 'Delhi') |
| `title` | string | Yes | Report title (max 200 characters) |
| `description` | string | No | Detailed description (max 1000 characters) |
| `username` | string | No | Anonymous username (auto-generated if not provided) |

### Response

```json
{
  "report_id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7",
  "status": "PENDING_VERIFICATION"
}
```

### Processing Flow

1. **Upload** → Images uploaded to Cloudflare R2
2. **Optimization** → WebP (85% quality) + JPEG (90% quality)
3. **Hashing** → Calculate dHash for duplicate detection
4. **Geocoding** → Convert location to lat/lng if needed
5. **Geohashing** → Calculate geohash (precision 7)
6. **Database** → Create PostgreSQL record
7. **Background Task** → Queue AI verification

### Background AI Verification

Asynchronous processing after report creation:

1. Download image from R2
2. Analyze with Gemini 2.5 Flash
3. Extract: `is_valid`, `category`, `severity`, `description`
4. Check for duplicates (perceptual hash + geohash)
5. Update status: `VERIFIED`, `REJECTED`, or `DUPLICATE`
6. Add timeline event

### Example

```bash
curl -X POST https://api.darshi.app/api/v1/report \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@pothole.jpg" \
  -F "title=Large pothole on Main Street" \
  -F "description=Dangerous pothole near traffic signal" \
  -F "location=28.7041,77.1025"
```

### Notes

- **5x rate limit** for authenticated users vs anonymous
- Duplicate detection: same category within ~153m (geohash precision 7) in last 24h
- Images optimized: WebP ~30% smaller than JPEG
- Geohashing: Fast proximity queries

---

## GET /api/v1/report/{report_id}

**Get a single report by ID**

- **Authentication**: None
- **Rate Limit**: 200/hour
- **Response**: 200 OK
- **Cache**: Public, 60s client + 120s CDN

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Unique report identifier |

### Response

```json
{
  "report_id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7",
  "username": "john_doe",
  "title": "Large pothole on Main Street",
  "description": "Dangerous pothole near traffic signal",
  "location": "Connaught Place, New Delhi",
  "latitude": 28.7041,
  "longitude": 77.1025,
  "geohash": "ttkvh2p",
  "status": "VERIFIED",
  "category": "Road Damage",
  "severity": 8,
  "image_data": [
    {
      "webp_url": "https://cdn.darshi.app/reports/abc123.webp",
      "jpeg_url": "https://cdn.darshi.app/reports/abc123.jpg"
    }
  ],
  "upvote_count": 45,
  "comment_count": 12,
  "created_at": "2025-12-27T10:30:00Z",
  "verified_at": "2025-12-27T10:32:15Z",
  "timeline": [
    {
      "event": "created",
      "timestamp": "2025-12-27T10:30:00Z",
      "actor": "john_doe"
    },
    {
      "event": "verified",
      "timestamp": "2025-12-27T10:32:15Z",
      "actor": "ai_system",
      "details": "AI classified as Road Damage with severity 8"
    }
  ]
}
```

### Example

```bash
curl https://api.darshi.app/api/v1/report/a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7
```

---

## GET /api/v1/reports

**List reports with pagination and filters**

- **Authentication**: None
- **Rate Limit**: 200/hour
- **Response**: 200 OK
- **Cache**: Public, 30s client + 60s CDN

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_after_id` | string | - | Pagination cursor (report UUID) |
| `geohash` | string | - | Filter by geohash prefix (precision 5) |
| `limit` | integer | 10 | Number of reports to return (max 50) |
| `status` | string | - | Filter by status (e.g., VERIFIED) |

### Response

```json
[
  {
    "report_id": "...",
    "title": "...",
    "status": "VERIFIED",
    "latitude": 28.7041,
    "longitude": 77.1025,
    "upvote_count": 45,
    "created_at": "2025-12-27T10:30:00Z"
  },
  {
    "report_id": "...",
    "title": "...",
    "status": "VERIFIED",
    "latitude": 28.7042,
    "longitude": 77.1026,
    "upvote_count": 32,
    "created_at": "2025-12-27T09:15:00Z"
  }
]
```

### Geohash Filtering

Filter reports within a geographic area:

```bash
# Precision 5 geohash covers ~4.9km × 4.9km
curl https://api.darshi.app/api/v1/reports?geohash=ttkv&limit=20
```

### Pagination

```bash
# First page
curl https://api.darshi.app/api/v1/reports?limit=10

# Next page (use last report_id from previous page)
curl https://api.darshi.app/api/v1/reports?limit=10&start_after_id=last_report_uuid
```

### Example

```bash
curl https://api.darshi.app/api/v1/reports?limit=20&status=VERIFIED
```

---

## PUT /api/v1/report/{report_id}

**Edit a report (title and description only)**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 50/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report to edit |

### Request (form-data)

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Updated title (optional, max 200 chars) |
| `description` | string | Updated description (optional, max 1000 chars) |

### Response

```json
{
  "message": "Report updated successfully",
  "report_id": "a1b2c3d4-e5f6-4789-a0b1-c2d3e4f5a6b7"
}
```

### Restrictions

- Only **report owner** can edit
- Cannot edit: `RESOLVED`, `REJECTED`, `DUPLICATE`, or `IN_PROGRESS` reports
- Timeline event added for audit trail

### Example

```bash
curl -X PUT https://api.darshi.app/api/v1/report/abc123 \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Updated pothole report" \
  -F "description=Added more context about the location"
```

---

## DELETE /api/v1/report/{report_id}

**Delete a report**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 50/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report to delete |

### Response

```json
{
  "message": "Report deleted successfully"
}
```

### Restrictions

- Only **report owner** can delete
- Cannot delete: `VERIFIED`, `RESOLVED`, `IN_PROGRESS`, or `DUPLICATE` reports

### Example

```bash
curl -X DELETE https://api.darshi.app/api/v1/report/abc123 \
  -H "Authorization: Bearer $TOKEN"
```

---

## POST /api/v1/report/{report_id}/upvote

**Upvote a report (idempotent per user)**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report to upvote |

### Response

```json
{
  "upvote_count": 46,
  "user_upvoted": true
}
```

### Behavior

- **Idempotent**: Multiple upvotes from same user = 1 upvote
- **Toggle**: Upvoting again removes upvote
- **Security**: Username extracted from JWT (prevents IDOR attacks)

### Milestone Notifications

Notifications sent to report author at:
- 10 upvotes
- 50 upvotes
- 100 upvotes
- 500 upvotes
- 1000 upvotes

### Example

```bash
curl -X POST https://api.darshi.app/api/v1/report/abc123/upvote \
  -H "Authorization: Bearer $TOKEN"
```

---

## POST /api/v1/report/{report_id}/comment

**Add a comment to a report**

- **Authentication**: Required (JWT Bearer token)
- **Rate Limit**: 50/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report to comment on |

### Request (form-data)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Comment text (1-500 characters) |

### Response

```json
{
  "id": "comment_uuid",
  "username": "john_doe",
  "text": "This pothole is still there!",
  "created_at": "2025-12-28T11:00:00Z"
}
```

### Behavior

- Username extracted from JWT
- Notification sent to report author (if different from commenter)
- Text sanitized before storage (HTML entities encoded)

### Example

```bash
curl -X POST https://api.darshi.app/api/v1/report/abc123/comment \
  -H "Authorization: Bearer $TOKEN" \
  -F "text=This pothole is still there!"
```

---

## GET /api/v1/report/{report_id}/comments

**Get all comments for a report**

- **Authentication**: None
- **Rate Limit**: 200/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

### Response

```json
[
  {
    "id": "comment_uuid_1",
    "username": "user1",
    "text": "This pothole is huge!",
    "created_at": "2025-12-27T12:00:00Z"
  },
  {
    "id": "comment_uuid_2",
    "username": "user2",
    "text": "I drove through this yesterday",
    "created_at": "2025-12-27T14:30:00Z"
  }
]
```

### Example

```bash
curl https://api.darshi.app/api/v1/report/abc123/comments
```

---

## GET /api/v1/report/{report_id}/nearby-landmarks

**Get nearby landmarks for a report**

- **Authentication**: None
- **Rate Limit**: 100/hour
- **Response**: 200 OK

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | UUID | Report ID |

### Response

```json
{
  "landmarks": [
    {
      "name": "Central Park",
      "type": "park",
      "distance_m": 125,
      "distance_text": "125m away"
    },
    {
      "name": "Main Street Traffic Signal",
      "type": "traffic_signal",
      "distance_m": 45,
      "distance_text": "45m away"
    },
    {
      "name": "City Hospital",
      "type": "hospital",
      "distance_m": 1200,
      "distance_text": "1.2km away"
    }
  ]
}
```

### Behavior

- Returns up to **5 landmarks** within **500m radius**
- Uses Overpass API for landmark data
- Distance formatted as "Xm away" or "X.Xkm away"

### Example

```bash
curl https://api.darshi.app/api/v1/report/abc123/nearby-landmarks
```

---

## Report Status Values

| Status | Description | Transition From |
|--------|-------------|-----------------|
| `PENDING_VERIFICATION` | Awaiting AI verification | (initial) |
| `VERIFIED` | AI verified as valid civic issue | PENDING_VERIFICATION |
| `REJECTED` | AI rejected (not a civic issue) | PENDING_VERIFICATION |
| `DUPLICATE` | Duplicate of existing report | PENDING_VERIFICATION |
| `IN_PROGRESS` | Admin marked as being worked on | VERIFIED |
| `RESOLVED` | Admin marked as resolved | IN_PROGRESS |
| `FLAGGED` | System error during processing | PENDING_VERIFICATION |

---

## Error Responses

### 400 Bad Request

```json
{
  "error": {
    "code": "ValidationError",
    "message": "Invalid file format",
    "details": "Only JPEG, PNG, and WebP images are allowed",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### 403 Forbidden

```json
{
  "error": {
    "code": "PermissionDenied",
    "message": "Cannot edit this report",
    "details": "You can only edit your own reports",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

### 404 Not Found

```json
{
  "error": {
    "code": "NotFoundError",
    "message": "Report not found",
    "details": "No report exists with ID: abc123",
    "timestamp": "2025-12-28T10:30:00Z",
    "request_id": "abc123"
  }
}
```

---

← Back to [[overview|API Overview]] | Next: [[geospatial|Geospatial API]] →

**Last Updated**: December 28, 2025
