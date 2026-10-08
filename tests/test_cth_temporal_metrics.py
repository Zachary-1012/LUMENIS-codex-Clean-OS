"""Scoped, publication-time CTH metric reads over Canonical snapshots."""

from copy import deepcopy
from datetime import date, timedelta
import json
import sqlite3

import pytest

import canonical_data
from canonical_data import CanonicalRecord, persist_canonical
from lumenis.shared.evidence import store as evidence_store
from trend_api import read_cth_temporal_metrics


def _binding(scope="FOCUS", subject="SUBJ-A", **overrides):
    binding = {
        "contract": "lumenis.scope-read-binding.v1",
        "module": "commercial_realtime_stream",
        "policy": "actor-exact-scope-v1",
        "domain_id": "CTH",
        "product_id": "CTH",
        "canonical_scope": scope,
        "subject_id": subject if scope == "FOCUS" else None,
        "applied": True,
        "read_allowed": True,
        "scope_verified": True,
        "actor_scope": "authenticated",
        "global_all_granted": scope == "GLOBAL_ALL",
    }
    binding.update(overrides)
    return binding


def _record(
    *, canonical_id="can-1", source_id="raw-1", subject="SUBJ-A",
    publish_datetime="2026-03-04", captured_at="2026-03-20T12:00:00Z",
    sentiment="positive", risk_level="low", quality_status="ok",
):
    return {
        "canonical_id": canonical_id,
        "product_id": "CTH",
        "domain_id": "cth",
        "subject_id": subject,
        "brand_focus_id": "",
        "scope_status": "VERIFIED",
        "source_id": source_id,
        "publish_datetime": publish_datetime,
        "captured_at": captured_at,
        "sentiment": sentiment,
        "risk_level": risk_level,
        "quality_status": quality_status,
        "title": "private source title",
        "content": "private source body",
        "scope_evidence": {
            "id": 17,
            "source_id": source_id,
            "stored_scope": {
                "product_id": "CTH", "domain_id": "cth",
                "subject_id": subject, "brand_focus_id": "",
                "scope_status": "VERIFIED",
            },
            "integrity": {
                "verified": True, "lineage_verified": True,
                "assurance": "writer-authenticated",
            },
        },
    }


def _snapshot(
    records, *, candidate_count=None, scanned_count=None,
    rejected_count=0, limit=100, truncated=False,
):
    returned_count = len(records)
    if scanned_count is None:
        scanned_count = returned_count + rejected_count
    if candidate_count is None:
        candidate_count = scanned_count + int(truncated)
    return {
        "records": records,
        "candidate_count": candidate_count,
        "scanned_count": scanned_count,
        "rejected_count": rejected_count,
        "returned_count": returned_count,
        "limit": limit,
        "truncated": truncated,
    }


def _patch_snapshot(monkeypatch, snapshot=None, *, error=None):
    calls = []

    def read(connection, **kwargs):
        calls.append((connection, kwargs))
        if error is not None:
            raise error
        return deepcopy(snapshot)

    monkeypatch.setattr(canonical_data, "list_scoped_canonical", read)
    return calls


def _read(monkeypatch, snapshot, *, binding=None, start_date="2026-03-04",
          end_date="2026-03-04", connection=None):
    calls = _patch_snapshot(monkeypatch, snapshot)
    authorizations = []
    expected_binding = binding or _binding()

    def authorize():
        authorizations.append(True)
        return deepcopy(expected_binding)

    connection = connection if connection is not None else object()
    result = read_cth_temporal_metrics(
        connection, start_date=start_date, end_date=end_date, authorize=authorize,
    )
    return result, calls, authorizations, connection


