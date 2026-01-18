#!/bin/bash
# Complete District Migration Script
# Run this to set up district-based filtering end-to-end
#
# Usage: ./scripts/migrate_districts.sh
#
# This script:
# 1. Creates districts table (migration 15)
# 2. Adds district_code to broadcast_alerts (migration 16)  
# 3. Seeds districts table from LGD data
# 4. Backfills district_code in existing alerts

set -e

echo "==============================================="
echo "District Migration - Complete Setup"
echo "==============================================="

# Database connection (uses Azure connection by default)
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_NAME="${POSTGRES_DB:-darshi}"
DB_USER="${POSTGRES_USER:-darshi_app}"
PGPASSWORD="${POSTGRES_PASSWORD:-}"

export PGPASSWORD

# Function to run SQL
run_sql() {
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$1"
}

run_query() {
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "$1"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MIGRATIONS="$PROJECT_ROOT/migrations"

echo ""
echo "Step 1: Creating districts table..."
echo "-----------------------------------"
run_sql "$MIGRATIONS/15_districts.sql" || echo "Table may already exist, continuing..."

echo ""
echo "Step 2: Adding district_code to broadcast_alerts..."
echo "----------------------------------------------------"
run_sql "$MIGRATIONS/16_alter_alerts_for_districts.sql" || echo "Column may already exist, continuing..."

echo ""
echo "Step 3: Seeding districts from LGD data..."
echo "-------------------------------------------"

# Check if districts already seeded
COUNT=$(run_query "SELECT COUNT(*) FROM districts;" -t | tr -d ' ')
if [ "$COUNT" -gt "0" ]; then
    echo "Districts already seeded ($COUNT records)"
else
    # Use Python script to seed
    cd "$PROJECT_ROOT"
    python scripts/seed_districts.py
fi

echo ""
echo "Step 4: Backfilling district_code in existing alerts..."
echo "--------------------------------------------------------"

# Backfill district_code by matching district name
run_query "
UPDATE broadcast_alerts ba
SET district_code = d.district_code
FROM districts d
WHERE ba.district_code IS NULL
  AND LOWER(TRIM(ba.district)) = LOWER(TRIM(d.district_name))
  AND LOWER(TRIM(ba.state)) = LOWER(TRIM(d.state_name));
"

# Count results
FILLED=$(run_query "SELECT COUNT(*) FROM broadcast_alerts WHERE district_code IS NOT NULL;" -t | tr -d ' ')
TOTAL=$(run_query "SELECT COUNT(*) FROM broadcast_alerts;" -t | tr -d ' ')
MISSING=$(run_query "SELECT COUNT(*) FROM broadcast_alerts WHERE district_code IS NULL;" -t | tr -d ' ')

echo ""
echo "==============================================="
echo "Migration Complete!"
echo "==============================================="
echo ""
echo "Districts loaded: $COUNT"
echo "Alerts with district_code: $FILLED / $TOTAL"
echo "Alerts without district_code: $MISSING"
echo ""

if [ "$MISSING" -gt "0" ]; then
    echo "⚠️  Some alerts couldn't be matched. Check district name spellings."
    run_query "
    SELECT DISTINCT district, state 
    FROM broadcast_alerts 
    WHERE district_code IS NULL 
    LIMIT 10;
    "
fi
