"""Persist platform fields only after exact Evidence and Canonical scope promotion."""

from __future__ import annotations

import json
import hashlib
from contextlib import nullcontext
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from lumenis.shared.database import get_repository
from lumenis.shared.evidence.store import classify_evidence_integrity
from lumenis.system.collector.adapters.platform_naming import map_raw_to_normalized, normalize_platform


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


def _unassigned_global_scope_identity(
    scope: Mapping[str, Any],
) -> tuple[str, str, None, None]:
    if not isinstance(scope, Mapping) or scope.get("global_scope") is not True:
        raise ValueError("strict GLOBAL scope is required for unassigned observations")
    if scope.get("subject_id") not in (None, "") or scope.get("brand_focus_id") not in (None, ""):
        raise ValueError("GLOBAL unassigned observations cannot assert a Subject or BrandFocus")
    domain = str(scope.get("domain_id") or "").strip().lower()
    if domain == "cth":
        product, stored_domain = "CTH", "cth"
    elif domain == "bmp":
        product, stored_domain = "ZBMP", "zbmp"
    else:
        raise ValueError("GLOBAL domain must be CTH or BMP")
    declared_product = scope.get("product_id")
    if declared_product not in (None, "", product):
        raise ValueError("GLOBAL product does not match its domain")
    return product, stored_domain, None, None


def _stable_observation(record: Mapping[str, Any]) -> dict[str, Any]:
    """Drop transport timestamps that change on every read, retaining source data."""
    return {
        key: value for key, value in record.items()
        if key not in {"captured_at", "collected_at", "last_collected_at",
                       "_lumenis_evidence_id"}
    }


