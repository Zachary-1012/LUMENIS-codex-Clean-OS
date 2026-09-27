"""Exact, Evidence-backed country relations and venue tenant assertions.

This repository stores source assertions against the canonical Subject Registry.
It does not create or infer global identities, and every source reference points
to the existing ``app_evidence_records`` owner.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from typing import Any, Optional


TABLE = "lumenis_entity_relation_assertions"
EVIDENCE_REF_TYPE = "app_evidence_records"
COUNTRY_RELATION_TYPES = frozenset({
    "ORIGIN", "HQ", "LEGAL_JURISDICTION", "OPERATES_IN", "VENUE_LOCATION",
    "MARKET_ACTIVITY",
})
RELATION_TYPES = COUNTRY_RELATION_TYPES | {"TENANT_OF"}
CLAIM_KINDS = frozenset({"ASSERTED", "EXPLICIT_ABSENCE"})
REVIEW_STATUSES = frozenset({"UNREVIEWED", "ACCEPTED", "CONFLICTED", "REJECTED"})
VALID_TIME_KINDS = frozenset({"AS_OF_CAPTURE", "INTERVAL", "UNKNOWN"})
COUNTRY_BUCKETS = frozenset({
    "CN", "KR", "JP", "GB", "FR", "US", "CA", "AU", "MY", "SG", "TH", "BR", "NO",
})
_ISO2_RE = re.compile(r"^[A-Z]{2}$", re.ASCII)
_LOCALE_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$", re.ASCII)


class EntityRelationError(ValueError):
    """A relation assertion is not backed by the required canonical truth."""


def country_bucket(country_iso: str) -> str:
    """Return the UI bucket for a stored ISO alpha-2 value.

    ``OTHER`` is a presentation bucket only. It is never accepted by writers as
    a country code and missing/unknown states are represented separately.
    """
    code = _normalize_country_iso(country_iso)
    return code if code in COUNTRY_BUCKETS else "OTHER"


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if exists is None:
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _require_prerequisites(conn: sqlite3.Connection) -> None:
    required = {
        "lumenis_subject_registry": {
            "subject_id", "brand_focus_id", "domain_id", "name_en", "name_zh", "status",
        },
        "app_evidence_records": {
            "id", "inputs_json", "domain_id", "product_id", "result", "status", "captured_at",
            "integrity_version", "integrity_algorithm", "integrity_key_id", "integrity_digest",
        },
        "notes": {
            "note_id", "url", "content", "domain_id", "product_id", "subject_id", "brand_focus_id",
            "scope_status", "scope_evidence_ref",
        },
    }
    for table, columns in required.items():
        actual = _table_columns(conn, table)
        if not columns.issubset(actual):
            missing = sorted(columns - actual)
            raise RuntimeError(
                f"entity relation prerequisite {table} is missing columns: {missing}"
            )


def ensure_entity_relation_schema(conn: sqlite3.Connection) -> None:
    """Create the additive v18 assertion table on the caller's connection.

    This function requires the canonical v17 Subject Registry, Evidence and
    note-scope tables. It never creates substitute owners or backfills history.
    """
    _require_prerequisites(conn)
    if not conn.in_transaction:
        conn.execute("BEGIN")
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            assertion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain_id TEXT NOT NULL CHECK(domain_id IN ('CTH', 'BMP')),
            subject_id TEXT NOT NULL REFERENCES lumenis_subject_registry(subject_id),
            relation_type TEXT NOT NULL CHECK(relation_type IN (
                'ORIGIN', 'HQ', 'LEGAL_JURISDICTION', 'OPERATES_IN',
                'VENUE_LOCATION', 'MARKET_ACTIVITY', 'TENANT_OF'
            )),
            country_iso TEXT,
            claim_kind TEXT NOT NULL CHECK(claim_kind IN ('ASSERTED', 'EXPLICIT_ABSENCE')),
            review_status TEXT NOT NULL DEFAULT 'UNREVIEWED'
                CHECK(review_status IN ('UNREVIEWED', 'ACCEPTED', 'CONFLICTED', 'REJECTED')),
            conflict_group TEXT,
            valid_time_kind TEXT NOT NULL CHECK(valid_time_kind IN (
                'AS_OF_CAPTURE', 'INTERVAL', 'UNKNOWN'
            )),
            valid_from TEXT,
            valid_to TEXT,
            source_evidence_ref_type TEXT NOT NULL DEFAULT 'app_evidence_records'
                CHECK(source_evidence_ref_type='app_evidence_records'),
            source_evidence_ref INTEGER NOT NULL REFERENCES app_evidence_records(id),
            source_note_id TEXT NOT NULL REFERENCES notes(note_id),
            source_locale TEXT NOT NULL DEFAULT '',
            target_subject_id TEXT REFERENCES lumenis_subject_registry(subject_id),
            tenant_name TEXT,
            floor TEXT,
            category TEXT,
            detail_url TEXT,
            listing_url TEXT,
            observed_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK(
                (relation_type='TENANT_OF' AND domain_id='CTH' AND country_iso IS NULL
                    AND tenant_name IS NOT NULL AND length(trim(tenant_name)) > 0
                    AND target_subject_id IS NOT subject_id)
                OR
                (relation_type<>'TENANT_OF' AND country_iso IS NOT NULL
                    AND tenant_name IS NULL AND floor IS NULL AND category IS NULL
                    AND detail_url IS NULL AND listing_url IS NULL AND observed_at IS NULL
                    AND target_subject_id IS NULL)
            ),
            CHECK(
                (valid_time_kind='AS_OF_CAPTURE' AND valid_from IS NULL AND valid_to IS NULL)
                OR (valid_time_kind='INTERVAL' AND valid_from IS NOT NULL)
                OR (valid_time_kind='UNKNOWN' AND valid_from IS NULL AND valid_to IS NULL)
            ),
            CHECK(relation_type<>'TENANT_OF' OR claim_kind='ASSERTED')
        )
    """)
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_entity_relation_lookup "
        f"ON {TABLE}(domain_id, relation_type, country_iso, review_status)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_entity_relation_subject "
        f"ON {TABLE}(subject_id, relation_type, valid_time_kind, valid_from, valid_to)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_entity_relation_evidence "
        f"ON {TABLE}(source_evidence_ref, source_note_id)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_entity_relation_tenant "
        f"ON {TABLE}(subject_id, relation_type, source_locale, observed_at)"
    )
    # SQLite treats NULL values as distinct in UNIQUE indexes. Partial
    # expression indexes give country and tenant assertions retry-safe keys.
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_relation_country_source "
        f"ON {TABLE}(source_evidence_ref, source_note_id, relation_type, subject_id, "
        "country_iso, claim_kind, valid_time_kind, ifnull(valid_from,''), ifnull(valid_to,''), "
        "ifnull(source_locale,'')) WHERE relation_type<>'TENANT_OF'"
    )
    conn.execute(
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_relation_tenant_source "
        f"ON {TABLE}(source_evidence_ref, source_note_id, subject_id, source_locale, "
        "tenant_name, ifnull(floor,''), ifnull(category,''), ifnull(detail_url,''), listing_url) "
        "WHERE relation_type='TENANT_OF'"
    )


