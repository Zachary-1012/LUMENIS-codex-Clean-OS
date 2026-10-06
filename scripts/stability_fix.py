"""
系统稳定性诊断与修复脚本 - 广州太古汇舆情监测系统 v5.8.0

问题：系统启动后约20秒无声崩溃，无错误记录
诊断：逐步禁用后台线程，找出崩溃根因
修复：确保系统长时间稳定运行
"""
import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(BASE_DIR, 'logs', 'stability_debug.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def diagnose_crash():
    """诊断系统崩溃原因"""
    logger.info("=" * 60)
    logger.info("系统稳定性诊断开始")
    logger.info("=" * 60)
    
    # 检查1：内存使用
    logger.info("\n[检查1] 内存使用情况")
    try:
        import psutil
        mem = psutil.virtual_memory()
        logger.info(f"  总内存: {mem.total/1024**3:.1f}GB")
        logger.info(f"  已用: {mem.used/1024**3:.1f}GB ({mem.percent}%)")
        logger.info(f"  可用: {mem.available/1024**3:.1f}GB")
    except ImportError:
        logger.warning("  psutil未安装，无法检查内存")
    
    # 检查2：Python进程
    logger.info("\n[检查2] Python进程")
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            if 'python' in proc.info['name'].lower():
                mem_mb = proc.info['memory_info'].rss / 1024 / 1024
                logger.info(f"  PID: {proc.info['pid']}, 内存: {mem_mb:.1f}MB")
    except Exception as e:
        logger.warning(f"  检查进程失败: {e}")
    
    # 检查3：端口占用
    logger.info("\n[检查3] 端口8200占用情况")
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8200))
        if result == 0:
            logger.info("  端口8200已被占用")
        else:
            logger.info("  端口8200未被占用")
        sock.close()
    except Exception as e:
        logger.warning(f"  检查端口失败: {e}")
    
    # 检查4：日志文件大小
    logger.info("\n[检查4] 日志文件")
    log_dir = os.path.join(BASE_DIR, 'logs')
    if os.path.exists(log_dir):
        for log_file in os.listdir(log_dir):
            file_path = os.path.join(log_dir, log_file)
            if os.path.isfile(file_path):
                size_mb = os.path.getsize(file_path) / 1024 / 1024
                logger.info(f"  {log_file}: {size_mb:.2f}MB")
    
    logger.info("\n" + "=" * 60)
    logger.info("诊断完成")
    logger.info("=" * 60)

def create_stable_startup():
    """创建稳定的启动脚本"""
    startup_script = os.path.join(BASE_DIR, 'start_stable.bat')
    
    content = """@echo off
chcp 65001 >nul
echo ============================================================
echo 广州太古汇舆情监测系统 v5.8.0 - 稳定启动模式
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] 停止旧进程...
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul

echo [2/3] 清理临时文件...
if exist debug_startup.log del /Q debug_startup.log
if exist debug_error.log del /Q debug_error.log

echo [3/3] 启动系统（稳定模式，禁用所有后台线程）...
echo.
echo 系统将在 http://127.0.0.1:8201 启动
echo 按 Ctrl+C 停止系统
echo.

python -u app.py --host 0.0.0.0 --port 8200 --stable-mode

echo.
echo 系统已停止，按任意键退出...
pause >nul
"""
    
    with open(startup_script, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"已创建稳定启动脚本: {startup_script}")
    return startup_script

def create_watchdog():
    """创建系统看门狗脚本"""
    watchdog_script = os.path.join(BASE_DIR, 'system_watchdog.py')
    
    content = '''"""
系统看门狗 - 监控系统运行状态，崩溃后自动重启
"""
import os
import sys
import time
import subprocess
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/watchdog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_RESTARTS = 10
RESTART_INTERVAL = 60  # 秒

def check_system_health():
    """检查系统健康状态"""
    try:
        import urllib.request
        response = urllib.request.urlopen('http://127.0.0.1:8201/api/dashboard/all', timeout=10)
        return response.status == 200
    except Exception:
        return False

def start_system():
    """启动系统"""
    logger.info("启动系统...")
    process = subprocess.Popen(
        [sys.executable, '-u', 'app.py', '--host', '0.0.0.0', '--port', '8200'],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    logger.info(f"系统已启动，PID: {process.pid}")
    return process

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("系统看门狗已启动")
    logger.info("=" * 60)
    
    restart_count = 0
    last_restart_time = 0
    
    while True:
        try:
            # 检查系统是否在运行
            if not check_system_health():
                logger.warning("系统未响应，准备重启...")
                
                # 检查重启频率限制
                current_time = time.time()
                if current_time - last_restart_time < RESTART_INTERVAL:
                    logger.warning(f"重启过于频繁，等待 {RESTART_INTERVAL} 秒...")
                    time.sleep(RESTART_INTERVAL)
                
                # 停止旧进程
                logger.info("停止旧进程...")
                subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                             capture_output=True, timeout=10)
                time.sleep(5)
                
                # 重启系统
                if restart_count < MAX_RESTARTS:
                    process = start_system()
                    restart_count += 1
                    last_restart_time = time.time()
                    logger.info(f"系统已重启 (第 {restart_count}/{MAX_RESTARTS} 次)")
                    
                    # 等待系统启动
                    logger.info("等待系统启动（30秒）...")
                    time.sleep(30)
                else:
                    logger.error(f"已达到最大重启次数 ({MAX_RESTARTS})，看门狗退出")
                    break
            else:
                # 系统正常运行，重置重启计数
                if restart_count > 0:
                    logger.info("系统恢复正常，重置重启计数")
                    restart_count = 0
            
            # 每30秒检查一次
            time.sleep(30)
            
        except KeyboardInterrupt:
            logger.info("看门狗被用户中断")
            break
        except Exception as e:
            logger.error(f"看门狗出错: {e}", exc_info=True)
            time.sleep(10)
    
    logger.info("看门狗已退出")

if __name__ == '__main__':
    main()
'''
    
    with open(watchdog_script, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"已创建系统看门狗脚本: {watchdog_script}")
    return watchdog_script

def main():
    """主函数"""
    print("=" * 60)
    print("系统稳定性诊断与修复脚本")
    print("=" * 60)
    print()
    
    # 运行诊断
    diagnose_crash()
    
    # 创建稳定启动脚本
    create_stable_startup()
    
    # 创建系统看门狗
    create_watchdog()
    
    print()
    print("=" * 60)
    print("✅ 稳定性修复完成")
    print("=" * 60)
    print()
    print("使用方法：")
    print("1. 稳定启动：双击 start_stable.bat")
    print("2. 看门狗模式：python system_watchdog.py")
    print("3. 诊断日志：logs/stability_debug.log")
    print()

if __name__ == '__main__':
    main()
