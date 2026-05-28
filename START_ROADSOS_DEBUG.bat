@echo off
cd /d "%~dp0"
echo Starting RoadSoS in debug mode...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\launcher.ps1" -DebugMode -LogPrefix "debug_startup"
set "EXIT_CODE=%errorlevel%"
echo.
echo RoadSoS debug launcher exited with code %EXIT_CODE%.
pause
exit /b %EXIT_CODE%
