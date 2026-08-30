# -*- coding: utf-8 -*-
"""Z-Brand Core / CTH-POMS 进程看门狗（生产常驻监督器）。

解决两类宕机：
1) 子进程真退出（含原生崩溃，退出码非0）-> 3 秒自动拉起；快速连续崩溃 -> 指数长冷却，不疯狂刷。
2) “假活”：Flask 为 multiprocessing 父子双进程，真正监听端口的 worker 原生崩溃后，父进程可能
   不退出，只盯进程会误判存活。故叠加 /healthz 端口探测：进程在但端口连续 N 次不通 => 杀整棵进程树重启。

监督器自身需以“脱离会话的独立常驻进程”方式启动（pythonw + Start-Process / 计划任务 / 启动项），
不依赖任何交互式 shell，否则会话结束监督器会被一并回收。
"""
import os
import subprocess
import sys
import time
import json
import signal
import socket
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / 'supervisor.log'
STATE_FILE = ROOT / 'data' / 'supervisor_state.json'
APP_OUT = LOG_DIR / 'supervised_app.out'

POLL_INTERVAL = 2                # 每 2 秒看一次子进程
HEALTH_INTERVAL = 10             # 每 10 秒探一次端口
HEALTH_FAIL_THRESHOLD = 3        # 连续 3 次不通(约30s)判定假活
RESTART_GRACE = 3
FAST_CRASH_WINDOW = 60
FAST_CRASH_LIMIT = 5
FAST_CRASH_COOLDOWN = 60
MAX_BACKOFF = 300


def log(msg):
    line = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def write_state(**kw):
    try:
        STATE_FILE.parent.mkdir(exist_ok=True)
        kw['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(kw, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def http_health(port, timeout=3):
    """探 /healthz；返回 True/False，不依赖第三方库。"""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=timeout) as r:
            return 200 <= r.status < 500
    except Exception:
        return False


def port_listening(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        return s.connect_ex(('127.0.0.1', int(port))) == 0
    finally:
        s.close()


def kill_tree(pid):
    """Windows 下杀整棵进程树（父+multiprocessing worker），避免残留假活父进程。"""
    try:
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'],
                       capture_output=True, creationflags=0x08000000)  # CREATE_NO_WINDOW
        log(f'已杀进程树 PID={pid}')
    except Exception as e:
        log(f'杀进程树失败 PID={pid}: {e}')


def spawn(app, host, port):
    out = open(APP_OUT, 'a', encoding='utf-8')
    creationflags = 0x08000000 if sys.platform == 'win32' else 0
    proc = subprocess.Popen(
        [sys.executable, '-u', app, '--host', host, '--port', str(port)],
        cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    return proc


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', default='app.py')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', default='8201')
    args = ap.parse_args()

    stopping = False

    def _sig(sig, frame):
        nonlocal stopping
        stopping = True
    signal.signal(signal.SIGINT, _sig)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _sig)

    log(f'Supervisor 启动(常驻+健康探测)，目标: {sys.executable} {args.app} --host {args.host} --port {args.port}')
    crash_times = []
    proc = spawn(args.app, args.host, args.port)
    started = time.time()
    health_fails = 0
    last_health = 0.0
    write_state(app=args.app, host=args.host, port=args.port,
                started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                restarts=0, status='starting', pid=proc.pid, fast_crashes=0)

    while not stopping:
        rc = proc.poll()

        # —— 分支1：子进程真的退出了 ——
        if rc is not None:
            life = time.time() - started
            log(f'!! {args.app} 退出，退出码={rc}，存活 {life:.1f}s')
            now = time.time()
            crash_times = [t for t in crash_times if now - t < FAST_CRASH_WINDOW]
            crash_times.append(now)
            backoff = 0
            if len(crash_times) >= FAST_CRASH_LIMIT:
                step = min(FAST_CRASH_COOLDOWN * (2 ** (len(crash_times) - FAST_CRASH_LIMIT)), MAX_BACKOFF)
                backoff = step
                log(f'快速崩溃 {len(crash_times)} 次，冷却 {backoff}s 再拉起，避免空转刷进程')
                write_state(status='backoff', pid=proc.pid, fast_crashes=len(crash_times),
                            last_exit_code=rc, backoff_seconds=backoff)
            time.sleep(RESTART_GRACE + backoff)
            if stopping:
                break
            log('拉起 app.py 子进程 ...')
            proc = spawn(args.app, args.host, args.port)
            started = time.time()
            health_fails = 0
            last_health = 0.0
            write_state(status='starting', pid=proc.pid, restarts=len(crash_times),
                        fast_crashes=len(crash_times), last_exit_code=rc)
            continue

        # —— 分支2：进程在，但端口/健康探测（抓 multiprocessing worker 崩溃的“假活”）——
        now = time.time()
        if now - last_health >= HEALTH_INTERVAL:
            last_health = now
            # 给新启动留 25s 宽限，避免启动慢被误杀
            if time.time() - started > 25:
                if http_health(args.port):
                    if health_fails:
                        log(f'健康探测恢复（此前连续失败 {health_fails} 次）')
                    health_fails = 0
                    write_state(status='running', pid=proc.pid, restarts=len(crash_times),
                                fast_crashes=len(crash_times))
                else:
                    health_fails += 1
                    log(f'健康探测失败 {health_fails}/{HEALTH_FAIL_THRESHOLD}（进程 PID={proc.pid} 在，端口不通）')
                    if health_fails >= HEALTH_FAIL_THRESHOLD:
                        log(f'!! 判定假活：进程在但服务连续 {health_fails} 次不可达，杀整棵进程树重启')
                        kill_tree(proc.pid)
                        time.sleep(2)
                        try:
                            proc.wait(timeout=5)
                        except Exception:
                            pass
                        crash_times.append(time.time())
                        proc = spawn(args.app, args.host, args.port)
                        started = time.time()
                        health_fails = 0
                        last_health = 0.0
                        write_state(status='restart_after_zombie', pid=proc.pid,
                                    restarts=len(crash_times), note='worker假活杀树重启')
        time.sleep(POLL_INTERVAL)

    log('Supervisor 收到停止信号，关闭子进程 ...')
    kill_tree(proc.pid)
    write_state(status='stopped', pid=proc.pid)
    log('Supervisor 已退出')


if __name__ == '__main__':
    main()
