"""
采集器自动化启动模块 v1.0
功能：
1. 自动检测Edge浏览器是否安装
2. 自动启动Edge浏览器带CDP端口
3. 检测CDP端口是否可用
4. 自动重试机制
5. 采集状态管理
"""

import os
import sys
import time
import subprocess
import socket
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class CollectorAutoStarter:
    """采集器自动化启动器"""

    def __init__(self):
        self.cdp_port = 9222
        self.edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Users\%s\AppData\Local\Microsoft\Edge\Application\msedge.exe" % os.environ.get('USERNAME', ''),
        ]
        self.user_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'edge-cdp-profile')
        self.process = None
        self.status_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'collector_status.json')

    def find_edge(self):
        """查找Edge浏览器路径"""
        for path in self.edge_paths:
            if os.path.exists(path):
                return path
        # 尝试从注册表查找
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
            path, _ = winreg.QueryValueEx(key, "")
            winreg.CloseKey(key)
            if os.path.exists(path):
                return path
        except:
            pass
        return None

    def is_port_open(self, port):
        """检查端口是否开放"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0
        except:
            return False

    def check_cdp_available(self):
        """检查CDP是否可用"""
        try:
            import urllib.request
            response = urllib.request.urlopen(f"http://127.0.0.1:{self.cdp_port}/json/version", timeout=3)
            data = json.loads(response.read())
            return 'webSocketDebuggerUrl' in data
        except:
            return False

    def start_edge_with_cdp(self):
        """启动Edge浏览器带CDP端口"""
        edge_path = self.find_edge()
        if not edge_path:
            return {'ok': False, 'error': '未找到Edge浏览器，请先安装Microsoft Edge'}

        # 检查是否已经在运行
        if self.is_port_open(self.cdp_port):
            if self.check_cdp_available():
                self.update_status('running', 'CDP已在运行')
                return {'ok': True, 'message': 'CDP已在运行', 'port': self.cdp_port}

        # 创建用户数据目录
        os.makedirs(self.user_data_dir, exist_ok=True)

        # 启动Edge
        cmd = [
            edge_path,
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={self.user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-popup-blocking",
            "--start-maximized",
            "about:blank"
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            self.update_status('starting', 'Edge启动中')

            # 等待CDP可用
            for i in range(15):
                time.sleep(2)
                if self.check_cdp_available():
                    self.update_status('running', 'CDP已就绪')
                    return {'ok': True, 'message': 'Edge启动成功，CDP已就绪', 'port': self.cdp_port}

            self.update_status('error', 'CDP启动超时')
            return {'ok': False, 'error': 'Edge启动成功，但CDP端口未就绪，请手动检查'}

        except Exception as e:
            self.update_status('error', f'启动失败: {str(e)}')
            return {'ok': False, 'error': f'启动Edge失败: {str(e)}'}

    def stop_edge(self):
        """停止本采集器启动的 Edge（独立 profile，按 PID 精确关闭，不全量 taskkill 以免误关用户窗口）"""
        try:
            if self.process and self.process.poll() is None:
                pid = self.process.pid
                if sys.platform == 'win32':
                    subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True, timeout=15)
                else:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=8)
                    except Exception:
                        self.process.kill()
            self.process = None
            self.update_status('stopped', 'Edge已停止')
            return {'ok': True, 'message': 'Edge已停止'}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def get_status(self):
        """获取采集器状态"""
        status = self.load_status()
        status['cdp_port'] = self.cdp_port
        status['cdp_available'] = self.check_cdp_available()
        status['port_open'] = self.is_port_open(self.cdp_port)
        status['edge_found'] = self.find_edge() is not None
        return status

    def update_status(self, state, message):
        """更新状态文件"""
        status = {
            'state': state,
            'message': message,
            'updated_at': datetime.now().isoformat(),
            'cdp_port': self.cdp_port
        }
        try:
            os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_status(self):
        """加载状态文件"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {'state': 'unknown', 'message': '状态未知'}


# 全局实例
collector_starter = CollectorAutoStarter()

print("[CollectorAuto] 采集器自动化启动模块已加载", flush=True)
