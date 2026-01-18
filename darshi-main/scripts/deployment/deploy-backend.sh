#!/bin/bash
# Deploy Darshi Backend to Cloud Run with Security Fixes

set -e  # Exit on error

echo "🚀 Deploying Darshi Backend to Cloud Run..."

# Configuration
PROJECT_ID="darshi-cb3a7"
REGION="asia-southeast1"
SERVICE_NAME="darshi-backend"

# IMPORTANT: Set these secrets in Google Secret Manager first!
# Then reference them here

echo "📦 Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

echo "🚢 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,ENVIRONMENT=production,LOG_LEVEL=INFO,CORS_ORIGINS=https://darshi.app,https://www.darshi.app,https://api.darshi.app,FRONTEND_URL=https://darshi.app,RATE_LIMIT_ENABLED=true,EMAIL_ENABLED=false,SMS_ENABLED=true,SMS_BACKEND=firebase,ENABLE_SENTRY=false" \
  --set-secrets="SECRET_KEY=darshi-secret-key:latest,GEMINI_API_KEY=darshi-gemini-key:latest" \
  --service-account=darshi-backend@$PROJECT_ID.iam.gserviceaccount.com \
  --max-instances=10 \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300

echo "✅ Deployment complete!"
echo ""
echo "Backend URL:"
gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'
