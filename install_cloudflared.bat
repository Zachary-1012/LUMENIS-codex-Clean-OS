@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
setlocal
where cloudflared >nul 2>nul
if not errorlevel 1 (
  echo cloudflared 已安装：
  cloudflared --version
  pause
  exit /b 0
)
where winget >nul 2>nul
if errorlevel 1 (
  echo 未找到 winget。请安装 Cloudflare cloudflared 后再运行 start_remote_5g.bat。
  pause
  exit /b 1
)
echo 正在尝试通过 winget 安装 cloudflared...
winget install --id Cloudflare.cloudflared -e --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
  echo 自动安装失败，请手动安装 cloudflared。
  pause
  exit /b 1
)
echo.
echo 安装完成。请关闭并重新打开 PowerShell/命令提示符，再执行：
echo cloudflared --version
pause
