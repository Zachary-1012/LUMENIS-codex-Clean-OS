"""Deterministic due policy for explicitly authorized prelaunch public baselines.

This module decides *when* an existing SYSTEM Collector plan is eligible. It
does not fetch sources, enable end-user AUTO, or persist Canonical/Evidence.
The caller must supply the durable attempt history from the existing run store.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import hmac
import json
import math
import sqlite3
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Optional
from urllib.parse import parse_qsl, urlsplit


MAX_DUE_ATTEMPTS_PER_TICK = 8
MAX_REGISTRY_EXPANSION_TARGETS = 5000
MAX_REGISTRY_EXPANSION_QUERIES = 100000
MAX_REGISTRY_EXPANSION_PAGES = 2000
MAX_REGISTRY_SNAPSHOT_RETRIES = 3
PUBLIC_POLICY = "public-read-only-exact-import-v1"
PURPOSE_POLICY = "purpose-query-read-only-exact-import-v1"
BASELINE_POLICIES = frozenset({PUBLIC_POLICY, PURPOSE_POLICY})
PURPOSE_PLATFORMS = frozenset({"xhs", "douyin", "x", "instagram", "facebook", "wechat"})
POST_INTAKE_KEYWORD_POLICY = {
    "policy_id": "internal-collected-keyword-candidates-v1",
    "processing_version": "deterministic-collector-keywords:v1",
    "authority_ref": "00-GOVERNANCE/evidence/approvals/PO-20261008-REAL-OUTCOME-POLICY-C1-RESUME.json#/scope_manifest/C1_subject_batch_postanalysis_single_cover/post_intake_purpose_implementation",
    "purpose": "INTERNAL_KEYWORD_TOPIC_CANDIDATES",
    "actions": ("READ", "ANALYZE", "DERIVED_SAVE"),
}


def _validated_post_intake_policy(value: Any, *, baseline_policy: str) -> Optional[dict]:
    """Accept only the exact signed internal keyword-candidate use policy."""
    if value is None:
        return None
    if baseline_policy != PURPOSE_POLICY or type(value) is not dict:
        raise ValueError("post-intake policy is unsupported for this baseline")
    expected_keys = set(POST_INTAKE_KEYWORD_POLICY)
    if set(value) != expected_keys:
        raise ValueError("post-intake policy fields are invalid")
    for key in ("policy_id", "processing_version", "authority_ref", "purpose"):
        if type(value.get(key)) is not str or value[key] != POST_INTAKE_KEYWORD_POLICY[key]:
            raise ValueError("post-intake policy value is invalid")
    actions = value.get("actions")
    if type(actions) is not list or tuple(actions) != POST_INTAKE_KEYWORD_POLICY["actions"]:
        raise ValueError("post-intake policy actions are invalid")
    return {
        "policy_id": POST_INTAKE_KEYWORD_POLICY["policy_id"],
        "processing_version": POST_INTAKE_KEYWORD_POLICY["processing_version"],
        "authority_ref": POST_INTAKE_KEYWORD_POLICY["authority_ref"],
        "purpose": POST_INTAKE_KEYWORD_POLICY["purpose"],
        "actions": list(POST_INTAKE_KEYWORD_POLICY["actions"]),
    }


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
    policy_id: str = PUBLIC_POLICY
    _signed_config_digest: str = field(default="", repr=False, compare=False)
    purpose_query: Optional[dict] = None
    internal_auto_opt_in: bool = False
    post_intake_policy: Optional[dict] = None

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
        if self.policy_id not in BASELINE_POLICIES:
            raise ValueError("unsupported baseline permission policy")
        post_intake_policy = _validated_post_intake_policy(
            self.post_intake_policy, baseline_policy=self.policy_id,
        )
        object.__setattr__(self, "post_intake_policy", post_intake_policy)
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


def round_robin_due(evaluated, limit=MAX_DUE_ATTEMPTS_PER_TICK, *, last_attempts=None):
    """Rotate platforms and use durable least-recent attempts for query fairness."""
    from collections import deque
    groups = {}
    # A failed query's overdue retry must not perpetually precede every query
    # whose first due time is this tick. Eligibility/backoff is unchanged.
    def order(row):
        if last_attempts is None:
            return (row[0], row[1], row[2])
        attempted = last_attempts.get(row[1])
        return (attempted is not None, attempted.timestamp() if attempted else 0,
                row[0], row[1], row[2])

    for row in sorted(evaluated, key=order):
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
    last_failure_status: Optional[str] = None
    last_progress_at: Optional[datetime] = None


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

    # A partial batch with committed Source originals is useful progress, while
    # its unresolved rows still keep the attempt FAILED. Continue at the signed
    # cadence instead of exponentially delaying the remaining acquisition.
    if (history.last_progress_at is not None
            and history.last_progress_at == history.last_failure_at):
        due_at = history.last_progress_at + timedelta(seconds=plan.cadence_seconds)
        return BaselineDueDecision(
            now >= due_at, "PARTIAL_PROGRESS_DUE" if now >= due_at
            else "PARTIAL_PROGRESS_CADENCE", due_at, pid)

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


def _verified_partial_source_progress(result: Any) -> int:
    """Count committed originals without promoting a partial task to success."""
    if (not isinstance(result, dict) or result.get("status") not in {
            "PARTIAL_SCOPE_REVIEW_REQUIRED", "PARTIAL_ACQUISITION_PENDING",
            "PARTIAL_SOURCE_INTAKE_PENDING"}
            or result.get("evidence_recorded") is not True
            or not isinstance(result.get("source_intake_outcome_ref"), str)
            or re.fullmatch(r"app_evidence_records:[1-9][0-9]*",
                            result["source_intake_outcome_ref"]) is None):
        return 0
    intake = result.get("source_intake")
    rows = result.get("live_original_refs")
    if not isinstance(intake, dict) or not isinstance(rows, list):
        return 0
    saved = intake.get("originals_saved")
    canonical = result.get("canonical_synced")
    if (type(saved) is not int or saved <= 0 or type(canonical) is not int
            or canonical < saved):
        return 0
    verified = [row for row in rows if isinstance(row, dict)
                and row.get("status") == "SAVED"
                and row.get("evidence_integrity_verified") is True
                and row.get("evidence_assurance") == "writer-authenticated"
                and row.get("source_evidence_version") == "collected-native-source:live-v1"
                and isinstance(row.get("source_evidence_ref"), str)
                and re.fullmatch(r"app_evidence_records:[1-9][0-9]*",
                                 row["source_evidence_ref"])
                and isinstance(row.get("source_artifact_ref"), str)
                and bool(row["source_artifact_ref"])]
    return saved if len(verified) == saved else 0


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
    platform_lock = getattr(store, "platform_attempt_lock", None)
    if not callable(platform_lock):
        decision = BaselineDueDecision(
            False, "STORE_PLATFORM_LOCK_UNAVAILABLE", None, plan.plan_id,
        )
        return {"decision": decision, "attempt_id": None, "result": None,
                "status": "STORE_PLATFORM_LOCK_UNAVAILABLE"}
    with platform_lock(plan.platform) as acquired:
        if acquired is not True:
            decision = BaselineDueDecision(
                False, "PLATFORM_IN_PROGRESS", None, plan.plan_id,
            )
            return {"decision": decision, "attempt_id": None, "result": None,
                    "status": "PLATFORM_IN_PROGRESS"}
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
                partial_saved_count=0 if success else _verified_partial_source_progress(result),
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
    post_intake_policy: Optional[dict] = None
    recovery_only: bool = False

    def __post_init__(self) -> None:
        if type(self.recovery_only) is not bool:
            raise ValueError("recovery_only must be a boolean")
        policy = _validated_post_intake_policy(
            self.post_intake_policy, baseline_policy=self.policy_id,
        )
        object.__setattr__(self, "post_intake_policy", policy)

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
            and self.post_intake_policy == plan.post_intake_policy
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
            and self.policy_id in BASELINE_POLICIES
            and 60 <= self.cadence_seconds <= 31 * 24 * 60 * 60
        )


def _canonical_config(config: dict) -> bytes:
    unsigned = {k: v for k, v in config.items() if k != "hmac"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_prelaunch_baseline_config(path: Optional[str] = None, *,
                                   hmac_key: str | None = None,
                                   registry_loader: Callable[[], Any] | None = None,
                                   expand_registry: bool = True):
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
    if config.get("policy_id") not in BASELINE_POLICIES:
        raise BaselineConfigError("POLICY_UNSUPPORTED")
    sources = config.get("sources", [])
    expansion_raw = config.get("registry_expansion")
    recovery_raw = config.get("recovery_sources", [])
    if (not isinstance(sources, list)
            or not isinstance(recovery_raw, list)
            or (not sources and expansion_raw is None and not recovery_raw)):
        raise BaselineConfigError("SOURCE_SET_INVALID")
    expansion = None
    if expansion_raw is not None:
        if config.get("policy_id") != PURPOSE_POLICY or config.get("internal_auto_opt_in") is not True:
            raise BaselineConfigError("REGISTRY_EXPANSION_POLICY_INVALID")
        expansion = _validated_registry_expansion(expansion_raw)
    if recovery_raw and (config.get("policy_id") != PURPOSE_POLICY
                         or config.get("internal_auto_opt_in") is not True):
        raise BaselineConfigError("RECOVERY_POLICY_UNSUPPORTED")
    source_policies = []
    for source in sources:
        if not isinstance(source, dict):
            raise BaselineConfigError("SOURCE_ENTRY_INVALID")
        source_policy = source.get("policy_id", config["policy_id"])
        if not isinstance(source_policy, str) or source_policy not in BASELINE_POLICIES:
            raise BaselineConfigError("POLICY_UNSUPPORTED")
        if source_policy == PURPOSE_POLICY and config.get("internal_auto_opt_in") is not True:
            raise BaselineConfigError("INTERNAL_AUTO_OPT_IN_REQUIRED")
        source_policies.append(source_policy)
    key = _resolve_baseline_config_key(hmac_key)
    _verify_config_hmac(config, key)
    version = config.get("plan_version")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", version):
        raise BaselineConfigError("PLAN_VERSION_INVALID")
    digest = hashlib.sha256(_canonical_config(config)).hexdigest()
    post_intake_policies = []
    for source, source_policy in zip(sources, source_policies):
        policy_value = (source["post_intake_policy"] if "post_intake_policy" in source
                        else config.get("post_intake_policy"))
        try:
            post_intake_policies.append(_validated_post_intake_policy(
                policy_value, baseline_policy=source_policy,
            ))
        except (TypeError, ValueError):
            raise BaselineConfigError("POST_INTAKE_POLICY_INVALID") from None
    plans = []
    seen = set()
    for source, source_policy, post_intake_policy in zip(
            sources, source_policies, post_intake_policies):
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
                policy_id=source_policy,
                _signed_config_digest=digest,
                purpose_query=source.get("purpose_query"),
                internal_auto_opt_in=(
                    source_policy == PURPOSE_POLICY
                    and config.get("internal_auto_opt_in") is True
                ),
                post_intake_policy=post_intake_policy,
            )
        except (KeyError, TypeError, ValueError):
            raise BaselineConfigError("SOURCE_ENTRY_INVALID") from None
        if not plan._signed_config_digest or plan.plan_id in seen:
            raise BaselineConfigError("SOURCE_ENTRY_DUPLICATE")
        seen.add(plan.plan_id)
        plans.append(plan)
    expansion_summary = None
    if expansion is not None and expand_registry:
        dynamic_sources, expansion_summary = _registry_expansion_sources(
            expansion, config_plan_version=version, registry_loader=registry_loader,
        )
        for source in dynamic_sources:
            try:
                scope = {key: source.get(key) for key in
                         ("domain_id", "subject_id", "brand_focus_id")}
                plan = PublicBaselinePlan(
                    source_key=source["source_key"], source_version=source["source_version"],
                    exact_scope=json.dumps(scope, sort_keys=True, separators=(",", ":")),
                    scope_version=source["scope_version"], cadence_seconds=source["cadence_seconds"],
                    authorization_ref=source["authorization_ref"], enabled=True,
                    prelaunch_authorized=True, end_user_auto=False,
                    platform=source["platform"], source_url=source["source_url"],
                    domain_id=source["domain_id"], subject_id=source.get("subject_id"),
                    brand_focus_id=source.get("brand_focus_id"), max_results=source["max_results"],
                    plan_version=source["plan_version"], policy_id=PURPOSE_POLICY,
                    _signed_config_digest=digest, purpose_query=source["purpose_query"],
                    internal_auto_opt_in=True,
                )
            except (KeyError, TypeError, ValueError):
                raise BaselineConfigError("REGISTRY_EXPANSION_PLAN_INVALID") from None
            if plan.plan_id in seen:
                continue
            seen.add(plan.plan_id)
            plans.append(plan)
    elif expansion is not None:
        expansion_summary = {"status": "PENDING_CANONICAL_REGISTRY_READ"}

    recovery_sources = recovery_raw
    recovery_plans = []
    for source in recovery_sources:
        if not isinstance(source, dict):
            raise BaselineConfigError("RECOVERY_SOURCE_ENTRY_INVALID")
        source_policy = source.get("policy_id", config["policy_id"])
        if source_policy != PURPOSE_POLICY:
            raise BaselineConfigError("RECOVERY_POLICY_UNSUPPORTED")
        source_plan_version = source.get("plan_version", version)
        try:
            plan = PublicBaselinePlan(
                source_key=source["source_key"], source_version=source["source_version"],
                exact_scope=json.dumps({k: source.get(k) for k in
                    ("domain_id", "subject_id", "brand_focus_id")}, sort_keys=True, separators=(",", ":")),
                scope_version=source["scope_version"], cadence_seconds=source["cadence_seconds"],
                authorization_ref=source["authorization_ref"], enabled=True,
                prelaunch_authorized=True, end_user_auto=False, platform=source["platform"],
                source_url=source["source_url"], domain_id=source["domain_id"],
                subject_id=source.get("subject_id"), brand_focus_id=source.get("brand_focus_id"),
                max_results=source.get("max_results", 20), plan_version=source_plan_version,
                policy_id=PURPOSE_POLICY, _signed_config_digest=digest,
                purpose_query=source.get("purpose_query"), internal_auto_opt_in=True,
            )
        except (KeyError, TypeError, ValueError):
            raise BaselineConfigError("RECOVERY_SOURCE_ENTRY_INVALID") from None
        if plan.plan_id in {item.plan_id for item in recovery_plans}:
            raise BaselineConfigError("RECOVERY_SOURCE_DUPLICATE")
        recovery_plans.append(plan)
    return {"status": "READY" if plans else "STAGED", "plan_version": version,
            "plans": plans, "recovery_plans": recovery_plans,
            "registry_expansion": expansion_summary,
            "signature_verified": True}


def maintenance_authorization(plan: PublicBaselinePlan, *, recovery_only: bool = False) -> PrelaunchMaintenanceAuthorization:
    if not plan._signed_config_digest:
        raise BaselineConfigError("HMAC_UNAVAILABLE")
    if type(recovery_only) is not bool:
        raise BaselineConfigError("RECOVERY_MODE_INVALID")
    return PrelaunchMaintenanceAuthorization(
        plan_id=plan.plan_id, source_url=plan.source_url, platform=plan.platform,
        domain_id=plan.domain_id, subject_id=plan.subject_id,
        brand_focus_id=plan.brand_focus_id, source_version=plan.source_version,
        scope_version=plan.scope_version, cadence_seconds=plan.cadence_seconds,
        authorization_ref=plan.authorization_ref, policy_id=plan.policy_id,
        signature_verified=True, post_intake_policy=plan.post_intake_policy,
        recovery_only=recovery_only,
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
    if not loaded.get("plans"):
        return {"status": "STAGED", "reason": "NO_ACTIVE_COLLECTION_PLANS",
                "plan_version": loaded.get("plan_version"),
                "summary": {"registry_expansion": loaded.get("registry_expansion"),
                            "recovery_plan_count": len(loaded.get("recovery_plans", []))},
                "runs": []}
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
    last_attempts = {}
    not_due = []
    purpose_platform_backoff = {}
    for order, plan in enumerate(loaded["plans"]):
        history = store.public_baseline_history(plan)
        last_attempts[plan.plan_id] = history.last_attempt_at
        decision = evaluate_baseline_due(plan, history, now=now)
        # A query's relevance/time/intake failure must not cool down every other
        # topic on the platform. Only a durable platform access failure does so.
        if (plan.policy_id == PURPOSE_POLICY and decision.reason == "RETRY_BACKOFF"
                and history.last_failure_status in {
                    "NEED_VERIFY", "BLOCKED", "RISK_WARNING", "SESSION_EXPIRED",
                    "AUTH_REQUIRED", "NOT_CONFIGURED", "COOLING_DOWN", "RATE_LIMITED",
                    "PROVIDER_UNAVAILABLE",
                }):
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
    selected = round_robin_due(evaluated, last_attempts=last_attempts)
    selected_ids = {row[1] for row in selected}
    results = []
    blocked_platforms = set(purpose_platform_backoff)
    selected_order = {row[1]: i for i, row in enumerate(selected)}

    def execute_selected(row):
        _, plan_id, _, plan, decision = row
        scope = {"domain_id": plan.domain_id, "subject_id": plan.subject_id,
                 "brand_focus_id": plan.brand_focus_id}
        try:
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
            return item
        except Exception as exc:
            return {"plan_id": plan_id, "status": "FAILED",
                    "error_type": type(exc).__name__}

    terminal_platform_statuses = {
        "NEED_VERIFY", "BLOCKED", "RISK_WARNING", "SESSION_EXPIRED",
        "AUTH_REQUIRED", "NOT_CONFIGURED", "COOLING_DOWN", "RATE_LIMITED",
    }

    def run_platform_group(platform, rows):
        # Each platform owns its block state; no worker mutates shared scheduler state.
        purpose_blocked = platform in purpose_platform_backoff
        platform_stop_status = None
        group_results = {}
        for row in rows:
            plan_id, plan = row[1], row[3]
            if plan.policy_id == PURPOSE_POLICY and purpose_blocked:
                group_results[plan_id] = {
                    "plan_id": plan_id, "attempt_id": None,
                    "status": "PLATFORM_BACKOFF", "platform": platform,
                }
                continue
            if platform_stop_status is not None:
                group_results[plan_id] = {
                    "plan_id": plan_id, "attempt_id": None,
                    "status": platform_stop_status, "platform": platform,
                }
                continue
            item = execute_selected(row)
            group_results[plan_id] = item
            status = item.get("status")
            if status in {"PLATFORM_IN_PROGRESS", "STORE_PLATFORM_LOCK_UNAVAILABLE"}:
                platform_stop_status = status
            elif (plan.policy_id == PURPOSE_POLICY
                    and status in terminal_platform_statuses):
                purpose_blocked = True
        return group_results, purpose_blocked, platform_stop_status

    platform_groups = {}
    for row in selected:
        plan = row[3]
        if plan.policy_id == PURPOSE_POLICY and plan.platform in purpose_platform_backoff:
            continue
        platform_groups.setdefault(plan.platform, []).append(row)

    execution_results = {}
    platform_stop_statuses = {}
    if platform_groups:
        with ThreadPoolExecutor(
                max_workers=min(len(platform_groups), MAX_DUE_ATTEMPTS_PER_TICK),
                thread_name_prefix="prelaunch-baseline") as executor:
            futures = {
                platform: executor.submit(run_platform_group, platform, rows)
                for platform, rows in platform_groups.items()
            }
            for platform, future in futures.items():
                try:
                    group_results, platform_blocked, platform_stop_status = future.result()
                except Exception as exc:
                    group_results = {
                        row[1]: {"plan_id": row[1], "status": "FAILED",
                                 "error_type": type(exc).__name__}
                        for row in platform_groups[platform]
                    }
                    platform_blocked = False
                    platform_stop_status = None
                execution_results.update(group_results)
                if platform_blocked:
                    blocked_platforms.add(platform)
                if platform_stop_status is not None:
                    platform_stop_statuses[platform] = platform_stop_status

    for _, plan_id, _, plan, decision in sorted(
            evaluated, key=lambda row: selected_order.get(row[1], len(selected))):
        if plan.policy_id == PURPOSE_POLICY and plan.platform in purpose_platform_backoff:
            results.append({"plan_id": plan.plan_id, "attempt_id": None,
                            "status": "PLATFORM_BACKOFF", "platform": plan.platform})
            continue
        if plan_id not in selected_ids:
            platform_stop_status = platform_stop_statuses.get(plan.platform)
            if platform_stop_status is not None:
                results.append({"plan_id": plan.plan_id, "attempt_id": None,
                                "status": platform_stop_status, "platform": plan.platform})
            elif plan.policy_id == PURPOSE_POLICY and plan.platform in blocked_platforms:
                results.append({"plan_id": plan.plan_id, "attempt_id": None,
                                "status": "PLATFORM_BACKOFF", "platform": plan.platform})
            else:
                results.append({"decision": decision, "attempt_id": None,
                                "status": "BATCH_DEFERRED"})
            continue
        item = execution_results.get(plan_id)
        if item is None:
            item = {"plan_id": plan_id, "status": "FAILED",
                    "error_type": "EXECUTION_RESULT_MISSING"}
        results.append(item)

    results.extend({"plan_id": plan.plan_id, "decision": decision,
                    "attempt_id": None, "status": decision.reason}
                   for plan, decision in not_due)
    statuses = [str(item.get("status") or "FAILED") for item in results]
    deferred_statuses = {"NOT_DUE", "ATTEMPT_IN_PROGRESS", "RETRY_BACKOFF",
                         "BATCH_DEFERRED", "PLATFORM_BACKOFF", "PLATFORM_IN_PROGRESS",
                         "FIRST_RUN", "DISABLED", "PARTIAL_PROGRESS_CADENCE"}
    deferred = sum(status in deferred_statuses for status in statuses)
    failed = sum(status != "SUCCESS" and status not in deferred_statuses
                 for status in statuses)
    succeeded = sum(status == "SUCCESS" for status in statuses)
    overall = "FAILED" if failed == len(results) else "PARTIAL" if failed else "COMPLETED"
    return {"status": overall, "plan_version": loaded["plan_version"],
            "summary": {"succeeded": succeeded, "failed": failed,
                        "deferred": deferred,
                        "registry_expansion": loaded.get("registry_expansion"),
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
                    "authorization_ref","platform","source_url","domain_id","policy_id",
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


def _resolve_baseline_config_key(hmac_key: str | None) -> str:
    key = hmac_key if hmac_key is not None else os.environ.get(
        "LUMENIS_PRELAUNCH_BASELINE_HMAC_KEY", "",
    )
    if not isinstance(key, str) or not key:
        raise BaselineConfigError("HMAC_UNAVAILABLE")
    return key


def _verify_config_hmac(config: dict, hmac_key: str) -> None:
    signature = config.get("hmac")
    if not isinstance(signature, dict):
        raise BaselineConfigError("HMAC_UNAVAILABLE")
    if signature.get("algorithm") != "HMAC-SHA256" or not isinstance(signature.get("value"), str):
        raise BaselineConfigError("HMAC_INVALID")
    expected = hmac.new(
        hmac_key.encode("utf-8"), _canonical_config(config), hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature["value"]):
        raise BaselineConfigError("HMAC_MISMATCH")


def _registry_snapshot_fingerprint(rows) -> str:
    """Hash only the current registry inputs that can change query targets."""
    fields = ("domain_id", "subject_id", "brand_focus_id", "subject_type", "name_en",
              "name_zh", "keywords", "aliases", "approved_aliases", "status")
    snapshot = []
    for row in rows:
        if not isinstance(row, dict):
            snapshot.append({"invalid_row": type(row).__name__})
            continue
        snapshot.append({field: row.get(field) for field in fields})
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _registry_rows(loader=None):
    try:
        if loader is None:
            from subject_registry import list_subjects
            loader = list_subjects
        rows = loader()
    except (ImportError, OSError, RuntimeError, TypeError, ValueError, sqlite3.Error):
        raise BaselineConfigError("REGISTRY_UNAVAILABLE") from None
    if not isinstance(rows, (list, tuple)):
        raise BaselineConfigError("REGISTRY_UNAVAILABLE")
    return list(rows)


def _validated_registry_expansion(value):
    """Validate an HMAC-covered GLOBAL registered-entity query template."""
    from ...acquisition_plan import (
        _BUSINESS_DIMENSIONS,
        AcquisitionPlanError,
        _normalise_text,
    )

    if type(value) is not dict or set(value) != {
            "schema_version", "source_version", "scope_version", "authorization_ref",
            "cadence_seconds", "max_results", "templates"}:
        raise BaselineConfigError("REGISTRY_EXPANSION_SCHEMA_INVALID")
    if value.get("schema_version") != 1:
        raise BaselineConfigError("REGISTRY_EXPANSION_SCHEMA_INVALID")
    try:
        source_version = _normalise_text(value.get("source_version"), field="source_version", max_length=64)
        scope_version = _normalise_text(value.get("scope_version"), field="scope_version", max_length=64)
        authorization_ref = _normalise_text(value.get("authorization_ref"), field="authorization_ref", max_length=200)
    except (TypeError, ValueError):
        raise BaselineConfigError("REGISTRY_EXPANSION_AUTHORITY_INVALID") from None
    cadence = value.get("cadence_seconds")
    max_results = value.get("max_results")
    if (not source_version or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,64}", source_version)
            or not scope_version or not re.fullmatch(r"[A-Za-z0-9._:/-]{1,64}", scope_version)
            or not authorization_ref or type(cadence) is not int or isinstance(cadence, bool)
            or not 60 <= cadence <= 31 * 24 * 60 * 60):
        raise BaselineConfigError("REGISTRY_EXPANSION_AUTHORITY_INVALID")
    if type(max_results) is not int or isinstance(max_results, bool) or not 1 <= max_results <= 20:
        raise BaselineConfigError("REGISTRY_EXPANSION_LIMIT_INVALID")
    templates = value.get("templates")
    if not isinstance(templates, list) or not 1 <= len(templates) <= 16:
        raise BaselineConfigError("REGISTRY_EXPANSION_TEMPLATES_INVALID")
    allowed_template_fields = {
        "domain_id", "purpose", "dimension", "platforms", "acquisition_stage",
        "geography_terms", "venue_boundary_terms",
    }
    normalized_templates = []
    unsupported_platforms = set()
    for template in templates:
        if (type(template) is not dict or not {"domain_id", "purpose", "dimension", "platforms",
                                               "acquisition_stage"}.issubset(template)
                or set(template) - allowed_template_fields):
            raise BaselineConfigError("REGISTRY_EXPANSION_TEMPLATE_INVALID")
        domain = template.get("domain_id")
        if (type(domain) is not str or domain not in {"CTH", "BMP"}
                or template.get("acquisition_stage") != "SUBJECT_INTAKE"):
            raise BaselineConfigError("REGISTRY_EXPANSION_TEMPLATE_INVALID")
        try:
            purpose = _normalise_text(template.get("purpose"), field="purpose", max_length=256)
            dimension = template.get("dimension")
            if not purpose or dimension not in _BUSINESS_DIMENSIONS:
                raise ValueError
            if dimension == "venue_operations" and domain != "CTH":
                raise ValueError
            platforms = template.get("platforms")
            if not isinstance(platforms, list) or not 1 <= len(platforms) <= 32 or any(
                    type(platform) is not str or not platform.strip() for platform in platforms):
                raise ValueError
            from ..platform_naming import normalize_platform
            normalized_platforms = []
            for platform in platforms:
                normalized = normalize_platform(platform)
                if normalized == "xiaohongshu":
                    normalized = "xhs"
                if normalized not in PURPOSE_PLATFORMS:
                    unsupported_platforms.add((normalized or "UNKNOWN")[:40])
                    continue
                if normalized not in normalized_platforms:
                    normalized_platforms.append(normalized)
            geography = template.get("geography_terms", [])
            venue = template.get("venue_boundary_terms", [])
            if (not isinstance(geography, list) or not isinstance(venue, list)
                    or len(geography) > 16 or len(venue) > 16
                    or any(type(term) is not str or not term.strip() or len(term) > 80
                           for term in geography + venue)):
                raise ValueError
        except (AcquisitionPlanError, TypeError, ValueError):
            raise BaselineConfigError("REGISTRY_EXPANSION_TEMPLATE_INVALID") from None
        normalized_templates.append({
            "domain_id": domain, "purpose": purpose, "dimension": dimension,
            "platforms": normalized_platforms, "acquisition_stage": "SUBJECT_INTAKE",
            "geography_terms": geography, "venue_boundary_terms": venue,
        })
    return {
        "schema_version": 1, "source_version": source_version,
        "scope_version": scope_version, "authorization_ref": authorization_ref,
        "cadence_seconds": cadence, "max_results": max_results,
        "templates": normalized_templates,
        "unsupported_platforms": sorted(unsupported_platforms),
    }


def _registry_expansion_sources(expansion, *, config_plan_version, registry_loader=None):
    """Compile every current registry target from the signed template, without truncation."""
    from ...acquisition_plan import (
        AcquisitionPlanError,
        _registry_aliases,
        build_acquisition_plan,
    )
    from ..platform_naming import normalize_platform

    def make_requests(rows, templates):
        requests = []
        targets = set()
        blocked_rows = 0
        for row in rows:
            if not isinstance(row, dict):
                blocked_rows += 1
                continue
            status = str(row.get("status") or "configured").strip().lower()
            if status in {"archived", "disabled", "deleted"}:
                continue
            if status not in {"configured", "active"}:
                blocked_rows += 1
                continue
            domain = row.get("domain_id")
            expected_type = "company" if domain == "CTH" else "brand" if domain == "BMP" else None
            registry_id = row.get("subject_id")
            focus_id = row.get("brand_focus_id")
            try:
                aliases = _registry_aliases(row)
            except AcquisitionPlanError:
                blocked_rows += 1
                continue
            if (not expected_type or row.get("subject_type") != expected_type
                    or not isinstance(registry_id, str) or not registry_id.strip()
                    or (domain == "CTH" and focus_id is not None)
                    or (domain == "BMP" and (not isinstance(focus_id, str) or not focus_id.strip()))
                    or not aliases):
                blocked_rows += 1
                continue
            target_key = (domain, registry_id)
            if target_key in targets:
                continue
            targets.add(target_key)
            if len(targets) > MAX_REGISTRY_EXPANSION_TARGETS:
                raise BaselineConfigError("REGISTRY_EXPANSION_TARGET_LIMIT")
            scope_key = focus_id if domain == "BMP" else registry_id
            for template in templates:
                if template["domain_id"] != domain:
                    continue
                for platform in template["platforms"]:
                    for alias, _ in aliases:
                        requests.append({
                            "domain_id": domain, "scope_key": scope_key,
                            "aliases": [alias],
                            "purpose": template["purpose"], "dimension": template["dimension"],
                            "platforms": [platform], "acquisition_stage": "SUBJECT_INTAKE",
                            "geography_terms": template["geography_terms"],
                            "venue_boundary_terms": template["venue_boundary_terms"],
                        })
                        if len(requests) > MAX_REGISTRY_EXPANSION_QUERIES:
                            raise BaselineConfigError("REGISTRY_EXPANSION_QUERY_LIMIT")
        return requests, len(targets), blocked_rows

    for attempt in range(MAX_REGISTRY_SNAPSHOT_RETRIES):
        snapshot = _registry_rows(registry_loader)
        fingerprint = _registry_snapshot_fingerprint(snapshot)
        requests, target_count, blocked_rows = make_requests(snapshot, expansion["templates"])
        queries = []
        staged_reasons = set()
        if requests:
            continuation = None
            pages = 0
            while True:
                try:
                    plan = build_acquisition_plan(
                        business_requests=requests, registry_loader=lambda snapshot=snapshot: snapshot,
                        max_queries=64, continuation=continuation,
                    )
                except AcquisitionPlanError as exc:
                    raise BaselineConfigError("REGISTRY_EXPANSION_PLAN_INVALID") from exc
                if plan.status not in {"READY", "STAGED"}:
                    raise BaselineConfigError(plan.reason_code or "REGISTRY_EXPANSION_PLAN_UNAVAILABLE")
                if plan.status == "STAGED" and plan.reason_code:
                    staged_reasons.add(plan.reason_code)
                queries.extend(plan.queries)
                if len(queries) > MAX_REGISTRY_EXPANSION_QUERIES:
                    raise BaselineConfigError("REGISTRY_EXPANSION_QUERY_LIMIT")
                pages += 1
                if pages > MAX_REGISTRY_EXPANSION_PAGES:
                    raise BaselineConfigError("REGISTRY_EXPANSION_PAGE_LIMIT")
                continuation = plan.next_cursor
                if continuation is None:
                    break

        current = _registry_rows(registry_loader)
        if _registry_snapshot_fingerprint(current) != fingerprint:
            if attempt + 1 < MAX_REGISTRY_SNAPSHOT_RETRIES:
                continue
            raise BaselineConfigError("REGISTRY_CHANGED_DURING_PLAN")

        entries = []
        seen = set()
        for query in queries:
            platform = normalize_platform((query.business_context or {}).get("platform"))
            identity = hashlib.sha256(json.dumps(
                query.to_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
            domain = "cth" if query.domain_id == "CTH" else "bmp"
            source = {
                "source_key": platform + ":" + identity,
                "source_version": expansion["source_version"],
                "scope_version": expansion["scope_version"],
                "cadence_seconds": expansion["cadence_seconds"],
                "authorization_ref": expansion["authorization_ref"],
                "platform": platform, "source_url": query.keyword, "domain_id": domain,
                "subject_id": query.subject_id, "brand_focus_id": query.brand_focus_id,
                "max_results": expansion["max_results"], "plan_version": config_plan_version,
                "purpose_query": query.to_dict(), "policy_id": PURPOSE_POLICY,
            }
            source_identity = hashlib.sha256(json.dumps(
                source, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
            if source_identity not in seen:
                seen.add(source_identity)
                entries.append(source)
        return entries, {
            "status": "READY" if entries else "STAGED",
            "snapshot_sha256": fingerprint,
            "registered_target_count": target_count,
            "blocked_registry_row_count": blocked_rows,
            "generated_query_count": len(entries),
            "unsupported_platforms": expansion.get("unsupported_platforms", []),
            "staged_reasons": sorted(staged_reasons),
        }
    raise BaselineConfigError("REGISTRY_CHANGED_DURING_PLAN")
