# Darshi Azure VPS Migration Package

Complete migration toolkit to move Darshi from Google Cloud Platform to Azure VPS with zero-cost open-source alternatives.

## 📦 What's Included

This migration package contains everything you need to migrate Darshi to a cost-effective Azure VPS setup:

### Documentation
- **AZURE_MIGRATION_GUIDE.md** - Comprehensive step-by-step migration guide (6-8 hours)
- **MIGRATION_CHECKLIST.md** - Detailed checklist with every task
- **AZURE_CODE_CHANGES.md** - All required code modifications
- **QUICK_START_AZURE.md** - One-page quick reference

### Configuration Files
- **docker-compose.azure.yml** - Multi-container Docker setup
- **Dockerfile.azure** - Backend container configuration
- **frontend/Dockerfile.azure** - Frontend container configuration
- **nginx.conf** - Nginx reverse proxy configuration
- **.env.azure.example** - Environment variables template

### Migration Scripts
- **scripts/export_firestore.py** - Export data from Firestore
- **scripts/transform_to_postgres.py** - Convert Firestore JSON to PostgreSQL SQL
- **scripts/migrate_images_to_r2.py** - Migrate images from GCS to Cloudflare R2
- **scripts/requirements-migration.txt** - Dependencies for migration scripts

### Deployment
- **deploy-azure-vps.sh** - Automated VPS setup script
- **.github/workflows/deploy-azure.yml** - CI/CD pipeline with GitHub Actions

## 🏗️ New Architecture

| Component | Old (GCP) | New (Azure Stack) | Monthly Cost |
|-----------|-----------|-------------------|--------------|
| **Compute** | Cloud Run | Azure VPS (yours) + Docker | ₹0 |
| **Database** | Firestore | **Supabase PostgreSQL** | ₹0 (free 500MB) |
| **Storage** | Cloud Storage | **Cloudflare R2** | ₹0 (free 10GB) |
| **Cache** | Memorystore Redis | Self-hosted Redis | ₹0 |
| **CDN** | None | **Cloudflare CDN** | ₹0 |
| **Auth** | Firebase Auth | **Supabase Auth** | ₹0 |
| **Analytics** | BigQuery | PostgreSQL | ₹0 |
| **Monitoring** | None | **Grafana Cloud** | ₹0 |
| **CI/CD** | Cloud Build | **GitHub Actions** | ₹0 |

### Key Benefits

✅ **Zero Monthly Costs** - All services use free tiers
✅ **Better Performance** - Direct VPS control, no cold starts
✅ **Full Control** - Complete access to infrastructure
✅ **Scalable** - Your VPS can handle significant load
✅ **Modern Stack** - PostgreSQL + PostGIS for geospatial features
✅ **Easy Backups** - Supabase automated backups included

### Cost Savings

**Before:** ₹4,500/month (GCP)
**After:** ₹0/month (Azure VPS stack)
**Annual Savings:** ₹54,000

## 🚀 Getting Started

### Quick Start (Choose One)

#### Option 1: Automated Deployment (Recommended)
```bash
# SSH into your VPS
ssh user@your-vps-ip

# Run automated setup
wget https://raw.githubusercontent.com/yourusername/darshi/main/deploy-azure-vps.sh
chmod +x deploy-azure-vps.sh
./deploy-azure-vps.sh
```

#### Option 2: Manual Deployment
Follow **QUICK_START_AZURE.md** for step-by-step manual setup.

#### Option 3: Full Migration
Follow **AZURE_MIGRATION_GUIDE.md** for complete migration with data transfer.

### Prerequisites

Before starting, ensure you have:

