"""Reporting-owner job, artifact reopen, recovery and Evaluation integration."""
import json
import sqlite3
import uuid

import pytest

import lumenis.shared.reporting.source_brief_job as jobs
from canonical_data import CanonicalRecord, ensure_canonical_table, persist_canonical
from lumenis.shared.database.business_schema import apply_business_schema
from lumenis.shared.evaluation.recorder import init_db
from lumenis.shared.evidence import store as evidence_store


@pytest.fixture
def job_db(tmp_path, monkeypatch):
    """Build canonical/Evidence/Report tables in an explicit disposable seed."""
    path = tmp_path / "source-brief-job.sqlite3"
    monkeypatch.setenv("ZBC_DB_PATH", str(path))
    monkeypatch.setenv(
        "LUMENIS_EVIDENCE_HMAC_KEY_RING",
        json.dumps({"job-test": "ephemeral-disposable-test-key"}),
    )
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "job-test")
    with sqlite3.connect(path) as conn:
        evidence_store.ensure_evidence_schema(conn)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
        ensure_canonical_table(connection=conn)
        apply_business_schema(conn)
        conn.commit()
    init_db()
    return path


def _source(conn, source_id="brief-job-source", subject="SUBJECT-A"):
    evidence_id = evidence_store.record_evidence(
        connection=conn, source="public_http", project="LUMENIS",
        product="CTH", feature_id="SOURCE_BRIEF_JOB_TEST", test_name="signed_source",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id="cth", subject_id=subject,
    )
    persist_canonical(conn, CanonicalRecord(
        canonical_id="canonical-" + source_id, product_id="CTH", domain_id="cth",
        subject_id=subject, scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
        source_id=source_id, external_id=source_id, source_type="web_mention",
        source_platform="web", title="Real public source", url="https://source.example/item/1",
        content="Private source body is not part of the brief", captured_at="2026-09-30T12:00:00Z",
    ))


def _request(con, job_id=None, **overrides):
    args = {
        "product_id": "CTH", "global_scope": False, "entity_label": "Registered Subject A",
        "subject_id": "SUBJECT-A", "actor_id": "workspace:local",
        "permission_audit_ref": "permission-audit:read-source-brief",
        "trace_id": "trace-source-brief-test", "job_id": job_id or "job-" + uuid.uuid4().hex,
    }
    args.update(overrides)
    return jobs.create_source_brief_job(con, **args)


