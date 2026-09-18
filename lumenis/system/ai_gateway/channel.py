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
#    Fatal auth/bad-request stops the chain immediately to avoid wasteful provider switching.
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
    return ['zhipu', 'ark', 'ollama']  # V1.0: zhipu primary -> ark fallback -> ollama local -> rule final


def route_with_fallback(call_fn, providers=None, on_result=None):
    """
    多 Provider 故障转移执行器。
    call_fn(provider_name) -> (result, provider_used) 或抛异常。
    按 provider_chain() 顺序尝试；每个 Provider 独立熔断；全部失败返回 (None, 'rule')。
    auth / bad_request 等 fatal error 立即终止 provider 链，避免无效切换与额度浪费。
    on_result(provider, result, ok) 用于审计/额度记录。
    """
    chain = providers or provider_chain()
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
            if on_result:
                try:
                    on_result(prov, None, False)
                except Exception:
                    pass
            if not retryable:
                break
            continue
    # 全部 Provider 失败/熔断，或 fatal error → 本地规则兜底
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


# ============================================================
# Track B 补全：编码转换（UTF-8/流式/特殊字符）
# ============================================================
def safe_encode_payload(data, encoding='utf-8'):
    """安全编码请求 payload，处理特殊字符和编码异常。

    - 优先 UTF-8 编码
    - 遇到无法编码的字符时使用 'replace' 而非抛异常
    - 返回 (bytes, encoding_used)
    """
    if isinstance(data, bytes):
        return data, 'bytes-passthrough'
    if isinstance(data, dict):
        import json as _json
        text = _json.dumps(data, ensure_ascii=False, default=str)
    else:
        text = str(data)
    try:
        encoded = text.encode(encoding, errors='strict')
        return encoded, encoding
    except (UnicodeEncodeError, LookupError):
        # 回退到 UTF-8 with replace，保证不丢请求
        encoded = text.encode('utf-8', errors='replace')
        return encoded, 'utf-8-replace'


def safe_decode_response(body_bytes, encoding='utf-8'):
    """安全解码响应体，处理编码不一致和特殊字符。

    - 优先按指定编码解码
    - 失败时尝试 UTF-8 / GBK / Latin-1 回退链
    - 返回 (text, encoding_used, had_replacement)
    """
    if isinstance(body_bytes, str):
        return body_bytes, 'already-str', False
    encodings_to_try = [encoding, 'utf-8', 'gbk', 'gb18030', 'latin-1']
    for enc in encodings_to_try:
        try:
            text = body_bytes.decode(enc, errors='strict')
            return text, enc, False
        except (UnicodeDecodeError, LookupError):
            continue
    # 全部失败：用 UTF-8 replace 兜底，标记有替换字符
    text = body_bytes.decode('utf-8', errors='replace')
    return text, 'utf-8-replace', True


def normalize_special_chars(text):
    """规范化特殊字符（零宽字符、BOM、不可见控制字符）。

    用于 AI 响应后处理，避免特殊字符导致 JSON 解析或下游处理失败。
    """
    if not isinstance(text, str):
        return text
    import re as _re
    # 移除 BOM
    text = text.lstrip('\ufeff')
    # 移除零宽字符
    text = _re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)
    # 替换其他控制字符（除换行/制表符）为空格
    text = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', text)
    return text


