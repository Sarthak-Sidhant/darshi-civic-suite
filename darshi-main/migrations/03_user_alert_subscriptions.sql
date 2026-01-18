-- Migration: User Alert Subscriptions for Nagar Alert Hub
-- Allows users to subscribe to alerts by location and category

-- 1. USER ALERT SUBSCRIPTIONS TABLE
-- Stores user preferences for receiving location-based alerts
CREATE TABLE IF NOT EXISTS user_alert_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    
    -- Location preferences
    home_geohash TEXT,              -- Primary location (auto-derived from user profile)
    work_geohash TEXT,              -- Secondary location (optional)
    custom_geohashes TEXT[],        -- Additional locations to monitor
    subscription_radius_km FLOAT DEFAULT 5.0,
    
    -- Alert preferences  
    categories TEXT[] DEFAULT ARRAY['traffic', 'power', 'water', 'safety', 'community'],
    severity_threshold TEXT DEFAULT 'low', -- low, medium, high, critical
    enabled BOOLEAN DEFAULT TRUE,
    
    -- Notification channels (for future WhatsApp integration)
    notify_in_app BOOLEAN DEFAULT TRUE,
    notify_whatsapp BOOLEAN DEFAULT FALSE,
    whatsapp_number TEXT,
    
    -- Quiet hours
    quiet_hours_start TIME,         -- e.g., 22:00
    quiet_hours_end TIME,           -- e.g., 07:00
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_user_subs_user ON user_alert_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subs_home_geohash ON user_alert_subscriptions(home_geohash);
CREATE INDEX IF NOT EXISTS idx_user_subs_enabled ON user_alert_subscriptions(enabled) WHERE enabled = TRUE;


-- 2. ALERT DELIVERY LOG (for tracking what was sent to whom)
CREATE TABLE IF NOT EXISTS alert_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(username) ON DELETE CASCADE,
    
    channel TEXT NOT NULL DEFAULT 'in_app',  -- in_app, whatsapp, email
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, sent, delivered, read, failed
    
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_delivery_alert ON alert_delivery_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_alert_delivery_user ON alert_delivery_log(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_delivery_status ON alert_delivery_log(status);


-- 3. ADD ADDITIONAL COLUMNS TO ALERTS TABLE (if not present)
-- These enhance the alerts table from migration 02

-- Track sent count and reach
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'alerts' AND column_name = 'sent_count') THEN
        ALTER TABLE alerts ADD COLUMN sent_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'alerts' AND column_name = 'delivery_count') THEN
        ALTER TABLE alerts ADD COLUMN delivery_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'alerts' AND column_name = 'read_count') THEN
        ALTER TABLE alerts ADD COLUMN read_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'alerts' AND column_name = 'updated_at') THEN
        ALTER TABLE alerts ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;
