# -*- coding: utf-8 -*-
"""
动态风控状态机（Adaptive Risk Controller）
==========================================
取代把“自动30min / 手动20min / 冷却1h / 每日9次”写死成永久规则的旧做法：
这些数字只作为 *健康基线*，真实频率由平台实时风险等级动态决定。

风险等级流转：
  HEALTHY 正常采集
    └─ 出现 BLOCKED/CAPTCHA → LIGHT（降频） 再犯 → MEDIUM（延长冷却）
         └─ 持续拦截 / 300012 / IP 风险 → IP_RISK（熔断，自动任务暂停）
  AUTH_REQUIRED → NEED_VERIFY（暂停，等待登录恢复，恢复后进入 RECOVERING 半开试探）
  NETWORK_ERROR  → 不计账号风险，仅短暂退避
  连续成功        → RECOVERING 半开 → MEDIUM→LIGHT→HEALTHY 逐步恢复频率

手动触发默认不被“到没到间隔”挡住（用户主动操作），仅 IP_RISK 硬熔断时拦截以保护账号；
自动调度严格遵循动态间隔与熔断。状态持久化到 data/risk_state.json，进程重启不丢，
支撑“晚上自动跑、人不在电脑前也能正确暂停/恢复”。
"""
import os
import json
import time
import threading
from pathlib import Path
from typing import Dict, Optional
from lumenis.shared.database.registry import get_data_dir

# ---------- 风险等级 ----------
HEALTHY = "HEALTHY"            # 健康：基线频率
LIGHT = "LIGHT"              # 轻度风险：降频
MEDIUM = "MEDIUM"            # 风险升高：进一步延长冷却
NEED_VERIFY = "NEED_VERIFY"  # 需登录/人机验证：暂停，等待恢复
IP_RISK = "IP_RISK"          # IP/强风控：熔断
RECOVERING = "RECOVERING"    # 恢复中：半开试探

# 六态 → 风险影响
_GOOD = {"SUCCESS", "EMPTY"}
_AUTH = {"AUTH_REQUIRED", "AUTH_FAILED", "CAPTCHA"}
_BLOCK = {"BLOCKED"}
_NET = {"NETWORK_ERROR"}

# 健康基线（仅初始参考，非永久真理，可被外部配置覆盖）
DEFAULT_POLICY = {
    "base_interval": 1800,      # 健康时自动采集最小间隔(秒)，历史值30min
    "interval_multiplier": {LIGHT: 2, MEDIUM: 4, RECOVERING: 3},
    "cooldown_seconds": {LIGHT: 900, MEDIUM: 3600, IP_RISK: 7200},
    "success_to_recover": 2,    # 半开阶段连续成功N次降一级
    "block_to_light": 1,
    "light_to_medium": 2,       # 轻度下再犯N次升中度
    "medium_to_iprisk": 2,
    "net_backoff": 60,
    "state_file": str(Path(get_data_dir()) / 'risk_state.json'),
}

_LEVEL_CN = {
    HEALTHY: "健康", LIGHT: "轻度风险·已降频", MEDIUM: "风险升高·冷却中",
    NEED_VERIFY: "需登录/验证·已暂停", IP_RISK: "IP风控·已熔断",
    RECOVERING: "恢复中·半开试探",
}


class PlatformRisk:
    def __init__(self, platform: str):
        self.platform = platform
        self.level = HEALTHY
        self.consecutive_good = 0
        self.consecutive_bad = 0
        self.last_result = ""
        self.last_run_at = 0.0
        self.last_success_at = 0.0
        self.cooldown_until = 0.0
        self.detail = ""
        self.provider_retry_after_until = 0.0

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict) -> "PlatformRisk":
        p = cls(d["platform"])
        for k, v in d.items():
            setattr(p, k, v)
        return p


