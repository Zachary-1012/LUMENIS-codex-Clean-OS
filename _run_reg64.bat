@echo off
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" -m pytest tests -m "not online" --ignore=tests/test_browser_e2e.py -k "not alembic" --no-header -q -p no:cacheprovider > "%TEMP%\zbc_reg64.txt" 2>&1
echo EXIT=%ERRORLEVEL% >> "%TEMP%\zbc_reg64.txt"
