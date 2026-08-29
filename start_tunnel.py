"""启动cloudflared并捕获URL，用DETACHED_PROCESS让进程独立运行"""
import subprocess
import re
import os
import sys
import time

dst = r"D:\taikoo-monitor\taikoo-monitor-v4.2-remote-optimized\taikoo-monitor-clean"
cloudflared = r"C:\Program Files (x86)\cloudflared\cloudflared.exe"
url_file = os.path.join(dst, "tunnel_url.txt")
log_file = os.path.join(dst, "tunnel_log.txt")

# 用DETACHED_PROCESS启动cloudflared，输出重定向到文件
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

with open(log_file, 'w', encoding='utf-8') as log_f:
    proc = subprocess.Popen(
        [cloudflared, "tunnel", "--url", "http://localhost:8200", "--protocol", "http2"],
        cwd=dst,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW
    )

print(f"cloudflared已启动，PID: {proc.pid}")
print(f"日志文件: {log_file}")

# 等待并读取日志文件，查找URL
url_found = False
start_time = time.time()
while time.time() - start_time < 30:
    time.sleep(1)
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', content)
            if match:
                url = match.group(0)
                with open(url_file, 'w', encoding='utf-8') as f:
                    f.write(url)
                print(f"\nURL: {url}")
                print(f"URL已写入: {url_file}")
                url_found = True
                break

if not url_found:
    print("30秒内未找到URL")
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
            print("日志内容:")
            print(f.read()[-1000:])

print("\n脚本退出，cloudflared继续独立运行")
