# Darshi Documentation

> AI-powered civic grievance platform for reporting and tracking municipal issues

**Live Site:** https://darshi.app
**Backend API:** https://api.darshi.app

---

## 📚 Documentation Structure

### Getting Started
- [[quick_start|Quick Start Guide]] - Get Darshi running locally in 5 minutes
- [[guides/development/setup|Development Setup]] - Environment configuration
- [[../CLAUDE|CLAUDE.md]] - Essential developer reference

### API Documentation
- [[guides/api/overview|API Overview]] - Complete REST API reference (62 endpoints)
- [[guides/api/authentication|Authentication]] - JWT, OAuth, security
- [[guides/api/reports|Reports]] - CRUD operations for civic reports
- [[guides/api/geospatial|Geospatial]] - Geocoding, PostGIS queries
- [[guides/api/users|Users]] - Profile management
- [[guides/api/notifications|Notifications]] - Push notifications
- [[guides/api/admin|Admin]] - Administrative operations

### Architecture & Deployment
- [[guides/architecture/overview|Architecture Overview]] - System design and tech stack
- [[guides/architecture/backend-architecture|Backend Architecture]] - FastAPI, PostgreSQL, services
- [[guides/architecture/data-models|Data Models]] - PostgreSQL schema with PostGIS
- [[guides/deployment/overview|Deployment Overview]] - Production deployment on Azure VPS

### Reference
- [[reference/PHILOSOPHY|Philosophy]] - **READ THIS FIRST** - Development principles and conventions
- [[TAGS|Tags Index]] - Complete index of all documentation tags (85+ tags)

---

## 🏗️ Current Tech Stack (v2.0.0)

### Backend
- **FastAPI** (Python 3.11) - Async web framework
- **PostgreSQL 15 + PostGIS** - Relational database with geospatial extensions
- **Redis 7** - Caching and rate limiting (AOF persistence)
- **Gemini 2.5 Flash** - AI image verification
- **Cloudflare R2** - Object storage (S3-compatible)
- **Resend** - Email service

### Frontend
- **SvelteKit 5** - Web framework with Runes API ($state, $derived, $effect)
- **TypeScript 5.9+** - Type safety
- **Leaflet 1.9+** - Interactive maps
- **Vite 7.2+** - Build tool

