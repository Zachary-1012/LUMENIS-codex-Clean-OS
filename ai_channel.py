# -*- coding: utf-8 -*-
"""
ai_channel.py — 云端 AI 通道多层稳固层（零第三方依赖，标准库实现）

分层：配置自加载 → UTF-8 编码 → 失败分类 → 有限重试(指数退避有上限)
      → 熔断状态机(CLOSED/OPEN/HALF_OPEN) → 后台心跳保活 → 健康快照可观测

设计红线：
- 禁止无限重试：max_retries 硬上限 _HARD_MAX_ATTEMPTS；401/400 等不可恢复错误不重试。
- 熔断 OPEN 期间快速降级（由上层回退本地规则），不阻塞业务、不打爆云端。
- 本层只负责"把请求可靠地送到并把响应可靠地取回"，不做脱敏/预算/业务判断（那些在 intelligence/ai_resource_packs）。
- 全部状态判断为可单测纯逻辑；真实网络只在 post_with_retry / 心跳内发生。
"""
import os
import json
import time
import errno
import socket
import threading
import urllib.request, urllib.error

# Runtime Guardian 统一熔断器（收敛重复实现，ZBC-PHASE2-RUNTIME-GUARDIAN）
from runtime_guardian import CircuitBreaker as _BaseCircuitBreaker
from runtime_guardian import CircuitState as _RGCircuitState

_HERE = os.path.dirname(os.path.abspath(__file__))

# 硬上限：即使配置写错也绝不超过该尝试次数（含首次），杜绝无限重试
_HARD_MAX_ATTEMPTS = 5
# 退避封顶（秒），避免长时间阻塞业务调用
_MAX_BACKOFF = 4.0

# ZBC Phase 7: module status markers
MODULE_STATUS = 'ACTIVE'
AI_ROLE = 'TRANSPORT_LAYER'  # retry, circuit breaker, heartbeat, multi-provider fallback - not business judgment


# ============================================================
# 1) 配置自加载：不依赖 app.py 的 import 副作用，任何上下文都能读到 .env
# ============================================================
_ENV_LOADED = False
_ENV_LOCK = threading.Lock()


def ensure_env_loaded(path=None):
    """幂等加载同目录 .env 到 os.environ；只填充不存在的键，不覆盖进程已有环境。"""
    global _ENV_LOADED
    with _ENV_LOCK:
        if _ENV_LOADED:
            return True
        env_path = path or os.path.join(_HERE, '.env')
        try:
            if os.path.exists(env_path):
                with open(env_path, 'rb') as f:
                    raw = f.read().decode('utf-8', errors='ignore')
                for line in raw.splitlines():
                    s = line.strip()
                    if not s or s.startswith('#') or '=' not in s:
                        continue
                    k, v = s.split('=', 1)
                    k, v = k.strip(), v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass  # .env 读取失败不应阻断启动（可能由外部注入环境变量）
        _ENV_LOADED = True
        return True


def _env(name, default=''):
    # 只读环境变量，不在 import 时触发 .env 自动加载（避免全局副作用污染测试/进程隔离）；
    # 独立上下文需要 .env 时显式调用 ensure_env_loaded()。
    return os.environ.get(name, default)


# ============================================================
# 2) 失败分类（纯函数）：决定是否值得重试
# ============================================================
# 可重试类别：网络瞬时 / 限流 / 服务端；不可重试：鉴权 / 参数
RETRYABLE_KINDS = {'network', 'rate_limit', 'server', 'parse'}
FATAL_KINDS = {'auth', 'bad_request', 'unknown'}


def classify_error(exc=None, status=None):
    """返回 (kind, retryable)。优先按 HTTP status，否则按异常类型。"""
    if status is not None:
        if status in (401, 403):
            return 'auth', False
        if status == 400:
            return 'bad_request', False
        if status == 429:
            return 'rate_limit', True
        if 500 <= status < 600:
            return 'server', True
        if 200 <= status < 300:
            return 'ok', False
        return 'unknown', False
    if isinstance(exc, (urllib.error.URLError, socket.timeout, TimeoutError,
                        ConnectionError, OSError)):
        # OSError 里区分"连接被拒/重置/超时"等瞬时网络问题
        if isinstance(exc, OSError) and getattr(exc, 'errno', None) in (
                errno.ECONNREFUSED, errno.ECONNRESET, errno.ETIMEDOUT, errno.EHOSTUNREACH):
            return 'network', True
        if isinstance(exc, urllib.error.HTTPError):
            return classify_error(status=exc.code)
        return 'network', True
    return 'unknown', False


