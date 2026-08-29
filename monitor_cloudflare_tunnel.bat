@echo off
chcp 65001 >nul
title Taikoo Tunnel Monitor
echo 启动Cloudflare Tunnel监控...

:loop
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | find /I "cloudflared.exe" >nul
if errorlevel 1 (
    echo [%date% %time%] cloudflared未运行，正在重启...
    start "" /MIN "%~dp0tools\cloudflared.exe" tunnel --url http://127.0.0.1:8200 --protocol http2 --ha-connections 4 --no-autoupdate
    echo [%date% %time%] 已重启
)
timeout /t 30 /nobreak >nul
goto loop

