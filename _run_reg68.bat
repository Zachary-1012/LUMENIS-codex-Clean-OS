@echo off
cd /d D:\Taikoo-monitor-new
"D:\Taikoo-monitor-new\.venv\Scripts\python.exe" -m pytest tests -m "not online" --ignore=tests/test_browser_e2e.py -k "not alembic" --no-header -q -p no:capture -p no:cacheprovider > "%TEMP%\zbc_reg68.txt" 2>&1
echo EXITCODE=%ERRORLEVEL% >> "%TEMP%\zbc_reg68.txt"
