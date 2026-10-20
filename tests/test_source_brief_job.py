"""Reporting-owner job, artifact reopen, recovery and Evaluation integration."""
import json
import sqlite3
import uuid

import pytest

import canonical_data
import lumenis.shared.reporting.source_brief_job as jobs
from lumenis.shared.reporting import business_brief
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


def _source(conn, source_id="brief-job-source", subject="SUBJECT-A", *, source_type="web_mention"):
    evidence_id = evidence_store.record_evidence(
        connection=conn, source="public_http", project="LUMENIS",
        product="CTH", feature_id="SOURCE_BRIEF_JOB_TEST", test_name="signed_source",
        result="PASS", status="verified", inputs={"source_ids": [source_id]},
        outputs={"source_read": True}, domain_id="cth", subject_id=subject,
    )
    persist_canonical(conn, CanonicalRecord(
        canonical_id="canonical-" + source_id, product_id="CTH", domain_id="cth",
        subject_id=subject, scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
        source_id=source_id, external_id=source_id, source_type=source_type,
        source_platform="web", title="Real public source", url="https://source.example/item/1",
        content="Private source body is not part of the brief", captured_at="2026-09-30T12:00:00Z",
    ))
    return evidence_id


def _document_row(conn, source_id, evidence_id, subject="SUBJECT-A"):
    persist_canonical(conn, CanonicalRecord(
        canonical_id="canonical-row-" + source_id, product_id="CTH", domain_id="cth",
        subject_id=subject, scope_status="VERIFIED", scope_evidence_ref=str(evidence_id),
        source_id=source_id, external_id=source_id + ":row:1", source_type="document_row",
        source_platform="approved_research_document", title="Selected row",
        url="https://source.example/item/1", content="Selected row body",
        captured_at="2026-09-30T12:00:00Z",
        provenance=json.dumps({
            "schema": "document-row-projection/v1",
            "source_locator": {"unit": "parsed_table_row", "table_index": 0, "row_index": 1},
            "source_row_sha256": "a" * 64,
        }),
        raw_ref=json.dumps({"source_id": source_id, "evidence_id": evidence_id}),
    ))


def _mock_report_read_permission(monkeypatch):
    from lumenis.shared.reporting import saved_work

    monkeypatch.setattr(
        saved_work, "authorize",
        lambda actor, scope, *, action, connection=None: {
            **scope, "principal_kind": "local_workspace", "principal_ref": "workspace:local",
        },
    )


def _mock_research(monkeypatch):
    calls = []

    def run(_system, user, **_kwargs):
        payload = json.loads(user)
        calls.append(payload)
        source_id = payload["sources"][0]["source_id"]
        result = {
            "source_observations": [{"source_id": source_id, "excerpt_index": 0}],
            "interpretations": [{
                "text": "单条来源只能形成待验证假设。", "source_ids": [source_id],
            }],
            "proposed_actions": [{
                "action": "将这条来源作为后续内容讨论材料。",
                "reason": "当前只有这一项已绑定来源。",
                "check": "由团队复核来源后再决定是否采用。",
                "source_ids": [source_id],
                "pilot": {
                    "audience": "建议邀请少量目标受众参与复核。",
                    "procedure": "先展示来源，再收集参与者的独立理解。",
                    "measure": "记录理解是否与预期表达一致。",
                    "continue_if": "反馈一致时再讨论下一步。",
                    "stop_if": "反馈不一致或不足时先补充材料。",
                },
            }],
            "unknowns": ["实际反馈、权利与执行资源仍需确认。"],
        }
        return json.dumps(result, ensure_ascii=False), "ollama", {"model": "isolated-fake"}

    monkeypatch.setattr(business_brief, "_request_business_inference", run)
    return calls


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


