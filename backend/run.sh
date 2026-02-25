#!/usr/bin/env bash
# Robust build and run script for the Go backend

set -euo pipefail

# Navigation
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Terminal Coloring for info/errors
GREEN="\03\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Dependency Checks
if ! command -v go &> /dev/null; then
    log_error "Go compiler is not installed or not in PATH."
    exit 1
fi

log_info "Downloading Go dependencies..."
if ! go mod download; then
    log_error "Failed to download Go modules."
    exit 1
fi

log_info "Building the Vanguard Go API server..."
if ! go build -o bin/server cmd/server/main.go; then
    log_error "Go build failed! Please check your syntax."
    exit 1
fi

log_info "Starting Vanguard backend server..."
exec ./bin/server
