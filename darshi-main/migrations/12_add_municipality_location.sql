-- Migration 12: Add location columns to municipalities
-- Supports finding nearest municipality for report assignment

ALTER TABLE municipalities 
ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
ADD COLUMN IF NOT EXISTS radius_km INTEGER DEFAULT 20;

CREATE INDEX IF NOT EXISTS idx_municipalities_lat_lng ON municipalities(latitude, longitude);

-- Update seed data for key cities (manual override for now)
-- We will update others via script later

-- Ranchi
UPDATE municipalities SET latitude = 23.3441, longitude = 85.3096, radius_km = 15 WHERE id = 'ranchi_mc';

-- Jamshedpur (JNAC / Mango / Adityapur)
UPDATE municipalities SET latitude = 22.8046, longitude = 86.2029, radius_km = 15 WHERE id = 'jamshedpur_nac'; -- Check ID matches seed
UPDATE municipalities SET latitude = 22.7983, longitude = 86.1837, radius_km = 10 WHERE id = 'adityapur_mc';

-- Dhanbad
UPDATE municipalities SET latitude = 23.7957, longitude = 86.4304, radius_km = 20 WHERE id = 'dhanbad_mc';

-- Bangalore / Bengaluru
UPDATE municipalities SET latitude = 12.9716, longitude = 77.5946, radius_km = 40 WHERE id = 'bengaluru_mc';

-- Mumbai
UPDATE municipalities SET latitude = 19.0760, longitude = 72.8777, radius_km = 30 WHERE id = 'mumbai_mc';

-- Delhi
UPDATE municipalities SET latitude = 28.7041, longitude = 77.1025, radius_km = 40 WHERE id = 'delhi_mc';

-- Kolkata
UPDATE municipalities SET latitude = 22.5726, longitude = 88.3639, radius_km = 25 WHERE id = 'kolkata_mc';

-- Chennai
UPDATE municipalities SET latitude = 13.0827, longitude = 80.2707, radius_km = 25 WHERE id = 'chennai_mc';
