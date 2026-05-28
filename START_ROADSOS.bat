@echo off
setlocal EnableDelayedExpansion
title RoadSoS - AI Emergency Response Platform
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"
set "RETRY_COUNT=0"
set "MAX_RETRIES=12"

:: ANSI color codes via escape sequences
for /f "delims=." %%a in ('ver') do set "WINVER=%%a"
set "ESC="
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"

cls
echo %ESC%[96m
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║   %ESC%[1mROADSOS%ESC%[0m%ESC%[96m  -  AI Emergency Response Intelligence Platform     ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo %ESC%[0m

:: ============================================================
:: STEP 1 — Detect System Dependencies
:: ============================================================
echo.
echo %ESC%[93m[1/7]%ESC%[0m Detecting system dependencies...

:: Python check
python --version >nul 2>&1
if errorlevel 1 (
    echo %ESC%[91m  ✗ Python not found!%ESC%[0m
    echo    Install Python 3.11+ from https://python.org
    echo    Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo %ESC%[92m  ✓ %%v%ESC%[0m

:: Node.js check
node --version >nul 2>&1
if errorlevel 1 (
    echo %ESC%[91m  ✗ Node.js not found!%ESC%[0m
    echo    Install Node.js 20+ from https://nodejs.org
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo %ESC%[92m  ✓ Node.js %%v%ESC%[0m

:: npm check
npm --version >nul 2>&1
if errorlevel 1 (
    echo %ESC%[91m  ✗ npm not found!%ESC%[0m
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('npm --version 2^>^&1') do echo %ESC%[92m  ✓ npm %%v%ESC%[0m

:: ============================================================
:: STEP 2 — Set up Python Virtual Environment
:: ============================================================
echo.
echo %ESC%[93m[2/7]%ESC%[0m Setting up Python environment...

if not exist "%BACKEND%\.venv" (
    echo    Creating virtual environment...
    python -m venv "%BACKEND%\.venv"
    if errorlevel 1 (
        echo %ESC%[91m  ✗ Failed to create virtual environment%ESC%[0m
        pause
        exit /b 1
    )
    echo %ESC%[92m  ✓ Virtual environment created%ESC%[0m
) else (
    echo %ESC%[92m  ✓ Virtual environment exists%ESC%[0m
)

:: Activate venv and upgrade pip
call "%BACKEND%\.venv\Scripts\activate.bat"
if errorlevel 1 (
    echo %ESC%[91m  ✗ Failed to activate virtual environment%ESC%[0m
    pause
    exit /b 1
)

python -m pip install --upgrade pip --quiet --disable-pip-version-check >nul 2>&1

:: ============================================================
:: STEP 3 — Install Backend Dependencies
:: ============================================================
echo.
echo %ESC%[93m[3/7]%ESC%[0m Installing backend dependencies...

:: Check if requirements are already installed
python -c "import fastapi, uvicorn, httpx, websockets" >nul 2>&1
if errorlevel 1 (
    echo    Installing Python packages (first time may take ~2 minutes)...
    pip install -r "%BACKEND%\requirements.txt" --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo %ESC%[91m  ✗ pip install failed. Retrying with detailed output...%ESC%[0m
        pip install -r "%BACKEND%\requirements.txt"
        if errorlevel 1 (
            echo.
            echo %ESC%[91m  ✗ Installation failed. Try manually:%ESC%[0m
            echo    pip install -r backend\requirements.txt
            pause
            exit /b 1
        )
    )
    echo %ESC%[92m  ✓ Backend requirements installed%ESC%[0m
) else (
    echo %ESC%[92m  ✓ All backend packages present%ESC%[0m
)

:: Verify critical packages
python -c "import fastapi" >nul 2>&1 && echo %ESC%[92m  ✓ fastapi%ESC%[0m || echo %ESC%[91m  ✗ fastapi missing%ESC%[0m
python -c "import uvicorn" >nul 2>&1 && echo %ESC%[92m  ✓ uvicorn%ESC%[0m || echo %ESC%[91m  ✗ uvicorn missing%ESC%[0m
python -c "import httpx" >nul 2>&1 && echo %ESC%[92m  ✓ httpx%ESC%[0m || echo %ESC%[91m  ✗ httpx missing%ESC%[0m
python -c "import websockets" >nul 2>&1 && echo %ESC%[92m  ✓ websockets%ESC%[0m || echo %ESC%[91m  ✗ websockets missing%ESC%[0m

:: ============================================================
:: Create .env if missing
:: ============================================================
if not exist "%BACKEND%\.env" (
    if exist "%BACKEND%\.env.example" (
        copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul
        echo %ESC%[92m  ✓ Created backend\.env from example%ESC%[0m
    ) else (
        echo    Creating default .env configuration...
        (
            echo APP_VERSION=1.0.0
            echo DEMO_MODE=true
            echo DEMO_CRASH_INTERVAL_SECONDS=45
            echo BANGALORE_LAT=12.9716
            echo BANGALORE_LON=77.5946
            echo ALLOWED_ORIGINS=["*"]
            echo DATABASE_URL=sqlite:///./roadsos.db
            echo WS_HEARTBEAT_INTERVAL=30
            echo CRASH_CONFIRM_THRESHOLD=0.85
            echo CRASH_SUSPECT_THRESHOLD=0.60
            echo BLACKSPOT_RISK_THRESHOLD=65
            echo DEMO_HOSPITAL_UPDATE_INTERVAL_SECONDS=15
        ) > "%BACKEND%\.env"
        echo %ESC%[92m  ✓ Created default backend\.env%ESC%[0m
    )
)

:: ============================================================
:: STEP 4 — Install Frontend Dependencies
:: ============================================================
echo.
echo %ESC%[93m[4/7]%ESC%[0m Setting up frontend dependencies...

if not exist "%FRONTEND%\node_modules" (
    echo    Installing frontend packages (first time may take ~1 minute)...
    cd /d "%FRONTEND%"
    npm install --no-fund --no-audit
    if errorlevel 1 (
        echo %ESC%[91m  ✗ npm install failed. Retrying...%ESC%[0m
        npm install
        if errorlevel 1 (
            echo.
            echo %ESC%[91m  ✗ npm install failed. Try:%ESC%[0m
            echo    cd frontend ^&^& npm install
            cd /d "%ROOT%"
            pause
            exit /b 1
        )
    )
    cd /d "%ROOT%"
    echo %ESC%[92m  ✓ Frontend dependencies installed%ESC%[0m
) else (
    echo %ESC%[92m  ✓ node_modules exists%ESC%[0m
)

:: Verify vite is installed
if exist "%FRONTEND%\node_modules\.bin\vite.cmd" (
    echo %ESC%[92m  ✓ Vite build tool ready%ESC%[0m
) else (
    echo %ESC%[91m  ⚠ Vite not found, reinstalling...%ESC%[0m
    cd /d "%FRONTEND%"
    npm install --no-fund --no-audit
    cd /d "%ROOT%"
)

:: ============================================================
:: STEP 5 — Kill Existing Processes on Target Ports
:: ============================================================
echo.
echo %ESC%[93m[5/7]%ESC%[0m Clearing ports %BACKEND_PORT%^ and %FRONTEND_PORT%...

for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1 && echo    Killed process %%p on port %BACKEND_PORT%
)
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /PID %%p /F >nul 2>&1 && echo    Killed process %%p on port %FRONTEND_PORT%
)
echo %ESC%[92m  ✓ Ports cleared%ESC%[0m

:: ============================================================
:: STEP 6 — Start Backend Server
:: ============================================================
echo.
echo %ESC%[93m[6/7]%ESC%[0m Starting services...

:: Start backend
echo    Starting FastAPI backend on http://localhost:%BACKEND_PORT% ...
start "RoadSoS Backend" cmd /k "title RoadSoS Backend && cd /d "%BACKEND%" && call "%BACKEND%\.venv\Scripts\activate.bat" && python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --log-level info --reload"

:: Wait for backend with health check retry loop
echo    Waiting for backend to respond...
:wait_backend
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo %ESC%[91m  ⚠ Backend might not have started properly. Continuing...%ESC%[0m
    goto after_backend_wait
)
timeout /t 2 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:%BACKEND_PORT%/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { write-host '%ESC%[92m  ✓ Backend is running (attempt %RETRY_COUNT%)%ESC%[0m'; exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto wait_backend
:after_backend_wait

:: Start frontend
echo    Starting React frontend on http://localhost:%FRONTEND_PORT% ...
start "RoadSoS Frontend" cmd /k "title RoadSoS Frontend && cd /d "%FRONTEND%" && npm run dev"

:: Wait for frontend
set "RETRY_COUNT=0"
:wait_frontend
set /a RETRY_COUNT+=1
if %RETRY_COUNT% gtr %MAX_RETRIES% (
    echo %ESC%[91m  ⚠ Frontend might not have started. Continuing...%ESC%[0m
    goto after_frontend_wait
)
timeout /t 2 /nobreak >nul
powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://localhost:%FRONTEND_PORT%/' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { write-host '%ESC%[92m  ✓ Frontend is running (attempt %RETRY_COUNT%)%ESC%[0m'; exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto wait_frontend
:after_frontend_wait

:: ============================================================
:: STEP 7 — Launch Browser
:: ============================================================
cls
echo.
echo %ESC%[96m╔══════════════════════════════════════════════════════════════════╗
echo ║                    %ESC%[1;92mROADSOS IS LIVE%ESC%[0;96m                                     ║
echo ╚══════════════════════════════════════════════════════════════════╝%ESC%[0m
echo.
echo %ESC%[97m  Main Dashboard:%ESC%[0m
echo    %ESC%[94mhttp://localhost:%FRONTEND_PORT%/%ESC%[0m
echo.
echo %ESC%[97m  API Documentation:%ESC%[0m
echo    %ESC%[94mhttp://localhost:%BACKEND_PORT%/api/docs%ESC%[0m
echo.
echo %ESC%[97m  Backend Health:%ESC%[0m
echo    %ESC%[94mhttp://localhost:%BACKEND_PORT%/health%ESC%[0m
echo.
echo %ESC%[93m  ┌─────────────────────────────────────────────────────────────┐%ESC%[0m
echo %ESC%[93m  │  The 3 UIs are tabs in the top nav bar:                    │%ESC%[0m
echo %ESC%[93m  │                                                             │%ESC%[0m
echo %ESC%[93m  │  Command Center  = Live map + incident feed + ambulances   │%ESC%[0m
echo %ESC%[93m  │  Citizen SOS     = Emergency SOS + sensor telemetry        │%ESC%[0m
echo %ESC%[93m  │  Analytics       = Incident trends + blackspot heatmap     │%ESC%[0m
echo %ESC%[93m  └─────────────────────────────────────────────────────────────┘%ESC%[0m
echo.
echo %ESC%[92m  DEMO MODE IS ACTIVE%ESC%[0m - Crashes auto-generate every 45 seconds
echo %ESC%[90m  Close the two server windows to stop RoadSoS%ESC%[0m
echo.

:: Open browser
timeout /t 2 /nobreak >nul
start "" "http://localhost:%FRONTEND_PORT%"
timeout /t 1 /nobreak >nul
start "" "http://localhost:%BACKEND_PORT%/api/docs"

echo.
echo %ESC%[92m  ✓ System launched successfully!%ESC%[0m
echo.
pause