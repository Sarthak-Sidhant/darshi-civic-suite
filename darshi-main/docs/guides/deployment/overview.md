---
title: Deployment Overview
tags: [deployment, azure, docker, production, vps, nginx, ssl, ci-cd, github-actions, devops]
related:
  - "[[../architecture/overview]]"
  - "[[../development/setup]]"
  - "[[../../quick_start]]"
---

# Deployment Overview

Production deployment on Azure VPS with Docker Compose.

## Infrastructure

- **Server**: Azure VPS (20.193.150.79)
- **OS**: Ubuntu 22.04 LTS
- **Specs**: 4 vCPU, 16GB RAM
- **Services**: PostgreSQL, Redis, FastAPI, Prometheus
- **Orchestration**: Docker Compose
- **Proxy**: Nginx + Let's Encrypt
- **CI/CD**: GitHub Actions

## Architecture

```
Azure VPS
├── Nginx (Port 443) → SSL/TLS
├── Backend (Port 8080) → FastAPI Docker
├── PostgreSQL → Docker volume
├── Redis → Docker volume
└── Prometheus → Docker volume
```

## Deployment Flow

1. Push to `main` branch
2. GitHub Actions runs tests
3. SSH into Azure VPS
4. Pull latest code
5. Rebuild Docker containers
6. Health checks
7. ✅ Live

## Quick Commands

```bash
# SSH into VPS
ssh darshi@20.193.150.79

# Check services
docker ps

# View logs
docker logs darshi-backend -f

# Restart services
cd /opt/darshi
docker compose -f docker-compose.azure.yml restart

# Manual deployment
git pull origin main
docker compose -f docker-compose.azure.yml up -d --build
```

## Monitoring

- **Health**: https://api.darshi.app/health
- **Metrics**: http://20.193.150.79:9090 (Prometheus)
- **Logs**: `docker logs <container>`

---

**Last Updated**: December 28, 2025
