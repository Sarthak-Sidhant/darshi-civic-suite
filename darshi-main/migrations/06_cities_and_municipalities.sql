-- Cities table for geospatial filtering
CREATE TABLE IF NOT EXISTS cities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    radius_km INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, state)
);

-- Index for spatial lookups (if we add PostGIS later, but simple lat/lng for now)
CREATE INDEX IF NOT EXISTS idx_cities_active ON cities(is_active);
CREATE INDEX IF NOT EXISTS idx_cities_name ON cities(name);

-- Add city_id to reports for easier filtering
ALTER TABLE reports 
ADD COLUMN IF NOT EXISTS city_id UUID REFERENCES cities(id);

CREATE INDEX IF NOT EXISTS idx_reports_city_id ON reports(city_id);

-- Seed initial cities (Ranchi + major Indian cities)
INSERT INTO cities (name, state, latitude, longitude, radius_km, is_active) 
VALUES 
    ('Ranchi', 'Jharkhand', 23.3441, 85.3096, 15, true),
    ('Jamshedpur', 'Jharkhand', 22.8046, 86.2029, 15, true),
    ('Delhi', 'Delhi', 28.7041, 77.1025, 25, true),
    ('Mumbai', 'Maharashtra', 19.0760, 72.8777, 25, true),
    ('Bangalore', 'Karnataka', 12.9716, 77.5946, 20, true),
    ('Hyderabad', 'Telangana', 17.3850, 78.4867, 20, true),
    ('Chennai', 'Tamil Nadu', 13.0827, 80.2707, 20, true),
    ('Kolkata', 'West Bengal', 22.5726, 88.3639, 20, true),
    ('Pune', 'Maharashtra', 18.5204, 73.8567, 15, true),
    ('Ahmedabad', 'Gujarat', 23.0225, 72.5714, 15, true)
ON CONFLICT (name, state) DO NOTHING;

-- Function to find nearest city for a location
CREATE OR REPLACE FUNCTION find_nearest_city(lat DOUBLE PRECISION, lng DOUBLE PRECISION)
RETURNS UUID AS $$
DECLARE
    nearest_city_id UUID;
BEGIN
    SELECT id INTO nearest_city_id
    FROM cities
    WHERE is_active = true
    -- Haversine formula approximation for performance
    ORDER BY (
        6371 * acos(
            cos(radians(lat)) * cos(radians(latitude)) * cos(radians(longitude) - radians(lng)) +
            sin(radians(lat)) * sin(radians(latitude))
        )
    ) ASC
    LIMIT 1;
    
    RETURN nearest_city_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically assign city_id on report creation if null
CREATE OR REPLACE FUNCTION assign_report_city()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.city_id IS NULL AND NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        NEW.city_id := find_nearest_city(NEW.latitude, NEW.longitude);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_assign_report_city ON reports;

CREATE TRIGGER trigger_assign_report_city
BEFORE INSERT ON reports
FOR EACH ROW
EXECUTE FUNCTION assign_report_city();
