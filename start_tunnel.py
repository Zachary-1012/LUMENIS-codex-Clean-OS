# ============================================================
# Z-Brand-Core · Zachary-OS-AI T0-3 Legacy Redirect Notice
#  此入口已标注为 LEGACY（保留用于调试/历史兼容）。官方统一生产入口已收敛为：
#     powershell -ExecutionPolicy Bypass -File scripts\start_production.ps1
#  如确需直接执行此 .py，请使用项目 .venv：  .venv\Scripts\python.exe <this_file>.py
# ============================================================
"""启动 cloudflared 快速隧道（trycloudflare）并捕获公网 URL。

- 目标端口由环境变量 TUNNEL_PORT 指定，默认 8201（v4 验证实例）；切生产时设 TUNNEL_PORT=8200。
- cloudflared 路径按 CLOUDFLARED_BIN / 常见安装路径 / PATH 顺序探测。
- 用 DETACHED_PROCESS 让隧道独立于本脚本持续运行；URL/日志写入项目根，不硬编码旧目录。
注意：trycloudflare 为随机临时域名，进程重启后会变；固定域名需用 Cloudflare 命名隧道（账号 token）。
"""
import subprocess
import re
import os
import sys
import time
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET_PORT = os.getenv('TUNNEL_PORT', '8201')
url_file = os.path.join(ROOT, 'tunnel_url.txt')
log_file = os.path.join(ROOT, 'logs', 'cloudflared_tunnel.log')
os.makedirs(os.path.dirname(log_file), exist_ok=True)


def find_cloudflared():
    env = os.getenv('CLOUDFLARED_BIN')
    candidates = [
        env,
        r'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        r'C:\Program Files\cloudflared\cloudflared.exe',
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    found = shutil.which('cloudflared')
    return found


cloudflared = find_cloudflared()
if not cloudflared:
    print('未找到 cloudflared.exe，请设置 CLOUDFLARED_BIN 或安装 cloudflared。')
    sys.exit(1)

# 已存在同名隧道则提示（不强制杀，避免误断其它通道）
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

print(f'隧道目标: http://localhost:{TARGET_PORT}')
print(f'cloudflared: {cloudflared}')
with open(log_file, 'w', encoding='utf-8') as log_f:
    proc = subprocess.Popen(
        [cloudflared, 'tunnel', '--url', f'http://localhost:{TARGET_PORT}', '--protocol', 'http2'],
        cwd=ROOT,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
    )

print(f'cloudflared 已启动，PID: {proc.pid}')
print(f'日志文件: {log_file}')

url_found = False
start_time = time.time()
timeout = int(os.getenv('TUNNEL_WAIT', '75'))  # trycloudflare 首次建链通常 10-40s
url_re = re.compile(r'https://[-a-z0-9]+\.trycloudflare\.com')
while time.time() - start_time < timeout:
    time.sleep(1)
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        m = url_re.search(content)
        if m:
            url = m.group(0)
            with open(url_file, 'w', encoding='utf-8') as f:
                f.write(url)
            print(f'\nPUBLIC_URL: {url}')
            print(f'已写入: {url_file}')
            url_found = True
            break

if not url_found:
    print(f'{timeout}s 内未获取公网 URL，日志尾部：')
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            print(f.read()[-1500:])
    sys.exit(2)

print('\n脚本退出，cloudflared 独立持续运行；停止隧道：taskkill /F /PID <PID> 或按映像名结束 cloudflared。')
