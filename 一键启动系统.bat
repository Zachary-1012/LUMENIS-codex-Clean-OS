@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 一键启动
echo ========================================
echo   广州太古汇舆情监测系统 v5.9.0
echo   一键启动（系统+CDP+Cloudflare+守护）
echo ========================================
echo.

cd /d "D:\Taikoo-monitor-new"

echo [1/4] 启动系统服务...
start "TaikooMonitor-System" /min cmd /c ".venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200"
timeout /t 3 /nobreak >nul

echo [2/4] 启动CDP浏览器（用于采集）...
start "TaikooMonitor-CDP" /min cmd /c "start_cdp_auto.bat"
timeout /t 2 /nobreak >nul

echo [3/4] 启动Cloudflare Tunnel（公网访问）...
start "TaikooMonitor-Cloudflare" /min cmd /c "start_cloudflare_stable.bat"
timeout /t 2 /nobreak >nul

echo [4/4] 启动进程守护（崩溃自动重启）...
start "TaikooMonitor-Guardian" /min cmd /c "start_system_guardian.bat"

echo.
echo ========================================
echo   系统启动完成！
echo   本地访问: http://127.0.0.1:8200
echo   局域网: http://192.168.0.213:8200
echo   账号: Zachary / ID082610
echo ========================================
echo.
echo 提示：本窗口可以关闭，系统在后台运行
echo 查看运行状态：任务管理器中查找 python.exe
pause
