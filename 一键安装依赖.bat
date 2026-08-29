@echo off
chcp 65001 >nul
title 广州太古汇舆情监测系统 - 一键安装依赖

echo ============================================================
echo   广州太古汇舆情监测系统 - 一键安装依赖
echo ============================================================
echo.

cd /d "%~dp0"

:: 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在，请先创建虚拟环境
    echo 创建命令: python -m venv .venv
    pause
    exit /b 1
)

echo [1/4] 升级pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo.

echo [2/4] 安装Python依赖...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
echo.

echo [3/4] 安装Playwright浏览器...
".venv\Scripts\python.exe" -m playwright install chromium
echo.

echo [4/4] 验证安装...
".venv\Scripts\python.exe" -c "import flask; import pandas; import psutil; print('Flask:', flask.__version__); print('Pandas:', pandas.__version__); print('Psutil:', psutil.__version__); print('所有核心依赖安装成功！')"
echo.

echo ============================================================
echo   依赖安装完成！
echo ============================================================
echo.
echo 系统目录: %~dp0
echo 虚拟环境: .venv\
echo 依赖清单: requirements.txt
echo.
echo 启动系统: .venv\Scripts\python.exe app.py --host 0.0.0.0 --port 8200
echo.
pause
