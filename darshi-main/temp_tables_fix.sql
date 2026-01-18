-- Migration 05: Flags and Audit Logging System
-- Part of Darshi Platform Overhaul Phase 1

-- ============================================================================
-- REPORT FLAGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS report_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id UUID NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    flag_type TEXT NOT NULL CHECK (flag_type IN ('fake_report', 'inappropriate', 'spam', 'request_update', 'other')),
    reason TEXT,
    image_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'actioned')),
    reviewed_by TEXT REFERENCES users(username),
    reviewed_at TIMESTAMPTZ,
    admin_note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_report_flags_pending ON report_flags(status, created_at DESC) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_report_flags_report ON report_flags(report_id);
CREATE INDEX IF NOT EXISTS idx_report_flags_user ON report_flags(user_id);

-- Rate limiting table for flags
CREATE TABLE IF NOT EXISTS flag_rate_limits (
    user_id TEXT PRIMARY KEY REFERENCES users(username) ON DELETE CASCADE,
    hourly_count INTEGER DEFAULT 0,
    daily_count INTEGER DEFAULT 0,
    last_flag_at TIMESTAMPTZ,
    hourly_reset_at TIMESTAMPTZ DEFAULT NOW(),
    daily_reset_at DATE DEFAULT CURRENT_DATE
);

-- ============================================================================
-- COMPREHENSIVE AUDIT LOGS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    actor_id TEXT REFERENCES users(username),
    actor_role TEXT,
    old_value JSONB,
    new_value JSONB,
    metadata JSONB DEFAULT '{}',
    ip_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Action types:
-- flag_created, flag_reviewed, flag_dismissed, flag_actioned
-- report_status_changed, report_assigned, report_merged
-- user_role_changed, user_verified, user_warned, user_banned
-- municipality_assigned, department_changed
-- update_created, update_deleted, update_flagged

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action_type);

-- ============================================================================
-- UPDATE FLAGS TABLE (for flagging individual updates)
-- ============================================================================

CREATE TABLE IF NOT EXISTS update_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    update_id UUID NOT NULL,  -- Will reference report_updates when that table exists
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    reason TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'dismissed', 'actioned')),
    reviewed_by TEXT REFERENCES users(username),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_update_flags_pending ON update_flags(status) WHERE status = 'pending';

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE report_flags IS 'User-submitted flags for reports (fake, inappropriate, spam, update request)';
COMMENT ON TABLE audit_logs IS 'Comprehensive audit trail for all moderation and administrative actions';
COMMENT ON TABLE flag_rate_limits IS 'Rate limiting for flag submissions to prevent abuse';
COMMENT ON TABLE update_flags IS 'Flags for individual report updates';

COMMENT ON COLUMN audit_logs.action_type IS 'Type of action: flag_*, report_*, user_*, municipality_*, update_*';
COMMENT ON COLUMN audit_logs.entity_type IS 'Entity type: report, user, flag, update, municipality';
COMMENT ON COLUMN audit_logs.old_value IS 'Previous state (for changes)';
COMMENT ON COLUMN audit_logs.new_value IS 'New state (for changes)';
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
