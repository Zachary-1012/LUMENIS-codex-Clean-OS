@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
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