def _normalize_domain(value: Any) -> str:
    domain = str(value or "").strip().upper()
    aliases = {"CTH": "CTH", "BMP": "BMP", "ZBMP": "BMP"}
    if domain not in aliases:
        raise EntityRelationError("domain_id must identify CTH or BMP")
    return aliases[domain]


def _normalize_country_iso(value: Any) -> str:
    if type(value) is not str:
        raise EntityRelationError("country_iso must be a two-letter ISO alpha-2 code")
    code = value.strip().upper()
    if _ISO2_RE.fullmatch(code) is None or code == "OTHER":
        raise EntityRelationError("country_iso must be a two-letter ISO alpha-2 code")
    return code


def _text(value: Any, field: str, *, required: bool = False, max_length: int = 2048) -> str:
    if value is None:
        value = ""
    if type(value) is not str:
        raise EntityRelationError(f"{field} must be text")
    value = value.strip()
    if len(value) > max_length:
        raise EntityRelationError(f"{field} exceeds {max_length} characters")
    if required and not value:
        raise EntityRelationError(f"{field} is required")
    return value


def _normalize_timestamp(value: Any, field: str, *, required: bool = False) -> Optional[str]:
    if value is None or value == "":
        if required:
            raise EntityRelationError(f"{field} is required")
        return None
    raw = _text(value, field, required=True, max_length=64)
    try:
        datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        raise EntityRelationError(f"{field} must be an ISO date or datetime") from None
    return raw


