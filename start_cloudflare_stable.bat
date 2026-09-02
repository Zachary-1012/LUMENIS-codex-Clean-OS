@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
echo ============================================================
echo   广州太古汇舆情监测系统 - Cloudflare Tunnel 稳定启动
echo ============================================================
echo.

REM 配置
set CLOUDFLARED_PATH=C:\Program Files (x86)\cloudflared\cloudflared.exe
set LOCAL_URL=http://127.0.0.1:8200
set URL_FILE=D:\Taikoo-monitor-new\data\cloudflared_url.txt
set LOG_FILE=D:\Taikoo-monitor-new\data\cloudflared.log

REM 检查cloudflared是否存在
if not exist "%CLOUDFLARED_PATH%" (
    echo [错误] 未找到 cloudflared.exe: %CLOUDFLARED_PATH%
    echo 请先安装 cloudflared 或修改脚本中的路径
    pause
    exit /b 1
)

REM 检查本地系统是否运行
netstat -ano | findstr ":8200" >nul
if %errorlevel% neq 0 (
    echo [警告] 本地系统8200端口未监听，Tunnel可能无法正常工作
    echo 请先启动系统: start_system.bat
    echo.
)

REM 创建数据目录
if not exist "D:\Taikoo-monitor-new\data" mkdir "D:\Taikoo-monitor-new\data"

echo [1/3] 启动 Cloudflare Tunnel（HTTP2协议，4条高可用连接）...
echo.

REM 启动Tunnel并捕获输出
"%CLOUDFLARED_PATH%" tunnel --url %LOCAL_URL% --protocol http2 --ha-connections 4 --no-autoupdate 2>&1 | tee "%LOG_FILE%"

echo.
echo [2/3] Tunnel 已启动
echo.
echo ============================================================
echo   访问地址:
echo   本地: http://127.0.0.1:8200
echo   公网: 请查看上方日志中的 trycloudflare.com 地址
echo ============================================================
echo.
echo 提示: Quick Tunnel URL每次重启会变化
echo       如需固定URL，请配置 Named Tunnel 或接入公司域名
echo.
pause
