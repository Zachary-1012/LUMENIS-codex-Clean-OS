# -*- coding: utf-8 -*-
"""RedNote / 小红书采集运行策略（阶段5 集中策略 SoT，纯配置、零副作用）。

用户 2026-09-01 拍板的暂行策略（唯一权威口径，散落在各采集器的开关以后统一读这里）：
1. 国内 xiaohongshu.com 当前保持暂停（熔断中，不撞、不绕验证）；
2. RedNote 香港/国际入口为主，**每天登录一次保活**，尽量长期在线；
3. 三端开关：话题端(topic)持续监测收录 = 开；舆情笔记端(public_opinion) = 开；
   事件笔记端(event) = 暂不开；
4. 一律按「真人频率」节奏，系统正式运行、边采边供 Zachary 学习。

工程纪律（不可违反）：
- 本模块**只产出策略判定，不发起任何采集、不连浏览器、不联网**；
- 会触发真实平台动作的总开关默认保守（不自动跑），须显式 env 或调度授权才运行；
- 真人频率数值未经最新一轮实测前标 NOT_VERIFIED，使用保守占位，绝不伪装成实测结论；
- 遇到验证码 / 300012 / IP 风险只识别→停→熔断→冷却→合法人工验证，不破解不绕。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict
from typing import Dict

# 三端（note/task kind）开关：与用户拍板一致；事件笔记默认关
_DEFAULT_KIND_ENABLED = {
    "topic": True,            # 话题端：持续监测与收录
    "public_opinion": True,   # 舆情笔记端：开放
    "event": False,           # 事件笔记端：暂不开放
}

# 入口区域：intl=RedNote 香港/国际为主；cn=国内（2026-09-02 用户指令恢复国内采集，不再暂停）
DEFAULT_PRIMARY_REGION = "intl"
CN_PAUSED = False

# 真人节奏保守占位（秒）。NOT_VERIFIED：待最新一轮真人频率实测后用实测值覆盖；
# 这里宁慢勿快，避免把未实测数值当作结论。
HUMAN_CADENCE_PLACEHOLDER = {
    "status": "NOT_VERIFIED",
    "search_settle_min_s": 3.0,
    "search_settle_max_s": 6.0,
    "scroll_step_min_s": 2.5,
    "scroll_step_max_s": 5.0,
    "detail_read_min_s": 4.0,     # 详情停留，模拟阅读
    "detail_read_max_s": 9.0,
    "between_notes_min_s": 3.0,
    "between_notes_max_s": 8.0,
    "comment_page_min_s": 1.5,
    "comment_page_max_s": 3.5,
    "daily_login_keepalive": "once_per_day",
}


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None or v == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class RedNotePolicy:
    primary_region: str
    cn_paused: bool
    # 真实平台自动运行总闸（默认 False：只在显式授权时才自动跑，避免误撞）
    auto_run_enabled: bool
    daily_login_keepalive: bool
    kind_enabled: Dict[str, bool]
    human_cadence: Dict[str, object]

    def can_run_kind(self, kind: str) -> bool:
        """三端门控：未登记的 kind 默认不放行（白名单制）。"""
        return bool(self.kind_enabled.get(str(kind).lower(), False))

    def to_dict(self) -> dict:
        return asdict(self)


def effective_policy() -> RedNotePolicy:
    """汇总当前生效策略（env 可覆盖，但默认安全）。"""
    kind = dict(_DEFAULT_KIND_ENABLED)
    # 允许用 env 精确覆盖三端，缺省维持拍板值
    kind["topic"] = _env_bool("REDNOTE_KIND_TOPIC", kind["topic"])
    kind["public_opinion"] = _env_bool("REDNOTE_KIND_PUBLIC_OPINION", kind["public_opinion"])
    kind["event"] = _env_bool("REDNOTE_KIND_EVENT", kind["event"])
    return RedNotePolicy(
        primary_region=(os.environ.get("REDNOTE_PRIMARY_REGION") or DEFAULT_PRIMARY_REGION).strip().lower(),
        cn_paused=_env_bool("REDNOTE_CN_PAUSED", CN_PAUSED),
        auto_run_enabled=_env_bool("REDNOTE_AUTO_RUN", False),
        daily_login_keepalive=_env_bool("REDNOTE_DAILY_LOGIN_KEEPALIVE", False),
        kind_enabled=kind,
        human_cadence=dict(HUMAN_CADENCE_PLACEHOLDER),
    )
