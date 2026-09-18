# -*- coding: utf-8 -*-
"""统一采集状态映射（单一权威，避免多套状态系统互相冲突）。

以 v5.8.6 platform_adapters 的 CollectionStatus 八态为内部规范态(canonical)，向另外三套
现存表示做双向兼容：
  - collector_guard.state.CollectState（七态小写，现网风险状态机）
  - collection_logs.status（冲刺6 大写六态 + 历史小写 success/error）
  - 小红书 collector 显式错误码（IP_RISK_OR_300012 / NEED_VERIFY / AUTH_REQUIRED）

并落实“三类分清”：
  A 登录失效(SESSION_EXPIRED) → 弹统一 Auth 窗/合法登录入口
  B 人机验证(NEED_VERIFY)     → 提示人工验证，不绕过
  C IP风控/熔断(BLOCKED/COOLING_DOWN) → 冷却熔断，绝不伪装成“扫码可解”或“0 条”
"""
from __future__ import annotations

from typing import Optional


# —— 规范态（与 platform_adapters.base.CollectionStatus 的值保持一致）——
class CS:
    SUCCESS = "SUCCESS"
    NO_NEW_DATA = "NO_NEW_DATA"
    RISK_WARNING = "RISK_WARNING"
    NEED_VERIFY = "NEED_VERIFY"
    BLOCKED = "BLOCKED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    COLLECT_ERROR = "COLLECT_ERROR"
    COOLING_DOWN = "COOLING_DOWN"
    NETWORK_ERROR = "NETWORK_ERROR"  # 内部细分：网络类错误（退避用），落库时归一到 COLLECT_ERROR/NETWORK


CANONICAL_ALL = (
    CS.SUCCESS, CS.NO_NEW_DATA, CS.RISK_WARNING, CS.NEED_VERIFY, CS.BLOCKED,
    CS.SESSION_EXPIRED, CS.COLLECT_ERROR, CS.COOLING_DOWN, CS.NETWORK_ERROR,
)

# 规范态 -> collector_guard CollectState（小写七态）
CANON_TO_GUARD = {
    CS.SUCCESS: "healthy",
    CS.NO_NEW_DATA: "healthy",
    CS.RISK_WARNING: "warning",
    CS.COOLING_DOWN: "cooldown",
    CS.BLOCKED: "paused",
    CS.SESSION_EXPIRED: "auth_required",
    CS.NEED_VERIFY: "need_verify",
    CS.COLLECT_ERROR: "network_error",
    CS.NETWORK_ERROR: "network_error",
}
# collector_guard -> 规范态
GUARD_TO_CANON = {
    "healthy": CS.SUCCESS,        # 有无内容由 items 数另行判定为 NO_NEW_DATA
    "warning": CS.RISK_WARNING,
    "cooldown": CS.COOLING_DOWN,
    "paused": CS.BLOCKED,
    "auth_required": CS.SESSION_EXPIRED,
    "need_verify": CS.NEED_VERIFY,
    "network_error": CS.NETWORK_ERROR,
}

# collection_logs 六态/历史小写 -> 规范态
LOG_TO_CANON = {
    "SUCCESS": CS.SUCCESS,
    "EMPTY": CS.NO_NEW_DATA,
    "NO_NEW_DATA": CS.NO_NEW_DATA,
    "AUTH_REQUIRED": CS.SESSION_EXPIRED,
    "AUTH_FAILED": CS.SESSION_EXPIRED,   # 小红书登录失效属 A 类，弹统一 Auth 窗，不计为采集错误/0 条
    "SESSION_EXPIRED": CS.SESSION_EXPIRED,
    "CAPTCHA": CS.NEED_VERIFY,
    "NEED_VERIFY": CS.NEED_VERIFY,
    "BLOCKED": CS.BLOCKED,
    "COOLING_DOWN": CS.COOLING_DOWN,
    "RISK_WARNING": CS.RISK_WARNING,
    "PARTIAL_BLOCKED": CS.RISK_WARNING,  # 部分关键词被拦截=轻度风险，降频而非熔断/0条
    "NETWORK_ERROR": CS.NETWORK_ERROR,
    "COLLECT_ERROR": CS.COLLECT_ERROR,
    "success": CS.SUCCESS,       # 历史旧实例小写兼容
    "error": CS.COLLECT_ERROR,
}

