-- Migration 15: Districts Reference Table
-- Creates districts table with LGD (Local Government Directory) data
-- Enables district-based scoping for alerts and reports

-- Create districts table
CREATE TABLE IF NOT EXISTS districts (
    district_code INTEGER PRIMARY KEY,
    district_name TEXT NOT NULL,
    district_name_local TEXT,
    state_code INTEGER NOT NULL,
    state_name TEXT NOT NULL,
    census_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_districts_state ON districts(state_code);
CREATE INDEX IF NOT EXISTS idx_districts_name ON districts(LOWER(district_name));
CREATE INDEX IF NOT EXISTS idx_districts_state_name ON districts(state_code, LOWER(district_name));

-- Add district_code to municipalities
ALTER TABLE municipalities 
ADD COLUMN IF NOT EXISTS district_code INTEGER REFERENCES districts(district_code);

CREATE INDEX IF NOT EXISTS idx_municipalities_district ON municipalities(district_code);

-- Comments
COMMENT ON TABLE districts IS 'LGD districts reference data for India (785 districts)';
COMMENT ON COLUMN districts.district_code IS 'Official LGD district code';
COMMENT ON COLUMN districts.state_code IS 'Official LGD state code';
COMMENT ON COLUMN municipalities.district_code IS 'District this municipality belongs to';