def _persist_native_records(
    records: Sequence[Mapping[str, Any]], normalized: Sequence[Mapping[str, Any]], *,
    expected_ids: Sequence[str], platform: str, evidence_id: int, product: str,
    domain: str, subject: str | None, brand: str | None, now: str, connection,
) -> None:
    """Write the current native view and append changed metrics, including unknowns."""
    from lumenis.system.collector.adapters.multi_platform_import import _normalize_source_publication

    columns = ", ".join(_CONTENT_FIELDS)
    placeholders = ", ".join("?" for _ in _CONTENT_FIELDS)
    updates = ", ".join(f"{field}=excluded.{field}" for field in _CONTENT_FIELDS)
    for record, content in zip(records, normalized):
        content_id = str(content["platform_content_id"])
        values = []
        for field in _CONTENT_FIELDS:
            value = content[field]
            if field == "published_at":
                if value is None or (isinstance(value, str) and not value.strip()):
                    value = record.get("publish_datetime")
                value = _normalize_source_publication(value, platform) or None
            if field in _JSON_FIELDS and value is not None:
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            values.append(value)
        observation = dict(record)
        observation["_lumenis_evidence_id"] = evidence_id
        raw_json = json.dumps(observation, ensure_ascii=False, sort_keys=True)
        connection.execute(
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
        metrics = {name: content.get(name) for name in (
            "like_count", "comment_count", "collect_count", "share_count", "view_count",
        )}
        if any(value is not None and (type(value) is not int or value < 0)
               for value in metrics.values()):
            raise ValueError("source metrics must be nonnegative integers or unknown")
        entity_key = f"{platform}:{content_id}"
        prior_row = connection.execute(
            "SELECT raw_json FROM metric_snapshots "
            "WHERE entity_type='platform_content' AND entity_key=? "
            "ORDER BY id DESC LIMIT 1", (entity_key,),
        ).fetchone()
        prior = json.loads(prior_row[0]) if prior_row else None
        if (not isinstance(prior, dict) or not all(name in prior for name in metrics)
                or any(prior[name] != value for name, value in metrics.items())):
            connection.execute(
                "INSERT INTO metric_snapshots "
                "(entity_type, entity_key, likes, comments, collects, shares, raw_json, "
                "source, collector_version, snapshot_at) "
                "VALUES ('platform_content', ?, ?, ?, ?, ?, ?, ?, 'secondary-collection-v2', ?)",
                (
                    entity_key, metrics["like_count"], metrics["comment_count"],
                    metrics["collect_count"], metrics["share_count"],
                    json.dumps({
                        "schema_version": 2, **metrics, "platform": platform,
                        "platform_content_id": content_id, "source_id": content_id,
                        "canonical_source_id": content_id,
                        "source_url": record.get("feed_url") or content.get("url"),
                        "evidence_id": evidence_id, "product_id": product, "domain_id": domain,
                        "subject_id": subject, "brand_focus_id": brand,
                    }, ensure_ascii=False, sort_keys=True, allow_nan=False),
                    platform, now,
                ),
            )


def persist_unassigned_platform_records(
    records: Sequence[Mapping[str, Any]], *, platform: str,
    note_ids: Sequence[str], evidence_id: int, scope: Mapping[str, Any],
    connection=None,
) -> int:
    """Persist source-backed GLOBAL observations without assigning business scope."""
    if connection is not None and not connection.in_transaction:
        raise ValueError("the caller must own an active collection transaction")
    if not isinstance(evidence_id, int) or isinstance(evidence_id, bool) or evidence_id <= 0:
        raise ValueError("a persisted Evidence id is required")
    if not records or len(records) > 200:
        raise ValueError("bounded non-empty records are required")
    product, domain, subject, brand = _unassigned_global_scope_identity(scope)
    canonical_platform = normalize_platform(platform)
    if canonical_platform is None or canonical_platform != platform:
        raise ValueError("a canonical platform identifier is required")
    if isinstance(note_ids, (str, bytes)):
        raise ValueError("one unique note id is required for each source record")
    expected_ids = list(note_ids)
    if (len(expected_ids) != len(records) or any(
        not isinstance(value, str) or not value.strip() or value != value.strip()
        for value in expected_ids
    ) or len(set(expected_ids)) != len(expected_ids)):
        raise ValueError("one unique note id is required for each source record")
    source_records = [dict(record) if isinstance(record, Mapping) else None for record in records]
    if any(record is None for record in source_records):
        raise ValueError("source records must be objects")
    normalized = [map_raw_to_normalized(record, canonical_platform) for record in source_records]
    actual_ids = [row.get("platform_content_id") for row in normalized]
    if actual_ids != expected_ids or any(row.get("platform") != canonical_platform for row in normalized):
        raise ValueError("platform record identities do not match imported notes")

    from lumenis.system.collector.adapters.secondary_collection import _credential_free_observations

    sanitized_records = [_credential_free_observations(record) for record in source_records]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    context = get_repository().transaction() if connection is None else nullcontext(connection)
    with context as conn:
        cursor = conn.execute("SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,))
        evidence_row = cursor.fetchone()
        if evidence_row is None:
            raise ValueError("source Evidence is missing")
        evidence = _row_dict(cursor, evidence_row)
        integrity = classify_evidence_integrity(evidence)
        if not integrity.get("verified") or integrity.get("assurance") != "writer-authenticated":
            raise ValueError("source Evidence integrity is not writer-authenticated")
        inputs = json.loads(evidence.get("inputs_json") or "{}")
        evidence_scope = inputs.get("_lumenis_scope") or {}
        if (
            evidence.get("product_id") != product
            or evidence.get("domain_id") != domain
            or str(evidence.get("result") or "").upper() != "PASS"
            or str(evidence.get("status") or "").lower() != "verified"
            or not isinstance(evidence_scope, Mapping)
            or evidence_scope.get("global") is not True
            or evidence_scope.get("domain_id") != domain
            or evidence_scope.get("product_id") != product
            or evidence_scope.get("subject_id") not in (None, "")
            or evidence_scope.get("brand_focus_id") not in (None, "")
            or normalize_platform(inputs.get("platform")) != canonical_platform
            or inputs.get("source_ids") != expected_ids
        ):
            raise ValueError("source Evidence does not bind the exact GLOBAL scope and IDs")

        observations = inputs.get("source_observations")
        if not isinstance(observations, list) or len(observations) != len(expected_ids):
            raise ValueError("GLOBAL source observation proof is missing or incomplete")
        proof_ids = [item.get("source_id") if isinstance(item, dict) else None for item in observations]
        if proof_ids != expected_ids:
            raise ValueError("GLOBAL source observation proof identities do not match")
        for content_id, record, proof in zip(expected_ids, sanitized_records, observations):
            try:
                digest = hashlib.sha256(json.dumps(
                    _stable_observation(record), ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")).hexdigest()
            except (TypeError, ValueError) as exc:
                raise ValueError("GLOBAL source observation is not stable JSON") from exc
            if (normalize_platform(proof.get("platform")) != canonical_platform
                    or proof.get("observation_sha256") != digest):
                raise ValueError(f"GLOBAL source observation does not match signed Evidence for {content_id}")

        for content_id in expected_ids:
            for table, id_column in (("notes", "note_id"), ("canonical_data", "source_id")):
                row = conn.execute(
                    f"SELECT source_platform, product_id, domain_id, subject_id, "
                    f"brand_focus_id, scope_status FROM {table} WHERE {id_column}=?",
                    (content_id,),
                ).fetchone()
                stored = (
                    (normalize_platform(row[0]), row[1], row[2], row[3] or None,
                     row[4] or None, str(row[5] or "").upper())
                    if row is not None else None
                )
                if stored != (canonical_platform, product, domain, None, None, "UNASSIGNED"):
                    raise ValueError(
                        f"{table} is missing matching unassigned GLOBAL identity for {content_id}"
                    )

        _persist_native_records(
            sanitized_records, normalized, expected_ids=expected_ids,
            platform=canonical_platform, evidence_id=evidence_id, product=product,
            domain=domain, subject=subject, brand=brand, now=now, connection=conn,
        )
    return len(records)


def platform_records_changed(
    records: Sequence[Mapping[str, Any]], *, platform: str,
    connection=None,
) -> bool:
    """Return whether the source observation differs from the saved native row."""
    from lumenis.system.collector.adapters.secondary_collection import _credential_free_observations

    normalized = [map_raw_to_normalized(dict(record), platform) for record in records]
    if not normalized:
        return False
    context = get_repository().transaction() if connection is None else nullcontext(connection)
    with context as conn:
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
            current = _credential_free_observations(dict(record))
            if _stable_observation(prior) != _stable_observation(current):
                return True
    return False


def persist_verified_platform_records(
    records: Sequence[Mapping[str, Any]], *, platform: str,
    note_ids: Sequence[str], evidence_id: int, scope: Mapping[str, Any],
    connection=None, require_observation_proof: bool = False,
) -> int:
    """Save native and comparable fields through the existing Shared DB owner.

    The Collector calls this only after its raw note import and Canonical sync.
    This function rechecks every row and the Evidence in one transaction. A
    failure writes no platform rows or metric observations.
    """
    if connection is not None and not connection.in_transaction:
        raise ValueError("the caller must own an active collection transaction")
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
    context = get_repository().transaction() if connection is None else nullcontext(connection)
    with context as conn:
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
        if require_observation_proof:
            from lumenis.system.collector.adapters.secondary_collection import _credential_free_observations
            observations = inputs.get("source_observations")
            if not isinstance(observations, list):
                raise ValueError("current source observation proof is missing")
            proofs = {}
            for observation in observations:
                if not isinstance(observation, dict):
                    raise ValueError("current source observation proof is malformed")
                identity = observation.get("source_id")
                if identity in proofs:
                    raise ValueError("current source observation proof is ambiguous")
                proofs[identity] = observation
            for content_id, record in zip(expected_ids, records):
                proof = proofs.get(content_id) or {}
                digest = hashlib.sha256(json.dumps(
                    _stable_observation(_credential_free_observations(dict(record))),
                    ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")).hexdigest()
                if (normalize_platform(proof.get("platform")) != platform
                        or proof.get("observation_sha256") != digest):
                    raise ValueError("current source observation does not match signed Evidence")

        for content_id in expected_ids:
            scope_refs = []
            for table, id_column in (("notes", "note_id"), ("canonical_data", "source_id")):
                row = conn.execute(
                    f"SELECT source_platform, product_id, domain_id, subject_id, "
                    f"brand_focus_id, scope_status, scope_evidence_ref FROM {table} "
                    f"WHERE {id_column}=?", (content_id,),
                ).fetchone()
                stored = (
                    (normalize_platform(row[0]), row[1], row[2], row[3] or None, row[4] or None, row[5], row[6])
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

        _persist_native_records(
            records, normalized, expected_ids=expected_ids, platform=platform,
            evidence_id=evidence_id, product=product, domain=domain,
            subject=subject, brand=brand, now=now, connection=conn,
        )
    return len(records)
