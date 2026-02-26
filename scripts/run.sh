#!/bin/bash
set -e

# Vanguard Local Dev Runner
# ─────────────────────────────────────────────────────────────────────
# Starts backend + frontend locally with auth bypass active.
# ─────────────────────────────────────────────────────────────────────

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo -e "${YELLOW}>>> VANGUARD LOCAL DEV (auth bypass active)${NC}"

# ── 1. Source .env (exports ALL vars including API keys) ──────────────
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
  echo -e "${GREEN}>>> Loaded .env (API keys active)${NC}"
fi

# ── 2. Force dev bypass ───────────────────────────────────────────────
export APP_ENV=dev
export DEV_BYPASS_TOKEN=devtoken123

# ── 3. Start backend ──────────────────────────────────────────────────
echo -e "${BLUE}>>> Starting backend on :8765${NC}"
cd "$ROOT/backend/cmd/server"
go run . &>/tmp/vanguard_backend.log &
BACKEND_PID=$!

# Wait for backend to be ready (up to 15s)
echo -n "Waiting for backend"
for i in $(seq 1 15); do
  sleep 1
  if curl -sf http://localhost:8765/api/health >/dev/null 2>&1; then
    echo -e " ${GREEN}ready!${NC}"
    break
  fi
  echo -n "."
done

# ── 4. Start frontend ─────────────────────────────────────────────────
echo -e "${BLUE}>>> Starting frontend (Vite)${NC}"
cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}>>> App at http://localhost:5173${NC}"
echo -e "${YELLOW}>>> Auth bypass ON — login screen skipped (admin as dev@local)${NC}"
echo ""
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
