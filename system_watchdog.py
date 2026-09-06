"""
系统看门狗 - 广州太古汇舆情监测系统 v5.8.0
监控系统运行状态，崩溃后自动重启
确保系统长时间稳定可用

[LEGACY NOTICE - ZBC Phase 2 Runtime Guardian 统一收敛]
本模块已由 runtime_guardian.py 接管为统一生命周期守护者（Worker->Lease->Heartbeat->
Checkpoint->Reaper->Retry->DLQ->Resume）。保留全部原有类与函数行为（向后兼容），
新代码请直接使用 runtime_guardian.RuntimeGuardian。不删除本文件，保持 import 兼容。
收敛工单：ZBC-PHASE2-RUNTIME-GUARDIAN-001
"""
import os
import sys
import time
import subprocess
import logging
import json
from datetime import datetime
from pathlib import Path

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'watchdog.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('watchdog')

# 配置参数
MAX_RESTARTS = 20  # 最大重启次数
RESTART_COOLDOWN = 60  # 重启冷却时间（秒）
HEALTH_CHECK_INTERVAL = 30  # 健康检查间隔（秒）
HEALTH_CHECK_URL = 'http://127.0.0.1:8200/api/dashboard/all'
SYSTEM_STARTUP_SCRIPT = 'app.py'
SYSTEM_HOST = '0.0.0.0'
SYSTEM_PORT = '8200'
# HTTP 认证信息：统一从环境变量读取，禁止在源码硬编码凭证（与 app.py 的 TAIKOO_AUTH_* 一致）
AUTH_USERNAME = os.getenv('TAIKOO_AUTH_USER', '')
AUTH_PASSWORD = os.getenv('TAIKOO_AUTH_PASSWORD', '')

