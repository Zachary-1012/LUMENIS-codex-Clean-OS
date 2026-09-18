# -*- coding: utf-8 -*-
"""Safe public-data collection contract（无公害采集契约层，ZBC 版）— 对账 P1-3 / CASE-2026-0013。

【边界 / 红线】
- 本模块**零网络、零采集客户端、零登录**：不发 HTTP、不绕过验证码/签名/设备指纹、不实现账号池或代理池。
- 它只定义任何采集器（collector_v2 / xhs_cdp_collector / rednote_collector / 未来 adapter）在采集
  *公开*数据后必须穿过的、与具体引擎解耦的离线契约：
    1. PII 脱敏 redact_text / redact_record（字段级 + 自由文本联系方式级，深拷贝不改原记录）
    2. CollectionHygienePolicy + RateGovernor（声明式只读/低频策略 + 纯限速/风险信号判定，不 sleep）
    3. build/validate_collection_audit（每批次 provenance 审计，凭证键强制剔除）
    4. run_offline_pipeline（取回之后的纯离线 shadow 管线：限速判定 → 脱敏 → 审计）
- 与现役关系：collector_guard 七态/ResponseAnalyzer 负责运行时熔断（在线）；本契约负责离线合规与证据，
  两者互补不替代。风险停止信号表与 collector_guard 对齐（300012/验证码等）。
- dual_pool（Cookie/Proxy 状态机）只允许 internal/侧端；deployment_target='public_web' 时池化/写入被硬拦截。
- 本模块为旁路新增：import 无副作用、不改变现役采集主链；未来接管须先旁路验证 + Release Gate。
设计对齐 Zachary OS AI 的 src/contracts/safe_collection.py（学契约不复制实现，schema 独立为 zbc.*）。
"""
from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, asdict
from typing import Any, Iterable, List, Tuple

AUDIT_SCHEMA = "zbc.collection-audit.v1"

# --- 1. PII redaction -------------------------------------------------------
# 作者侧身份/联系方式/精确定位字段；note_id 等内容标识刻意保留。
DEFAULT_PII_FIELDS = {
    "user_id", "userid", "uid", "user_key", "red_id", "redid",
    "xsec_token", "xsecsource", "sec_uid", "secuid",
    "nickname", "nick_name", "nick", "avatar", "avatar_url", "head_img",
    "headimage", "portrait",
    "phone", "mobile", "tel", "wechat", "weixin", "wx", "qq", "email",
    "mail", "contact",
    "ip", "ip_addr", "client_ip", "location_detail", "precise_location",
    "lat", "lng", "latitude", "longitude",
}
TEXT_FIELDS = {
    "title", "desc", "description", "content", "text", "note", "comment",
    "正文", "标题", "内容", "评论", "笔记",
}
# 凭证键永不进入审计/外发记录（与全局“不提交/不外泄 cookie/token”一致）。
CREDENTIAL_KEY_RE = re.compile(r"(cookie|token|secret|password|passwd|auth|session|api[_-]?key)", re.IGNORECASE)

_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_WECHAT_RE = re.compile(r"(?:微信|vx|v信|weixin|wechat|wx)[号:：\s]*(?:[a-zA-Z][-_a-zA-Z0-9]{5,19}|\d{6,12})", re.IGNORECASE)
_QQ_RE = re.compile(r"(?:qq|q\.q|企鹅|q号)[号:：\s]*([1-9]\d{4,11})", re.IGNORECASE)
_TEXT_PATTERNS: Tuple[Tuple[re.Pattern, str], ...] = (
    (_PHONE_RE, "phone"), (_EMAIL_RE, "email"), (_WECHAT_RE, "wechat"), (_QQ_RE, "qq"),
)


def sanitize(obj: Any) -> Any:
    """递归剔除凭证键（值替换为 [REDACTED:CREDENTIAL]），用于审计 extra 等不可信输入。"""
    if isinstance(obj, dict):
        clean = {}
        for k, v in obj.items():
            if CREDENTIAL_KEY_RE.search(str(k)):
                clean[k] = "[REDACTED:CREDENTIAL]"
            else:
                clean[k] = sanitize(v)
        return clean
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def redact_text(text: str) -> Tuple[str, int]:
    """遮蔽正文里的手机/邮箱/微信/QQ，返回 (新文本, 命中数)。短号、价格、普通数字刻意不动。"""
    if not isinstance(text, str):
        return text, 0
    hits = 0
    for pattern, label in _TEXT_PATTERNS:
        def _repl(_m, _label=label):
            nonlocal hits
            hits += 1
            return f"[REDACTED:{_label}]"
        text = pattern.sub(_repl, text)
    return text, hits


