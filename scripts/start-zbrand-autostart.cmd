@echo off
rem Z-Brand Core auto-start at Windows logon (no admin required). Launches idempotent production starter.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "D:\Taikoo-monitor-new\scripts\start_production.ps1"