# ============================================================
# 3) 熔断状态机（线程安全，可注入时钟便于单测）
# ============================================================
class CircuitBreaker(_BaseCircuitBreaker):
    """AI 通道熔断器：继承 runtime_guardian.CircuitBreaker 统一状态机，
    额外追踪延迟/错误类型等传输层指标，保持原 ai_channel 接口不变。

    收敛说明（ZBC-PHASE2-RUNTIME-GUARDIAN）：核心 CLOSED->OPEN->HALF_OPEN 状态机
    委托给 runtime_guardian.CircuitBreaker，本类只加 AI 通道特有字段。
    """
    CLOSED, OPEN, HALF_OPEN = 'CLOSED', 'OPEN', 'HALF_OPEN'
    _STATE_MAP = {
        _RGCircuitState.CLOSED: CLOSED,
        _RGCircuitState.OPEN: OPEN,
        _RGCircuitState.HALF_OPEN: HALF_OPEN,
    }

    def __init__(self, fail_threshold=3, cooldown_sec=30.0, now_func=time.time):
        super().__init__(
            name='ai_channel',
            failure_threshold=max(1, int(fail_threshold)),
            reset_timeout=float(cooldown_sec),
            now_func=now_func,
        )
        self.fail_threshold = self.failure_threshold
        self.cooldown_sec = self.reset_timeout
        # AI 通道额外追踪字段
        self.consecutive_failures = 0
        self.opened_at = None
        self.last_success_at = None
        self.last_failure_at = None
        self.last_error_kind = None
        self.success_count = 0
        self.failure_count = 0
        self.last_latency_ms = None

    @property
    def state(self):
        """返回字符串状态（兼容原 ai_channel 接口）"""
        return self._STATE_MAP[super().state]

    def record_success(self, latency_ms=None):
        super().record_success()
        self.consecutive_failures = 0
        self.opened_at = None
        self.last_success_at = self._now()
        self.success_count += 1
        if latency_ms is not None:
            self.last_latency_ms = int(latency_ms)

    def record_failure(self, kind='unknown'):
        super().record_failure()
        self.consecutive_failures = self._failure_count
        self.failure_count += 1
        self.last_failure_at = self._now()
        self.last_error_kind = kind
        if super().state == _RGCircuitState.OPEN:
            self.opened_at = self._now()

    def snapshot(self):
        return {
            'state': self.state,
            'consecutive_failures': self.consecutive_failures,
            'fail_threshold': self.fail_threshold,
            'cooldown_sec': self.cooldown_sec,
            'opened_at': self.opened_at,
            'last_success_at': self.last_success_at,
            'last_failure_at': self.last_failure_at,
            'last_error_kind': self.last_error_kind,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'last_latency_ms': self.last_latency_ms,
        }


# 进程级单例（云端通道共用一个熔断）
_cfg_fail_threshold = int(_env('AI_CB_FAIL_THRESHOLD', '3') or '3')
_cfg_cooldown = float(_env('AI_CB_COOLDOWN_SEC', '30') or '30')
breaker = CircuitBreaker(fail_threshold=_cfg_fail_threshold, cooldown_sec=_cfg_cooldown)


# ============================================================
# 4) 有限重试 HTTP POST（UTF-8 编码/解码，指数退避有上限）
# ============================================================
def _backoff_delay(attempt_idx, base):
    return min(_MAX_BACKOFF, base * (2 ** attempt_idx))


