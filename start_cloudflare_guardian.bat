@echo off
chcp 65001 >nul
title Taikoo Monitor - Cloudflare Guardian
echo ??Cloudflare????...
powershell -ExecutionPolicy Bypass -File "%~dp0cloudflared_guardian.ps1"

