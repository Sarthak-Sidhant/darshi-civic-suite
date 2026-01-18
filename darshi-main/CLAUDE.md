# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT**: Before making any changes, read [[docs/reference/PHILOSOPHY|PHILOSOPHY]] for development workflow, design principles, error handling standards, logging guidelines, and commit conventions.

## Quick Reference

**Project**: Darshi - AI-powered civic grievance platform for reporting and tracking municipal issues
**Tech Stack**: FastAPI + Python 3.11 (backend) | SvelteKit 5 + TypeScript (frontend) | Azure VPS + PostgreSQL + Docker (infrastructure)
**Live**: https://darshi.app | Backend: https://api.darshi.app

## Current Technology Stack

### Backend
- **Framework**: FastAPI (async Python 3.11)
- **Database**: PostgreSQL 15 + PostGIS (self-hosted)
- **Cache**: Redis 7 (self-hosted, AOF persistence)
- **Storage**: Cloudflare R2 (S3-compatible)
- **AI**: Google Gemini 2.5 Flash
- **Email**: Resend API
- **Hosting**: Azure VPS (4 vCPU, 16GB RAM)
- **Orchestration**: Docker Compose 3.8

### Frontend
- **Framework**: SvelteKit 5 (Runes API)
- **Language**: TypeScript 5.9+
- **Build**: Vite 7.2+
- **Maps**: Leaflet.js 1.9+
- **Hosting**: Cloudflare Pages (SSG)

### Infrastructure
- **Server**: Azure VPS (20.193.150.79)
- **Reverse Proxy**: Nginx + Let's Encrypt
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus
- **Containers**: Docker + Docker Compose

## Common Commands

### Backend Development

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.azure.example .env  # Edit with your values

# Start local database (Docker)
docker compose up -d postgres redis

# Run development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Run tests
pytest                          # All tests
pytest -v                       # Verbose
pytest -k "test_name"          # Specific test
pytest --cov=app               # With coverage

# Database migrations
alembic upgrade head            # Apply migrations
alembic revision --autogenerate -m "message"  # Create migration
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Configure environment (optional - has defaults)
cp .env.example .env

# Run development server (auto-reload on changes)
npm run dev

# Type checking (watch mode for active development)
npm run check:watch

# Type checking (single check)
npm run check

# Build for production
npm run build

# Preview production build locally
npm run preview

# Run tests
npm run test              # Run all tests once
npm run test:watch        # Watch mode
npm run test:coverage     # With coverage report
```

### Docker Compose (Production)

```bash
# Start all services
docker compose -f docker-compose.azure.yml up -d

# View logs
docker logs darshi-backend -f
docker logs darshi-postgres -f
docker logs darshi-redis -f

# Stop all services
docker compose -f docker-compose.azure.yml down

# Rebuild and restart
docker compose -f docker-compose.azure.yml up -d --build

