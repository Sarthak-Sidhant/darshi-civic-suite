---
title: Architecture Overview
tags: [architecture, system-design, azure, postgresql, docker, infrastructure, tech-stack, deployment, cloudflare]
related:
  - "[[backend-architecture]]"
  - "[[data-models]]"
  - "[[../deployment/overview]]"
  - "[[../api/overview]]"
---

# Darshi Architecture Overview

Complete system architecture for the Darshi civic grievance platform.

## System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│         CLOUDFLARE (DNS + CDN + Proxy)                       │
│      darshi.app │ api.darshi.app                             │
└─────────┬──────────────────┬─────────────────────────────────┘
          │                  │
          ▼                  ▼
┌──────────────────┐  ┌──────────────────────────────────────┐
│ CLOUDFLARE PAGES │  │   CLOUDFLARE PROXY                   │
│   (Frontend)     │  │   api.darshi.app                     │
│  - SvelteKit SSG │  └──────────┬───────────────────────────┘
│  - Global CDN    │             │
│  - Auto SSL      │             ▼
└──────────────────┘  ┌──────────────────────────────────────┐
                      │  AZURE VPS (20.193.150.79)           │
                      │  Ubuntu 22.04, 16GB, 4 vCPU          │
                      │  ┌────────────────────────────────┐  │
                      │  │   NGINX (Port 443)             │  │
                      │  │   - SSL/TLS (Let's Encrypt)    │  │
                      │  │   - Reverse Proxy              │  │
                      │  └──────────┬─────────────────────┘  │
                      │             │                        │
                      │  ┌──────────▼─────────────────────┐  │
                      │  │ FastAPI Backend (Port 8080)    │  │
                      │  │ Docker Container               │  │
                      │  └────────┬────┬──────┬───────────┘  │
                      │           │    │      │              │
                      │  ┌────────▼┐  ┌▼──┐  ┌▼───────────┐ │
                      │  │Postgres│  │Redis│ │Prometheus  │ │
                      │  │PostGIS │  │AOF  │ │(Metrics)   │ │
                      │  │Volume  │  │Vol. │ │Volume      │ │
                      │  └────────┘  └────┘  └────────────┘ │
                      └──────────────────────────────────────┘
                                    │
                      ┌─────────────┴───────────────┐
                      ▼                             ▼
         ┌──────────────────────┐      ┌──────────────────┐
         │   CLOUDFLARE R2      │      │  EXTERNAL APIs   │
         │   (Image Storage)    │      │  - Gemini AI     │
         │   - S3-Compatible    │      │  - Nominatim     │
         │   - Global CDN       │      │  - Overpass      │
         └──────────────────────┘      └──────────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python 3.11)
- **Database**: PostgreSQL 15 + PostGIS
- **Cache**: Redis 7 (AOF persistence)
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

## Architecture Layers

### 1. Presentation Layer
- [[frontend-architecture|Frontend Architecture]] - SvelteKit 5, Runes API, TypeScript
- Static site generation (SSG)
- Service Worker for push notifications
- Responsive design (mobile-first)

### 2. API Gateway Layer
- Nginx reverse proxy with SSL termination
- FastAPI with async support
- JWT authentication
- Rate limiting (Redis-backed)
- Request validation (Pydantic)

### 3. Business Logic Layer
- [[backend-architecture|Backend Architecture]] - Service functions (module-level)
- Circuit breakers for external APIs
- Retry logic with exponential backoff
- Caching strategies (Redis)
- Background task processing

### 4. Data Layer
- [[data-models|Data Models]] - PostgreSQL with PostGIS
- Redis for caching and rate limiting
- Cloudflare R2 for image storage
- Docker volumes for persistence

### 5. External Integration Layer
- Google Gemini 2.5 Flash (AI)
- Nominatim (geocoding)
- Overpass API (landmarks)
- OAuth providers (Google, GitHub, Facebook)

## Key Features

### Security
- JWT token authentication (HS256)
- OAuth 2.0 integration
- Rate limiting (tiered by user type)
- Input validation and sanitization
- CORS protection
- SSL/TLS (Let's Encrypt)

### Performance
- Async/await throughout
- Connection pooling (20 max)
- Circuit breakers
- Response caching (CDN headers)
- GZip compression
- WebP image optimization

### Scalability
- Docker containerization
- Horizontal scaling (add more VPS instances)
- PostgreSQL replication (future)
- Redis cluster (future)
- CDN distribution (Cloudflare)

### Monitoring
- [[monitoring|Monitoring & Observability]]
- Prometheus metrics
- Structured logging
- Health checks
- Error tracking (Sentry)

## Design Decisions

### Why PostgreSQL over Firestore?
1. **Relational data**: Clear relationships between reports, users, comments
2. **ACID transactions**: Atomic updates (upvote count, comment count)
3. **PostGIS**: Powerful spatial queries
4. **Cost predictability**: Fixed VPS cost vs usage-based
5. **Better tooling**: pgAdmin, pg_dump, familiar SQL

### Why Cloudflare R2 over GCS?
1. **No egress fees**: GCS charges for bandwidth, R2 doesn't
2. **S3 compatibility**: Standard boto3 API
3. **Global CDN**: Edge locations worldwide
4. **Cost**: ~70% cheaper than GCS

### Why Docker Compose over Kubernetes?
1. **Simplicity**: Single VPS, no orchestration complexity
2. **Resource efficiency**: K8s overhead not justified
3. **Easy management**: Simpler to debug and maintain
4. **Sufficient scale**: Current traffic fits on 16GB VPS

### Why SvelteKit 5 over React/Next.js?
1. **Performance**: Compiles to vanilla JS (no virtual DOM)
2. **Bundle size**: ~30-40% smaller than React
3. **Developer experience**: Less boilerplate, intuitive reactivity
4. **Runes API**: Modern reactivity primitives
5. **SSR/SSG**: Built-in support

## Related Documentation

- [[backend-architecture|Backend Architecture]] - Services, routers, middleware
- [[frontend-architecture|Frontend Architecture]] - Components, stores, routing
- [[data-models|Data Models]] - PostgreSQL schema, indexes
- [[security|Security Architecture]] - Auth, rate limiting, encryption
- [[deployment|Deployment Guide]] - Production setup

---

**Last Updated**: December 28, 2025
**Stack**: Azure + PostgreSQL + Docker + SvelteKit + Cloudflare
