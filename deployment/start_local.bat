@echo off
setlocal
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run start_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python app.py --host 127.0.0.1 --port 8200
pause
