# -*- coding: utf-8 -*-
"""LUMENIS Product Core process supervisor.

The canonical Windows launcher is scripts/start_production.ps1. This module is
its owned 8201 child supervisor: it restarts a crashed Core and detects a live
process whose health endpoint is unavailable. Historical Z-Brand/CTH-POMS names
do not define the current product identity.
"""
import errno
import hashlib
import os
import subprocess
import sys
import time
import json
import signal
import socket
import threading
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path


def _force_utf8_stdio():
    """Supervisor diagnostics must survive legacy Windows console/pipe code pages."""
    for _stream in (sys.stdout, sys.stderr):
        try:
            if _stream is not None and hasattr(_stream, 'reconfigure'):
                _stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass


_force_utf8_stdio()

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / 'logs'
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
CHILD_SHUTDOWN_TIMEOUT = 10
LOCK_CONTENTION_ERRNOS = {errno.EACCES, errno.EAGAIN, errno.EDEADLK}


def _pid_alive(pid):
    """检查 Windows 进程是否存活（ctypes，无重依赖）。"""
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    except Exception:
        return False


def log(msg):
    line = f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {msg}'
    print(line, flush=True)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
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
        return True
    except Exception:
        return False


def http_health(port, timeout=3, *, expected_launch_id=None,
                expected_boot_id=None, expected_entry_sha256=None):
    """只接受 Product Core 的真实 healthy + database-ok 响应。"""
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/healthz', timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read(16 * 1024).decode('utf-8'))
        dependencies = payload.get('dependencies')
        return (
            payload.get('ok') is True
            and payload.get('status') == 'healthy'
            and isinstance(dependencies, dict)
            and dependencies.get('database') == 'ok'
            and _matches_core_identity(
                payload,
                expected_launch_id=expected_launch_id,
                expected_boot_id=expected_boot_id,
                expected_entry_sha256=expected_entry_sha256,
            )
        )
    except Exception:
        return False


def _matches_core_identity(payload, *, expected_launch_id=None,
                           expected_boot_id=None, expected_entry_sha256=None):
    expected = {
        'launch_id': expected_launch_id,
        'boot_id': expected_boot_id,
        'entry_sha256': expected_entry_sha256,
    }
    expected = {key: value for key, value in expected.items() if value is not None}
    if not expected:
        return True
    core_instance = payload.get('core_instance')
    return (
        isinstance(core_instance, dict)
        and all(core_instance.get(key) == value for key, value in expected.items())
    )


