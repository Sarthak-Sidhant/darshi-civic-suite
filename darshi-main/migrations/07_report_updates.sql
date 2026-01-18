-- Migration 07: Report Updates System
-- Part of Darshi Platform Overhaul Phase 2

-- Drop trigger if exists to avoid errors on re-run
DROP TRIGGER IF EXISTS update_report_updates_timestamp ON report_updates;

CREATE TABLE IF NOT EXISTS report_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    author_id TEXT REFERENCES users(username) ON DELETE SET NULL,
    content TEXT NOT NULL,
    status TEXT DEFAULT 'public' CHECK (status IN ('public', 'internal')),
    media_urls TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_official BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_report_updates_report ON report_updates(report_id);
CREATE INDEX IF NOT EXISTS idx_report_updates_created ON report_updates(created_at DESC);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_report_updates_modtime()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_report_updates_timestamp
    BEFORE UPDATE ON report_updates
    FOR EACH ROW
    EXECUTE FUNCTION update_report_updates_modtime();
