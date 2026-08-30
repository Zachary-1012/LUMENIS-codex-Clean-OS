# -*- coding: utf-8 -*-
"""采集风险评分引擎（对齐《交叉认证+风险闸门+采集安全控制》补丁 §21/§22）。

与 state.py 的离散七态互补：本模块给出 0-100 的连续“采集风险分”并映射到风险档位，
供动态降频/冷却/熔断决策使用。只做识别与降级，绝不更换身份、伪造设备或绕过平台安全机制。

风险分档（补丁口径，阈值可由 config/collector_guard.yaml 覆盖）：
    0-29  NORMAL        正常采集
    30-49 WATCH         观察（轻度风险，准备降频）
    50-69 THROTTLED     降速（拉长间隔）
    70-84 COOLDOWN      冷却（停止该平台请求一段时间）
    85-100 CIRCUIT_OPEN 熔断（停止任务，走恢复检测，不无限重试）

风险分随“成功/健康响应”衰减、随时间自然回落，实现 健康→升高→熔断→恢复检查→逐渐恢复 的闭环。
"""
import time

from .state import CollectState


# 风险因子加分（补丁 §21 参考值，可在构造时覆盖）
DEFAULT_FACTOR_WEIGHTS = {
    'continuous_failure': 20,   # 连续失败
    'security_page': 40,        # 安全限制页 / challenge
    'login_error': 30,          # 登录态异常
    'abnormal_response': 15,    # 响应异常（结构不符/异常状态码）
    'empty_result': 10,         # 异常空结果（区别于真实无内容）
    'http_error': 10,           # HTTP 4xx/5xx
    'rate_limited': 25,         # 明确限流（429/访问频繁）
}

# 分档阈值上界（含）
DEFAULT_BANDS = (
    (29, 'NORMAL'),
    (49, 'WATCH'),
    (69, 'THROTTLED'),
    (84, 'COOLDOWN'),
    (100, 'CIRCUIT_OPEN'),
)

# 风险档位 -> 采集状态机动作
BAND_TO_STATE = {
    'NORMAL': CollectState.HEALTHY,
    'WATCH': CollectState.HEALTHY,       # 观察期仍可采，但收紧
    'THROTTLED': CollectState.WARNING,   # 降速
    'COOLDOWN': CollectState.COOLDOWN,   # 冷却
    'CIRCUIT_OPEN': CollectState.PAUSED, # 熔断停任务，等待恢复检测
}

# 命中即直接熔断/冷却/认证的“硬信号”（不依赖累加分），与三类分清口径一致
HARD_SIGNAL_BAND = {
    'security_page': 'CIRCUIT_OPEN',  # 安全验证页：停，等人工，不绕过
    'login_error': 'CIRCUIT_OPEN',    # 登录失效：转 Auth Recovery
    'rate_limited': 'COOLDOWN',
}


class RiskEngine:
    """单平台单任务的滚动采集风险评分。线程内使用；多平台请各建一个实例。"""

    def __init__(self, weights=None, decay_per_success=12, decay_per_10s=3,
                 max_score=100, bands=None):
        self.weights = dict(DEFAULT_FACTOR_WEIGHTS)
        if weights:
            self.weights.update(weights)
        self.decay_per_success = decay_per_success  # 每次成功响应减分
        self.decay_per_10s = decay_per_10s          # 每经过 10 秒自然回落
        self.max_score = max_score
        self.bands = bands or DEFAULT_BANDS
        self.score = 0
        self.consecutive_failures = 0
        self.last_update = time.time()
        self.last_factors = []

    def _time_decay(self, now):
        elapsed = max(0.0, now - self.last_update)
        steps = int(elapsed // 10)
        if steps:
            self.score = max(0, self.score - steps * self.decay_per_10s)
            self.last_update = now

    def band_of(self, score=None):
        s = self.score if score is None else score
        for upper, name in self.bands:
            if s <= upper:
                return name
        return self.bands[-1][1]

    def record_failure(self, factor, times=1):
        """登记一次风险因子，返回 (score, band, state)。factor 见 DEFAULT_FACTOR_WEIGHTS 的 key。"""
        now = time.time()
        self._time_decay(now)
        self.consecutive_failures += 1
        w = self.weights.get(factor, 10)
        # 连续失败按补丁口径：第一次用因子分，后续连续失败叠加 continuous_failure
        add = w * max(1, times)
        if factor != 'continuous_failure' and self.consecutive_failures >= 2:
            add += self.weights.get('continuous_failure', 20)
        self.score = min(self.max_score, self.score + add)
        self.last_update = now
        self.last_factors.append((now, factor))
        band = HARD_SIGNAL_BAND.get(factor) or self.band_of()
        return self.score, band, BAND_TO_STATE[band]

    def record_success(self):
        """登记一次健康成功响应：清零连续失败、风险分衰减，返回 (score, band, state)。"""
        now = time.time()
        self._time_decay(now)
        self.consecutive_failures = 0
        self.score = max(0, self.score - self.decay_per_success)
        self.last_update = now
        band = self.band_of()
        return self.score, band, BAND_TO_STATE[band]

    def snapshot(self):
        self._time_decay(time.time())
        band = self.band_of()
        return {
            'risk_score': self.score,
            'band': band,
            'state': BAND_TO_STATE[band],
            'consecutive_failures': self.consecutive_failures,
            'should_stop_request': band in ('COOLDOWN', 'CIRCUIT_OPEN'),
        }
