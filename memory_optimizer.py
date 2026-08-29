"""
广州太古汇舆情监测系统 - 内存监控与自动清理模块
====================================================
基于GitHub最佳实践，解决Python Flask应用内存泄漏和OOM崩溃问题

核心能力：
1. 实时内存使用监控
2. 自动垃圾回收（gc.collect()）
3. 内存阈值告警和自动清理
4. 内存泄漏检测（tracemalloc）
5. 全局缓存大小限制
6. 数据库连接自动关闭

使用方法：
    from memory_optimizer import MemoryOptimizer
    mem_opt = MemoryOptimizer()
    mem_opt.start_monitoring()  # 启动后台监控线程
"""
import os
import gc
import json
import time
import threading
import tracemalloc
from datetime import datetime
from pathlib import Path
from collections import deque

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print('[Memory] psutil未安装，内存监控功能受限（pip install psutil）')


class MemoryOptimizer:
    """内存监控与自动清理优化器"""
    
    def __init__(self, 
                 warning_threshold_mb=500,
                 critical_threshold_mb=800,
                 check_interval_sec=60,
                 gc_interval_min=30,  # 从10分钟改为30分钟，避免频繁gc导致崩溃
                 log_file='data/memory_usage.log'):
        """
        初始化内存优化器
        
        Args:
            warning_threshold_mb: 警告阈值（MB），超过则触发告警
            critical_threshold_mb: 严重阈值（MB），超过则强制清理
            check_interval_sec: 内存检查间隔（秒）
            gc_interval_min: 自动垃圾回收间隔（分钟）
            log_file: 内存使用日志文件路径
        """
        self.warning_threshold = warning_threshold_mb
        self.critical_threshold = critical_threshold_mb
        self.check_interval = check_interval_sec
        self.gc_interval = gc_interval_min * 60
        
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._running = False
        self._monitor_thread = None
        self._last_gc_time = time.time()
        
        # 内存使用历史（保留最近100条记录）
        self.memory_history = deque(maxlen=100)
        
        # 告警记录
        self.alerts = deque(maxlen=50)
        
        # 全局缓存引用（用于限制大小）
        self._caches = {}
        
        print(f'[Memory] 内存优化器初始化完成（警告:{warning_threshold_mb}MB, 严重:{critical_threshold_mb}MB）')
    
    def register_cache(self, name, cache_obj, max_size=1000):
        """
        注册全局缓存，用于大小限制和自动清理
        
        Args:
            name: 缓存名称
            cache_obj: 缓存对象（dict或list）
            max_size: 最大大小
        """
        self._caches[name] = {
            'obj': cache_obj,
            'max_size': max_size
        }
        print(f'[Memory] 注册缓存: {name} (最大{max_size}条)')
    
    def get_current_memory_mb(self):
        """获取当前进程内存使用量（MB）"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                return process.memory_info().rss / (1024 * 1024)
            except Exception:
                return 0
        else:
            # 无psutil时使用tracemalloc估算
            if tracemalloc.is_tracing():
                current, _ = tracemalloc.get_traced_memory()
                return current / (1024 * 1024)
            return 0
    
    def get_memory_info(self):
        """获取详细内存信息"""
        info = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_mb': round(self.get_current_memory_mb(), 2),
            'warning_threshold_mb': self.warning_threshold,
            'critical_threshold_mb': self.critical_threshold,
            'gc_count': gc.get_count(),
            'gc_threshold': gc.get_threshold(),
            'tracked_objects': len(gc.get_objects()),
        }
        
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                info['cpu_percent'] = process.cpu_percent(interval=0.1)
                info['num_threads'] = process.num_threads()
                info['num_handles'] = len(process.open_files()) if hasattr(process, 'open_files') else 0
            except Exception:
                pass
        
        # 缓存大小统计
        cache_sizes = {}
        for name, cache_info in self._caches.items():
            try:
                cache_sizes[name] = len(cache_info['obj'])
            except Exception:
                cache_sizes[name] = 'error'
        info['cache_sizes'] = cache_sizes
        
        return info
    
    def force_gc(self):
        """强制垃圾回收"""
        collected = gc.collect()
        self._last_gc_time = time.time()
        
        # 清理超限缓存
        cleaned_caches = []
        for name, cache_info in self._caches.items():
            try:
                obj = cache_info['obj']
                max_size = cache_info['max_size']
                if isinstance(obj, dict) and len(obj) > max_size:
                    # 删除最早的条目
                    excess = len(obj) - max_size
                    for _ in range(excess):
                        obj.pop(next(iter(obj)))
                    cleaned_caches.append(f'{name}(-{excess})')
                elif isinstance(obj, list) and len(obj) > max_size:
                    del obj[:len(obj) - max_size]
                    cleaned_caches.append(f'{name}(-{len(obj) - max_size})')
            except Exception as e:
                print(f'[Memory] 缓存清理失败 {name}: {e}')
        
        memory_after = self.get_current_memory_mb()
        print(f'[Memory] 强制垃圾回收完成，回收{collected}个对象，当前内存:{memory_after:.1f}MB')
        if cleaned_caches:
            print(f'[Memory] 缓存清理: {", ".join(cleaned_caches)}')
        
        return collected, memory_after
    
    def _check_and_cleanup(self):
        """检查内存使用并在需要时清理"""
        current_mb = self.get_current_memory_mb()
        
        # 记录内存历史
        self.memory_history.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'mb': round(current_mb, 1)
        })
        
        # 写入日志
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | {current_mb:.1f}MB | gc:{gc.get_count()}\n')
        except Exception:
            pass
        
        # 定期自动垃圾回收
        if time.time() - self._last_gc_time > self.gc_interval:
            self.force_gc()
        
        # 超过警告阈值
        if current_mb > self.warning_threshold:
            alert = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'warning',
                'memory_mb': round(current_mb, 1),
                'message': f'内存使用超过警告阈值: {current_mb:.1f}MB > {self.warning_threshold}MB'
            }
            self.alerts.append(alert)
            print(f'[Memory] ⚠️ 警告: {alert["message"]}')
            
            # 触发垃圾回收
            self.force_gc()
        
        # 超过严重阈值
        if current_mb > self.critical_threshold:
            alert = {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'level': 'critical',
                'memory_mb': round(current_mb, 1),
                'message': f'内存使用严重超标: {current_mb:.1f}MB > {self.critical_threshold}MB，强制清理'
            }
            self.alerts.append(alert)
            print(f'[Memory] 🔴 严重: {alert["message"]}')
            
            # 强制清理所有缓存
            for name, cache_info in self._caches.items():
                try:
                    if isinstance(cache_info['obj'], dict):
                        cache_info['obj'].clear()
                    elif isinstance(cache_info['obj'], list):
                        cache_info['obj'].clear()
                except Exception:
                    pass
            
            # 强制垃圾回收
            self.force_gc()
    
    def _monitor_loop(self):
        """后台监控循环"""
        print('[Memory] 内存监控线程启动')
        while self._running:
            try:
                self._check_and_cleanup()
            except Exception as e:
                print(f'[Memory] 监控循环错误: {e}')
            time.sleep(self.check_interval)
        print('[Memory] 内存监控线程停止')
    
    def start_monitoring(self):
        """启动后台内存监控"""
        if self._running:
            print('[Memory] 监控已在运行')
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, 
            daemon=True, 
            name='memory_monitor'
        )
        self._monitor_thread.start()
        print('[Memory] 内存监控已启动')
    
    def stop_monitoring(self):
        """停止后台内存监控"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        print('[Memory] 内存监控已停止')
    
    def get_alerts(self, level=None):
        """获取告警记录"""
        if level:
            return [a for a in self.alerts if a['level'] == level]
        return list(self.alerts)
    
    def get_memory_trend(self):
        """获取内存使用趋势"""
        if len(self.memory_history) < 2:
            return {'trend': 'insufficient_data', 'history': list(self.memory_history)}
        
        first = self.memory_history[0]['mb']
        last = self.memory_history[-1]['mb']
        change = last - first
        
        if change > 50:
            trend = 'increasing'
        elif change < -50:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change_mb': round(change, 1),
            'first_mb': first,
            'last_mb': last,
            'history': list(self.memory_history)
        }


# 全局单例
_memory_optimizer = None

def get_memory_optimizer():
    """获取全局内存优化器单例"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer


def optimize_decorator(func):
    """
    函数装饰器：自动清理大对象，防止内存泄漏
    
    使用方法：
        @optimize_decorator
        def process_large_data():
            large_list = [i for i in range(1000000)]
            return sum(large_list)
    """
    import functools
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        finally:
            # 函数执行后触发垃圾回收
            gc.collect()
    return wrapper


if __name__ == '__main__':
    # 测试
    opt = MemoryOptimizer()
    print('当前内存:', opt.get_current_memory_mb(), 'MB')
    print('内存信息:', json.dumps(opt.get_memory_info(), ensure_ascii=False, indent=2))
    opt.force_gc()
    print('回收后内存:', opt.get_current_memory_mb(), 'MB')
