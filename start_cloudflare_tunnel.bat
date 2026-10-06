@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
﻿@echo off
chcp 65001 >nul
title Taikoo Cloudflare Tunnel
echo ========================================
echo  广州太古汇舆情系统 - Cloudflare Tunnel
echo ========================================
echo.
echo 使用HTTP2协议，4条高可用连接，稳定运行
echo.

"%~dp0tools\cloudflared.exe" tunnel --url http://127.0.0.1:8201 --protocol http2 --ha-connections 4 --no-autoupdate

pause