1. **Azure VPS** - 4vCPU, 16GB RAM, SSH access
2. **Domain name** - With DNS control
3. **Accounts created:**
   - Supabase (https://supabase.com)
   - Cloudflare (https://cloudflare.com)
   - Grafana Cloud (https://grafana.com) - optional
4. **API keys:**
   - Gemini AI API key
   - Your existing credentials

## 📋 Migration Steps Overview

### Phase 1: Infrastructure Setup (30 minutes)
1. Create Supabase project and database
2. Create Cloudflare R2 bucket
3. Configure Cloudflare CDN
4. Set up Grafana monitoring (optional)

### Phase 2: Data Migration (1-2 hours)
1. Export Firestore data
2. Transform to PostgreSQL format
3. Import to Supabase
4. Migrate images to R2
5. Verify data integrity

### Phase 3: Code Updates (2-3 hours)
1. Update dependencies
2. Replace Firestore with PostgreSQL
3. Replace GCS with R2
4. Replace Firebase Auth with Supabase Auth
5. Test locally

### Phase 4: Deployment (1 hour)
1. Set up VPS with Docker
2. Deploy containers
3. Configure Nginx
4. Set up SSL with Let's Encrypt
5. Update DNS

### Phase 5: Verification (30 minutes)
1. Test all features
2. Monitor performance
3. Verify no errors
4. Run for 48 hours

### Phase 6: Cleanup (15 minutes)
1. Verify stability
2. Delete old GCP resources
3. Save costs

**Total Time:** 6-8 hours (can be done over weekend)

## 📚 Documentation Guide

### Start Here
1. Read this README (you are here!)
2. Review **QUICK_START_AZURE.md** for overview
3. Follow **MIGRATION_CHECKLIST.md** for step-by-step

### Deep Dive
- **AZURE_MIGRATION_GUIDE.md** - Complete guide with all commands
- **AZURE_CODE_CHANGES.md** - Detailed code modifications

### Reference
- **docker-compose.azure.yml** - Container configuration
- **nginx.conf** - Nginx setup
- **.env.azure.example** - Required environment variables

## 🛠️ Stack Details

### Backend
- **FastAPI** - Python web framework
- **PostgreSQL** - Primary database (via Supabase)
- **PostGIS** - Geospatial extension
- **Supabase** - Database hosting + Auth
- **Redis** - Caching layer (self-hosted)
- **Gunicorn** - Production WSGI server

### Frontend
- **SvelteKit 5** - Frontend framework
- **TypeScript** - Type safety
- **Supabase JS** - Auth client
- **Vite** - Build tool

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy + SSL termination
- **Cloudflare** - CDN + R2 storage
- **Let's Encrypt** - Free SSL certificates
- **Grafana Cloud** - Monitoring (optional)

### DevOps
- **GitHub Actions** - CI/CD pipeline
- **GitHub Container Registry** - Docker image storage

## 🔐 Security Features

- ✅ SSL/TLS encryption (Let's Encrypt)
- ✅ Rate limiting (Nginx + Redis)
- ✅ JWT authentication
- ✅ Row-level security (PostgreSQL RLS)
- ✅ Input sanitization
- ✅ Security headers
- ✅ Container isolation
- ✅ Non-root containers
- ✅ Secrets management

## 📊 Monitoring & Observability

### Built-in
- Docker container stats
- Nginx access/error logs
- Application logs (structured JSON)
- Health check endpoints

### Optional (Grafana Cloud)
- System metrics (CPU, memory, disk)
- Application metrics (requests, latency, errors)
- Custom dashboards
- Alerting (email, Slack, Telegram)

## 🔄 CI/CD Pipeline

Automated deployment with GitHub Actions:

1. **Trigger:** Push to main branch or manual trigger
2. **Build:** Build Docker images for backend + frontend
3. **Push:** Push images to GitHub Container Registry
4. **Deploy:** SSH into VPS, pull images, restart containers
5. **Verify:** Health check, notify on success/failure
6. **Monitor:** Check logs and metrics

## 🐛 Troubleshooting

### Common Issues

**Database connection fails**
```bash
# Verify DATABASE_URL is correct
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL -c "SELECT 1"
```

**Images not loading**
```bash
# Verify R2 configuration
aws s3 ls s3://darshi-reports --endpoint-url $R2_ENDPOINT

# Check public access
curl https://reports.darshi.app/reports/test.jpg
```

**Container won't start**
```bash
# Check logs
docker-compose -f docker-compose.azure.yml logs backend

# Inspect container
docker inspect darshi-backend
```

See **MIGRATION_CHECKLIST.md** for more troubleshooting tips.

## 📈 Performance Expectations

### Response Times (p95)
- API endpoints: <500ms
- Database queries: <100ms
- Image uploads: <2s
- Page loads: <3s

### Capacity (4vCPU, 16GB VPS)
- Concurrent users: 500-1000
- Requests/second: 100-200
- Database connections: 20 pooled
- Redis cache hit rate: >90%

## 🔄 Rollback Plan

If migration fails, you can easily rollback:

1. **DNS:** Point domain back to GCP Cloud Run
2. **Database:** Firestore still intact, no data loss
3. **Storage:** GCS images still available
4. **Auth:** Firebase Auth still active

**No data is deleted until you confirm migration success!**

## 🎯 Success Criteria

Migration is successful when:

- ✅ All users can login
- ✅ All features work correctly
- ✅ Performance is acceptable
- ✅ No errors in logs
- ✅ Monitoring shows healthy metrics
- ✅ Running stable for 48+ hours

## 📞 Support

### Self-Help Resources
1. Check documentation in this package
2. Review migration checklist
3. Check troubleshooting section
4. Review service logs

### External Documentation
- Supabase: https://supabase.com/docs
- Cloudflare R2: https://developers.cloudflare.com/r2/
- Docker: https://docs.docker.com/
- PostgreSQL: https://www.postgresql.org/docs/

### Community
- Supabase Discord: https://discord.supabase.com/
- Cloudflare Community: https://community.cloudflare.com/

## 📝 Migration Timeline

### Recommended Schedule

**Friday Evening (2 hours)**
- Set up Supabase project
- Create R2 bucket
- Configure Cloudflare
- Export Firestore data

**Saturday Morning (4 hours)**
- Migrate database
- Migrate images
- Update code
- Test locally

**Saturday Afternoon (2 hours)**
- Deploy to VPS
- Configure DNS
- Verify deployment

**Sunday**
- Monitor for issues
- Make adjustments
- Confirm stability

**Monday**
- Business as usual
- Monitor performance

**Next Weekend**
- Clean up GCP resources (after 7 days stable)

## 🎉 What's Next?

After successful migration:

1. **Set up automated backups**
   - Supabase auto-backups enabled
   - Manual PostgreSQL dumps
   - R2 bucket versioning

2. **Optimize performance**
   - Add database indexes
   - Tune PostgreSQL settings
   - Configure caching strategies

3. **Enhance monitoring**
   - Set up custom alerts
   - Create dashboards
   - Track key metrics

4. **Implement staging environment**
   - Clone production setup
   - Test changes before production
   - Use separate Supabase project

5. **Document your setup**
   - Runbooks for common tasks
   - Incident response procedures
   - Team knowledge base

## 🙏 Credits

This migration package was created to help teams move from expensive cloud platforms to cost-effective, open-source alternatives without sacrificing features or performance.

**Technologies Used:**
- Supabase (PostgreSQL hosting + Auth)
- Cloudflare (CDN + R2 storage)
- Docker (containerization)
- Nginx (reverse proxy)
- Grafana (monitoring)

## 📄 License

Same license as Darshi project.

---

**Ready to migrate?** Start with **QUICK_START_AZURE.md** or **MIGRATION_CHECKLIST.md**!

Questions? Check the documentation or create an issue on GitHub.

**Happy migrating! 🚀**
