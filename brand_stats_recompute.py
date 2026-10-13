"""Recompute brand aggregates from the existing scoped Canonical owner.

The aggregation table is a compatibility projection. This module does not
authenticate scope, verify Source quality, or establish commercial readiness;
those guarantees must come from the server-held callbacks and their existing
owners.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from canonical_metrics import (
    engagement_count,
    engagement_stats,
    risk_count,
    sentiment_count,
)
from lumenis.shared.database import DatabaseRepository, main_db_path

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = main_db_path()
_CANONICAL_ENGAGEMENT_KEYS = (
    "engagement_likes",
    "engagement_comments",
    "engagement_collects",
    "engagement_shares",
)
_SNAPSHOT_FIELDS = {
    "records", "candidate_count", "scanned_count", "returned_count",
    "rejected_count", "limit", "truncated",
}
_AUDIT_FIELDS = ("permission_audit_ref", "operation_audit_ref")


def _to_int(value: Any) -> int | None:
    """Compatibility wrapper using the canonical exact-count parser."""
    return engagement_count(value)


def _brand_keys(chinese_name: Any, english_name: Any) -> list[str]:
    """Return the existing nonempty brand-name keys without inventing aliases."""
    keys: list[str] = []
    if isinstance(chinese_name, str) and chinese_name.strip():
        keys.append(chinese_name.strip())
    english = english_name.strip() if isinstance(english_name, str) else ""
    if len(english) >= 3:
        keys.append(english)
    return keys


def _known_complete(counts: Mapping[str, Any], *, buckets: Iterable[str], total: int) -> bool:
    return (
        all(type(counts.get(bucket)) is int for bucket in buckets)
        and sum(counts[bucket] for bucket in buckets) == total
    )


def aggregate_brand_observations(
    rows: Iterable[Mapping[str, Any]], *, complete_scan: bool,
) -> dict[str, Any]:
    """Aggregate scoped Canonical rows without turning unknown into zero.

    ``complete_scan`` describes the validated snapshot boundary. It must be an
    explicit bool; the metric owners separately establish classification and
    engagement-component coverage.
    """
    if type(complete_scan) is not bool:
        raise TypeError("complete_scan must be an explicit boolean")
    if isinstance(rows, (str, bytes, Mapping)):
        raise TypeError("rows must be an iterable of Canonical row mappings")
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("each Canonical row must be a mapping")
        normalized.append(dict(row))

    sentiment = sentiment_count(normalized)
    risk = risk_count(normalized)
    engagement = engagement_stats(normalized, keys=_CANONICAL_ENGAGEMENT_KEYS)
    observed_count = len(normalized)

    if observed_count == 0:
        state = "NOT_COLLECTED" if complete_scan else "PARTIAL"
    else:
        sentiment_complete = sentiment["unknown"] == 0
        risk_complete = _known_complete(
            risk,
            buckets=("high", "medium", "low", "critical"),
            total=observed_count,
        )
        engagement_complete = engagement["quality"]["state"] == "COMPLETE"
        state = (
            "COMPLETE"
            if complete_scan and sentiment_complete and risk_complete and engagement_complete
            else "PARTIAL"
        )

    sentiment_complete = observed_count > 0 and sentiment["unknown"] == 0
    risk_complete = observed_count > 0 and _known_complete(
        risk,
        buckets=("high", "medium", "low", "critical"),
        total=observed_count,
    )

    values: dict[str, Any] = {
        "note_count": observed_count if complete_scan and observed_count else None,
        "positive_count": (
            sentiment["positive"] if complete_scan and sentiment_complete else None
        ),
        "neutral_count": (
            sentiment["neutral"] if complete_scan and sentiment_complete else None
        ),
        "negative_count": (
            sentiment["negative"] if complete_scan and sentiment_complete else None
        ),
        "total_engagement": (
            engagement["sum"] if complete_scan and observed_count else None
        ),
        "risk_level": None,
    }
    if complete_scan and observed_count and sentiment_complete and risk_complete:
        if sentiment["negative"] and (risk["high"] or risk["critical"]):
            values["risk_level"] = "high"
        elif sentiment["negative"]:
            values["risk_level"] = "medium"
        else:
            values["risk_level"] = "low"

    return {
        "state": state,
        "values": values,
        "observed": {
            "record_count": observed_count,
            "sentiment": sentiment,
            "risk": risk,
            "engagement": engagement,
        },
        "quality": {
            "sentiment_complete": sentiment_complete,
            "risk_complete": risk_complete,
            "engagement": engagement["quality"],
            "complete_scan": complete_scan,
        },
        "source_basis": "SCOPED_CANONICAL_FROM_OWNER",
        "canonical_runtime_verified": False,
        "live_state": "LIVE_NOT_VERIFIED",
        "commercial_state": "COMMERCIAL_NOT_VERIFIED",
        "commercial_ready": False,
        "scope_proof_limit": (
            "Canonical scope lineage proof does not establish Source quality or "
            "sentiment/risk classification correctness."
        ),
        "aggregate_projection_bound": False,
        "normal_dependency": (
            "The server-held reader supplies rows from the existing scoped Canonical "
            "and Source owners. The aggregate table has no scoped identity/source-version "
            "contract; W6 must bind that projection before live or commercial claims."
        ),
    }


def _validated_snapshot(snapshot: Any) -> tuple[list[dict[str, Any]], bool, dict[str, Any]]:
    if not isinstance(snapshot, dict) or not _SNAPSHOT_FIELDS.issubset(snapshot):
        raise ValueError("scoped Canonical snapshot is malformed")
    records = snapshot["records"]
    if type(records) is not list or any(not isinstance(row, dict) for row in records):
        raise ValueError("scoped Canonical records are malformed")
    for name in ("candidate_count", "scanned_count", "returned_count", "rejected_count"):
        if type(snapshot[name]) is not int or snapshot[name] < 0:
            raise ValueError("scoped Canonical snapshot counts are malformed")
    limit = snapshot["limit"]
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("scoped Canonical snapshot limit is malformed")
    if type(snapshot["truncated"]) is not bool:
        raise ValueError("scoped Canonical truncation state is malformed")

    candidates = snapshot["candidate_count"]
    scanned = snapshot["scanned_count"]
    returned = snapshot["returned_count"]
    rejected = snapshot["rejected_count"]
    truncated = snapshot["truncated"]
    if (
        returned != len(records)
        or scanned != returned + rejected
        or scanned > candidates
        or scanned > limit
        or truncated is not (candidates > scanned)
    ):
        raise ValueError("scoped Canonical snapshot counts are inconsistent")

    # Current Canonical reads attach the verified scope proof to every row.
    # This structural check does not independently authenticate that proof.
    canonical_ids = set()
    source_ids = set()
    domain_pairs = set()
    scope_bindings = set()
    for record in records:
        canonical_id = record.get("canonical_id")
        source_id = record.get("source_id")
        evidence_ref = record.get("scope_evidence_ref")
        if (
            type(canonical_id) is not str or not canonical_id.strip()
            or canonical_id != canonical_id.strip()
            or type(source_id) is not str or not source_id.strip()
            or source_id != source_id.strip()
            or type(evidence_ref) is not str or not evidence_ref.strip()
            or evidence_ref != evidence_ref.strip()
        ):
            raise ValueError("scoped Canonical identity and Source references must be exact nonempty strings")
        product_id = record.get("product_id")
        domain_id = record.get("domain_id")
        if (product_id, domain_id) not in {("CTH", "cth"), ("ZBMP", "zbmp")}:
            raise ValueError("scoped Canonical product/domain identity is invalid")
        domain_pairs.add((product_id, domain_id))
        subject_id = record.get("subject_id") or ""
        brand_focus_id = record.get("brand_focus_id") or ""
        if subject_id and brand_focus_id:
            raise ValueError("scoped Canonical row mixes Subject and BrandFocus")
        focus_id = subject_id if product_id == "CTH" else brand_focus_id
        other_focus = brand_focus_id if product_id == "CTH" else subject_id
        if (
            type(focus_id) is not str or not focus_id.strip()
            or focus_id != focus_id.strip()
            or other_focus not in ("", None)
        ):
            raise ValueError("scoped Canonical row has no exact single focus identity")
        scope_bindings.add((product_id, domain_id, focus_id))
        if canonical_id in canonical_ids or source_id in source_ids:
            raise ValueError("scoped Canonical identities or Source references are duplicated")
        canonical_ids.add(canonical_id)
        source_ids.add(source_id)

        proof = record.get("scope_evidence")
        if not isinstance(proof, dict) or not isinstance(proof.get("integrity"), dict):
            raise ValueError("scoped Canonical row is missing its owner proof")
        integrity = proof["integrity"]
        stored_scope = proof.get("stored_scope")
        if (
            type(proof.get("id")) is not str or not proof.get("id", "").strip()
            or type(proof.get("source_id")) is not str or not proof.get("source_id", "").strip()
            or proof.get("id") != record.get("scope_evidence_ref")
            or proof.get("source_id") != record.get("source_id")
            or integrity.get("verified") is not True
            or integrity.get("lineage_verified") is not True
            or integrity.get("assurance") != "writer-authenticated"
            or not isinstance(stored_scope, dict)
            or stored_scope.get("product_id") != record.get("product_id")
            or stored_scope.get("domain_id") != record.get("domain_id")
            or stored_scope.get("subject_id") != (record.get("subject_id") or "")
            or stored_scope.get("brand_focus_id") != (record.get("brand_focus_id") or "")
            or stored_scope.get("scope_status") != record.get("scope_status")
            or record.get("scope_status") != "VERIFIED"
        ):
            raise ValueError("scoped Canonical owner proof is inconsistent")

    if len(domain_pairs) > 1 or len(scope_bindings) > 1:
        raise ValueError("scoped Canonical snapshot mixes product/domain or focus identities")

    full_scan = (
        not truncated
        and candidates == scanned == returned
        and rejected == 0
    )
    return records, full_scan, {
        "candidate_count": candidates,
        "scanned_count": scanned,
        "returned_count": returned,
        "rejected_count": rejected,
        "limit": limit,
        "truncated": truncated,
    }


def _authorization_receipt(authorize: Callable[[], Any]) -> dict[str, str]:
    try:
        receipt = authorize()
    except Exception:
        raise PermissionError("brand aggregate authorization is unavailable") from None
    if not isinstance(receipt, Mapping):
        raise PermissionError("brand aggregate authorization is invalid")
    values: dict[str, str] = {}
    for field in _AUDIT_FIELDS:
        value = receipt.get(field)
        if type(value) is not str or not value.strip() or value != value.strip():
            raise PermissionError("brand aggregate authorization is invalid")
        values[field] = value
    return values


def recompute_brand_stats(
    db_path: str | None = DB_PATH,
    verbose: bool = True,
    *,
    read_brand_records: Callable[[sqlite3.Connection, Mapping[str, Any]], Any] | None = None,
    authorize: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Refresh compatibility aggregates from a server-bound scoped Canonical read.

    The callbacks are required and must be supplied by server-side existing
    owners. Without them this function fails before opening the database.
    """
    if not callable(read_brand_records) or not callable(authorize):
        raise PermissionError("server-held scoped Canonical callbacks are required")

    _authorization_receipt(authorize)
    repository = DatabaseRepository(db_path)
    updated = 0
    nonzero = 0
    negative_brands = set()
    positive_brands = set()
    samples = []
    brand_results: list[dict[str, Any]] = []
    final_authorization_receipt: dict[str, str] = {}

    with repository.transaction() as conn:
        # DatabaseRepository.transaction supplies commit/rollback/close; acquire
        # the write reservation first so brand selection, Canonical reads and
        # compatibility updates share one SQLite transaction snapshot.
        conn.execute("BEGIN IMMEDIATE")
        conn.row_factory = sqlite3.Row
        brands = [dict(row) for row in conn.execute(
            "SELECT id, brand_name, brand_name_cn FROM brand_industry_monitor"
        ).fetchall()]
        final_authorization_receipt = _authorization_receipt(authorize)

        for brand in brands:
            keys = _brand_keys(brand.get("brand_name_cn"), brand.get("brand_name"))
            brand_label = brand.get("brand_name_cn") or brand.get("brand_name") or str(brand["id"])
            if not keys:
                brand_results.append({
                    "brand_id": brand["id"],
                    "brand": brand_label,
                    "state": "UNAVAILABLE",
                    "reason": "NO_BRAND_KEYWORDS",
                    "values": {
                        "note_count": None,
                        "positive_count": None,
                        "neutral_count": None,
                        "negative_count": None,
                        "total_engagement": None,
                        "risk_level": None,
                    },
                    "source_basis": "SCOPED_CANONICAL_FROM_OWNER",
                    "canonical_runtime_verified": False,
                    "live_state": "LIVE_NOT_VERIFIED",
                    "commercial_state": "COMMERCIAL_NOT_VERIFIED",
                    "commercial_ready": False,
                    "skip_reason": "Brand has no usable existing Chinese or English keyword.",
                })
                continue

            _authorization_receipt(authorize)
            try:
                snapshot = read_brand_records(conn, brand)
            except Exception:
                raise RuntimeError("scoped Canonical brand read failed") from None
            final_authorization_receipt = _authorization_receipt(authorize)
            try:
                rows, full_scan, snapshot_counts = _validated_snapshot(snapshot)
            except (TypeError, ValueError):
                raise ValueError("scoped Canonical snapshot failed validation") from None

            aggregate = aggregate_brand_observations(rows, complete_scan=full_scan)
            aggregate["snapshot"] = snapshot_counts
            aggregate["brand_id"] = brand["id"]
            aggregate["brand"] = brand_label
            if not rows:
                aggregate["reason"] = "NO_CANONICAL_RECORDS_IN_SCOPED_SNAPSHOT"
            elif not full_scan:
                aggregate["reason"] = "SCOPED_CANONICAL_SNAPSHOT_INCOMPLETE"

            values = aggregate["values"]
            conn.execute(
                "UPDATE brand_industry_monitor SET note_count=?, positive_count=?, "
                "negative_count=?, total_engagement=?, risk_level=?, "
                "last_updated=datetime('now','localtime') WHERE id=?",
                (
                    values["note_count"],
                    values["positive_count"],
                    values["negative_count"],
                    values["total_engagement"],
                    values["risk_level"] or "unknown",
                    brand["id"],
                ),
            )
            updated += 1
            if values["note_count"] is not None and values["note_count"] > 0:
                nonzero += 1
                if len(samples) < 12:
                    samples.append((brand_label, values["note_count"], values["positive_count"], values["negative_count"]))
            if values["negative_count"] is not None and values["negative_count"] > 0:
                negative_brands.add(brand["id"])
            if values["positive_count"] is not None and values["positive_count"] > 0:
                positive_brands.add(brand["id"])
            brand_results.append(aggregate)

        final_authorization_receipt = _authorization_receipt(authorize)

    result = {
        "updated": updated,
        "nonzero": nonzero,
        "negative_brands": len(negative_brands),
        "positive_brands": len(positive_brands),
        "samples": samples,
        "brands": brand_results,
        "source_basis": "SCOPED_CANONICAL_FROM_OWNER",
        "canonical_runtime_verified": False,
        "live_state": "LIVE_NOT_VERIFIED",
        "commercial_state": "COMMERCIAL_NOT_VERIFIED",
        "commercial_ready": False,
        "scope_proof_limit": (
            "Canonical scope lineage proof does not establish Source quality or "
            "sentiment/risk classification correctness."
        ),
        "aggregate_projection_bound": False,
        "final_authorization_receipt": final_authorization_receipt,
        "authorization_receipt_is_scope_proof": False,
        "normal_dependency": (
            "Each checkpoint calls the server-held authorization owner for a fresh "
            "receipt; that owner must enforce the current exact actor/Scope. A "
            "receipt is audit metadata, not Scope proof. The reader must use the "
            "existing scoped Canonical and Source owners and request source_level=True. "
            "The aggregate table has no scoped identity/source-version contract; W6 "
            "must bind the projection before live or commercial claims."
        ),
    }
    if verbose:
        print(
            f"[BrandStats] compatibility projection updated for {updated} brands; "
            "Canonical runtime and commercial readiness remain unverified"
        )
    return result


__all__ = ["_to_int", "aggregate_brand_observations", "recompute_brand_stats"]
