@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 进程守护模式
echo ========================================
echo   广州太古汇舆情监测系统 v5.7.0
echo   进程守护模式 - 崩溃自动重启
echo ========================================
echo.

cd /d "%~dp0"

:loop
echo [%date% %time%] 启动系统...
.venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200
echo.
echo [%date% %time%] 系统已退出，退出码: %errorlevel%
echo [%date% %time%] 5秒后自动重启...
timeout /t 5 /nobreak >nul
echo.
goto loop