def port_listening(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        return s.connect_ex(('127.0.0.1', int(port))) == 0
    finally:
        s.close()


def _kill_windows_owned_tree(proc, timeout):
    """Freeze and reap only the owned Popen tree, with PID-reuse protection."""
    import psutil

    deadline = time.monotonic() + max(0.0, float(timeout))
    owned = list(getattr(proc, '_owned_windows_processes', ()))
    frozen = []
    confirmed = False
    try:
        if proc.poll() is None:
            root = psutil.Process(proc.pid)
            # The Popen handle proves this PID still belongs to this child.
            if proc.poll() is not None or not root.is_running():
                return False
            owned.insert(0, root)
        owned = list({(p.pid, p.create_time()): p for p in owned}.values())
        identities = {(p.pid, p.create_time()) for p in owned}
        proc._owned_windows_processes = tuple(owned)
        index = 0
        while index < len(owned):
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired('owned process discovery', timeout)
            member = owned[index]
            index += 1
            if not member.is_running():
                # Do not infer that an exiting parent left no descendants.
                # A retry may skip only a previously fully discovered tree.
                if not getattr(proc, '_owned_windows_tree_discovered', False):
                    return False
                continue
            # Freeze each parent before discovering its immediate children.
            # Once every discovered member is frozen, no member can spawn more.
            member.suspend()
            frozen.append(member)
            for child in member.children():
                identity = (child.pid, child.create_time())
                if identity not in identities:
                    identities.add(identity)
                    owned.append(child)
                    proc._owned_windows_processes = tuple(owned)
        proc._owned_windows_tree_discovered = True
        for member in reversed(frozen):
            try:
                member.kill()
            except psutil.NoSuchProcess:
                continue
        _, alive = psutil.wait_procs(owned, timeout=max(0.0, deadline - time.monotonic()))
        if alive:
            log(f'未确认全部 owned 子进程退出 PID={proc.pid}')
            return False
        proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        confirmed = proc.poll() is not None
        if confirmed:
            proc._owned_windows_processes = ()
            log(f'已确认 owned 进程树退出 PID={proc.pid}, members={len(identities)}')
        return confirmed
    except (psutil.Error, OSError, subprocess.TimeoutExpired) as exc:
        log(f'停止 owned 进程树未获确认 PID={proc.pid}: {type(exc).__name__}')
        return False
    finally:
        if not confirmed:
            # Failed cleanup must not leave live owned members suspended.
            # Their identity-fenced objects remain attached for the final retry.
            for member in reversed(frozen):
                try:
                    if member.is_running():
                        member.resume()
                except psutil.Error:
                    log(f'恢复 owned 进程暂停状态失败 PID={member.pid}')


def kill_tree(proc, timeout=CHILD_SHUTDOWN_TIMEOUT):
    """终止由本监督器启动的子进程树，并确认全部已知成员退出。"""
    if proc is None:
        return True
    try:
        if proc.poll() is not None and not getattr(proc, '_owned_windows_processes', ()):
            proc.wait(timeout=0)
            return True

        if sys.platform == 'win32':
            return _kill_windows_owned_tree(proc, timeout)
        else:
            # The supervisor itself requires the Windows msvcrt lock. This direct-child
            # path keeps the helper testable on other platforms without scanning processes.
            proc.terminate()

        proc.wait(timeout=timeout)
        if proc.poll() is None:
            log(f'进程树停止后子进程仍存活 PID={proc.pid}')
            return False
        log(f'已确认子进程退出 PID={proc.pid}')
        return True
    except subprocess.TimeoutExpired:
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass
        log(f'停止进程树超时 PID={proc.pid}')
        return False
    except Exception as e:
        try:
            proc.wait(timeout=timeout)
        except Exception:
            pass
        log(f'停止进程树失败 PID={proc.pid}: {e}')
        return False


def _normalize_launch_id(value=None):
    try:
        return uuid.uuid4().hex if value is None else uuid.UUID(str(value)).hex
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError('launch_id must be a valid UUID') from exc


def _resolve_core_entry(app):
    root = Path(ROOT).resolve()
    requested = Path(app)
    if not requested.is_absolute():
        requested = root / requested
    try:
        entry = requested.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError('Core entry must exist within the runtime root') from exc
    if not entry.is_file():
        raise ValueError('Core entry must be a file within the runtime root')
    root_path = os.path.normcase(str(root))
    entry_path = os.path.normcase(str(entry))
    try:
        inside_root = os.path.commonpath((root_path, entry_path)) == root_path
    except ValueError:
        inside_root = False
    if not inside_root:
        raise ValueError('Core entry must resolve within the runtime root')
    return entry


def _process_identity(proc):
    return {
        'launch_id': proc.launch_id,
        'boot_id': proc.boot_id,
        'entry_sha256': proc.entry_sha256,
    }


def spawn(app, host, port, launch_id=None, *, no_scheduler=False):
    launch_id = _normalize_launch_id(launch_id)
    entry = _resolve_core_entry(app)
    # This identifies the exact entry file and spawn attempt, not the full runtime tree.
    entry_sha256 = hashlib.sha256(entry.read_bytes()).hexdigest()
    boot_id = uuid.uuid4().hex
    creationflags = 0x08000000 if sys.platform == 'win32' else 0
    APP_OUT.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        'PYTHONUTF8': '1',
        'PYTHONIOENCODING': 'utf-8',
        'LUMENIS_CORE_LAUNCH_ID': launch_id,
        'LUMENIS_CORE_BOOT_ID': boot_id,
        'LUMENIS_CORE_ENTRY_SHA256': entry_sha256,
    }
    child_args = [sys.executable, '-X', 'utf8', '-u', str(entry), '--host', host, '--port', str(port)]
    if no_scheduler:
        child_args.append('--no-scheduler')
    with open(APP_OUT, 'a', encoding='utf-8') as out:
        proc = subprocess.Popen(
            child_args,
            cwd=str(ROOT), stdout=out, stderr=subprocess.STDOUT,
            creationflags=creationflags, env=env,
        )
    proc.launch_id = launch_id
    proc.boot_id = boot_id
    proc.entry_sha256 = entry_sha256
    return proc


