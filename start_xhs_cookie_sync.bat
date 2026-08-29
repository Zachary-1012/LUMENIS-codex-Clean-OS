@echo off
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
