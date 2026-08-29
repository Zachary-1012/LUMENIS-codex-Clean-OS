@echo off
cd /d "D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean"
"%~dp0tools\cloudflared.exe" tunnel --url http://localhost:8200 --protocol http2 > cf_output.log 2>&1

