@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
setlocal
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
  if errorlevel 1 (echo Python 3 not found. Please install Python 3.11+ and try again.&pause&exit /b 1)
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not exist node_modules (
  npm install
)
if not exist "%LOCALAPPDATA%\ms-playwright" (
  npx playwright install chromium
)
python app.py --host 0.0.0.0
pause

