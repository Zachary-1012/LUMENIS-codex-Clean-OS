@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 守护闭环
echo ========================================
echo   广州太古汇舆情监测系统 - 守护闭环
echo   自动检测 + 崩溃自动重启 + 运行闭环
echo ========================================
echo.
echo 守护闭环已启动，系统崩溃后5秒内自动重启
echo 此窗口不要关闭，关闭后守护功能失效
echo.
cd /d "D:\Taikoo-monitor-new"
powershell -ExecutionPolicy Bypass -File "系统守护闭环.ps1"
pause