class SystemWatchdog:
    """系统看门狗"""
    
    def __init__(self):
        self.restart_count = 0
        self.last_restart_time = 0
        self.current_process = None
        self.start_time = time.time()
        self.status_history = []
        
    def check_system_health(self):
        """检查系统健康状态"""
        try:
            import urllib.request
            import base64
            
            # 创建请求；仅在配置了凭证时才带 Basic 认证头（未配置则匿名，适配本机免认证场景）
            request = urllib.request.Request(HEALTH_CHECK_URL)
            if AUTH_USERNAME and AUTH_PASSWORD:
                auth_string = f"{AUTH_USERNAME}:{AUTH_PASSWORD}"
                base64_auth = base64.b64encode(auth_string.encode('ascii')).decode('ascii')
                request.add_header('Authorization', f'Basic {base64_auth}')
            
            response = urllib.request.urlopen(request, timeout=10)
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return True, data
            return False, {'error': f'HTTP状态码: {response.status}'}
        except Exception as e:
            return False, {'error': str(e)}
    
    def start_system(self):
        """启动系统"""
        logger.info("=" * 60)
        logger.info("启动系统...")
        logger.info("=" * 60)
        
        try:
            # 停止旧进程
            self.stop_system()
            
            # 启动新进程（使用全局Python）
            python_exe = 'python'  # 使用全局Python
            cmd = [python_exe, '-u', SYSTEM_STARTUP_SCRIPT, 
                   '--host', SYSTEM_HOST, '--port', SYSTEM_PORT]
            
            logger.info(f"启动命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {BASE_DIR}")
            
            self.current_process = subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                stdout=open(os.path.join(LOG_DIR, 'system_stdout.log'), 'a', encoding='utf-8'),
                stderr=open(os.path.join(LOG_DIR, 'system_stderr.log'), 'a', encoding='utf-8'),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            self.restart_count += 1
            self.last_restart_time = time.time()
            
            logger.info(f"系统已启动，PID: {self.current_process.pid}")
            logger.info(f"重启次数: {self.restart_count}/{MAX_RESTARTS}")
            
            # 等待系统启动
            logger.info("等待系统启动（30秒）...")
            time.sleep(30)
            
            # 检查系统是否启动成功
            healthy, data = self.check_system_health()
            if healthy:
                logger.info(f"✅ 系统启动成功，运行时间: {data.get('uptime_seconds', 'N/A')}秒")
                return True
            else:
                logger.warning(f"⚠️ 系统启动后健康检查失败: {data.get('error', '未知错误')}")
                return False
                
        except Exception as e:
            logger.error(f"启动系统失败: {e}", exc_info=True)
            return False
    
    def stop_system(self):
        """停止系统"""
        if self.current_process and self.current_process.poll() is None:
            try:
                logger.info(f"停止系统进程 PID: {self.current_process.pid}")
                self.current_process.terminate()
                time.sleep(3)
                if self.current_process.poll() is None:
                    self.current_process.kill()
                    time.sleep(2)
            except Exception as e:
                logger.error(f"停止系统进程失败: {e}")
        
        # 强制停止所有Python进程（除了看门狗自己）
        try:
            if sys.platform == 'win32':
                # Windows下使用wmic获取进程列表，只杀死不是看门狗的python进程
                my_pid = os.getpid()
                result = subprocess.run(['wmic', 'process', 'where', 
                                       "name='python.exe'", 'get', 'processid', '/format:csv'],
                                      capture_output=True, text=True, timeout=10)
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # 跳过表头
                        if line.strip():
                            parts = line.split(',')
                            if len(parts) >= 2:
                                try:
                                    pid = int(parts[1].strip())
                                    if pid != my_pid:
                                        subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                                                     capture_output=True, timeout=5)
                                except (ValueError, IndexError):
                                    pass
            else:
                # Linux/Mac下使用pkill
                my_pid = os.getpid()
                result = subprocess.run(['pgrep', '-f', 'python'], capture_output=True, text=True)
                if result.stdout:
                    for pid_str in result.stdout.split():
                        pid = int(pid_str)
                        if pid != my_pid:
                            subprocess.run(['kill', '-9', str(pid)], capture_output=True)
        except Exception as e:
            logger.error(f"强制停止Python进程失败: {e}")
        
        time.sleep(3)
    
    def run(self):
        """运行看门狗主循环"""
        logger.info("=" * 60)
        logger.info("系统看门狗已启动")
        logger.info(f"最大重启次数: {MAX_RESTARTS}")
        logger.info(f"健康检查间隔: {HEALTH_CHECK_INTERVAL}秒")
        logger.info(f"系统地址: http://{SYSTEM_HOST}:{SYSTEM_PORT}")
        logger.info("=" * 60)
        
        # 首次启动系统
        if not self.start_system():
            logger.error("首次启动系统失败")
        
        # 主循环
        consecutive_failures = 0
        
        while True:
            try:
                # 检查是否达到最大重启次数
                if self.restart_count >= MAX_RESTARTS:
                    logger.critical(f"已达到最大重启次数 ({MAX_RESTARTS})，看门狗退出")
                    break
                
                # 检查系统进程是否还在运行
                if self.current_process and self.current_process.poll() is not None:
                    logger.warning(f"系统进程已退出，退出码: {self.current_process.returncode}")
                    consecutive_failures += 1
                    
                    # 检查冷却时间
                    time_since_restart = time.time() - self.last_restart_time
                    if time_since_restart < RESTART_COOLDOWN:
                        wait_time = RESTART_COOLDOWN - time_since_restart
                        logger.info(f"等待重启冷却时间: {wait_time:.1f}秒")
                        time.sleep(wait_time)
                    
                    # 重启系统
                    if self.start_system():
                        consecutive_failures = 0
                    else:
                        logger.error("系统重启失败")
                else:
                    # 进程在运行，进行健康检查
                    healthy, data = self.check_system_health()
                    
                    if healthy:
                        consecutive_failures = 0
                        uptime = data.get('uptime_seconds', 'N/A')
                        logger.info(f"✅ 系统健康，运行时间: {uptime}秒，重启次数: {self.restart_count}")
                    else:
                        consecutive_failures += 1
                        logger.warning(f"⚠️ 系统健康检查失败 ({consecutive_failures}次): {data.get('error', '未知错误')}")
                        
                        # 连续3次健康检查失败，重启系统
                        if consecutive_failures >= 3:
                            logger.warning("连续3次健康检查失败，准备重启系统...")
                            if self.start_system():
                                consecutive_failures = 0
                            else:
                                logger.error("系统重启失败")
                
                # 记录状态
                self.status_history.append({
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'healthy': healthy if 'healthy' in dir() else False,
                    'restart_count': self.restart_count,
                    'consecutive_failures': consecutive_failures,
                })
                
                # 只保留最近100条状态记录
                if len(self.status_history) > 100:
                    self.status_history = self.status_history[-100:]
                
                # 等待下一次健康检查
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("看门狗被用户中断")
                break
            except Exception as e:
                logger.error(f"看门狗主循环异常: {e}", exc_info=True)
                time.sleep(10)
        
        # 退出前停止系统
        logger.info("看门狗退出，停止系统...")
        self.stop_system()
        logger.info("系统已停止")

def main():
    """主函数"""
    print("=" * 60)
    print("广州太古汇舆情监测系统 - 看门狗模式")
    print("=" * 60)
    print()
    print("看门狗将监控系统运行状态，崩溃后自动重启")
    print(f"系统地址: http://127.0.0.1:8200")
    print(f"最大重启次数: {MAX_RESTARTS}")
    print(f"健康检查间隔: {HEALTH_CHECK_INTERVAL}秒")
    print()
    print("按 Ctrl+C 停止看门狗")
    print("=" * 60)
    print()
    
    watchdog = SystemWatchdog()
    watchdog.run()

if __name__ == '__main__':
    main()