@pytest.mark.parametrize(
    "denied",
    [
        {"read_allowed": False},
        {"scope_verified": False},
        {"applied": False},
        {"contract": "wrong-contract"},
        {"product_id": "BMP"},
        {"domain_id": "BMP"},
        {"canonical_scope": "FOCUS", "subject_id": None},
        {"canonical_scope": "GLOBAL_ALL", "subject_id": "SUBJ-A"},
        {"canonical_scope": "UNKNOWN", "subject_id": None},
        {"policy": "unknown-policy"},
        {"actor_scope": "unknown-actor-scope"},
        {"policy": "actor-exact-scope-v1", "actor_scope": "anonymous_read"},
        {"policy": "local-workspace-read-v1", "actor_scope": "authenticated"},
    ],
)
def test_missing_or_invalid_authorization_never_reads_or_returns_data(monkeypatch, denied):
    calls = _patch_snapshot(monkeypatch, _snapshot([_record()]))
    binding = _binding(**denied, private_marker="must-not-leak")

    with pytest.raises(PermissionError) as raised:
        read_cth_temporal_metrics(
            object(), start_date="2026-03-04", end_date="2026-03-04",
            authorize=lambda: binding,
        )

    assert calls == []
    assert "must-not-leak" not in str(raised.value)


@pytest.mark.parametrize(
    "binding",
    [
        _binding("FOCUS", "SUBJ-A", global_all_granted=True),
        _binding("GLOBAL_ALL", None, global_all_granted=False),
    ],
)
def test_inconsistent_scope_grant_receipt_never_reads(monkeypatch, binding):
    calls = _patch_snapshot(monkeypatch, _snapshot([_record()]))

    with pytest.raises(PermissionError):
        read_cth_temporal_metrics(
            object(), start_date="2026-03-04", end_date="2026-03-04",
            authorize=lambda: binding,
        )

    assert calls == []


@pytest.mark.parametrize(
    "binding",
    [
        _binding("FOCUS", "SUBJ-A", global_all_granted=0),
        _binding("GLOBAL_ALL", None, global_all_granted=1),
    ],
)
def test_non_boolean_global_grant_receipt_never_reads(monkeypatch, binding):
    calls = _patch_snapshot(monkeypatch, _snapshot([_record()]))

    with pytest.raises(PermissionError):
        read_cth_temporal_metrics(
            object(), start_date="2026-03-04", end_date="2026-03-04",
            authorize=lambda: binding,
        )

    assert calls == []


def test_none_authorizer_never_reads(monkeypatch):
    calls = _patch_snapshot(monkeypatch, _snapshot([_record()]))

    with pytest.raises(PermissionError, match="authorization"):
        read_cth_temporal_metrics(
            object(), start_date="2026-03-04", end_date="2026-03-04",
            authorize=None,
        )

    assert calls == []


@pytest.mark.parametrize(
    ("binding", "expected_subject", "records"),
    [
        (
            _binding("FOCUS", "SUBJ-A"), "SUBJ-A",
            [_record(subject="SUBJ-A")],
        ),
        (
            _binding("GLOBAL_ALL", None), None,
            [_record(canonical_id="can-a", source_id="raw-a", subject="SUBJ-A"),
             _record(canonical_id="can-b", source_id="raw-b", subject="SUBJ-B")],
        ),
        (
            _binding(
                "FOCUS", "SUBJ-A", policy="local-workspace-read-v1",
                actor_scope="anonymous_read", global_all_granted=False,
            ), "SUBJ-A", [_record(subject="SUBJ-A")],
        ),
        (
            _binding(
                "GLOBAL_ALL", None, policy="local-workspace-read-v1",
                actor_scope="anonymous_read", global_all_granted=False,
            ), None,
            [_record(canonical_id="can-local-a", source_id="raw-local-a", subject="SUBJ-A"),
             _record(canonical_id="can-local-b", source_id="raw-local-b", subject="SUBJ-B")],
        ),
    ],
)
def test_authorized_focus_and_global_reads_use_exact_binding(
    monkeypatch, binding, expected_subject, records,
):
    snapshot = _snapshot(records)
    calls = _patch_snapshot(monkeypatch, snapshot)
    authorization_calls = []

    def authorize():
        authorization_calls.append(True)
        return deepcopy(binding)

    connection = object()
    result = read_cth_temporal_metrics(
        connection, start_date="2026-03-04", end_date="2026-03-04",
        authorize=authorize,
    )

    assert authorization_calls == [True, True]
    assert len(calls) == 1 and calls[0][0] is connection
    assert calls[0][1] == {
        "product_id": "CTH", "subject_id": expected_subject,
        "limit": 100, "source_level": True,
    }
    assert result["binding"] == binding
    assert result["read"]["returned_count"] == len(records)
    assert result["state"] == "ready"


