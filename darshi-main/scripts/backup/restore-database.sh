#!/bin/bash
# Restore PostgreSQL database from backup
# Usage: ./restore-database.sh <backup_file.sql.gz>

set -e

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: ./restore-database.sh <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    find /opt/darshi/backups -name "darshi_backup_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | head -10 | while read timestamp file; do
        size=$(du -h "$file" | cut -f1)
        date=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S")
        echo "  - $file ($size) - $date"
    done
    exit 1
fi

BACKUP_FILE="$1"

# Check if backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  WARNING: This will REPLACE the current database with the backup!"
echo "⚠️  Backup file: $BACKUP_FILE"
echo "⚠️  Target database: darshi (in darshi-postgres container)"
echo ""
read -p "Are you sure? Type 'yes' to continue: " -r
if [ "$REPLY" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q '^darshi-postgres$'; then
    echo "❌ ERROR: darshi-postgres container is not running!"
    exit 1
fi

echo "=== Starting database restore at $(date) ==="

# Create a pre-restore backup (just in case)
PRE_RESTORE_BACKUP="/opt/darshi/backups/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
echo "📦 Creating pre-restore backup: $PRE_RESTORE_BACKUP"
docker exec darshi-postgres pg_dump -U postgres -d darshi | gzip > "$PRE_RESTORE_BACKUP"

# Drop existing connections to the database
echo "🔌 Terminating active database connections..."
docker exec darshi-postgres psql -U postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='darshi' AND pid <> pg_backend_pid();"

# Drop and recreate database
echo "🗑️  Dropping existing database..."
docker exec darshi-postgres psql -U postgres -c "DROP DATABASE IF EXISTS darshi;"
echo "🆕 Creating fresh database..."
docker exec darshi-postgres psql -U postgres -c "CREATE DATABASE darshi;"

# Restore from backup
echo "📥 Restoring from backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i darshi-postgres psql -U postgres -d darshi

if [ $? -eq 0 ]; then
    echo "✅ Database restored successfully!"

    # Verify restoration
    echo "🔍 Verifying restoration..."
    REPORT_COUNT=$(docker exec darshi-postgres psql -U postgres -d darshi -t -c "SELECT COUNT(*) FROM reports;")
    USER_COUNT=$(docker exec darshi-postgres psql -U postgres -d darshi -t -c "SELECT COUNT(*) FROM users;")
    echo "   - Reports: $REPORT_COUNT"
    echo "   - Users: $USER_COUNT"
else
    echo "❌ Restore failed!"
    echo "💡 Pre-restore backup available at: $PRE_RESTORE_BACKUP"
    exit 1
fi

echo "=== Restore completed at $(date) ==="
echo ""
echo "🎉 Database restored from: $BACKUP_FILE"
echo "💾 Pre-restore backup saved at: $PRE_RESTORE_BACKUP"
