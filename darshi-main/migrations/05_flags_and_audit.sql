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
