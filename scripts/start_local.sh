#!/bin/bash
# RoadSoS Local Development Startup Script

echo "============================================"
echo " RoadSoS - Local Development Startup"
echo "============================================"
echo ""

# Start backend
echo "Starting Backend (FastAPI)..."
cd "$(dirname "$0")/../backend"
pip install -r requirements.txt -q
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend
sleep 3

# Start frontend
echo "Starting Frontend (Vite)..."
cd "$(dirname "$0")/../frontend"
npm install -q
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "============================================"
echo " RoadSoS is running!"
echo " Frontend: http://localhost:5173"
echo " Backend:  http://localhost:8000"
echo " API Docs: http://localhost:8000/api/docs"
echo "============================================"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
