# Darshi - AI-Powered Civic Grievance Platform

[![Live Demo](https://img.shields.io/badge/demo-darshi.app-blue)](https://darshi.app)
[![Backend API](https://img.shields.io/badge/api-api.darshi.app-green)](https://api.darshi.app)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Darshi** (दर्शी) is an AI-powered civic grievance platform that enables citizens to report and track municipal issues like potholes, garbage, broken streetlights, and drainage problems. The platform uses Google Gemini 2.5 Flash AI to automatically verify and categorize reports, creating a transparent system for civic engagement in India.

---

## 🌟 Key Features

### For Citizens
- **📸 Visual Reporting** - Submit reports with photos and precise GPS locations
- **🤖 AI Verification** - Automated verification and categorization using Gemini 2.5 Flash
- **📍 Location Intelligence** - Nearby landmarks, human-readable addresses, interactive maps with Leaflet
- **🗳️ Community Engagement** - Upvote reports and add comments to increase visibility
- **🚨 Duplicate Detection** - Automatic duplicate detection using perceptual hashing + geolocation
- **🌐 Bilingual Support** - Full English and Hindi (हिन्दी) translation
- **🌙 Dark Mode** - Uber Black theme with pure black backgrounds
- **📱 Mobile Optimized** - Responsive design that works on all devices and screen sizes
- **🔐 Multiple Auth Methods** - Username/password, Google, GitHub, Facebook OAuth

### For Administrators
- **📊 Analytics Dashboard** - Track reports, categories, severity trends, and user activity
- **✅ Report Management** - Update status, add admin notes, manage report lifecycle
- **👥 User Management** - Create moderators, manage user roles and permissions
- **📈 Audit Logs** - Complete timeline of all admin actions with IP tracking
- **🎯 Smart Filtering** - Filter by status, category, severity, location, date range

### Technical Highlights
- **⚡ High Performance** - Redis caching, WebP image optimization (~30% smaller), async operations
- **🛡️ Robust Error Handling** - Circuit breakers for external APIs, retry logic, graceful degradation
- **🔒 Security First** - Tiered rate limiting, input sanitization, JWT auth, CORS protection
- **📦 Duplicate Detection** - Perceptual hash (dHash) + geohash proximity matching
- **🌍 Geospatial Features** - PostGIS spatial queries, geohash indexing, 5km radius search
- **🚀 CI/CD Pipeline** - GitHub Actions auto-deployment to Azure VPS with health checks
- **💾 Data Persistence** - Docker volumes survive all restarts and reboots

---

## 🏗️ Tech Stack (2025)

### Backend
- **FastAPI** (Python 3.11) - High-performance async web framework
- **PostgreSQL 15 + PostGIS** - Relational database with geospatial extensions
- **Redis 7** - Caching and rate limiting with AOF persistence
- **SQLAlchemy 2.0** - Async ORM with connection pooling
- **Alembic** - Database migrations
- **Gemini 2.5 Flash** - AI image analysis and verification
- **Cloudflare R2** - S3-compatible object storage (no egress fees)

### Frontend
- **SvelteKit 5** - Modern web framework with Runes API
- **TypeScript** - Type-safe development
- **Leaflet.js** - Interactive maps with OpenStreetMap tiles
- **Vite** - Lightning-fast build tool with HMR

### Infrastructure
- **Azure VPS** (16GB RAM, 4 vCPU, Ubuntu 22.04) - Self-hosted at 20.193.150.79
- **Docker + Docker Compose** - Containerization with health checks
- **Nginx** - Reverse proxy with SSL termination (Let's Encrypt)
- **Cloudflare Pages** - Frontend hosting with global CDN
- **GitHub Actions** - Automated CI/CD pipeline
- **Prometheus** - Metrics collection and monitoring
- **systemd** - Auto-restart containers on boot

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 15+ with PostGIS
- Redis 7+

### Local Development with Docker (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/Sarthak-Sidhant/darshi.git
cd darshi

# 2. Start PostgreSQL and Redis
docker compose up -d postgres redis

# 3. Backend setup
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and set:
# - DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/darshi
# - REDIS_URL=redis://localhost:6379/0
# - GEMINI_API_KEY (get from https://aistudio.google.com/app/apikey)
# - R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY (Cloudflare R2 credentials)
# - SECRET_KEY (generate with: python3 -c "import secrets; print(secrets.token_urlsafe(64))")

# 5. Initialize database
alembic upgrade head

# 6. Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Backend API: http://localhost:8080 | Swagger Docs: http://localhost:8080/docs

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend: http://localhost:5173

---

## 📖 Documentation

Comprehensive documentation is available in the [`/docs`](docs/) directory:

### Getting Started
- **[📚 Documentation Hub](docs/index.md)** - Start here for overview
- **[⚡ Quick Start Guide](docs/QUICK_START.md)** - Get running locally in 15 minutes
- **[💻 Development Guide](docs/guides/DEVELOPMENT.md)** - Developer workflow and best practices
- **[📋 CI/CD Setup](CI_CD_SETUP.md)** - GitHub Actions auto-deployment configuration

### Architecture & Deployment
- **[🏛️ Architecture Guide](docs/guides/ARCHITECTURE.md)** - System design, data models, tech decisions
- **[🚀 Deployment Guide](docs/guides/DEPLOYMENT.md)** - Production deployment on Azure VPS
- **[📡 API Reference](docs/guides/API.md)** - Complete API documentation (62 endpoints)

### Reference
- **[🎨 Philosophy](docs/reference/PHILOSOPHY.md)** - Development principles and conventions
- **[🤖 CLAUDE.md](CLAUDE.md)** - Instructions for Claude Code AI assistant

---

## 🔐 Authentication

Darshi supports multiple authentication methods:

1. **Username & Password** - Traditional login with JWT tokens (30-day expiry)
2. **Google OAuth** - Sign in with Google account
3. **GitHub OAuth** - Sign in with GitHub account
4. **Facebook OAuth** - Sign in with Facebook account

Admin users have separate JWT tokens with 1-hour expiry and require `super_admin` or `moderator` role.

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
9. ✅ Report visible on homepage
```

### Report Status Flow
```
PENDING_VERIFICATION → VERIFIED ──→ IN_PROGRESS ──→ RESOLVED
                    ↓           ↘               ↗
                 REJECTED       FLAGGED (system error)
                    ↓
                 DUPLICATE (links to original report)
```

---

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_reports.py -v
```

### Frontend Tests
```bash
cd frontend

# Run tests
npm run test

# Type checking
npm run check

# Build verification
npm run build
```

---

## 🚀 Deployment

### Production Infrastructure

**Current Setup:**
- **Frontend**: Cloudflare Pages (https://darshi.app)
- **Backend**: Azure VPS at 20.193.150.79 (https://api.darshi.app)
- **Database**: PostgreSQL 15 + PostGIS on Docker
- **Cache**: Redis 7 with AOF persistence on Docker
- **Storage**: Cloudflare R2 (S3-compatible)
- **CI/CD**: GitHub Actions auto-deploys on push to `main`

**Architecture:**
```
[User] → [Cloudflare Pages (Frontend)]
           ↓
       [Cloudflare Proxy]
           ↓
       [Azure VPS: Nginx → FastAPI → PostgreSQL + Redis]
           ↓
       [Cloudflare R2 (Images)]
```

### Deployment Method

Push to `main` branch triggers:
1. ✅ Run pytest (backend tests)
2. ✅ Run svelte-check (frontend type checks)
3. ✅ Build frontend (verify compilation)
4. ✅ SSH into VPS
5. ✅ Pull latest code
6. ✅ Rebuild Docker containers
7. ✅ Run health checks
8. ✅ Clean up old images
9. ✅ Deployment complete!

**Auto-Restart on Boot:**
- systemd service `darshi-deploy.service` ensures containers restart after VPS reboot
- All data persists in Docker volumes (postgres_data, redis_data, prometheus_data)

See [Deployment Guide](docs/guides/DEPLOYMENT.md) for detailed instructions.

---

## 📊 Key Statistics

- **62+ API Endpoints** - Complete REST API with OpenAPI docs
- **32 Custom Exception Types** - Structured error handling
- **5 Report Status States** - Comprehensive lifecycle tracking
- **7 Report Categories** - Pothole, Garbage, Streetlight, Drainage, Graffiti, Wildlife, Other
- **10 Severity Levels** - AI-assessed from 1 (minor) to 10 (critical)
- **3 User Roles** - Citizen, Moderator, Super Admin
- **Rate Limits** - Anonymous: 3/hr, Registered: 10/hr, Admin: unlimited

---

## 🛡️ Security Features

- **Input Sanitization** - All form data sanitized at router layer
- **Rate Limiting** - Redis-backed tiered rate limits
- **JWT Authentication** - Stateless auth with HS256 signing
- **Password Hashing** - bcrypt with 12 rounds
- **CORS Protection** - Explicit allowed origins (never wildcard)
- **Security Headers** - CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **File Validation** - Max 10MB per image, MIME type verification
- **SQL Injection Prevention** - Parameterized queries via SQLAlchemy ORM

---

## 📝 Contributing

We follow [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:

```bash
feat(scope): add new feature
fix(scope): resolve bug
refactor(scope): restructure code
perf(scope): improve performance
docs(scope): update documentation
test(scope): add/modify tests
chore(scope): build process, dependencies
```

**Examples:**
```bash
git commit -m "feat(reports): add duplicate detection with perceptual hashing"
git commit -m "fix(auth): resolve undefined username in delete endpoint"
git commit -m "docs(api): update endpoint documentation with rate limits"
```

See [Development Guide](docs/guides/DEVELOPMENT.md) for detailed contribution guidelines.

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Google Gemini AI** - Powering intelligent report verification
- **OpenStreetMap** - Providing free map tiles
- **Cloudflare** - CDN and R2 storage infrastructure
- **SvelteKit** - Modern frontend framework
- **FastAPI** - High-performance backend framework

---

## 📧 Contact

- **Live Site**: https://darshi.app
- **Backend API**: https://api.darshi.app
- **API Documentation**: https://api.darshi.app/docs
- **GitHub**: https://github.com/Sarthak-Sidhant/darshi

---

**Built with ❤️ for better civic engagement in India**

**Tech Stack**: FastAPI + PostgreSQL + Redis + SvelteKit 5 + Azure VPS + Cloudflare

**Version**: 2.0.0 (Azure Migration Complete - December 2025)