def redact_record(record: Any, pii_fields=None) -> Tuple[Any, List[str]]:
    """返回 (深拷贝的干净记录, 有序脱敏标记)。字段级 PII → [REDACTED:field]，文本字段再过 redact_text；不改原对象。"""
    pii = {f.lower() for f in (pii_fields or DEFAULT_PII_FIELDS)}
    hits: List[str] = []

    def walk(obj):
        if isinstance(obj, dict):
            clean = {}
            for key, value in obj.items():
                kl = str(key).lower()
                if kl in pii:
                    clean[key] = f"[REDACTED:{kl}]"
                    hits.append(kl)
                elif kl in TEXT_FIELDS and isinstance(value, str):
                    new_text, n = redact_text(value)
                    clean[key] = new_text
                    if n:
                        hits.extend([f"{kl}:text"] * n)
                else:
                    clean[key] = walk(value)
            return clean
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        return obj

    return walk(copy.deepcopy(record)), hits


# --- 2. Hygiene policy + pure rate/risk decisions ---------------------------
MIN_INTERVAL_FLOOR = 2.0
DEFAULT_MIN_INTERVAL = 3.0
DEFAULT_DAILY_CAP = 200
DEFAULT_MAX_BATCH = 20

# 与 collector_guard 七态/analyzer 对齐的风控停止信号（XHS 300012、验证码等）。
RISK_STOP_SIGNALS = {
    "300012", "captcha", "slider", "click_captcha", "verify_code",
    "login_expired", "throttled", "empty_throttle", "blocked", "banned",
    "ip_risk_or_300012", "need_verify", "auth_required",
}
AUDIT_STATUSES = {"completed", "partial", "stopped_risk", "aborted"}


@dataclass
class CollectionHygienePolicy:
    """声明式无公害采集策略，默认值即最安全路径。"""
    platform: str = "xiaohongshu"
    read_only: bool = True
    public_data_only: bool = True
    single_local_account: bool = True
    allow_account_pool: bool = False
    allow_proxy_pool: bool = False
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL
    daily_cap: int = DEFAULT_DAILY_CAP
    max_batch: int = DEFAULT_MAX_BATCH
    stop_on_risk_signal: bool = True
    write_enabled: bool = False
    human_confirmation_required_for_write: bool = True
    deployment_target: str = "internal"  # internal | public_web

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.read_only:
            errors.append("read_only_must_hold")
        if not self.public_data_only:
            errors.append("public_data_only_required")
        if not self.single_local_account:
            errors.append("single_local_account_required")
        if self.allow_account_pool:
            errors.append("account_pool_forbidden")
        if self.allow_proxy_pool:
            errors.append("proxy_pool_forbidden")
        if self.min_interval_seconds < MIN_INTERVAL_FLOOR:
            errors.append(f"min_interval_below_{MIN_INTERVAL_FLOOR}s")
        if self.daily_cap <= 0:
            errors.append("daily_cap_must_be_positive")
        if self.max_batch <= 0:
            errors.append("max_batch_must_be_positive")
        if self.write_enabled and not self.human_confirmation_required_for_write:
            errors.append("write_requires_human_confirmation")
        if self.deployment_target not in {"internal", "public_web"}:
            errors.append("invalid_deployment_target")
        if self.deployment_target == "public_web" and (
            self.allow_account_pool or self.allow_proxy_pool
            or self.write_enabled or not self.read_only
        ):
            errors.append("public_web_forbids_pooling_and_write")
        return errors

    def is_safe(self) -> bool:
        return not self.validate()

    def snapshot(self) -> dict:
        return asdict(self)


class RateGovernor:
    """纯限速/风险判定，不 sleep，时钟可注入。"""
    def __init__(self, policy: CollectionHygienePolicy):
        self.policy = policy

    def permit(self, now: float, last_action_ts) -> Tuple[bool, float]:
        if last_action_ts is None:
            return True, 0.0
        elapsed = now - last_action_ts
        if elapsed + 1e-9 >= self.policy.min_interval_seconds:
            return True, 0.0
        return False, max(0.0, self.policy.min_interval_seconds - elapsed)

    def within_daily_cap(self, used_today: int, planned: int = 1) -> bool:
        return used_today + planned <= self.policy.daily_cap

    def within_batch(self, batch_size: int) -> bool:
        return batch_size <= self.policy.max_batch

    def assess_risk_signal(self, signal: str) -> str:
        if not signal:
            return "continue"
        norm = str(signal).strip().lower()
        if norm in RISK_STOP_SIGNALS and self.policy.stop_on_risk_signal:
            return "stop"
        return "continue"


