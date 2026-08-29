@echo off
setlocal
cd /d "%~dp0"
if "%TAIKOO_AUTH_USER%"=="" (
  echo WARNING: Set TAIKOO_AUTH_USER and TAIKOO_AUTH_PASSWORD before exposing this service remotely.
  echo Example in this terminal:
  echo   set TAIKOO_AUTH_USER=admin
  echo   set TAIKOO_AUTH_PASSWORD=change-this
  pause
  exit /b 1
)
start "Taikoo Monitor" cmd /c "call .venv\Scripts\activate.bat ^&^& python app.py"
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo cloudflared not found. Install cloudflared first, then run this file again.
  pause
  exit /b 1
)
cloudflared tunnel --url http://127.0.0.1:8200
