#!/bin/bash

# PGA Application Startup Script
# Starts both frontend (Next.js) and backend (FastAPI) servers
#
# Alternative: run the full stack in Docker:
#   docker compose up --build          (production)
#   docker compose --profile dev up    (development with hot reload)

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# PIDs for cleanup
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting PGA Application${NC}"
echo "================================"

# Start backend
echo -e "${YELLOW}Starting backend on http://localhost:8001${NC}"
cd "$BACKEND_DIR"
uv run uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 2

# Start frontend
echo -e "${YELLOW}Starting frontend on http://localhost:3001${NC}"
cd "$FRONTEND_DIR"
npm run dev -- -p 3001 &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}PGA Application is running!${NC}"
echo -e "  Frontend: ${GREEN}http://localhost:3001${NC}"
echo -e "  Backend:  ${GREEN}http://localhost:8001${NC}"
echo -e "  API Docs: ${GREEN}http://localhost:8001/docs${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for both processes
wait
