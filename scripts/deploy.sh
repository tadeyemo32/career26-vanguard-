#!/bin/bash
set -e

# Vanguard Unified Deployment Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}>>> Starting Vanguard Deployment Pipeline...${NC}"

# 1. Backend Automation
echo -e "${BLUE}>>> [1/4] Testing Backend...${NC}"
cd backend
go test ./...

echo -e "${BLUE}>>> [2/4] Deploying Backend to Google Cloud Run...${NC}"
gcloud run deploy vanguard26 --source . --region europe-west1 --quiet

# Extract service URL
SERVICE_URL=$(gcloud run services describe vanguard26 --region europe-west1 --format 'value(status.url)')
echo -e "${GREEN}>>> Backend deployed successfully to: ${SERVICE_URL}${NC}"

echo -e "${BLUE}>>> [3/4] Verifying Backend Endpoints...${NC}"
# Smoke test health check
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/health")
if [ "$HEALTH_STATUS" -eq 200 ]; then
    echo -e "${GREEN}✓ Health Check Passed (200 OK)${NC}"
else
    echo -e "${RED}✗ Health Check Failed (Status $HEALTH_STATUS)${NC}"
    exit 1
fi

# 2. Frontend Automation (Optional - Requires Vercel CLI)
echo -e "${BLUE}>>> [4/4] Deploying Frontend...${NC}"
cd ../frontend

if command -v vercel &> /dev/null; then
    echo -e "${BLUE}Deploying to Vercel...${NC}"
    vercel --prod --yes
    echo -e "${GREEN}>>> Frontend deployed successfully.${NC}"
else
    echo -e "${RED}Vercel CLI not found. Please deploy manually or install via 'npm i -g vercel'.${NC}"
fi

echo -e "${GREEN}>>> Deployment Complete!${NC}"
