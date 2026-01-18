-- Database initialization script for Darshi
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable PostGIS extension for geospatial features
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    username VARCHAR(50) PRIMARY KEY,
    email VARCHAR(255),
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'citizen' CHECK (role IN ('citizen', 'admin')),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    email_verified BOOLEAN DEFAULT false,
    phone_verified BOOLEAN DEFAULT false,
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    location_address TEXT,
    magic_link_token VARCHAR(255),
    magic_link_expires TIMESTAMPTZ,
    last_login TIMESTAMPTZ,
    reports_count INTEGER DEFAULT 0,
    upvotes_received INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id);

-- Create reports table
CREATE TABLE IF NOT EXISTS reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(30) DEFAULT 'PENDING_VERIFICATION' CHECK (
        status IN ('PENDING_VERIFICATION', 'VERIFIED', 'REJECTED', 'DUPLICATE',
                   'IN_PROGRESS', 'RESOLVED', 'FLAGGED')
    ),
    flag_reason TEXT,
    location GEOGRAPHY(POINT, 4326),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geohash VARCHAR(12),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    image_urls TEXT[],
    image_hash VARCHAR(64),
    submitted_by VARCHAR(50) REFERENCES users(username) ON DELETE SET NULL ON UPDATE CASCADE,
    upvotes TEXT[] DEFAULT '{}',
    upvote_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    ai_analysis JSONB,
    duplicate_of UUID REFERENCES reports(id) ON DELETE SET NULL,
    timeline JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

-- Create indexes for reports
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_geohash ON reports(geohash);
CREATE INDEX IF NOT EXISTS idx_reports_location ON reports USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_submitted_by ON reports(submitted_by);
CREATE INDEX IF NOT EXISTS idx_reports_category ON reports(category);
CREATE INDEX IF NOT EXISTS idx_reports_duplicate ON reports(duplicate_of) WHERE duplicate_of IS NOT NULL;

-- Create comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    author VARCHAR(50) REFERENCES users(username) ON DELETE SET NULL ON UPDATE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_comments_report_id ON comments(report_id);
CREATE INDEX IF NOT EXISTS idx_comments_created_at ON comments(created_at);

-- Create push_subscriptions table
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
    subscription JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_push_subscriptions_username ON push_subscriptions(username);

-- Create user_metadata table for tracking signup location (admin-only visibility)
CREATE TABLE IF NOT EXISTS user_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
    -- Signup location from IP geolocation
    signup_ip VARCHAR(45),  -- Supports IPv6
    signup_city VARCHAR(100),
    signup_region VARCHAR(100),
    signup_country VARCHAR(100),
    signup_country_code VARCHAR(10),
    signup_lat DOUBLE PRECISION,
    signup_lng DOUBLE PRECISION,
    signup_isp VARCHAR(255),
    signup_timezone VARCHAR(100),
    -- Trust indicators
    location_mismatch BOOLEAN DEFAULT FALSE,  -- True if claimed location != signup location
    vpn_detected BOOLEAN DEFAULT FALSE,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_metadata_username ON user_metadata(username);
CREATE INDEX IF NOT EXISTS idx_user_metadata_country ON user_metadata(signup_country);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating timestamps
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_reports_updated_at ON reports;
CREATE TRIGGER update_reports_updated_at BEFORE UPDATE ON reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function for proximity search
CREATE OR REPLACE FUNCTION nearby_reports(
    lat DOUBLE PRECISION,
    lng DOUBLE PRECISION,
    radius_meters INTEGER DEFAULT 5000,
    limit_count INTEGER DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    title VARCHAR,
    distance_meters DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id,
        r.title,
        ST_Distance(r.location::geography, ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography) as distance_meters
    FROM reports r
    WHERE ST_DWithin(
        r.location::geography,
        ST_SetSRID(ST_MakePoint(lng, lat), 4326)::geography,
        radius_meters
    )
    AND r.status IN ('VERIFIED', 'IN_PROGRESS')
    ORDER BY distance_meters
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO postgres;
