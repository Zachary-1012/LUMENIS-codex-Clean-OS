"""Persist platform fields only after exact Evidence and Canonical scope promotion."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from lumenis.shared.database import get_repository
from lumenis.shared.evidence.store import classify_evidence_integrity
from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized


_CONTENT_FIELDS = (
    "content_type", "author_id", "author_name", "title", "content",
    "published_at", "url", "like_count", "comment_count", "share_count",
    "collect_count", "view_count", "topic_list", "hashtag_list",
    "mention_list", "media_list", "language", "location",
)
_JSON_FIELDS = frozenset({"topic_list", "hashtag_list", "mention_list", "media_list"})


def _row_dict(cursor, row) -> dict[str, Any]:
    return dict(zip((column[0] for column in cursor.description), row))


def _scope_identity(scope: Mapping[str, Any]) -> tuple[str, str, str | None, str | None]:
    domain = str(scope.get("domain_id") or "").strip().lower()
    subject = scope.get("subject_id") or None
    brand = scope.get("brand_focus_id") or None
    if scope.get("global_scope") is True:
        raise ValueError("GLOBAL is a view, not an exact content scope")
    if domain == "cth" and subject and not brand:
        return "CTH", "cth", str(subject), None
    if domain == "bmp" and brand and not subject:
        return "ZBMP", "zbmp", None, str(brand)
    raise ValueError("exact CTH Subject or BMP BrandFocus is required")


def _stable_observation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Drop transport timestamps that change on every read, retaining source data."""
    return {
        key: value for key, value in record.items()
        if key not in {"captured_at", "collected_at", "last_collected_at",
                       "_lumenis_evidence_id"}
    }


def platform_records_changed(
    records: Sequence[Mapping[str, Any]], *, platform: str,
) -> bool:
    """Return whether the source observation differs from the saved native row."""
    normalized = [map_raw_to_normalized(dict(record), platform) for record in records]
    if not normalized:
        return False
    with get_repository().transaction() as conn:
        for record, content in zip(records, normalized):
            content_id = str(content.get("platform_content_id") or "").strip()
            if not content_id:
                return True
            row = conn.execute(
                "SELECT raw_data FROM platform_contents WHERE platform=? AND platform_content_id=?",
                (platform, content_id),
            ).fetchone()
            if row is None:
                return True
            try:
                prior = json.loads(row[0] or "{}")
            except (TypeError, ValueError):
                return True
            if _stable_observation(prior) != _stable_observation(dict(record)):
                return True
    return False


