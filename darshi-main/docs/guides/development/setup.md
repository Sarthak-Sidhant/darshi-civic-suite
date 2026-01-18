---
title: Development Environment Setup
tags: [development, setup, docker, python, nodejs, environment, local, getting-started, quickstart]
related:
  - "[[../../CLAUDE]]"
  - "[[../architecture/overview]]"
  - "[[../../quick_start]]"
---

# Development Environment Setup

Quick guide to set up Darshi development environment.

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker + Docker Compose**
- **Git**

## Quick Start

```bash
# Clone repository
git clone https://github.com/Sarthak-Sidhant/darshi.git
cd darshi

# Start databases
docker compose up -d postgres redis

# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.azure.example .env  # Edit with your values
alembic upgrade head

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

## Access Points

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## Environment Variables

Required in `.env`:
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- `GEMINI_API_KEY` - From Google AI Studio
- `SECRET_KEY` - Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`

See [[../../../CLAUDE|CLAUDE.md]] for complete guide.

---

**Last Updated**: December 28, 2025
