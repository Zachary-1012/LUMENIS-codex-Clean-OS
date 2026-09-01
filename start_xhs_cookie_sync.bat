@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -c "import xhs_cookie_bridge; print('Cookie configured:', xhs_cookie_bridge.cookie_configured())"
python -c "import requests; r=requests.post('http://127.0.0.1:8200/api/xhs/cookie/sync',json={'max_scroll':6},timeout=10); print(r.status_code); print(r.text)"
pause
