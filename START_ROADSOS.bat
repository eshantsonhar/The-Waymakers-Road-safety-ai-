@echo off
setlocal EnableDelayedExpansion
title RoadSoS - Startup

cls
echo.
echo  ============================================================
echo   ROADSOS - AI Emergency Response Platform
echo  ============================================================
echo.

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

:: ============================================================
:: CHECK PYTHON
:: ============================================================
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Python not found in PATH.
    echo  Install Python 3.11+ from https://python.org and tick "Add to PATH".
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo        %%v found

:: ============================================================
:: CHECK NODE
:: ============================================================
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Node.js not found in PATH.
    echo  Install Node.js 20+ from https://nodejs.org
    echo.
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo        Node.js %%v found

:: ============================================================
:: INSTALL BACKEND DEPS (if needed)
:: ============================================================
echo [3/5] Checking backend dependencies...
python -c "import uvicorn, fastapi, geoalchemy2, httpx" >nul 2>&1
if errorlevel 1 (
    echo        Installing backend requirements (first run, ~2 min)...
    pip install -r "%BACKEND%\requirements.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo  [ERROR] pip install failed. Try running manually:
        echo    pip install -r backend\requirements.txt
        echo.
        pause & exit /b 1
    )
    echo        Installing additional dependencies...
    pip install geoalchemy2 --quiet --disable-pip-version-check
    pip install asyncpg --quiet --disable-pip-version-check 2>nul
    echo        Backend requirements installed OK
) else (
    echo        All backend packages present - skipping install
)

:: ============================================================
:: CREATE .env IF MISSING
:: ============================================================
if not exist "%BACKEND%\.env" (
    if exist "%BACKEND%\.env.example" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo        Created backend\.env from .env.example
    )
)

:: ============================================================
:: INSTALL FRONTEND DEPS (if needed)
:: ============================================================
echo [4/5] Checking frontend dependencies...
if not exist "%FRONTEND%\node_modules\vite" (
    echo        Installing frontend dependencies (first run, ~1 min)...
    npm install --prefix "%FRONTEND%"
    if errorlevel 1 (
        echo.
        echo  [ERROR] npm install failed. Try running manually:
        echo    npm install --prefix frontend
        echo.
        pause & exit /b 1
    )
    echo        Frontend dependencies installed OK
) else (
    echo        node_modules present - skipping install
)

:: ============================================================
:: KILL ANY EXISTING PROCESSES ON THESE PORTS
:: ============================================================
echo [5/5] Clearing ports %BACKEND_PORT% and %FRONTEND_PORT%...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1
)
echo        Ports cleared

echo.
echo  ============================================================
echo   Starting servers...
echo  ============================================================
echo.

:: ============================================================
:: START BACKEND
:: ============================================================
echo  Starting backend on http://localhost:%BACKEND_PORT% ...
start "RoadSoS Backend" cmd /k "title RoadSoS Backend && cd /d "%BACKEND%" && python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --log-level info"

:: Wait a fixed time for backend to start
echo  Waiting for backend to start (15 seconds)...
timeout /t 15 /nobreak >nul

:: Quick check if backend is up
powershell -command "try { $r = Invoke-WebRequest -Uri 'http://localhost:%BACKEND_PORT%/health' -UseBasicParsing -TimeoutSec 3; if ($r.StatusCode -eq 200) { write-host '[OK] Backend is running' } else { write-host '[WARN] Backend may not be ready yet' } } catch { write-host '[WARN] Backend health check failed - continuing anyway' }"

:: ============================================================
:: START FRONTEND
:: ============================================================
echo.
echo  Starting frontend on http://localhost:%FRONTEND_PORT% ...
start "RoadSoS Frontend" cmd /k "title RoadSoS Frontend && cd /d "%FRONTEND%" && npm run dev"

:: Wait a fixed time for frontend to start
echo  Waiting for frontend to start (10 seconds)...
timeout /t 10 /nobreak >nul

:: ============================================================
:: OPEN BROWSER
:: ============================================================
cls
echo.
echo  ============================================================
echo   ROADSOS IS LIVE
echo  ============================================================
echo.
echo   Open in browser:
echo.
echo     http://localhost:5173          ^<-- Main app (all 3 UIs^)
echo     http://localhost:8000/api/docs ^<-- API documentation
echo     http://localhost:8000/health   ^<-- Backend health check
echo.
echo   The 3 UIs are tabs in the top nav bar:
echo.
echo     Command Center  = Live map + incident feed + ambulance tracking
echo     Citizen SOS     = Emergency SOS button + ambulance ETA tracker
echo     Analytics       = Accident trends + blackspot heatmap + stats
echo.
echo   DEMO MODE is ON - crashes auto-generate every 45 seconds
echo.
echo  ============================================================
echo.
echo   Opening browser...
echo.

:: Always try to open the browser
timeout /t 2 /nobreak >nul
start "" "http://localhost:5173"

:: Also open API docs as a fallback
timeout /t 1 /nobreak >nul
start "" "http://localhost:8000/api/docs"

echo.
echo   Two server windows are running in the background.
echo   Close them to stop the servers.
echo.
pause