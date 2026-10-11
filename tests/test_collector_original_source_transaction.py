from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path

import pytest

from tests.test_collector_transaction_truth import REGISTERED_NAME


NATIVE_ID = "1987654321098765432"
SOURCE_URL = f"https://x.com/fixture-author/status/{NATIVE_ID}"
CAPTURED_AT = "2026-10-08T03:04:05"
BODY = "Registered Harbor Venue Holdings 的广州太古汇周末活动很有趣，咖啡 🍵。\n第二行包含更多内容。"
QUOTE = "广州太古汇"
BASE_RAW_REF_KEYS = {"table", "note_id", "id"}


@pytest.fixture
def native_case(collector_case, tmp_path, monkeypatch):
    """Bind Shared Artifacts to the existing fixture's disposable v19 DB."""
    from lumenis.shared.database import repository

    artifact_root = tmp_path / "artifacts"
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(artifact_root))
    db_repository = repository.DatabaseRepository(str(collector_case["db_path"]))
    monkeypatch.setattr(repository, "_default_repository", db_repository)
    import shared_artifacts

    shared_artifacts.ensure_artifact_table()
    artifact_root.mkdir(parents=True, exist_ok=True)
    return {**collector_case, "artifact_root": artifact_root, "db_repository": db_repository}


def _native_capture(case, *, body=BODY, rights="public-reference-only"):
    parent_bytes = b"synthetic-x-native-response-v1"
    metrics = {
        name: {"value": value, "captured_at": CAPTURED_AT}
        for name, value in {
            "favorite_count": 12, "reply_count": 4, "retweet_count": 2,
            "bookmark_count": 1, "view_count": 400,
        }.items()
    }
    value = {
        "platform": "x", "native_id": NATIVE_ID,
        "stable_source_key": f"x:{NATIVE_ID}", "source_url": SOURCE_URL,
        "body": body, "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "source_lineage": [{
            "sha256": hashlib.sha256(parent_bytes).hexdigest(),
            "locator": f"fixture://x/{NATIVE_ID}/post-body",
        }],
        "capture_observation_native": CAPTURED_AT,
        "publication": {"published_at_utc": None, "native_literal": None},
        "publication_since_2026": None, "rights": rights,
        "claim_type": "source_statement", "body_state": "NATIVE_FULL_POST",
        "native_record": {
            "tweet_id": NATIVE_ID, "screen_name": "fixture-author",
            "author_numeric_id": "fixture-author-001",
            "title": f"{REGISTERED_NAME} public update", "metrics_observed": metrics,
        },
    }
    content = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    capture = case["surface"].NativePublicCapture(
        platform="x", content=content, sha256=hashlib.sha256(content).hexdigest()
    )
    return capture, value


def _collect(case, capture):
    surface = case["surface"]
    case["reset_rate_limit"]()
    surface._last_action["x"] = time.monotonic() - surface.MIN_INTERVAL_SECONDS - 1
    with case["client"].application.test_request_context(
        "/api/experience/cth/platform-collection/search",
        headers={**case["focus_headers"], "Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        actor = case["permission"].resolve_local_workspace_principal(
            module="collector", action="write"
        )
        assert actor is not None, "principal must be server-issued in a local request context"
        result = surface.collect_search(
            "x", SOURCE_URL, max_results=1, operator="human",
            scope=case["scope"], actor=actor, native_capture=capture,
        )
        assert case["fetches"] == [], "native capture must not invoke a network adapter"
        return result


def _approval_for_capture(case, capture):
    from lumenis.system.security import OperationType

    denied = _collect(case, capture)
    assert denied.get("status") == "APPROVAL_REQUIRED", denied
    resource = denied.get("approval_resource")
    assert isinstance(resource, str) and resource.startswith("collector-source-import:v1:")
    return case["gate"].grant_approval(
        OperationType.DATA_IMPORT.value, resource=resource,
        granted_by="isolated synthetic native source transaction test",
    )


def _approved_collect(case, capture):
    _approval_for_capture(case, capture)
    result = _collect(case, capture)
    assert result.get("ok") is True and result.get("status") == "SUCCESS", result
    return result


def _connect(case):
    connection = sqlite3.connect(str(case["db_path"]))
    connection.row_factory = sqlite3.Row
    return connection


def _evidence(case, ref):
    assert isinstance(ref, str) and ref.startswith("app_evidence_records:")
    evidence_id = int(ref.split(":", 1)[1])
    with _connect(case) as connection:
        row = connection.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        ).fetchone()
    assert row is not None
    item = dict(row)
    item["evidence_id"] = evidence_id
    item["metadata"] = json.loads(item["collection_metadata"])
    return item


