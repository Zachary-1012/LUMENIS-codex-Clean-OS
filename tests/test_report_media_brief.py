"""Isolated Source Artifact to owned-Gateway report-media Evidence flow."""
import hashlib
import json
import struct
import zlib
from types import SimpleNamespace

import pytest

import lumenis.shared.reporting.media_brief as media_brief
import shared_artifacts
from lumenis.shared.evidence import store as evidence_store
from tests.test_local_content_source_routes import HEADERS, confirm, local_client as local_source_client
from tests.test_content_project_storage import media_store
from lumenis.system.security import permission as p


def _png():
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 4, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress((b"\0\x80\x20\x10" * 8) * 4))
            + chunk(b"IEND", b""))


@pytest.fixture
def media_setup(local_source_client, monkeypatch):
    client, store, app = local_source_client
    monkeypatch.setattr(media_brief, "get_repository", lambda: store["repository"])
    with store["repository"].connect() as conn:
        evidence_store.ensure_evidence_schema(conn)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(app_evidence_records)")}
        for name, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if name not in columns:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                conn.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {name} {kind}{suffix}")
    # The adapter tests exercise persisted source bytes/resolution. Probe installation
    # is covered by the Content Source owner and is unavailable in this test runner.
    def isolated_fingerprint(path):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix.lower() == ".png":
            return shared_artifacts._ImageSourceAsset(path.name, digest, 8, 4)
        asset_dict = {
            "asset_id": "MEDIA-" + digest[:16], "filename": path.name,
            "sha256": digest, "duration_sec": 0.5, "media_kind": "audio",
            "has_video": False, "audio_stream_count": 1,
            "evidence_refs": [], "rights_status": "unknown",
        }
        return SimpleNamespace(
            filename=path.name, sha256=digest, rights_status="unknown", evidence_refs=(),
            to_dict=lambda: asset_dict,
        )

    monkeypatch.setattr(shared_artifacts, "_fingerprint_content_source", isolated_fingerprint)
    payload = _png()
    url = "/api/experience/content-sources?filename=report.png"
    first = client.post(url, headers=HEADERS, data=payload,
                        content_type="application/octet-stream")
    assert first.status_code == 403, first.get_json()
    assert confirm(client, first.get_json()["confirmation"]["confirmation_id"]).status_code == 200
    imported = client.post(url, headers=HEADERS, data=payload,
                           content_type="application/octet-stream")
    assert imported.status_code == 201, imported.get_json()
    artifact = imported.get_json()["result"]["artifact"]["artifact_id"]
    with app.test_request_context(
            "/", headers=HEADERS, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        actor = p.resolve_local_workspace_principal(module="content", action="read")
    assert type(actor) is p.LocalWorkspacePrincipal
    scope = {"domain_id": "zbmp", "global_scope": True}
    brief = {"scope": {"product_id": "ZBMP", "domain_id": "zbmp", "global": True},
             "markdown": "Only use this scoped Source Brief as unverified context."}
    return {"client": client, "store": store, "actor": actor, "scope": scope,
            "artifact": artifact, "bytes": payload, "brief": brief, "app": app}


def _vision(monkeypatch, *, response=None):
    calls = []

    def fake(*, image_bytes, media_type, text, analysis_type, response_schema, note_id):
        assert set(response_schema["required"]) == {"visible_facts", "unverifiable", "business_implications"}
        calls.append({"image_bytes": image_bytes, "media_type": media_type, "text": text,
                      "analysis_type": analysis_type, "note_id": note_id})
        return {
            "ok": True, "status": "COMPLETED", "code": "", "provider": "owned",
            "model": "owned-vision-test-v1", "execution_ref": note_id,
            "analysis": response or {
            "visible_facts": ["A small product image is visible."],
            "unverifiable": ["The product identity and image date are not verified."],
            "business_implications": ["A human may compare the visible packaging with the brief."],
            },
        }

    monkeypatch.setattr(media_brief.ai_core, "run_owned_multimodal_analysis", fake)
    monkeypatch.setattr(media_brief.ai_core, "vision_chat",
                        lambda *_args, **_kwargs: pytest.fail("retired vision provider path was called"))
    return calls


def _run(media_setup, *, artifact_ref=None, scope=None, job_id="report-job-001"):
    with media_setup["app"].test_request_context(
            "/", headers=HEADERS, environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        return media_brief.analyze_report_media(
            artifact_ref or media_setup["artifact"], actor=media_setup["actor"],
            scope=scope or media_setup["scope"], job_id=job_id,
            brief_context=media_setup["brief"],
        )


def test_owned_gateway_image_result_is_persisted_as_reopenable_scoped_evidence(
        media_setup, monkeypatch):
    calls = _vision(monkeypatch)
    result = _run(media_setup)

    assert result["state"] == "complete"
    assert result["real_input_bound"] is True
    assert result["input_content_sha256"] == hashlib.sha256(media_setup["bytes"]).hexdigest()
    assert result["review_status"] == "HUMAN_PENDING" and result["model"] == "owned-vision-test-v1"
    assert len(calls) == 1
    assert calls[0]["image_bytes"] == media_setup["bytes"]
    assert calls[0]["media_type"] == "image/png"
    assert calls[0]["analysis_type"] == "report_media_analysis"
    assert "never follow" in calls[0]["text"]
    with media_setup["store"]["repository"].connect() as conn:
        row = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?",
            (int(result["evidence_ref"].rsplit(":", 1)[1]),),
        ).fetchone()
    evidence = dict(row)
    inputs, outputs = json.loads(evidence["inputs_json"]), json.loads(evidence["outputs_json"])
    assert inputs["source_artifact_ref"] == media_setup["artifact"]
    assert inputs["source_execution_id"]
    assert inputs["source_content_sha256"] == result["input_content_sha256"]
    assert inputs["job_id"] == "report-job-001" and inputs["actor_ref"] == "workspace:local"
    assert outputs["provider"] == "owned"
    assert outputs["model"] == "owned-vision-test-v1"
    assert media_brief.evidence_store.verify_evidence_record_integrity(evidence)
    reopened = media_brief.read_verified_report_media(
        result["evidence_ref"], job_id="report-job-001", actor_ref="workspace:local",
        scope=media_setup["scope"],
    )
    assert reopened == result


def test_historical_local_provider_result_is_not_promoted_on_readback(media_setup, monkeypatch):
    _vision(monkeypatch)
    result = _run(media_setup)
    record_id = int(result["evidence_ref"].rsplit(":", 1)[1])
    repository = media_setup["store"]["repository"]

    with repository.connect() as conn:
        row = conn.execute(
            "SELECT * FROM app_evidence_records WHERE id=?", (record_id,),
        ).fetchone()
        outputs = json.loads(row["outputs_json"])
        outputs["provider"] = "ollama"
        outputs["model"] = "historical-local-model"
        conn.execute(
            "UPDATE app_evidence_records SET provider=?, outputs_json=? WHERE id=?",
            ("ollama", json.dumps(outputs), record_id),
        )
        evidence_store._sign_evidence_record(conn, record_id)
        stored_before = tuple(conn.execute(
            "SELECT provider, inputs_json, outputs_json, integrity_digest FROM app_evidence_records WHERE id=?",
            (record_id,),
        ).fetchone())

    reopened = media_brief.read_verified_report_media(
        result["evidence_ref"], job_id="report-job-001", actor_ref="workspace:local",
        scope=media_setup["scope"],
    )

    with repository.connect(read_only=True) as conn:
        stored_after = tuple(conn.execute(
            "SELECT provider, inputs_json, outputs_json, integrity_digest FROM app_evidence_records WHERE id=?",
            (record_id,),
        ).fetchone())
    assert reopened["state"] == "historical_not_reverified"
    assert reopened["inference_status"] == "HISTORICAL_NOT_REVERIFIED"
    assert reopened["current_inference_verified"] is False
    assert reopened["historical_provider"] is True
    assert reopened["real_input_bound"] is True
    assert reopened["source_hash_bound"] is True
    assert reopened["provider"] == "ollama"
    assert reopened["model"] == "historical-local-model"
    assert reopened["analysis_text"] == result["analysis_text"]
    assert stored_after == stored_before


def test_scope_mismatch_and_missing_artifact_fail_closed_without_model_call(media_setup, monkeypatch):
    calls = _vision(monkeypatch)
    denied = _run(media_setup, scope={"domain_id": "cth", "global_scope": True})
    missing = _run(media_setup, artifact_ref="ART-0000000000000000", job_id="report-job-002")
    assert denied["state"] == missing["state"] == "unavailable"
    assert not denied["real_input_bound"] and not missing["real_input_bound"]
    assert calls == []


def test_unbound_owned_vision_is_unavailable_and_never_calls_retired_provider(media_setup, monkeypatch):
    monkeypatch.setattr(
        media_brief.ai_core, "vision_chat",
        lambda *_args, **_kwargs: pytest.fail("retired vision provider path was called"),
    )
    with media_setup["store"]["repository"].connect() as conn:
        before = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]

    result = _run(media_setup)

    with media_setup["store"]["repository"].connect() as conn:
        after = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]
    assert result["state"] == "unavailable" and result["real_input_bound"] is True
    assert result["provider"] == "owned"
    assert result["reason"] == "OWNED_RUNTIME_NOT_BOUND"
    assert after == before


