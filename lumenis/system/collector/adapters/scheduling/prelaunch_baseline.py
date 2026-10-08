"""Deterministic due policy for explicitly authorized prelaunch public baselines.

This module decides *when* an existing SYSTEM Collector plan is eligible. It
does not fetch sources, enable end-user AUTO, or persist Canonical/Evidence.
The caller must supply the durable attempt history from the existing run store.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Optional
from urllib.parse import parse_qsl, urlsplit


MAX_DUE_ATTEMPTS_PER_TICK = 8
PURPOSE_POLICY = "purpose-query-read-only-exact-import-v1"
PURPOSE_PLATFORMS = frozenset({"xhs", "douyin", "x", "instagram", "facebook", "wechat"})


@dataclass(frozen=True)
class PublicBaselinePlan:
    """Versioned authorization for one exact public source and collection scope."""

    source_key: str
    source_version: str
    exact_scope: str
    scope_version: str
    cadence_seconds: int
    authorization_ref: str
    enabled: bool = False
    prelaunch_authorized: bool = False
    end_user_auto: bool = False
    platform: str = "public_http"
    source_url: str = ""
    domain_id: str = ""
    subject_id: Optional[str] = None
    brand_focus_id: Optional[str] = None
    max_results: int = 20
    plan_version: str = "1"
    policy_id: str = "public-read-only-exact-import-v1"
    _signed_config_digest: str = field(default="", repr=False, compare=False)
    purpose_query: Optional[dict] = None
    internal_auto_opt_in: bool = False

    def __post_init__(self) -> None:
        for name in ("source_key", "source_version", "exact_scope", "scope_version",
                     "authorization_ref"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be an explicit non-empty value")
        if (len(self.source_key) > 180 or len(self.source_version) > 64
                or len(self.exact_scope) > 2048 or len(self.scope_version) > 64
                or len(self.authorization_ref) > 200):
            raise ValueError("baseline plan identity fields exceed limits")
        if any(token in self.exact_scope for token in ("*", "?")):
            raise ValueError("exact_scope must not contain wildcards")
        if not 60 <= self.cadence_seconds <= 31 * 24 * 60 * 60:
            raise ValueError("cadence_seconds must be between one minute and 31 days")
        if self.end_user_auto:
            raise ValueError("prelaunch baseline must not enable end-user AUTO")
        if self.policy_id not in {"public-read-only-exact-import-v1", PURPOSE_POLICY}:
            raise ValueError("unsupported baseline permission policy")
        purpose = self.policy_id == PURPOSE_POLICY
        if purpose:
            if self.platform not in PURPOSE_PLATFORMS or self.internal_auto_opt_in is not True:
                raise ValueError("purpose baseline requires an explicitly approved internal platform")
            if not isinstance(self.purpose_query, dict):
                raise ValueError("a full source-derived purpose query is required")
            query = _purpose_query(self.purpose_query)
            context = query.business_context or {}
            from ...acquisition_plan import _validate_publication_period
            _validate_publication_period(context.get("publication_since"), context.get("publication_until"))
            if (query.keyword != self.source_url or not 1 <= len(query.keyword) <= 256
                    or context.get("platform") not in {self.platform, "xiaohongshu" if self.platform == "xhs" else self.platform}
                    or query.subject_id != self.subject_id or query.brand_focus_id != self.brand_focus_id
                    or ("cth" if query.domain_id == "CTH" else "bmp") != self.domain_id):
                raise ValueError("purpose query must bind exact plan identity, scope and requested period")
        elif self.platform not in {"public_http", "web_atom"} or self.purpose_query is not None or self.internal_auto_opt_in:
            raise ValueError("public policy does not grant purpose-query AUTO")
        if self.source_url and not purpose:
            parts = urlsplit(self.source_url)
            if (len(self.source_url) > 2048 or any(ch.isspace() for ch in self.source_url)
                    or parts.scheme != "https" or not parts.hostname or parts.username
                    or parts.password or parts.fragment):
                raise ValueError("source_url must be an exact public HTTPS URL")
            sensitive_query_keys = {"token", "access_token", "api_key", "key", "auth",
                                    "authorization", "cookie", "session", "secret"}
            if any(name.lower() in sensitive_query_keys for name, _ in parse_qsl(parts.query)):
                raise ValueError("source_url must not contain credentials")
            host = parts.hostname.lower().rstrip(".")
            if host == "youtube.com" or host.endswith(".youtube.com") or host == "youtu.be" or host.endswith(".youtu.be"):
                raise ValueError("YouTube collection is not allowed")
        if not 1 <= self.max_results <= 20:
            raise ValueError("max_results must be between 1 and 20")
        if not isinstance(self.max_results, int) or isinstance(self.max_results, bool):
            raise ValueError("max_results must be an integer")
        if not isinstance(self.cadence_seconds, int) or isinstance(self.cadence_seconds, bool):
            raise ValueError("cadence_seconds must be an integer")
        if (self.domain_id not in {"", "cth", "bmp"}
                or (self.subject_id is not None and (not isinstance(self.subject_id, str) or not self.subject_id))
                or (self.brand_focus_id is not None and (not isinstance(self.brand_focus_id, str) or not self.brand_focus_id))
                or (self.domain_id == "cth" and (not self.subject_id or self.brand_focus_id is not None))
                or (self.domain_id == "bmp" and (not self.brand_focus_id or self.subject_id is not None))):
            raise ValueError("exact CTH Subject or BMP BrandFocus scope required")

    @property
    def plan_id(self) -> str:
        """Stable identity changes when source, scope, cadence, or authority changes."""
        payload = {
            "source_key": self.source_key,
            "source_version": self.source_version,
            "exact_scope": self.exact_scope,
            "scope_version": self.scope_version,
            "cadence_seconds": self.cadence_seconds,
            "authorization_ref": self.authorization_ref,
            "platform": self.platform,
            "source_url": self.source_url,
            "domain_id": self.domain_id,
            "subject_id": self.subject_id,
            "brand_focus_id": self.brand_focus_id,
            "max_results": self.max_results,
            "plan_version": self.plan_version,
            "policy_id": self.policy_id,
        }
        if self.policy_id == PURPOSE_POLICY:
            payload.update(purpose_query=self.purpose_query, internal_auto_opt_in=self.internal_auto_opt_in)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _purpose_query(value):
    from ...acquisition_plan import AcquisitionQuery
    names = ("keyword", "domain_id", "product_id", "registry_id", "subject_id",
             "brand_focus_id", "priority", "reason_code", "alias_kind",
             "context_mode", "business_context")
    if not isinstance(value, dict):
        raise ValueError("purpose query must be an object")
    return AcquisitionQuery(**{name: value[name] for name in names if name in value})


def round_robin_due(evaluated, limit=MAX_DUE_ATTEMPTS_PER_TICK):
    """Use durable oldest-due ordering while rotating platforms within a tick."""
    from collections import deque
    groups = {}
    for row in sorted(evaluated, key=lambda r: (r[0], r[1], r[2])):
        groups.setdefault(row[3].platform, deque()).append(row)
    selected = []
    while any(groups.values()) and len(selected) < limit:
        for rows in groups.values():
            if rows and len(selected) < limit:
                selected.append(rows.popleft())
    return selected


@dataclass(frozen=True)
class BaselineRunHistory:
    """Durable run facts loaded from the existing collector run store."""

    last_attempt_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    consecutive_failures: int = 0
    attempt_in_progress: bool = False


@dataclass(frozen=True)
class BaselineDueDecision:
    due: bool
    reason: str
    due_at: Optional[datetime]
    plan_id: str


def evaluate_baseline_due(
    plan: PublicBaselinePlan,
    history: BaselineRunHistory,
    *,
    now: datetime,
    retry_base_seconds: int = 300,
    retry_cap_seconds: int = 6 * 60 * 60,
) -> BaselineDueDecision:
    """Evaluate without side effects; a caller must durably claim before execution."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    pid = plan.plan_id
    if not plan.enabled:
        return BaselineDueDecision(False, "DISABLED", None, pid)
    if not plan.prelaunch_authorized:
        return BaselineDueDecision(False, "AUTHORIZATION_REQUIRED", None, pid)
    if history.attempt_in_progress:
        return BaselineDueDecision(False, "ATTEMPT_IN_PROGRESS", None, pid)
    if retry_base_seconds < 1 or retry_cap_seconds < retry_base_seconds:
        raise ValueError("invalid retry backoff bounds")

    # A failure is retried from last_attempt using capped exponential backoff.
    if history.consecutive_failures:
        failed_at = history.last_failure_at or history.last_attempt_at
        if failed_at is None:
            return BaselineDueDecision(False, "HISTORY_INCOMPLETE", None, pid)
        delay = min(retry_base_seconds * (2 ** min(history.consecutive_failures - 1, 30)),
                    retry_cap_seconds)
        due_at = failed_at + timedelta(seconds=delay)
        return BaselineDueDecision(now >= due_at, "RETRY_DUE" if now >= due_at else "RETRY_BACKOFF", due_at, pid)

    # First run starts immediately. Later successful runs use cadence from the
    # last success; an attempt without a known outcome fails closed.
    if history.last_attempt_at and not history.last_success_at:
        return BaselineDueDecision(False, "OUTCOME_UNKNOWN", None, pid)
    if history.last_success_at is None:
        return BaselineDueDecision(True, "FIRST_RUN", now, pid)
    due_at = history.last_success_at + timedelta(seconds=plan.cadence_seconds)
    return BaselineDueDecision(now >= due_at, "CADENCE_DUE" if now >= due_at else "NOT_DUE", due_at, pid)


