@echo off
chcp 65001 >nul
title 微博扫码登录 - 广州太古汇舆情监测系统

echo ============================================================
echo   微博扫码登录 - 广州太古汇舆情监测系统
echo ============================================================
echo.
echo 功能说明：
echo   1. 自动打开浏览器，显示微博登录二维码
echo   2. 使用微博APP扫码登录
echo   3. 登录成功后自动保存登录态
echo   4. 后续采集微博数据无需重复登录
echo.
echo 注意事项：
echo   - 请确保已安装Playwright浏览器
echo   - 登录过程中请勿关闭浏览器窗口
echo   - 登录超时时间为5分钟
echo.
echo ============================================================
echo.

cd /d "%~dp0"

:: 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在，请先运行 一键安装依赖.bat
    pause
    exit /b 1
)

echo 启动微博登录管理器...
echo.

".venv\Scripts\python.exe" -c "
from weibo_login_manager import WeiboLoginManager
import json

manager = WeiboLoginManager()

# 先检测当前登录状态
status = manager.check_login_status()
print('当前登录状态:')
print(json.dumps(status, ensure_ascii=False, indent=2))
print()

if status['logged_in']:
    choice = input('检测到已有登录态，是否重新登录？(y/n): ')
    if choice.lower() != 'y':
        print('保持现有登录态，退出')
        exit(0)
    manager.clear_login_data()

# 开始扫码登录
print()
print('=' * 50)
print('即将打开浏览器，请使用微博APP扫码登录')
print('登录成功后浏览器会自动关闭')
print('=' * 50)
print()

success = manager.login_with_qrcode(headless=False, timeout=300)

if success:
    print()
    print('=' * 50)
    print('  微博登录成功！')
    print('  登录态已保存，可用于全网话题搜集')
    print('=' * 50)
else:
    print()
    print('=' * 50)
    print('  微博登录失败或超时')
    print('  请重新运行此脚本')
    print('=' * 50)
"

echo.
pause
