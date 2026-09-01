@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
﻿@echo off
chcp 65001 >nul
title Taikoo Monitor - Cloudflare Guardian
echo ??Cloudflare????...
powershell -ExecutionPolicy Bypass -File "%~dp0cloudflared_guardian.ps1"

