# 🚀 Darshi - Quick Start Guide

> **Get Darshi up and running locally in 15 minutes!**

**Live Site**: https://darshi.app | **API**: https://api.darshi.app

---

## 📋 Prerequisites

Before starting, ensure you have:
- **Python 3.11+** installed
- **Node.js 20+** installed
- **PostgreSQL 15+** with PostGIS extension
- **Redis 7+** (or use Docker for both)
- **Git** installed
- **Docker & Docker Compose** (recommended for quick setup)

---

## ⚡ Fast Setup with Docker (Recommended)

```bash
# 1. Clone and navigate
git clone https://github.com/Sarthak-Sidhant/darshi.git
cd darshi

# 2. Start PostgreSQL and Redis
docker compose up -d postgres redis

# 3. Backend setup
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 4. Configure environment (edit this file!)
cp .env.example .env
nano .env  # Add your Gemini API key, Cloudflare R2 credentials

# 5. Run backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# 6. Frontend setup (new terminal)
cd frontend
npm install
cp .env.example .env  # Optional: customize API URL
npm run dev
```

✅ **Done!** Open http://localhost:5173

---

## 📝 Detailed Setup

### Step 1: Database Setup (3 minutes)

#### Option A: Docker (Recommended)

```bash
# Start PostgreSQL with PostGIS and Redis
docker compose up -d postgres redis

# Verify containers are running
docker ps

# Check logs
docker logs darshi-postgres
docker logs darshi-redis
```

**Default credentials** (configured in docker-compose.yml):
- PostgreSQL: `postgres:postgres@localhost:5432/darshi`
- Redis: `redis://localhost:6379`

#### Option B: Manual Installation

**PostgreSQL with PostGIS**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-15-postgis-3

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres psql
CREATE DATABASE darshi;
\c darshi
CREATE EXTENSION postgis;
CREATE USER darshi_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE darshi TO darshi_user;
\q
```

**Redis**:
```bash
# Ubuntu/Debian
sudo apt install redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Test connection
redis-cli ping  # Should return PONG
```

---

### Step 2: Backend Setup (5 minutes)

#### 2.1 Create Virtual Environment

```bash
cd /path/to/darshi
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate    # Windows
```

#### 2.2 Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- SQLAlchemy + asyncpg (PostgreSQL ORM)
- Redis client
- Cloudflare R2 SDK
- Gemini AI SDK
- Authentication libraries (JWT, bcrypt)
- And more...

#### 2.3 Configure Backend Environment

```bash
cp .env.example .env
nano .env  # or use your favorite editor
```

**Essential variables**:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/darshi

# Redis
REDIS_URL=redis://localhost:6379/0

# Cloudflare R2 (S3-compatible storage)
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=your-r2-access-key
R2_SECRET_ACCESS_KEY=your-r2-secret-key
R2_BUCKET_NAME=darshi-reports
R2_PUBLIC_URL=https://your-bucket.r2.cloudflarestorage.com

# Gemini AI
GEMINI_API_KEY=your-gemini-api-key-from-google-ai-studio

# JWT Secret (generate with: python3 -c "import secrets; print(secrets.token_urlsafe(64))")
SECRET_KEY=your-generated-secret-key

# OAuth (optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
FACEBOOK_CLIENT_ID=your-facebook-client-id
FACEBOOK_CLIENT_SECRET=your-facebook-client-secret

# App Config
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

#### 2.4 Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click **Create API Key**
3. Copy the key and add to `.env`

#### 2.5 Set Up Cloudflare R2 (Image Storage)

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. Navigate to **R2 Object Storage**
3. Create a bucket: `darshi-reports`
4. Create API token:
   - Go to **Manage R2 API Tokens**
   - Click **Create API Token**
   - Set permissions: **Object Read & Write**
   - Copy **Access Key ID** and **Secret Access Key**
5. Add credentials to `.env`

#### 2.6 Initialize Database

```bash
# Run migrations (creates all tables)
alembic upgrade head

