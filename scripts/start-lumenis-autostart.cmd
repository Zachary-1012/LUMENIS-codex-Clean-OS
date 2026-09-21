@echo off
setlocal
rem Canonical LUMENIS Windows autostart entry. Resolve the production launcher from this repository.
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start_production.ps1"
set "exitCode=%ERRORLEVEL%"
endlocal & exit /b %exitCode%