def post_with_retry(url, payload_bytes, headers, timeout=90,
                    max_attempts=3, backoff_base=0.5, opener=None, sleep=None,
                    on_success=None, on_failure=None):
    """
    返回 (resp_bytes, attempts)。
    - 仅对 classify 判定可重试的错误重试；401/400 立即终止。
    - 尝试次数硬上限 _HARD_MAX_ATTEMPTS；退避封顶 _MAX_BACKOFF。
    - on_success(latency_ms)/on_failure(kind) 用于接熔断/健康，默认接全局 breaker。
    抛出最后一次异常（不可恢复或重试用尽），由上层决定降级。
    """
    sleep = sleep or time.sleep
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    attempts = max(1, min(int(max_attempts), _HARD_MAX_ATTEMPTS))
    last_exc = None
    for i in range(attempts):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload_bytes, headers=headers, method='POST')
            with opener.open(req, timeout=timeout) as resp:
                body = resp.read().decode('utf-8', 'replace')
            lat = int((time.time() - t0) * 1000)
            (on_success or breaker.record_success)(lat)
            return body.encode('utf-8'), i + 1
        except Exception as exc:
            kind, retryable = classify_error(exc)
            (on_failure or breaker.record_failure)(kind)
            last_exc = exc
            if not retryable or i == attempts - 1:
                break
            sleep(_backoff_delay(i, backoff_base))
    raise last_exc if last_exc else RuntimeError('post_with_retry failed without exception')


# ============================================================
# 5) 健康快照
# ============================================================
def channel_health(provider='', model=''):
    snap = breaker.snapshot()
    paused = False
    pause_reason = ''
    try:
        import ai_resource_packs as rp
        p = rp.is_paused()
        paused = bool(p.get('paused'))
        pause_reason = p.get('reason', '')
    except Exception:
        pass
    snap.update({
        'provider': provider, 'model': model, 'paused': paused, 'pause_reason': pause_reason,
        'available': snap['state'] != breaker.OPEN and not paused,
    })
    return snap


# ============================================================
# 6) 后台心跳保活：周期极小探活，实现"随时可用、断了自动发现并恢复"
#    daemon 线程幂等只起一个；不占业务预算（track=False 由调用方保证）。
# ============================================================
_MONITOR = {'thread': None, 'stop': False, 'interval': None}
_MONITOR_LOCK = threading.Lock()