### Infrastructure
- **Azure VPS** (16GB RAM, 4 vCPU, Ubuntu 22.04) - Self-hosted server
- **Docker + Docker Compose** - Container orchestration
- **Nginx** - Reverse proxy with SSL (Let's Encrypt)
- **GitHub Actions** - CI/CD pipeline
- **Prometheus** - Metrics and monitoring
- **Cloudflare Pages** - Frontend hosting (SSG)

### Stack Migration (December 2024)
**Previous (GCP)** → **Current (Azure/Self-hosted)**
- ~~Google Cloud Run~~ → Azure VPS + Docker
- ~~Firestore~~ → PostgreSQL 15 + PostGIS
- ~~Cloud Storage~~ → Cloudflare R2
- ~~Cloud Memorystore~~ → Self-hosted Redis
- ~~BigQuery~~ → PostgreSQL analytics
- ~~Firebase Hosting~~ → Cloudflare Pages

---

## 🚀 Quick Links

| Resource | URL |
|----------|-----|
| **Production Site** | https://darshi.app |
| **API Endpoint** | https://api.darshi.app/api/v1 |
| **API Docs (Swagger)** | https://api.darshi.app/docs |
| **GitHub Repository** | https://github.com/Sarthak-Sidhant/darshi |
| **CI/CD Dashboard** | https://github.com/Sarthak-Sidhant/darshi/actions |

---

## 📖 Key Features

### For Citizens
- **Report Civic Issues** - Potholes, broken streetlights, garbage, drainage, etc.
- **AI Verification** - Gemini 2.5 Flash auto-verifies reports with image analysis
- **Track Progress** - Timeline showing report status from submission to resolution
- **Upvote & Comment** - Community engagement on reports
- **Location-based Filtering** - Find issues near you
- **Duplicate Detection** - Automatic detection using perceptual hashing + geohashing
- **Bilingual Support** - English and Hindi (हिन्दी)
- **Dark Mode** - Uber Black theme

### For Administrators
- **Admin Dashboard** - Manage reports, users, and moderators
- **Status Management** - Update report status with notes
- **User Management** - Create moderators and admins
- **Analytics** - View trends and statistics
- **Audit Logs** - Track all admin actions

### Technical Features
- **OAuth Integration** - Google, GitHub, Facebook login
- **Real-time Updates** - WebSocket support for live notifications
- **Geospatial Queries** - PostGIS-powered location search
- **Image Optimization** - WebP conversion for 30% smaller files
- **Rate Limiting** - Tiered limits (anonymous: 3/hr, registered: 10/hr)
- **Offline Support** - Service worker for PWA capabilities
- **Responsive Design** - Mobile-first, works on all devices

---

## 🔐 Authentication Methods

### User Authentication
1. **Username/Password** - Traditional login with JWT tokens (30-day expiry)
2. **OAuth Providers** - Google, GitHub, Facebook via backend OAuth flow
3. **Email Verification** - Optional email verification for accounts

### Admin Authentication
- Separate JWT with 1-hour expiry
- Requires `role="super_admin"` or `role="moderator"`
- Two-factor authentication support (optional)

---

## 🗺️ Report Lifecycle

```
1. User submits report with image(s)
   ↓
2. Images uploaded to Cloudflare R2 (WebP optimized)
   ↓
3. Perceptual hash (dHash) calculated for duplicate detection
   ↓
4. Background task: AI verification with Gemini 2.5 Flash
   ↓
5. AI extracts: is_valid, category, severity, description
   ↓
6. Check for duplicates (perceptual hash + geohash proximity)
   ↓
7. Status updated: VERIFIED / REJECTED / DUPLICATE
   ↓
8. Timeline updated with state change event
   ↓
9. BigQuery analytics identifies hotspots (3+ severe issues in 24h)
```

### Report Status Flow
```
PENDING_VERIFICATION → VERIFIED ────→ IN_PROGRESS ──→ RESOLVED
                    ↓           ↘                ↗
                 REJECTED       FLAGGED (system error)
                    ↓
                 DUPLICATE (links to original report)
```

---

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+ with PostGIS
- Redis 7+
- Docker & Docker Compose (optional)

### Quick Start
```bash
# 1. Clone repository
git clone https://github.com/Sarthak-Sidhant/darshi.git
cd darshi

# 2. Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# 3. Start database & cache
docker compose up -d postgres redis

# 4. Run backend
uvicorn app.main:app --reload --port 8080

# 5. Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

Visit: http://localhost:5173

See **[QUICK_START.md](quick_start.md)** for detailed instructions.

---

## 🚀 Production Deployment

### Infrastructure
- **VPS:** Azure VM (16GB RAM, 4 vCPU, Ubuntu 22.04)
- **IP:** 20.193.150.79
- **Domains:**
  - darshi.app (frontend on Cloudflare Pages)
  - api.darshi.app (backend on Azure VPS)

### Deployment Method
- **CI/CD:** GitHub Actions auto-deploys on push to `main`
- **Containers:** Docker Compose with health checks
- **Persistence:** Docker volumes for data
- **Auto-restart:** systemd service `darshi-deploy.service`
- **SSL:** Cloudflare proxy + Let's Encrypt

### Data Persistence
All data survives VPS reboots:
- PostgreSQL database (`postgres_data` volume)
- Redis cache with AOF (`redis_data` volume)
- Prometheus metrics (`prometheus_data` volume)

See **[Deployment Guide](deployment.md)** for full details.

---

## 📊 Architecture Overview

### High-Level Architecture
```
[User Browser]
    ↓ HTTPS
[Cloudflare Pages] ← Frontend (SvelteKit)
    ↓ API Calls
[Cloudflare Proxy]
    ↓ HTTPS
[Nginx] ← Azure VPS (20.193.150.79)
    ↓
[Backend (FastAPI)] ← Docker Container (port 8080)
    ↓
[PostgreSQL] + [Redis] ← Docker Containers
    ↓
[Cloudflare R2] ← Image Storage
```

### Request Flow
1. User visits https://darshi.app (served by Cloudflare Pages)
2. Frontend makes API calls to https://api.darshi.app
3. Cloudflare proxy routes to Azure VPS (20.193.150.79)
4. Nginx reverse proxy forwards to backend container (port 8080)
5. Backend queries PostgreSQL, caches in Redis
6. Images served from Cloudflare R2 CDN

See **[Architecture Guide](architecture.md)** for detailed diagrams.

---

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_reports.py -v
```

### Frontend Tests
```bash
cd frontend

# Run tests
npm run test

# Watch mode
npm run test:watch

# With coverage
npm run test:coverage
```

---

## 📝 Contributing

### Commit Convention
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat(scope): add new feature
fix(scope): resolve bug
refactor(scope): restructure code
perf(scope): improve performance
docs(scope): update documentation
test(scope): add/modify tests
chore(scope): build process, dependencies
```

### Development Workflow
1. Create feature branch: `git checkout -b feat/my-feature`
2. Make changes and test locally
3. Run tests: `pytest` and `npm run test`
4. Commit with conventional format
5. Push to GitHub
6. CI/CD runs tests automatically
7. If tests pass, auto-deploys to production

See **[PHILOSOPHY.md](reference/PHILOSOPHY.md)** for coding standards.

---

## 🆘 Support & Resources

### Documentation
- **[API Reference](api.md)** - All 62 endpoints documented
- **[Development Guide](development.md)** - Setup and best practices
- **[Deployment Guide](deployment.md)** - Production hosting
- **[CI/CD Setup](../CI_CD_SETUP.md)** - GitHub Actions configuration

### Monitoring
- **GitHub Actions:** https://github.com/Sarthak-Sidhant/darshi/actions
- **API Health:** https://api.darshi.app/health
- **Prometheus:** http://20.193.150.79:9090 (VPS only)

### Getting Help
1. Check relevant documentation above
2. Review [PHILOSOPHY.md](reference/PHILOSOPHY.md) for conventions
3. Check GitHub Issues for similar problems
4. SSH into VPS and check Docker logs:
   ```bash
   ssh darshi@20.193.150.79
   docker logs darshi-backend --tail 100 -f
   ```

---

**Documentation Last Updated**: December 28, 2025
**Codebase Version**: 2.0.0 (Azure Migration Complete)
**Infrastructure**: Azure VPS + PostgreSQL + Docker + Cloudflare

---

## 📖 Documentation Notes

This documentation uses Obsidian-compatible wikilinks for easy navigation:
- `[[file]]` - Link to file in same directory
- `[[folder/file]]` - Link to file in subdirectory
- `[[file|Display Text]]` - Link with custom text

**Recommended**: Open this documentation in Obsidian for the best experience with graph view and bidirectional links.
