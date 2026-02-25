#!/usr/bin/env bash
# Robust build and run script for the React/Vite Frontend

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

GREEN="\03\033[0;32m"
RED="\033[0;31m"
NC="\033[0m"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

if ! command -v npm &> /dev/null; then
    log_error "npm is not installed or not in PATH."
    exit 1
fi

log_info "Installing dependencies..."
if ! npm install --silent; then
    log_error "npm install failed."
    exit 1
fi

log_info "Starting Vite development server..."
exec npm run dev
