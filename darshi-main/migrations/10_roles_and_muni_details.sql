-- Migration 10: Roles and Enhanced Municipality Details

-- ============================================================================
-- ENHANCED MUNICIPALITY DETAILS
-- ============================================================================

ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS website TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS contact_email TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS contact_phone TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS population INTEGER;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS logo_url TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS mayor_name TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS city_tier TEXT; -- Tier 1, 2, etc.
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS social_twitter TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS social_facebook TEXT;
ALTER TABLE municipalities ADD COLUMN IF NOT EXISTS district TEXT;

-- Index for searching municipals by state/district
CREATE INDEX IF NOT EXISTS idx_municipalities_state ON municipalities(state);
CREATE INDEX IF NOT EXISTS idx_municipalities_district ON municipalities(district);

-- ============================================================================
-- ROLE MANAGEMENT (Foundational Schema)
-- ============================================================================

-- Table to define granular permissions for roles
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY, -- e.g. 'report.delete', 'user.ban'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table relationships for role-based access control (RBAC)
-- Note: 'users' table already has a 'role' column (enum/text).
-- We will expand this to allow dynamic role definitions.

CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY, -- 'citizen', 'moderator', 'municipality_admin'
    display_name TEXT NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT FALSE, -- System roles cannot be deleted
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mapping roles to permissions
CREATE TABLE IF NOT EXISTS role_permissions (
    role_name TEXT REFERENCES roles(name) ON DELETE CASCADE,
    permission_id TEXT REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_name, permission_id)
);

-- Initial Roles Seeding (Matches existing hardcoded roles)
INSERT INTO roles (name, display_name, description, is_system) VALUES
('citizen', 'Citizen', 'Standard user who can report issues', TRUE),
('verified_citizen', 'Verified Citizen', 'Trusted user with faster report approval', TRUE),
('local_guide', 'Local Guide', 'User with high reputation', TRUE),
('official', 'Official', 'Municipality officer or staff', TRUE),
('moderator', 'Moderator', 'Can review flags and manage content', TRUE),
('super_admin', 'Super Admin', 'Full system access', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Initial Permissions Seeding (Examples)
INSERT INTO permissions (id, description) VALUES
('report.create', 'Can create reports'),
('report.view', 'Can view public reports'),
('report.resolve', 'Can mark reports as resolved'),
('report.delete', 'Can delete any report'),
('user.ban', 'Can ban users')
ON CONFLICT (id) DO NOTHING;

-- Map basic permissions (Example)
INSERT INTO role_permissions (role_name, permission_id) VALUES
('super_admin', 'report.delete'),
('super_admin', 'user.ban'),
('official', 'report.resolve')
ON CONFLICT DO NOTHING;