# Check health
curl http://localhost:8080/health
```

## Architecture Overview

### Backend Structure (`/app`)

```
app/
├── main.py                    # FastAPI application, middleware, CORS, exception handlers
├── core/                      # Shared utilities and infrastructure
│   ├── config.py             # Environment variables, settings (Pydantic)
│   ├── exceptions.py         # 32 custom exception types
│   ├── error_handling.py     # Circuit breakers, retry decorators, error context
│   ├── security.py           # JWT, bcrypt, rate limiting, input sanitization
│   ├── validation.py         # Input validators (coords, files, strings)
│   ├── logging_config.py     # Structured logging with Sentry
│   ├── redis_client.py       # Redis connection management
│   ├── cache.py              # Caching layer with Redis fallback
│   └── http_client.py        # Shared httpx client with retry logic
├── db/                        # Database layer (PostgreSQL + SQLAlchemy)
│   ├── session.py            # AsyncSession management
│   ├── models.py             # SQLAlchemy ORM models
│   └── migrations/           # Alembic migrations
├── routers/                   # API endpoints (route handlers)
│   ├── reports.py            # Report CRUD, upvotes, comments
│   ├── admin.py              # Admin dashboard, analytics, audit logs
│   ├── auth.py               # Username/password + magic link authentication
│   ├── oauth.py              # OAuth (Google, GitHub, Facebook)
│   ├── users.py              # User management
│   └── notifications.py      # Push notification subscriptions
├── services/                  # Business logic layer
│   ├── postgres_service.py   # PostgreSQL operations (asyncpg)
│   ├── ai_service.py         # Gemini image analysis with circuit breaker
│   ├── storage_service.py    # Cloudflare R2 uploads (boto3, WebP optimization)
│   ├── geo_service.py        # Geocoding, geohashing, proximity queries
│   ├── auth_service.py       # JWT tokens, password hashing
│   ├── admin_service.py      # Admin operations
│   ├── notification_service.py # Push notifications (WebPush)
│   ├── email_service.py      # Email via Resend API
│   ├── image_service.py      # Image hashing (dHash), duplicate detection
│   └── oauth_service.py      # OAuth provider integration
├── models/                    # Pydantic schemas for request/response
└── middleware/                # Custom middleware (performance monitoring)
```

### Frontend Structure (`/frontend`)

```
frontend/
├── src/
│   ├── routes/                           # SvelteKit pages (file-based routing)
│   │   ├── +page.svelte                 # Home - reports list, hotspot alerts
│   │   ├── submit/+page.svelte          # Submit report form (GPS, geocoding)
│   │   ├── report/[id]/+page.svelte     # Report detail (comments, timeline)
│   │   ├── signin/+page.svelte          # Sign-in (OAuth, credentials, phone, email)
│   │   ├── register/+page.svelte        # User registration
│   │   └── admin/+page.svelte           # Admin dashboard
│   └── lib/                              # Shared frontend code
│       ├── api.ts                        # API client with error handling
│       ├── validation.ts                 # Form validation utilities
│       ├── stores.ts                     # Svelte stores (user, auth)
│       ├── stores/                       # Additional stores (toast)
│       └── components/                   # Reusable UI components
│           ├── Toast.svelte              # Toast notifications
│           ├── LoadingButton.svelte      # Buttons with loading states
│           └── LoadingSpinner.svelte     # Loading indicators
├── static/                               # Static assets (images, fonts)
├── svelte.config.js                      # SvelteKit configuration
├── vite.config.ts                        # Vite configuration
└── tsconfig.json                         # TypeScript configuration
```

## Core Concepts

### Report Lifecycle

1. **Submission** → User submits report with image(s) via POST `/api/v1/report`
2. **Upload** → Images uploaded to Cloudflare R2 with WebP optimization
3. **Hashing** → Calculate perceptual hash (dHash) for duplicate detection
4. **Background Processing** → AI verification task queued
   - Download image from R2
   - Analyze with Gemini AI (gemini-2.5-flash)
   - Extract: `is_valid`, `category`, `severity`, `description`
   - Check for duplicates (perceptual hash + geohash proximity)
   - Update status: `VERIFIED`, `REJECTED`, or `DUPLICATE`
5. **Timeline** → All state changes tracked in `timeline` JSONB column for audit trail
6. **PostGIS Indexing** → Spatial queries for nearby reports

### Report Status Flow

```
PENDING_VERIFICATION  →  VERIFIED ────→ IN_PROGRESS ──→ RESOLVED
                     ↓            ↘                ↗
                  REJECTED        FLAGGED (system error)
                     ↓
                  DUPLICATE (links to original report)