def test_job_persists_reopens_exact_scope_and_records_real_artifact_evaluation(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        _source(conn)
        conn.commit()
        result = _request(conn, job_id="job-brief-00000001")
        retried = _request(conn, job_id="job-brief-00000001")

    assert result["job_state"] == "completed"
    assert result["artifact_outcome"]["state"] == "persisted_and_reopened_verified"
    assert result["artifact_outcome"]["source_count"] == 1
    assert result["review_status"] == "HUMAN_PENDING"
    assert result["multimodal"] == {
        "state": "unavailable", "reason": "MULTIMODAL_ANALYZER_OWNER_NOT_BOUND", "real_input_bound": False,
    }
    assert {row["metric_name"]: row["status"] for row in result["evaluation"]["records"]} == {
        "report_artifact_integrity": "pass",
        "source_evidence_grounding": "pass",
        "multimodal_analysis_integrity": "unknown",
    }

    scope = result["source_brief"]["scope"]
    reopened = jobs.get_source_brief_job(
        result["job_id"], actor_id="workspace:local", expected_scope=scope,
    )
    assert reopened["artifact_outcome"] == result["artifact_outcome"]
    assert reopened["evaluation"]["state"] == "recorded"
    assert reopened["evaluation"]["records"] == result["evaluation"]["records"]
    assert retried == result
    with sqlite3.connect(job_db) as conn:
        row = conn.execute(
            "SELECT total_notes,positive_count,total_likes,source_snapshot FROM daily_reports WHERE report_id=?",
            (result["job_id"],),
        ).fetchone()
    assert row[0] == 1
    assert row[1] is None and row[2] is None
    snapshot = json.loads(row[3])
    assert snapshot["permission_audit_ref"] == "permission-audit:read-source-brief"
    assert snapshot["source_brief"]["records"][0]["scope_evidence_ref"]


def test_reopened_job_is_actor_and_scope_bound(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn, job_id="job-brief-00000002")
    with pytest.raises(PermissionError, match="ACTOR_MISMATCH"):
        jobs.get_source_brief_job(result["job_id"], actor_id="workspace:other")
    wrong_scope = dict(result["source_brief"]["scope"], entity_label="Other Subject")
    with pytest.raises(PermissionError, match="SCOPE_MISMATCH"):
        jobs.get_source_brief_job(
            result["job_id"], actor_id="workspace:local", expected_scope=wrong_scope,
        )
    assert result["artifact_outcome"]["source_count"] == 0
    grounding = next(
        record for record in result["evaluation"]["records"]
        if record["metric_name"] == "source_evidence_grounding"
    )
    assert grounding["metric_value"] is None and grounding["status"] == "unknown"


def test_distinct_jobs_in_same_scope_and_day_do_not_replace_each_other(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        first = _request(conn, job_id="job-brief-same-scope-0001")
        second = _request(conn, job_id="job-brief-same-scope-0002")
    assert first["source_brief"]["scope"] == second["source_brief"]["scope"]
    assert jobs.get_source_brief_job(first["job_id"], actor_id="workspace:local")["job_id"] == first["job_id"]
    assert jobs.get_source_brief_job(second["job_id"], actor_id="workspace:local")["job_id"] == second["job_id"]
    with sqlite3.connect(job_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_reports WHERE report_id IN (?, ?)",
            (first["job_id"], second["job_id"]),
        ).fetchone()[0] == 2


def test_retry_recovers_evaluation_after_artifact_was_already_persisted(job_db, monkeypatch):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        _source(conn)
        conn.commit()
        original = jobs.record_evaluation
        monkeypatch.setattr(jobs, "record_evaluation", lambda **kwargs: (_ for _ in ()).throw(OSError("simulated")))
        with pytest.raises(OSError, match="simulated"):
            _request(conn, job_id="job-brief-00000003")
        monkeypatch.setattr(jobs, "record_evaluation", original)
        recovered = _request(conn, job_id="job-brief-00000003")

    assert recovered["artifact_outcome"]["state"] == "persisted_and_reopened_verified"
    assert recovered["evaluation"]["state"] == "recorded"
    assert jobs.get_source_brief_job(
        recovered["job_id"], actor_id="workspace:local",
    )["evaluation"]["state"] == "recorded"
    with sqlite3.connect(job_db) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM daily_reports WHERE report_id='job-brief-00000003'"
        ).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 3


def test_report_tampering_is_rejected_on_reopen(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn, job_id="job-brief-00000004")
    with sqlite3.connect(job_db) as conn:
        conn.execute("UPDATE daily_reports SET summary='tampered' WHERE report_id=?", (result["job_id"],))
        conn.commit()
    with pytest.raises(RuntimeError, match="ARTIFACT_HASH_MISMATCH"):
        jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")


def test_unverified_media_failure_cannot_assert_bound_input(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn, multimodal_result={
            "state": "error", "reason": "MODEL_UNAVAILABLE",
            "real_input_bound": True, "input_content_sha256": "a" * 64,
        })
    assert result['multimodal']['real_input_bound'] is False
    assert 'input_content_sha256' not in result['multimodal']


def test_quality_review_returns_with_report_without_promoting_human_acceptance(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn)
    artifact = result["artifact_outcome"]
    review = jobs.record_evaluation(
        dimension="report", metric_name="business_usefulness", metric_value=None,
        pass_threshold=1.0, warn_threshold=0.8, source="engineering_runtime_review",
        evidence_ref=f"daily_reports:{result['job_id']}:{artifact['artifact_hash']}",
        metadata={"job_id": result["job_id"], "artifact_hash": artifact["artifact_hash"],
                  "scope": result["source_brief"]["scope"],
                  "observations": ["Claim requires source review."],
                  "required_followup": "Check before client delivery.",
                  "evaluator": "Engineering inspection", "review_status": "PASS",
                  "private_diagnostic": "Do not expose arbitrary metadata"},
    )
    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")
    quality = reopened["evaluation"]["quality_review"]
    assert quality["state"] == "recorded" and len(quality["records"]) == 1
    assert quality["records"][0]["evaluation_id"] == review.evaluation_id
    assert quality["records"][0]["status"] == "unknown"
    assert quality["records"][0]["metric_value"] is None
    assert quality["records"][0]["observations"] == ["Claim requires source review."]
    assert quality["review_status"] == reopened["review_status"] == "HUMAN_PENDING"
    assert "private_diagnostic" not in json.dumps(quality)
    assert reopened["artifact_outcome"] == artifact
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        assert _request(conn, job_id=result["job_id"]) == reopened


@pytest.mark.parametrize("mismatch", ["job_id", "artifact_hash", "scope", "actor_id", "evidence_ref", "missing_actor"])
def test_quality_review_excludes_unbound_or_other_actor_feedback(job_db, mismatch):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn)
    metadata = {"job_id": result["job_id"],
                "artifact_hash": result["artifact_outcome"]["artifact_hash"],
                "scope": result["source_brief"]["scope"], "actor_id": "workspace:local"}
    ref = f"daily_reports:{result['job_id']}:{metadata['artifact_hash']}"
    if mismatch == "evidence_ref":
        ref = "app_evidence_records:foreign"
    elif mismatch == "missing_actor":
        metadata.pop("actor_id")
    else:
        metadata[mismatch] = "other"
    jobs.record_evaluation(
        dimension="report", metric_name="business_usefulness", metric_value=1.0,
        pass_threshold=1.0, warn_threshold=0.8, source="user_review",
        evidence_ref=ref, metadata=metadata,
    )
    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")
    assert reopened["evaluation"]["quality_review"]["state"] == "not_recorded"
    assert reopened["evaluation"]["quality_review"]["records"] == []


def test_malformed_legacy_evaluation_metadata_does_not_break_report_reopen(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn)
    review = jobs.record_evaluation(
        dimension="report", metric_name="legacy", metric_value=None,
        pass_threshold=1, warn_threshold=0.8,
    )
    with sqlite3.connect(job_db) as conn:
        conn.execute("UPDATE evaluation_records SET metadata='broken-json' WHERE evaluation_id=?",
                     (review.evaluation_id,))
        conn.commit()
    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")
    assert reopened["evaluation"]["quality_review"]["state"] == "not_recorded"
