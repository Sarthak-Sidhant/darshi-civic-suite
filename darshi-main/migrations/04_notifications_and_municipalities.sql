-- Migration 04: Notification System & Municipality Assignment
-- Part of Dashboard Implementation Plan Phase 1

-- ============================================================================
-- NOTIFICATION TABLES
-- ============================================================================

-- In-app notifications for users
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE ON UPDATE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('report_status', 'alert_broadcast', 'escalation', 'system', 'admin_action')),
    title TEXT NOT NULL,
    message TEXT,
    data JSONB DEFAULT '{}',
    read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, read, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- Notification queue for async delivery (push, email)
CREATE TABLE IF NOT EXISTS notification_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_type TEXT NOT NULL CHECK (notification_type IN ('push', 'email', 'in_app')),
    recipient_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    data JSONB DEFAULT '{}',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'sending', 'sent', 'failed')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    scheduled_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_queue_status ON notification_queue(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notification_queue_recipient ON notification_queue(recipient_id);

-- ============================================================================
-- MUNICIPALITY ASSIGNMENT
-- ============================================================================

-- Add municipality assignment columns to reports
ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_municipality TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_department TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS assigned_by TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolution_eta TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolution_notes TEXT;

-- Index for municipality-based queries
CREATE INDEX IF NOT EXISTS idx_reports_municipality ON reports(assigned_municipality) WHERE assigned_municipality IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reports_department ON reports(assigned_department) WHERE assigned_department IS NOT NULL;

-- ============================================================================
-- MUNICIPALITIES TABLE
-- ============================================================================

-- List of municipalities for assignment dropdown
CREATE TABLE IF NOT EXISTS municipalities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    short_code TEXT,
    state TEXT,
    jurisdiction_geohashes TEXT[], -- Areas managed by this municipality
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some default municipalities (can be removed/updated)
INSERT INTO municipalities (id, name, short_code, state) VALUES
    ('ranchi_mc', 'Ranchi Municipal Corporation', 'RMC', 'Jharkhand'),
    ('jamshedpur_nac', 'Jamshedpur Notified Area Committee', 'JNAC', 'Jharkhand'),
    ('dhanbad_mc', 'Dhanbad Municipal Corporation', 'DMC', 'Jharkhand')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- DEPARTMENTS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS departments (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    municipality_id TEXT REFERENCES municipalities(id) ON DELETE CASCADE,
    categories TEXT[], -- Categories this department handles
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default departments
INSERT INTO departments (id, name, municipality_id, categories) VALUES
    ('roads', 'Roads & Infrastructure', NULL, ARRAY['pothole', 'road_damage', 'footpath']),
    ('sanitation', 'Sanitation & Waste', NULL, ARRAY['garbage', 'drainage', 'public_toilet']),
    ('electricity', 'Electricity', NULL, ARRAY['streetlight', 'power_outage']),
    ('water', 'Water Supply', NULL, ARRAY['water_supply', 'drainage', 'flooding']),
    ('traffic', 'Traffic & Transport', NULL, ARRAY['traffic_congestion', 'traffic_accident', 'road_closure']),
    ('general', 'General', NULL, ARRAY[]::TEXT[])
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- EXTEND ALERTS TABLE
-- ============================================================================

-- Add delivery tracking columns to alerts
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS sent_count INTEGER DEFAULT 0;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS delivered_count INTEGER DEFAULT 0;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS read_count INTEGER DEFAULT 0;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS failed_count INTEGER DEFAULT 0;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS target_count INTEGER DEFAULT 0;

COMMENT ON TABLE notifications IS 'In-app notifications shown in user notification bell';
COMMENT ON TABLE notification_queue IS 'Queue for async push/email notifications';
COMMENT ON TABLE municipalities IS 'List of municipalities for report assignment';
COMMENT ON TABLE departments IS 'Departments within municipalities for assignment';
