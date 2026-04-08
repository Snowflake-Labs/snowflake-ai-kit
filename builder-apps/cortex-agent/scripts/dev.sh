#!/usr/bin/env bash
# Cortex Agent App — Development Server
# Starts the FastAPI backend and Vite dev server.

set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env.local
if [ -f .env.local ]; then
  set -a
  source .env.local
  set +a
fi

echo "Starting Cortex Agent App..."
echo ""

# Start backend
echo "Starting backend on :8001..."
uvicorn server.main:app --reload --port 8001 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend on :5174..."
cd client
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend:  http://localhost:8001"
echo "Frontend: http://localhost:5174"
echo ""
echo "Press Ctrl+C to stop."

# Cleanup on exit
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM
wait