@pytest.mark.parametrize(
    ("second_binding", "message"),
    [
        (_binding("FOCUS", "SUBJ-B"), "scope changed"),
        (_binding("GLOBAL_ALL", None), "scope changed"),
        (_binding("FOCUS", "SUBJ-A", read_allowed=False), "not authorized"),
    ],
)
def test_revocation_or_scope_change_after_snapshot_never_returns_snapshot(
    monkeypatch, second_binding, message,
):
    record = _record(source_id="secret-source-that-must-not-return")
    calls = _patch_snapshot(monkeypatch, _snapshot([record]))
    bindings = [_binding("FOCUS", "SUBJ-A"), second_binding]
    authorization_calls = []

    def authorize():
        index = len(authorization_calls)
        authorization_calls.append(True)
        return deepcopy(bindings[min(index, 1)])

    with pytest.raises(PermissionError, match=message):
        read_cth_temporal_metrics(
            object(), start_date="2026-03-04", end_date="2026-03-04",
            authorize=authorize,
        )

    assert authorization_calls == [True, True]
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        ("2026-02-30", "2026-03-04"),
        ("2026-03-04T00:00:00Z", "2026-03-04"),
        ((date.today() + timedelta(days=1)).isoformat(),
         (date.today() + timedelta(days=1)).isoformat()),
    ],
)
def test_invalid_or_future_window_fails_before_authorization_or_read(
    monkeypatch, start_date, end_date,
):
    calls = _patch_snapshot(monkeypatch, _snapshot([]))
    authorization_calls = []

    def authorize():
        authorization_calls.append(True)
        return _binding()

    with pytest.raises(ValueError):
        read_cth_temporal_metrics(
            object(), start_date=start_date, end_date=end_date,
            authorize=authorize,
        )

    assert authorization_calls == []
    assert calls == []


def test_native_publication_dates_and_offset_datetimes_keep_their_source_day(monkeypatch):
    rows = [
        _record(canonical_id="can-date", source_id="raw-date",
                publish_datetime="2026-03-04", captured_at="2026-04-01T00:00:00Z"),
        _record(canonical_id="can-offset-a", source_id="raw-offset-a",
                publish_datetime="2026-03-04T23:30:00-08:00"),
        _record(canonical_id="can-offset-b", source_id="raw-offset-b",
                publish_datetime="2026-03-05T00:30:00+14:00"),
    ]

    result, _, _, _ = _read(
        monkeypatch, _snapshot(rows), start_date="2026-03-04", end_date="2026-03-05",
    )

    by_date = {day["date"]: day for day in result["days"]}
    assert by_date["2026-03-04"]["total"]["value"] == 2
    assert by_date["2026-03-04"]["total"]["observed_count"] == 2
    assert by_date["2026-03-05"]["total"]["value"] == 1
    assert [item["publication_day"] for item in result["contributions"]] == [
        "2026-03-04", "2026-03-04", "2026-03-05",
    ]
    assert result["window"]["time_basis"] == "native_publication_calendar_day"
    assert result["window"]["timezone_conversion"] == "none"
    assert result["recipe"] == "CTH_NATIVE_PUBLICATION_COUNTS_V1"
    assert result["metric_definitions"]["high"].endswith("excludes critical")


def test_missing_invalid_and_capture_only_times_stay_unknown(monkeypatch):
    rows = [
        _record(canonical_id="can-known", source_id="raw-known",
                publish_datetime="2026-03-04"),
        _record(canonical_id="can-missing", source_id="raw-missing",
                publish_datetime=None, captured_at="2026-03-04T10:00:00Z"),
        _record(canonical_id="can-capture-only", source_id="raw-capture-only",
                publish_datetime="", captured_at="2026-03-04T11:00:00Z"),
        _record(canonical_id="can-invalid", source_id="raw-invalid",
                publish_datetime="2026-02-30T12:00:00Z", captured_at="2026-03-04T12:00:00Z"),
        _record(canonical_id="can-outside", source_id="raw-outside",
                publish_datetime="2026-03-03", captured_at="2026-03-04T13:00:00Z"),
    ]

    result, _, _, _ = _read(monkeypatch, _snapshot(rows))

    assert result["state"] == "partial"
    assert result["unknown_publication_count"] == 3
    assert result["outside_window_count"] == 1
    assert result["days"][0]["total"] == {
        "value": None, "observed_count": 1, "unknown_count": 0, "state": "partial",
    }
    assert [item["publication_day"] for item in result["contributions"]] == [
        "2026-03-04", None, None, None, "2026-03-03",
    ]
    assert result["contributions"][1]["captured_at"] == "2026-03-04T10:00:00Z"