```

### Authentication Methods

1. **Username/Password** → JWT tokens (30-day expiry)
2. **Magic Link (Passwordless)** → One-time email links (15-min expiry, auto-creates accounts)
3. **OAuth** → Google, GitHub, Facebook via OAuth 2.0
4. **Admin** → Separate JWT with 1-hour expiry, requires `role="admin"`

### Error Handling Architecture (3-Layer Defense)

**Layer 1: Prevention**
- Input validation at router layer (`core/validation.py`)
- Type checking (Pydantic models, TypeScript interfaces)
- Sanitization (`sanitize_form_data()`)

**Layer 2: Recovery**
- Retry decorators: `@retry_database_operation`, `@retry_ai_operation`, `@retry_storage_operation`
- Circuit breakers: Gemini (5 failures/120s), Nominatim (3 failures/60s)
- Graceful degradation (continue with partial data)

**Layer 3: Communication**
- Structured error responses with request IDs
- User-friendly messages via toast notifications
- Detailed logging with context (`exc_info=True`)

### Custom Exceptions (always raise specific types, never None/False)

```
DarshiBaseException (base class with to_dict())
├── DatabaseError → PostgreSQL operations
├── StorageError → Cloudflare R2 operations
├── AIServiceError → Gemini API failures
├── GeocodingError → Nominatim/geocoding failures
├── ValidationError → Input validation (400)
└── AuthenticationError → Auth failures (401)
```

### Duplicate Detection Strategy

1. **Exact duplicates**: Perceptual hash (dHash) comparison
2. **Proximity duplicates**: Geohash (precision 7) + category matching within ~153m
3. **Time window**: Only checks reports from last 24 hours
4. **Status filter**: Only VERIFIED and PENDING_VERIFICATION reports

### Geospatial Features

- **PostGIS**: Native geospatial queries with GEOGRAPHY type
- **Geohash encoding**: Precision 7 (~153m × 153m) for fast proximity lookups
- **Proximity queries**: PostGIS `ST_DWithin` for radius queries
- **Geocoding**: Nominatim API (limited to India with `countrycodes=in`)
- **Reverse geocoding**: Coordinates → human-readable address
- **Landmarks**: Overpass API for nearby POIs

## Critical Development Rules

### Backend

1. **Always raise specific exceptions** - Never return None/False for errors
2. **Include context in exceptions** - IDs, operation type, relevant data
3. **Use retry decorators** - `@retry_database_operation`, `@retry_ai_operation`
4. **Use circuit breakers** - External APIs (Gemini, Nominatim)
5. **Validate at router layer** - `sanitize_form_data()` before passing to services
6. **Structured logging** - Include IDs (report_id, user_id), use f-strings
7. **Never log sensitive data** - Passwords, tokens, PII
8. **Follow logging levels**:
   - DEBUG: Internal operations (queries, geohash encoding)
   - INFO: User-facing operations (report created, user login)
   - WARNING: Validation failures, recoverable errors
   - ERROR: Actual failures (database errors, API failures)
   - CRITICAL: System initialization failures

### Frontend

1. **Always use toast notifications** - Never `alert()` dialogs
2. **Always use LoadingButton** - For all form submissions
3. **Always validate forms** - Inline errors, character counters
4. **Always add ARIA labels** - Semantic HTML, keyboard navigation
5. **Never use console.log** - Remove before committing
6. **Use SvelteKit 5 Runes** - `$state`, `$derived`, `$effect`, `$props`
7. **Handle loading states** - Show LoadingSpinner during data fetching
8. **Handle error states** - User-friendly messages via `getErrorMessage()`

## Environment Configuration

### Backend (.env)

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `R2_ACCESS_KEY_ID` - Cloudflare R2 access key
- `R2_SECRET_ACCESS_KEY` - Cloudflare R2 secret key
- `R2_BUCKET_NAME` - Cloudflare R2 bucket name
- `R2_ENDPOINT` - Cloudflare R2 endpoint URL
- `GEMINI_API_KEY` - From Google AI Studio
- `SECRET_KEY` - JWT signing key (generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`)

**Optional:**
- `CORS_ORIGINS` - Comma-separated allowed origins
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
- `ENABLE_SENTRY` - Error tracking (default: false)
- `SENTRY_DSN` - Sentry DSN URL
- `ENVIRONMENT` - development, staging, production (default: development)
- `RESEND_API_KEY` - Email service API key
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - OAuth credentials
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` - OAuth credentials
- `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET` - OAuth credentials

### Frontend (.env)

**Optional:**
- `VITE_API_URL` - Backend API URL (default: http://localhost:8080)

## Key Design Patterns

### Service Functions (module-level, stateless)

```python
from app.core.error_handling import retry_database_operation, ErrorContext
from app.core.exceptions import DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

@retry_database_operation
async def create_report(db: AsyncSession, data: dict) -> int:
    """Create a new report in PostgreSQL."""
    with ErrorContext("database", "create_report"):
        try:
            stmt = insert(Report).values(**data).returning(Report.id)
            result = await db.execute(stmt)
            await db.commit()
            report_id = result.scalar()
            logger.info(f"Report created: {report_id}")
            return report_id
        except SQLAlchemyError as e:
            await db.rollback()
            raise DatabaseError(
                message="Failed to create report",
                details=str(e),
                context={"operation": "create"}
            )
```

### SvelteKit 5 Components (Runes-based reactivity)

```svelte
<script lang="ts">
  import { toast } from '$lib/stores/toast';
  import LoadingButton from '$lib/components/LoadingButton.svelte';

  let loading = $state(false);
  let formData = $state({ title: '', description: '' });
  let errors = $state<Record<string, string[]>>({});

  async function handleSubmit() {
    loading = true;
    try {
      await api.post('/api/v1/report', formData);
      toast.show('Report created successfully!', 'success');
    } catch (error) {
      toast.show(getErrorMessage(error), 'error');
    } finally {
      loading = false;
    }
  }