def _is_lock_contention(exc):
    """Distinguish the expected nonblocking-lock collision from setup failures."""
    return (
        exc.errno in LOCK_CONTENTION_ERRNOS
        or getattr(exc, 'winerror', None) == 33  # ERROR_LOCK_VIOLATION
    )


def acquire_instance_lock(lock_path, port):
    """Return the owned lock handle, or None only for a benign duplicate instance."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    import msvcrt  # Windows-only production supervisor lock.

    handle = open(str(lock_path), 'a+', encoding='utf-8')
    try:
        # Windows locks only bytes that exist in the file, so reserve one byte first.
        if handle.seek(0, 2) == 0:
            handle.write(' ')
            handle.flush()
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if _is_lock_contention(exc):
                handle.close()
                return None
            raise

        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()))
        handle.flush()
        return handle
    except Exception:
        try:
            handle.close()
        except Exception:
            pass
        raise


def _release_instance_lock(handle):
    if handle is None:
        return True
    try:
        handle.close()
        return True
    except Exception as exc:
        log(f'释放单实例锁失败: {exc}')
        return False


def _wait_or_stop(stop_event, is_stopping, timeout):
    """Wait in bounded Event.wait slices so signal handling never takes a lock."""
    remaining = max(0.0, float(timeout))
    while remaining > 0 and not is_stopping():
        interval = min(remaining, 1.0)
        stop_event.wait(interval)
        remaining -= interval
    return is_stopping()


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--app', default='app.py')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', default='8201')
    ap.add_argument('--launch-id', type=uuid.UUID, default=None)
    ap.add_argument('--no-scheduler', action='store_true',
                    help='Start the Core child without scheduler automation.')
    args = ap.parse_args()
    launch_id = _normalize_launch_id(args.launch_id)

    # ===== 单实例保护：意外锁错误必须 fail closed；只有已持锁才作为重复实例正常退出 =====
    _lock = ROOT / 'data' / f'supervisor_{args.port}.lock'
    try:
        _lock_handle = acquire_instance_lock(_lock, args.port)
    except Exception as _e:
        log(f'单实例保护检查失败，拒绝启动: {_e}')
        raise SystemExit(1)
    if _lock_handle is None:
        try:
            _old = _lock.read_text().strip()
        except Exception:
            _old = ''
        log(f'Supervisor 已存在(PID={_old or "?"}，端口 {args.port})，退出避免重复守护')
        raise SystemExit(0)
    log(f'Supervisor 单实例锁写入 PID={os.getpid()} (port {args.port})')

    # ===== 双重防线: 端口已被健康实例监听则退出（跨权限/跨进程可靠，防 HealthGuard 与手动启动时序错开产生双 supervisor）=====
    try:
        import socket as _socket
        import urllib.request as _urllib
        _probe = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        _probe.settimeout(2)
        _can_bind = True
        try:
            _probe.bind(('127.0.0.1', int(args.port)))
        except OSError:
            _can_bind = False
        finally:
            _probe.close()
        def _probe_health():
            try:
                with _urllib.urlopen(f'http://127.0.0.1:{args.port}/healthz', timeout=2) as _r:
                    return _r.status == 200
            except Exception:
                return False
        if not _can_bind:
            # 端口已被监听 = 已有实例在跑(可能 app 仍在启动中), 一律退出避免双实例; 僵尸场景由 HealthGuard ps1 清理
            log(f'端口 {args.port} 已被占用, 退出避免重复守护(既有实例由 supervisor/HealthGuard 管理)')
            if not _release_instance_lock(_lock_handle):
                raise SystemExit(1)
            raise SystemExit(0)
    except Exception as _e:
        log(f'端口健康检查异常(继续启动): {_e}')

    stop_event = threading.Event()
    stopping = False

    def _sig(sig, frame):
        # Keep signal handling to a plain flag assignment. Event.wait is checked
        # in bounded slices below, avoiding locks inside the signal handler.
        nonlocal stopping
        stopping = True

    crash_times = []
    proc = None
    child_started = False
    cleanup_confirmed = True
    state_saved = True
    restart_failure = None
    try:
        signal.signal(signal.SIGINT, _sig)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, _sig)

        log(f'Supervisor 启动(常驻+健康探测)，目标: {sys.executable} {args.app} --host {args.host} --port {args.port}')
        proc = spawn(args.app, args.host, args.port, launch_id=launch_id,
                     no_scheduler=args.no_scheduler)
        child_started = True
        started = time.time()
        health_fails = 0
        last_health = 0.0
        write_state(app=args.app, host=args.host, port=args.port,
                    started_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    restarts=0, status='starting', pid=proc.pid, fast_crashes=0,
                    **_process_identity(proc))

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
                                last_exit_code=rc, backoff_seconds=backoff,
                                **_process_identity(proc))
                if _wait_or_stop(stop_event, lambda: stopping, RESTART_GRACE + backoff):
                    break
                log('拉起 app.py 子进程 ...')
                proc = spawn(args.app, args.host, args.port, launch_id=launch_id,
                             no_scheduler=args.no_scheduler)
                started = time.time()
                health_fails = 0
                last_health = 0.0
                write_state(status='starting', pid=proc.pid, restarts=len(crash_times),
                            fast_crashes=len(crash_times), last_exit_code=rc,
                            **_process_identity(proc))
                continue

            # —— 分支2：进程在，但端口/健康探测（抓 multiprocessing worker 崩溃的“假活”）——
            now = time.time()
            if now - last_health >= HEALTH_INTERVAL:
                last_health = now
                # 给新启动留 25s 宽限，避免启动慢被误杀
                if time.time() - started > 25:
                    if http_health(
                        args.port,
                        expected_launch_id=proc.launch_id,
                        expected_boot_id=proc.boot_id,
                        expected_entry_sha256=proc.entry_sha256,
                    ):
                        if health_fails:
                            log(f'健康探测恢复（此前连续失败 {health_fails} 次）')
                        health_fails = 0
                        write_state(status='running', pid=proc.pid, restarts=len(crash_times),
                                    fast_crashes=len(crash_times),
                                    **_process_identity(proc))
                    else:
                        health_fails += 1
                        log(f'健康探测失败 {health_fails}/{HEALTH_FAIL_THRESHOLD}（进程 PID={proc.pid} 在，端口不通）')
                        if health_fails >= HEALTH_FAIL_THRESHOLD:
                            log(f'!! 判定假活：进程在但服务连续 {health_fails} 次不可达，杀整棵进程树重启')
                            if not kill_tree(proc):
                                restart_failure = 'restart_failed'
                                write_state(status=restart_failure, pid=proc.pid,
                                            restarts=len(crash_times), fast_crashes=len(crash_times),
                                            note='worker假活进程树未能确认退出；未启动替代进程',
                                            **_process_identity(proc))
                                break
                            if _wait_or_stop(stop_event, lambda: stopping, 2):
                                break
                            crash_times.append(time.time())
                            proc = spawn(args.app, args.host, args.port, launch_id=launch_id,
                                         no_scheduler=args.no_scheduler)
                            started = time.time()
                            health_fails = 0
                            last_health = 0.0
                            write_state(status='restart_after_zombie', pid=proc.pid,
                                        restarts=len(crash_times), note='worker假活杀树重启',
                                        **_process_identity(proc))
            if _wait_or_stop(stop_event, lambda: stopping, POLL_INTERVAL):
                break
    finally:
        log('Supervisor 正在清理其拥有的子进程 ...')
        cleanup_confirmed = kill_tree(proc) if proc is not None else True
        if child_started:
            final_status = restart_failure or ('stopped' if cleanup_confirmed else 'stop_failed')
            state_saved = write_state(
                app=args.app, host=args.host, port=args.port, pid=proc.pid,
                status=final_status,
                child_cleanup='confirmed' if cleanup_confirmed else 'failed',
                restarts=len(crash_times), fast_crashes=len(crash_times),
                **_process_identity(proc),
            )
            if not state_saved:
                log(f'无法保存监督器终态 status={final_status}')
        else:
            state_saved = True

        if cleanup_confirmed and state_saved:
            if _release_instance_lock(_lock_handle):
                log('Supervisor 已释放单实例锁')
            else:
                state_saved = False
        else:
            log('未释放单实例锁：子进程清理或终态持久化未获确认')

    if not cleanup_confirmed or not state_saved or restart_failure:
        raise SystemExit(1)
    log('Supervisor 已退出')


if __name__ == '__main__':
    main()
