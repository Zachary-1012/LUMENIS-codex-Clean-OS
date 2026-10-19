"""Hermetic, self-authored retained-source fixtures for BusinessBrief tests.

These records are synthetic test inputs. They do not claim rights in, or facts
about, the example URL stored by the older Source Brief fixture, and they do
use the real Importer with exact approval, without executing a model/provider.
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
        "source_platform": row["source_platform"] or "UNKNOWN",
    }


def prepare_synthetic_content_sources(client, monkeypatch):
    """Replace synthetic Canonical setup with actual authorized Importer sources.

    The disposable old IDs map to writer-issued DOC IDs; no test producer is
    signed and no production verification hook is bypassed. Empty-body rows
    remain empty so missing-material negative cases retain their meaning.
    """
    from datetime import datetime, timezone
    from lumenis.importer import documents
    import shared_artifacts

    _api, app, db_path, _entry, gate = client
    db_path = Path(db_path).resolve()
    monkeypatch.setenv("ZBC_DB_PATH", str(db_path))
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(db_path.parent / "business-brief-test-artifacts"))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    monkeypatch.setattr(permission, "_TESTING_BYPASS_ENABLED", False)
    gate.grant_permission(permission.PermissionLevel.COMMIT)
    repository = DatabaseRepository(str(db_path))
    for module in (shared_artifacts, documents, saved_work, evidence_store):
        monkeypatch.setattr(module, "get_repository", lambda: repository)
    shared_artifacts.ensure_artifact_table()
    aliases = app.extensions.setdefault("business_brief_fixture_source_ids", {})
    sources = {}
    with app.test_request_context("/", headers={"Host": "localhost"},
                                  environ_overrides={"REMOTE_ADDR": "127.0.0.1"}):
        actor = permission.resolve_local_workspace_principal(module="reports", action="write")
        if type(actor) is not permission.LocalWorkspacePrincipal:
            raise AssertionError("real local workspace principal required")
        with repository.connection(read_only=True) as con:
            con.row_factory = sqlite3.Row
            rows = [dict(row) for row in con.execute(
                "SELECT * FROM canonical_data WHERE source_id IS NOT NULL "
                "AND source_type != 'document_row' ORDER BY source_id,canonical_id")]
        seen = set()
        for row in rows:
            old_id, body = row["source_id"], row["content"]
            if not old_id or old_id in seen:
                continue
            seen.add(old_id)
            aliases.setdefault(old_id, old_id)
            if not isinstance(body, str) or not body.strip():
                continue
            scope = _source_scope(row)
            if row['source_type'] == 'document':
                with repository.connection(read_only=True) as con:
                    context = saved_work.authorize(actor, scope, action='read', connection=con)
                    ev = saved_work._verified_evidence(con, int(row['scope_evidence_ref']), context, actor)
                assert ev['asset_id'] == old_id and ev['raw_content'] == body
                sources[old_id] = _source_view(row, reference=f"app_evidence_records:{ev['id']}", body=body)
                continue
            safe_name = re.sub(r"[^A-Za-z0-9_-]", "-", old_id)[:80]
            original = db_path.parent / (safe_name + '.txt')
            original.write_text(body, encoding='utf-8')
            captured = datetime.fromisoformat((row['captured_at'] or _CAPTURED_AT).replace('Z', '+00:00'))
            if captured.tzinfo is None:
                captured = captured.replace(tzinfo=timezone.utc)
            provenance = {
                'source_url': None, 'published_at': None, 'captured_at': captured.isoformat(),
                'rights': 'owner-approved', 'title': row['title'] or 'Synthetic BusinessBrief fixture',
                'intended_use': 'research_reference',
                'source_origin': {'kind': 'approved-file', 'ref': 'business-brief-test-' + safe_name},
                'content_origin': {'kind': 'self-authored', 'claim_type': 'synthetic_sample'},
                'rights_statement': 'Self-authored isolated test text; no external source rights or real-world facts claimed.',
            }
            args = {'actor': actor, 'scope': scope, 'provenance': provenance}
            resource = documents.document_import_resource(str(original), **args)
            gate.grant_approval(permission.OperationType.DATA_IMPORT.value,
                                resource=resource, granted_by='isolated-fixture-exact-owner-import')
            imported = documents.import_document(str(original), **args)
            new_id = imported['source_id']
            aliases[old_id] = new_id
            with repository.transaction() as con:
                # Remove only the obsolete synthetic row, after real intake succeeds.
                con.execute('DELETE FROM canonical_data WHERE canonical_id=? AND source_id=?',
                            (row['canonical_id'], old_id))
                con.row_factory = sqlite3.Row
                stored = dict(con.execute('SELECT * FROM canonical_data WHERE canonical_id=?',
                                          (imported['canonical_id'],)).fetchone())
                context = saved_work.authorize(actor, scope, action='read', connection=con)
                ev = saved_work._verified_evidence(con, imported['evidence_id'], context, actor)
                assert ev['feature_id'] == 'DOCUMENT_IMPORT' and ev['asset_id'] == new_id
                sources[new_id] = _source_view(stored, reference=f"app_evidence_records:{imported['evidence_id']}",
                                               body=ev['raw_content'])
    return {'actor': actor, 'sources': sources, 'source_ids': dict(aliases), 'db_path': db_path, 'app': app}


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
        # The historical question is also input to the current deterministic
        # research companion. Rebind it through the real Source owner rather
        # than leaving an unrelated question/hash in this signed test snapshot.
        if snapshot.get("research_analysis") is not None:
            from agent_research.source_bound import analyze_source_records
            with prepared["app"].test_request_context(
                "/", headers={"Host": "localhost"},
                environ_overrides={"REMOTE_ADDR": "127.0.0.1"},
            ):
                admitted = jobs._resolve_source_records(
                    {"source_brief": job["source_brief"]}, actor=actor, connection=connection,
                )
                snapshot["research_analysis"] = analyze_source_records(
                    question, admitted["records"], actor_id=snapshot["actor_id"],
                    scope=snapshot["scope"], **(snapshot.get("research") or {}),
                )
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