def test_reopen_downgrades_legacy_media_provider_without_changing_saved_snapshot(job_db, monkeypatch):
    old_media = {
        "state": "complete", "real_input_bound": True,
        "input_content_sha256": "a" * 64, "analysis_input_sha256": "b" * 64,
        "image_preprocessing": "unchanged", "analysis_execution_ref": "legacy-execution-1",
        "evidence_ref": "app_evidence_records:123", "result_ref": "app_evidence_records:123:outputs.analysis_text",
        "analysis_text": '{"business_implications":[],"unverifiable":["legacy"],"visible_facts":["legacy"]}',
        "provider": "ollama", "model": "historical-local-model", "review_status": "HUMAN_PENDING",
    }
    monkeypatch.setattr(jobs, "_multimodal_snapshot", lambda *_args, **_kwargs: old_media)
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        _source(conn)
        conn.commit()
        result = _request(conn, job_id="job-legacy-media-0001", multimodal_result={"state": "complete"})
    with sqlite3.connect(job_db) as conn:
        row = conn.execute(
            "SELECT * FROM daily_reports WHERE report_id=?", (result["job_id"],),
        ).fetchone()
        column_names = [item[1] for item in conn.execute("PRAGMA table_info(daily_reports)")]
        stored = dict(zip(column_names, row))
        source_snapshot, artifact_hash = stored["source_snapshot"], stored["artifact_hash"]
    with sqlite3.connect(job_db) as conn:
        prior_evaluation = conn.execute(
            "SELECT metric_value, status FROM evaluation_records WHERE evaluation_id=?",
            (jobs._evaluation_ids(result["job_id"])["multimodal_analysis_integrity"],),
        ).fetchone()
    assert prior_evaluation == (1.0, "pass")

    # Other current readers must downgrade the historical inference even before
    # the SourceBrief is reopened; the original database receipt stays intact.
    from flask import Flask
    import system_ai_data_api
    from lumenis.shared.evaluation.recorder import get_evaluation_records, get_evaluation_summary

    summary = get_evaluation_summary(db_path=str(job_db))
    assert summary["counts"]["unknown"] == 1
    assert summary["counts"]["pass"] == 2
    unknown = get_evaluation_records(status="unknown", db_path=str(job_db))
    assert [item["metric_name"] for item in unknown] == ["multimodal_analysis_integrity"]
    assert unknown[0]["inference_status"] == "HISTORICAL_NOT_REVERIFIED"
    passed = get_evaluation_records(status="pass", db_path=str(job_db))
    assert len(passed) == 2
    app = Flask("evaluation-assurance")
    app.register_blueprint(system_ai_data_api.system_ai_bp)
    api_result = app.test_client().get("/api/ai/evaluations").get_json()
    assert api_result["stats"] == {"pass": 2, "unknown": 1}
    api_media = next(item for item in api_result["items"] if item["metric_name"] == "multimodal_analysis_integrity")
    assert api_media["decision"] == "unknown"
    assert api_media["inference_status"] == "HISTORICAL_NOT_REVERIFIED"

    historical_readback = {
        **old_media, "state": "historical_not_reverified", "real_input_bound": True,
        "source_hash_bound": True, "inference_status": "HISTORICAL_NOT_REVERIFIED",
        "current_inference_verified": False, "historical_provider": True,
    }
    monkeypatch.setattr(jobs, "_multimodal_snapshot", lambda *_args, **_kwargs: historical_readback)
    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")

    assert reopened["multimodal"] == historical_readback
    media_evaluation = next(
        item for item in reopened["evaluation"]["records"]
        if item["metric_name"] == "multimodal_analysis_integrity"
    )
    assert media_evaluation["metric_value"] is None
    assert media_evaluation["status"] == "unknown"
    assert media_evaluation["historical_record_status"] == "pass"
    assert media_evaluation["current_inference_verified"] is False
    with sqlite3.connect(job_db) as conn:
        persisted = conn.execute(
            "SELECT source_snapshot, artifact_hash FROM daily_reports WHERE report_id=?",
            (result["job_id"],),
        ).fetchone()
        evaluation_after = conn.execute(
            "SELECT metric_value, status FROM evaluation_records WHERE evaluation_id=?",
            (jobs._evaluation_ids(result["job_id"])["multimodal_analysis_integrity"],),
        ).fetchone()
    assert persisted == (source_snapshot, artifact_hash)
    assert evaluation_after == prior_evaluation