def test_absent_day_is_not_collected_while_observed_zero_remains_zero(monkeypatch):
    rows = [_record(sentiment="positive", risk_level="low")]

    result, _, _, _ = _read(
        monkeypatch, _snapshot(rows), start_date="2026-03-04", end_date="2026-03-05",
    )

    observed_day, absent_day = result["days"]
    assert result["state"] == "partial"
    for name in ("negative", "high", "critical"):
        assert observed_day[name] == {
            "value": 0, "observed_count": 0, "unknown_count": 0, "state": "ready",
        }
    assert absent_day["total"] == {
        "value": None, "observed_count": 0, "unknown_count": 0,
        "state": "notcollected",
    }
    assert absent_day["negative"]["value"] is None


def test_empty_window_is_not_collected_not_a_measured_zero(monkeypatch):
    result, _, _, _ = _read(
        monkeypatch, _snapshot([]), start_date="2026-03-04", end_date="2026-03-05",
    )

    assert result["state"] == "notcollected"
    assert all(day["total"] == {
        "value": None, "observed_count": 0, "unknown_count": 0,
        "state": "notcollected",
    } for day in result["days"])
    assert result["totals"]["negative"]["value"] is None


@pytest.mark.parametrize("risk_level", ["unknown", "bogus", None, ""])
def test_unknown_sentiment_or_risk_stays_unknown_instead_of_zero(monkeypatch, risk_level):
    rows = [_record(sentiment="unrecognized", risk_level=risk_level)]

    result, _, _, _ = _read(monkeypatch, _snapshot(rows))

    day = result["days"][0]
    assert result["state"] == "partial"
    assert day["total"]["value"] == 1
    assert day["negative"]["value"] is None
    assert day["negative"]["observed_count"] == 0
    assert day["negative"]["unknown_count"] == 1
    assert day["negative"]["state"] == "partial"
    assert day["high"]["value"] is None
    assert day["high"]["observed_count"] == 0
    assert day["high"]["unknown_count"] == 1
    assert day["critical"]["value"] is None
    assert day["critical"]["unknown_count"] == 1


@pytest.mark.parametrize("quality_status", ["review", "error", None])
def test_quality_and_label_uncertainty_count_each_record_once_per_metric(
    monkeypatch, quality_status,
):
    rows = [_record(
        sentiment="unrecognized", risk_level="unrecognized",
        quality_status=quality_status,
    )]

    result, _, _, _ = _read(monkeypatch, _snapshot(rows))

    day = result["days"][0]
    assert result["state"] == "partial"
    assert day["total"] == {
        "value": None, "observed_count": 1, "unknown_count": 1, "state": "partial",
    }
    for name in ("negative", "high", "critical"):
        assert day[name]["value"] is None
        assert day[name]["observed_count"] == 0
        assert day[name]["unknown_count"] == 1
        assert day[name]["state"] == "partial"


def test_unknown_label_does_not_erase_other_genuine_total_or_known_bucket(monkeypatch):
    rows = [
        _record(canonical_id="can-unknown", source_id="raw-unknown",
                sentiment="unrecognized", risk_level="low"),
        _record(canonical_id="can-known", source_id="raw-known",
                publish_datetime="2026-03-05", sentiment="negative", risk_level="high"),
    ]

    result, _, _, _ = _read(
        monkeypatch, _snapshot(rows), start_date="2026-03-04", end_date="2026-03-05",
    )

    assert result["state"] == "partial"
    assert result["totals"]["total"]["value"] == 2
    assert result["totals"]["total"]["state"] == "ready"
    assert result["totals"]["negative"]["value"] is None
    assert result["totals"]["negative"]["unknown_count"] == 1
    assert result["days"][0]["total"]["value"] == 1
    assert result["days"][0]["negative"]["value"] is None
    assert result["days"][1]["negative"]["value"] == 1
    assert result["days"][1]["high"]["value"] == 1


