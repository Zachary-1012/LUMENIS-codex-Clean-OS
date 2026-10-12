"""Hermetic, self-authored retained-source fixtures for BusinessBrief tests.

These records are synthetic test inputs. They do not claim rights in, or facts
about, the example URL stored by the older Source Brief fixture, and they do
not execute the Importer or any model/provider.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from lumenis.shared.database import DatabaseRepository
from lumenis.shared.evidence import store as evidence_store
from lumenis.shared.reporting import saved_work
from lumenis.system.security import permission


_CAPTURED_AT = "2026-10-08T00:00:00Z"
_CONTENT_REF = re.compile(r"app_evidence_records:([1-9]\d*)\Z")
_SCOPE_KEYS = {"domain_id", "subject_id", "brand_focus_id", "global_scope"}


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _source_scope(row: Any) -> dict[str, Any]:
    domain = str(row["domain_id"] or "").strip().lower()
    if domain == "bmp":
        domain = "zbmp"
    subject_id = row["subject_id"] or None
    brand_focus_id = row["brand_focus_id"] or None
    global_scope = subject_id is None and brand_focus_id is None
    return {
        "domain_id": domain,
        "subject_id": subject_id,
        "brand_focus_id": brand_focus_id,
        "global_scope": global_scope,
    }


def _existing_content_evidence(connection, *, row, raw_ref, actor, context, body):
    reference = raw_ref.get("content_evidence_ref")
    match = _CONTENT_REF.fullmatch(reference) if isinstance(reference, str) else None
    if match is None:
        return None
    try:
        evidence = saved_work._verified_evidence(connection, int(match[1]), context, actor)
    except Exception:
        return None
    if (evidence.get("asset_id") != row["source_id"]
            or evidence.get("raw_content") != body
            or evidence.get("content_hash") != _sha(body.encode("utf-8"))):
        return None
    return reference


def _source_view(row, *, reference, body):
    return {
        "source_id": row["source_id"],
        "evidence_ref": str(row["scope_evidence_ref"] or ""),
        "content_evidence_ref": reference,
        "title": row["title"] or "Synthetic BusinessBrief fixture",
        "text": body,
        "truncated": False,
        "text_selection": {"start": 0, "end": len(body)},
        "body_sha256": _sha(body.encode("utf-8")),
        "publish_datetime": row["publish_datetime"],
        "captured_at": row["captured_at"],
        "source_platform": "UNKNOWN",
    }


def prepare_synthetic_content_sources(client, monkeypatch):
    """Bind each current nonempty test Canonical body to signed retained bytes.

    The scope receipt remains untouched. A separate content Evidence and
    Artifact are staged atomically in the disposable ``job_db`` database.
    """
    _api, app, db_path, _entry, gate = client
    db_path = Path(db_path).resolve()
    artifact_root = db_path.parent / "business-brief-test-artifacts"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(artifact_root))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    gate.grant_permission(permission.PermissionLevel.COMMIT)

    repository = DatabaseRepository(str(db_path))
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "get_repository", lambda: repository)
    shared_artifacts.ensure_artifact_table()

    created_paths = []
    source_views = {}
    request_context = app.test_request_context(
        "/", headers={"Host": "localhost"},
        environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
    )
    request_context.push()
    try:
        actor = permission.resolve_local_workspace_principal(module="reports", action="write")
        if type(actor) is not permission.LocalWorkspacePrincipal:
            raise AssertionError("the fixture requires the real loopback LocalWorkspacePrincipal")

        with repository.transaction() as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT canonical_id, source_id, product_id, domain_id, subject_id, brand_focus_id, "
                "scope_status, scope_evidence_ref, source_type, source_platform, title, content, "
                "publish_datetime, captured_at, raw_ref "
                "FROM canonical_data WHERE source_id IS NOT NULL AND source_type != 'document_row' "
                "ORDER BY source_id, canonical_id"
            ).fetchall()
            seen = set()
            for row in rows:
                source_id = row["source_id"]
                body = row["content"]
                if (not isinstance(source_id, str) or not source_id or source_id in seen
                        or not isinstance(body, str) or not body.strip()):
                    continue
                seen.add(source_id)
                try:
                    raw_ref = json.loads(row["raw_ref"] or "{}")
                except (TypeError, ValueError) as exc:
                    raise AssertionError("the test Canonical raw_ref must remain readable") from exc
                if not isinstance(raw_ref, dict):
                    raise AssertionError("the test Canonical raw_ref must be an object")

                scope = _source_scope(row)
                write_context = saved_work.authorize(
                    actor, scope, action="write", connection=connection,
                )
                current_ref = _existing_content_evidence(
                    connection, row=row, raw_ref=raw_ref, actor=actor,
                    context=write_context, body=body,
                )
                if current_ref is None:
                    raw = body.encode("utf-8")
                    body_hash = _sha(raw)
                    safe_source = re.sub(r"[^A-Za-z0-9_-]", "-", source_id)[:80]
                    origin_ref = "business-brief-test-" + (safe_source or "source")
                    source_provenance = {
                        "source_url": None,
                        "published_at": None,
                        "captured_at": row["captured_at"] or None,
                        "rights": "owner-approved",
                        "title": "Self-authored synthetic BusinessBrief source fixture",
                        "intended_use": "research_reference",
                        "source_origin": {"kind": "approved-file", "ref": origin_ref},
                        "content_origin": {"kind": "self-authored", "claim_type": "synthetic_sample"},
                    }
                    from lumenis.importer import documents
                    boundaries = documents.source_boundaries(source_provenance)
                    metadata = {
                        "context": write_context,
                        "source_url": None,
                        "source_fingerprint": body_hash,
                        "parsed_text_sha256": body_hash,
                        "provenance": source_provenance,
                        "locators": [],
                        "source_name": safe_source + ".txt",
                        "owner": {key: value for key, value in write_context.items()
                                  if key not in _SCOPE_KEYS},
                        "parser": {"contract": "synthetic-test-source/1"},
                        "parsed_text": body,
                        "capture_mode": "synthetic_test_fixture",
                        **boundaries,
                        "autonomous_collection": False,
                    }
                    product = "CTH" if write_context["domain_id"] == "cth" else "ZBMP"
                    artifact, path = saved_work._stage_bytes(
                        connection, raw=raw, context=write_context,
                        kind="imported_document_source", source_execution_id=source_id,
                        extension=".txt", media_type="text/plain",
                    )
                    created_paths.append(path)
                    metadata["source_artifact_ref"] = artifact["artifact_id"]
                    evidence_id = evidence_store.record_evidence(
                        connection=connection,
                        source="test_fixture", project="LUMENIS", product=product,
                        feature_id="BUSINESS_BRIEF_TEST_SOURCE_CONTENT", asset_id=source_id,
                        version="synthetic-test-source/1", env="staging",
                        test_name="business-brief-source:" + source_id,
                        capture_mode="synthetic_test_fixture", captured_at=_CAPTURED_AT,
                        inputs={"source_ids": [source_id], "fixture_only": True},
                        outputs={"parsed_text_sha256": body_hash},
                        result="PASS", status="verified", raw_content=body,
                        collection_metadata=metadata, provider="test_fixture",
                        publish_datetime="", domain_id=write_context["domain_id"],
                        subject_id=write_context["subject_id"],
                        brand_focus_id=write_context["brand_focus_id"],
                        global_scope=write_context["global_scope"],
                    )
                    connection.execute(
                        "UPDATE lumenis_shared_artifacts SET evidence_id=?, updated_at=? WHERE artifact_id=?",
                        (str(evidence_id), _CAPTURED_AT, artifact["artifact_id"]),
                    )
                    read_context = saved_work.authorize(
                        actor, scope, action="read", connection=connection,
                    )
                    saved_work._verified_evidence(connection, evidence_id, read_context, actor)
                    current_ref = f"app_evidence_records:{evidence_id}"
                    raw_ref["content_evidence_ref"] = current_ref
                    connection.execute(
                        "UPDATE canonical_data SET raw_ref=?, source_platform='UNKNOWN' "
                        "WHERE canonical_id=? AND source_id=?",
                        (json.dumps(raw_ref, ensure_ascii=False, sort_keys=True),
                         row["canonical_id"], source_id),
                    )
                source_views[source_id] = _source_view(row, reference=current_ref, body=body)
    except BaseException:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    finally:
        request_context.pop()

    return {"actor": actor, "sources": source_views, "db_path": db_path, "app": app}


def attach_legacy_brief_to_job(client, prepared, job, *, version, question, stored_analysis):
    """Attach a fixed historical signed Evidence snapshot for reader coverage.

    The route creates only the Source Brief. This helper writes an old signed
    reader fixture; it never invokes a retired provider or current generation.
    """
    import lumenis.shared.reporting.source_brief_job as jobs
    from lumenis.shared.reporting import business_brief as brief
    from lumenis.shared.reporting import media_brief
    from lumenis.shared.reporting.operational_brief import _analysis_window

    _api, _app, db_path, _entry, _gate = client
    actor = prepared["actor"]
    actor_ref = media_brief._actor_ref(actor)
    scope = jobs._media_scope(job["source_brief"]["scope"])
    source_rows = []
    for record in job["source_brief"]["records"]:
        source = prepared["sources"].get(record["source_id"])
        if source is None:
            continue
        text, selection = _analysis_window(source["text"], question)
        source_rows.append({
            **source, "text": text, "text_selection": selection,
            "truncated": len(text) < len(source["text"]),
        })
    if not source_rows:
        raise AssertionError("the historical fixture needs a nonempty retained test source")

    material = {
        "question": question,
        "sources": source_rows,
        "sample": {"coverage": "PARTIAL", "test_only": True},
    }
    product_id = "CTH" if scope["domain_id"] == "cth" else "ZBMP"
    with DatabaseRepository(str(db_path)).transaction() as connection:
        evidence_id = evidence_store.record_evidence(
            connection=connection, source="shared_reporting", project="LUMENIS",
            product=product_id, feature_id=brief._FEATURE,
            test_name=job["job_id"], result="PASS", status="derived",
            inputs={"job_id": job["job_id"], "actor_ref": actor_ref, "scope": scope,
                    "version": version, "material": material},
            outputs={"analysis": stored_analysis,
                     "analysis_sha256": brief._digest(stored_analysis),
                     "input_sha256": brief._digest(material),
                     "provider": "ollama", "model": "historical-test-fixture"},
            provider="ollama", domain_id=scope["domain_id"],
            subject_id=scope["subject_id"], brand_focus_id=scope["brand_focus_id"],
            global_scope=scope["global_scope"],
            notes="Fixed signed historical test fixture; no provider was called.",
        )
    evidence_ref = f"app_evidence_records:{evidence_id}"
    historical = brief.read_business_brief(
        evidence_ref, job_id=job["job_id"], actor_ref=actor_ref,
        scope=scope, actor=actor,
    )

    with DatabaseRepository(str(db_path)).transaction() as connection:
        row = connection.execute(
            "SELECT report_type, report_date, total_notes, summary, source_snapshot "
            "FROM daily_reports WHERE report_id=?", (job["job_id"],),
        ).fetchone()
        if row is None:
            raise AssertionError("the Source Brief report must exist before historical replay")
        report_type, report_date, total_notes, summary, source_snapshot = row
        snapshot = json.loads(source_snapshot)
        snapshot["business_question"] = question
        snapshot["business_analysis"] = historical
        serialized = jobs._json(snapshot)
        artifact_hash = jobs._hash_artifact(
            report_id=job["job_id"], report_type=report_type,
            report_date=report_date, total_notes=total_notes,
            summary=summary, source_snapshot=serialized,
        )
        connection.execute(
            "UPDATE daily_reports SET source_snapshot=?, artifact_hash=? WHERE report_id=?",
            (serialized, artifact_hash, job["job_id"]),
        )
    return historical