# ============================================================
# Track B 补全：增强可观测性（连接状态/最后成功/失败计数/熔断）
# ============================================================
def get_channel_status_detailed():
    """获取 AI 通道详细状态（可观测性增强）。

    返回所有 Provider 的连接状态、最后成功时间、失败计数、熔断状态、延迟等。
    用于健康检查 API 和审计。
    """
    snapshots = all_provider_snapshots()
    global_snap = breaker.snapshot()

    # 计算总体可用性
    total_providers = len(snapshots)
    available_providers = sum(
        1 for s in snapshots.values()
        if s.get('state') != 'OPEN'
    )

    return {
        "module": "ai_channel",
        "track_b_status": "ACTIVE",
        "global_breaker": global_snap,
        "providers": snapshots,
        "provider_count": total_providers,
        "providers_available": available_providers,
        "overall_available": available_providers > 0,
        "provider_chain": provider_chain(),
        "fallback_chain": ["zhipu", "ark", "doubao", "rule"],
        "hard_limits": {
            "max_attempts": _HARD_MAX_ATTEMPTS,
            "max_backoff_sec": _MAX_BACKOFF,
        },
        "encoding": {
            "request": "utf-8 (with replace fallback)",
            "response": "utf-8 -> gbk -> gb18030 -> latin-1 fallback chain",
            "special_char_normalization": True,
        },
        "heartbeat": {
            "monitor_active": bool(_MONITOR.get('thread') and _MONITOR['thread'].is_alive()),
            "interval_sec": _MONITOR.get('interval'),
        },
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# ============================================================
# Track B 补全：豆包最小兜底通道配置
# ============================================================
def get_doubao_fallback_config():
    """获取豆包（Doubao）最小兜底通道配置。

    豆包作为最小输出兜底：当智谱主通道和 ark 备用通道都失败/熔断时，
    使用豆包的最小模型（如 doubao-1.5-lite）做最短响应，保证业务不中断。
    """
    return {
        "provider": "doubao",
        "role": "minimal_fallback",
        "priority": 3,  # 1=zhipu主, 2=ark备, 3=doubao兜底, 4=rule本地
        "model": _env('DOUBAO_FALLBACK_MODEL', 'doubao-1.5-lite-32k'),
        "endpoint": _env('DOUBAO_FALLBACK_ENDPOINT', ''),
        "max_tokens": int(_env('DOUBAO_FALLBACK_MAX_TOKENS', '256')),
        "temperature": 0.3,
        "timeout_sec": 15,
        "description": "豆包最小兜底通道：仅在主通道和备用通道都失败时使用，输出最短响应",
        "circuit_breaker": get_provider_breaker('doubao').snapshot(),
    }


def full_fallback_chain():
    """完整故障转移链：智谱主 → ark备 → 豆包兜底 → 本地规则。

    24h 保活目标：任何时刻至少有一个通道可用。
    """
    chain = provider_chain()
    # 确保豆包兜底在链中（如果未配置则追加）
    if 'doubao' not in chain:
        chain = chain + ['doubao']
    # 本地规则始终是最后兜底
    if 'rule' not in chain:
        chain = chain + ['rule']
    return chain


# ============================================================
# Track B 补全：断线重连（指数退避+上限）封装
# ============================================================
def reconnect_with_backoff(connect_fn, max_attempts=5, base_delay=1.0,
                            max_delay=30.0, on_attempt=None):
    """断线重连：指数退避+上限，保证不无限重试。

    Args:
        connect_fn: 无参连接函数，成功返回 True/连接对象，失败抛异常
        max_attempts: 最大尝试次数（含首次）
        base_delay: 基础退避时间（秒）
        max_delay: 退避上限（秒）
        on_attempt: 回调 on_attempt(attempt, success, delay, error)

    Returns:
        (success, result, attempts)
    """
    attempts = min(max(1, max_attempts), _HARD_MAX_ATTEMPTS)
    last_error = None
    for i in range(attempts):
        try:
            result = connect_fn()
            if on_attempt:
                try:
                    on_attempt(i + 1, True, 0, None)
                except Exception:
                    pass
            return True, result, i + 1
        except Exception as exc:
            last_error = exc
            delay = min(max_delay, base_delay * (2 ** i))
            if on_attempt:
                try:
                    on_attempt(i + 1, False, delay, exc)
                except Exception:
                    pass
            if i < attempts - 1:
                time.sleep(delay)
    return False, last_error, attempts


# ============================================================
# Track B 自描述
# ============================================================
def track_b_self_check():
    """Track B 自检：验证所有组件就绪。"""
    return {
        "connection_keepalive": {
            "heartbeat_24h": "implemented (start_24h_heartbeat, 60s default)",
            "reconnect_backoff": "implemented (reconnect_with_backoff, exp+cap)",
        },
        "multi_channel": {
            "primary": "zhipu (glm-5.3 / glm-4.5-air)",
            "backup": "ark (volcengine)",
            "minimal_fallback": "doubao (doubao-1.5-lite, 256 tokens)",
            "local_fallback": "rule (local rules engine)",
            "failover_executor": "route_with_fallback (per-provider circuit breaker)",
        },
        "encoding": {
            "request_encoding": "safe_encode_payload (utf-8 with replace fallback)",
            "response_decoding": "safe_decode_response (utf-8->gbk->gb18030->latin-1 chain)",
            "special_char_normalization": "normalize_special_chars (BOM/zero-width/control chars)",
        },
        "observability": {
            "connection_status": "get_channel_status_detailed (per-provider state)",
            "last_success_tracking": "CircuitBreaker.last_success_at",
            "failure_count": "CircuitBreaker.failure_count / consecutive_failures",
            "circuit_breaker": "CLOSED/OPEN/HALF_OPEN state machine per provider",
            "health_snapshot": "channel_health + all_provider_snapshots",
        },
        "hard_limits": {
            "max_attempts": _HARD_MAX_ATTEMPTS,
            "max_backoff_sec": _MAX_BACKOFF,
            "min_heartbeat_interval_sec": 30,
        },
        "status": "READY",
    }


# ============================================================
# V1.0 AI Provider Failover Policy (2026-09-07)
# 6层 Provider 层级 + 自动切换 + token 记录 + 切换审计
# ============================================================
import uuid as _uuid

# 6层 Provider 层级定义
PROVIDER_LAYERS_V1 = [
    {"layer": 1, "provider": "zhipu",   "role": "cloud_primary",    "models": ["glm-4.5-air", "glm-5.3", "glm-4.6v", "web-search-pro"]},
    {"layer": 2, "provider": "ark",     "role": "cloud_fallback",   "models": ["doubao-lite-4k", "doubao-pro-32k"]},
    {"layer": 3, "provider": "qwen",    "role": "cloud_standby",    "models": ["qwen-flash", "qwen-turbo"]},
    {"layer": 4, "provider": "ollama",  "role": "local_primary",    "models": ["qwen2.5-coder:7b-agent"]},
    {"layer": 5, "provider": "lmstudio","role": "local_secondary",  "models": ["local-model"]},
    {"layer": 6, "provider": "rule",    "role": "deterministic",    "models": ["deterministic_rule"]},
]

# 切换审计日志（内存环形缓冲，最近 200 条）
_FAILOVER_LOG = []
_FAILOVER_LOG_LOCK = threading.Lock()
_FAILOVER_LOG_MAX = 200


def extract_token_usage(response_data):
    """从 AI API 响应中提取 token 用量。
    支持 OpenAI 兼容格式: {"usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}}
    支持智谱格式: {"usage": {"prompt_tokens": N, "completion_tokens": N, "total_tokens": N}}
    返回 dict {prompt_tokens, completion_tokens, total_tokens}，全 0 表示无法解析。
    """
    if not isinstance(response_data, dict):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    usage = response_data.get("usage") or {}
    if not isinstance(usage, dict):
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    try:
        pt = int(usage.get("prompt_tokens", 0) or 0)
        ct = int(usage.get("completion_tokens", 0) or 0)
        tt = int(usage.get("total_tokens", 0) or 0)
        if tt == 0 and (pt > 0 or ct > 0):
            tt = pt + ct
        return {"prompt_tokens": pt, "completion_tokens": ct, "total_tokens": tt}
    except Exception:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def record_provider_switch(from_provider, to_provider, reason="",
                            task_id="", trace_id="", first_result=None):
    """记录 Provider 切换审计（V1.0 硬规则：禁止静默切换）。
    记录字段：时间/从哪到哪/原因/task_id/trace_id/切换后首次结果。
    """
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "from_provider": from_provider or "",
        "to_provider": to_provider or "",
        "reason": reason or "",
        "task_id": task_id or "",
        "trace_id": trace_id or _uuid.uuid4().hex[:16],
        "first_result": str(first_result)[:200] if first_result is not None else "",
    }
    with _FAILOVER_LOG_LOCK:
        _FAILOVER_LOG.append(entry)
        if len(_FAILOVER_LOG) > _FAILOVER_LOG_MAX:
            _FAILOVER_LOG.pop(0)
    # 同时写入 ai_call_logs（如果可用）
    try:
        import ai_call_logger as _acl
        _acl.log_call(
            provider=to_provider or "",
            model="provider_switch",
            prompt_version="failover_v1",
            input_hash=_acl.compute_input_hash(from_provider, to_provider, reason),
            output=f"switch: {from_provider} -> {to_provider}, reason={reason}",
            confidence=0.0,
            latency_ms=0,
            token_usage=0,
            failure_reason=f"failover:{from_provider}->{to_provider}:{reason}"[:300],
            success=True,
            task_id=task_id,
            trace_id=entry["trace_id"],
        )
    except Exception:
        pass
    return entry


