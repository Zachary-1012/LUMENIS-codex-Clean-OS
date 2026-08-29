@echo off
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