def _artifact(case, artifact_id):
    with _connect(case) as connection:
        row = connection.execute(
            "SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=?", (artifact_id,)
        ).fetchone()
    assert row is not None
    item = dict(row)
    item["path"] = (case["artifact_root"] / item["relative_path"]).resolve()
    return item


def _source_canonical(case, source_id):
    with _connect(case) as connection:
        rows = connection.execute(
            "SELECT * FROM canonical_data WHERE source_table='notes' AND source_id=?",
            (str(source_id),),
        ).fetchall()
    assert len(rows) == 1, f"expected one note Canonical row, found {len(rows)}"
    item = dict(rows[0])
    item["raw_ref_value"] = json.loads(item["raw_ref"] or "{}")
    return item


def _snapshot(case):
    with _connect(case) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "notes", "canonical_data", "app_evidence_records",
                "platform_contents", "metric_snapshots",
            )
        }
        artifacts = connection.execute(
            "SELECT artifact_id,sha256,size_bytes,note_id,evidence_id FROM lumenis_shared_artifacts "
            "WHERE kind='collected_source' ORDER BY artifact_id"
        ).fetchall()
        notes = connection.execute(
            "SELECT note_id,content,publish_datetime,captured_at,scope_status,scope_evidence_ref "
            "FROM notes ORDER BY note_id"
        ).fetchall()
        canonical = connection.execute(
            "SELECT canonical_id,source_id,raw_ref,content,publish_datetime,captured_at,scope_status,"
            "scope_evidence_ref FROM canonical_data WHERE source_table='notes' ORDER BY source_id"
        ).fetchall()
        platform_contents = connection.execute(
            "SELECT platform,platform_content_id,title,content,view_count,raw_data,last_collected_at "
            "FROM platform_contents ORDER BY platform,platform_content_id"
        ).fetchall()
        metrics = connection.execute(
            "SELECT entity_type,entity_key,raw_json FROM metric_snapshots ORDER BY id"
        ).fetchall()
        source_evidence = connection.execute(
            "SELECT id,asset_id,content_hash FROM app_evidence_records "
            "WHERE source='collector' AND feature_id='COLLECTED_SOURCE' ORDER BY id"
        ).fetchall()
        documents = connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT'"
        ).fetchone()[0]
    return {
        "counts": counts, "artifacts": [tuple(row) for row in artifacts],
        "notes": [tuple(row) for row in notes],
        "canonical": [tuple(row) for row in canonical],
        "platform_contents": [tuple(row) for row in platform_contents],
        "metrics": [tuple(row) for row in metrics],
        "source_evidence": [tuple(row) for row in source_evidence],
        "document_evidence": documents,
    }


def _files(case):
    return sorted(case["artifact_root"].rglob("*")) if case["artifact_root"].exists() else []