def _verified_source_refresh(result: Any) -> tuple[bool, str]:
    """Require source rows, Evidence, and explicit canonical refresh proof."""
    if not isinstance(result, dict) or result.get("ok") is not True:
        return False, str(result.get("status") or "SOURCE_UNAVAILABLE") if isinstance(result, dict) else "INVALID_RESULT"
    try:
        records = int(result.get("returned_count", 0))
        canonical = int(result.get("canonical_synced", 0))
    except (TypeError, ValueError):
        return False, "CANONICAL_REFRESH_UNVERIFIED"
    # A reachable exact source can legitimately have no delta.  Treat that
    # result as an idempotent maintenance success only when the collector has
    # persisted Evidence and explicitly verified the unchanged scope.
    if (
        str(result.get("status") or "") == "NO_NEW_DATA"
        and records == 0
        and canonical == 0
        and result.get("evidence_recorded") is True
        and result.get("refresh_verified") is True
        and result.get("scope_status") == "VERIFIED"
    ):
        return True, "NO_NEW_DATA"
    if records <= 0:
        return False, "NO_SOURCE_RESULT"
    if result.get("evidence_recorded") is not True:
        return False, "EVIDENCE_WRITE_FAILED"
    if (result.get("refresh_verified") is not True
            or result.get("scope_status") != "VERIFIED"
            or canonical != records):
        return False, "REFRESH_UNVERIFIED"
    return True, str(result.get("status") or "SUCCESS")


