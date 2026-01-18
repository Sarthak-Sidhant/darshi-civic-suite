-- Migration 09: Resolution Fields
-- Part of Phase 6: Status Machine

ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolution_summary TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolution_image_url TEXT;

COMMENT ON COLUMN reports.resolution_summary IS 'Description of how the issue was resolved';
COMMENT ON COLUMN reports.resolution_image_url IS 'Image proof of resolution';