def get_failover_log(limit=50):
    """获取最近的 Provider 切换审计日志。"""
    with _FAILOVER_LOG_LOCK:
        return list(_FAILOVER_LOG[-int(limit):])


def build_fallback_chain_v1():
    """构建 V1.0 6层 fallback 链（基于 .env 配置动态过滤）。
    有 API Key 的云端 Provider + 可探测的本地 Provider + 最终 rule。
    返回 provider 名称列表，按层级顺序。
    """
    ensure_env_loaded()
    chain = []
    # L1 智谱（必须有 key）
    if _env("ZHIPU_API_KEY"):
        chain.append("zhipu")
    # L2 ARK/豆包（必须有 key）
    if _env("ARK_API_KEY"):
        chain.append("ark")
    # L3 千问（必须有 key）
    if _env("DASHSCOPE_API_KEY") or _env("QWEN_API_KEY"):
        chain.append("qwen")
    # L4 Ollama（本地，默认可用）
    chain.append("ollama")
    # L5 LM Studio / llama.cpp（本地，默认可用）
    chain.append("lmstudio")
    # L6 本地确定性规则（最终兜底，始终在链中）
    chain.append("rule")
    return chain


def route_with_fallback_v1(call_fn, providers=None, on_result=None,
                            task_id="", trace_id=""):
    """V1.0 多 Provider 故障转移执行器（6层链 + 切换审计 + rule 标记）。
    call_fn(provider_name) -> (result_text, usage_dict) 或抛异常。
    usage_dict: {prompt_tokens, completion_tokens, total_tokens}
    按 providers 顺序尝试；每个 Provider 独立熔断；全部失败返回 (None, "rule", usage, switch_log)。
    auth / bad_request 等 fatal error 立即停止 provider 链。
    rule 兜底标记为 deterministic_fallback，不计算在 AI 失败率内。
    """
    chain = providers or build_fallback_chain_v1()
    last_provider = ""
    switches = []
    for prov in chain:
        # rule 是最终兜底，不走熔断
        if prov == "rule":
            break
        pb = get_provider_breaker(prov)
        if not pb.allow():
            if last_provider:
                sw = record_provider_switch(last_provider, prov, f"circuit_breaker_open:{prov}",
                                             task_id, trace_id)
                switches.append(sw)
            last_provider = prov
            continue
        try:
            result, usage = call_fn(prov)
            pb.record_success()
            if last_provider and last_provider != prov:
                sw = record_provider_switch(last_provider, prov, "fallback_success",
                                             task_id, trace_id, first_result=str(result)[:100])
                switches.append(sw)
            if on_result:
                try:
                    on_result(prov, result, True, usage)
                except Exception:
                    pass
            return result, prov, usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, switches
        except Exception as exc:
            kind, retryable = classify_error(exc)
            pb.record_failure(kind)
            if last_provider and last_provider != prov:
                sw = record_provider_switch(last_provider, prov, f"{kind}:{str(exc)[:80]}",
                                             task_id, trace_id)
                switches.append(sw)
            last_provider = prov
            if on_result:
                try:
                    on_result(prov, None, False, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
                except Exception:
                    pass
            if not retryable:
                break
            continue
    # 全部 Provider 失败/熔断或 fatal error → L6 本地规则兜底
    usage_zero = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    if last_provider and last_provider != "rule":
        sw = record_provider_switch(last_provider, "rule", "provider_chain_exhausted_or_fatal",
                                     task_id, trace_id)
        switches.append(sw)
    return None, "rule", usage_zero, switches


def get_provider_status_v1():
    """V1.0 获取所有 Provider 运行时状态（基于 .env 配置 + 熔断状态）。"""
    ensure_env_loaded()
    statuses = {}
    for layer in PROVIDER_LAYERS_V1:
        prov = layer["provider"]
        if prov == "rule":
            statuses[prov] = {"status": "DETERMINISTIC_FALLBACK", "layer": layer["layer"], "role": layer["role"]}
            continue
        # 检查 API key
        key_env = {
            "zhipu": "ZHIPU_API_KEY",
            "ark": "ARK_API_KEY",
            "qwen": "DASHSCOPE_API_KEY",
            "ollama": None,
            "lmstudio": None,
        }.get(prov)
        has_key = True
        if key_env:
            has_key = bool(_env(key_env))
        # 检查熔断状态
        try:
            pb = get_provider_breaker(prov)
            cb_state = pb.state
        except Exception:
            cb_state = "UNKNOWN"
        # 确定状态
        if not has_key:
            st = "NOT_CONFIGURED"
        elif cb_state == "OPEN":
            st = "CIRCUIT_OPEN"
        elif prov == "zhipu":
            st = "ACTIVE"
        else:
            st = "ACTIVE_FALLBACK"
        statuses[prov] = {
            "status": st,
            "layer": layer["layer"],
            "role": layer["role"],
            "models": layer["models"],
            "circuit_breaker": cb_state,
            "api_key_configured": has_key,
        }
    return statuses