def run_due_public_baseline(plan: PublicBaselinePlan, store: Any, *,
                            now: datetime, execute: Callable[[], Any],
                            finish_now: Optional[Callable[[], datetime]] = None):
    """Claim once, execute one existing SYSTEM Collector plan, and persist outcome.

    ``execute`` must call the already-approved bounded collector path and return
    its result mapping. This function never chooses sources, scope, or Permission.
    """
    if not plan._signed_config_digest:
        decision = BaselineDueDecision(False, "HMAC_UNAVAILABLE", None, plan.plan_id)
        return {"decision": decision, "attempt_id": None, "result": None,
                "status": "HMAC_UNAVAILABLE"}
    attempt_id, decision = store.claim_public_baseline_attempt(plan, now=now)
    if attempt_id is None:
        return {"decision": decision, "attempt_id": None, "result": None}
    try:
        result = execute()
        success, status = _verified_source_refresh(result)
        finished_at = (finish_now or (lambda: datetime.now(tz=now.tzinfo)))()
        stored = store.finish_public_baseline_attempt(
            plan, attempt_id, success=success, now=finished_at,
            error_code=None if success else status[:80],
        )
        persisted = stored is True
        terminal_status = status if persisted else "OUTCOME_PERSISTENCE_FAILED"
        return {"decision": decision, "attempt_id": attempt_id,
                "result": result, "persisted": persisted, "status": terminal_status}
    except Exception as exc:
        store.finish_public_baseline_attempt(
            plan, attempt_id, success=False,
            now=(finish_now or (lambda: datetime.now(tz=now.tzinfo)))(),
            error_code=type(exc).__name__[:80],
        )
        raise


