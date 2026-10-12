"""Hermetic tests for the brand Canonical aggregate compatibility projection."""
import sqlite3

import pytest

import brand_stats_recompute as module
from brand_stats_recompute import aggregate_brand_observations, recompute_brand_stats

_BRAND_DDL = """
CREATE TABLE brand_industry_monitor (
    id INTEGER PRIMARY KEY,
    brand_name TEXT,
    brand_name_cn TEXT,
    note_count INTEGER,
    positive_count INTEGER,
    negative_count INTEGER,
    total_engagement INTEGER,
    risk_level TEXT,
    last_updated TEXT
)
"""


def _create_db(path, brands):
    with sqlite3.connect(path) as conn:
        conn.execute(_BRAND_DDL)
        conn.executemany(
            "INSERT INTO brand_industry_monitor "
            "(id, brand_name, brand_name_cn, note_count, positive_count, "
            "negative_count, total_engagement, risk_level) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            brands,
        )


def _stored_rows(path):
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(
            "SELECT * FROM brand_industry_monitor ORDER BY id"
        )]


def _canonical_row(
    *, canonical_id="canonical-1", sentiment="positive", risk_level="low",
    likes=0, comments=0, collects=0, shares=0, product_id="CTH",
    domain_id="cth", subject_id="SUBJECT-A", brand_focus_id="",
):
    evidence_ref = f"scope-evidence-{canonical_id}"
    source_id = f"source-{canonical_id}"
    scope = {
        "product_id": product_id,
        "domain_id": domain_id,
        "subject_id": subject_id or "",
        "brand_focus_id": brand_focus_id or "",
        "scope_status": "VERIFIED",
    }
    return {
        "canonical_id": canonical_id,
        "product_id": product_id,
        "domain_id": domain_id,
        "subject_id": subject_id,
        "brand_focus_id": brand_focus_id,
        "scope_status": "VERIFIED",
        "scope_evidence_ref": evidence_ref,
        "source_id": source_id,
        "sentiment": sentiment,
        "risk_level": risk_level,
        "engagement_likes": likes,
        "engagement_comments": comments,
        "engagement_collects": collects,
        "engagement_shares": shares,
        # Test-only callback proof. This fixture does not authenticate real scope.
        "scope_evidence": {
            "id": evidence_ref,
            "source_id": source_id,
            "stored_scope": scope,
            "integrity": {
                "verified": True,
                "lineage_verified": True,
                "assurance": "writer-authenticated",
            },
        },
    }


def _snapshot(records, *, candidate_count=None, scanned_count=None,
              rejected_count=0, limit=30, truncated=False):
    returned = len(records)
    if scanned_count is None:
        scanned_count = returned + rejected_count
    if candidate_count is None:
        candidate_count = scanned_count
    return {
        "records": records,
        "candidate_count": candidate_count,
        "scanned_count": scanned_count,
        "returned_count": returned,
        "rejected_count": rejected_count,
        "limit": limit,
        "truncated": truncated,
    }


def _authorized():
    return {
        "permission_audit_ref": "test-permission-audit",
        "operation_audit_ref": "test-operation-audit",
    }


def test_aggregate_preserves_real_zero_and_keeps_critical_separate():
    rows = [
        _canonical_row(canonical_id="critical", sentiment="negative", risk_level="critical"),
        _canonical_row(canonical_id="ordinary", sentiment="positive", risk_level="low"),
    ]

    result = aggregate_brand_observations(rows, complete_scan=True)

    assert result["state"] == "COMPLETE"
    assert result["values"] == {
        "note_count": 2,
        "positive_count": 1,
        "neutral_count": 0,
        "negative_count": 1,
        "total_engagement": 0,
        "risk_level": "high",
    }
    assert result["observed"]["risk"]["high"] == 0
    assert result["observed"]["risk"]["critical"] == 1
    assert result["observed"]["engagement"]["sum"] == 0


