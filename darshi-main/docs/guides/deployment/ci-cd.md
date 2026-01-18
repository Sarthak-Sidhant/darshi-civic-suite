# CI/CD Setup Guide

## ✅ What's Been Configured

### 1. **GitHub Actions Workflow** (`.github/workflows/deploy.yml`)
- Runs on every push to `main` branch
- **Test Stage**: Runs pytest, frontend type checks, and build verification
- **Deploy Stage**: Auto-deploys to VPS if tests pass
- **Verification**: Health checks after deployment
- **Cleanup**: Removes old Docker images to save disk space

### 2. **Docker Volume Persistence**
All data persists across container restarts:
- `postgres_data` - PostgreSQL database (reports, users, comments)
- `redis_data` - Redis cache with AOF persistence
- `prometheus_data` - Prometheus metrics (7 days retention)

### 3. **Systemd Auto-Restart Service**
- Service: `darshi-deploy.service`
- Automatically starts Docker containers on VPS reboot
- Graceful shutdown on system stop
- Enabled and ready for next reboot

---

## 🔑 GitHub Secrets Setup

You MUST add these secrets to your GitHub repository for CI/CD to work:

### Go to: `https://github.com/Sarthak-Sidhant/darshi/settings/secrets/actions`

Click **"New repository secret"** and add each of these:

#### 1. `VPS_SSH_KEY` (Required)
**Value:**
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAe9r4BKLz74zkp2ojlrQ8Jxuqylq0LLZ5iJqQMNuExDAAAAJixU/25sVP9
uQAAAAtzc2gtZWQyNTUxOQAAACAe9r4BKLz74zkp2ojlrQ8Jxuqylq0LLZ5iJqQMNuExDA
AAAEDDQ35u4OsJ3Q0mBqB8SvskwthD0FEwUnLW+YzPM2VDBx72vgEovPvjOSnaiOWtDwnG
6rKWrQstnmImpAw24TEMAAAAFWdpdGh1Yi1hY3Rpb25zQGRhcnNoaQ==
-----END OPENSSH PRIVATE KEY-----
```
**Description:** SSH private key for GitHub Actions to connect to VPS

#### 2. `VPS_HOST` (Required)
**Value:** `20.193.150.79`
**Description:** Your Azure VPS IP address

#### 3. `VPS_USER` (Required)
**Value:** `darshi`
**Description:** SSH user on VPS

---

## 🚀 How It Works

### Automatic Deployment Flow:
```
1. You push code to GitHub main branch
   ↓
2. GitHub Actions starts workflow
   ↓
3. Run backend tests (pytest)
   ↓
4. Run frontend type checks (svelte-check)
   ↓
5. Build frontend to verify it compiles
   ↓
6. If tests pass → SSH into VPS
   ↓
7. Pull latest code from GitHub
   ↓
8. Rebuild Docker containers
   ↓
9. Wait for services to be healthy
   ↓
10. Run health checks on backend
   ↓
11. Verify frontend files exist
   ↓
12. Clean up old Docker images
   ↓
13. ✅ Deployment complete!
```

### On VPS Reboot:
```
1. VPS reboots
   ↓
2. Docker service starts
   ↓
3. darshi-deploy.service starts
   ↓
4. Runs: docker compose up -d
   ↓
5. All containers restored with persistent data
   ↓
6. ✅ App is live again automatically
```

---

## 📋 Testing the CI/CD Pipeline

### Option 1: Manual Trigger (Recommended for first test)
1. Go to: `https://github.com/Sarthak-Sidhant/darshi/actions/workflows/deploy.yml`
2. Click **"Run workflow"** → Select `main` branch → **"Run workflow"**
3. Watch the logs in real-time

### Option 2: Push a Test Commit
```bash
# Make a small change (add newline to README)
echo "" >> README.md
git add README.md
git commit -m "test: trigger CI/CD pipeline"
git push origin main

# Watch the deployment
# Go to: https://github.com/Sarthak-Sidhant/darshi/actions
```

---

## 🔍 Monitoring Deployments

### GitHub Actions Dashboard
- **URL:** `https://github.com/Sarthak-Sidhant/darshi/actions`
- View all workflow runs, logs, and deployment status
- Get email notifications on failure (configurable in Settings)

