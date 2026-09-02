@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
echo ============================================================
echo 广州太古汇舆情监测系统 v5.8.0 - 本地部署启动
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] 停止旧进程...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul

echo [2/3] 清理临时文件...
if exist debug_startup.log del /Q debug_startup.log
if exist debug_error.log del /Q debug_error.log

echo [3/3] 启动系统（全局Python，本地部署）...
echo.
echo 系统将在 http://127.0.0.1:8200 启动
echo 局域网访问: http://192.168.0.213:8200
echo 按 Ctrl+C 停止系统
echo.

python -u app.py --host 0.0.0.0 --port 8200

echo.
echo 系统已停止，按任意键退出...
pause >nul
