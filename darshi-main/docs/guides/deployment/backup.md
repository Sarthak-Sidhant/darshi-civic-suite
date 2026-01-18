# Database Backup & Recovery System

## Overview

This directory contains scripts for automated PostgreSQL database backups with disaster recovery capabilities.

## ⚠️ CRITICAL: Data Protection Rules

1. **NEVER run `docker-compose down -v`** - This deletes all data volumes!
2. **Always use `docker-compose down`** (without `-v`) to preserve data
3. **The `fix-deployment.sh` script has been fixed** - It now preserves volumes by default
4. **Backups run automatically** at 3:00 AM daily (after cron setup)

## Scripts

### 1. `backup-database.sh` - Create Backups
Creates a compressed backup of the PostgreSQL database.

```bash
# Manual backup
./backup-database.sh

# Output: /opt/darshi/backups/darshi_backup_YYYYMMDD_HHMMSS.sql.gz
```

**Features:**
- Compressed with gzip (saves ~70% space)
- Automatic rotation (keeps 30 days)
- Backup verification
- Size reporting

### 2. `restore-database.sh` - Restore from Backup
Restores the database from a backup file.

```bash
# List available backups
./restore-database.sh

# Restore specific backup
./restore-database.sh /opt/darshi/backups/darshi_backup_20250128_030000.sql.gz
```

**Safety Features:**
- Confirmation prompt before restore
- Creates pre-restore backup automatically
- Terminates active connections safely
- Verifies restoration

### 3. `setup-backup-cron.sh` - Enable Automated Backups
Sets up daily automatic backups via cron.

```bash
# Run once on the server
./setup-backup-cron.sh
```

**Configuration:**
- Schedule: Daily at 3:00 AM
- Logs: `/opt/darshi/logs/backup.log`
- Retention: 30 days

## Installation (One-Time Setup)

Run these commands on the Azure VPS:

```bash
# 1. Navigate to project directory
cd /opt/darshi

# 2. Make scripts executable
chmod +x backup-database.sh restore-database.sh setup-backup-cron.sh

# 3. Set up automated backups
./setup-backup-cron.sh

# 4. Test manual backup
./backup-database.sh
```

## Backup Storage

**Location:** `/opt/darshi/backups/`

**Naming:** `darshi_backup_YYYYMMDD_HHMMSS.sql.gz`

**Retention Policy:**
- Automatic: 30 days (older backups deleted)
- Manual backups: Keep indefinitely
- Pre-restore backups: Named `pre_restore_*.sql.gz`

## Recovery Scenarios

### Scenario 1: Accidental Data Loss
```bash
# 1. List available backups
./restore-database.sh

# 2. Choose most recent backup before incident
./restore-database.sh /opt/darshi/backups/darshi_backup_20250127_030000.sql.gz

# 3. Restart backend to reconnect
docker-compose -f docker-compose.azure.yml restart backend
```

### Scenario 2: Volume Accidentally Deleted
```bash
# 1. Recreate containers (data will be empty)
docker-compose -f docker-compose.azure.yml up -d

# 2. Wait for PostgreSQL to initialize
sleep 10

# 3. Restore from latest backup
./restore-database.sh /opt/darshi/backups/darshi_backup_20250127_030000.sql.gz
```

### Scenario 3: Corruption or Schema Issues
```bash
# 1. Backup current state (for forensics)
./backup-database.sh

# 2. Restore from known good backup
./restore-database.sh /opt/darshi/backups/darshi_backup_20250126_030000.sql.gz
```

## Monitoring

### Check Backup Status
```bash
# View backup logs
tail -f /opt/darshi/logs/backup.log

# List recent backups
ls -lh /opt/darshi/backups/ | tail -10

# Check cron jobs
crontab -l
```

### Verify Last Backup
```bash
# Check if backup ran today
ls -lh /opt/darshi/backups/darshi_backup_$(date +%Y%m%d)*.sql.gz
```

## Troubleshooting

### Backup Fails with "Container not running"
```bash
# Check container status
docker ps | grep darshi-postgres

# Restart if needed
docker-compose -f docker-compose.azure.yml restart postgres
```

### Restore Fails with Permission Denied
```bash
# Ensure scripts are executable
chmod +x backup-database.sh restore-database.sh

# Check file ownership
ls -l /opt/darshi/backups/
```

### Cron Job Not Running
```bash
# Verify cron service
systemctl status cron

# Check cron logs
grep CRON /var/log/syslog | tail -20

# Manually test backup
./backup-database.sh
```

## Best Practices

1. **Test Restores Regularly**
   - Monthly test restore to verify backups work
   - Use a test environment if available

2. **Monitor Disk Space**
   ```bash
   df -h /opt/darshi/backups
   ```

3. **Off-Site Backups** (Recommended)
   - Sync backups to cloud storage (S3, R2, etc.)
   - Example: `rclone sync /opt/darshi/backups/ cloudflare:darshi-backups/`

4. **Before Major Changes**
   ```bash
   # Always backup before:
   # - Schema migrations
   # - Major deployments
   # - Docker rebuilds
   ./backup-database.sh
   ```

5. **Document Incidents**
   - Keep notes on what was restored and why
   - Store in `/opt/darshi/backups/INCIDENTS.log`

## Security Notes

- Backups contain sensitive user data
- Restrict access: `chmod 700 /opt/darshi/backups/`
- Don't commit backups to Git
- Encrypt backups for off-site storage

## Emergency Contacts

If disaster recovery fails:
1. Check `/opt/darshi/backups/pre_restore_*.sql.gz` for safety backups
2. Images are safe in Cloudflare R2 (`darshi-reports` bucket)
3. Contact: [Your contact information]

## File Locations

```
/opt/darshi/
├── backup-database.sh          # Create backups
├── restore-database.sh         # Restore from backup
├── setup-backup-cron.sh        # Enable automation
├── backups/                    # Backup storage
│   ├── darshi_backup_*.sql.gz  # Daily backups
│   └── pre_restore_*.sql.gz    # Safety backups
└── logs/
    └── backup.log              # Backup operation logs
```

## Version History

- **2025-01-28**: Initial backup system created after data loss incident
  - Automatic daily backups at 3 AM
  - 30-day retention
  - Fixed `fix-deployment.sh` to preserve volumes
