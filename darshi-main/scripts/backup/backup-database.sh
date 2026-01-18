#!/bin/bash
# Automated PostgreSQL backup script for Darshi
# Backs up database to local directory with rotation

set -e

# Configuration
BACKUP_DIR="/opt/darshi/backups"
RETENTION_DAYS=30  # Keep backups for 30 days
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/darshi_backup_${TIMESTAMP}.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "=== Starting PostgreSQL backup at $(date) ==="

# Check if postgres container is running
if ! docker ps --format '{{.Names}}' | grep -q '^darshi-postgres$'; then
    echo "❌ ERROR: darshi-postgres container is not running!"
    exit 1
fi

# Perform backup using pg_dump
echo "📦 Creating backup: $BACKUP_FILE"
docker exec darshi-postgres pg_dump -U postgres -d darshi | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ] && [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup successful! Size: $BACKUP_SIZE"
    echo "   Location: $BACKUP_FILE"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Remove old backups (older than RETENTION_DAYS)
echo "🗑️  Cleaning up old backups (keeping last ${RETENTION_DAYS} days)..."
find "$BACKUP_DIR" -name "darshi_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

# List current backups
BACKUP_COUNT=$(find "$BACKUP_DIR" -name "darshi_backup_*.sql.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
echo "📊 Total backups: ${BACKUP_COUNT} (${TOTAL_SIZE})"

# Show 5 most recent backups
echo "📁 Recent backups:"
find "$BACKUP_DIR" -name "darshi_backup_*.sql.gz" -type f -printf "%T@ %p\n" | sort -rn | head -5 | while read timestamp file; do
    size=$(du -h "$file" | cut -f1)
    date=$(date -d "@$timestamp" "+%Y-%m-%d %H:%M:%S")
    echo "   - $(basename $file) ($size) - $date"
done

echo "=== Backup completed at $(date) ==="