def start_health_monitor(ping_func, interval_sec=300):
    """启动唯一心跳线程。ping_func() 无参，成功返回真、失败返回假/抛异常。"""
    interval_sec = max(30, int(interval_sec))  # 不允许比 30s 更频繁，避免无谓消耗
    with _MONITOR_LOCK:
        if _MONITOR['thread'] and _MONITOR['thread'].is_alive():
            return False  # 已在运行，幂等
        _MONITOR['stop'] = False
        _MONITOR['interval'] = interval_sec

        def _loop():
            # 启动后稍等再首次 ping，避开服务冷启动高峰
            time.sleep(min(15, interval_sec // 10 + 1))
            while not _MONITOR['stop']:
                try:
                    ok = bool(ping_func())
                    if ok:
                        breaker.record_success()
                    else:
                        breaker.record_failure('heartbeat')
                except Exception:
                    breaker.record_failure('heartbeat')
                # 分片睡眠，stop 时快速退出
                slept = 0
                while slept < interval_sec and not _MONITOR['stop']:
                    step = min(5, interval_sec - slept)
                    time.sleep(step)
                    slept += step
            return

        t = threading.Thread(target=_loop, daemon=True, name='ai-channel-health')
        _MONITOR['thread'] = t
        t.start()
        return True


def stop_health_monitor():
    with _MONITOR_LOCK:
        _MONITOR['stop'] = True
        return True


# ============================================================
# 7) 多 Provider 故障转移层（智谱主 + 豆包备 + 本地规则兜底）
#    每个 Provider 独立熔断；主通道失败/熔断时自动切备用；备用也失败才降 rule。
#    设计目标：24h 连接不断——主通道抖动时业务无感切换，不打爆任一通道。
# ============================================================
class ProviderBreaker:
    """单个 Provider 的独立熔断 + 健康快照（线程安全）。"""

    def __init__(self, name, fail_threshold=3, cooldown_sec=20.0):
        self.name = name
        self.breaker = CircuitBreaker(fail_threshold=fail_threshold, cooldown_sec=cooldown_sec)

    def allow(self):
        return self.breaker.allow_request()

    def record_success(self, latency_ms=None):
        self.breaker.record_success(latency_ms)

    def record_failure(self, kind='unknown'):
        self.breaker.record_failure(kind)

    def snapshot(self):
        s = self.breaker.snapshot()
        s['provider'] = self.name
        return s

    @property
    def state(self):
        return self.breaker.state


# 进程级 Provider 独立熔断（智谱主、豆包备；其他 provider 按需注册）
_PROVIDER_BREAKERS = {}
_PROVIDER_LOCK = threading.Lock()


def get_provider_breaker(name, fail_threshold=3, cooldown_sec=20.0):
    """获取或创建指定 Provider 的独立熔断器。"""
    with _PROVIDER_LOCK:
        if name not in _PROVIDER_BREAKERS:
            _PROVIDER_BREAKERS[name] = ProviderBreaker(name, fail_threshold, cooldown_sec)
        return _PROVIDER_BREAKERS[name]


def all_provider_snapshots():
    """所有已注册 Provider 的健康快照（可观测）。"""
    with _PROVIDER_LOCK:
        return {name: pb.snapshot() for name, pb in _PROVIDER_BREAKERS.items()}


# Provider 优先级配置（环境变量可覆盖）
# 主通道智谱（最大算力），备用豆包（最小输出兜底），最后本地规则
def provider_chain():
    """返回 Provider 优先级列表 [主, 备...]。环境变量 AI_PROVIDER_CHAIN 可覆盖（逗号分隔）。"""
    raw = _env('AI_PROVIDER_CHAIN', '').strip()
    if raw:
        return [p.strip() for p in raw.split(',') if p.strip()]
    return ['zhipu', 'ark']  # ark = 豆包（火山引擎）


def route_with_fallback(call_fn, providers=None, on_result=None):
    """
    多 Provider 故障转移执行器。
    call_fn(provider_name) -> (result, provider_used) 或抛异常。
    按 provider_chain() 顺序尝试；每个 Provider 独立熔断；全部失败返回 (None, 'rule')。
    on_result(provider, result, ok) 用于审计/额度记录。
    """
    chain = providers or provider_chain()
    last_exc = None
    for prov in chain:
        pb = get_provider_breaker(prov)
        if not pb.allow():
            continue  # 该 Provider 熔断中，跳过
        try:
            result, used = call_fn(prov)
            pb.record_success()
            if on_result:
                try:
                    on_result(prov, result, True)
                except Exception:
                    pass
            return result, used
        except Exception as exc:
            kind, retryable = classify_error(exc)
            pb.record_failure(kind)
            last_exc = exc
            if on_result:
                try:
                    on_result(prov, None, False)
                except Exception:
                    pass
            # 不可重试错误（auth/bad_request）不切下一个（配置问题，切了也没用）
            if not retryable and kind in ('auth', 'bad_request'):
                break
            continue
    # 全部 Provider 失败/熔断 → 本地规则兜底
    return None, 'rule'


# ============================================================
# 8) 24h 保活心跳增强：默认 60s 间隔（原 300s 太长），支持多 Provider 分别探活
# ============================================================
def start_24h_heartbeat(ping_funcs, interval_sec=60):
    """
    启动 24h 保活心跳（默认 60s，最小 30s）。
    ping_funcs: dict {provider_name: ping_fn}，每个 Provider 独立探活、独立熔断。
    幂等：已在运行则不重复启动。
    """
    interval_sec = max(30, int(interval_sec))
    with _MONITOR_LOCK:
        if _MONITOR['thread'] and _MONITOR['thread'].is_alive():
            return False
        _MONITOR['stop'] = False
        _MONITOR['interval'] = interval_sec

        def _loop():
            time.sleep(min(10, interval_sec // 6 + 1))
            while not _MONITOR['stop']:
                for prov, ping_fn in ping_funcs.items():
                    try:
                        ok = bool(ping_fn())
                        pb = get_provider_breaker(prov)
                        if ok:
                            pb.record_success()
                        else:
                            pb.record_failure('heartbeat')
                    except Exception:
                        try:
                            get_provider_breaker(prov).record_failure('heartbeat')
                        except Exception:
                            pass
                slept = 0
                while slept < interval_sec and not _MONITOR['stop']:
                    step = min(5, interval_sec - slept)
                    time.sleep(step)
                    slept += step

        t = threading.Thread(target=_loop, daemon=True, name='ai-channel-24h-heartbeat')
        _MONITOR['thread'] = t
        t.start()
        return True
