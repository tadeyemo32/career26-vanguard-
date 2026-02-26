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
gcloud run deploy vanguard26 --source . --region europe-west1 --quiet \
  --set-env-vars "VANGUARD_API_KEY=dev_secret_key,RESEND_API_KEY=re_jM1Tphc9_EjyALFswGLuw26EDEp21tUsW,JWT_SECRET=super-secret-vanguard-key"

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

# 2. Frontend Automation (via GitHub Integration)
echo -e "${BLUE}>>> [4/4] Syncing Changes to main for Vercel Deployment...${NC}"
cd ..

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${BLUE}Committing local changes...${NC}"
    git add .
    git commit -m "chore: automated deployment sync [$(date +'%Y-%m-%d %H:%M:%S')]" || true
fi

echo -e "${BLUE}Pushing to GitHub (triggers Vercel deploy)...${NC}"
git push origin main
echo -e "${GREEN}>>> Changes pushed. Vercel will build automatically.${NC}"

echo -e "${GREEN}>>> Deployment Complete!${NC}"
