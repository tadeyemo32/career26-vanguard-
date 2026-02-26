#!/bin/bash
set -e

# Vanguard Local Dev Runner
# ─────────────────────────────────────────────────────────────────────
# Starts the backend (Go) and frontend (Vite) locally.
# AUTH IS BYPASSED — any request with Bearer token "devtoken123" is
# treated as an admin user. This only works when APP_ENV=dev.
# ─────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo -e "${YELLOW}>>> VANGUARD LOCAL DEV (auth bypass active)${NC}"
echo ""

# ── 1. Load .env ─────────────────────────────────────────────────────
if [ -f "$ROOT/.env" ]; then
  export $(grep -v '^#' "$ROOT/.env" | grep -v '^$' | xargs)
fi

# ── 2. Force dev bypass settings ─────────────────────────────────────
export APP_ENV=dev
export DEV_BYPASS_TOKEN=devtoken123

# ── 3. Set VITE_DEV_TOKEN so frontend auto-logs in ───────────────────
export VITE_DEV_TOKEN=devtoken123
export VITE_API_URL=http://localhost:8765/api
export VITE_VANGUARD_API_KEY=${VANGUARD_API_KEY:-dev_secret_key}

# ── 4. Start backend ──────────────────────────────────────────────────
echo -e "${BLUE}>>> Starting backend on :8765${NC}"
cd "$ROOT/backend"
go run ./main.go &
BACKEND_PID=$!
echo -e "${GREEN}>>> Backend PID: $BACKEND_PID${NC}"

# Wait for backend to be ready
sleep 2

# ── 5. Start frontend ─────────────────────────────────────────────────
echo -e "${BLUE}>>> Starting frontend (Vite)${NC}"
cd "$ROOT/frontend"
VITE_DEV_TOKEN=devtoken123 \
VITE_API_URL=http://localhost:8765/api \
VITE_VANGUARD_API_KEY=${VANGUARD_API_KEY:-dev_secret_key} \
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}>>> App running at http://localhost:5173${NC}"
echo -e "${YELLOW}>>> Auth bypass: login screen is skipped automatically${NC}"
echo ""
echo "Press Ctrl+C to stop both servers."

# ── 6. Clean shutdown ─────────────────────────────────────────────────
trap "echo -e '\n${YELLOW}Stopping servers...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
