"""
采集适配器基类
所有新采集源继承此基类，实现统一接口
支持：熔断器、重试、标准化输出、故障隔离
"""
import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from ..config import ADAPTER_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class CollectedNote:
    """标准化采集结果"""
    title: str
    content: str = ""
    url: str = ""
    author: str = ""
    author_id: str = ""
    publish_date: str = ""
    likes: int = 0
    comments: int = 0
    collects: int = 0
    shares: int = 0
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


class BaseAdapter(ABC):
    """采集适配器基类"""
    platform_name: str = "base"
    platform_display: str = "基础适配器"

    def __init__(self):
        self.breaker = CircuitBreaker()
        self.config = ADAPTER_CONFIG

    @abstractmethod
    def search(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """搜索采集，子类必须实现"""
        pass

    def collect(self, keyword: str, max_results: int = 20) -> AdapterResult:
        """
        采集入口（带熔断器+重试）
        外部调用此方法，不要直接调search
        """
        start = time.time()
        if not self.breaker.allow():
            return AdapterResult(success=False, error=f"熔断器开启，平台{self.platform_name}暂不可用")

        last_error = ""
        for attempt in range(self.config["max_retries"]):
            try:
                result = self.search(keyword, max_results)
                if result.success:
                    self.breaker.record_success()
                    result.duration_seconds = time.time() - start
                    return result
                last_error = result.error
            except Exception as e:
                last_error = str(e)
                logger.error(f"[{self.platform_name}] 第{attempt+1}次失败: {e}")
            time.sleep(self.config["retry_delay"] * (attempt + 1))

        self.breaker.record_failure()
        return AdapterResult(
            success=False,
            error=f"{self.platform_display}采集失败: {last_error}",
            duration_seconds=time.time() - start,
        )

    def _make_note(self, **kwargs) -> CollectedNote:
        """快速创建标准化笔记"""
        kwargs.setdefault("source_platform", self.platform_name)
        return CollectedNote(**kwargs)

    def get_status(self) -> dict:
        """获取适配器状态"""
        return {
            "platform": self.platform_name,
            "display": self.platform_display,
            "breaker_state": self.breaker.state,
            "fail_count": self.breaker.fail_count,
        }
