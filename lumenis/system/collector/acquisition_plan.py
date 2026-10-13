"""Scope-aware acquisition query planning for the SYSTEM Collector.

The planner resolves a bounded set of public-source queries from the canonical
Subject registry before any collector, browser, profile, session, or network
operation is attempted.  It is deliberately a pure planning boundary: source
policy is read for safe metadata only, while collection identity and effects
remain owned by the existing runtime callers.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import re
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence


PLAN_VERSION = "lumenis.acquisition-plan.v1"
REGISTRY_SOURCE = "lumenis_subject_registry"
GLOBAL_ALL = "GLOBAL_ALL"
FOCUS = "FOCUS"
READY = "READY"
STAGED = "STAGED"
BLOCKED = "BLOCKED"

DEFAULT_QUERY_LIMIT = 32
MAX_QUERY_LIMIT = 64
_VALID_DOMAINS = {"CTH", "BMP"}
_WHITESPACE = re.compile(r"\s+")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
APPROVED_TOPIC_SEED_SHA256 = "cfe3b6cb424ee0efe3d917479ba95db66f4ca9b8df32fa891fcf16fd6c576028"


def load_approved_topic_seed() -> dict[str, Any]:
    """Load the unchanged reviewed seed from the product package, not work/.

    This is an input version, not entity admission, trend truth or training
    permission. New observed terms use the existing source/topic owners; keep
    this approved original when publishing a subsequent seed version.
    """
    path = Path(__file__).resolve().parents[3] / "config/collection-topic-seed-20261004.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != APPROVED_TOPIC_SEED_SHA256:
        raise AcquisitionPlanError("approved topic seed bytes changed")
    return json.loads(raw)


def _verify_seed_reference(reference, entry, platforms, seed):
    if not isinstance(reference, Mapping) or reference.get("input_sha256") != APPROVED_TOPIC_SEED_SHA256:
        raise AcquisitionPlanError("unknown topic seed version")
    topic = next((row for row in seed["topics"] if row["id"] == reference.get("topic_id")), None)
    if topic is None or entry is None:
        raise AcquisitionPlanError("topic seed needs an existing term and registered entity")
    from .adapters.platform_naming import normalize_platform
    aliases = {_normalised_key(alias) for alias, _ in entry["aliases"]}
    # This frozen input uses a disambiguated display label, while the existing
    # Registry stores the Chinese name and the district in its English name.
    # Bind only that reviewed input to its exact current canonical identity.
    # This does not register an alias or establish any collected-source scope.
    canonical_names = {alias for alias, kind in entry["aliases"] if kind == "registered_name"}
    luohu_seed_binding = (
        topic["entity"] == "深圳万象城（罗湖）"
        and entry["domain_id"] == "CTH"
        and entry["registry_id"] == "SUBJ-74f25e92c6744e738c7edf66"
        and {"深圳万象城", "Shenzhen MixC Luohu"}.issubset(canonical_names)
    )
    if ((_normalised_key(topic["entity"]) not in aliases and not luohu_seed_binding)
            or normalize_platform(topic["platform"]) not in {normalize_platform(p) for p in platforms}
            or any(reference.get(key) != topic[field] for key, field in (
                ("source_id", "source_id"), ("source_url", "source_url"),
                ("term_preserved", "topic"), ("literal", "observed_literal")))):
        raise AcquisitionPlanError("topic seed reference does not match its original source/entity")


class AcquisitionPlanError(ValueError):
    """Raised only for malformed planner arguments.

    Ordinary registry or source-policy gaps are represented by a BLOCKED or
    STAGED plan so callers can return an honest state without performing I/O.
    """


@dataclass(frozen=True)
class AcquisitionQuery:
    """One bounded keyword with an exact canonical registry scope."""

    keyword: str
    domain_id: str
    product_id: str
    registry_id: str
    subject_id: Optional[str]
    brand_focus_id: Optional[str]
    priority: int
    reason_code: str
    alias_kind: str
    context_mode: str = GLOBAL_ALL
    business_context: Mapping[str, Any] | None = None

    @property
    def scope_key(self) -> str:
        return self.subject_id or self.brand_focus_id or ""

    @property
    def scope(self) -> dict[str, Any]:
        """Return the exact scope shape shared by collection/Evidence callers."""

        domain_id = "cth" if self.domain_id == "CTH" else "zbmp"
        return {
            "domain_id": domain_id,
            "subject_id": self.subject_id,
            "brand_focus_id": self.brand_focus_id,
            "global_scope": not bool(self.subject_id or self.brand_focus_id),
        }

    @property
    def provenance(self) -> dict[str, str]:
        """Explain scheduling without carrying actor or credential identifiers."""

        return {
            "source": REGISTRY_SOURCE,
            "reason_code": self.reason_code,
            "alias_kind": self.alias_kind,
            "context_mode": self.context_mode,
            "scope_key": self.scope_key,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "keyword": self.keyword,
            "domain_id": self.domain_id,
            "product_id": self.product_id,
            "registry_id": self.registry_id,
            "subject_id": self.subject_id,
            "brand_focus_id": self.brand_focus_id,
            "scope": self.scope,
            "priority": self.priority,
            "reason_code": self.reason_code,
            "alias_kind": self.alias_kind,
            "provenance": self.provenance,
            "business_context": dict(self.business_context or {}),
            "scope_role": "PLANNED_TARGET_NOT_VERIFIED_SOURCE_BINDING",
        }


@dataclass(frozen=True)
class AcquisitionPlan:
    """A bounded, serializable query plan and its honest readiness state."""

    status: str
    context_mode: str
    queries: tuple[AcquisitionQuery, ...]
    requested_keywords: tuple[str, ...]
    registry_counts: dict[str, int]
    missing_domains: tuple[str, ...]
    truncated: bool
    query_limit: int
    reason_code: str = ""
    reason: str = ""
    source_policy: dict[str, Any] | None = None
    rate_policy: dict[str, Any] | None = None
    focus_scope: dict[str, Any] | None = None
    total_queries: int = 0
    next_cursor: dict[str, Any] | None = None
    input_fingerprint: str = ""

    @property
    def keywords(self) -> tuple[str, ...]:
        return tuple(query.keyword for query in self.queries)

    @property
    def is_runnable(self) -> bool:
        return self.status in {READY, STAGED} and bool(self.queries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_version": PLAN_VERSION,
            "status": self.status,
            "context_mode": self.context_mode,
            "queries": [query.to_dict() for query in self.queries],
            "keywords": list(self.keywords),
            "requested_keywords": list(self.requested_keywords),
            "registry_source": REGISTRY_SOURCE,
            "registry_counts": dict(self.registry_counts),
            "coverage_basis": "registered_entries_only",
            "world_completeness": "NOT_ASSERTED",
            "missing_domains": list(self.missing_domains),
            "truncated": self.truncated,
            "query_limit": self.query_limit,
            "total_queries": self.total_queries,
            "next_cursor": dict(self.next_cursor) if self.next_cursor else None,
            "input_fingerprint": self.input_fingerprint,
            "continuation_required": self.next_cursor is not None,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "source_policy": dict(self.source_policy or {}),
            "rate_policy": dict(self.rate_policy or {}),
            "focus_scope": dict(self.focus_scope or {}) or None,
            # A focus only affects ordering/context. It never disables the
            # background entries included by a GLOBAL_ALL server plan.
            "background_collection_continues": True,
        }


def _normalise_domain(value: Any) -> str:
    domain = str(value or "").strip().upper()
    if domain == "ZBMP":
        domain = "BMP"
    if domain not in _VALID_DOMAINS:
        raise AcquisitionPlanError("domain_id must be CTH or BMP")
    return domain


def _normalise_text(value: Any, *, field: str, max_length: int = 80) -> str:
    if not isinstance(value, str):
        value = str(value or "")
    value = _WHITESPACE.sub(" ", value).strip()
    if not value:
        return ""
    if len(value) > max_length:
        raise AcquisitionPlanError(f"{field} exceeds {max_length} characters")
    if _CONTROL_CHARS.search(value):
        raise AcquisitionPlanError(f"{field} contains control characters")
    if not any(char.isalnum() for char in value):
        return ""
    return value


def _normalised_key(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip().casefold()


def _as_terms(value: Any, *, field: str) -> list[str]:
    if value is None or value == "":
        return []
    values: Iterable[Any]
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        raise AcquisitionPlanError(f"{field} must be a string or a list")
    terms: list[str] = []
    seen: set[str] = set()
    for item in values:
        term = _normalise_text(item, field=field)
        key = _normalised_key(term)
        if term and key not in seen:
            seen.add(key)
            terms.append(term)
    return terms


def _registry_aliases(row: Mapping[str, Any]) -> list[tuple[str, str]]:
    """Return canonical names and registry-provided aliases in stable order."""

    fields = (
        ("name_en", "registered_name"),
        ("name_zh", "registered_name"),
        ("keywords", "registered_alias"),
        ("aliases", "registered_alias"),
        ("approved_aliases", "registered_alias"),
    )
    aliases: list[tuple[str, str]] = []
    seen: set[str] = set()
    for field, kind in fields:
        for term in _as_terms(row.get(field), field=field):
            key = _normalised_key(term)
            if key not in seen:
                seen.add(key)
                aliases.append((term, kind))
    return aliases


def _safe_policy_metadata(policy: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read the existing source policy without exposing identity material."""

    try:
        from .adapters import rednote_policy

        active = policy or rednote_policy.effective_policy()
        kind_enabled = getattr(active, "kind_enabled", {}) or {}
        cadence = getattr(active, "human_cadence", {}) or {}
        source_policy = {
            "source": "rednote_policy",
            "policy_version": str(getattr(rednote_policy, "POLICY_VERSION", "")),
            "region": str(getattr(active, "primary_region", "intl") or "intl"),
            "allowed_region": "intl",
            "host": str(getattr(rednote_policy, "REGION_HOST", {}).get("intl", "")),
            "enabled_kinds": sorted(str(key) for key, value in kind_enabled.items() if value),
            "auto_run_enabled": bool(getattr(active, "auto_run_enabled", False)),
            "cn_paused": bool(getattr(active, "cn_paused", True)),
        }
        rate_policy = {
            "source": "rednote_policy",
            "status": str(cadence.get("status", "UNKNOWN")),
            "human_cadence": {
                key: value
                for key, value in cadence.items()
                if isinstance(value, (str, int, float, bool))
            },
        }
        return source_policy, rate_policy
    except Exception:
        # A missing policy is a real source-policy blocker, not permission to
        # invent a permissive fallback.  Keep the diagnostic secret-safe.
        return (
            {"source": "rednote_policy", "status": "UNAVAILABLE"},
            {"source": "rednote_policy", "status": "UNAVAILABLE"},
        )


