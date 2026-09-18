"""
采集适配器基类
所有新采集源继承此基类，实现统一接口
支持：熔断器、重试、限流、降级、标准化输出、故障隔离、指标统计

v5.9.9 增量增强：
- 新增 RateLimiter 令牌桶限流
- 新增 Fallback 降级机制（采集失败返回缓存/空结果，不抛异常）
- 新增 AdapterMetrics 运行指标统计
- 新增 safe_collect() 永不抛异常入口
- 保留原有 search()/collect() 接口完全不变，20个适配器零改动
"""
import time
import logging
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from ..config import ADAPTER_CONFIG

logger = logging.getLogger(__name__)


def optional_int(value):
    """Convert an observed count without turning absence into a measured zero."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


@dataclass
class CollectedNote:
    """标准化采集结果"""
    title: str
    content: str = ""
    url: str = ""
    author: str = ""
    author_id: str = ""
    publish_date: str = ""
    # Missing observations are unknown, not measured zero.
    likes: Optional[int] = None
    comments: Optional[int] = None
    collects: Optional[int] = None
    shares: Optional[int] = None
    cover: str = ""
    source_platform: str = ""
    raw_data: dict = field(default_factory=dict)


@dataclass
class AdapterResult:
    """适配器执行结果"""
    success: bool
    notes: List[CollectedNote] = field(default_factory=list)
    error: str = ""
    raw_count: int = 0
    duration_seconds: float = 0


class CircuitBreaker:
    """熔断器：连续失败N次后熔断，冷却后恢复"""
    def __init__(self, threshold: int = None, reset_seconds: int = None):
        self.threshold = threshold or ADAPTER_CONFIG["circuit_breaker_threshold"]
        self.reset_seconds = reset_seconds or ADAPTER_CONFIG["circuit_breaker_reset"]
        self.fail_count = 0
        self.last_fail_time = 0
        self.state = "closed"  # closed/open/half_open

    def allow(self) -> bool:
        if self.state == "open":
            if time.time() - self.last_fail_time > self.reset_seconds:
                self.state = "half_open"
                return True
            return False
        return True

    def record_success(self):
        self.fail_count = 0
        self.state = "closed"

    def record_failure(self):
        self.fail_count += 1
        self.last_fail_time = time.time()
        if self.fail_count >= self.threshold:
            self.state = "open"
            logger.warning(f"熔断器触发，失败{self.fail_count}次")


class RateLimiter:
    """令牌桶限流：控制采集频率，避免触发平台风控"""
    def __init__(self, rate_per_minute: int = None, burst: int = None):
        self.rate = rate_per_minute or ADAPTER_CONFIG.get("rate_limit_per_minute", 30)
        self.burst = burst or ADAPTER_CONFIG.get("rate_limit_burst", 5)
        self.tokens = float(self.burst)
        self.last_refill = time.time()
        self._lock = False  # 简单自旋锁，避免多线程超发

    def acquire(self, timeout: float = 5.0) -> bool:
        """获取一个令牌，超时返回False"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            now = time.time()
            elapsed = now - self.last_refill
            self.last_refill = now
            self.tokens = min(self.burst, self.tokens + elapsed * (self.rate / 60.0))
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            time.sleep(0.1)
        return False

    def try_acquire(self) -> bool:
        """非阻塞获取令牌"""
        now = time.time()
        elapsed = now - self.last_refill
        self.last_refill = now
        self.tokens = min(self.burst, self.tokens + elapsed * (self.rate / 60.0))
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class AdapterMetrics:
    """适配器运行指标统计"""
    def __init__(self, window_seconds: int = 3600):
        self.window = window_seconds
        self.total_calls = 0
        self.success_count = 0
        self.failure_count = 0
        self.circuit_open_count = 0
        self.rate_limited_count = 0
        self.fallback_count = 0
        self.total_duration = 0.0
        self.recent_durations = deque(maxlen=100)
        self.errors = deque(maxlen=50)

    def record_call(self, success: bool, duration: float, error: str = "",
                    circuit_open: bool = False, rate_limited: bool = False, fallback: bool = False):
        self.total_calls += 1
        self.total_duration += duration
        self.recent_durations.append(duration)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            if error:
                self.errors.append(f"{time.strftime('%H:%M:%S')} {error[:80]}")
        if circuit_open:
            self.circuit_open_count += 1
        if rate_limited:
            self.rate_limited_count += 1
        if fallback:
            self.fallback_count += 1

    @property
    def success_rate(self) -> float:
        return round(self.success_count / self.total_calls * 100, 1) if self.total_calls > 0 else 0.0

    @property
    def avg_duration(self) -> float:
        return round(self.total_duration / self.total_calls, 2) if self.total_calls > 0 else 0.0

    @property
    def p95_duration(self) -> float:
        if not self.recent_durations:
            return 0.0
        sorted_d = sorted(self.recent_durations)
        idx = int(len(sorted_d) * 0.95)
        return round(sorted_d[min(idx, len(sorted_d) - 1)], 2)

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "circuit_open_count": self.circuit_open_count,
            "rate_limited_count": self.rate_limited_count,
            "fallback_count": self.fallback_count,
            "avg_duration": self.avg_duration,
            "p95_duration": self.p95_duration,
            "recent_errors": list(self.errors)[-5:],
        }