def _normalize_locale(value: Any, *, required: bool = False) -> str:
    locale = _text(value, "source_locale", required=required, max_length=35)
    if locale and _LOCALE_RE.fullmatch(locale) is None:
        raise EntityRelationError("source_locale must be a BCP-47 style locale")
    return locale


def _registry_subject(conn: sqlite3.Connection, domain: str, subject_id: str) -> dict:
    subject_id = _text(subject_id, "subject_id", required=True, max_length=256)
    row = conn.execute(
        "SELECT subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh, status "
        "FROM lumenis_subject_registry WHERE subject_id=? LIMIT 1",
        (subject_id,),
    ).fetchone()
    if row is None or str(row["domain_id"] or "").upper() != domain:
        raise EntityRelationError("subject_id is not an exact registry identity in domain_id")
    if str(row["status"] or "").lower() in {"archived", "disabled", "deleted"}:
        raise EntityRelationError("subject_id is archived or unavailable")
    if domain == "BMP" and not _text(row["brand_focus_id"], "brand_focus_id", required=True):
        raise EntityRelationError("BMP registry identity has no BrandFocus id")
    return dict(row)


def _load_evidence_and_note(
    conn: sqlite3.Connection,
    *,
    domain: str,
    subject: dict,
    evidence_ref: Any,
    note_id: Any,
) -> tuple[dict, dict]:
    if isinstance(evidence_ref, bool) or not isinstance(evidence_ref, int) or evidence_ref <= 0:
        raise EntityRelationError("source_evidence_ref must be a positive app_evidence_records id")
    note_id = _text(note_id, "source_note_id", required=True, max_length=256)
    evidence_row = conn.execute(
        "SELECT * FROM app_evidence_records WHERE id=? LIMIT 1", (evidence_ref,)
    ).fetchone()
    if evidence_row is None:
        raise EntityRelationError("source Evidence reference does not exist")
    evidence = dict(evidence_row)
    from lumenis.shared.evidence.store import classify_evidence_integrity

    integrity = classify_evidence_integrity(evidence)
    if not integrity.get("verified") or integrity.get("assurance") != "writer-authenticated":
        raise EntityRelationError("source Evidence is not writer-authenticated")
    if str(evidence.get("result") or "").upper() != "PASS":
        raise EntityRelationError("source Evidence result is not PASS")
    if str(evidence.get("status") or "").lower() != "verified":
        raise EntityRelationError("source Evidence status is not verified")

    domain_lower = domain.lower() if domain == "CTH" else "zbmp"
    product_id = "CTH" if domain == "CTH" else "ZBMP"
    if str(evidence.get("domain_id") or "").lower() != domain_lower:
        raise EntityRelationError("source Evidence domain does not match the registry identity")
    if str(evidence.get("product_id") or "").upper() != product_id:
        raise EntityRelationError("source Evidence product does not match the registry identity")
    try:
        inputs = json.loads(evidence.get("inputs_json") or "")
    except (TypeError, ValueError, json.JSONDecodeError):
        raise EntityRelationError("source Evidence inputs_json is invalid") from None
    if not isinstance(inputs, dict):
        raise EntityRelationError("source Evidence inputs_json must be an object")
    stored_scope = inputs.get("_lumenis_scope")
    if not isinstance(stored_scope, dict):
        raise EntityRelationError("source Evidence has no exact _lumenis_scope")
    expected_scope = {
        "domain_id": domain_lower,
        "product_id": product_id,
        "global": False,
    }
    if domain == "CTH":
        expected_scope["subject_id"] = subject["subject_id"]
        if "brand_focus_id" in stored_scope:
            raise EntityRelationError("CTH Evidence scope contains a conflicting BrandFocus")
    else:
        expected_scope["brand_focus_id"] = subject["brand_focus_id"]
        if "subject_id" in stored_scope:
            raise EntityRelationError("BMP Evidence scope contains a conflicting Subject")
    if stored_scope != expected_scope:
        raise EntityRelationError("source Evidence _lumenis_scope does not exactly match the registry identity")
    source_ids = inputs.get("source_ids")
    if not isinstance(source_ids, list) or note_id not in source_ids:
        raise EntityRelationError("source_note_id is not listed in the signed Evidence source_ids")

    note_row = conn.execute(
        "SELECT note_id, url, content, product_id, domain_id, subject_id, brand_focus_id, "
        "scope_status, scope_evidence_ref FROM notes WHERE note_id=? LIMIT 1",
        (note_id,),
    ).fetchone()
    if note_row is None:
        raise EntityRelationError("source note does not exist in canonical notes")
    note = dict(note_row)
    expected_note_domain = "cth" if domain == "CTH" else "zbmp"
    if (
        str(note.get("domain_id") or "").lower() != expected_note_domain
        or str(note.get("product_id") or "").upper() != product_id
        or str(note.get("scope_status") or "").upper() != "VERIFIED"
        or str(note.get("scope_evidence_ref") or "") != str(evidence_ref)
    ):
        raise EntityRelationError("source note is not verified against this exact Evidence reference")
    if domain == "CTH":
        if note.get("subject_id") != subject["subject_id"] or note.get("brand_focus_id") not in (None, ""):
            raise EntityRelationError("source note Subject scope does not match")
    elif note.get("brand_focus_id") != subject["brand_focus_id"] or note.get("subject_id") not in (None, ""):
        raise EntityRelationError("source note BrandFocus scope does not match")
    return evidence, note