def persist_verified_platform_records(
    records: Sequence[Mapping[str, Any]], *, platform: str,
    note_ids: Sequence[str], evidence_id: int, scope: Mapping[str, Any],
) -> int:
    """Save native and comparable fields through the existing Shared DB owner.

    The Collector calls this only after its raw note import and Canonical sync.
    This function rechecks every row and the Evidence in one transaction. A
    failure writes no platform rows or metric observations.
    """
    if not isinstance(evidence_id, int) or isinstance(evidence_id, bool) or evidence_id <= 0:
        raise ValueError("a persisted Evidence id is required")
    if not records or len(records) > 200:
        raise ValueError("bounded non-empty records are required")
    product, domain, subject, brand = _scope_identity(scope)
    expected_ids = [str(value).strip() for value in note_ids]
    if len(expected_ids) != len(records) or not all(expected_ids) or len(set(expected_ids)) != len(expected_ids):
        raise ValueError("one unique note id is required for each source record")

    normalized = [map_raw_to_normalized(dict(record), platform) for record in records]
    actual_ids = [str(row.get("platform_content_id") or "").strip() for row in normalized]
    if actual_ids != expected_ids or any(row.get("platform") != platform for row in normalized):
        raise ValueError("platform record identities do not match imported notes")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_repository().transaction() as conn:
        cursor = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,))
        evidence_row = cursor.fetchone()
        if evidence_row is None:
            raise ValueError("source Evidence is missing")
        evidence = _row_dict(cursor, evidence_row)
        integrity = classify_evidence_integrity(evidence)
        if not integrity.get("verified"):
            raise ValueError("source Evidence integrity is not verified")
        inputs = json.loads(evidence.get("inputs_json") or "{}")
        evidence_scope = inputs.get("_lumenis_scope") or {}
        if (
            evidence.get("product_id") != product
            or evidence.get("domain_id") != domain
            or str(evidence.get("result") or "").upper() != "PASS"
            or str(evidence.get("status") or "").lower() != "verified"
            or evidence_scope.get("subject_id") != subject
            or evidence_scope.get("brand_focus_id") != brand
            or set(inputs.get("source_ids") or ()) != set(expected_ids)
        ):
            raise ValueError("source Evidence does not bind the exact imported scope and IDs")

        for content_id in expected_ids:
            scope_refs = []
            for table, id_column in (("notes", "note_id"), ("canonical_data", "source_id")):
                row = conn.execute(
                    f"SELECT source_platform, product_id, domain_id, subject_id, "
                    f"brand_focus_id, scope_status, scope_evidence_ref FROM {table} "
                    f"WHERE {id_column}=?", (content_id,),
                ).fetchone()
                stored = (
                    (row[0], row[1], row[2], row[3] or None, row[4] or None, row[5], row[6])
                    if row is not None else None
                )
                if stored is None or stored[:6] != (
                    platform, product, domain, subject, brand, "VERIFIED"
                ) or not stored[6]:
                    raise ValueError(f"{table} has no matching verified scope for {content_id}")
                scope_refs.append(str(stored[6]))
            if scope_refs[0] != scope_refs[1]:
                raise ValueError(f"Raw and Canonical scope Evidence differs for {content_id}")
            scope_evidence_id = scope_refs[0]
            if scope_evidence_id != str(evidence_id):
                prior_cursor = conn.execute(
                    "SELECT * FROM app_evidence_records WHERE id=?",
                    (scope_evidence_id,),
                )
                prior_row = prior_cursor.fetchone()
                prior = _row_dict(prior_cursor, prior_row) if prior_row is not None else None
                if prior is None or not classify_evidence_integrity(prior).get("verified"):
                    raise ValueError(f"original scope Evidence is not signed for {content_id}")
                prior_inputs = json.loads(prior.get("inputs_json") or "{}")
                prior_scope = prior_inputs.get("_lumenis_scope") or {}
                if (
                    prior.get("product_id") != product
                    or prior.get("domain_id") != domain
                    or str(prior.get("result") or "").upper() != "PASS"
                    or str(prior.get("status") or "").lower() != "verified"
                    or prior_scope.get("subject_id") != subject
                    or prior_scope.get("brand_focus_id") != brand
                    or content_id not in (prior_inputs.get("source_ids") or [])
                ):
                    raise ValueError(f"original scope Evidence does not bind {content_id}")

        columns = ", ".join(_CONTENT_FIELDS)
        placeholders = ", ".join("?" for _ in _CONTENT_FIELDS)
        updates = ", ".join(f"{field}=excluded.{field}" for field in _CONTENT_FIELDS)
        for record, content in zip(records, normalized):
            content_id = str(content["platform_content_id"])
            values = [
                json.dumps(content[field], ensure_ascii=False, sort_keys=True)
                if field in _JSON_FIELDS and content[field] is not None
                else content[field]
                for field in _CONTENT_FIELDS
            ]
            observation = dict(record)
            observation["_lumenis_evidence_id"] = evidence_id
            raw_json = json.dumps(observation, ensure_ascii=False, sort_keys=True)
            conn.execute(
                f"INSERT INTO platform_contents "
                f"(platform, platform_content_id, {columns}, raw_data, "
                f"first_collected_at, last_collected_at, collected_at) "
                f"VALUES (?, ?, {placeholders}, ?, ?, ?, ?) "
                f"ON CONFLICT(platform, platform_content_id) DO UPDATE SET "
                f"{updates}, raw_data=excluded.raw_data, "
                f"last_collected_at=excluded.last_collected_at, "
                f"collected_at=excluded.collected_at",
                (platform, content_id, *values, raw_json, now, now, now),
            )
            view_count = content.get("view_count")
            if view_count is not None:
                if isinstance(view_count, bool) or not isinstance(view_count, int) or view_count < 0:
                    raise ValueError("source view count must be a nonnegative integer")
                entity_key = f"{platform}:{content_id}"
                prior = conn.execute(
                    "SELECT raw_json FROM metric_snapshots "
                    "WHERE entity_type='platform_content' AND entity_key=? "
                    "ORDER BY id DESC LIMIT 1", (entity_key,),
                ).fetchone()
                prior_count = json.loads(prior[0]).get("view_count") if prior else None
                if prior_count != view_count:
                    conn.execute(
                        "INSERT INTO metric_snapshots "
                        "(entity_type, entity_key, raw_json, source, collector_version, snapshot_at) "
                        "VALUES ('platform_content', ?, ?, ?, 'secondary-collection-v1', ?)",
                        (
                            entity_key,
                            json.dumps({
                                "view_count": view_count,
                                "platform": platform,
                                "platform_content_id": content_id,
                                "source_id": content_id,
                                "canonical_source_id": content_id,
                                "source_url": record.get("feed_url") or content.get("url"),
                                "evidence_id": evidence_id,
                                "product_id": product,
                                "domain_id": domain,
                                "subject_id": subject,
                                "brand_focus_id": brand,
                            }, ensure_ascii=False, sort_keys=True),
                            platform, now,
                        ),
                    )
    return len(records)
