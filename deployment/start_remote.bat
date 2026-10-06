@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run start_windows.bat first.
  pause
  exit /b 1
)
where cloudflared >nul 2>nul
if errorlevel 1 (
  echo [ERROR] cloudflared not found. Check: cloudflared --version
  pause
  exit /b 1
)
if not exist ".env" (
  echo [ERROR] .env not found. Copy .env.example to .env and set a strong password.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -c "from app import AUTH_USER,AUTH_PASSWORD; import sys; sys.exit(0 if AUTH_USER and AUTH_PASSWORD else 1)"
if errorlevel 1 (
  echo [ERROR] Basic Auth is not configured.
  pause
  exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CD%\scripts\start_production.ps1"
if errorlevel 1 (
  echo [ERROR] Canonical LUMENIS 8201 runtime failed to start.
  pause
  exit /b 1
)
echo.
echo ===== LUMENIS Cloudflare Quick Tunnel =====
echo Copy the https://*.trycloudflare.com address shown below to your authorized device.
echo Keep this window open while using remote access.
echo.
cloudflared tunnel --url http://127.0.0.1:8201
pause
