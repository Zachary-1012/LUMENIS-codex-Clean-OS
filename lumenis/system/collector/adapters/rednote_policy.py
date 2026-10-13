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

# 入口区域：intl=RedNote 香港/国际；cn=国内。
# 当前生产边界由最新运行指令冻结为：仅使用香港/国际账号，内地暂停。
DEFAULT_PRIMARY_REGION = "intl"
DEFAULT_COLLECTION_ACCOUNT = "XHS_RETINAUT"
POLICY_VERSION = "rednote-hk-only-v1"
CN_PAUSED = True

# Automatic collection is only supported for the existing narrow scheduler
# contract. These values must be explicitly configured together with
# REDNOTE_AUTO_RUN; missing, broad, or mismatched configuration stays manual.
AUTO_COLLECTION_SCOPE = "ALL_REGISTERED_SUBJECTS"  # PO 2026-10-13: every active registered Subject/BrandFocus; targets come from acquisition_plan registry
AUTO_COLLECTION_SOURCE = "rednote_hk"
AUTO_COLLECTION_CADENCE_MINUTES = 720

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


def automatic_collection_opt_in_enabled() -> bool:
    """Return true only for the explicit scope/source/cadence this scheduler runs."""
    if not _env_bool("REDNOTE_AUTO_RUN", False):
        return False
    scope = (os.environ.get("REDNOTE_AUTO_SCOPE") or "").strip().upper()
    source = (os.environ.get("REDNOTE_AUTO_SOURCE") or "").strip().lower()
    cadence = (os.environ.get("REDNOTE_AUTO_CADENCE_MINUTES") or "").strip()
    return (
        scope == AUTO_COLLECTION_SCOPE
        and source == AUTO_COLLECTION_SOURCE
        and cadence == str(AUTO_COLLECTION_CADENCE_MINUTES)
    )


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

    def region_allowed(self, region: str) -> bool:
        """判断区域是否允许进入生产采集主链。"""
        normalized = (region or "").strip().lower()
        if normalized == "intl":
            return True
        if normalized == "cn":
            return not self.cn_paused
        return False

    def account_allowed(self, account: str) -> bool:
        """判断账号是否允许进入生产采集主链。

        当前只允许 XHS_RETINAUT（香港/国际账号）；内地账号仍可被
        Runtime 诊断识别，但不能触发生产采集。
        """
        return (account or "").strip().upper() == DEFAULT_COLLECTION_ACCOUNT

    def to_dict(self) -> dict:
        data = asdict(self)
        data.update({
            "policy_version": POLICY_VERSION,
            "collection_account": DEFAULT_COLLECTION_ACCOUNT,
            "collection_region": "intl",
            "collection_accounts": [DEFAULT_COLLECTION_ACCOUNT],
            "paused_regions": ["cn"] if self.cn_paused else [],
            "mainland_opt_in": not self.cn_paused,
        })
        return data


def effective_policy() -> RedNotePolicy:
    """汇总当前生效策略（env 可覆盖，但默认安全）。"""
    kind = dict(_DEFAULT_KIND_ENABLED)
    # 允许用 env 精确覆盖三端，缺省维持拍板值
    kind["topic"] = _env_bool("REDNOTE_KIND_TOPIC", kind["topic"])
    kind["public_opinion"] = _env_bool("REDNOTE_KIND_PUBLIC_OPINION", kind["public_opinion"])
    kind["event"] = _env_bool("REDNOTE_KIND_EVENT", kind["event"])
    # 当前用户边界是不可由运行环境偷偷解除的暂停；未来如恢复内地，必须
    # 经过新的产品/安全确认并修改这份策略源代码，而不是注入一个环境变量。
    cn_paused = CN_PAUSED
    return RedNotePolicy(
        primary_region=(os.environ.get("REDNOTE_PRIMARY_REGION") or DEFAULT_PRIMARY_REGION).strip().lower(),
        cn_paused=cn_paused,
        auto_run_enabled=automatic_collection_opt_in_enabled(),
        daily_login_keepalive=_env_bool("REDNOTE_DAILY_LOGIN_KEEPALIVE", False),
        kind_enabled=kind,
        human_cadence=dict(HUMAN_CADENCE_PLACEHOLDER),
    )


# ============================================================
# 区域选择（当前生产主链固定 RedNote 港版 intl；大陆仅保留诊断映射）
# ============================================================
# CDP 端口映射（与 start_production.ps1 三浏览器对齐）：
#   9222 = XHS_CN_PRIMARY  大陆 xiaohongshu.com
#   9223 = XHS_RETINAUT    港版/国际 RedNote
#   9224 = GENERAL_BROWSE  通用浏览（不用于采集主链路）
REGION_CDP_PORT = {"cn": 9222, "intl": 9223}
# 区域对应的站点 host（用于导航与日志，不做硬编码假设之外的用途）
REGION_HOST = {
    "cn": "www.xiaohongshu.com",
    "intl": "www.rednote.com",
}