def test_aggregate_keeps_unknown_labels_and_incomplete_engagement_unknown():
    result = aggregate_brand_observations(
        [_canonical_row(sentiment="unknown", risk_level="unknown", likes=4, comments=None)],
        complete_scan=True,
    )

    assert result["state"] == "PARTIAL"
    assert result["values"]["note_count"] == 1
    assert result["values"]["positive_count"] is None
    assert result["values"]["negative_count"] is None
    assert result["values"]["total_engagement"] is None
    assert result["values"]["risk_level"] is None
    assert result["observed"]["sentiment"]["unknown"] == 1
    assert result["observed"]["risk"]["other"] == 1
    engagement = result["observed"]["engagement"]
    assert engagement["sum"] is None
    assert engagement["observed_sum"] == 4
    assert engagement["observed_per_field"]["engagement_likes"] == 4
    assert result["canonical_runtime_verified"] is False
    assert result["live_state"] == "LIVE_NOT_VERIFIED"
    assert result["commercial_state"] == "COMMERCIAL_NOT_VERIFIED"
    assert result["commercial_ready"] is False


def test_aggregate_partial_scan_retains_observations_but_nulls_full_values():
    result = aggregate_brand_observations(
        [_canonical_row(likes=3, comments=2, collects=1, shares=0)],
        complete_scan=False,
    )

    assert result["state"] == "PARTIAL"
    assert result["values"] == {
        "note_count": None,
        "positive_count": None,
        "neutral_count": None,
        "negative_count": None,
        "total_engagement": None,
        "risk_level": None,
    }
    assert result["observed"]["record_count"] == 1
    assert result["observed"]["engagement"]["observed_sum"] == 6
    assert result["observed"]["engagement"]["quality"]["known_field_count"] == 4


def test_empty_incomplete_sample_does_not_prove_no_collection():
    result = aggregate_brand_observations([], complete_scan=False)

    assert result["state"] == "PARTIAL"
    assert all(value is None for value in result["values"].values())
    assert result["observed"]["record_count"] == 0
    assert result["quality"]["complete_scan"] is False


def test_empty_complete_sample_is_not_collected_not_zero():
    result = aggregate_brand_observations([], complete_scan=True)

    assert result["state"] == "NOT_COLLECTED"
    assert all(value is None for value in result["values"].values())
    assert result["observed"]["record_count"] == 0
    assert result["observed"]["engagement"]["sum"] is None


@pytest.mark.parametrize("bad", [1, 0, None, "true"])
def test_complete_scan_requires_exact_boolean(bad):
    with pytest.raises(TypeError, match="explicit boolean"):
        aggregate_brand_observations([], complete_scan=bad)


def test_to_int_compatibility_uses_canonical_missing_and_invalid_semantics():
    assert module._to_int(0) == 0
    assert module._to_int("1,200") == 1200
    assert module._to_int(None) is None
    assert module._to_int(True) is None
    assert module._to_int(-1) is None
    assert module._to_int("not-a-count") is None


def test_missing_callbacks_fail_before_database_repository_is_opened(monkeypatch, tmp_path):
    def forbidden_repository(*args, **kwargs):
        raise AssertionError("repository must not be constructed")

    monkeypatch.setattr(module, "DatabaseRepository", forbidden_repository)
    with pytest.raises(PermissionError, match="callbacks are required"):
        recompute_brand_stats(db_path=str(tmp_path / "must-not-open.sqlite"), verbose=False)