# Or use the init script
python scripts/init_db.py
```

This creates tables:
- `users` - User accounts
- `reports` - Civic grievance reports
- `comments` - Report comments
- `upvotes` - User upvotes on reports
- `admin_logs` - Audit trail for admin actions

---

### Step 3: Frontend Setup (3 minutes)

#### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

This installs:
- SvelteKit 5 with Runes API
- TypeScript
- Leaflet (maps)
- And more...

#### 3.2 Configure Frontend Environment (Optional)

```bash
cp .env.example .env
nano .env
```

**Optional variables** (defaults work for local development):

```bash
# Backend API URL (default: http://localhost:8080)
VITE_API_URL=http://localhost:8080
```

---

### Step 4: Run the Application (1 minute)

Open **two terminal windows**:

#### Terminal 1: Backend

```bash
cd /path/to/darshi
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

✅ Backend running at: **http://localhost:8080**
✅ API Docs at: **http://localhost:8080/docs**

#### Terminal 2: Frontend

```bash
cd /path/to/darshi/frontend
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

---

## 🧪 Test Your Setup

### 1. Check Health Endpoint

```bash
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Darshi Backend",
  "database": "connected",
  "redis": "connected"
}
```

### 2. Open API Documentation

Go to http://localhost:8080/docs

You should see:
- Interactive Swagger UI
- All 62+ API endpoints
- Try out authentication, reports, admin endpoints

### 3. Open Frontend

Go to http://localhost:5173

You should see:
- Landing page with navigation
- Sign In button (unified auth page)
- Recent reports list
- Map preview

### 4. Create Test Account

1. Click **Sign In**
2. Switch to **Create Account** tab
3. Choose any registration method:
   - Email + password
   - Google/GitHub/Facebook OAuth
4. Fill in username and email
5. You're in! 🎉

### 5. Submit Test Report

1. Click **Submit Report** in navigation
2. Fill in details:
   - Title: "Test pothole"
   - Description: "Testing the platform"
   - Category: Pothole
   - Upload an image
3. Click **Current Location** to auto-fill GPS
4. Submit report
5. Wait for AI verification (~5-10 seconds)
6. Report appears on homepage!

---

## 🔐 OAuth Setup (Optional)

To enable Google, GitHub, and Facebook login:

### Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project or select existing
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs:
   - `http://localhost:8080/api/v1/oauth/google/callback`
   - `https://api.darshi.app/api/v1/oauth/google/callback`
7. Copy **Client ID** and **Client Secret** to `.env`

### GitHub OAuth

