"""
广州太古汇舆情监测系统 - 进程级稳定性监控层
================================================
功能：
1. 全局异常捕获（sys.excepthook, threading.excepthook）
2. 线程异常捕获
3. 进程级watchdog（心跳检测）
4. APScheduler任务监控
5. Playwright生命周期管理
6. 浏览器自动回收
7. 数据库连接保护
8. 任务超时机制
9. 任务防重入
10. 内存/进程监控
11. 结构化crash log
12. 启动/停止原因记录
13. 每分钟heartbeat
14. 异常自动重启关键任务
15. 系统级崩溃前最后状态记录

设计原则：
- 不改业务逻辑，只增加监控和保护
- 不动主体词过滤口径（SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit()）
- 不动主体SQL过滤、事件聚合过滤和日报中的主体过滤

[LEGACY NOTICE - ZBC Phase 2 Runtime Guardian 统一收敛]
本模块已由 runtime_guardian.py 接管为统一生命周期守护者（Worker->Lease->Heartbeat->
Checkpoint->Reaper->Retry->DLQ->Resume）。保留全部原有类与函数行为（向后兼容），
新代码请直接使用 runtime_guardian.RuntimeGuardian。不删除本文件，保持 import 兼容。
收敛工单：ZBC-PHASE2-RUNTIME-GUARDIAN-001
"""
import os
import logging
import sys
import json
import time
import threading
import traceback
import signal
import atexit
from pathlib import Path
from datetime import datetime
from collections import deque


logger = logging.getLogger(__name__)