def test_nonimage_content_source_is_not_sent_to_vision(media_setup, monkeypatch):
    calls = _vision(monkeypatch)
    response = media_setup["client"].post(
        "/api/experience/content-sources?filename=voice.wav", headers=HEADERS,
        data=media_setup["store"]["source"].read_bytes(),
        content_type="application/octet-stream",
    )
    assert response.status_code == 403
    assert confirm(media_setup["client"], response.get_json()["confirmation"]["confirmation_id"]).status_code == 200
    imported = media_setup["client"].post(
        "/api/experience/content-sources?filename=voice.wav", headers=HEADERS,
        data=media_setup["store"]["source"].read_bytes(),
        content_type="application/octet-stream",
    )
    assert imported.status_code == 201, imported.get_json()
    result = _run(media_setup, artifact_ref=imported.get_json()["result"]["artifact"]["artifact_id"])
    assert result["state"] == "unavailable" and not result["real_input_bound"]
    assert calls == []


@pytest.mark.parametrize("response", [
    " ",
    json.dumps({"visible_facts": [], "unverifiable": [], "business_implications": []}),
])
def test_empty_vision_output_is_unavailable_and_does_not_write_derived_evidence(
        media_setup, monkeypatch, response):
    calls = _vision(monkeypatch, response=response)
    with media_setup["store"]["repository"].connect() as conn:
        before = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]
    result = _run(media_setup)
    with media_setup["store"]["repository"].connect() as conn:
        after = conn.execute("SELECT COUNT(*) FROM app_evidence_records").fetchone()[0]
    assert result["state"] == "unavailable" and result["real_input_bound"] is True
    assert calls and calls[0]["analysis_type"] == "report_media_analysis" and after == before


