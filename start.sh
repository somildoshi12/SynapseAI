#!/bin/bash
# SynapseAI — Start backend + frontend
# Usage: bash start.sh

cd "$(dirname "$0")"

echo "Starting SynapseAI..."

# Backend
cd backend
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Frontend
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "  Backend  → http://localhost:8000"
echo "  App      → http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both."

# Stop both on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
