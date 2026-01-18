-- Migration: Add location validation and constraints
-- Author: Claude Code
-- Date: 2026-01-01
-- Description: Adds NOT NULL constraints and default values for city/state/country fields

-- STEP 1: Update existing NULL/empty values with placeholder
-- This ensures we don't violate NOT NULL constraints when we add them

UPDATE users
SET city = 'Unspecified'
WHERE city IS NULL OR TRIM(city) = '';

UPDATE users
SET state = 'Unspecified'
WHERE state IS NULL OR TRIM(state) = '';

UPDATE users
SET country = 'India'
WHERE country IS NULL OR TRIM(country) = '';

-- STEP 2: Add CHECK constraints to prevent empty strings
-- (PostgreSQL doesn't enforce NOT NULL on empty strings, so we need explicit checks)

ALTER TABLE users
ADD CONSTRAINT check_city_not_empty
CHECK (city IS NOT NULL AND TRIM(city) != '');

ALTER TABLE users
ADD CONSTRAINT check_state_not_empty
CHECK (state IS NOT NULL AND TRIM(state) != '');

ALTER TABLE users
ADD CONSTRAINT check_country_not_empty
CHECK (country IS NOT NULL AND TRIM(country) != '');

-- STEP 3: Add length constraints
ALTER TABLE users
ADD CONSTRAINT check_city_length
CHECK (LENGTH(city) >= 2 AND LENGTH(city) <= 100);

ALTER TABLE users
ADD CONSTRAINT check_state_length
CHECK (LENGTH(state) >= 2 AND LENGTH(state) <= 100);

ALTER TABLE users
ADD CONSTRAINT check_country_length
CHECK (LENGTH(country) >= 2 AND LENGTH(country) <= 100);

-- STEP 4: Update column defaults for new users
ALTER TABLE users
ALTER COLUMN city SET DEFAULT 'Unspecified';

ALTER TABLE users
ALTER COLUMN state SET DEFAULT 'Unspecified';

ALTER TABLE users
ALTER COLUMN country SET DEFAULT 'India';

-- STEP 5: Add comment explaining the constraints
COMMENT ON CONSTRAINT check_city_not_empty ON users IS 'Ensures city is not null or empty string';
COMMENT ON CONSTRAINT check_state_not_empty ON users IS 'Ensures state is not null or empty string';
COMMENT ON CONSTRAINT check_country_not_empty ON users IS 'Ensures country is not null or empty string';

COMMENT ON CONSTRAINT check_city_length ON users IS 'Ensures city name is between 2-100 characters';
COMMENT ON CONSTRAINT check_state_length ON users IS 'Ensures state name is between 2-100 characters';
COMMENT ON CONSTRAINT check_country_length ON users IS 'Ensures country name is between 2-100 characters';

-- Migration complete
-- Users with incomplete locations will show 'Unspecified' and will be prompted to update on next login