class BaselineConfigError(ValueError):
    """Non-secret, stable reason a configured baseline cannot execute."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PrelaunchMaintenanceAuthorization:
    """Typed authorization token produced only by the signed plan loader."""

    plan_id: str
    source_url: str
    platform: str
    domain_id: str
    subject_id: Optional[str]
    brand_focus_id: Optional[str]
    source_version: str
    scope_version: str
    cadence_seconds: int
    authorization_ref: str
    policy_id: str
    signature_verified: bool = field(default=False, repr=False)

    def matches(self, plan: PublicBaselinePlan, *, source_url: str,
                platform: str, scope: dict) -> bool:
        from ..platform_naming import normalize_platform
        return (
            self.signature_verified is True
            and self.plan_id == plan.plan_id
            and self.source_url == source_url == plan.source_url
            and normalize_platform(self.platform) == normalize_platform(platform) == normalize_platform(plan.platform)
            and self.domain_id == scope.get("domain_id") == plan.domain_id
            and self.subject_id == scope.get("subject_id") == plan.subject_id
            and self.brand_focus_id == scope.get("brand_focus_id") == plan.brand_focus_id
            and self.source_version == plan.source_version
            and self.scope_version == plan.scope_version
            and self.cadence_seconds == plan.cadence_seconds
            and self.authorization_ref == plan.authorization_ref
            and self.policy_id == plan.policy_id
        )

    def matches_request(self, *, source_url: str, platform: str, scope: dict) -> bool:
        from ..platform_naming import normalize_platform
        return (
            self.signature_verified is True
            and bool(re.fullmatch(r"[0-9a-f]{64}", self.plan_id))
            and self.source_url == source_url
            and normalize_platform(self.platform) == normalize_platform(platform)
            and self.domain_id == scope.get("domain_id")
            and self.subject_id == scope.get("subject_id")
            and self.brand_focus_id == scope.get("brand_focus_id")
            and bool(self.source_version and self.scope_version and self.authorization_ref)
            and self.policy_id in {"public-read-only-exact-import-v1", PURPOSE_POLICY}
            and 60 <= self.cadence_seconds <= 31 * 24 * 60 * 60
        )


def _canonical_config(config: dict) -> bytes:
    unsigned = {k: v for k, v in config.items() if k != "hmac"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_prelaunch_baseline_config(path: Optional[str] = None, *,
                                   hmac_key: Optional[str] = None):
    """Load the one versioned config; enabled plans require an HMAC signature."""
    configured_path = path or os.environ.get("LUMENIS_PRELAUNCH_BASELINE_CONFIG")
    config_path = (Path(configured_path) if configured_path else
                   Path(__file__).resolve().parents[5] / "config" / "prelaunch_public_baseline.json")
    try:
        if config_path.stat().st_size > 4 * 1024 * 1024:
            raise BaselineConfigError("CONFIG_TOO_LARGE")
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except BaselineConfigError:
        raise
    except FileNotFoundError:
        return {"status": "DISABLED", "plans": []}
    except (OSError, json.JSONDecodeError):
        raise BaselineConfigError("CONFIG_UNAVAILABLE") from None
    if not isinstance(config, dict) or config.get("schema_version") != 1:
        raise BaselineConfigError("CONFIG_SCHEMA_INVALID")
    if config.get("enabled") is not True:
        return {"status": "DISABLED", "plans": []}
    if config.get("end_user_auto") is not False:
        raise BaselineConfigError("END_USER_AUTO_MUST_REMAIN_OFF")
    if config.get("policy_id") not in {"public-read-only-exact-import-v1", PURPOSE_POLICY}:
        raise BaselineConfigError("POLICY_UNSUPPORTED")
    if config.get("policy_id") == PURPOSE_POLICY and config.get("internal_auto_opt_in") is not True:
        raise BaselineConfigError("INTERNAL_AUTO_OPT_IN_REQUIRED")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        raise BaselineConfigError("SOURCE_SET_INVALID")
    key = hmac_key if hmac_key is not None else os.environ.get("LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY", "")
    signature = config.get("hmac")
    if not key or not isinstance(signature, dict):
        raise BaselineConfigError("HMAC_UNAVAILABLE")
    if signature.get("algorithm") != "HMAC-SHA256" or not isinstance(signature.get("value"), str):
        raise BaselineConfigError("HMAC_INVALID")
    expected = hmac.new(key.encode("utf-8"), _canonical_config(config), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature["value"]):
        raise BaselineConfigError("HMAC_MISMATCH")
    version = config.get("plan_version")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", version):
        raise BaselineConfigError("PLAN_VERSION_INVALID")
    digest = hashlib.sha256(_canonical_config(config)).hexdigest()
    plans = []
    seen = set()
    for source in sources:
        if not isinstance(source, dict):
            raise BaselineConfigError("SOURCE_ENTRY_INVALID")
        source_plan_version = source.get("plan_version", version)
        if not isinstance(source_plan_version, str) or not re.fullmatch(
                r"[A-Za-z0-9._-]{1,64}", source_plan_version):
            raise BaselineConfigError("SOURCE_PLAN_VERSION_INVALID")
        try:
            plan = PublicBaselinePlan(
                source_key=source["source_key"],
                source_version=source["source_version"],
                exact_scope=json.dumps({k: source.get(k) for k in
                    ("domain_id", "subject_id", "brand_focus_id")}, sort_keys=True, separators=(",", ":")),
                scope_version=source["scope_version"],
                cadence_seconds=source["cadence_seconds"],
                authorization_ref=source["authorization_ref"],
                enabled=True,
                prelaunch_authorized=True,
                end_user_auto=False,
                platform=source["platform"],
                source_url=source["source_url"],
                domain_id=source["domain_id"],
                subject_id=source.get("subject_id"),
                brand_focus_id=source.get("brand_focus_id"),
                max_results=source.get("max_results", 20),
                plan_version=source_plan_version,
                policy_id=config["policy_id"],
                _signed_config_digest=digest,
                purpose_query=source.get("purpose_query"),
                internal_auto_opt_in=config.get("internal_auto_opt_in", False),
            )
        except (KeyError, TypeError, ValueError):
            raise BaselineConfigError("SOURCE_ENTRY_INVALID") from None
        if not plan._signed_config_digest or plan.plan_id in seen:
            raise BaselineConfigError("SOURCE_ENTRY_DUPLICATE")
        seen.add(plan.plan_id)
        plans.append(plan)
    return {"status": "READY", "plan_version": version, "plans": plans,
            "signature_verified": True}


def maintenance_authorization(plan: PublicBaselinePlan) -> PrelaunchMaintenanceAuthorization:
    if not plan._signed_config_digest:
        raise BaselineConfigError("HMAC_UNAVAILABLE")
    return PrelaunchMaintenanceAuthorization(
        plan_id=plan.plan_id, source_url=plan.source_url, platform=plan.platform,
        domain_id=plan.domain_id, subject_id=plan.subject_id,
        brand_focus_id=plan.brand_focus_id, source_version=plan.source_version,
        scope_version=plan.scope_version, cadence_seconds=plan.cadence_seconds,
        authorization_ref=plan.authorization_ref, policy_id=plan.policy_id,
        signature_verified=True,
    )


def run_due_prelaunch_baseline(*, now: Optional[datetime] = None,
                               config_path: Optional[str] = None,
                               hmac_key: Optional[str] = None,
                               store: Any = None,
                               collect: Optional[Callable[..., Any]] = None,
                               finish_now: Optional[Callable[[], datetime]] = None):
    """Scheduler entry: signed exact plans only; isolate each source failure."""
    try:
        loaded = load_prelaunch_baseline_config(config_path, hmac_key=hmac_key)
    except BaselineConfigError as exc:
        return {"status": "FAILED", "reason": exc.code, "runs": []}
    if loaded["status"] == "DISABLED":
        return {"status": "DISABLED", "runs": []}
    if store is None:
        from . import get_planner
        store = get_planner().store
    if store is None:
        return {"status": "FAILED", "reason": "SCHEDULE_STORE_UNAVAILABLE", "runs": []}
    if collect is None:
        from ..secondary_collection import collect_search
        collect = collect_search
    now = now or datetime.now().astimezone()
    evaluated = []
    not_due = []
    purpose_platform_backoff = {}
    for order, plan in enumerate(loaded["plans"]):
        history = store.public_baseline_history(plan)
        decision = evaluate_baseline_due(plan, history, now=now)
        if plan.policy_id == PURPOSE_POLICY and decision.reason == "RETRY_BACKOFF":
            purpose_platform_backoff[plan.platform] = max(
                purpose_platform_backoff.get(plan.platform, now), decision.due_at or now)
        expired_claim = (history.attempt_in_progress and history.last_attempt_at is not None
                         and now >= history.last_attempt_at + timedelta(hours=1))
        # The atomic claim owner expires abandoned workers and records backoff.
        # Filtering RUNNING rows here would prevent that recovery after restart.
        if decision.due or expired_claim:
            evaluated.append((decision.due_at or now, plan.plan_id, order, plan, decision))
        else:
            not_due.append((plan, decision))
    # Bound actual source attempts per scheduler tick, while allowing the signed
    # baseline to cover the full approved inventory. Oldest due sources go first.
    evaluated.sort(key=lambda row: (row[0], row[1], row[2]))
    selected = round_robin_due(evaluated)
    selected_ids = {row[1] for row in selected}
    results = []
    blocked_platforms = set(purpose_platform_backoff)
    selected_order = {row[1]: i for i, row in enumerate(selected)}
    for decision_at, plan_id, order, plan, decision in sorted(
            evaluated, key=lambda row: selected_order.get(row[1], len(selected))):
        if plan.policy_id == PURPOSE_POLICY and plan.platform in blocked_platforms:
            results.append({"plan_id": plan.plan_id, "attempt_id": None,
                            "status": "PLATFORM_BACKOFF", "platform": plan.platform})
            continue
        if plan_id not in selected_ids:
            results.append({"decision": decision, "attempt_id": None,
                            "status": "BATCH_DEFERRED"})
            continue
        scope = {"domain_id": plan.domain_id, "subject_id": plan.subject_id,
                 "brand_focus_id": plan.brand_focus_id}
        auth = maintenance_authorization(plan)
        def execute(plan=plan, scope=scope, auth=auth):
            def collect_once():
                options = {}
                if plan.policy_id == PURPOSE_POLICY:
                    options["business_query"] = _purpose_query(plan.purpose_query)
                return collect(
                    plan.platform, plan.source_url, max_results=plan.max_results,
                    operator="prelaunch_maintenance", scope=scope,
                    prelaunch_local_import=True, prelaunch_authorization=auth,
                    **options,
                )

            result = collect_once()
            if (isinstance(result, dict)
                    and result.get("status") == "RATE_LIMITED"
                    and result.get("error_type") == "LOCAL_RATE_LIMIT"
                    and result.get("network_attempted") is not True
                    and result.get("persistence_attempted") is not True):
                wait_seconds = result.get("wait_seconds")
                if (isinstance(wait_seconds, (int, float))
                        and not isinstance(wait_seconds, bool)
                        and 0 < wait_seconds <= 60
                        and math.isfinite(wait_seconds)):
                    time.sleep(wait_seconds + 0.1)
                    return collect_once()
            return result
        try:
            item = run_due_public_baseline(
                plan, store, now=now, execute=execute, finish_now=finish_now,
            )
            if item.get("attempt_id") is None:
                item["status"] = item["decision"].reason
            elif item.get("persisted") is not True:
                item["status"] = "OUTCOME_PERSISTENCE_FAILED"
            else:
                result = item.get("result")
                success, status = _verified_source_refresh(result)
                item["status"] = "SUCCESS" if success else status
            if (plan.policy_id == PURPOSE_POLICY and item.get("status") in {
                    "NEED_VERIFY", "BLOCKED", "RISK_WARNING", "SESSION_EXPIRED",
                    "AUTH_REQUIRED", "NOT_CONFIGURED", "COOLING_DOWN", "RATE_LIMITED"}):
                blocked_platforms.add(plan.platform)
            results.append(item)
        except Exception as exc:
            results.append({"plan_id": plan.plan_id, "status": "FAILED",
                            "error_type": type(exc).__name__})
    results.extend({"plan_id": plan.plan_id, "decision": decision,
                    "attempt_id": None, "status": decision.reason}
                   for plan, decision in not_due)
    statuses = [str(item.get("status") or "FAILED") for item in results]
    deferred_statuses = {"NOT_DUE", "ATTEMPT_IN_PROGRESS", "RETRY_BACKOFF",
                         "BATCH_DEFERRED", "PLATFORM_BACKOFF", "FIRST_RUN", "DISABLED"}
    deferred = sum(status in deferred_statuses for status in statuses)
    failed = sum(status != "SUCCESS" and status not in deferred_statuses
                 for status in statuses)
    succeeded = sum(status == "SUCCESS" for status in statuses)
    overall = "FAILED" if failed == len(results) else "PARTIAL" if failed else "COMPLETED"
    return {"status": overall, "plan_version": loaded["plan_version"],
            "summary": {"succeeded": succeeded, "failed": failed,
                        "deferred": deferred,
                        "due_batch": {
                            "eligible_source_count": len(evaluated),
                            "selected_source_count": len(selected),
                            "limit_per_tick": MAX_DUE_ATTEMPTS_PER_TICK,
                            "deferred_source_count": len(evaluated) - len(selected),
                        }},
            "runs": results}



def purpose_baseline_config(query_pages, *, source_version, scope_version,
                            authorization_ref, cadence_seconds=3600, plan_version="1"):
    """Serialize all compiled purpose pages for owner signing, without granting AUTO."""
    import dataclasses
    from ..platform_naming import normalize_platform
    if not isinstance(query_pages, (list, tuple)) or not query_pages:
        raise ValueError("nonempty compiled pages are required")
    source_entries = []
    seen = set()
    for page in query_pages:
        if not isinstance(page, dict) or page.get("status") != "READY":
            raise ValueError("only actual READY planner pages may be serialized")
        for value in page.get("queries", []):
            query = _purpose_query(value)
            platform = normalize_platform(query.business_context.get("platform"))
            if platform == "xiaohongshu":
                platform = "xhs"
            if platform not in PURPOSE_PLATFORMS:
                raise ValueError("unsupported purpose baseline platform")
            identity = hashlib.sha256(json.dumps(query.to_dict(), sort_keys=True,
                ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
            if identity in seen:
                continue
            seen.add(identity)
            domain = "cth" if query.domain_id == "CTH" else "bmp"
            scope = {"domain_id":domain,"subject_id":query.subject_id,"brand_focus_id":query.brand_focus_id}
            plan = PublicBaselinePlan(
                source_key=platform+":"+identity, source_version=source_version,
                exact_scope=json.dumps(scope,sort_keys=True,separators=(",",":")),
                scope_version=scope_version,cadence_seconds=cadence_seconds,
                authorization_ref=authorization_ref,platform=platform,source_url=query.keyword,
                domain_id=domain,subject_id=query.subject_id,brand_focus_id=query.brand_focus_id,
                plan_version=plan_version,policy_id=PURPOSE_POLICY,
                purpose_query=query.to_dict(),internal_auto_opt_in=True)
            source_entries.append({
                name:getattr(plan,name) for name in (
                    "source_key","source_version","scope_version","cadence_seconds",
                    "authorization_ref","platform","source_url","domain_id",
                    "subject_id","brand_focus_id","max_results","plan_version","purpose_query")
            })
    if not source_entries:
        raise ValueError("no purpose queries survived serialization")
    # The existing Permission owner reviews the exact actor/scope/use and signs
    # the final enabled config. This serialized candidate cannot execute itself.
    return {"schema_version":1,"enabled":False,"end_user_auto":False,
            "internal_auto_opt_in":True,"policy_id":PURPOSE_POLICY,
            "plan_version":plan_version,"sources":source_entries,
            "hmac":None,"admission_state":"OWNER_SCOPE_AND_SIGNATURE_PENDING"}
