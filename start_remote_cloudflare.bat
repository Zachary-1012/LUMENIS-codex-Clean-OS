@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
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