def test_successful_callback_projection_rechecks_authorization_and_keeps_boundary(tmp_path):
    db_path = tmp_path / "brand-projection.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 88, 12, 3, 777, "medium")])
    calls = {"authorize": 0, "read": 0}

    def authorize():
        calls["authorize"] += 1
        return {
            "permission_audit_ref": f"test-permission-audit-{calls['authorize']}",
            "operation_audit_ref": f"test-operation-audit-{calls['authorize']}",
        }

    def read_brand_records(connection, brand):
        calls["read"] += 1
        assert brand["id"] == 1
        return _snapshot([
            _canonical_row(canonical_id="critical", sentiment="negative", risk_level="critical"),
            _canonical_row(canonical_id="positive", sentiment="positive", risk_level="low"),
        ])

    result = recompute_brand_stats(
        str(db_path), verbose=False,
        read_brand_records=read_brand_records,
        authorize=authorize,
    )

    assert calls["authorize"] >= 5
    assert calls["read"] == 1
    assert result["updated"] == 1
    assert result["brands"][0]["snapshot"]["rejected_count"] == 0
    assert result["brands"][0]["values"]["total_engagement"] == 0
    assert result["source_basis"] == "SCOPED_CANONICAL_FROM_OWNER"
    assert result["canonical_runtime_verified"] is False
    assert result["live_state"] == "LIVE_NOT_VERIFIED"
    assert result["commercial_state"] == "COMMERCIAL_NOT_VERIFIED"
    assert result["commercial_ready"] is False
    assert "source_level=True" in result["normal_dependency"]
    assert result["aggregate_projection_bound"] is False
    assert "scope lineage proof" in result["scope_proof_limit"]
    assert result["final_authorization_receipt"] == {
        "permission_audit_ref": "test-permission-audit-5",
        "operation_audit_ref": "test-operation-audit-5",
    }
    assert result["authorization_receipt_is_scope_proof"] is False
    stored = _stored_rows(db_path)[0]
    assert (stored["note_count"], stored["positive_count"], stored["negative_count"]) == (2, 1, 1)
    assert stored["total_engagement"] == 0
    assert stored["risk_level"] == "high"


def test_no_keyword_brand_is_skipped_without_clearing_existing_values(tmp_path):
    db_path = tmp_path / "brand-no-key.sqlite"
    _create_db(db_path, [(1, "AB", "", 52, 11, 4, 321, "high")])
    reads = []

    result = recompute_brand_stats(
        str(db_path), verbose=False,
        read_brand_records=lambda *_args: reads.append(True),
        authorize=_authorized,
    )

    assert result["updated"] == 0
    assert result["brands"][0]["state"] == "UNAVAILABLE"
    assert result["brands"][0]["reason"] == "NO_BRAND_KEYWORDS"
    assert result["brands"][0]["values"]["note_count"] is None
    assert reads == []
    stored = _stored_rows(db_path)[0]
    assert (stored["note_count"], stored["positive_count"], stored["negative_count"]) == (52, 11, 4)
    assert stored["total_engagement"] == 321
    assert stored["risk_level"] == "high"


def test_rejected_canonical_row_makes_scan_partial_and_persisted_totals_unknown(tmp_path):
    db_path = tmp_path / "brand-rejected.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 88, 12, 3, 777, "medium")])
    snapshot = _snapshot(
        [_canonical_row()], candidate_count=2, scanned_count=2,
        rejected_count=1, limit=10, truncated=False,
    )

    result = recompute_brand_stats(
        str(db_path), verbose=False,
        read_brand_records=lambda *_args: snapshot,
        authorize=_authorized,
    )

    aggregate = result["brands"][0]
    assert aggregate["state"] == "PARTIAL"
    assert aggregate["snapshot"]["rejected_count"] == 1
    assert aggregate["observed"]["record_count"] == 1
    assert all(value is None for value in aggregate["values"].values() if value != "unknown")
    assert aggregate["values"]["risk_level"] is None
    stored = _stored_rows(db_path)[0]
    assert stored["note_count"] is None
    assert stored["positive_count"] is None
    assert stored["negative_count"] is None
    assert stored["total_engagement"] is None
    assert stored["risk_level"] == "unknown"


