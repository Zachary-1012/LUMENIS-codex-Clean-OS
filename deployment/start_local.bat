@echo off
setlocal
cd /d "%~dp0.."
echo [LUMENIS] Redirecting compatibility launcher to the canonical 8201 production launcher.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\scripts\start_production.ps1"
exit /b %ERRORLEVEL%