# --- 3. Collection audit / provenance --------------------------------------
_AUDIT_REQUIRED = (
    "audit_id", "schema", "timestamp", "platform", "keyword",
    "requested_count", "returned_count", "redacted_count",
    "collector_name", "operator", "human_triggered", "read_only",
    "policy_snapshot", "status",
)


def build_collection_audit(*, keyword: str, requested_count: int, returned_count: int,
                           redacted_count: int, collector_name: str, operator: str,
                           policy: CollectionHygienePolicy, human_triggered: bool = True,
                           status: str = "completed", risk_signals=None,
                           started_at: str = "", finished_at: str = "",
                           collector_version: str = "", source_sha: str = "", extra=None) -> dict:
    record = {
        "schema": AUDIT_SCHEMA,
        "audit_id": uuid.uuid4().hex,
        "timestamp": finished_at or started_at,
        "started_at": started_at,
        "finished_at": finished_at,
        "platform": policy.platform,
        "keyword": keyword,
        "requested_count": requested_count,
        "returned_count": returned_count,
        "redacted_count": redacted_count,
        "collector_name": collector_name,
        "collector_version": collector_version,
        "source_sha": source_sha,
        "operator": operator,
        "human_triggered": human_triggered,
        "read_only": policy.read_only,
        "policy_snapshot": policy.snapshot(),
        "risk_signals": risk_signals or [],
        "status": status,
    }
    if extra:
        record["extra"] = sanitize(extra)  # 防御：凭证绝不搭车进审计
    return record


def validate_collection_audit(record: dict) -> List[str]:
    errors: List[str] = []
    for key in _AUDIT_REQUIRED:
        if record.get(key) is None or record.get(key) == "":
            if key == "started_at":
                continue
            errors.append(f"missing:{key}")
    if record.get("status") not in AUDIT_STATUSES:
        errors.append(f"invalid:status ({record.get('status')})")
    for num_key in ("requested_count", "returned_count", "redacted_count"):
        val = record.get(num_key)
        if not isinstance(val, int) or val < 0:
            errors.append(f"invalid:{num_key}")
    if isinstance(record.get("human_triggered"), bool) and not record["human_triggered"]:
        if not (record.get("extra") or {}).get("automation_justification"):
            errors.append("non_human_triggered_requires_justification")
    return errors


# --- 4. Offline shadow pipeline (no network) --------------------------------
def run_offline_pipeline(raw_records: Iterable[dict], *, keyword: str, collector_name: str,
                         operator: str, policy: CollectionHygienePolicy = None,
                         requested_count: int = None, human_triggered: bool = True,
                         now: float = None, last_action_ts: float = None,
                         risk_signals=None, started_at: str = "", finished_at: str = "",
                         pii_fields=None) -> dict:
    """纯离线：限速判定 → 逐条脱敏 → 审计。不联网、不 sleep、不改原始对象。

    返回 {allowed, wait_seconds, records, redacted_total, audit, audit_errors, stopped_risk}。
    """
    policy = policy or CollectionHygienePolicy()
    gov = RateGovernor(policy)
    now_ts = now if now is not None else 0.0
    allowed, wait = gov.permit(now_ts, last_action_ts)

    stopped = [s for s in (risk_signals or []) if gov.assess_risk_signal(s) == "stop"]
    raws = list(raw_records)
    clean_records, redacted_total = [], 0
    if allowed and not stopped:
        for r in raws:
            cleaned, marks = redact_record(r, pii_fields=pii_fields)
            redacted_total += len(marks)
            clean_records.append(cleaned)

    if stopped:
        status = "stopped_risk"
    elif len(clean_records) < len(raws) or (requested_count and len(clean_records) < requested_count):
        status = "partial"
    else:
        status = "completed"

    audit = build_collection_audit(
        keyword=keyword, requested_count=requested_count if requested_count is not None else len(raws),
        returned_count=len(clean_records), redacted_count=redacted_total,
        collector_name=collector_name, operator=operator, policy=policy,
        human_triggered=human_triggered, status=status, risk_signals=risk_signals or [],
        started_at=started_at, finished_at=finished_at)
    return {
        "allowed": allowed, "wait_seconds": round(wait, 3),
        "records": clean_records, "redacted_total": redacted_total,
        "audit": audit, "audit_errors": validate_collection_audit(audit),
        "stopped_risk": stopped,
    }
