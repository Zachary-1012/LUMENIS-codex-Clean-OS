@echo off
chcp 65001 >nul
title Taikoo Cloudflare Tunnel
echo ========================================
echo  广州太古汇舆情系统 - Cloudflare Tunnel
echo ========================================
echo.
echo 使用HTTP2协议，4条高可用连接，稳定运行
echo.

"%~dp0tools\cloudflared.exe" tunnel --url http://127.0.0.1:8200 --protocol http2 --ha-connections 4 --no-autoupdate

pause