def test_document_and_selected_row_share_one_source_brief_record_and_reopen_by_canonical_id(job_db, monkeypatch):
    source_id = "brief-document-with-row"
    research_calls = _mock_research(monkeypatch)
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        evidence_id = _source(conn, source_id, source_type="document")
        _document_row(conn, source_id, evidence_id)
        conn.commit()
        result = _request(
            conn, job_id="job-document-row-0001", source_ids=[source_id], limit=1,
            business_question="What should be checked before using this source?",
        )

    records = result["source_brief"]["records"]
    assert result["job_state"] == "completed"
    assert len(records) == 1
    assert records[0]["source_id"] == source_id
    assert records[0]["canonical_id"] == "canonical-" + source_id
    assert records[0]["source_type"] == "document"
    assert records[0]["scope_evidence_ref"] == str(evidence_id)
    assert result["source_brief"]["sample"]["returned_verified_count"] == 1
    assert result["source_brief"]["sample"]["candidate_count"] == 1
    assert result["business_analysis"]["state"] == "unavailable"
    assert result["business_analysis"]["reason"] == "BUSINESS_BRIEF_RETIRED_OR_UNAVAILABLE_PROVIDER"
    assert len(research_calls) == 1
    assert research_calls[0]["sources"][0]["source_id"] == source_id
    assert "Private source body" in "".join(research_calls[0]["sources"][0]["excerpts"])
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        canonical_rows = canonical_data.list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJECT-A", source_ids=[source_id], limit=10,
        )
        source_rows = canonical_data.list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJECT-A", source_ids=[source_id],
            limit=1, source_level=True,
        )
    assert len(canonical_rows["records"]) == 2
    assert canonical_rows["candidate_count"] == 2
    assert len(source_rows["records"]) == 1
    assert source_rows["candidate_count"] == 1 and source_rows["truncated"] is False

    _mock_report_read_permission(monkeypatch)
    reopened = jobs.get_source_brief_job(
        result["job_id"], actor_id="workspace:local", actor=object(),
    )
    assert reopened["source_brief"]["records"] == records
    assert reopened["artifact_outcome"] == result["artifact_outcome"]


def test_legacy_report_resolves_document_by_type_and_evidence_after_row_projection(job_db, monkeypatch):
    source_id = "legacy-document-with-row"
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        evidence_id = _source(conn, source_id, source_type="document")
        conn.commit()
        result = _request(conn, job_id="job-legacy-document-0001", source_ids=[source_id], limit=1)

    with sqlite3.connect(job_db) as conn:
        row = conn.execute(
            "SELECT report_type,report_date,total_notes,summary,source_snapshot "
            "FROM daily_reports WHERE report_id=?", (result["job_id"],),
        ).fetchone()
        snapshot = json.loads(row[4])
        snapshot["source_brief"]["records"][0].pop("canonical_id")
        source_snapshot = jobs._json(snapshot)
        artifact_hash = jobs._hash_artifact(
            report_id=result["job_id"], report_type=row[0], report_date=row[1],
            total_notes=row[2], summary=row[3], source_snapshot=source_snapshot,
        )
        conn.execute(
            "UPDATE daily_reports SET source_snapshot=?,artifact_hash=? WHERE report_id=?",
            (source_snapshot, artifact_hash, result["job_id"]),
        )
        for evaluation_id in jobs._evaluation_ids(result["job_id"]).values():
            evaluation = conn.execute(
                "SELECT metadata FROM evaluation_records WHERE evaluation_id=?", (evaluation_id,),
            ).fetchone()
            metadata = json.loads(evaluation[0])
            metadata["artifact_hash"] = artifact_hash
            conn.execute(
                "UPDATE evaluation_records SET evidence_ref=?,metadata=? WHERE evaluation_id=?",
                (f"daily_reports:{result['job_id']}:{artifact_hash}", json.dumps(metadata, ensure_ascii=False), evaluation_id),
            )
        _document_row(conn, source_id, evidence_id)
        conn.commit()

    _mock_report_read_permission(monkeypatch)
    reopened = jobs.get_source_brief_job(
        result["job_id"], actor_id="workspace:local", actor=object(),
    )
    assert reopened["source_brief"]["records"][0]["source_id"] == source_id
    assert "canonical_id" not in reopened["source_brief"]["records"][0]
    assert reopened["artifact_outcome"]["artifact_hash"] == artifact_hash
    assert reopened["artifact_outcome"]["source_count"] == result["artifact_outcome"]["source_count"]


