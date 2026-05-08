@echo off
echo ============================================
echo  RoadSoS - Local Development Startup
echo ============================================
echo.

echo Starting Backend (FastAPI)...
start "RoadSoS Backend" cmd /k "cd /d %~dp0..\backend && pip install -r requirements.txt && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

echo Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak > nul

echo Starting Frontend (Vite)...
start "RoadSoS Frontend" cmd /k "cd /d %~dp0..\frontend && npm install && npm run dev"

echo.
echo ============================================
echo  RoadSoS is starting up!
echo  Frontend: http://localhost:5173
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/api/docs
echo ============================================
echo.
echo Note: Database features require PostgreSQL with PostGIS.
echo The platform runs in memory-only mode without a database.
echo.
pause
