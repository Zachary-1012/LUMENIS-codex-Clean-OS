@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo [LUMENIS] .venv not found & exit /b 1)
.venv\Scripts\python.exe -X utf8 -c "from lumenis.system.ai_gateway.core import owned_inference_status; import json; print(json.dumps(owned_inference_status(), ensure_ascii=False, indent=2))"
exit /b %ERRORLEVEL%