def test_mismatched_document_row_evidence_is_not_hidden_by_source_level_read(job_db):
    source_id = "brief-document-row-evidence-conflict"
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        evidence_id = _source(conn, source_id, source_type="document")
        _document_row(conn, source_id, evidence_id)
        conn.execute(
            "UPDATE canonical_data SET scope_evidence_ref='foreign-evidence' "
            "WHERE canonical_id=?", ("canonical-row-" + source_id,),
        )
        conn.commit()
        source_rows = canonical_data.list_scoped_canonical(
            conn, product_id="CTH", subject_id="SUBJECT-A", source_ids=[source_id],
            limit=1, source_level=True,
        )
        assert source_rows["candidate_count"] == 2
        assert source_rows["truncated"] is True
        with pytest.raises(PermissionError, match="SOURCE_BRIEF_SELECTED_SOURCE_UNAVAILABLE"):
            _request(conn, job_id="job-document-row-conflict-001", source_ids=[source_id], limit=1)


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


@pytest.mark.parametrize("field,value", [
    ("dimension", "data"),
    ("metric_name", "foreign_metric"),
    ("metric_value", 0.5),
    ("threshold", "{}"),
    ("status", "fail"),
    ("source", "foreign_source"),
    ("evidence_ref", "foreign_artifact"),
    ("metadata", "{}"),
    ("evaluated_at", ""),
    ("evaluated_at", "not-a-time"),
])
def test_reopen_omits_non_equivalent_evaluation_and_keeps_it_pending(job_db, field, value):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn)
    evaluation_id = jobs._evaluation_ids(result["job_id"])["report_artifact_integrity"]
    with sqlite3.connect(job_db) as conn:
        conn.execute(f"UPDATE evaluation_records SET {field}=? WHERE evaluation_id=?", (value, evaluation_id))
        conn.commit()

    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")
    assert reopened["evaluation"]["state"] == "pending_recovery"
    assert all(record["metric_name"] != "report_artifact_integrity"
               for record in reopened["evaluation"]["records"])


def test_explicit_resume_keeps_invalid_timestamp_pending(job_db):
    job_id = "job-brief-resume-invalid-time"
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn, job_id=job_id)
    evaluation_id = jobs._evaluation_ids(job_id)["report_artifact_integrity"]
    with sqlite3.connect(job_db) as conn:
        conn.execute("UPDATE evaluation_records SET evaluated_at='not-a-time' WHERE evaluation_id=?",
                     (evaluation_id,))
        conn.commit()
        conn.row_factory = sqlite3.Row
        resumed = _request(conn, job_id=job_id)

    assert resumed["evaluation"]["state"] == "pending_recovery"
    assert len(resumed["evaluation"]["records"]) == 2
    assert result["evaluation"]["state"] == "recorded"


def test_missing_evaluation_readback_stays_pending_until_explicit_recovery(job_db):
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        result = _request(conn, job_id="job-brief-readback-recovery-01")
    evaluation_id = jobs._evaluation_ids(result["job_id"])["source_evidence_grounding"]
    with sqlite3.connect(job_db) as conn:
        conn.execute("DELETE FROM evaluation_records WHERE evaluation_id=?", (evaluation_id,))
        conn.commit()

    reopened = jobs.get_source_brief_job(result["job_id"], actor_id="workspace:local")
    assert reopened["evaluation"]["state"] == "pending_recovery"
    assert len(reopened["evaluation"]["records"]) == 2
    with sqlite3.connect(job_db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM evaluation_records").fetchone()[0] == 2
        conn.row_factory = sqlite3.Row
        recovered = _request(conn, job_id=result["job_id"])
        assert recovered["evaluation"]["state"] == "recorded"
        assert len(recovered["evaluation"]["records"]) == 3
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
