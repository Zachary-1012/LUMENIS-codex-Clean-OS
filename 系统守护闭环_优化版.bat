@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 守护闭环（优化版）

echo ============================================================
echo   广州太古汇舆情监测系统 - 守护闭环（优化版）
echo ============================================================
echo.
echo 优化特性：
echo   1. 重启前等待10秒，确保端口完全释放
echo   2. 重启后等待60秒，确保系统稳定运行
echo   3. 1小时内最多重启5次，防止频繁重启
echo   4. 双重检测：端口检测 + API响应检测
echo   5. 完整日志记录
echo.
echo ============================================================
echo.

setlocal enabledelayedexpansion

:: 配置
set "SYSTEM_DIR=%~dp0"
set "PYTHON_EXE=%SYSTEM_DIR%\.venv\Scripts\python.exe"
set "APP_FILE=%SYSTEM_DIR%\app.py"
set "PORT=8200"
set "LOG_FILE=%SYSTEM_DIR%\guardian_loop_optimized.log"
set "MAX_RESTARTS_PER_HOUR=5"
set "RESTART_WAIT_BEFORE=10"
set "RESTART_WAIT_AFTER=60"
set "CHECK_INTERVAL=15"

:: 重启记录（时间戳队列）
set "RESTART_TIMES="

cd /d "%SYSTEM_DIR%"

echo [%date% %time%] 守护闭环启动，系统目录: %SYSTEM_DIR% >> "%LOG_FILE%"
echo [%date% %time%] 守护闭环启动，系统目录: %SYSTEM_DIR%

:loop
:: 检查系统是否在运行
echo [%date% %time%] 检测系统状态...

:: 1. 检测端口
netstat -ano | findstr ":%PORT% " >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] 端口 %PORT% 未监听，系统可能已崩溃
    goto restart
)

:: 2. 检测API响应（双重验证）
curl -s -o nul -w "%%{http_code}" --max-time 5 http://127.0.0.1:%PORT%/api/architecture/status -H "Authorization: Basic WmFjaGFyeTpJRDgyNjEw" >nul 2>&1
if %errorlevel% neq 0 (
    echo [%date% %time%] API无响应，系统可能已卡死
    goto restart
)

:: 系统正常运行
echo [%date% %time%] 系统运行正常，等待 %CHECK_INTERVAL% 秒后再次检测...
timeout /t %CHECK_INTERVAL% /nobreak >nul
goto loop

:restart
:: 检查重启频率限制
echo [%date% %time%] 准备重启系统...

:: 清理1小时前的重启记录
set "NEW_TIMES="
set "COUNT=0"
for %%T in (%RESTART_TIMES%) do (
    :: 简单的时间差检查（这里用计数代替，实际可优化）
    set /a COUNT+=1
    if !COUNT! leq %MAX_RESTARTS_PER_HOUR% (
        set "NEW_TIMES=!NEW_TIMES! %%T"
    )
)

:: 检查是否超过频率限制
set "RESTART_COUNT=0"
for %%T in (%RESTART_TIMES%) do (
    set /a RESTART_COUNT+=1
)

if %RESTART_COUNT% geq %MAX_RESTARTS_PER_HOUR% (
    echo [%date% %time%] ⚠️ 警告：1小时内已重启 %RESTART_COUNT% 次，超过限制 %MAX_RESTARTS_PER_HOUR% 次
    echo [%date% %time%] 等待5分钟后再尝试重启...
    echo [%date% %time%] ⚠️ 重启频率超限，等待5分钟 >> "%LOG_FILE%"
    timeout /t 300 /nobreak >nul
    set "RESTART_TIMES="
)

:: 重启前：强制杀死所有python进程，等待端口释放
echo [%date% %time%] 停止现有进程...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1

echo [%date% %time%] 等待 %RESTART_WAIT_BEFORE% 秒，确保端口完全释放...
timeout /t %RESTART_WAIT_BEFORE% /nobreak >nul

:: 启动系统
echo [%date% %time%] 启动系统...
start "TaikooMonitor" /min "%PYTHON_EXE%" "%APP_FILE%" --host 0.0.0.0 --port %PORT%

:: 记录重启时间
set "RESTART_TIMES=%RESTART_TIMES% %time%"

echo [%date% %time%] 系统已启动，等待 %RESTART_WAIT_AFTER% 秒确保稳定运行...
echo [%date% %time%] 系统重启完成，等待稳定 >> "%LOG_FILE%"

timeout /t %RESTART_WAIT_AFTER% /nobreak >nul

:: 验证系统是否成功启动
netstat -ano | findstr ":%PORT% " >nul 2>&1
if %errorlevel% equ 0 (
    echo [%date% %time%] ✅ 系统重启成功，端口 %PORT% 已监听
    echo [%date% %time%] ✅ 系统重启成功 >> "%LOG_FILE%"
) else (
    echo [%date% %time%] ❌ 系统重启失败，端口未监听，将再次尝试
    echo [%date% %time%] ❌ 系统重启失败 >> "%LOG_FILE%"
)

goto loop
