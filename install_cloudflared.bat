@echo off
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