class StabilityMonitor:
    """进程级稳定性监控器"""
    
    def __init__(self, log_dir='data/stability', *, service_port=None):
        self.configure_service_port(service_port)
        self.base_dir = Path(__file__).resolve().parent
        self.log_dir = self.base_dir / log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件
        self.heartbeat_log = self.log_dir / 'heartbeat.log'
        self.crash_log = self.log_dir / 'crash.log'
        self.event_log = self.log_dir / 'events.log'
        self.last_state_file = self.log_dir / 'last_state.json'
        
        # 状态
        self.start_time = time.time()
        self.last_heartbeat = time.time()
        self.is_running = True
        self.watchdog_interval = 30  # 30秒检测一次
        self.heartbeat_interval = 60  # 每分钟心跳
        
        # 模块状态
        self.module_status = {
            'flask': {'status': 'unknown', 'last_check': 0, 'errors': 0},
            'scheduler': {'status': 'unknown', 'last_check': 0, 'errors': 0, 'tasks_run': 0},
            'crawler': {'status': 'unknown', 'last_check': 0, 'errors': 0, 'tasks_run': 0},
            'playwright': {'status': 'unknown', 'last_check': 0, 'browsers_open': 0, 'pages_open': 0, 'errors': 0},
            'database': {'status': 'unknown', 'last_check': 0, 'connections': 0, 'errors': 0, 'locks': 0},
            'memory': {'status': 'unknown', 'last_check': 0, 'current_mb': 0, 'peak_mb': 0},
            'threads': {'status': 'unknown', 'active_count': 0, 'daemon_count': 0},
            'child_processes': {'status': 'unknown', 'count': 0, 'chromium_count': 0}
        }
        
        # 任务防重入
        self._task_locks = {}
        self._task_timeouts = {}
        
        # 事件历史
        self.events = deque(maxlen=500)
        
        # 监控线程
        self._watchdog_thread = None
        self._heartbeat_thread = None
        
        print(f'[Stability] 稳定性监控器初始化完成，日志目录: {self.log_dir}')
    
    def install_global_hooks(self):
        """安装全局异常钩子"""
        # 全局未捕获异常
        def global_excepthook(exc_type, exc_value, exc_traceback):
            self._log_crash('global_exception', exc_type, exc_value, exc_traceback)
            # 调用默认处理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
        
        sys.excepthook = global_excepthook
        
        # 线程未捕获异常
        def thread_excepthook(args):
            self._log_crash('thread_exception', args.exc_type, args.exc_value, args.exc_traceback, 
                           thread_name=args.thread.name if args.thread else 'unknown')
        
        threading.excepthook = thread_excepthook
        
        # 退出钩子
        atexit.register(self._on_exit)
        
        # 信号处理（Windows下有限支持）
        try:
            signal.signal(signal.SIGTERM, self._on_signal)
            signal.signal(signal.SIGINT, self._on_signal)
        except Exception:
            pass
        
        print('[Stability] 全局异常钩子已安装')
    
    def start_monitoring(self):
        """启动监控"""
        self.install_global_hooks()
        
        # 启动watchdog线程
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True, name='stability_watchdog')
        self._watchdog_thread.start()
        
        # 启动heartbeat线程
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name='stability_heartbeat')
        self._heartbeat_thread.start()
        
        # 记录启动事件
        self.log_event('system_start', {
            'pid': os.getpid(),
            'python_version': sys.version,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
        print('[Stability] 稳定性监控已启动（watchdog+heartbeat）')
    
    def _watchdog_loop(self):
        """watchdog循环：每30秒检测各模块状态"""
        while self.is_running:
            try:
                self._check_all_modules()
                self._save_last_state()
            except Exception as e:
                print(f'[Stability] watchdog异常: {e}')
            time.sleep(self.watchdog_interval)
    
    def _heartbeat_loop(self):
        """heartbeat循环：每分钟写心跳"""
        while self.is_running:
            # 先更新内存心跳（进程存活的本质信号，不依赖写文件成功）
            self.last_heartbeat = time.time()
            try:
                self._write_heartbeat()
            except Exception as e:
                print(f'[Stability] heartbeat写日志异常(不影响内存心跳): {e}')
            time.sleep(self.heartbeat_interval)
    
    def _check_all_modules(self):
        """检测所有模块状态"""
        now = time.time()
        
        # 内存检测
        try:
            import psutil
            process = psutil.Process(os.getpid())
            mem_mb = process.memory_info().rss / (1024 * 1024)
            self.module_status['memory']['current_mb'] = round(mem_mb, 2)
            self.module_status['memory']['peak_mb'] = max(self.module_status['memory']['peak_mb'], mem_mb)
            self.module_status['memory']['status'] = 'ok' if mem_mb < 500 else 'warning' if mem_mb < 800 else 'critical'
            self.module_status['memory']['last_check'] = now
            
            # 子进程检测
            children = process.children(recursive=True)
            self.module_status['child_processes']['count'] = len(children)
            chromium_count = sum(1 for c in children if 'chrome' in c.name().lower() or 'chromium' in c.name().lower() or 'msedge' in c.name().lower())
            self.module_status['child_processes']['chromium_count'] = chromium_count
            self.module_status['child_processes']['status'] = 'ok'
        except ImportError:
            self.module_status['memory']['status'] = 'unknown'
        except Exception as e:
            self.module_status['memory']['errors'] += 1
            self.module_status['memory']['status'] = 'error'
        
        # 线程检测
        try:
            active_threads = threading.enumerate()
            self.module_status['threads']['active_count'] = len(active_threads)
            self.module_status['threads']['daemon_count'] = sum(1 for t in active_threads if t.daemon)
            self.module_status['threads']['status'] = 'ok'
            self.module_status['threads']['last_check'] = now
        except Exception as e:
            self.module_status['threads']['status'] = 'error'
        
        # Listener availability is not a business-task acceptance result.
        self._check_http_listener(now)

        # 调度器检测：存在存活的 scheduler 线程即视为运行
        try:
            sched_alive = any(
                (getattr(t, 'name', '') or '').lower() in ('scheduler', 'weekly_scheduler') and t.is_alive()
                for t in threading.enumerate())
            self.module_status['scheduler']['status'] = 'ok' if sched_alive else 'error'
            self.module_status['scheduler']['last_check'] = now
        except Exception:
            self.module_status['scheduler']['status'] = 'unknown'

        # 采集器检测：运行中→running，熔断→blocked，否则就绪 ok
        try:
            import xhs_cookie_bridge as _xhs
            running = any((t.get('status') in ('running', 'pending'))
                          for t in (getattr(_xhs, '_tasks', {}) or {}).values())
            circ = _xhs.get_circuit_state()
            if running:
                self.module_status['crawler']['status'] = 'running'
            elif circ.get('open'):
                self.module_status['crawler']['status'] = 'blocked'
            else:
                self.module_status['crawler']['status'] = 'ok'
            self.module_status['crawler']['last_check'] = now
        except Exception:
            self.module_status['crawler']['status'] = 'unknown'
    
    def configure_service_port(self, port=None):
        """Bind the monitor to the actual launcher-selected Core port."""
        if port is None:
            port = os.environ.get('TAIKOO_PORT', '8200')
        if isinstance(port, str) and port.isascii() and port.isdecimal():
            port = int(port)
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('STABILITY_SERVICE_PORT_INVALID')
        self.service_port = port

    def _check_http_listener(self, now=None):
        import socket
        observed = self.module_status['flask']
        observed.update(last_check=time.time() if now is None else now,
                        port=self.service_port, observation_kind='TCP_LISTENER_ONLY')
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', self.service_port))
            observed['status'] = 'ok' if result == 0 else 'error'
        except OSError:
            observed['status'] = 'unknown'

    def _write_heartbeat(self):
        """写心跳日志"""
        try:
            uptime_seconds = int(time.time() - self.start_time)
            uptime_str = f'{uptime_seconds//3600}h{(uptime_seconds%3600)//60}m{uptime_seconds%60}s'
            
            heartbeat = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pid': os.getpid(),
                'uptime': uptime_str,
                'uptime_seconds': uptime_seconds,
                'memory_mb': self.module_status['memory']['current_mb'],
                'threads': self.module_status['threads']['active_count'],
                'child_processes': self.module_status['child_processes']['count'],
                'chromium_processes': self.module_status['child_processes']['chromium_count'],
                'flask_status': self.module_status['flask']['status'],
                'scheduler_status': self.module_status['scheduler']['status'],
                'crawler_status': self.module_status['crawler']['status'],
                'gc_count': self._get_gc_count()
            }
            
            with open(self.heartbeat_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(heartbeat, ensure_ascii=False) + '\n')
            
            # 每10次心跳打印一次
            if uptime_seconds % 600 == 0:
                print(f'[Stability] 心跳: 运行{uptime_str}, 内存{heartbeat["memory_mb"]}MB, 线程{heartbeat["threads"]}, 子进程{heartbeat["child_processes"]}')
                
        except Exception as e:
            print(f'[Stability] 写心跳失败: {e}')
    
    def _get_gc_count(self):
        """获取GC计数"""
        try:
            import gc
            return list(gc.get_count())
        except Exception:
            return [0, 0, 0]
    
    def _log_crash(self, crash_type, exc_type, exc_value, exc_traceback, thread_name=None):
        """记录崩溃日志"""
        try:
            crash_info = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'crash_type': crash_type,
                'thread_name': thread_name,
                'exception_type': str(exc_type),
                'exception_value': str(exc_value),
                'traceback': ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
                'uptime_seconds': int(time.time() - self.start_time),
                'module_status_at_crash': self._get_serializable_status()
            }
            
            with open(self.crash_log, 'a', encoding='utf-8') as f:
                f.write('=' * 80 + '\n')
                f.write(json.dumps(crash_info, ensure_ascii=False, indent=2) + '\n')
                f.write('=' * 80 + '\n\n')
            
            print(f'[Stability] ⚠️ 捕获到{crash_type}: {exc_type.__name__ if hasattr(exc_type, "__name__") else exc_type}: {exc_value}')
            print(f'[Stability] 崩溃详情已记录到: {self.crash_log}')
            
            # 保存最后状态
            self._save_last_state()
            
        except Exception as e:
            print(f'[Stability] 记录崩溃日志失败: {e}')
    
    def _get_serializable_status(self):
        """获取可序列化的状态"""
        try:
            return {k: {kk: vv for kk, vv in v.items() if kk != 'last_check' or isinstance(vv, (int, float, str, bool, list, dict))} 
                    for k, v in self.module_status.items()}
        except Exception:
            return {}
    
    def _save_last_state(self):
        """保存最后状态（崩溃前可恢复）"""
        try:
            state = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'pid': os.getpid(),
                'uptime_seconds': int(time.time() - self.start_time),
                'module_status': self._get_serializable_status(),
                'events_count': len(self.events),
                'recent_events': list(self.events)[-10:]
            }
            
            with open(self.last_state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[Stability] 保存最后状态失败: {e}')
    
    def _on_exit(self):
        """退出钩子"""
        self.is_running = False
        self.log_event('system_exit', {
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uptime_seconds': int(time.time() - self.start_time),
            'reason': 'atexit'
        })
        self._save_last_state()
        print(f'[Stability] 系统退出，运行时长: {int(time.time() - self.start_time)}秒')
    
    def _on_signal(self, signum, frame):
        """信号处理"""
        self.log_event('signal_received', {
            'signal': signum,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        print(f'[Stability] 收到信号: {signum}')
    
    def log_event(self, event_type, data=None):
        """记录事件"""
        event = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'event_type': event_type,
            'data': data or {}
        }
        self.events.append(event)
        
        try:
            with open(self.event_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception:
            pass
    
    def update_module_status(self, module, status, **kwargs):
        """更新模块状态"""
        if module in self.module_status:
            self.module_status[module]['status'] = status
            self.module_status[module]['last_check'] = time.time()
            for k, v in kwargs.items():
                self.module_status[module][k] = v
    
    def run_with_timeout(self, func, timeout, *args, **kwargs):
        """带超时执行任务"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            raise TimeoutError(f'任务执行超时（{timeout}秒）')
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def acquire_task_lock(self, task_name, timeout=60):
        """获取任务锁（防重入）"""
        if task_name not in self._task_locks:
            self._task_locks[task_name] = threading.Lock()
        
        lock = self._task_locks[task_name]
        acquired = lock.acquire(timeout=timeout)
        
        if acquired:
            self._task_timeouts[task_name] = time.time()
            return True
        else:
            print(f'[Stability] 任务"{task_name}"正在执行中，跳过（防重入）')
            return False
    
    def release_task_lock(self, task_name):
        """释放任务锁"""
        if task_name in self._task_locks:
            self._task_locks[task_name].release()
            if task_name in self._task_timeouts:
                del self._task_timeouts[task_name]
    
    def get_status_report(self):
        """获取状态报告"""
        return {
            'uptime_seconds': int(time.time() - self.start_time),
            'start_time': datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'module_status': self._get_serializable_status(),
            'events_count': len(self.events),
            'last_heartbeat': datetime.fromtimestamp(self.last_heartbeat).strftime('%Y-%m-%d %H:%M:%S') if self.last_heartbeat else None
        }


# 全局单例
_stability_monitor = None

def get_stability_monitor(*, service_port=None):
    """获取全局稳定性监控器单例"""
    global _stability_monitor
    if _stability_monitor is None:
        _stability_monitor = StabilityMonitor(service_port=service_port)
    elif service_port is not None:
        _stability_monitor.configure_service_port(service_port)
    return _stability_monitor


if __name__ == '__main__':
    # 测试
    monitor = StabilityMonitor()
    monitor.start_monitoring()
    
    print('稳定性监控器测试运行中...')
    print('按Ctrl+C退出')
    
    try:
        while True:
            time.sleep(10)
            status = monitor.get_status_report()
            print(f'运行{status["uptime_seconds"]}秒, Flask:{status["module_status"]["flask"]["status"]}, 内存:{status["module_status"]["memory"]["current_mb"]}MB')
    except KeyboardInterrupt:
        print('退出测试')
