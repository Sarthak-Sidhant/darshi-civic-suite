-- Migration 16: Alter broadcast_alerts to use districts
-- Updates existing table from city-based to district-based

-- Add district columns to existing table
ALTER TABLE broadcast_alerts 
ADD COLUMN IF NOT EXISTS district_code INTEGER REFERENCES districts(district_code);

-- Rename city to district (if city column exists)
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'broadcast_alerts' AND column_name = 'city'
    ) THEN
        ALTER TABLE broadcast_alerts RENAME COLUMN city TO district;
    END IF;
END $$;

-- Create indexes for district-based queries
DROP INDEX IF EXISTS idx_alerts_city_state;
CREATE INDEX IF NOT EXISTS idx_alerts_district_state ON broadcast_alerts(LOWER(district), LOWER(state), status);
CREATE INDEX IF NOT EXISTS idx_alerts_district_code ON broadcast_alerts(district_code, status);

-- Update comments
COMMENT ON COLUMN broadcast_alerts.district IS 'District name from Nominatim (e.g., Ranchi, Bokaro)';
COMMENT ON COLUMN broadcast_alerts.district_code IS 'LGD district code for official mapping';
