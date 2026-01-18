#!/bin/bash
set -e

echo "⚠️  WARNING: This script will rebuild containers but PRESERVE DATA VOLUMES"
echo "⚠️  If you need to wipe data, run: docker volume rm darshi_postgres_data darshi_redis_data"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo "🧹 Cleaning Docker build cache..."
docker builder prune -af

echo "🗑️ Stopping containers (keeping volumes)..."
# IMPORTANT: Removed -v flag to preserve data volumes!
docker compose -f docker-compose.azure.yml down
docker system prune -af

echo "🔄 Rebuilding from scratch..."
docker compose -f docker-compose.azure.yml build --no-cache

echo "🚀 Starting services..."
docker compose -f docker-compose.azure.yml up -d

echo "⏳ Waiting for services..."
sleep 15

echo "✅ Checking service status..."
docker ps --filter "name=darshi" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "✅ Deployment fixed! Data volumes preserved."
