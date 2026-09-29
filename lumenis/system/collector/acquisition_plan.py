"""Scope-aware acquisition query planning for the SYSTEM Collector.

The planner resolves a bounded set of public-source queries from the canonical
Subject registry before any collector, browser, profile, session, or network
operation is attempted.  It is deliberately a pure planning boundary: source
policy is read for safe metadata only, while collection identity and effects
remain owned by the existing runtime callers.
"""

from __future__ import annotations

from dataclasses import dataclass
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
            "global_scope": False,
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
        if status == "archived":
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

    if not entries:
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

    queries.sort(key=lambda item: (
        item.priority,
        item.domain_id,
        item.scope_key,
        _normalised_key(item.keyword),
    ))
    truncated = len(queries) > query_limit
    queries = queries[:query_limit]
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
    )


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
