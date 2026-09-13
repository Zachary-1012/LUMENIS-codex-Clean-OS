@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
echo ============================================================
echo   广州太古汇舆情监测系统 - CDP自动启动脚本
echo ============================================================
echo.

REM 配置
set EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
set CDP_PORT=9222
set PROFILE_DIR=%~dp0edge-cdp-profile
set APP_PATH=%~dp0
set PYTHON_PATH=%APP_PATH%\.venv\Scripts\python.exe

REM 检查Edge是否存在
if not exist "%EDGE_PATH%" (
    echo [错误] 未找到Edge浏览器: %EDGE_PATH%
    echo 请修改脚本中的 EDGE_PATH 配置
    pause
    exit /b 1
)

REM 检查Python虚拟环境
if not exist "%PYTHON_PATH%" (
    echo [错误] 未找到Python虚拟环境: %PYTHON_PATH%
    pause
    exit /b 1
)

REM 创建profile目录
if not exist "%PROFILE_DIR%" mkdir "%PROFILE_DIR%"

echo [1/3] 检查CDP端口是否已占用...
netstat -ano | findstr ":%CDP_PORT%" >nul
if %errorlevel%==0 (
    echo   CDP端口 %CDP_PORT% 已在使用，跳过启动Edge
) else (
    echo   启动Edge浏览器（CDP模式）...
    start "" "%EDGE_PATH%" --remote-debugging-port=%CDP_PORT% --remote-allow-origins=* --user-data-dir="%PROFILE_DIR%" --no-first-run --no-default-browser-check
    echo   Edge已启动，请在浏览器中登录小红书/rednote
    timeout /t 3 /nobreak >nul
)

echo.
echo [2/3] 检查系统是否已运行...
netstat -ano | findstr ":8200" >nul
if %errorlevel%==0 (
    echo   系统已在8200端口运行，跳过启动
) else (
    echo   启动舆情监测系统...
    cd /d "%APP_PATH%"
    start "广州太古汇舆情监测系统" cmd /k "%PYTHON_PATH% app.py --host 0.0.0.0 --port 8200"
    echo   系统启动中...
    timeout /t 5 /nobreak >nul
)

echo.
echo [3/3] 启动完成！
echo.
echo ============================================================
echo   访问地址:
echo   本地: http://127.0.0.1:8200
echo   局域网: http://[你的IP]:8200
echo   CDP调试: http://127.0.0.1:%CDP_PORT%
echo ============================================================
echo.
echo 提示:
echo   1. 请确保Edge浏览器已登录小红书/rednote
echo   2. 系统启动后可在网页触发采集
echo   3. 如需公网访问，请另行启动Cloudflare Tunnel
echo.
pause
