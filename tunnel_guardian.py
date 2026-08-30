"""
Cloudflare Tunnel 守护脚本（V3.0 稳定版）
功能：
  1. 监控 cloudflared 隧道状态，断了自动重连
  2. 自动捕获公网 URL，写入 tunnel_url.txt
  3. 健康检查：定期验证隧道可访问
  4. 日志记录：隧道启动/重连/失败日志
  5. 目标端口可配置：默认 8200（生产）
用法：
  python tunnel_guardian.py [--port 8200] [--interval 30]
"""
import subprocess
import re
import os
import sys
import time
import shutil
import argparse
import threading
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
URL_FILE = os.path.join(ROOT, 'tunnel_url.txt')
LOG_DIR = os.path.join(ROOT, 'data', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'tunnel_guardian.log')
PID_FILE = os.path.join(ROOT, 'data', 'tunnel_guardian.pid')

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)


def log(msg: str):
    """写日志"""
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def find_cloudflared() -> str:
    """查找 cloudflared 可执行文件"""
    env = os.getenv('CLOUDFLARED_BIN')
    candidates = [
        env,
        os.path.join(ROOT, 'cloudflared.exe'),
        r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        r'C:\Program Files\cloudflared\cloudflared.exe',
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    found = shutil.which('cloudflared')
    return found or ''


def extract_url_from_log(log_text: str) -> str:
    """从 cloudflared 日志中提取公网 URL"""
    # 匹配 https://xxx.trycloudflare.com
    patterns = [
        r'https://[a-zA-Z0-9-]+\.trycloudflare\.com',
        r'https://[a-zA-Z0-9.-]+\.trycloudflare\.com',
    ]
    for pattern in patterns:
        m = re.search(pattern, log_text)
        if m:
            return m.group(0)
    return ''


class TunnelGuardian:
    """隧道守护器"""

    def __init__(self, port: int = 8200, interval: int = 30):
        self.port = port
        self.interval = interval
        self.cloudflared = find_cloudflared()
        self.proc = None
        self.current_url = ''
        self.running = True
        self.reconnect_count = 0
        self.last_health_check = 0

    def start_tunnel(self) -> bool:
        """启动 cloudflared 隧道"""
        if not self.cloudflared:
            log('错误：未找到 cloudflared.exe')
            return False

        # 停止旧进程
        self.stop_tunnel()
        time.sleep(1)

        log(f'启动隧道: http://localhost:{self.port}')
        log(f'cloudflared: {self.cloudflared}')

        try:
            CREATE_NO_WINDOW = 0x08000000
            DETACHED_PROCESS = 0x00000008

            self.proc = subprocess.Popen(
                [
                    self.cloudflared, 'tunnel',
                    '--url', f'http://localhost:{self.port}',
                    '--protocol', 'http2',
                    '--no-autoupdate',
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                text=True,
                encoding='utf-8',
                errors='replace',
            )

            # 等待 URL 出现（最多 30 秒）
            url = ''
            log_buffer = []
            start_time = time.time()
            while time.time() - start_time < 30:
                if self.proc.poll() is not None:
                    log(f'错误：cloudflared 进程已退出，code={self.proc.returncode}')
                    return False

                try:
                    line = self.proc.stdout.readline()
                    if line:
                        log_buffer.append(line.strip())
                        url = extract_url_from_log(line)
                        if url:
                            break
                    else:
                        time.sleep(0.5)
                except Exception:
                    time.sleep(0.5)

            if url:
                self.current_url = url
                self.reconnect_count += 1
                # 写入 URL 文件
                with open(URL_FILE, 'w', encoding='utf-8') as f:
                    f.write(url + '\n')
                log(f'隧道启动成功: {url} (第{self.reconnect_count}次连接)')
                return True
            else:
                log('错误：30秒内未获取到公网URL')
                log(f'日志片段: {" | ".join(log_buffer[-5:])}')
                self.stop_tunnel()
                return False

        except Exception as e:
            log(f'启动隧道异常: {e}')
            return False

    def stop_tunnel(self):
        """停止隧道进程"""
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
                log('隧道进程已停止')
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None

    def health_check(self) -> bool:
        """健康检查：验证隧道可访问"""
        if not self.current_url:
            return False

        try:
            import urllib.request
            req = urllib.request.Request(
                self.current_url + '/healthz',
                headers={'User-Agent': 'TunnelGuardian/1.0'},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return True
        except Exception as e:
            log(f'健康检查失败: {e}')
        return False

    def run(self):
        """主循环：监控 + 自动重连"""
        log(f'=== 隧道守护启动 (端口={self.port}, 检查间隔={self.interval}s) ===')

        # 写入 PID 文件
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        # 首次启动
        if not self.start_tunnel():
            log('首次启动失败，5秒后重试...')
            time.sleep(5)
            self.start_tunnel()

        while self.running:
            try:
                time.sleep(self.interval)

                # 检查进程是否存活
                if not self.proc or self.proc.poll() is not None:
                    log('检测到隧道进程已退出，正在重连...')
                    self.start_tunnel()
                    continue

                # 定期健康检查（每 2 次检查做一次）
                now = time.time()
                if now - self.last_health_check > self.interval * 2:
                    self.last_health_check = now
                    if not self.health_check():
                        log('健康检查失败，正在重连...')
                        self.start_tunnel()

            except KeyboardInterrupt:
                log('收到中断信号，停止守护...')
                break
            except Exception as e:
                log(f'守护循环异常: {e}')
                time.sleep(5)

        self.stop_tunnel()
        # 清理 PID 文件
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        log('=== 隧道守护已停止 ===')


def main():
    parser = argparse.ArgumentParser(description='Cloudflare Tunnel 守护脚本')
    parser.add_argument('--port', type=int, default=8200, help='目标端口（默认8200生产）')
    parser.add_argument('--interval', type=int, default=30, help='检查间隔秒数（默认30）')
    args = parser.parse_args()

    guardian = TunnelGuardian(port=args.port, interval=args.interval)
    guardian.run()


if __name__ == '__main__':
    main()
