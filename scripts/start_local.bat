@echo off
cd /d "%~dp0.."
call "%~dp0..\START_ROADSOS.bat"
exit /b %errorlevel%
