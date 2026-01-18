-- Migration 17: Add district_code to reports
-- Enables district-based filtering for reports

-- Add district_code column to reports
ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS district_code INTEGER REFERENCES districts(district_code);

-- Add district column if not exists (for text-based matching)
ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS district TEXT;

-- Create indexes for district-based queries
CREATE INDEX IF NOT EXISTS idx_reports_district_code ON reports(district_code, status);
CREATE INDEX IF NOT EXISTS idx_reports_district ON reports(LOWER(district), status);

-- Comments
COMMENT ON COLUMN reports.district_code IS 'LGD district code for official mapping';
COMMENT ON COLUMN reports.district IS 'District name from Nominatim';