# 进程内轮番记忆（线程安全由 GIL 保证单写；跨进程由调度器持久化 last_region）
_last_region_state = {"region": None, "count": 0}


def get_cdp_port(region: str):
    """区域 → CDP 端口。未知区域回落到 primary_region 对应端口。"""
    region = (region or "").strip().lower()
    if region in REGION_CDP_PORT:
        return REGION_CDP_PORT[region]
    pol = effective_policy()
    return REGION_CDP_PORT.get(pol.primary_region, REGION_CDP_PORT["intl"])


def collection_gate(*, account: str = None, region: str = None) -> dict:
    """生产采集统一门禁；只判定，不连接平台、不启动浏览器。"""
    pol = effective_policy()
    requested_account = (account or DEFAULT_COLLECTION_ACCOUNT).strip().upper()
    requested_region = (region or "intl").strip().lower()
    if not pol.account_allowed(requested_account):
        return {
            "ok": False,
            "code": "account_paused",
            "account": requested_account,
            "region": requested_region,
            "allowed_account": DEFAULT_COLLECTION_ACCOUNT,
            "reason": "当前生产采集仅允许XHS_RETINAUT香港/国际账号，内地账号已暂停",
            "policy_version": POLICY_VERSION,
        }
    if not pol.region_allowed(requested_region):
        return {
            "ok": False,
            "code": "region_paused" if requested_region == "cn" else "region_not_allowed",
            "account": requested_account,
            "region": requested_region,
            "allowed_region": "intl",
            "reason": "当前生产采集仅允许RedNote香港/国际入口，内地入口已暂停",
            "policy_version": POLICY_VERSION,
        }
    return {
        "ok": True,
        "code": "allowed",
        "account": requested_account,
        "region": "intl",
        "cdp_port": REGION_CDP_PORT["intl"],
        "host": REGION_HOST["intl"],
        "policy_version": POLICY_VERSION,
    }


def select_region(*, kos_only: bool = False, last_region: str = None,
                  force_region: str = None):
    """选择下一次采集的区域。

    规则（安全优先，不做高频纯随机）：
    1. KOS 品牌采集：强制 intl（RedNote 港版），不走大陆通道；
    2. 当前 cn_paused=True 时，显式指定 cn 也拒绝，不得被强制参数穿透；
    3. 普通生产采集固定使用 intl，保留 last_region 参数仅用于兼容历史调用；
    4. 只有未来显式恢复内地总闸后，才允许旧的 intl/cn 轮番逻辑重新启用。

    返回 dict: {region, cdp_port, host, rotated(bool), reason}
    """
    pol = effective_policy()
    # KOS 强制 intl
    if kos_only:
        return {"region": "intl", "cdp_port": REGION_CDP_PORT["intl"],
                "host": REGION_HOST["intl"], "rotated": False,
                "reason": "kos_only: KOS品牌采集专用RedNote港版通道"}
    # 显式指定：暂停区域必须返回阻断事实，不能静默当作已接受。
    if force_region and force_region.strip().lower() in REGION_CDP_PORT:
        r = force_region.strip().lower()
        if not pol.region_allowed(r):
            return {"region": "intl", "cdp_port": REGION_CDP_PORT["intl"],
                    "host": REGION_HOST["intl"], "rotated": False,
                    "blocked": True, "requested_region": r,
                    "reason": "cn_paused: force_region=cn被生产门禁拒绝"}
        return {"region": r, "cdp_port": REGION_CDP_PORT[r],
                "host": REGION_HOST[r], "rotated": False,
                "blocked": False, "reason": f"force_region={r}"}
    # 大陆熔断 → 全部 intl
    if pol.cn_paused:
        return {"region": "intl", "cdp_port": REGION_CDP_PORT["intl"],
                "host": REGION_HOST["intl"], "rotated": False, "blocked": False,
                "reason": "cn_paused: 大陆熔断回落intl"}
    # 轮番交替：优先用外部传入的 last_region，其次进程内记忆
    prev = (last_region or _last_region_state["region"] or "").strip().lower()
    if prev == "intl":
        nxt = "cn"
    elif prev == "cn":
        nxt = "intl"
    else:
        nxt = pol.primary_region  # 首次用策略主区域
    _last_region_state["region"] = nxt
    _last_region_state["count"] += 1
    return {"region": nxt, "cdp_port": REGION_CDP_PORT[nxt],
            "host": REGION_HOST[nxt], "rotated": prev is not None and prev != "", "blocked": False,
            "reason": f"rotation: {prev or 'init'} -> {nxt}"}