</script>
```

## API Endpoint Conventions

- All endpoints prefixed with `/api/v1/`
- Authentication: JWT Bearer tokens in `Authorization` header
- Rate limiting: Tiered (anonymous: 3/hr, registered: 10/hr, admin: unlimited)
- Request validation: Pydantic models
- Response format: JSON with structured errors
- Error responses: `{ "error": { "code", "message", "details", "timestamp", "request_id" } }`

## Testing Structure

**Backend (`/tests`):**
- `tests/unit/` - Unit tests for services and utilities
- `tests/integration/` - Integration tests for API endpoints
- `conftest.py` - Shared fixtures (mock database, test client)
- Run with: `pytest`, `pytest -v`, `pytest --cov=app`

**Frontend (`/frontend/src`):**
- `*.test.ts` - Vitest tests alongside source files
- Test library: `@testing-library/svelte`
- Run with: `npm run test`, `npm run test:watch`

## Git Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): add new feature
fix(scope): resolve bug
refactor(scope): restructure code without behavior change
perf(scope): improve performance
docs(scope): update documentation
test(scope): add/modify tests
chore(scope): build process, dependencies
```

**Examples:**
```
feat(reports): add perceptual hash duplicate detection
fix(auth): resolve undefined username variable in delete endpoint
refactor(logging): standardize logging levels across services
docs(api): update endpoint documentation with rate limits
```

## Data Models (PostgreSQL Tables)

**users** - User accounts
- `id` (SERIAL PRIMARY KEY)
- `username` (UNIQUE, NOT NULL)
- `email`, `phone` (optional, not unique)
- `password_hash` (bcrypt, nullable for magic link/OAuth users)
- `role`: citizen | admin
- `is_active`, `is_verified`, `email_verified`
- `oauth_provider`, `oauth_id`
- `city`, `state`, `country` (location fields for onboarding)
- `lat`, `lng`, `location_address` (coordinates and address)
- `magic_link_token`, `magic_link_expires` (passwordless auth)
- `last_login` (timestamp)
- `created_at`, `updated_at`

**reports** - Main collection for civic grievance reports
- `id` (SERIAL PRIMARY KEY)
- `report_id` (UUID UNIQUE)
- `user_id` (FOREIGN KEY → users)
- `username`, `title`, `description`
- `latitude`, `longitude`
- `geom` (GEOGRAPHY(POINT, 4326)) - PostGIS column
- `geohash` (VARCHAR(10), precision 7)
- `address`, `city`, `state`, `country`
- `status`: PENDING_VERIFICATION | VERIFIED | REJECTED | DUPLICATE | IN_PROGRESS | RESOLVED | FLAGGED
- `category`, `severity` (AI-classified)
- `image_urls` (TEXT[]), `image_data` (JSONB)
- `image_hash` (SHA256), `dhash` (perceptual hash)
- `duplicate_of` (FOREIGN KEY → reports)
- `upvote_count`, `comment_count`
- `timeline` (JSONB array of state changes)
- `created_at`, `updated_at`, `verified_at`, `resolved_at`

**comments** - Report comments
- `id` (SERIAL PRIMARY KEY)
- `report_id` (FOREIGN KEY → reports, CASCADE)
- `user_id`, `username`
- `text` (max 500 chars)
- `created_at`, `edited_at`

**upvotes** - Report upvotes
- `id` (SERIAL PRIMARY KEY)
- `report_id` (FOREIGN KEY → reports, CASCADE)
- `user_id` (FOREIGN KEY → users, CASCADE)
- `username`
- `created_at`
- UNIQUE(report_id, user_id)

## Performance Optimizations

1. **Redis caching**: Frequently accessed data (reports list, user info)
2. **WebP image format**: ~30% smaller than JPEG
3. **Async PostgreSQL**: asyncpg with connection pooling (20 max connections)
4. **Circuit breakers**: Prevent cascading failures
5. **GZip compression**: 60-80% payload reduction (Nginx)
6. **Geohash + PostGIS indexing**: Fast proximity queries
7. **Docker volumes**: Persistent data across restarts

## Security Measures

1. **Input sanitization**: `sanitize_form_data()` at router layer
2. **Rate limiting**: SlowAPI with tiered limits (Redis-backed)
3. **CORS configuration**: Explicit allowed origins (never wildcard with credentials)
4. **Security headers**: X-Content-Type-Options, X-Frame-Options, CSP (Nginx)
5. **JWT tokens**: HS256 signing with 30-day expiry
6. **Password hashing**: bcrypt with salt rounds
7. **File validation**: Max 10MB, image types only
8. **Body size limit**: 20MB max request size
9. **SSL/TLS**: Let's Encrypt certificates, TLS 1.2/1.3 only
10. **Firewall**: UFW configured (ports 22, 80, 443 only)

## Common Pitfalls to Avoid