def test_malformed_snapshot_fails_closed_and_rolls_back_batch(tmp_path):
    db_path = tmp_path / "brand-malformed.sqlite"
    _create_db(db_path, [(1, "FirstBrand", "第一品牌", 41, 8, 2, 200, "low")])
    malformed = _snapshot([_canonical_row()], candidate_count=3, scanned_count=1)

    with pytest.raises(ValueError, match="failed validation"):
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=lambda *_args: malformed,
            authorize=_authorized,
        )

    stored = _stored_rows(db_path)[0]
    assert (stored["note_count"], stored["positive_count"], stored["negative_count"]) == (41, 8, 2)
    assert stored["total_engagement"] == 200
    assert stored["risk_level"] == "low"


@pytest.mark.parametrize("malformation", ["missing-returned", "wrong-returned", "truncated-not-bool", "boolean-count"])
def test_snapshot_count_and_truncation_fields_are_strict(tmp_path, malformation):
    db_path = tmp_path / f"brand-snapshot-{malformation}.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 41, 8, 2, 200, "low")])
    snapshot = _snapshot([_canonical_row()])
    if malformation == "missing-returned":
        snapshot.pop("returned_count")
    elif malformation == "wrong-returned":
        snapshot["returned_count"] = 0
    elif malformation == "truncated-not-bool":
        snapshot["truncated"] = 0
    elif malformation == "boolean-count":
        snapshot["candidate_count"] = True

    with pytest.raises(ValueError, match="failed validation"):
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=lambda *_args: snapshot,
            authorize=_authorized,
        )

    stored = _stored_rows(db_path)[0]
    assert stored["note_count"] == 41
    assert stored["total_engagement"] == 200


@pytest.mark.parametrize(
    "case",
    [
        "empty-canonical-id",
        "empty-source-id",
        "invalid-product-domain",
        "mixed-domain",
        "mixed-focus",
        "duplicate-canonical-id",
        "duplicate-source-id",
        "missing-exact-focus",
    ],
)
def test_snapshot_identity_or_scope_conflict_fails_closed(tmp_path, case):
    db_path = tmp_path / f"brand-identity-{case}.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 41, 8, 2, 200, "low")])
    first = _canonical_row(canonical_id="first")
    records = [first]

    if case == "empty-canonical-id":
        first["canonical_id"] = ""
    elif case == "empty-source-id":
        first["source_id"] = ""
        first["scope_evidence"]["source_id"] = ""
    elif case == "invalid-product-domain":
        first["domain_id"] = "zbmp"
        first["scope_evidence"]["stored_scope"]["domain_id"] = "zbmp"
    elif case == "mixed-domain":
        records.append(_canonical_row(
            canonical_id="second", product_id="ZBMP", domain_id="zbmp",
            subject_id=None, brand_focus_id="BRAND-A",
        ))
    elif case == "mixed-focus":
        records.append(_canonical_row(canonical_id="second", subject_id="SUBJECT-B"))
    elif case == "duplicate-canonical-id":
        second = _canonical_row(canonical_id="second")
        second["canonical_id"] = first["canonical_id"]
        records.append(second)
    elif case == "duplicate-source-id":
        second = _canonical_row(canonical_id="second")
        second["source_id"] = first["source_id"]
        second["scope_evidence"]["source_id"] = first["source_id"]
        records.append(second)
    elif case == "missing-exact-focus":
        first["subject_id"] = ""
        first["scope_evidence"]["stored_scope"]["subject_id"] = ""

    with pytest.raises(ValueError, match="failed validation"):
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=lambda *_args: _snapshot(records),
            authorize=_authorized,
        )

    stored = _stored_rows(db_path)[0]
    assert (stored["note_count"], stored["positive_count"], stored["negative_count"]) == (41, 8, 2)
    assert stored["total_engagement"] == 200
    assert stored["risk_level"] == "low"