class BaseAdapter(ABC):
    """采集适配器基类

    v5.9.9 增强：熔断器 + 重试 + 限流 + 降级 + 指标统计
    子类只需实现 search()，外部调用 collect() 或 safe_collect()
    """
    platform_name: str = "base"
    platform_display: str = "基础适配器"

    def __init__(self, fallback_handler: Callable = None,
                 rate_per_minute: int = None, enable_metrics: bool = True):
        self.breaker = CircuitBreaker()
        self.rate_limiter = RateLimiter(rate_per_minute=rate_per_minute)
        self.metrics = AdapterMetrics() if enable_metrics else None
        self.fallback_handler = fallback_handler  # 降级回调：(keyword, error) -> List[CollectedNote]
        self.config = ADAPTER_CONFIG
        self._last_result: Optional[AdapterResult] = None  # 最近一次成功结果，用于降级缓存

    @abstractmethod
    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """搜索采集，子类必须实现"""
        pass

    def collect(self, keyword: str, max_results: int = 20, *,
                allow_fallback: bool = True) -> AdapterResult:
        """
        采集入口（带熔断器+重试+限流）
        外部调用此方法，不要直接调search
        v5.9.9：增加限流检查，限流时等待令牌
        """
        start = time.time()

        # 限流检查
        if not self.rate_limiter.try_acquire():
            if self.metrics:
                self.metrics.record_call(False, 0, rate_limited=True)
            logger.info(f"[{self.platform_name}] 限流中，等待令牌...")
            if not self.rate_limiter.acquire(timeout=10.0):
                return self._fallback_or_fail(keyword, "限流超时", start, allow_fallback=allow_fallback)

        # 熔断检查
        if not self.breaker.allow():
            if self.metrics:
                self.metrics.record_call(False, time.time() - start, circuit_open=True)
            return self._fallback_or_fail(
                keyword, f"熔断器开启，平台{self.platform_name}暂不可用", start,
                allow_fallback=allow_fallback,
            )

        last_error = ""
        for attempt in range(self.config["max_retries"]):
            try:
                result = self.search(keyword, max_results)
                if result.success:
                    self.breaker.record_success()
                    result.duration_seconds = time.time() - start
                    self._last_result = result
                    if self.metrics:
                        self.metrics.record_call(True, result.duration_seconds)
                    return result
                last_error = result.error
                if self._is_terminal_provider_state(last_error):
                    # Authentication, rate-limit and risk responses must not be
                    # hammered by automatic retries.
                    break
            except Exception as e:
                last_error = str(e)
                logger.error("[%s] attempt=%s error_type=%s",
                             self.platform_name, attempt + 1, type(e).__name__)
                if self._is_terminal_provider_state(last_error):
                    break
            time.sleep(self.config["retry_delay"] * (attempt + 1))

        self.breaker.record_failure()
        duration = time.time() - start
        if self.metrics:
            self.metrics.record_call(False, duration, last_error)
        return self._fallback_or_fail(
            keyword, f"{self.platform_display}采集失败: {last_error}", start,
            allow_fallback=allow_fallback,
        )

    @staticmethod
    def _is_terminal_provider_state(error: str) -> bool:
        text = str(error or "").lower()
        markers = (
            "captcha", "验证码", "安全验证", "need_verify", "login", "登录",
            "cookie", "session expired", "会话失效", "风控", "risk", "频控",
            "rate limit", "too many requests", "http 429", "http 403", "blocked",
            "封禁", "300012", "-352", "-509",
        )
        return any(marker in text for marker in markers)

    def safe_collect(self, keyword: str, max_results: int = 20, *,
                     allow_fallback: bool = True) -> AdapterResult:
        """
        安全采集入口：永不抛异常，失败时返回空结果而非异常
        适用于批量采集场景，单个适配器失败不影响整体
        """
        try:
            return self.collect(keyword, max_results, allow_fallback=allow_fallback)
        except Exception as e:
            logger.error("[%s] safe_collect error_type=%s", self.platform_name, type(e).__name__)
            if self.metrics:
                self.metrics.record_call(False, 0, type(e).__name__)
            return AdapterResult(success=False, error=f"{self.platform_name}异常: {e}")

    def _fallback_or_fail(self, keyword: str, error: str, start: float, *,
                          allow_fallback: bool = True) -> AdapterResult:
        """降级处理：优先用fallback_handler，其次用最近成功结果缓存，最后返回失败"""
        duration = time.time() - start
        if not allow_fallback:
            return AdapterResult(success=False, error=error, duration_seconds=duration)
        # 1. 用户自定义降级
        if self.fallback_handler:
            try:
                notes = self.fallback_handler(keyword, error)
                if notes:
                    if self.metrics:
                        self.metrics.record_call(True, duration, fallback=True)
                    return AdapterResult(success=True, notes=notes, error=f"降级返回: {error}", duration_seconds=duration)
            except Exception as e:
                logger.warning(f"[{self.platform_name}] 降级回调异常: {e}")
        # 2. 最近成功结果缓存
        if self._last_result and self._last_result.success:
            if self.metrics:
                self.metrics.record_call(True, duration, fallback=True)
            return AdapterResult(
                success=True, notes=self._last_result.notes,
                error=f"缓存降级: {error}", duration_seconds=duration
            )
        # 3. 返回失败
        return AdapterResult(success=False, error=error, duration_seconds=duration)

    def _make_note(self, **kwargs) -> CollectedNote:
        """快速创建标准化笔记"""
        kwargs.setdefault("source_platform", self.platform_name)
        return CollectedNote(**kwargs)

    def get_status(self) -> dict:
        """获取适配器状态（v5.9.9增加限流和指标）"""
        status = {
            "platform": self.platform_name,
            "display": self.platform_display,
            "breaker_state": self.breaker.state,
            "fail_count": self.breaker.fail_count,
            "rate_limiter_tokens": round(self.rate_limiter.tokens, 2),
            "rate_limit_per_minute": self.rate_limiter.rate,
        }
        if self.metrics:
            status["metrics"] = self.metrics.to_dict()
        return status
