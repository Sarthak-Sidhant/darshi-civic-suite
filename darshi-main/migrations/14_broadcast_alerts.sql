-- Migration 14: Broadcast Alerts System (District-Based)
-- District-scoped alerts that work everywhere (not just municipalities)
-- Uses Nominatim for automatic district detection from LGD data

CREATE TABLE IF NOT EXISTS broadcast_alerts (
    id TEXT PRIMARY KEY,
    created_by TEXT NOT NULL REFERENCES users(username),
    
    -- Location (REQUIRED - from Nominatim + LGD)
    district TEXT NOT NULL,           -- "Ranchi", "Bokaro", "Patna"
    district_code INTEGER REFERENCES districts(district_code),  -- LGD district code
    state TEXT NOT NULL,              -- "Jharkhand", "Bihar"
    
    -- GPS coordinates (for map display)
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,                     -- Full address from Nominatim
    
    -- Municipality (OPTIONAL - only if district has one)
    municipality_id TEXT REFERENCES municipalities(id),
    is_official BOOLEAN DEFAULT FALSE,  -- TRUE if created by municipality
    verified_by TEXT REFERENCES users(username),  -- Municipality can verify citizen alerts
    verified_at TIMESTAMP,
    
    -- Content (image required)
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT NOT NULL,
    image_webp_url TEXT,
    
    -- Classification
    category TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Targeting (hyper-local within district)
    radius_km INTEGER NOT NULL DEFAULT 5 CHECK (radius_km >= 1 AND radius_km <= 30),
    geohash TEXT,
    
    -- Lifecycle
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'EXPIRED', 'CANCELLED')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    
    -- Engagement
    view_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    upvote_count INTEGER DEFAULT 0,
    
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- Alert updates (like report updates)
CREATE TABLE IF NOT EXISTS alert_updates (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL REFERENCES broadcast_alerts(id) ON DELETE CASCADE,
    author_username TEXT NOT NULL REFERENCES users(username),
    content TEXT NOT NULL,
    image_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Alert upvotes (reuse pattern from reports)
CREATE TABLE IF NOT EXISTS alert_upvotes (
    alert_id TEXT NOT NULL REFERENCES broadcast_alerts(id) ON DELETE CASCADE,
    username TEXT NOT NULL REFERENCES users(username),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (alert_id, username)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_alerts_district_state ON broadcast_alerts(LOWER(district), LOWER(state), status);
CREATE INDEX IF NOT EXISTS idx_alerts_district_code ON broadcast_alerts(district_code, status);
CREATE INDEX IF NOT EXISTS idx_alerts_status_expires ON broadcast_alerts(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_alerts_geohash ON broadcast_alerts(geohash);
CREATE INDEX IF NOT EXISTS idx_alerts_category ON broadcast_alerts(category);
CREATE INDEX IF NOT EXISTS idx_alerts_location ON broadcast_alerts(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_alerts_official ON broadcast_alerts(is_official, verified_by);
CREATE INDEX IF NOT EXISTS idx_alerts_municipality ON broadcast_alerts(municipality_id) WHERE municipality_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_alert_updates_alert ON alert_updates(alert_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_upvotes_alert ON alert_upvotes(alert_id);

-- Comments: Extend existing comments table
ALTER TABLE comments ADD COLUMN IF NOT EXISTS alert_id TEXT REFERENCES broadcast_alerts(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_comments_alert ON comments(alert_id) WHERE alert_id IS NOT NULL;

-- Add constraint: comment must be for either report OR alert
ALTER TABLE comments DROP CONSTRAINT IF EXISTS comment_target_check;
ALTER TABLE comments ADD CONSTRAINT comment_target_check 
    CHECK ((report_id IS NOT NULL AND alert_id IS NULL) OR (report_id IS NULL AND alert_id IS NOT NULL));

-- Comments
COMMENT ON TABLE broadcast_alerts IS 'District-based alerts that work everywhere, with optional municipality verification';
COMMENT ON COLUMN broadcast_alerts.district IS 'District name from Nominatim (e.g., Ranchi, Bokaro)';
COMMENT ON COLUMN broadcast_alerts.district_code IS 'LGD district code for official mapping';
COMMENT ON COLUMN broadcast_alerts.municipality_id IS 'NULL for districts without municipality, set for districts with municipality';
COMMENT ON COLUMN broadcast_alerts.is_official IS 'TRUE if created by municipality official';
COMMENT ON COLUMN broadcast_alerts.verified_by IS 'Municipality can verify citizen alerts in their district';
