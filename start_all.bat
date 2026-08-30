@echo off
chcp 65001 >nul
title 广州太古汇·舆情监测系统 v5.4 - 一键启动
echo ============================================
echo   广州太古汇·舆情监测系统 v5.4
echo   一键启动（含 rednote CDP 采集）
echo ============================================
echo.

cd /d "%~dp0"

:: 检查 Python 虚拟环境
if not exist .venv (
  echo [1/4] 创建 Python 虚拟环境...
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] Python 3 未找到，请安装 Python 3.11+
    pause
    exit /b 1
  )
)

call .venv\Scripts\activate.bat

:: 安装依赖
echo [2/4] 检查依赖...
python -m pip install -r requirements.txt -q 2>nul

:: 检查 Node 依赖
if not exist node_modules (
  echo [3/4] 安装 Node 依赖...
  npm install -q 2>nul
)

:: 启动 Edge 调试模式（CDP 9222端口），用于 rednote 采集
echo [4/4] 启动 Edge 调试模式（CDP 端口 9222）...
tasklist /fi "imagename eq msedge.exe" 2>nul | findstr /i "msedge.exe" >nul
if errorlevel 1 (
  start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%LOCALAPPDATA%\Microsoft\Edge\User Data" "https://www.rednote.com"
  echo   Edge 已启动，请确保已登录 rednote 账号
) else (
  echo   Edge 已在运行，请确保已使用 --remote-debugging-port=9222 启动
  echo   如果未使用调试模式启动，请先关闭所有 Edge 窗口后重新运行此脚本
)

timeout /t 3 /nobreak >nul

:: 设置环境变量
set XHS_CDP_URL=http://127.0.0.1:9222
set TAIKOO_HOST=0.0.0.0
set TAIKOO_PORT=8200
set AUTO_INTERVAL_MINUTES=90
set DAILY_REPORT_HOUR=9

echo.
echo ============================================
echo   系统启动中...
echo   访问地址: http://127.0.0.1:8200
echo   局域网访问: http://[本机IP]:8200
echo   CDP 调试: http://127.0.0.1:9222
echo   自动采集: 每 90 分钟
echo ============================================
echo.

:: 自动打开浏览器
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8200"

:: 启动 Flask 应用
python app.py --host 0.0.0.0 --port 8200

pause
