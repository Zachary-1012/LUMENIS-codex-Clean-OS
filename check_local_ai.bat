@echo off
setlocal
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python -c "import intelligence; print(intelligence.ai_status())"
echo.
echo 说明：若显示 Ollama / LM Studio / llama_cpp，即已自动接入本机模型；若显示 local_rule，系统仍可正常运行。
pause
