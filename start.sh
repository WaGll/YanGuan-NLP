#!/usr/bin/env bash
# YanGuan-NLP 一键启动: backend (port 3001) + frontend (port 3000)
# Usage: ./start.sh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null && echo "  backend stopped"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && echo "  frontend stopped"
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# ---- prerequisite checks ----
command -v pnpm >/dev/null 2>&1 || { echo "ERROR: pnpm not found. Install: npm i -g pnpm"; exit 1; }
[ -z "$CONDA_DEFAULT_ENV" ] && echo "WARNING: no conda env active — dependencies may be missing"

echo "=== YanGuan-NLP ==="
echo "Backend  → http://localhost:3001"
echo "Frontend → http://localhost:3000"
echo "Ctrl+C to stop"
echo ""

cd "$PROJECT_DIR/backend"
uvicorn app.main:app --reload --port 3001 &
BACKEND_PID=$!

cd "$PROJECT_DIR/frontend"
pnpm dev --port 3000 &
FRONTEND_PID=$!

echo "Backend PID: $BACKEND_PID | Frontend PID: $FRONTEND_PID"
wait
