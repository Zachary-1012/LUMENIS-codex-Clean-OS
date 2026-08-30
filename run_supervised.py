# -*- coding: utf-8 -*-
"""
Z-Brand Core / CTH-POMS 进程看门狗（Supervisor）
作用：以子进程方式运行 app.py；无论子进程因 Python 异常、原生段错误还是被信号终止而退出，
都记录原因并在数秒内自动重启，保证 Web/API 永不长期离线——用户不在电脑前也能自愈。

- 子进程 stdout/stderr 追加到 logs/supervised_app.out
- 每次拉起/退出写入 logs/supervisor.log 与 data/supervisor_state.json（供系统状态中心展示自愈状态）
- 快速崩溃保护：启动后 BOOT_GRACE 秒内连续崩溃达阈值则拉长冷却，避免疯狂重启，但仍持续尝试
- Ctrl+C 优雅停止；不删数据库、不清历史

用法:
  .venv\\Scripts\\python.exe run_supervised.py --port 8201
  （其余参数原样透传给 app.py）
"""
import os, sys, time, json, subprocess, signal, argparse
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, 'logs'); DATA_DIR = os.path.join(ROOT, 'data')
os.makedirs(LOG_DIR, exist_ok=True); os.makedirs(DATA_DIR, exist_ok=True)
SUP_LOG = os.path.join(LOG_DIR, 'supervisor.log')
APP_OUT = os.path.join(LOG_DIR, 'supervised_app.out')
STATE = os.path.join(DATA_DIR, 'supervisor_state.json')

BOOT_GRACE = 20        # 启动后多少秒内退出算“快速崩溃”
FAST_CRASH_LIMIT = 5   # 连续快速崩溃达到此次数后进入长冷却
SHORT_RESTART = 3
LONG_RESTART = 30


def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        with open(SUP_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass


def write_state(d):
    try:
        d['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(STATE, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default=os.getenv('TAIKOO_HOST', '0.0.0.0'))
    ap.add_argument('--port', default=os.getenv('TAIKOO_PORT', '8200'))
    known, rest = ap.parse_known_args()
    cmd = [sys.executable, 'app.py', '--host', str(known.host), '--port', str(known.port)] + rest

    out_f = open(APP_OUT, 'a', encoding='utf-8')
    state = {'app': 'app.py', 'host': known.host, 'port': known.port,
             'started_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
             'restarts': 0, 'last_exit_code': None, 'last_restart_at': None, 'status': 'starting'}
    write_state(state)
    log(f"Supervisor 启动，目标: {' '.join(cmd)}")

    stop_flag = {'v': False}
    def _sig(a, b): stop_flag['v'] = True
    signal.signal(signal.SIGINT, _sig)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, _sig)

    fast_crashes = 0
    while not stop_flag['v']:
        t0 = time.time()
        log("拉起 app.py 子进程 ...")
        state['status'] = 'starting'; write_state(state)
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=out_f, stderr=subprocess.STDOUT,
                                creationflags=creationflags)
        state['pid'] = proc.pid; state['status'] = 'running'; write_state(state)
        log(f"子进程 PID={proc.pid}")
        rc = proc.wait()
        life = time.time() - t0
        state['last_exit_code'] = rc
        state['last_exit_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if stop_flag['v']:
            log(f"收到停止信号，子进程退出码={rc}，Supervisor 结束（不再重启）")
            state['status'] = 'stopped'; write_state(state); break
        log(f"!! app.py 退出，退出码={rc}，存活 {life:.1f}s")
        fast_crashes = fast_crashes + 1 if life < BOOT_GRACE else 0
        if fast_crashes >= FAST_CRASH_LIMIT:
            cool = LONG_RESTART
            log(f"连续快速崩溃 {fast_crashes} 次，进入 {cool}s 长冷却（仍会继续尝试自愈）")
        else:
            cool = SHORT_RESTART
        state['restarts'] += 1
        state['last_restart_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        state['status'] = 'restarting'; state['fast_crashes'] = fast_crashes
        write_state(state)
        for _ in range(cool):  # 可中断冷却
            if stop_flag['v']: break
            time.sleep(1)
    out_f.close()
    log("Supervisor 已退出")


if __name__ == '__main__':
    main()
