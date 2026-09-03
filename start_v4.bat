@echo off
REM ============================================================
REM Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
REM  此脚本已标注为 LEGACY。官方统一生产入口已收敛为：
REM    PowerShell 5.1+  :  powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
REM  说明：不删除本脚本（保持向后兼容），但任何后续生产运维请使用上述入口。
REM ============================================================
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ========================================
echo   CTH-POMS V4.0 - 启动脚本(双击即用)
echo ========================================
echo.

REM --- 选择装全依赖的解释器：优先 Python3.13，回退 PATH 中的 python ---
set "PY="
py -3.13 --version >nul 2>&1 && set "PY=py -3.13"
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [错误] 未找到 Python，请先安装 Python 3.10-3.13
  pause
  exit /b 1
)
echo [解释器]
%PY% --version
echo.

REM --- 依赖自检：缺啥补啥（网站运行硬依赖）---
echo [1/3] 检查依赖...
%PY% -c "import flask,requests,waitress,bs4,pdfplumber,docx,openpyxl,pandas" >nul 2>&1
if errorlevel 1 (
  echo 正在补齐依赖，请稍候...
  %PY% -m pip install --disable-pip-version-check flask requests waitress beautifulsoup4 pdfplumber python-docx openpyxl pandas
)
REM playwright 仅 CDP 采集需要，缺失不阻断网站启动
%PY% -c "import playwright" >nul 2>&1
if errorlevel 1 echo [提示] 未装 playwright，不影响网站启动；如需 CDP 采集再执行: %PY% -m pip install playwright

REM --- 初始化 V4 模块(建表，幂等) ---
echo [2/3] 初始化 V4 模块...
%PY% -c "from v4_upgrade import init_v4_modules; init_v4_modules(); print('V4 模块初始化完成')"
if errorlevel 1 (
  echo [错误] V4 模块初始化失败
  pause
  exit /b 1
)

REM --- 启动主系统 ---
echo [3/3] 启动 CTH-POMS ...
echo.
echo   主系统 : http://127.0.0.1:8200
echo   V4设置 : http://127.0.0.1:8200/v4/settings/
echo   健康检 : http://127.0.0.1:8200/v4/health
echo   主账号 : Zachary / Zachary01
echo   按 Ctrl+C 停止
echo.
%PY% app.py
pause
