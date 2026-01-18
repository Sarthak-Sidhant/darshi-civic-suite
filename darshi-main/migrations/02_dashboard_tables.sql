-- Migration: Add Tables for Municipality Dashboard (Alerts & Roles)
-- Excludes Communication Tower (Circulars) for now.

-- 1. ALERTS TABLE (Nagar Alert Hub)
-- Stores real-time disruptions broadcasting.
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    severity TEXT NOT NULL DEFAULT 'medium', -- low, medium, high, critical
    category TEXT NOT NULL, -- traffic, power, water, safety, community
    
    -- Geospatial Scope
    geohash TEXT, -- Target specific area (e.g., 'tunm7')
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    radius_meters INTEGER DEFAULT 0, -- 0 = Global/City-wide, >0 = localized
    
    -- Metadata
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, RESOLVED
    source TEXT NOT NULL DEFAULT 'authority', -- authority, system
    author_id TEXT, -- User/Admin who posted it
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ, -- When does the alert auto-expire?
    resolved_at TIMESTAMPTZ
);

-- Index for fast geospatial querying of alerts
CREATE INDEX IF NOT EXISTS idx_alerts_geohash ON alerts(geohash);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- 2. MUNICIPALITY ROLES TABLE
-- Links a User to a Municipality Department.
CREATE TABLE IF NOT EXISTS municipality_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE, -- Link to existing users
    
    municipality_id TEXT NOT NULL, -- Logical ID (e.g., 'ranchi_municipal_corp')
    department TEXT NOT NULL, -- mayor, roads, sanitation, electricity, traffic
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, municipality_id) -- One role per municipality per user
);

-- 3. UPDATES TO REPORTS TABLE (If needed)
-- Ensuring we have columns for assignment (Work Orders) if not already present.
-- (Checking existing schema in postgres_service.py... content seems standard)
-- We might need 'assigned_to' later, but for now 'status' transitions handle the flow.