1. Go to [GitHub Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Application name: Darshi
4. Homepage URL: `http://localhost:5173`
5. Authorization callback URL: `http://localhost:8080/api/v1/oauth/github/callback`
6. Copy **Client ID** and **Client Secret** to `.env`

### Facebook OAuth

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Create an app → **Consumer** type
3. Add **Facebook Login** product
4. Settings → **Valid OAuth Redirect URIs**:
   - `http://localhost:8080/api/v1/oauth/facebook/callback`
5. Copy **App ID** and **App Secret** to `.env`

---

## 🎯 Next Steps

### Essential Configuration

1. **Create Admin User**:
   ```bash
   python scripts/create_admin.py
   # Follow prompts to create super_admin or moderator
   ```

2. **Test All Features**:
   - Submit a report with images
   - View on map
   - Add comments
   - Upvote reports
   - Test admin panel at `/admin`

3. **Run Tests**:
   ```bash
   # Backend tests
   pytest -v
   pytest --cov=app

   # Frontend tests
   cd frontend
   npm run test
   npm run check  # Type checking
   ```

### Production Readiness

Before deploying to production:

1. **Security**:
   - Change `SECRET_KEY` to strong random value
   - Update `CORS_ORIGINS` to your domain only
   - Enable rate limiting (already configured)
   - Use strong PostgreSQL password
   - Review [DEPLOYMENT.md](deployment.md)

2. **OAuth**:
   - Update OAuth callback URLs to production domain
   - Add production redirect URIs to providers

3. **Database**:
   - Set up automated backups (see [DEPLOYMENT.md](deployment.md))
   - Configure connection pooling
   - Add monitoring

4. **CI/CD**:
   - See [CI_CD_SETUP.md](../CI_CD_SETUP.md) for GitHub Actions workflow
   - Configure secrets in GitHub repository
   - Test auto-deployment

---

## 🐛 Common Issues

### Backend won't start

**"Connection refused to PostgreSQL"**:
```bash
# Check PostgreSQL is running
docker ps | grep postgres
# Or if installed manually:
sudo systemctl status postgresql

# Test connection
psql postgresql://postgres:postgres@localhost:5432/darshi
```

**"Connection refused to Redis"**:
```bash
# Check Redis is running
docker ps | grep redis
# Or if installed manually:
sudo systemctl status redis-server

# Test connection
redis-cli ping  # Should return PONG
```

**"Port 8080 already in use"**:
```bash
# Find and kill process using port 8080
lsof -ti:8080 | xargs kill -9

# Or use different port
uvicorn app.main:app --reload --port 8000
```

### Frontend won't start

**"Module not found"**:
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**"VITE_API_URL not defined"**:
- Default is `http://localhost:8080`, no `.env` needed
- Only create `frontend/.env` if you need custom API URL

### Database connection fails

**"Role 'postgres' does not exist"**:
```bash
# If using Docker, check connection string matches docker-compose.yml
# Default: postgresql://postgres:postgres@localhost:5432/darshi
```

**"Database 'darshi' does not exist"**:
```bash
# Create database
docker exec -it darshi-postgres psql -U postgres -c "CREATE DATABASE darshi;"

# Or if installed manually:
sudo -u postgres createdb darshi
```

**"Extension 'postgis' not available"**:
```bash
# Install PostGIS extension
docker exec -it darshi-postgres psql -U postgres -d darshi -c "CREATE EXTENSION postgis;"
```

### Image uploads fail

**"Cloudflare R2 access denied"**:
- Verify R2 credentials in `.env`
- Check bucket name matches
- Ensure API token has read/write permissions

**"File too large"**:
- Max file size: 10MB per image
- Max 5 images per report
- Backend will return 413 error

---

## 📚 Documentation Index

- **Getting Started**:
  - [Quick Start](quick_start.md) - This guide
  - [Development Guide](development.md) - Developer workflow
  - [CI/CD Setup](../CI_CD_SETUP.md) - Auto-deployment

- **Deployment**:
  - [Deployment Guide](deployment.md) - Production hosting on Azure VPS
  - [Architecture Guide](architecture.md) - System design

- **API**:
  - [API Reference](api.md) - Complete API documentation (62 endpoints)
  - Interactive docs: http://localhost:8080/docs

- **Reference**:
  - [Philosophy](reference/PHILOSOPHY.md) - Development principles
  - [CLAUDE.md](../CLAUDE.md) - AI assistant context

---

## 🆘 Getting Help

If you're stuck:

1. **Check logs**:
   ```bash
   # Backend logs (in terminal running uvicorn)
   # Watch for errors in red

   # Docker logs
   docker logs darshi-postgres --tail 50
   docker logs darshi-redis --tail 50

   # Frontend (in browser console)
   F12 → Console tab
   ```

2. **Verify environment**:
   ```bash
   # Backend
   source venv/bin/activate
   python -c "import sys; print(sys.version)"  # Should be 3.11+
   python -c "import fastapi; print(fastapi.__version__)"

   # Frontend
   node --version  # Should be 20+
   npm --version
   ```

3. **Check running services**:
   ```bash
   # Health check
   curl http://localhost:8080/health

   # Database connection
   psql postgresql://postgres:postgres@localhost:5432/darshi -c "SELECT version();"

   # Redis connection
   redis-cli ping
   ```

4. **Review documentation**:
   - Check [DEVELOPMENT.md](development.md) for patterns
   - See [PHILOSOPHY.md](reference/PHILOSOPHY.md) for conventions
   - Review [API.md](api.md) for endpoint details

---

## ✅ Success Checklist

You're ready to develop when:

- [ ] PostgreSQL and Redis are running
- [ ] Backend health check returns OK
- [ ] Frontend loads at localhost:5173
- [ ] Can register a new user
- [ ] Can login with test credentials
- [ ] Can submit a test report with image
- [ ] Image uploads to Cloudflare R2
- [ ] Report appears on homepage
- [ ] Can view report details
- [ ] Can add comments and upvote
- [ ] Admin panel accessible (if admin user created)

---

**Congratulations! Darshi is running locally. 🎉**

**Next**: Try submitting your first civic report, explore the map, or set up the admin panel!