def _quote(case, evidence_id, body, *, start=None, end=None):
    from lumenis.importer import documents

    start = body.index(QUOTE) if start is None else start
    end = start + len(QUOTE) if end is None else end
    with case["client"].application.test_request_context(
        "/api/experience/cth/reports",
        headers={**case["focus_headers"], "Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    ):
        actor = case["permission"].resolve_local_workspace_principal(
            module="collector", action="read"
        )
        assert actor is not None
        return documents.locate_quote(
            evidence_id, actor=actor, scope=case["scope"], start=start, end=end
        )


def test_native_original_is_exact_signed_source_with_unicode_body_locator(native_case):
    case = native_case
    capture, value = _native_capture(case)
    result = _approved_collect(case, capture)
    refs = result["native_original_refs"]
    original = refs["original_source"]
    assert refs["source_id"] == str(refs["canonical"]["source_id"])
    assert original["status"] == "SAVED" and original["source_signature_verified"] is True
    assert original["source_kind"] == "collected_source"
    assert original["rights"] == "public-reference-only"
    assert original["per_use_admission"] == {
        "DATA_IMPORT": "CURRENT_CALLER_APPROVED",
        "READ_ANALYZE_SAVE_EXPORT": "CHECK_EACH_CURRENT_USE", "MODEL_TRAIN": "NOT_GRANTED",
    }

    evidence = _evidence(case, original["source_evidence_ref"])
    artifact = _artifact(case, original["source_artifact_ref"])
    metadata = evidence["metadata"]
    assert evidence["source"] == "collector" and evidence["feature_id"] == "COLLECTED_SOURCE"
    assert evidence["asset_id"] == refs["source_id"]
    assert metadata["native_source_binding"]["source_id"] == refs["source_id"]
    assert metadata["native_source_binding"]["collection_evidence_ref"] == refs["evidence_ref"]
    assert metadata["native_claim_type"] == "source_statement"
    assert metadata["provenance"]["rights"] == value["rights"]
    assert metadata["provenance"]["captured_at"] == CAPTURED_AT
    assert metadata["provenance"]["published_at"] is None
    assert metadata["native_publication"] == value["publication"]
    assert metadata["parsed_text"] == value["body"]
    locator = {
        "unit": "native-post-body", "json_path": "$.body", "start": 0,
        "end": len(value["body"]), "offset_unit": "unicode-codepoint",
    }
    assert metadata["locators"] == [locator]
    assert artifact["kind"] == "collected_source"
    assert artifact["source_execution_id"] == artifact["note_id"] == refs["source_id"]
    assert artifact["evidence_id"] == str(evidence["evidence_id"])
    assert artifact["sha256"] == capture.sha256 and artifact["size_bytes"] == len(capture.content)
    assert artifact["path"].is_file() and artifact["path"].read_bytes() == capture.content

    with _connect(case) as connection:
        note = dict(connection.execute(
            "SELECT * FROM notes WHERE note_id=?", (refs["source_id"],)
        ).fetchone())
        assert connection.execute(
            "SELECT COUNT(*) FROM canonical_data WHERE source_table='notes' AND source_id=?",
            (refs["source_id"],),
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM canonical_data WHERE source_type='document' AND source_id=?",
            (refs["source_id"],),
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT'"
        ).fetchone()[0] == 0
    canonical = _source_canonical(case, refs["source_id"])
    assert note["note_id"] == canonical["source_id"] == refs["source_id"]
    assert note["content"] == canonical["content"] == value["body"]
    assert note["captured_at"] == canonical["captured_at"] == CAPTURED_AT
    assert note["publish_datetime"] in (None, "")
    assert canonical["publish_datetime"] in (None, "")
    raw_ref = canonical["raw_ref_value"]
    assert set(raw_ref) == BASE_RAW_REF_KEYS | {"content_evidence_ref"}
    assert raw_ref["table"] == "notes" and raw_ref["note_id"] == refs["source_id"]
    assert raw_ref["id"] == note["id"]
    assert raw_ref["content_evidence_ref"] == original["source_evidence_ref"]

    start = value["body"].index(QUOTE)
    assert len(value["body"].encode("utf-8")) > len(value["body"])
    quote = _quote(case, evidence["evidence_id"], value["body"], start=start)
    assert quote["citation"] == {
        "evidence_id": evidence["evidence_id"], "start": start,
        "end": start + len(QUOTE), "quote": QUOTE,
    }
    assert quote["source_id"] == refs["source_id"] and quote["rights"] == "public-reference-only"
    assert quote["published_at"] is None and quote["captured_at"] == CAPTURED_AT
    assert quote["locators"] == [locator]


def test_identical_capture_reuses_artifact_evidence_and_preserves_canonical_raw_ref(native_case):
    case = native_case
    capture, _ = _native_capture(case)
    first = _approved_collect(case, capture)
    first_refs = first["native_original_refs"]
    first_original = first_refs["original_source"]
    raw_ref = _source_canonical(case, first_refs["source_id"])["raw_ref_value"]
    assert raw_ref["content_evidence_ref"] == first_original["source_evidence_ref"]
    before = _snapshot(case)

    replay = _collect(case, capture)
    assert replay.get("ok") is True and replay.get("status") == "SUCCESS", replay
    replay_original = replay["native_original_refs"]["original_source"]
    assert replay_original["replayed"] is True
    assert replay_original["source_artifact_ref"] == first_original["source_artifact_ref"]
    assert replay_original["source_evidence_ref"] == first_original["source_evidence_ref"]
    assert _snapshot(case) == before
    assert _source_canonical(case, first_refs["source_id"])["raw_ref_value"] == raw_ref


def test_changed_bytes_create_distinct_original_while_retaining_one_note_canonical(native_case):
    case = native_case
    first_capture, first_value = _native_capture(case)
    first = _approved_collect(case, first_capture)
    first_refs = first["native_original_refs"]
    first_original = first_refs["original_source"]

    second_capture, second_value = _native_capture(case, body=BODY + "\n第二个合成原文版本。")
    _approval_for_capture(case, second_capture)
    second = _collect(case, second_capture)
    assert second.get("ok") is True and second.get("status") == "SUCCESS", second
    second_refs = second["native_original_refs"]
    second_original = second_refs["original_source"]
    assert second_refs["source_id"] == first_refs["source_id"]
    assert second_original["source_artifact_ref"] != first_original["source_artifact_ref"]
    assert second_original["source_evidence_ref"] != first_original["source_evidence_ref"]
    assert second_original["source_fingerprint"] == second_capture.sha256
    assert _artifact(case, first_original["source_artifact_ref"])["path"].read_bytes() == first_capture.content
    assert _artifact(case, second_original["source_artifact_ref"])["path"].read_bytes() == second_capture.content
    assert _evidence(case, first_original["source_evidence_ref"])["metadata"]["parsed_text"] == first_value["body"]
    assert _evidence(case, second_original["source_evidence_ref"])["metadata"]["parsed_text"] == second_value["body"]
    canonical = _source_canonical(case, first_refs["source_id"])
    assert canonical["content"] == second_value["body"]
    raw_ref = canonical["raw_ref_value"]
    assert set(raw_ref) == BASE_RAW_REF_KEYS | {"content_evidence_ref"}
    assert raw_ref["table"] == "notes" and raw_ref["note_id"] == first_refs["source_id"]
    assert raw_ref["content_evidence_ref"] == second_original["source_evidence_ref"]
    snapshot = _snapshot(case)
    assert len(snapshot["canonical"]) == len(snapshot["artifacts"]) == len(snapshot["source_evidence"]) == 2
    assert snapshot["document_evidence"] == 0


def test_source_side_failure_rolls_back_savepoint_but_keeps_primary_intake(native_case, monkeypatch):
    case = native_case
    capture, value = _native_capture(case)
    _approval_for_capture(case, capture)
    writer = case["surface"]._persist_native_source_original
    observed = {"staged": False}

    def fail_after_stage(*args, **kwargs):
        result = writer(*args, **kwargs)
        paths = kwargs["staged_paths"]
        assert paths and all(path.is_file() for path in paths)
        observed["staged"] = True
        raise RuntimeError("synthetic post-stage source-side failure")

    monkeypatch.setattr(case["surface"], "_persist_native_source_original", fail_after_stage)
    result = _collect(case, capture)
    assert result.get("ok") is True and result.get("status") == "SUCCESS", result
    refs = result["native_original_refs"]
    unavailable = refs["original_source"]
    assert observed["staged"] is True
    assert unavailable["status"] == "UNAVAILABLE"
    assert unavailable["reason"] == "COLLECTED_SOURCE_WRITE_FAILED"
    assert unavailable["cleanup_status"] == "COMPLETE"
    assert refs["source_id"] == refs["canonical"]["source_id"]
    snapshot = _snapshot(case)
    assert snapshot["counts"]["notes"] == 1 and snapshot["counts"]["canonical_data"] == 1
    assert snapshot["source_evidence"] == [] and snapshot["artifacts"] == []
    assert snapshot["document_evidence"] == 0
    assert not any(path.is_file() for path in _files(case))
    canonical = _source_canonical(case, refs["source_id"])
    assert canonical["content"] == value["body"]
    assert set(canonical["raw_ref_value"]) == BASE_RAW_REF_KEYS
    assert canonical["raw_ref_value"]["table"] == "notes"
    assert canonical["raw_ref_value"]["note_id"] == refs["source_id"]


def test_final_approval_revocation_rolls_back_db_and_file_without_stale_refs(native_case, monkeypatch):
    case = native_case
    first_capture, first_value = _native_capture(case)
    first = _approved_collect(case, first_capture)
    first_refs = first["native_original_refs"]
    first_raw_ref = _source_canonical(case, first_refs["source_id"])["raw_ref_value"]

    second_capture, _ = _native_capture(case, body=BODY + "\n将被回滚的合成版本。")
    token = _approval_for_capture(case, second_capture)
    before = _snapshot(case)
    writer = case["surface"]._persist_native_source_original

    def revoke_after_stage(*args, **kwargs):
        result = writer(*args, **kwargs)
        assert kwargs["staged_paths"] and all(path.is_file() for path in kwargs["staged_paths"])
        assert case["gate"].revoke_approval(token) is True
        return result

    monkeypatch.setattr(case["surface"], "_persist_native_source_original", revoke_after_stage)
    denied = _collect(case, second_capture)
    assert denied.get("ok") is False and denied.get("status") == "APPROVAL_REQUIRED", denied
    assert "native_original_refs" not in denied
    assert _snapshot(case) == before
    canonical = _source_canonical(case, first_refs["source_id"])
    assert canonical["content"] == first_value["body"]
    assert canonical["raw_ref_value"] == first_raw_ref
    assert _artifact(case, first_refs["original_source"]["source_artifact_ref"])["path"].read_bytes() == first_capture.content
    assert len([path for path in _files(case) if path.is_file()]) == 1


def test_denial_before_exact_import_approval_creates_no_artifact(native_case):
    case = native_case
    capture, _ = _native_capture(case)
    result = _collect(case, capture)
    assert result.get("ok") is False and result.get("status") == "APPROVAL_REQUIRED", result
    assert "native_original_refs" not in result
    snapshot = _snapshot(case)
    assert snapshot["counts"]["notes"] == 0 and snapshot["counts"]["canonical_data"] == 0
    assert snapshot["source_evidence"] == [] and snapshot["artifacts"] == []
    assert snapshot["document_evidence"] == 0
    assert not any(path.is_file() for path in _files(case))


@pytest.mark.parametrize("rights", [{"status": "unknown", "grant": None}, None])
def test_unknown_or_null_rights_are_preserved_but_quote_reader_rejects_them(native_case, rights):
    from lumenis.shared.reporting.saved_work import SavedWorkError

    case = native_case
    capture, value = _native_capture(case, rights=rights)
    result = _approved_collect(case, capture)
    original = result["native_original_refs"]["original_source"]
    evidence = _evidence(case, original["source_evidence_ref"])
    assert original["rights"] == rights
    assert evidence["metadata"]["provenance"]["rights"] == rights
    assert json.loads(capture.content)["rights"] == rights
    assert _artifact(case, original["source_artifact_ref"])["path"].read_bytes() == capture.content
    with pytest.raises(SavedWorkError, match="WORK_SOURCE_RIGHTS_UNVERIFIED"):
        _quote(case, evidence["evidence_id"], value["body"])


def test_tampered_original_bytes_are_rejected_by_existing_quote_reader(native_case):
    from lumenis.shared.reporting.saved_work import SavedWorkError

    case = native_case
    capture, value = _native_capture(case)
    result = _approved_collect(case, capture)
    original = result["native_original_refs"]["original_source"]
    evidence = _evidence(case, original["source_evidence_ref"])
    _artifact(case, original["source_artifact_ref"])["path"].write_bytes(capture.content + b"tampered")
    with pytest.raises(SavedWorkError, match="DOCUMENT_SOURCE_ARTIFACT_INVALID"):
        _quote(case, evidence["evidence_id"], value["body"])
