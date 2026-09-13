@echo off
rem Z-Brand Core auto-start at Windows logon (no admin required). Launches idempotent production starter.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0start_production.ps1"
