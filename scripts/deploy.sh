#!/bin/bash
set -e

# Vanguard Minimal Deployment Sync Script
# This script pushes changes to GitHub to trigger Vercel's automatic deployment pipeline.

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}>>> Starting Vanguard Git Sync...${NC}"

# Ensure we are in the root directory
cd "$(dirname "$0")/.."

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo -e "${BLUE}Committing local changes...${NC}"
    git add .
    git commit -m "chore: automated deployment sync [$(date +'%Y-%m-%d %H:%M:%S')]" || true
fi

echo -e "${BLUE}Pushing to GitHub (triggers Vercel/Cloud Run)...${NC}"
git push origin main

echo -e "${GREEN}>>> Sync Complete! Your changes are now being deployed. [$(date +'%H:%M:%S')]${NC}"