@pytest.mark.parametrize("denied_on_call", [3, 4, 5])
def test_authorization_denial_before_read_after_read_or_commit_rolls_back(
    tmp_path, denied_on_call,
):
    db_path = tmp_path / f"brand-denied-{denied_on_call}.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 41, 8, 2, 200, "low")])
    calls = {"authorize": 0, "read": 0}

    def authorize():
        calls["authorize"] += 1
        if calls["authorize"] == denied_on_call:
            return None
        return _authorized()

    def read_brand_records(*_args):
        calls["read"] += 1
        return _snapshot([_canonical_row()])

    with pytest.raises(PermissionError, match="authorization is invalid"):
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=read_brand_records,
            authorize=authorize,
        )

    if denied_on_call == 3:
        assert calls["read"] == 0
    assert _stored_rows(db_path)[0]["note_count"] == 41
    assert _stored_rows(db_path)[0]["total_engagement"] == 200


def test_reader_oserror_is_sanitized_and_rolls_back(tmp_path):
    db_path = tmp_path / "brand-reader-error.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 41, 8, 2, 200, "low")])

    def fail_read(*_args):
        raise OSError("private implementation detail")

    with pytest.raises(RuntimeError, match="scoped Canonical brand read failed") as caught:
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=fail_read,
            authorize=_authorized,
        )
    assert "private implementation detail" not in str(caught.value)
    assert _stored_rows(db_path)[0]["note_count"] == 41


def test_late_batch_failure_rolls_back_earlier_update_and_closes_connection(
    tmp_path, monkeypatch,
):
    db_path = tmp_path / "brand-close.sqlite"
    _create_db(db_path, [
        (1, "FirstBrand", "第一品牌", 41, 8, 2, 200, "low"),
        (2, "SecondBrand", "第二品牌", 61, 9, 3, 300, "medium"),
    ])
    opened = []

    class TrackingConnection(sqlite3.Connection):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.did_rollback = False
            self.did_close = False

        def rollback(self):
            self.did_rollback = True
            return super().rollback()

        def close(self):
            self.did_close = True
            return super().close()

    statements = []
    # The first statement is captured on the connection returned by the repo.
    def tracked_connect(self, **kwargs):
        connection = sqlite3.connect(self.db_path, factory=TrackingConnection, **kwargs)
        connection.set_trace_callback(statements.append)
        opened.append(connection)
        return connection

    monkeypatch.setattr(module.DatabaseRepository, "connect", tracked_connect)
    reads = {"count": 0}

    def read_brand_records(_connection, _brand):
        reads["count"] += 1
        if reads["count"] == 2:
            raise OSError("late private read failure")
        return _snapshot([_canonical_row()])

    with pytest.raises(RuntimeError, match="scoped Canonical brand read failed"):
        recompute_brand_stats(
            str(db_path), verbose=False,
            read_brand_records=read_brand_records,
            authorize=_authorized,
        )

    assert len(opened) == 1
    assert statements[0] == "BEGIN IMMEDIATE"
    assert opened[0].did_rollback is True
    assert opened[0].did_close is True
    stored = _stored_rows(db_path)
    assert [row["note_count"] for row in stored] == [41, 61]
    assert [row["total_engagement"] for row in stored] == [200, 300]


def test_empty_snapshot_stores_not_collected_as_unknown_not_zero(tmp_path):
    db_path = tmp_path / "brand-empty.sqlite"
    _create_db(db_path, [(1, "ExampleBrand", "示例品牌", 41, 8, 2, 200, "low")])

    result = recompute_brand_stats(
        str(db_path), verbose=False,
        read_brand_records=lambda *_args: _snapshot([]),
        authorize=_authorized,
    )

    assert result["brands"][0]["state"] == "NOT_COLLECTED"
    assert all(value is None for value in result["brands"][0]["values"].values())
    stored = _stored_rows(db_path)[0]
    assert stored["note_count"] is None
    assert stored["positive_count"] is None
    assert stored["negative_count"] is None
    assert stored["total_engagement"] is None
    assert stored["risk_level"] == "unknown"
