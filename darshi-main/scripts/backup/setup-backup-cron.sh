#!/bin/bash
# Setup automated daily backups using cron
# Run this script once on the server to enable automatic backups

set -e

BACKUP_SCRIPT="/opt/darshi/backup-database.sh"
CRON_SCHEDULE="0 3 * * *"  # Daily at 3:00 AM
LOG_FILE="/opt/darshi/logs/backup.log"

echo "=== Setting up automated database backups ==="
echo ""
echo "Backup script: $BACKUP_SCRIPT"
echo "Schedule: $CRON_SCHEDULE (Daily at 3:00 AM)"
echo "Log file: $LOG_FILE"
echo ""

# Ensure backup script exists and is executable
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo "❌ ERROR: Backup script not found at $BACKUP_SCRIPT"
    exit 1
fi

chmod +x "$BACKUP_SCRIPT"
echo "✅ Backup script is executable"

# Create logs directory
mkdir -p "$(dirname $LOG_FILE)"
echo "✅ Log directory created"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo "⚠️  Cron job already exists. Removing old entry..."
    crontab -l | grep -v "$BACKUP_SCRIPT" | crontab -
fi

# Add cron job
echo "📅 Adding cron job..."
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $BACKUP_SCRIPT >> $LOG_FILE 2>&1") | crontab -

# Verify cron installation
echo ""
echo "✅ Cron job installed successfully!"
echo ""
echo "Current cron jobs:"
crontab -l | grep -v '^#' | grep -v '^$'

echo ""
echo "=== Setup complete ==="
echo ""
echo "📋 Next steps:"
echo "   1. Test backup manually: $BACKUP_SCRIPT"
echo "   2. Monitor logs: tail -f $LOG_FILE"
echo "   3. Backups will be stored in: /opt/darshi/backups"
echo "   4. Automatic rotation: backups older than 30 days are deleted"
echo ""
echo "💡 To restore from backup, use:"
echo "   ./restore-database.sh /opt/darshi/backups/darshi_backup_YYYYMMDD_HHMMSS.sql.gz"
