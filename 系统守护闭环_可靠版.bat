@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 守护闭环（可靠版）
echo ========================================
echo   广州太古汇舆情监测系统 - 守护闭环
echo   自动检测 + 崩溃自动重启
echo ========================================
echo.

cd /d "D:\Taikoo-monitor-new"

setlocal enabledelayedexpansion
set RESTART_COUNT=0
set LAST_RESTART=0

:loop
    :: 检测8200端口是否在监听
    netstat -ano | findstr ":8200" | findstr "LISTENING" >nul
    if %errorlevel%==0 (
        :: 端口在监听，检测API是否响应
        powershell -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8200/api/architecture/status' -Headers @{Authorization='Basic '+[Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes('Zachary:ID082610'))} -UseBasicParsing -TimeoutSec 3; exit 0 } catch { exit 1 }" >nul 2>&1
        if !errorlevel!==0 (
            :: 系统正常运行
            echo [%date% %time%] ✅ 系统正常运行
        ) else (
            :: 端口在监听但API不响应，重启
            echo [%date% %time%] ⚠️ API无响应，准备重启...
            call :restart
        )
    ) else (
        :: 端口不在监听，系统崩溃了，重启
        echo [%date% %time%] ❌ 系统未运行，准备启动...
        call :restart
    )

    :: 等待10秒后再次检测
    timeout /t 10 /nobreak >nul
goto loop

:restart
    set /a RESTART_COUNT+=1
    echo [%date% %time%] 🔄 正在重启系统（第!RESTART_COUNT!次）...

    :: 杀死所有python进程
    taskkill /f /im python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul

    :: 确保端口释放
    netstat -ano | findstr ":8200" | findstr "LISTENING" >nul
    if !errorlevel!==0 (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8200" ^| findstr "LISTENING"') do (
            taskkill /f /pid %%a >nul 2>&1
        )
        timeout /t 2 /nobreak >nul
    )

    :: 启动系统
    start "TaikooMonitor" /min ".venv\Scripts\python.exe" app.py --host 0.0.0.0 --port 8200
    echo [%date% %time%] ✅ 系统已启动，等待30秒稳定...
    timeout /t 30 /nobreak >nul

    :: 检测是否启动成功
    netstat -ano | findstr ":8200" | findstr "LISTENING" >nul
    if !errorlevel!==0 (
        echo [%date% %time%] ✅ 系统启动成功！
    ) else (
        echo [%date% %time%] ⚠️ 系统可能启动失败，将在下一轮检测中重试
    )
goto :eof