def _load_registry(
    registry_loader: Optional[Callable[[], Sequence[Mapping[str, Any]]]] = None,
) -> tuple[list[Mapping[str, Any]], str | None]:
    try:
        if registry_loader is not None:
            rows = registry_loader()
        else:
            from subject_registry import list_subjects

            rows = list_subjects()
        return list(rows or []), None
    except Exception:
        return [], "REGISTRY_UNAVAILABLE"


def _blocked_plan(
    *,
    context_mode: str,
    requested_keywords: Sequence[str],
    query_limit: int,
    reason_code: str,
    reason: str,
    registry_counts: Optional[dict[str, int]] = None,
    missing_domains: Sequence[str] = (),
    source_policy: Optional[dict[str, Any]] = None,
    rate_policy: Optional[dict[str, Any]] = None,
    focus_scope: Optional[dict[str, Any]] = None,
) -> AcquisitionPlan:
    return AcquisitionPlan(
        status=BLOCKED,
        context_mode=context_mode,
        queries=(),
        requested_keywords=tuple(requested_keywords),
        registry_counts=dict(registry_counts or {"CTH": 0, "BMP": 0}),
        missing_domains=tuple(missing_domains),
        truncated=False,
        query_limit=query_limit,
        reason_code=reason_code,
        reason=reason,
        source_policy=source_policy or {},
        rate_policy=rate_policy or {},
        focus_scope=focus_scope,
    )


# Registry statuses that never become collection targets (subject_registry.py treats them as inactive).
INACTIVE_STATUSES = frozenset({"archived", "disabled", "deleted"})


