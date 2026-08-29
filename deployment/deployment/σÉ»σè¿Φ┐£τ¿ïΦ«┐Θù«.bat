@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 v5.3.2 - 启动远程访问
echo ============================================
echo   广州太古汇舆情监测系统 v5.3.2
echo   启动 Cloudflare Tunnel 远程访问
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/2] 启动本地服务（后台）...
start "Taikoo Monitor" /min python app.py --host 127.0.0.1 --port 8200

echo [等待 3 秒让服务启动...]
timeout /t 3 /nobreak >nul

echo.
echo [2/2] 启动 Cloudflare Tunnel...
echo.
echo ============================================
echo   远程访问地址将在下方显示
echo   请将该地址分享给需要访问的人
echo ============================================
echo.

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo [提示] 未找到 cloudflared，尝试使用 npx...
    npx cloudflared tunnel --url http://127.0.0.1:8200
) else (
    cloudflared tunnel --url http://127.0.0.1:8200
)

pause