### VPS Logs (SSH into VPS)
```bash
# SSH into VPS
ssh darshi@20.193.150.79

# View container status
docker ps

# View backend logs
docker logs darshi-backend --tail 100 -f

# View frontend logs
docker logs darshi-frontend --tail 100 -f

# View systemd service logs
sudo journalctl -u darshi-deploy.service -f
```

---

## 🛡️ Data Persistence Verification

### Check Docker Volumes
```bash
ssh darshi@20.193.150.79

# List all volumes
docker volume ls

# Inspect postgres volume
docker volume inspect darshi_postgres_data

# Check volume size
docker system df -v
```

### Database Backup (Recommended)
```bash
# Create backup script
ssh darshi@20.193.150.79 'cat > ~/backup-database.sh << "EOF"
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
docker exec darshi-postgres pg_dump -U postgres darshi | gzip > $BACKUP_DIR/darshi_$(date +%Y%m%d_%H%M%S).sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "darshi_*.sql.gz" -mtime +7 -delete
echo "Backup complete: $(ls -lh $BACKUP_DIR | tail -1)"
EOF'

# Make executable
ssh darshi@20.193.150.79 'chmod +x ~/backup-database.sh'

# Run backup manually
ssh darshi@20.193.150.79 '~/backup-database.sh'

# Or setup daily cron job
ssh darshi@20.193.150.79 'crontab -e'
# Add line: 0 2 * * * /home/darshi/backup-database.sh
```

---

## 🔧 Troubleshooting

### CI/CD Pipeline Fails
**Problem:** Workflow shows red X
**Solution:**
1. Click on failed workflow run
2. Expand the failed step to see error logs
3. Common issues:
   - Missing GitHub secrets → Add them in Settings
   - Tests failing → Fix code and push again
   - SSH connection failed → Check VPS is online

### VPS Containers Don't Start on Reboot
**Problem:** After VPS reboot, site is down
**Solution:**
```bash
ssh darshi@20.193.150.79

# Check systemd service status
sudo systemctl status darshi-deploy.service

# Check Docker service
sudo systemctl status docker

# Manually start containers
cd /opt/darshi
docker compose -f docker-compose.azure.yml up -d

# View logs
docker ps -a
docker logs darshi-backend
```

### Disk Space Full
**Problem:** Docker fills up disk with old images
**Solution:**
```bash
ssh darshi@20.193.150.79

# Check disk usage
df -h
docker system df

# Clean up (workflow does this automatically)
docker image prune -af --filter "until=24h"
docker volume prune -f
docker builder prune -af
```

---

## 📊 What's Protected

### Data That Persists (survives reboots/restarts):
✅ PostgreSQL database (all reports, users, comments)
✅ Redis cache (with AOF persistence)
✅ Prometheus metrics (7 days)
✅ Nginx SSL certificates (`./ssl` mounted)
✅ Application logs (`./logs` mounted)

### Data That's Ephemeral (rebuilt on deploy):
❌ Docker images (rebuilt from Dockerfile)
❌ Container filesystems (recreated)
❌ In-memory caches (cleared on restart)

---

## 🎉 Success Criteria

Your CI/CD is working correctly if:

1. ✅ Pushing to `main` triggers GitHub Actions workflow
2. ✅ Tests pass (green checkmark)
3. ✅ Deployment completes successfully
4. ✅ Site is accessible at https://darshi.app
5. ✅ After VPS reboot, containers auto-start
6. ✅ Database data persists across restarts

---

## 📝 Next Steps

1. **Add GitHub Secrets** (see section above)
2. **Test the pipeline** with a dummy commit
3. **Verify VPS reboot recovery** (optional):
   ```bash
   ssh darshi@20.193.150.79 'sudo reboot'
   # Wait 2-3 minutes, then check: https://darshi.app
   ```
4. **Setup daily database backups** (see backup section)
5. **Monitor first few deployments** to ensure stability

---

## 🆘 Getting Help

If something goes wrong:
1. Check GitHub Actions logs
2. SSH into VPS and check Docker logs
3. Verify all secrets are set correctly
4. Check VPS disk space: `df -h`
5. Check container status: `docker ps -a`

**Emergency Rollback:**
```bash
ssh darshi@20.193.150.79
cd /opt/darshi
git log --oneline -10  # Find previous working commit
git reset --hard <commit-hash>
docker compose -f docker-compose.azure.yml up -d --build
```