def _validate_relation_time(
    valid_time_kind: Any,
    valid_from: Any,
    valid_to: Any,
) -> tuple[str, Optional[str], Optional[str]]:
    kind = _text(valid_time_kind, "valid_time_kind", required=True, max_length=24).upper()
    if kind not in VALID_TIME_KINDS:
        raise EntityRelationError("valid_time_kind must be AS_OF_CAPTURE, INTERVAL, or UNKNOWN")
    start = _normalize_timestamp(valid_from, "valid_from")
    end = _normalize_timestamp(valid_to, "valid_to")
    if kind == "AS_OF_CAPTURE" and (start is not None or end is not None):
        raise EntityRelationError("AS_OF_CAPTURE uses the linked Evidence captured_at")
    if kind == "UNKNOWN" and (start is not None or end is not None):
        raise EntityRelationError("UNKNOWN valid time cannot carry interval bounds")
    if kind == "INTERVAL":
        if start is None:
            raise EntityRelationError("INTERVAL requires valid_from")
        if end is not None:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            if start_dt >= end_dt:
                raise EntityRelationError("valid_to must be later than valid_from")
    return kind, start, end


def _claim_dict(row: Any) -> dict:
    claim = dict(row)
    claim["evidence_ref_type"] = claim.pop("source_evidence_ref_type", EVIDENCE_REF_TYPE)
    claim["country_bucket"] = (
        country_bucket(claim["country_iso"]) if claim.get("country_iso") else None
    )
    return claim