# 小红书 collector 显式错误码 -> 规范态
XHS_CODE_TO_CANON = {
    "IP_RISK_OR_300012": CS.BLOCKED,
    "NEED_VERIFY": CS.NEED_VERIFY,
    "AUTH_REQUIRED": CS.SESSION_EXPIRED,
}

# 规范态 -> collection_logs 落库六态（大写，供新代码统一写入）
CANON_TO_LOG = {
    CS.SUCCESS: "SUCCESS",
    CS.NO_NEW_DATA: "EMPTY",
    CS.RISK_WARNING: "BLOCKED",     # 轻度风险仍可能有数据；落库态以受控状态呈现，不计为成功空
    CS.NEED_VERIFY: "CAPTCHA",
    CS.BLOCKED: "BLOCKED",
    CS.SESSION_EXPIRED: "AUTH_REQUIRED",
    CS.COLLECT_ERROR: "NETWORK_ERROR",
    CS.NETWORK_ERROR: "NETWORK_ERROR",
    CS.COOLING_DOWN: "BLOCKED",
}

# 三类分清
CLASS_A_AUTH = "A_AUTH"
CLASS_B_VERIFY = "B_VERIFY"
CLASS_C_RISK = "C_RISK"
CLASS_NET = "NET"
CLASS_OK = "OK"
_INCIDENT_CLASS = {
    CS.SESSION_EXPIRED: CLASS_A_AUTH,
    CS.NEED_VERIFY: CLASS_B_VERIFY,
    CS.BLOCKED: CLASS_C_RISK,
    CS.COOLING_DOWN: CLASS_C_RISK,
    CS.NETWORK_ERROR: CLASS_NET,
    CS.COLLECT_ERROR: CLASS_NET,
    CS.RISK_WARNING: CLASS_C_RISK,
}

_STOP = {CS.BLOCKED, CS.COOLING_DOWN, CS.SESSION_EXPIRED, CS.NEED_VERIFY}
_HUMAN = {CS.SESSION_EXPIRED, CS.NEED_VERIFY}
_OK = {CS.SUCCESS, CS.NO_NEW_DATA}


def to_canonical(state: Optional[str], *, items: Optional[int] = None,
                 xhs_code: Optional[str] = None) -> str:
    """把任意来源状态字符串归一为规范态。

    items 仅用于把“健康但无内容”明确为 NO_NEW_DATA（区别于风控空）。
    xhs_code 优先级最高（collector 显式风控码不允许被文本稀释）。
    """
    if xhs_code and xhs_code in XHS_CODE_TO_CANON:
        canon = XHS_CODE_TO_CANON[xhs_code]
    elif state is None or str(state).strip() == "":
        canon = CS.COLLECT_ERROR
    else:
        s = str(state).strip()
        canon = LOG_TO_CANON.get(s) or GUARD_TO_CANON.get(s) or LOG_TO_CANON.get(s.upper())
        if canon is None:
            canon = CS.COLLECT_ERROR
    if canon == CS.SUCCESS and items is not None and items == 0:
        canon = CS.NO_NEW_DATA
    return canon


def to_guard(canon: str) -> str:
    return CANON_TO_GUARD.get(canon, "network_error")


def to_log_status(canon: str) -> str:
    return CANON_TO_LOG.get(canon, "NETWORK_ERROR")


def incident_class(canon: str) -> str:
    return _INCIDENT_CLASS.get(canon, CLASS_OK)


def is_stop_request(canon: str) -> bool:
    """命中即必须停止继续请求平台（熔断/等待人工），不得伪装 0 条。"""
    return canon in _STOP


def needs_human(canon: str) -> bool:
    return canon in _HUMAN


def is_ok(canon: str) -> bool:
    return canon in _OK


def is_network(canon: str) -> bool:
    return canon in (CS.NETWORK_ERROR, CS.COLLECT_ERROR)
