@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
set TAIKOO_HOST=0.0.0.0
set TAIKOO_PORT=8200
python app.py --host 0.0.0.0
pause