class EntityRelationRepository:
    """Connection-scoped writer and query API for source relation assertions."""

    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection
        self.conn.row_factory = sqlite3.Row
        if not _table_columns(connection, TABLE):
            raise RuntimeError("entity relation schema is unavailable; apply Shared DB v18 first")

    def record_country_relation(
        self,
        *,
        domain_id: str,
        subject_id: str,
        relation_type: str,
        country_iso: str,
        source_evidence_ref: int,
        source_note_id: str,
        claim_kind: str = "ASSERTED",
        valid_time_kind: str = "AS_OF_CAPTURE",
        valid_from: Optional[str] = None,
        valid_to: Optional[str] = None,
        source_locale: Optional[str] = None,
    ) -> int:
        domain = _normalize_domain(domain_id)
        relation = _text(relation_type, "relation_type", required=True, max_length=32).upper()
        if relation not in COUNTRY_RELATION_TYPES:
            raise EntityRelationError("record_country_relation requires a country relation type")
        code = _normalize_country_iso(country_iso)
        kind = _text(claim_kind, "claim_kind", required=True, max_length=24).upper()
        if kind not in CLAIM_KINDS:
            raise EntityRelationError("claim_kind must be ASSERTED or EXPLICIT_ABSENCE")
        temporal_kind, start, end = _validate_relation_time(valid_time_kind, valid_from, valid_to)
        locale = _normalize_locale(source_locale)
        subject = _registry_subject(self.conn, domain, subject_id)
        _load_evidence_and_note(
            self.conn, domain=domain, subject=subject,
            evidence_ref=source_evidence_ref, note_id=source_note_id,
        )
        cursor = self.conn.execute(
            f"INSERT OR IGNORE INTO {TABLE} ("
            "domain_id, subject_id, relation_type, country_iso, claim_kind, review_status, "
            "valid_time_kind, valid_from, valid_to, source_evidence_ref_type, "
            "source_evidence_ref, source_note_id, source_locale"
            ") VALUES (?, ?, ?, ?, ?, 'UNREVIEWED', ?, ?, ?, ?, ?, ?, ?)",
            (
                domain, subject["subject_id"], relation, code, kind, temporal_kind,
                start, end, EVIDENCE_REF_TYPE, source_evidence_ref,
                _text(source_note_id, "source_note_id", required=True, max_length=256), locale,
            ),
        )
        row = self.conn.execute(
            f"SELECT assertion_id FROM {TABLE} WHERE domain_id=? AND subject_id=? "
            "AND relation_type=? AND country_iso=? AND claim_kind=? "
            "AND valid_time_kind=? AND ifnull(valid_from,'')=? AND ifnull(valid_to,'')=? "
            "AND source_evidence_ref=? AND source_note_id=? "
            "AND source_locale=? ORDER BY assertion_id LIMIT 1",
            (
                domain, subject["subject_id"], relation, code, kind, temporal_kind,
                start or "", end or "", source_evidence_ref, source_note_id, locale,
            ),
        ).fetchone()
        return int(row[0])

    def record_venue_tenant_claim(
        self,
        *,
        venue_subject_id: str,
        source_evidence_ref: int,
        source_note_id: str,
        tenant_name: str,
        floor: Optional[str],
        category: Optional[str],
        detail_url: Optional[str],
        listing_url: str,
        source_locale: str,
        observed_at: Optional[str] = None,
        target_brand_focus_id: Optional[str] = None,
    ) -> int:
        venue = _registry_subject(self.conn, "CTH", venue_subject_id)
        tenant = _text(tenant_name, "tenant_name", required=True, max_length=256)
        floor_value = _text(floor, "floor", max_length=128)
        category_value = _text(category, "category", max_length=256)
        detail_value = _text(detail_url, "detail_url", max_length=2048)
        listing_value = _text(listing_url, "listing_url", required=True, max_length=2048)
        locale = _normalize_locale(source_locale, required=True)
        observed = _normalize_timestamp(observed_at, "observed_at")
        target_subject_id = None
        if target_brand_focus_id is not None:
            focus = _text(target_brand_focus_id, "target_brand_focus_id", required=True, max_length=256)
            target = self.conn.execute(
                "SELECT subject_id, status FROM lumenis_subject_registry "
                "WHERE domain_id='BMP' AND brand_focus_id=? LIMIT 1",
                (focus,),
            ).fetchone()
            if target is None or str(target["status"] or "").lower() in {
                "archived", "disabled", "deleted",
            }:
                raise EntityRelationError("target_brand_focus_id is not an existing active BMP identity")
            target_subject_id = target["subject_id"]
        _load_evidence_and_note(
            self.conn, domain="CTH", subject=venue,
            evidence_ref=source_evidence_ref, note_id=source_note_id,
        )
        note = self.conn.execute(
            "SELECT url, content FROM notes WHERE note_id=? LIMIT 1", (source_note_id,)
        ).fetchone()
        if note is None or note["url"] != listing_value:
            raise EntityRelationError("listing_url must exactly match the verified source note URL")
        source_content = re.sub(r"\s+", " ", str(note["content"] or "")).casefold()
        if not source_content:
            raise EntityRelationError("verified source note content is empty")
        if re.sub(r"\s+", " ", tenant).casefold() not in source_content:
            raise EntityRelationError("tenant_name is not present in the verified source note content")
        if floor_value and re.sub(r"\s+", " ", floor_value).casefold() not in source_content:
            raise EntityRelationError("floor is not present in the verified source note content")
        self.conn.execute(
            f"INSERT OR IGNORE INTO {TABLE} ("
            "domain_id, subject_id, relation_type, claim_kind, review_status, "
            "valid_time_kind, source_evidence_ref_type, source_evidence_ref, source_note_id, "
            "source_locale, target_subject_id, tenant_name, floor, category, detail_url, "
            "listing_url, observed_at"
            ") VALUES ('CTH', ?, 'TENANT_OF', 'ASSERTED', 'UNREVIEWED', 'AS_OF_CAPTURE', "
            "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                venue["subject_id"], EVIDENCE_REF_TYPE, source_evidence_ref,
                _text(source_note_id, "source_note_id", required=True, max_length=256),
                locale, target_subject_id, tenant, floor_value, category_value,
                detail_value, listing_value, observed,
            ),
        )
        row = self.conn.execute(
            f"SELECT assertion_id FROM {TABLE} WHERE domain_id='CTH' AND subject_id=? "
            "AND relation_type='TENANT_OF' AND source_evidence_ref=? AND source_note_id=? "
            "AND source_locale=? AND tenant_name=? AND floor=? AND category=? "
            "AND detail_url=? AND listing_url=? ORDER BY assertion_id LIMIT 1",
            (
                venue["subject_id"], source_evidence_ref, source_note_id, locale,
                tenant, floor_value, category_value, detail_value, listing_value,
            ),
        ).fetchone()
        return int(row[0])

    def query_country_entities(
        self,
        *,
        domain_id: str,
        country_iso: str,
        relation_type: str,
        as_of: Optional[str] = None,
    ) -> dict:
        domain = _normalize_domain(domain_id)
        raw_country = _text(country_iso, "country_iso", required=True, max_length=8).upper()
        other_bucket = raw_country == "OTHER"
        code = "OTHER" if other_bucket else _normalize_country_iso(raw_country)
        relation = _text(relation_type, "relation_type", required=True, max_length=32).upper()
        if relation not in COUNTRY_RELATION_TYPES:
            raise EntityRelationError("query_country_entities requires a country relation type")
        as_of_value = _normalize_timestamp(as_of, "as_of")
        if other_bucket:
            country_filter = (
                "a.country_iso GLOB '[A-Z][A-Z]' AND a.country_iso NOT IN ("
                + ",".join("?" for _ in COUNTRY_BUCKETS) + ")"
            )
            query_params = (domain, relation, *sorted(COUNTRY_BUCKETS))
        else:
            country_filter = "a.country_iso=?"
            query_params = (domain, relation, code)
        rows = self.conn.execute(
            f"SELECT a.*, r.brand_focus_id, r.subject_type, r.name_en, r.name_zh, r.status AS registry_status, "
            "e.source AS evidence_source, e.product AS evidence_product, e.domain_id AS evidence_domain_id, "
            "e.product_id AS evidence_product_id, e.result AS evidence_result, e.status AS evidence_status, "
            "e.captured_at AS evidence_captured_at, e.finished_at AS evidence_finished_at, "
            "n.url AS source_note_url "
            f"FROM {TABLE} a JOIN lumenis_subject_registry r ON r.subject_id=a.subject_id "
            "LEFT JOIN app_evidence_records e ON e.id=a.source_evidence_ref "
            "LEFT JOIN notes n ON n.note_id=a.source_note_id "
            f"WHERE a.domain_id=? AND a.relation_type=? AND {country_filter} "
            "ORDER BY r.name_en, r.subject_id, a.source_evidence_ref, a.assertion_id",
            query_params,
        ).fetchall()
        temporal_mismatch = bool(as_of_value and rows)
        claims = []
        for raw in rows:
            claim = _claim_dict(raw)
            claim["evidence_integrity"] = self._evidence_read_status(
                claim, expected_domain=domain, subject_id=claim["subject_id"]
            )
            claim["status"] = self._claim_status(claim)
            if as_of_value and not self._claim_matches_as_of(claim, as_of_value):
                continue
            claims.append(claim)
        temporal_mismatch = temporal_mismatch and not claims
        entities_by_id: dict[str, dict] = {}
        absences = []
        invalid_claims = []
        for claim in claims:
            if claim["evidence_integrity"] != "VERIFIED":
                invalid_claims.append(claim)
                continue
            if claim["claim_kind"] == "EXPLICIT_ABSENCE":
                absences.append(claim)
                continue
            entry = entities_by_id.get(claim["subject_id"])
            if entry is None:
                entry = {
                    "subject_id": claim["subject_id"],
                    "brand_focus_id": claim.get("brand_focus_id"),
                    "domain_id": claim["domain_id"],
                    "subject_type": claim["subject_type"],
                    "name_en": claim["name_en"],
                    "name_zh": claim["name_zh"],
                    "registry_status": claim["registry_status"],
                    "status": claim["status"],
                    "claims": [],
                }
                entities_by_id[claim["subject_id"]] = entry
            entry["claims"].append(claim)
            if claim["status"] == "CONFLICTED":
                entry["status"] = "CONFLICTED"
            elif claim["status"] == "ACCEPTED" and entry["status"] == "UNREVIEWED":
                entry["status"] = "PARTIAL_REVIEW"
        entities = list(entities_by_id.values())
        if any(entity["status"] == "CONFLICTED" for entity in entities):
            status = "CONFLICT"
        elif entities and all(entity["status"] == "ACCEPTED" for entity in entities):
            status = "MATCHED"
        elif entities:
            status = "UNREVIEWED"
        elif absences:
            status = "EXPLICIT_ABSENCE"
        elif invalid_claims:
            status = "EVIDENCE_INVALID"
        elif temporal_mismatch:
            status = "NOT_ESTABLISHED_FOR_AS_OF"
        else:
            status = "NOT_COLLECTED"
        return {
            "domain_id": domain,
            "country_iso": code,
            "country_bucket": "OTHER" if other_bucket else country_bucket(code),
            "relation_type": relation,
            "as_of": as_of_value,
            "status": status,
            "entities": entities,
            "absence_claims": absences,
            "claims": claims,
        }

    def query_venue_tenant_claims(
        self,
        *,
        venue_subject_id: str,
        as_of: Optional[str] = None,
    ) -> dict:
        venue = _registry_subject(self.conn, "CTH", venue_subject_id)
        as_of_value = _normalize_timestamp(as_of, "as_of")
        rows = self.conn.execute(
            f"SELECT a.*, venue.name_en AS venue_name_en, venue.name_zh AS venue_name_zh, "
            "target.brand_focus_id AS target_brand_focus_id, target.name_en AS target_name_en, "
            "target.name_zh AS target_name_zh, e.source AS evidence_source, "
            "e.product AS evidence_product, e.domain_id AS evidence_domain_id, "
            "e.product_id AS evidence_product_id, e.result AS evidence_result, "
            "e.status AS evidence_status, e.captured_at AS evidence_captured_at, "
            "e.finished_at AS evidence_finished_at, n.url AS source_note_url "
            f"FROM {TABLE} a JOIN lumenis_subject_registry venue ON venue.subject_id=a.subject_id "
            "LEFT JOIN lumenis_subject_registry target ON target.subject_id=a.target_subject_id "
            "LEFT JOIN app_evidence_records e ON e.id=a.source_evidence_ref "
            "LEFT JOIN notes n ON n.note_id=a.source_note_id "
            "WHERE a.domain_id='CTH' AND a.subject_id=? AND a.relation_type='TENANT_OF' "
            "ORDER BY a.source_locale, a.listing_url, a.tenant_name, a.assertion_id",
            (venue["subject_id"],),
        ).fetchall()
        temporal_mismatch = bool(as_of_value and rows)
        claims = []
        for raw in rows:
            claim = _claim_dict(raw)
            claim["evidence_integrity"] = self._evidence_read_status(
                claim, expected_domain="CTH", subject_id=venue["subject_id"]
            )
            claim["status"] = self._claim_status(claim)
            if as_of_value and not self._claim_matches_as_of(claim, as_of_value):
                continue
            claims.append(claim)
        temporal_mismatch = temporal_mismatch and not claims
        if not claims:
            status = "NOT_ESTABLISHED_FOR_AS_OF" if temporal_mismatch else "NOT_COLLECTED"
        elif any(claim["evidence_integrity"] != "VERIFIED" for claim in claims):
            status = "EVIDENCE_INVALID"
        elif any(claim["status"] == "CONFLICTED" for claim in claims):
            status = "CONFLICT"
        elif all(claim["status"] == "ACCEPTED" for claim in claims):
            status = "MATCHED"
        else:
            status = "UNREVIEWED"
        return {
            "domain_id": "CTH",
            "venue_subject_id": venue["subject_id"],
            "as_of": as_of_value,
            "status": status,
            "claims": claims,
        }

    def _evidence_read_status(self, claim: dict, *, expected_domain: str, subject_id: str) -> str:
        evidence_ref = claim.get("source_evidence_ref")
        row = self.conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=? LIMIT 1", (evidence_ref,)
        ).fetchone()
        if row is None:
            return "MISSING"
        from lumenis.shared.evidence.store import classify_evidence_integrity

        evidence = dict(row)
        assurance = classify_evidence_integrity(evidence)
        if (
            not assurance.get("verified")
            or assurance.get("assurance") != "writer-authenticated"
            or str(evidence.get("result") or "").upper() != "PASS"
            or str(evidence.get("status") or "").lower() != "verified"
        ):
            return "INVALID"
        expected_product = "CTH" if expected_domain == "CTH" else "ZBMP"
        expected_evidence_domain = "cth" if expected_domain == "CTH" else "zbmp"
        if (
            str(evidence.get("domain_id") or "").lower() != expected_evidence_domain
            or str(evidence.get("product_id") or "").upper() != expected_product
        ):
            return "SCOPE_MISMATCH"
        try:
            inputs = json.loads(evidence.get("inputs_json") or "")
        except (TypeError, ValueError, json.JSONDecodeError):
            return "INVALID"
        scope = inputs.get("_lumenis_scope") if isinstance(inputs, dict) else None
        if not isinstance(scope, dict):
            return "SCOPE_MISMATCH"
        if expected_domain == "CTH":
            exact = scope == {
                "domain_id": "cth", "product_id": "CTH", "global": False,
                "subject_id": subject_id,
            }
        else:
            registry = self.conn.execute(
                "SELECT brand_focus_id FROM lumenis_subject_registry WHERE subject_id=?",
                (subject_id,),
            ).fetchone()
            exact = registry is not None and scope == {
                "domain_id": "zbmp", "product_id": "ZBMP", "global": False,
                "brand_focus_id": registry[0],
            }
        if not exact:
            return "SCOPE_MISMATCH"
        note = self.conn.execute(
            "SELECT url, content, product_id, domain_id, subject_id, brand_focus_id, "
            "scope_status, scope_evidence_ref FROM notes WHERE note_id=? LIMIT 1",
            (claim.get("source_note_id"),),
        ).fetchone()
        if note is None:
            return "NOTE_MISSING"
        expected_note_domain = "cth" if expected_domain == "CTH" else "zbmp"
        if (
            str(note["domain_id"] or "").lower() != expected_note_domain
            or str(note["product_id"] or "").upper() != expected_product
            or str(note["scope_status"] or "").upper() != "VERIFIED"
            or str(note["scope_evidence_ref"] or "") != str(evidence_ref)
        ):
            return "NOTE_SCOPE_MISMATCH"
        if expected_domain == "CTH":
            if note["subject_id"] != subject_id or note["brand_focus_id"] not in (None, ""):
                return "NOTE_SCOPE_MISMATCH"
        elif note["subject_id"] not in (None, "") or note["brand_focus_id"] != registry[0]:
            return "NOTE_SCOPE_MISMATCH"
        source_ids = inputs.get("source_ids") if isinstance(inputs, dict) else None
        if not isinstance(source_ids, list) or claim.get("source_note_id") not in source_ids:
            return "NOTE_SOURCE_MISMATCH"
        if claim.get("relation_type") == "TENANT_OF":
            if note["url"] != claim.get("listing_url"):
                return "SOURCE_URL_MISMATCH"
            source_content = re.sub(r"\s+", " ", str(note["content"] or "")).casefold()
            if not source_content:
                return "SOURCE_CONTENT_EMPTY"
            if re.sub(r"\s+", " ", str(claim.get("tenant_name") or "")).casefold() not in source_content:
                return "SOURCE_CONTENT_MISMATCH"
            floor = str(claim.get("floor") or "").strip()
            if floor and re.sub(r"\s+", " ", floor).casefold() not in source_content:
                return "SOURCE_CONTENT_MISMATCH"
        return "VERIFIED"

    @staticmethod
    def _claim_status(claim: dict) -> str:
        if claim.get("review_status") == "CONFLICTED" or claim.get("conflict_group"):
            return "CONFLICTED"
        return str(claim.get("review_status") or "UNREVIEWED")

    @staticmethod
    def _claim_matches_as_of(claim: dict, as_of: str) -> bool:
        kind = claim.get("valid_time_kind")
        if kind == "UNKNOWN":
            return False
        if kind == "INTERVAL":
            point = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
            start = datetime.fromisoformat(str(claim["valid_from"]).replace("Z", "+00:00"))
            end_raw = claim.get("valid_to")
            end = datetime.fromisoformat(str(end_raw).replace("Z", "+00:00")) if end_raw else None
            return start <= point and (end is None or point < end)
        capture = claim.get("evidence_captured_at")
        if not capture:
            return False
        # A capture-as-of assertion proves only its capture date, never an
        # unbounded interval after that capture.
        if len(as_of) == 10:
            return str(capture)[:10] == as_of
        return str(capture) == as_of


__all__ = [
    "COUNTRY_RELATION_TYPES",
    "EVIDENCE_REF_TYPE",
    "EntityRelationError",
    "EntityRelationRepository",
    "country_bucket",
    "ensure_entity_relation_schema",
]