def build_acquisition_plan(
    keywords: Optional[Iterable[str]] = None,
    *,
    context_mode: str = GLOBAL_ALL,
    domain_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    brand_focus_id: Optional[str] = None,
    max_queries: int = DEFAULT_QUERY_LIMIT,
    registry_loader: Optional[Callable[[], Sequence[Mapping[str, Any]]]] = None,
    policy: Any = None,
    business_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    continuation: Optional[Mapping[str, Any]] = None,
) -> AcquisitionPlan:
    """Build a bounded query plan from registered Subjects and BrandFocus rows.

    ``keywords=None`` means *resolve from the live registry*.  It never means
    a historical/default Subject.  A focused plan keeps all registered
    background entries when keywords are omitted, but raises the selected
    entry's priority and records the exact scope.  Explicit keywords are
    accepted only when they map to a registered alias or an explicit focus.
    """

    try:
        query_limit = int(max_queries)
    except (TypeError, ValueError) as exc:
        raise AcquisitionPlanError("max_queries must be an integer") from exc
    if query_limit < 1:
        raise AcquisitionPlanError("max_queries must be positive")
    query_limit = min(query_limit, MAX_QUERY_LIMIT)

    mode = str(context_mode or GLOBAL_ALL).strip().upper()
    if mode in {"GLOBAL", "ALL"}:
        mode = GLOBAL_ALL
    if mode not in {GLOBAL_ALL, FOCUS}:
        raise AcquisitionPlanError("context_mode must be GLOBAL_ALL or FOCUS")

    if any(value is not None for value in (domain_id, subject_id, brand_focus_id)):
        mode = FOCUS
    focus_domain = _normalise_domain(domain_id) if domain_id is not None else None
    if mode == FOCUS and focus_domain is None:
        return _blocked_plan(
            context_mode=mode,
            requested_keywords=(),
            query_limit=query_limit,
            reason_code="FOCUS_SCOPE_REQUIRED",
            reason="a focused acquisition plan requires an exact domain and registry key",
        )
    if mode == FOCUS and focus_domain == "CTH" and brand_focus_id:
        return _blocked_plan(
            context_mode=mode,
            requested_keywords=(),
            query_limit=query_limit,
            reason_code="CTH_BRANDFOCUS_CONFLICT",
            reason="CTH scope cannot carry brand_focus_id",
        )
    source_policy, rate_policy = _safe_policy_metadata(policy)
    if business_requests is not None:
        source_policy = {"source": "SYSTEM_COLLECTOR_QUERY_CONTRACT", "rule_version": BUSINESS_RULE_VERSION,
                         "mode": "MANUAL", "identity_or_source_use_granted": False}
        rate_policy = {"source": "existing_platform_owner", "status": "EXECUTION_OWNER_REQUIRED"}
    if source_policy.get("status") == "UNAVAILABLE":
        return _blocked_plan(
            context_mode=mode,
            requested_keywords=(),
            query_limit=query_limit,
            reason_code="SOURCE_POLICY_UNAVAILABLE",
            reason="approved source policy is unavailable",
            source_policy=source_policy,
            rate_policy=rate_policy,
        )

    raw_keywords: Optional[list[str]]
    if keywords is None:
        raw_keywords = None
    else:
        raw_keywords = _as_terms(keywords, field="keywords")
        if not raw_keywords:
            return _blocked_plan(
                context_mode=mode,
                requested_keywords=(),
                query_limit=query_limit,
                reason_code="NO_KEYWORDS",
                reason="explicit acquisition keywords are empty",
                source_policy=source_policy,
                rate_policy=rate_policy,
            )

    rows, registry_error = _load_registry(registry_loader)
    if registry_error:
        return _blocked_plan(
            context_mode=mode,
            requested_keywords=raw_keywords or (),
            query_limit=query_limit,
            reason_code=registry_error,
            reason="canonical Subject/BrandFocus registry is unavailable",
            source_policy=source_policy,
            rate_policy=rate_policy,
        )

    entries: list[dict[str, Any]] = []
    registry_counts = {"CTH": 0, "BMP": 0}
    invalid_count = 0
    for row in rows:
        if not isinstance(row, Mapping):
            invalid_count += 1
            continue
        status = str(row.get("status") or "configured").strip().lower()
        if status in INACTIVE_STATUSES:
            continue
        try:
            domain = _normalise_domain(row.get("domain_id"))
        except AcquisitionPlanError:
            invalid_count += 1
            continue
        expected_type = "company" if domain == "CTH" else "brand"
        if str(row.get("subject_type") or "").strip().lower() != expected_type:
            invalid_count += 1
            continue
        registry_id = _normalise_text(row.get("subject_id"), field="subject_id", max_length=128)
        if not registry_id:
            invalid_count += 1
            continue
        brand_focus = _normalise_text(row.get("brand_focus_id"), field="brand_focus_id", max_length=128)
        if domain == "BMP" and not brand_focus:
            invalid_count += 1
            continue
        aliases = _registry_aliases(row)
        if not aliases:
            invalid_count += 1
            continue
        entries.append({
            "domain_id": domain,
            "product_id": "CTH" if domain == "CTH" else "ZBMP",
            "registry_id": registry_id,
            "subject_id": registry_id if domain == "CTH" else None,
            "brand_focus_id": brand_focus if domain == "BMP" else None,
            "aliases": aliases,
        })
        registry_counts[domain] += 1

    unassigned_discovery_only = bool(business_requests) and all(
        isinstance(r, Mapping) and r.get("unregistered_discovery") is True and not r.get("scope_key")
        for r in business_requests
    )
    if not entries and not unassigned_discovery_only:
        reason_code = "REGISTRY_EMPTY" if not rows else "REGISTRY_NOT_QUERYABLE"
        reason = (
            "no active registered Subject or BrandFocus has a query alias"
            if reason_code == "REGISTRY_NOT_QUERYABLE"
            else "canonical Subject/BrandFocus registry is empty; acquisition is staged"
        )
        return _blocked_plan(
            context_mode=mode,
            requested_keywords=raw_keywords or (),
            query_limit=query_limit,
            reason_code=reason_code,
            reason=reason,
            registry_counts=registry_counts,
            missing_domains=("CTH", "BMP"),
            source_policy=source_policy,
            rate_policy=rate_policy,
        )

    focus_entry: Optional[dict[str, Any]] = None
    focus_key = ""
    focus_scope: Optional[dict[str, Any]] = None
    if mode == FOCUS:
        requested_key = str(brand_focus_id or subject_id or "").strip()
        for entry in entries:
            keys = [entry["brand_focus_id"]] if focus_domain == "BMP" else [entry["subject_id"]]
            # BMP keeps ``subject_id`` as a compatibility identity while the
            # canonical acquisition scope is ``brand_focus_id``.  Accepting
            # the compatibility key here is a registry lookup, never a
            # guessed or synthesized scope.
            if focus_domain == "BMP":
                keys.append(entry["registry_id"])
                if brand_focus_id and subject_id and (
                    entry["brand_focus_id"] != brand_focus_id
                    or entry["registry_id"] != subject_id
                ):
                    continue
            if entry["domain_id"] == focus_domain and requested_key in keys:
                focus_entry = entry
                break
        if focus_entry is None:
            return _blocked_plan(
                context_mode=mode,
                requested_keywords=raw_keywords or (),
                query_limit=query_limit,
                reason_code="FOCUS_NOT_REGISTERED",
                reason="focused acquisition scope is not an active registry entry",
                registry_counts=registry_counts,
                missing_domains=tuple(domain for domain in ("CTH", "BMP") if not registry_counts[domain]),
                source_policy=source_policy,
                rate_policy=rate_policy,
            )
        focus_key = focus_entry["brand_focus_id"] or focus_entry["subject_id"]
        focus_scope = {
            "domain_id": "cth" if focus_domain == "CTH" else "zbmp",
            "product_id": focus_entry["product_id"],
            "subject_id": focus_entry["subject_id"],
            "brand_focus_id": focus_entry["brand_focus_id"],
            "scope_key": focus_key,
        }

    alias_index: dict[str, list[tuple[dict[str, Any], str, str]]] = {}
    for entry in entries:
        for alias, alias_kind in entry["aliases"]:
            alias_index.setdefault(_normalised_key(alias), []).append((entry, alias, alias_kind))

    candidates: list[tuple[dict[str, Any], str, str, str, int]] = []
    if raw_keywords is None:
        selected_entries = entries
        for entry in selected_entries:
            for alias, alias_kind in entry["aliases"]:
                priority = 0 if focus_entry is entry else 10
                reason_code = "focus_priority" if focus_entry is entry else "registered_alias"
                candidates.append((entry, alias, alias_kind, reason_code, priority))
    else:
        unresolved: list[str] = []
        for requested in raw_keywords:
            if focus_entry is not None:
                focus_matches = [
                    (alias, alias_kind)
                    for alias, alias_kind in focus_entry["aliases"]
                    if _normalised_key(alias) == _normalised_key(requested)
                ]
                if not focus_matches:
                    unresolved.append(requested)
                    continue
                alias, alias_kind = focus_matches[0]
                candidates.append((focus_entry, alias, alias_kind, "focus_keyword", 0))
                continue
            matches = alias_index.get(_normalised_key(requested), [])
            if not matches:
                unresolved.append(requested)
                continue
            for entry, alias, alias_kind in matches:
                candidates.append((entry, alias, alias_kind, "explicit_alias", 5))
        if unresolved:
            return _blocked_plan(
                context_mode=mode,
                requested_keywords=raw_keywords,
                query_limit=query_limit,
                reason_code="KEYWORD_SCOPE_UNRESOLVED",
                reason="one or more explicit keywords do not map to a registered scope",
                registry_counts=registry_counts,
                missing_domains=tuple(domain for domain in ("CTH", "BMP") if not registry_counts[domain]),
                source_policy=source_policy,
                rate_policy=rate_policy,
                focus_scope=focus_scope,
            )

    queries: list[AcquisitionQuery] = []
    seen: set[tuple[str, str, str]] = set()
    for entry, keyword, alias_kind, reason_code, priority in candidates:
        key = (_normalised_key(keyword), entry["domain_id"], entry["registry_id"])
        if key in seen:
            continue
        seen.add(key)
        queries.append(AcquisitionQuery(
            keyword=keyword,
            domain_id=entry["domain_id"],
            product_id=entry["product_id"],
            registry_id=entry["registry_id"],
            subject_id=entry["subject_id"],
            brand_focus_id=entry["brand_focus_id"],
            priority=priority,
            reason_code=reason_code,
            alias_kind=alias_kind,
            context_mode=mode,
        ))

    if business_requests is not None:
        queries = _purpose_queries(entries, business_requests, mode, focus_key)

    queries.sort(key=lambda item: (
        item.priority,
        item.domain_id,
        item.scope_key,
        _normalised_key(item.keyword),
    ))
    total_queries = len(queries)
    fingerprint = hashlib.sha256(json.dumps(
        [q.to_dict() for q in queries], ensure_ascii=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()
    offset = 0
    if continuation is not None:
        if (not isinstance(continuation, Mapping)
                or continuation.get("input_fingerprint") != fingerprint
                or type(continuation.get("offset")) is not int
                or not 0 <= continuation["offset"] <= total_queries):
            raise AcquisitionPlanError("continuation does not match current query inputs")
        offset = continuation["offset"]
    end = min(offset + query_limit, total_queries)
    truncated = end < total_queries
    next_cursor = {"offset": end, "input_fingerprint": fingerprint} if truncated else None
    queries = queries[offset:end]
    missing_domains = tuple(domain for domain in ("CTH", "BMP") if not registry_counts[domain])
    status = STAGED if missing_domains or invalid_count else READY
    reason_code = "REGISTRY_PARTIAL" if status == STAGED else ""
    if status == STAGED and missing_domains:
        reason = "plan is bounded to registered entries; one or more domains have no queryable entries"
    elif status == STAGED:
        reason = "plan is bounded to queryable registered entries; invalid registry rows are excluded"
    else:
        reason = ""
    return AcquisitionPlan(
        status=status,
        context_mode=mode,
        queries=tuple(queries),
        requested_keywords=tuple(raw_keywords or ()),
        registry_counts=registry_counts,
        missing_domains=missing_domains,
        truncated=truncated,
        query_limit=query_limit,
        reason_code=reason_code,
        reason=reason,
        source_policy=source_policy,
        rate_policy=rate_policy,
        focus_scope=focus_scope,
        total_queries=total_queries,
        next_cursor=next_cursor,
        input_fingerprint=fingerprint,
    )



_BUSINESS_DIMENSIONS = frozenset({
    "identity_discovery", "market_activity", "consumer_experience",
    "creator_content", "venue_operations",
})
_PRIMARY_PLATFORMS = frozenset({"xhs", "douyin", "wechat", "instagram", "x", "facebook"})
BUSINESS_RULE_VERSION = "lumenis.business-query.v2"


def _publication_boundary(value: Any, *, field: str):
    """Parse task time without supplying missing native time or timezone.

    A calendar date uses the supplied native timestamp's calendar date. A
    timestamp with an explicit offset compares instants. None adds no boundary.
    """
    from datetime import date, datetime

    if value is None:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise AcquisitionPlanError(f"{field} must be an ISO date or offset-aware timestamp")
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("offset required")
        return result
    except ValueError as exc:
        raise AcquisitionPlanError(f"{field} must be an ISO date or offset-aware timestamp") from exc


def _validate_publication_period(since=None, until=None):
    from datetime import datetime

    start = _publication_boundary(since, field="publication_since")
    end = _publication_boundary(until, field="publication_until")
    if start is not None and end is not None:
        if isinstance(start, datetime) and isinstance(end, datetime):
            reversed_period = start > end
        elif not isinstance(start, datetime) and not isinstance(end, datetime):
            reversed_period = start > end
        else:
            # Mixed precision needs the observed source offset. Comparing the
            # endpoint labels here would reject a valid local calendar day
            # whose UTC instant falls on the preceding date.
            reversed_period = False
        if reversed_period:
            raise AcquisitionPlanError("publication_since must not be after publication_until")
    return start, end


def _outside_publication_period(published, start, end) -> bool:
    from datetime import datetime

    return (
        start is not None and (published < start if isinstance(start, datetime)
                               else published.date() < start)
    ) or (
        end is not None and (published > end if isinstance(end, datetime)
                             else published.date() > end)
    )


def _public_query_target(value: Any) -> str:
    value = _normalise_text(value, field="source_url", max_length=2048)
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (parsed.scheme != "https" or not host or parsed.username or parsed.password
            or host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local")
            or set(parse_qs(parsed.query)) & {"access_token", "token", "api_key", "password"}):
        raise AcquisitionPlanError("tracking requires a public HTTPS source URL without credentials")
    return value


def _purpose_queries(entries, requests, mode, focus_key):
    """Compile selected task facets; never infer purpose or multiply all catalog topics."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise AcquisitionPlanError("business_requests must explicitly select task purposes and facets")
    seed = (load_approved_topic_seed() if any(
        isinstance(request, Mapping) and request.get("user_seed_topic_ref") is not None
        for request in requests) else None)
    result, seen = [], set()
    for request in requests:
        if not isinstance(request, Mapping):
            raise AcquisitionPlanError("each business request must be a mapping")
        domain = _normalise_domain(request.get("domain_id"))
        key = str(request.get("scope_key") or "").strip()
        entry = next((e for e in entries if e["domain_id"] == domain
            and key in {e["registry_id"], e["subject_id"], e["brand_focus_id"]}), None)
        discovery = request.get("unregistered_discovery") is True
        acquisition_stage = request.get("acquisition_stage")
        if acquisition_stage == "":
            acquisition_stage = None
        if acquisition_stage not in (None, "SUBJECT_INTAKE"):
            raise AcquisitionPlanError("acquisition_stage must be SUBJECT_INTAKE when supplied")
        subject_intake = acquisition_stage == "SUBJECT_INTAKE"
        if entry is None and not (discovery and not key):
            raise AcquisitionPlanError("business target is not registered; unknown discovery must keep ID null")
        if subject_intake and entry is None:
            raise AcquisitionPlanError("subject intake requires an existing registered entity")
        purpose = _normalise_text(request.get("purpose"), field="purpose", max_length=256)
        dimension = request.get("dimension")
        if not purpose or dimension not in _BUSINESS_DIMENSIONS:
            raise AcquisitionPlanError("explicit business purpose and approved dimension required")
        if dimension == "venue_operations" and domain != "CTH":
            raise AcquisitionPlanError("venue_operations requires a CTH venue target")
        platforms = _as_terms(request.get("platforms"), field="platforms")
        from .adapters.platform_naming import PLATFORM_ALIASES
        approved_names = set(PLATFORM_ALIASES) | {"wechat", "sogou_wechat"}
        if not platforms or any(p not in approved_names for p in platforms):
            raise AcquisitionPlanError("select existing named platforms explicitly")
        if request.get("user_seed_topic_ref") is not None:
            _verify_seed_reference(request["user_seed_topic_ref"], entry, platforms, seed)
        aliases = _as_terms(request.get("aliases"), field="aliases")
        registered_aliases = [a for a, _ in entry["aliases"]] if entry else []
        if entry:
            aliases = aliases or (registered_aliases if subject_intake else registered_aliases[:1])
            if any(_normalised_key(a) not in {_normalised_key(x) for x in registered_aliases} for a in aliases):
                raise AcquisitionPlanError("business alias is not supplied by the registry")
        elif aliases:
            raise AcquisitionPlanError("new entity discovery cannot invent an admitted entity alias")
        geography = _as_terms(request.get("geography_terms"), field="geography_terms")
        venue = _as_terms(request.get("venue_boundary_terms"), field="venue_boundary_terms")
        topics = _as_terms(request.get("topic_terms"), field="topic_terms")
        expansion = request.get("task_semantic_expansion")
        expansion_term = None
        if expansion is not None:
            if not isinstance(expansion, Mapping):
                raise AcquisitionPlanError("task_semantic_expansion must be an explicit term and reason")
            expansion_term = _normalise_text(expansion.get("term"), field="task_semantic_expansion.term", max_length=256)
            expansion_reason = _normalise_text(expansion.get("reason"), field="task_semantic_expansion.reason", max_length=512)
            if not expansion_term or not expansion_reason:
                raise AcquisitionPlanError("task_semantic_expansion requires a nonempty term and reason")
            if _normalised_key(expansion_term) not in {_normalised_key(t) for t in topics}:
                topics.append(expansion_term)
        exclude = _as_terms(request.get("exclude_terms"), field="exclude_terms")
        since = request.get("publication_since")
        until = request.get("publication_until")
        _validate_publication_period(since, until)
        tracking = request.get("tracking_sources") or []
        if not isinstance(tracking, (list, tuple)):
            raise AcquisitionPlanError("tracking_sources must be a list")
        if not tracking and not topics and not subject_intake:
            raise AcquisitionPlanError("select relevant topic terms; name-only is an identity seed, not a business plan")
        seeds = []
        if subject_intake:
            alias_kinds = {_normalised_key(alias): kind for alias, kind in entry["aliases"]}
            for alias in aliases:
                alias_key = _normalised_key(alias)
                disambiguation_terms = []
                seen_disambiguation = set()
                for term in geography + venue:
                    term_key = _normalised_key(term)
                    if term_key in alias_key or term_key in seen_disambiguation:
                        continue
                    seen_disambiguation.add(term_key)
                    disambiguation_terms.append(term)
                keyword = _normalise_text(
                    " ".join([alias] + disambiguation_terms),
                    field="business_query", max_length=256,
                )
                seeds.append((keyword, "DISCOVERY", None,
                              "SUBJECT_INTAKE_REGISTRY_ALIAS", alias_kinds[alias_key]))
        else:
            for alias in aliases or [""]:
                for topic in topics:
                    parts = [alias] + [v for v in geography + venue if v not in alias] + [topic]
                    keyword = _normalise_text(" ".join(p for p in parts if p), field="business_query", max_length=256)
                    origin = ("TASK_SEMANTIC_EXPANSION" if expansion_term
                              and _normalised_key(topic) == _normalised_key(expansion_term)
                              else "TASK_SELECTED_TOPIC")
                    seeds.append((keyword, "DISCOVERY", None, origin,
                                  "task_selected_registered_alias"))
        for source in tracking:
            if (not isinstance(source, Mapping) or not source.get("evidence_ref")
                    or source.get("scope_key") != key or entry is None):
                raise AcquisitionPlanError("tracking source needs matching entity and locatable identity evidence")
            seeds.append((_public_query_target(source.get("url")), "TRACKING",
                          str(source["evidence_ref"]), "SOURCE_TRACKING",
                          "task_selected_registered_alias"))
        for platform in platforms:
            for keyword, kind, source_ref, query_origin, query_alias_kind in seeds:
                unique = (platform, domain, key, purpose, dimension, keyword.casefold())
                if unique in seen:
                    continue
                seen.add(unique)
                context = {
                    "rule_version": BUSINESS_RULE_VERSION, "platform": platform, "purpose": purpose,
                    "dimension": dimension, "task_type": kind, "entity_aliases": tuple(aliases), "geography_terms": tuple(geography),
                    "query_origin": query_origin,
                    "venue_boundary_terms": tuple(venue), "topic_terms": tuple(topics),
                    "exclude_terms": tuple(exclude), "source_identity_evidence_ref": source_ref,
                    "publication_since": since, "publication_until": until,
                    "publication_boundary_basis": "NATIVE_CALENDAR_DATE_OR_EXPLICIT_OFFSET_INSTANT",
                    "time_role": "NATIVE_PUBLICATION_NOT_CAPTURE", "mode": "MANUAL",
                    "native_scope_bound": False, "source_use_grant": None,
                    "market_typed_ref": request.get("market_typed_ref"),
                    "unregistered_discovery": discovery and entry is None,
                    "user_seed_topic_ref": request.get("user_seed_topic_ref"),
                    "task_semantic_expansion": dict(expansion) if expansion is not None else None,
                }
                if subject_intake:
                    context["acquisition_stage"] = "SUBJECT_INTAKE"
                result.append(AcquisitionQuery(
                    keyword=keyword, domain_id=domain, product_id="CTH" if domain=="CTH" else "ZBMP",
                    registry_id=entry["registry_id"] if entry else "",
                    subject_id=entry["subject_id"] if entry else None,
                    brand_focus_id=entry["brand_focus_id"] if entry else None,
                    priority=0 if entry and focus_key in {entry["subject_id"],entry["brand_focus_id"]} else 10,
                    reason_code=("subject_intake" if subject_intake and entry else
                                 "business_purpose" if entry else "unregistered_discovery"),
                    alias_kind=query_alias_kind if entry else "UNASSIGNED",
                    context_mode=mode, business_context=context,
                ))
    return result


def assess_query_relevance(record: Mapping[str, Any], query: AcquisitionQuery) -> dict[str, Any]:
    """A source-linked lexical review aid, never admission/signature or consumer demand."""
    context = dict(query.business_context or {})
    text = " ".join(str(record.get(k) or "") for k in ("title", "body", "content", "native_topics")).casefold()
    reasons = []
    if any(str(t).casefold() in text for t in context.get("exclude_terms", ())):
        return {"status": "EXCLUDED_TASK_BOUNDARY", "derivative": True, "admitted": False}
    if not record.get("native_id") or not record.get("source_url") or not text.strip():
        reasons.append("SOURCE_ID_OR_LOCATABLE_BODY_MISSING")
    if not record.get("published_at"):
        reasons.append("NATIVE_PUBLICATION_UNKNOWN")
    aliases = context.get("entity_aliases", ())
    if aliases and not any(str(a).casefold() in text for a in aliases):
        reasons.append("ENTITY_ALIAS_NOT_OBSERVED")
    from datetime import datetime
    stamp = record.get("published_at")
    if stamp:
        try:
            published = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
            if published.tzinfo is None:
                raise ValueError("native offset unavailable")
            start, end = _validate_publication_period(
                context.get("publication_since"), context.get("publication_until"))
            if _outside_publication_period(published, start, end):
                return {"status": "OUTSIDE_REQUESTED_PUBLICATION_PERIOD", "derivative": True, "admitted": False}
            capture = record.get("capture_observation_utc")
            if capture is None:
                reasons.append("ACTUAL_CAPTURE_CUTOFF_MISSING")
            if capture is not None:
                observed = datetime.fromisoformat(str(capture).replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    raise ValueError("observation offset unavailable")
                if published > observed:
                    reasons.append("PUBLICATION_AFTER_ACTUAL_OBSERVATION")
        except (ValueError, TypeError):
            reasons.append("NATIVE_PUBLICATION_PRECISION_OR_OFFSET_UNVERIFIED")
    terms = context.get("topic_terms", ())
    if (context.get("acquisition_stage") != "SUBJECT_INTAKE" and terms
            and not any(all(part.casefold() in text for part in str(term).split()) for term in terms)):
        reasons.append("TASK_TOPIC_NOT_OBSERVED")
    boundaries = context.get("geography_terms", ()) + context.get("venue_boundary_terms", ())
    if boundaries and not all(str(t).casefold() in text for t in boundaries):
        reasons.append("REQUEST_BOUNDARY_NOT_OBSERVED")
    # The lexical result does not bind the entity; existing Evidence/Permission
    # owners still verify exact entity/market, source identity, time and use.
    return {"status": "REVIEW_REQUIRED" if reasons else "CANDIDATE_TASK_RELEVANT",
            "reasons": reasons, "derivative": True, "method": BUSINESS_RULE_VERSION,
            "admitted": False, "entity_scope_verified": False, "source_use_grant": None}

def build_observed_topic_catalog(observations: Iterable[Mapping[str, Any]], *,
                                 publication_since=None, publication_until=None,
                                 candidate_origin="NATIVE_PLATFORM_TOPIC") -> dict[str, Any]:
    """Retain source-linked topic candidates without granting admission.

    Native topics must carry inspected native-field locators. Derived text terms
    must carry exact body locators, a verified body hash, and current READ and
    ANALYZE audit/source references. This pure function owns no store or effects.
    """
    from datetime import datetime

    allowed_origins = {"NATIVE_PLATFORM_TOPIC", "DERIVED_SOURCE_BODY"}
    if not isinstance(candidate_origin, str) or candidate_origin not in allowed_origins:
        raise AcquisitionPlanError("unsupported observed topic candidate origin")

    start, end = _validate_publication_period(publication_since, publication_until)
    entries: dict[tuple[str, str, str], dict[str, Any]] = {}
    review = []
    input_count = 0
    required_formal_refs = (
        "read_audit_ref", "analyze_audit_ref", "source_evidence_ref",
        "source_artifact_ref", "source_evidence_version",
    )

    for observation in observations:
        input_count += 1
        platform = str(observation.get("platform") or "").strip()
        native_id = str(observation.get("platform_content_id") or "").strip()
        raw_ref = observation.get("native_raw_ref") or {}
        reason = None
        source_body = None
        body_sha256 = None
        source_use_refs = None
        try:
            source_url = _public_query_target(observation.get("source_url"))
            published = datetime.fromisoformat(str(observation.get("native_publication") or "").replace("Z", "+00:00"))
            captured = datetime.fromisoformat(str(observation.get("capture_observation_utc") or "").replace("Z", "+00:00"))
            if published.tzinfo is None or captured.tzinfo is None:
                reason = "NATIVE_TIME_OFFSET_UNKNOWN"
            elif _outside_publication_period(published, start, end):
                reason = "OUTSIDE_REQUESTED_PUBLICATION_PERIOD"
            elif published > captured:
                reason = "PUBLICATION_AFTER_ACTUAL_OBSERVATION"
            if candidate_origin == "NATIVE_PLATFORM_TOPIC":
                if (not platform or not native_id or not isinstance(raw_ref, Mapping)
                        or not re.fullmatch(r"[0-9a-f]{64}", str(raw_ref.get("sha256") or ""))
                        or not raw_ref.get("path")):
                    reason = "NATIVE_SOURCE_REFERENCE_MISSING"
            elif reason is None:
                if not platform or not native_id:
                    reason = "DERIVED_SOURCE_IDENTITY_MISSING"
                else:
                    source_body = observation.get("source_body")
                    body_sha256 = observation.get("body_sha256")
                    if not isinstance(source_body, str) or not source_body.strip():
                        reason = "DERIVED_SOURCE_BODY_MISSING"
                    elif (not isinstance(body_sha256, str)
                          or not re.fullmatch(r"[0-9a-f]{64}", body_sha256)
                          or hashlib.sha256(source_body.encode("utf-8")).hexdigest() != body_sha256):
                        reason = "DERIVED_SOURCE_BODY_HASH_INVALID"
                    else:
                        formal_refs = observation.get("formal_refs")
                        if (not isinstance(formal_refs, Mapping)
                                or any(not isinstance(formal_refs.get(ref), str)
                                       or not formal_refs[ref].strip()
                                       for ref in required_formal_refs)):
                            reason = "DERIVED_SOURCE_USE_REFS_INCOMPLETE"
                        else:
                            source_use_refs = {ref: formal_refs[ref] for ref in required_formal_refs}
                        if reason is None and "derived_topics" not in observation:
                            reason = "DERIVED_CANDIDATES_MISSING"
                        elif reason is None and not isinstance(observation.get("derived_topics"), (list, tuple)):
                            reason = "DERIVED_CANDIDATES_INVALID"
        except (ValueError, TypeError, UnicodeEncodeError):
            reason = "NATIVE_TIME_OR_PUBLIC_SOURCE_UNVERIFIED"

        def add_review(review_reason, *, candidate=None):
            item = {"platform": platform, "platform_content_id": native_id,
                    "reason": review_reason}
            if candidate_origin == "NATIVE_PLATFORM_TOPIC":
                item["native_raw_ref"] = dict(raw_ref) if isinstance(raw_ref, Mapping) else None
            else:
                item["candidate_origin"] = candidate_origin
                if isinstance(body_sha256, str):
                    item["source_body_sha256"] = body_sha256
                if source_use_refs is not None:
                    item["source_use_refs"] = dict(source_use_refs)
                if isinstance(candidate, Mapping) and isinstance(candidate.get("term"), str):
                    item["candidate_term"] = candidate["term"]
            review.append(item)

        if reason:
            add_review(reason)
            continue

        if candidate_origin == "NATIVE_PLATFORM_TOPIC":
            topics = observation.get("native_topics") or []
            if not isinstance(topics, (list, tuple)):
                raise AcquisitionPlanError("native_topics must contain inspected native fields")
        else:
            topics = observation["derived_topics"]

        for topic in topics:
            if candidate_origin == "NATIVE_PLATFORM_TOPIC":
                if not isinstance(topic, Mapping):
                    raise AcquisitionPlanError("native topic text needs its original field locator")
                literal = topic.get("text")
                locator = str(topic.get("native_locator") or "")
                if (not isinstance(literal, str) or not literal.strip()
                        or _CONTROL_CHARS.search(literal) or len(literal) > 256
                        or not locator.startswith("/") or locator == "/"):
                    add_review("NATIVE_TOPIC_LOCATOR_OR_TEXT_INVALID", candidate=topic)
                    continue
                term = literal.strip().removeprefix("#")
                if not term.strip():
                    add_review("NATIVE_TOPIC_EMPTY", candidate=topic)
                    continue
                topic_id = topic.get("native_topic_id")
                processing_version = None
                body_locators = None
                source_kind = None
                occurrence_count = None
            else:
                if not isinstance(topic, Mapping):
                    add_review("DERIVED_CANDIDATE_FIELDS_INVALID", candidate=topic)
                    continue
                literal = topic.get("term")
                kind = topic.get("kind")
                processing_version = topic.get("algorithm_version")
                body_locators = topic.get("body_locators")
                occurrence_count = topic.get("occurrence_count")
                if (not isinstance(literal, str) or not literal.strip()
                        or _CONTROL_CHARS.search(literal) or len(literal) > 256):
                    add_review("DERIVED_CANDIDATE_TERM_INVALID", candidate=topic)
                    continue
                if (not isinstance(kind, str)
                        or kind not in {"DERIVED_TEXT_KEYWORD", "VERBATIM_BODY_HASHTAG_LITERAL"}):
                    add_review("DERIVED_CANDIDATE_KIND_UNSUPPORTED", candidate=topic)
                    continue
                if processing_version != "deterministic-collector-keywords:v1":
                    add_review("DERIVED_PROCESSING_VERSION_UNSUPPORTED", candidate=topic)
                    continue
                if (topic.get("owned_inference") != "NOT_RUN"
                        or topic.get("platform_heat") is not None
                        or topic.get("representative_demand") is not None
                        or topic.get("admitted") is not False
                        or topic.get("automatic_adoption") is not False
                        or topic.get("native_topic_id") not in (None, "")):
                    add_review("DERIVED_CANDIDATE_STATE_INVALID", candidate=topic)
                    continue
                substring_count = source_body.count(literal)
                if kind == "VERBATIM_BODY_HASHTAG_LITERAL":
                    actual_count = sum(
                        match.group(0) == literal
                        for match in re.finditer(r"(?<!#)#[\w]+", source_body, flags=re.UNICODE)
                    )
                    valid_occurrence_counts = {actual_count}
                else:
                    english_pattern = re.compile(
                        r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9]*)(?![A-Za-z0-9])"
                    )
                    english_count = sum(
                        match.group(1) == literal
                        and sum(char.isascii() and char.isalpha() for char in literal) >= 2
                        for match in english_pattern.finditer(source_body)
                    )
                    valid_occurrence_counts = {substring_count, english_count}
                if (not isinstance(body_locators, (list, tuple))
                        or not 1 <= len(body_locators) <= 5
                        or type(occurrence_count) is not int or occurrence_count < len(body_locators)
                        or occurrence_count not in valid_occurrence_counts):
                    add_review("DERIVED_CANDIDATE_LOCATORS_OR_COUNT_INVALID", candidate=topic)
                    continue
                checked_locators = []
                locator_invalid = False
                for body_locator in body_locators:
                    if (not isinstance(body_locator, Mapping)
                            or set(body_locator) != {"unit", "json_path", "start", "end", "offset_unit"}
                            or body_locator.get("unit") != "source-body"
                            or body_locator.get("json_path") != "$.body"
                            or body_locator.get("offset_unit") != "unicode-codepoint"):
                        locator_invalid = True
                        break
                    start_offset, end_offset = body_locator.get("start"), body_locator.get("end")
                    if (type(start_offset) is not int or type(end_offset) is not int
                            or not 0 <= start_offset < end_offset <= len(source_body)
                            or source_body[start_offset:end_offset] != literal):
                        locator_invalid = True
                        break
                    checked_locators.append({key: body_locator[key] for key in (
                        "unit", "json_path", "start", "end", "offset_unit")})
                if locator_invalid or len({(row["start"], row["end"]) for row in checked_locators}) != len(checked_locators):
                    add_review("DERIVED_BODY_LOCATOR_INVALID", candidate=topic)
                    continue
                term = literal
                topic_id = None
                source_kind = kind
                body_locators = checked_locators

            key = (platform, candidate_origin, term.casefold())
            node_defaults = {
                "platform": platform, "term": term, "original_spellings": [],
                "native_topic_ids": [], "observations": [],
                "distinct_content_keys": [], "planned_tasks": [],
                "canonical_entity_refs": None, "source_use_ref": None,
                "admitted": False, "scope_status": "UNASSIGNED",
            }
            if candidate_origin == "DERIVED_SOURCE_BODY":
                node_defaults.update({"candidate_origin": candidate_origin,
                                      "processing_version": processing_version})
            node = entries.setdefault(key, node_defaults)
            if literal not in node["original_spellings"]:
                node["original_spellings"].append(literal)
            if topic_id not in (None, "") and str(topic_id) not in node["native_topic_ids"]:
                node["native_topic_ids"].append(str(topic_id))
            native_key = platform + ":" + native_id
            if native_key not in node["distinct_content_keys"]:
                node["distinct_content_keys"].append(native_key)
            if candidate_origin == "NATIVE_PLATFORM_TOPIC":
                source = {"platform_content_id": native_id, "source_url": source_url,
                          "native_publication": observation["native_publication"],
                          "capture_observation_utc": observation["capture_observation_utc"],
                          "native_raw_ref": dict(raw_ref), "native_locator": locator,
                          "original_topic_text": literal, "rights": observation.get("rights"),
                          "source_evidence_canonical_use_refs": observation.get("formal_refs")}
            else:
                source = {"platform_content_id": native_id, "source_url": source_url,
                    "native_publication": observation["native_publication"],
                    "capture_observation_utc": observation["capture_observation_utc"],
                    "rights": observation.get("rights"),
                    "candidate_origin": candidate_origin,
                    "candidate_kind": source_kind,
                    "original_candidate_term": literal,
                    "body_locators": body_locators,
                    "occurrence_count": occurrence_count,
                    "source_body_sha256": body_sha256,
                    "source_use_refs": dict(source_use_refs),
                    "source_evidence_canonical_use_refs": dict(source_use_refs),
                    "processing_version": processing_version,
                }
            if source not in node["observations"]:
                node["observations"].append(source)
            task = observation.get("planned_task")
            if task and task not in node["planned_tasks"]:
                node["planned_tasks"].append(task)
    nodes = list(entries.values())
    for node in nodes:
        node["sample_distinct_content_count"] = len(node["distinct_content_keys"])
    catalog = {"version": "lumenis.observed-topic-catalog.v2", "input_observation_count": input_count,
               "publication_since": publication_since, "publication_until": publication_until,
               "publication_boundary_basis": "NATIVE_CALENDAR_DATE_OR_EXPLICIT_OFFSET_INSTANT",
               "time_role": "NATIVE_PUBLICATION_NOT_CAPTURE",
               "terms": nodes, "review": review, "platform_heat": None,
               "representative_demand": None, "automatic_adoption": False,
               "purpose": "SOURCE_LINKED_DISCOVERY_AND_TASK_QUERY_REVIEW", "admitted": False}
    if candidate_origin == "DERIVED_SOURCE_BODY":
        catalog["candidate_origin"] = candidate_origin
    return catalog


def resolve_query_plan(*args: Any, **kwargs: Any) -> AcquisitionPlan:
    """Compatibility spelling for callers that use a resolver vocabulary."""

    return build_acquisition_plan(*args, **kwargs)


def build_query_plan(*args: Any, **kwargs: Any) -> AcquisitionPlan:
    """Compatibility spelling for scheduler/adaptor integrations."""

    return build_acquisition_plan(*args, **kwargs)


AcquisitionQueryPlan = AcquisitionPlan


__all__ = [
    "AcquisitionPlan",
    "AcquisitionPlanError",
    "AcquisitionQuery",
    "AcquisitionQueryPlan",
    "BLOCKED",
    "FOCUS",
    "GLOBAL_ALL",
    "READY",
    "STAGED",
    "build_acquisition_plan",
    "build_query_plan",
    "resolve_query_plan",
]