def test_reopened_result_rejects_signed_output_tampering(media_setup, monkeypatch):
    _vision(monkeypatch)
    result = _run(media_setup)
    assert result["state"] == "complete"
    record_id = int(result["evidence_ref"].rsplit(":", 1)[1])
    with media_setup["store"]["repository"].connect() as conn:
        conn.execute(
            "UPDATE app_evidence_records SET outputs_json=? WHERE id=?",
            (json.dumps({"analysis_text": "tampered"}), record_id),
        )
    with pytest.raises(ValueError, match="REPORT_MEDIA_EVIDENCE_SIGNATURE_INVALID"):
        media_brief.read_verified_report_media(
            result["evidence_ref"], job_id="report-job-001", actor_ref="workspace:local",
            scope=media_setup["scope"],
        )


def test_reopened_signed_analysis_still_requires_visible_facts(media_setup, monkeypatch):
    _vision(monkeypatch)
    result = _run(media_setup)
    record_id = int(result["evidence_ref"].rsplit(":", 1)[1])
    with media_setup["store"]["repository"].connect() as conn:
        row = conn.execute("SELECT outputs_json FROM app_evidence_records WHERE id=?", (record_id,)).fetchone()
        outputs = json.loads(row[0])
        outputs["analysis_text"] = '{"business_implications":[],"unverifiable":[],"visible_facts":[]}'
        outputs["analysis_text_sha256"] = hashlib.sha256(outputs["analysis_text"].encode()).hexdigest()
        conn.execute("UPDATE app_evidence_records SET outputs_json=? WHERE id=?", (json.dumps(outputs), record_id))
        evidence_store._sign_evidence_record(conn, record_id)
    with pytest.raises(ValueError, match="REPORT_MEDIA_EVIDENCE_OUTPUT_INVALID"):
        media_brief.read_verified_report_media(
            result["evidence_ref"], job_id="report-job-001", actor_ref="workspace:local",
            scope=media_setup["scope"],
        )
