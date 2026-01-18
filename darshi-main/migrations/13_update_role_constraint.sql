-- Migration to update role check constraint to include municipality roles
-- We drop the old constraint and add a new one with the updated allowed values

DO $$
BEGIN
    -- Try to drop the constraint if it exists
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'users_role_check') THEN
        ALTER TABLE users DROP CONSTRAINT users_role_check;
    END IF;
END $$;

-- Add the new constraint with all supported roles
ALTER TABLE users 
ADD CONSTRAINT users_role_check 
CHECK (role IN ('citizen', 'admin', 'super_admin', 'municipality_admin', 'municipality_staff'));
