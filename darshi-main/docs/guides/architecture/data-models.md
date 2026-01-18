---
title: Data Models & Schema
tags: [database, postgresql, postgis, schema, models, sql, orm, sqlalchemy, spatial, geospatial, indexes]
related:
  - "[[overview]]"
  - "[[backend-architecture#Database Layer]]"
  - "[[../api/geospatial]]"
  - "[[../api/reports]]"
---

# Data Models & Schema

← Back to [[overview|Architecture Overview]]

Complete PostgreSQL database schema with PostGIS spatial extensions.

## Schema Diagram

```
users
├── id (SERIAL PK)
├── username (UNIQUE)
├── email, phone
├── password_hash
├── role, oauth_provider
└── created_at, updated_at

reports
├── id (SERIAL PK)
├── report_id (UUID UNIQUE)
├── user_id (FK → users)
├── geom (GEOGRAPHY PostGIS)  ← Spatial queries
├── geohash (VARCHAR)
├── image_data (JSONB)
├── timeline (JSONB)          ← Audit trail
├── upvote_count, comment_count
└── created_at, verified_at

comments
├── id (SERIAL PK)
├── report_id (FK → reports CASCADE)
├── user_id (FK → users)
└── text, created_at

upvotes
├── id (SERIAL PK)
├── report_id (FK → reports CASCADE)
├── user_id (FK → users CASCADE)
└── UNIQUE(report_id, user_id)

admin_logs
├── id (SERIAL PK)
├── admin_username
├── action, resource_type
├── details (JSONB)
└── ip_address, created_at
```

## Tables

### users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'citizen',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_oauth UNIQUE(oauth_provider, oauth_id)
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
```

### reports

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE reports (
    id SERIAL PRIMARY KEY,
    report_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    location VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    geom GEOGRAPHY(POINT, 4326),  -- PostGIS column
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    geohash VARCHAR(10),
    status VARCHAR(30) DEFAULT 'PENDING_VERIFICATION',
    category VARCHAR(50),
    severity INTEGER,
    ai_description TEXT,
    ai_rejection_reason TEXT,
    image_urls TEXT[] NOT NULL,
    image_data JSONB,
    image_hash VARCHAR(64),
    dhash VARCHAR(16),  -- Perceptual hash
    duplicate_of INTEGER REFERENCES reports(id),
    upvote_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    resolved_at TIMESTAMP,
    timeline JSONB DEFAULT '[]'::jsonb,
    CONSTRAINT valid_coords CHECK (
        latitude BETWEEN -90 AND 90 AND
        longitude BETWEEN -180 AND 180
    ),
    CONSTRAINT valid_severity CHECK (severity BETWEEN 1 AND 10)
);

-- Indexes for performance
CREATE INDEX idx_reports_report_id ON reports(report_id);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX idx_reports_geohash ON reports(geohash);
CREATE INDEX idx_reports_dhash ON reports(dhash) WHERE dhash IS NOT NULL;

-- PostGIS spatial index
CREATE INDEX idx_reports_geom ON reports USING GIST(geom);

-- Composite indexes
CREATE INDEX idx_reports_status_created
    ON reports(status, created_at DESC);
```

## PostGIS Functions

### Proximity Search

```sql
-- Find reports within 5km radius
CREATE OR REPLACE FUNCTION nearby_reports(
    p_latitude DOUBLE PRECISION,
    p_longitude DOUBLE PRECISION,
    p_radius_meters INTEGER DEFAULT 5000
)
RETURNS TABLE(
    report_id UUID,
    title VARCHAR,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.report_id,
        r.title,
        ST_Distance(
            r.geom,
            ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography
        ) as distance_meters
    FROM reports r
    WHERE ST_DWithin(
        r.geom,
        ST_SetSRID(ST_MakePoint(p_longitude, p_latitude), 4326)::geography,
        p_radius_meters
    )
    AND r.status = 'VERIFIED'
    ORDER BY distance_meters;
END;
$$ LANGUAGE plpgsql;
```

Usage:
```sql
SELECT * FROM nearby_reports(28.7041, 77.1025, 5000);
```

## Report Status Flow

```
PENDING_VERIFICATION  →  VERIFIED  →  IN_PROGRESS  →  RESOLVED
                     ↓         ↘            ↗
                  REJECTED     FLAGGED
                     ↓
                  DUPLICATE
```

## JSONB Columns

### timeline (audit trail)

```json
[
  {
    "event": "created",
    "timestamp": "2025-12-27T10:00:00Z",
    "actor": "john_doe"
  },
  {
    "event": "verified",
    "timestamp": "2025-12-27T10:02:00Z",
    "actor": "ai_system",
    "details": "AI classified as Road Damage with severity 8"
  },
  {
    "event": "status_updated",
    "timestamp": "2025-12-28T09:00:00Z",
    "actor": "admin@darshi.app",
    "details": "Changed from VERIFIED to IN_PROGRESS"
  }
]
```

### image_data

```json
[
  {
    "webp_url": "https://cdn.darshi.app/reports/abc123.webp",
    "jpeg_url": "https://cdn.darshi.app/reports/abc123.jpg",
    "width": 1920,
    "height": 1080,
    "size_bytes": 245000
  }
]
```

## Indexes Strategy

| Index Type | Use Case | Performance Impact |
|------------|----------|-------------------|
| B-tree | Equality, range queries | Fast lookups |
| GIST | Spatial queries (PostGIS) | Proximity search |
| GIN | JSONB, arrays | Text search, contains |
| Partial | Conditional (WHERE clause) | Smaller index size |

---

← Back to [[overview|Architecture Overview]]

**Last Updated**: December 28, 2025