class RiskController:
    """动态风控控制器（进程内单例，线程安全，状态落盘）。"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._g = threading.Lock()
        self.policy = DEFAULT_POLICY
        self.states: Dict[str, PlatformRisk] = {}
        self._load()

    # ---------- 持久化 ----------
    def _load(self):
        path = self.policy["state_file"]
        try:
            if os.path.exists(path):
                data = json.load(open(path, encoding="utf-8"))
                for k, d in data.items():
                    self.states[k] = PlatformRisk.from_dict(d)
        except Exception:
            pass  # 状态文件损坏不阻断运行

    def _save(self):
        try:
            path = self.policy["state_file"]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({k: v.to_dict() for k, v in self.states.items()},
                          f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    def _of(self, platform: str) -> PlatformRisk:
        st = self.states.get(platform)
        if st is None:
            st = PlatformRisk(platform)
            self.states[platform] = st
        return st

    # ---------- 上报采集结果，驱动状态流转 ----------
    def report(self, platform: str, state: str, detail: str = "", now: float = None):
        now = now or time.time()
        with self._g:
            st = self._of(platform)
            st.last_run_at = now
            st.last_result = state
            st.detail = detail or st.detail
            pol = self.policy

            if state in _GOOD:
                st.consecutive_good += 1
                st.consecutive_bad = 0
                st.last_success_at = now
                st.cooldown_until = 0
                # 渐进恢复
                if st.level in (RECOVERING, MEDIUM, LIGHT):
                    if st.consecutive_good >= pol["success_to_recover"]:
                        st.level = {RECOVERING: LIGHT, MEDIUM: RECOVERING,
                                    LIGHT: HEALTHY}.get(st.level, HEALTHY)
                        st.consecutive_good = 0
                elif st.level == NEED_VERIFY:
                    st.level = RECOVERING
                    st.consecutive_good = 0
                elif st.level == IP_RISK and now >= st.cooldown_until:
                    st.level = RECOVERING
            elif state in _AUTH:
                # 登录失效/人机：暂停等待恢复，不做频率惩罚升级
                st.level = NEED_VERIFY
                st.consecutive_bad += 1
            elif state in _BLOCK:
                st.consecutive_bad += 1
                if st.level == HEALTHY and st.consecutive_bad >= pol["block_to_light"]:
                    st.level, st.cooldown_until = LIGHT, now + pol["cooldown_seconds"][LIGHT]
                elif st.level == LIGHT and st.consecutive_bad >= pol["light_to_medium"]:
                    st.level, st.cooldown_until = MEDIUM, now + pol["cooldown_seconds"][MEDIUM]
                elif st.level in (MEDIUM, RECOVERING) and st.consecutive_bad >= pol["medium_to_iprisk"]:
                    st.level, st.cooldown_until = IP_RISK, now + pol["cooldown_seconds"][IP_RISK]
                elif st.level == HEALTHY:
                    st.cooldown_until = now + pol["cooldown_seconds"][LIGHT]
            elif state in _NET:
                # 网络问题不升账号风险，仅短退避
                st.cooldown_until = max(st.cooldown_until, now + pol["net_backoff"])
            else:  # FAIL 其他失败，轻度计坏
                st.consecutive_bad += 1
            self._save()

    def mark_recovered(self, platform: str):
        """登录恢复成功后调用：进入半开恢复，下一次成功采集即逐级回落。"""
        with self._g:
            st = self._of(platform)
            st.level = RECOVERING
            st.consecutive_good = 0
            st.consecutive_bad = 0
            st.cooldown_until = 0
            st.detail = "登录已恢复，半开试探"
            self._save()

    def reset(self, platform: str):
        with self._g:
            self.states[platform] = PlatformRisk(platform)
            self._save()

    # ---------- 查询 ----------
    def _interval_locked(self, st, now=None):
        """调用方必须已持有 self._g。"""
        base = self.policy["base_interval"]
        if st.level == HEALTHY:
            return base
        return int(base * self.policy["interval_multiplier"].get(st.level, 4))

    def current_interval(self, platform: str, now: float = None) -> int:
        """当前等级下建议的自动采集最小间隔(秒)。公共入口（加锁）。"""
        with self._g:
            return self._interval_locked(self._of(platform), now)

    def defer_retry_after(self, platform: str, seconds: int, *, now: float = None):
        """Persist an observed provider cooldown for every manual/auto caller."""
        if type(seconds) is not int or seconds < 0:
            raise ValueError('Retry-After requires nonnegative observed seconds')
        stamp = time.time() if now is None else now
        with self._g:
            state = self._of(platform)
            state.provider_retry_after_until = max(state.provider_retry_after_until,stamp+seconds)
            self._save()

    def retry_after_remaining(self, platform: str, *, now: float = None) -> int:
        import math
        stamp = time.time() if now is None else now
        with self._g:
            return max(0,math.ceil(self._of(platform).provider_retry_after_until-stamp))

    def allow(self, platform: str, manual: bool = False, now: float = None):
        """是否允许此刻采集。返回 (allowed, reason)。
        手动：仅 NEED_VERIFY / IP_RISK 冷却中硬拦截（保护账号）；
        自动：还要满足动态间隔与冷却。"""
        now = now or time.time()
        with self._g:
            st = self._of(platform)
            if now < st.provider_retry_after_until:
                return False, f'平台 Retry-After 冷却中，剩余{int(st.provider_retry_after_until-now)+1}s'
            if st.level == NEED_VERIFY:
                return False, "登录态失效，需重新登录/验证"
            if st.level == IP_RISK:
                if now < st.cooldown_until:
                    return False, f"IP风控熔断中，{int(st.cooldown_until-now)}s 后半开"
                return True, "熔断冷却到期，允许半开试探"
            if not manual and now < st.cooldown_until:
                return False, f"{_LEVEL_CN.get(st.level, st.level)}，剩余{int(st.cooldown_until-now)}s"
            if not manual and st.last_run_at and \
                    now - st.last_run_at < self._interval_locked(st, now):
                wait = int(self._interval_locked(st, now) - (now - st.last_run_at))
                return False, f"未到动态采集间隔，还需{wait}s"
            return True, "ok"

    def snapshot(self) -> list:
        """全部平台风险快照（供健康中心/前端）。"""
        now = time.time()
        out = []
        with self._g:
            for name, st in self.states.items():
                cooling = max(0, int(st.cooldown_until - now))
                out.append({
                    "platform": name, "level": st.level,
                    "level_cn": _LEVEL_CN.get(st.level, st.level),
                    "last_result": st.last_result, "last_run_at": st.last_run_at,
                    "last_success_at": st.last_success_at, "cooldown_remain": cooling,
                    "interval_s": self._interval_locked(st, now), "detail": st.detail,
                    'provider_retry_after_remain':max(0,int(st.provider_retry_after_until-now)+1)
                        if now < st.provider_retry_after_until else 0,
                })
        return out


risk_controller = RiskController()