def test_high_risk_bucket_excludes_critical(monkeypatch):
    rows = [
        _record(canonical_id="can-high", source_id="raw-high", risk_level="high"),
        _record(canonical_id="can-critical", source_id="raw-critical", risk_level="critical"),
    ]

    result, _, _, _ = _read(monkeypatch, _snapshot(rows))

    day = result["days"][0]
    assert day["high"]["value"] == day["high"]["observed_count"] == 1
    assert day["critical"]["value"] == day["critical"]["observed_count"] == 1


@pytest.mark.parametrize("case", ["truncated", "rejected", "unknown-time"])
def test_incomplete_snapshots_keep_observed_counts_and_source_contributions(monkeypatch, case):
    row = _record(
        canonical_id="can-observed", source_id="raw-observed",
        sentiment="negative", risk_level="high",
    )
    if case == "truncated":
        snapshot = _snapshot(
            [row], candidate_count=2, scanned_count=1, limit=1, truncated=True,
        )
    elif case == "rejected":
        snapshot = _snapshot(
            [row], candidate_count=2, scanned_count=2,
            rejected_count=1, limit=100, truncated=False,
        )
    else:
        unknown_time = _record(
            canonical_id="can-no-time", source_id="raw-no-time",
            publish_datetime=None, captured_at="2026-03-04T09:00:00Z",
        )
        snapshot = _snapshot([row, unknown_time])

    result, _, _, _ = _read(monkeypatch, snapshot)

    day = result["days"][0]
    assert result["state"] == "partial"
    assert day["total"]["value"] is None
    assert day["total"]["observed_count"] == 1
    assert day["negative"]["value"] is None
    assert day["negative"]["observed_count"] == 1
    assert day["high"]["value"] is None
    assert day["high"]["observed_count"] == 1
    assert result["contributions"][0]["canonical_id"] == "can-observed"
    assert result["contributions"][0]["source_id"] == "raw-observed"
    assert result["contributions"][0]["scope_evidence"]["integrity"]["verified"] is True
    if case == "truncated":
        assert result["read"]["truncated"] is True
    elif case == "rejected":
        assert result["read"]["rejected_count"] == 1
    else:
        assert result["unknown_publication_count"] == 1
        assert result["read"]["returned_count"] == 2


def test_canonical_dependency_oserror_is_sanitized_and_never_zero(monkeypatch):
    calls = _patch_snapshot(monkeypatch, error=OSError("private db path and stack marker"))
    authorization_calls = []

    def authorize():
        authorization_calls.append(True)
        return _binding()

    result = read_cth_temporal_metrics(
        object(), start_date="2026-03-04", end_date="2026-03-04",
        authorize=authorize,
    )

    encoded = json.dumps(result, sort_keys=True)
    assert len(calls) == 1 and authorization_calls == [True, True]
    assert result["state"] == "error"
    assert result["code"] == "CANONICAL_READ_UNAVAILABLE"
    assert result["days"][0]["total"]["value"] is None
    assert result["totals"]["negative"]["value"] is None
    assert result["contributions"] == []
    assert result["snapshot_sha256"] is None
    assert "private db path" not in encoded and "stack marker" not in encoded


@pytest.mark.parametrize(
    "snapshot",
    [
        {
            **_snapshot([_record()]),
            "scanned_count": 0,
        },
        {
            **_snapshot([_record()], candidate_count=2, scanned_count=1, limit=1, truncated=True),
            "truncated": False,
        },
        {
            **_snapshot([_record()]),
            "returned_count": 0,
        },
    ],
)
def test_malformed_snapshot_counts_fail_closed_without_contributions(monkeypatch, snapshot):
    result, _, authorizations, _ = _read(monkeypatch, snapshot)

    assert authorizations == [True, True]
    assert result["state"] == "error"
    assert result["code"] == "CANONICAL_READ_INVALID"
    assert result["coverage"] == "NOT_VERIFIED"
    assert result["contributions"] == []
    assert result["snapshot_sha256"] is None
    assert result["totals"]["total"]["value"] is None


