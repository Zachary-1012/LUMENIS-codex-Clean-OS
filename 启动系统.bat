@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 v5.8.0
echo ========================================
echo   广州太古汇舆情监测系统 v5.8.0
echo ========================================
echo.
echo [提示] 请勿关闭此窗口，关闭后系统将停止运行！
echo.
cd /d "%~dp0"
python app.py --host 0.0.0.0 --port 8200
echo.
echo [系统已停止] 按任意键退出...
pause >nul
