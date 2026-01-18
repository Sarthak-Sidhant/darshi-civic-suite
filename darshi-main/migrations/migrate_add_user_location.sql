-- Migration: Add location and magic link fields to users table
-- Created: 2025-12-28
-- Purpose: Support user onboarding with location and passwordless authentication

-- Add location fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS city VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS state VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS country VARCHAR(100) DEFAULT 'India';
ALTER TABLE users ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS lng DOUBLE PRECISION;
ALTER TABLE users ADD COLUMN IF NOT EXISTS location_address TEXT;

-- Add magic link authentication fields
ALTER TABLE users ADD COLUMN IF NOT EXISTS magic_link_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS magic_link_expires TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ;

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_users_city ON users(city);
CREATE INDEX IF NOT EXISTS idx_users_country ON users(country);
CREATE INDEX IF NOT EXISTS idx_users_magic_link_token ON users(magic_link_token) WHERE magic_link_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login DESC);

-- Update existing users to have default country
UPDATE users SET country = 'India' WHERE country IS NULL;

COMMENT ON COLUMN users.city IS 'User''s city for location-based content personalization';
COMMENT ON COLUMN users.state IS 'User''s state/province';
COMMENT ON COLUMN users.country IS 'User''s country (default: India)';
COMMENT ON COLUMN users.lat IS 'Latitude coordinate';
COMMENT ON COLUMN users.lng IS 'Longitude coordinate';
COMMENT ON COLUMN users.location_address IS 'Human-readable address';
COMMENT ON COLUMN users.magic_link_token IS 'Token for passwordless email authentication (15-min expiry)';
COMMENT ON COLUMN users.magic_link_expires IS 'Expiration timestamp for magic link token';
COMMENT ON COLUMN users.last_login IS 'Timestamp of user''s last successful login';

-- Migration: Add dhash_bucket column to reports table for duplicate detection
ALTER TABLE reports ADD COLUMN IF NOT EXISTS dhash_bucket VARCHAR(4);
CREATE INDEX IF NOT EXISTS idx_reports_dhash_bucket ON reports(dhash_bucket) WHERE dhash_bucket IS NOT NULL;
COMMENT ON COLUMN reports.dhash_bucket IS 'First 4 chars of perceptual hash for fast duplicate lookup';
