@echo off
chcp 65001 >nul
echo ============================================================
echo   广州太古汇舆情监测系统 - 一键启动（含CDP浏览器）
echo ============================================================
echo.

cd /d D:\Taikoo-monitor-new

REM 配置
set EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
set CDP_PORT=9222
set PROFILE_DIR=D:\Taikoo-monitor-new\edge-cdp-newaccount

REM 检查Edge是否存在
if not exist "%EDGE_PATH%" (
    set EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe
)

echo [1/3] 检查CDP浏览器...
netstat -ano | findstr ":%CDP_PORT%" >nul
if %errorlevel%==0 (
    echo   CDP端口 %CDP_PORT% 已在使用，跳过启动
) else (
    if exist "%EDGE_PATH%" (
        echo   启动Edge浏览器（CDP模式）...
        if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"
        start "" "%EDGE_PATH%" --remote-debugging-port=%CDP_PORT% --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check https://www.xiaohongshu.com
        echo   Edge已启动，等待CDP端口就绪...
        timeout /t 5 /nobreak >nul
    ) else (
        echo   [警告] 未找到Edge浏览器，CDP采集可能不可用
    )
)

echo.
echo [2/3] 检查系统是否已运行...
netstat -ano | findstr ":8200" >nul
if %errorlevel%==0 (
    echo   系统已在8200端口运行，跳过启动
    echo.
    echo ============================================================
    echo   系统已在运行中
    echo   本地: http://127.0.0.1:8200
    echo   CDP: http://127.0.0.1:%CDP_PORT%
    echo ============================================================
    pause
    exit /b 0
)

echo.
echo [3/3] 启动舆情监测系统...
.venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200

echo.
echo 系统已退出
pause
