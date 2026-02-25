#!/usr/bin/env bash
# Vanguard root orchestrator

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Function to run backend in background
run_backend() {
    log_info "Starting Backend..."
    cd "$ROOT/backend"
    ./run.sh &
    cat > "$ROOT/.backend.pid" << EOF
$!
EOF
}

# Function to run frontend in background
run_frontend() {
    log_info "Starting Frontend..."
    cd "$ROOT/frontend"
    ./run.sh &
    cat > "$ROOT/.frontend.pid" << EOF
$!
EOF
}

cleanup() {
    log_info "Shutting down Vanguard processes..."
    if [ -f "$ROOT/.backend.pid" ]; then
        kill $(cat "$ROOT/.backend.pid") 2>/dev/null || true
        rm "$ROOT/.backend.pid"
    fi
    if [ -f "$ROOT/.frontend.pid" ]; then
        kill $(cat "$ROOT/.frontend.pid") 2>/dev/null || true
        rm "$ROOT/.frontend.pid"
    fi
}

trap cleanup EXIT INT TERM

run_backend
run_frontend

log_info "Vanguard is running locally! Press Ctrl+C to stop."
wait