def test_snapshot_pin_is_stable_and_changes_with_source_time_or_label(monkeypatch):
    baseline_record = _record()
    baseline, _, _, _ = _read(monkeypatch, _snapshot([baseline_record]))
    repeated, _, _, _ = _read(monkeypatch, _snapshot([baseline_record]))
    assert baseline["snapshot_sha256"] == repeated["snapshot_sha256"]

    mutations = [
        {"source_id": "raw-changed"},
        {"publish_datetime": "2026-03-05"},
        {"captured_at": "2026-03-21T12:00:00Z"},
        {"sentiment": "negative"},
        {"risk_level": "high"},
    ]
    for mutation in mutations:
        changed = deepcopy(baseline_record)
        changed.update(mutation)
        result, _, _, _ = _read(monkeypatch, _snapshot([changed]))
        assert result["snapshot_sha256"] != baseline["snapshot_sha256"]


@pytest.fixture
def signed_scope_db(tmp_path, monkeypatch):
    path = tmp_path / "cth-temporal-signed-scope.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"cth-temporal-test": "ephemeral-disposable-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "cth-temporal-test")
    with sqlite3.connect(path) as connection:
        evidence_store.ensure_evidence_schema(connection)
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(app_evidence_records)")
        }
        for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                connection.execute(
                    f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}"
                )
        canonical_data.ensure_canonical_table(connection=connection)
    return path


def _persist_signed_record(
    connection, *, source_id, subject_id, publish_datetime,
    sentiment="negative", risk_level="critical",
):
    evidence_id = evidence_store.record_evidence(
        source="public_http", project="LUMENIS", product="CTH",
        feature_id="CTH_TEMPORAL_METRICS_TEST", test_name="source_scope",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id="cth", subject_id=subject_id,
    )
    record = CanonicalRecord(
        canonical_id=f"can-{source_id}", product_id="CTH", domain_id="cth",
        subject_id=subject_id, scope_status="VERIFIED",
        scope_evidence_ref=str(evidence_id), source_id=source_id,
        source_type="note", title="private integration title",
        content="private integration body", publish_datetime=publish_datetime,
        captured_at="2026-03-20T12:00:00Z", sentiment=sentiment,
        risk_level=risk_level, quality_status="ok",
    )
    persist_canonical(connection, record)
    connection.commit()
    return evidence_id


def test_real_scoped_canonical_read_uses_signed_scope_evidence(signed_scope_db):
    period_day = (date.today() - timedelta(days=1)).isoformat()
    with sqlite3.connect(signed_scope_db) as connection:
        evidence_a = _persist_signed_record(
            connection, source_id="raw-cth-temporal-a", subject_id="SUBJ-A",
            publish_datetime=period_day, sentiment="negative", risk_level="critical",
        )
        _persist_signed_record(
            connection, source_id="raw-cth-temporal-b", subject_id="SUBJ-B",
            publish_datetime=period_day, sentiment="positive", risk_level="high",
        )
        result = read_cth_temporal_metrics(
            connection, start_date=period_day, end_date=period_day,
            authorize=lambda: _binding("FOCUS", "SUBJ-A"),
        )

    assert result["state"] == "ready"
    assert result["read"] == {
        "candidate_count": 1, "scanned_count": 1, "rejected_count": 0,
        "returned_count": 1, "limit": 100, "truncated": False,
    }
    assert result["days"][0]["total"]["value"] == 1
    assert result["days"][0]["negative"]["value"] == 1
    assert result["days"][0]["high"]["value"] == 0
    assert result["days"][0]["critical"]["value"] == 1
    contribution = result["contributions"][0]
    assert contribution["source_id"] == "raw-cth-temporal-a"
    assert contribution["publication_day"] == period_day
    assert contribution["scope_evidence"]["id"] == evidence_a
    assert contribution["scope_evidence"]["integrity"]["verified"] is True
    assert contribution["scope_evidence"]["integrity"]["lineage_verified"] is True
    assert contribution["scope_evidence"]["stored_scope"]["subject_id"] == "SUBJ-A"
    assert "title" not in contribution and "content" not in contribution
    assert result["classification_provenance"] == (
        "stored_canonical_labels; analysis_correctness_not_verified"
    )
    assert result["coverage"] == "NOT_VERIFIED"
    assert result["source_freshness"] == "UNKNOWN"
    assert result["recipe"] == "CTH_NATIVE_PUBLICATION_COUNTS_V1"
    assert result["metric_definitions"]["negative"] == (
        "FN-SENTIMENT-COUNT:v1 negative stored labels"
    )
