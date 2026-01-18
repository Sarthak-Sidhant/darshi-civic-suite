-- Migration 08: Enhanced Roles and Badges
-- Part of Darshi Platform Overhaul Phase 5

-- Add badges (array of strings) and reputation (integer)
ALTER TABLE users ADD COLUMN IF NOT EXISTS badges TEXT[] DEFAULT '{}';
ALTER TABLE users ADD COLUMN IF NOT EXISTS reputation INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS municipality_id TEXT; -- Link officials to municipalities (matches municipalities.id which is TEXT)

-- Index for leaderboards
CREATE INDEX IF NOT EXISTS idx_users_reputation ON users(reputation DESC);

-- Comment
COMMENT ON COLUMN users.badges IS 'Array of earned badges (e.g. local_guide, top_reporter)';
COMMENT ON COLUMN users.reputation IS 'User reputation score based on report verification and upvotes';
