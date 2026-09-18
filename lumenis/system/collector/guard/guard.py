# -*- coding: utf-8 -*-
"""CollectorGuard：包在“原采集函数”外层的韧性保护层（不重写 data_collector / 采集核心）。

统一闭环：受控状态判断 -> 动态限速等待 -> 调用原采集 -> 响应分类 -> 更新限速/指标/断点 -> 返回 GuardResult。
任何内部异常都被捕获并降级为 NETWORK_ERROR，绝不向上拖垮 Flask 主系统。
"""
import os
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional

from .state import CollectState
from .analyzer import ResponseAnalyzer, Reason
from .rate_limiter import AdaptiveRateLimiter
from .metrics import GuardMetrics
from .checkpoint import Checkpoint
from core.repository_registry import get_data_dir


@dataclass
class GuardResult:
    state: str
    reason: str
    notes: List[dict] = field(default_factory=list)
    detail: str = ''
    ok: bool = False
    latency: float = 0.0
    metrics: dict = field(default_factory=dict)
    raw: Any = None

    @property
    def should_stop(self):
        return self.state in CollectState.STOP_REQUEST

    def to_dict(self):
        return {'state': self.state, 'state_label': CollectState.label(self.state),
                'reason': self.reason, 'detail': self.detail, 'ok': self.ok,
                'latency': round(self.latency, 3), 'count': len(self.notes),
                'metrics': self.metrics}


# collector 已显式给出的风控态 -> Guard 状态（优先级最高，避免被文本分类稀释）
_EXPLICIT = {
    'IP_RISK_OR_300012': (CollectState.COOLDOWN, Reason.IP_RISK_300012),
    'NEED_VERIFY': (CollectState.NEED_VERIFY, Reason.NEED_CAPTCHA),
    'AUTH_REQUIRED': (CollectState.AUTH_REQUIRED, Reason.AUTH_EXPIRED),
}


class CollectorGuard:
    def __init__(self, platform, enabled=True, base_interval=None, checkpoint_dir=None):
        self.platform = platform
        self.enabled = enabled
        self.analyzer = ResponseAnalyzer()
        self.limiter = AdaptiveRateLimiter(base_interval=base_interval, enabled=enabled)
        self.metrics = GuardMetrics(
            persist_path=os.path.join(get_data_dir(), 'metrics', 'collector-metrics.jsonl'))
        self.checkpoint = Checkpoint(platform, checkpoint_dir)

    def run(self, collect_fn, keyword, **kwargs):
        # 关闭时直通，仅做异常兜底，不改变原采集行为
        if not self.enabled:
            t = time.time()
            try:
                raw = collect_fn(**kwargs)
            except Exception as e:
                return GuardResult(CollectState.NETWORK_ERROR, Reason.NETWORK, [], str(e)[:200],
                                   False, time.time() - t, self.metrics.snapshot())
            return GuardResult(CollectState.HEALTHY, Reason.HEALTHY, self._extract(raw), '',
                               True, time.time() - t, self.metrics.snapshot(), raw)

        # 熔断/暂停/验证/登录态：停止危险请求，直接返回受控状态（不伪装成 0 条）
        # COOLDOWN 冷却到期后允许 half-open 探测（避免死锁：否则永远不发请求→永远不触发on_success→永久COOLDOWN）
        if self.limiter.state in CollectState.STOP_REQUEST:
            if self.limiter.state == CollectState.COOLDOWN and self.limiter.can_run():
                # 冷却已到期：放行一次 half-open 探测，成功则 on_success 恢复 HEALTHY，失败则重新冷却
                pass
            else:
                snap = self.limiter.snapshot()
                return GuardResult(self.limiter.state, snap['state'], [],
                               f"受控状态 {CollectState.label(self.limiter.state)}，剩余冷却 "
                               f"{self.limiter.remaining_cooldown():.0f}s",
                               False, 0.0, self.metrics.snapshot())

        self.limiter.wait_slot()
        t = time.time()
        try:
            raw = collect_fn(**kwargs)
        except Exception as e:
            lat = time.time() - t
            cls = self.analyzer.classify(0, '', error=e)
            self._after_fail(cls, lat)
            return GuardResult(cls['state'], cls['reason'], [], cls['detail'], False, lat,
                               self.metrics.snapshot())

        lat = time.time() - t
        notes = self._extract(raw)
        err = (raw or {}).get('error', '') if isinstance(raw, dict) else ''

        if err in _EXPLICIT:
            st, rs = _EXPLICIT[err]
            cls = {'state': st, 'reason': rs, 'detail': err, 'should_stop': True}
        elif err:
            cls = self.analyzer.classify(200, str(err), has_content=bool(notes))
        else:
            # 采集器无错误返回即视为健康；notes 为空代表该词确无新内容，不是风控、不是网络错误
            cls = {'state': CollectState.HEALTHY, 'reason': Reason.HEALTHY, 'detail': 'ok', 'should_stop': False}

        if cls['state'] in CollectState.RISK:
            self._after_fail(cls, lat)
            ok = False
        else:
            self.limiter.on_success()
            # 采集准确度质量门：统计本次采集结果的9项完整性指标（COLLECTION_ACCURACY_GATE_v1）
            try:
                self.metrics.record_quality(notes)
            except Exception as _q_err:
                pass  # 质量门统计失败不阻断采集主流程
            self.metrics.record(True, lat)
            ids = [n.get('note_id') for n in notes if isinstance(n, dict) and n.get('note_id')]
            if ids:
                self.checkpoint.mark_seen(keyword, ids)
            ok = True
        return GuardResult(cls['state'], cls['reason'], notes, cls['detail'], ok, lat,
                           self.metrics.snapshot(), raw)

    def _after_fail(self, cls, lat):
        st = cls['state']
        if st in (CollectState.AUTH_REQUIRED, CollectState.NEED_VERIFY, CollectState.COOLDOWN):
            self.limiter.force_pause(st)
        else:
            self.limiter.on_failure(retry_after=cls.get('retry_after'))
        self.metrics.record(False, lat, cls.get('detail', ''))

    @staticmethod
    def _extract(raw):
        if raw is None:
            return []
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get('notes') or []
        return []

    def status(self):
        self.metrics.persist()  # 非热路径：限频落盘采集性能快照（P0-E）
        return {'platform': self.platform, 'enabled': self.enabled,
                'limiter': self.limiter.snapshot(), 'metrics': self.metrics.snapshot()}
