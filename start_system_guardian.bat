@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 进程守护模式
echo ========================================
echo   广州太古汇舆情监测系统 v5.7.0
echo   进程守护模式 - 崩溃自动重启
echo ========================================
echo.

cd /d D:\Taikoo-monitor-new

:loop
echo [%date% %time%] 启动系统...
.venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200
echo.
echo [%date% %time%] 系统已退出，退出码: %errorlevel%
echo [%date% %time%] 5秒后自动重启...
timeout /t 5 /nobreak >nul
echo.
goto loop
