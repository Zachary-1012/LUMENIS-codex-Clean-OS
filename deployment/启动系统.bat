@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 v5.3.2 - 启动系统
echo ============================================
echo   广州太古汇舆情监测系统 v5.3.2
echo   启动本地服务
echo ============================================
echo.

cd /d "%~dp0\.."

echo [1/3] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 环境正常

echo.
echo [2/3] 检查依赖...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt
)
echo [OK] 依赖检查完成

echo.
echo [3/3] 启动系统...
echo.
echo ============================================
echo   系统启动后，请在浏览器中访问：
echo   http://127.0.0.1:8200
echo ============================================
echo.
echo 按 Ctrl+C 可停止系统
echo.

python app.py --host 127.0.0.1 --port 8200

pause