1. ❌ **Don't return None/False for errors** → ✅ Raise specific exceptions
2. ❌ **Don't use bare except blocks** → ✅ Catch specific exceptions
3. ❌ **Don't skip retry decorators** → ✅ Use for all external operations
4. ❌ **Don't use alert() dialogs** → ✅ Use toast notifications
5. ❌ **Don't skip loading states** → ✅ Add LoadingButton and LoadingSpinner
6. ❌ **Don't leave console.log statements** → ✅ Remove before committing
7. ❌ **Don't log sensitive data** → ✅ Sanitize logs (no passwords, tokens)
8. ❌ **Don't skip input validation** → ✅ Validate at router layer
9. ❌ **Don't use generic error messages** → ✅ Provide actionable feedback
10. ❌ **Don't skip ARIA labels** → ✅ Ensure accessibility

## Deployment

**Backend** - Azure VPS (20.193.150.79)
- Docker Compose orchestration
- Nginx reverse proxy + SSL
- PostgreSQL 15 + PostGIS (Docker volume)
- Redis 7 with AOF persistence (Docker volume)
- Prometheus for metrics
- Auto-restart via systemd

**Frontend** - Cloudflare Pages
- Static site built with `npm run build`
- Deployed via GitHub integration (automatic)
- CDN distribution, HTTPS by default
- Zero configuration

**Database** - PostgreSQL 15 + PostGIS
- Self-hosted in Docker container
- Persistent volume: `postgres_data`
- PostGIS for geospatial queries
- Automated backups (see Database Backup section below)

**Storage** - Cloudflare R2
- Bucket: `darshi-reports`
- S3-compatible API (boto3)
- WebP/JPEG optimization on upload
- No egress fees

**Cache** - Redis 7
- Self-hosted in Docker container
- AOF persistence: `appendonly yes`
- Persistent volume: `redis_data`
- Used for rate limiting and report caching

**CI/CD** - GitHub Actions
- Automated testing (pytest, svelte-check)
- Zero-downtime deployments via SSH
- Health checks before completion
- Docker image cleanup

## Database Backup

### Backup Configuration

| Setting | Value |
|---------|-------|
| **Schedule** | Daily at 3:00 AM UTC (cron) |
| **Location** | `/opt/darshi/backups/` on Azure VPS |
| **Retention** | 30 days (older backups auto-deleted) |
| **Format** | Compressed SQL (`darshi_backup_YYYYMMDD_HHMMSS.sql.gz`) |
| **Method** | `pg_dump` via Docker exec |

### Backup Scripts (on server)

```bash
# Manual backup
sudo /opt/darshi/backup-database.sh

# View backup logs
tail -f /opt/darshi/logs/backup.log

# List backups
ls -la /opt/darshi/backups/
```

### Safe Docker Compose Wrapper

Use `dc` instead of `docker compose` on the server - it automatically backs up before destructive operations:

```bash
# Safe commands (use these on server)
sudo dc -f docker-compose.azure.yml ps              # No backup needed
sudo dc -f docker-compose.azure.yml up -d --build   # No backup needed
sudo dc -f docker-compose.azure.yml down            # AUTO-BACKUP first!
sudo dc -f docker-compose.azure.yml rm              # AUTO-BACKUP first!

# The wrapper lives at /usr/local/bin/dc
```

### Restore from Backup

```bash
# On the server
gunzip -c /opt/darshi/backups/darshi_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i darshi-postgres psql -U postgres -d darshi
```

### Cron Jobs (on server)

```bash
# View current cron jobs
sudo crontab -l

# Current schedule:
# 0 2 * * * - SSL certificate renewal (2:00 AM)
# 0 3 * * * - Database backup (3:00 AM)
```

## Additional Resources

- **Full Documentation**: `/docs` directory
  - [[docs/guides/architecture/overview|Architecture Guide]] - Detailed system design
  - [[docs/guides/development/setup|Development Guide]] - Developer setup and patterns
  - [[docs/guides/deployment/overview|Deployment Guide]] - Production deployment
  - [[docs/guides/api/overview|API Reference]] - Complete API documentation (65 endpoints)
  - [[docs/reference/PHILOSOPHY|Philosophy]] - **READ THIS FIRST** - Development workflow and standards
- **API Documentation**: http://localhost:8080/docs (FastAPI Swagger UI)
- **Live Site**: https://darshi.app
- **Backend API**: https://api.darshi.app

---

**Stack Migration Completed**: December 2024
**Current Version**: 2.0.0 (Azure + PostgreSQL + Docker)
**Previous Stack**: Google Cloud Platform (Cloud Run, Firestore, Cloud Storage)
