@echo off
setlocal EnableDelayedExpansion
title RoadSoS - Startup

cls
echo.
echo  ============================================================
echo   ROADSOS - AI Emergency Response Platform
echo   Starting backend + frontend...
echo  ============================================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"

:: ---- Check Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11+ and add to PATH.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

:: ---- Check Node ----
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Install Node.js 20+ from https://nodejs.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo [OK] Node.js %%v

:: ---- Check uvicorn ----
python -m uvicorn --version >nul 2>&1
if errorlevel 1 (
    echo [INFO] uvicorn not found. Installing backend requirements...
    pip install -r "%BACKEND%\requirements.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] pip install failed. See errors above.
        pause & exit /b 1
    )
    echo [OK] Backend requirements installed
) else (
    for /f "tokens=*" %%v in ('python -m uvicorn --version 2^>^&1') do echo [OK] %%v
)

:: ---- Create .env if missing ----
if not exist "%BACKEND%\.env" (
    if exist "%BACKEND%\.env.example" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo [OK] Created backend\.env from .env.example
    )
)

:: ---- Install frontend deps if missing ----
if not exist "%FRONTEND%\node_modules\vite" (
    echo [INFO] Installing frontend dependencies (first run, ~1 min)...
    npm install --prefix "%FRONTEND%" --silent
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause & exit /b 1
    )
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend node_modules present
)

echo.
echo [INFO] Launching backend on http://localhost:8000 ...
start "RoadSoS Backend [:8000]" cmd /k "title RoadSoS Backend [:8000] && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info"

echo [INFO] Waiting 6 seconds for backend to start...
timeout /t 6 /nobreak >nul

echo [INFO] Launching frontend on http://localhost:5173 ...
start "RoadSoS Frontend [:5173]" cmd /k "title RoadSoS Frontend [:5173] && npm run dev --prefix %FRONTEND%"

echo [INFO] Waiting 5 seconds for frontend to start...
timeout /t 5 /nobreak >nul

cls
echo.
echo  ============================================================
echo   ROADSOS IS LIVE
echo  ============================================================
echo.
echo   Open in browser:
echo.
echo   http://localhost:5173          (all 3 UIs)
echo   http://localhost:8000/api/docs (API docs)
echo   http://localhost:8000/health   (health check)
echo.
echo   The 3 UIs are tabs in the top nav bar:
echo     Command  = Emergency operations center + live map
echo     Citizen  = SOS button + ambulance tracker
echo     Analytics= Accident trends + blackspot analytics
echo.
echo   DEMO MODE is ON - crashes auto-generate every 45s
echo  ============================================================
echo.
echo  Opening browser...
timeout /t 2 /nobreak >nul
start "" "http://localhost:5173"
echo.
echo  Close the two backend/frontend windows to stop the servers.
echo.
pause
