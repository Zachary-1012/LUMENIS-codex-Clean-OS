"""Synthetic regressions for Collector source citation continuity; not business acceptance."""
from __future__ import annotations

import hashlib
import json

import pytest

pytest_plugins = ("tests.test_saved_document_workflow",)

from lumenis.shared.evidence import store
from lumenis.system.security import permission


_BODY = "公开帖子：新品「云海」于秋季发布，详细信息见官网。"
_SOURCE_ID = "fixture-x-note-1234567890"
_NATIVE_ID = "1234567890"
_SOURCE_URL = f"https://x.com/lumenis-fixture/status/{_NATIVE_ID}"
_PUBLISHED_AT = "2026-10-07T09:15:00Z"
_CAPTURED_AT = "2026-10-08T08:00:00Z"


def _json_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _seed_collected_source(
    workspace,
    *,
    parent_domain_id="cth",
    parent_status="verified",
    rights="public-reference-only",
    original_body=None,
    locator=None,
    binding_source_id=None,
    artifact_note_id=None,
    body=None,
):
    """Create test-only signed Collection and source Evidence plus the original Artifact bytes."""
    from_scope = workspace["scope"]
    context = workspace["work"].authorize(workspace["actor"], from_scope, action="read")
    owner = {key: value for key, value in context.items()
             if key not in {"domain_id", "subject_id", "brand_focus_id", "global_scope"}}
    body = _BODY if body is None else body
    native_body = body if original_body is None else original_body
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    native_body_sha256 = hashlib.sha256(native_body.encode("utf-8")).hexdigest()
    stable_source_key = f"x:{_NATIVE_ID}"
    parent_product = "CTH" if parent_domain_id == "cth" else "ZBMP"

    original = {
        "source_url": _SOURCE_URL,
        "body": native_body,
        "body_state": "NATIVE_FULL_POST",
        "capture_observation_native": _CAPTURED_AT,
        "platform": "x",
        "native_id": _NATIVE_ID,
        "stable_source_key": stable_source_key,
        "body_sha256": native_body_sha256,
        "publication": {"published_at_utc": _PUBLISHED_AT},
        "native_record": {
            "id": _NATIVE_ID,
            "text": native_body,
            "created_at": _PUBLISHED_AT,
        },
        "source_lineage": [
            {
                "locator": _SOURCE_URL,
                "sha256": hashlib.sha256(b"test-only original parent bytes").hexdigest(),
            }
        ],
    }
    raw = _json_bytes(original)
    source_fingerprint = hashlib.sha256(raw).hexdigest()
    expected_locator = {
        "unit": "native-post-body",
        "json_path": "$.body",
        "start": 0,
        "end": len(body),
        "offset_unit": "unicode-codepoint",
    }
    source_locator = expected_locator if locator is None else locator
    provenance = {
        "source_url": _SOURCE_URL,
        "published_at": _PUBLISHED_AT,
        "captured_at": _CAPTURED_AT,
        "rights": rights,
        "intended_use": "research_reference",
        "title": "Synthetic X native-source citation fixture",
        "content_origin": {"kind": "publisher-material", "claim_type": "source_statement"},
        "rights_statement": "Test-only public-reference declaration; no live source was accessed.",
    }

    parent_scope = {
        "domain_id": parent_domain_id,
        "subject_id": None,
        "brand_focus_id": None,
        "global_scope": True,
    }
    with workspace["repo"].transaction() as connection:
        parent_id = store.record_evidence(
            connection=connection,
            source="collector",
            project="LUMENIS",
            product=parent_product,
            feature_id="COLLECTOR_SOURCE_SCOPE_FIXTURE",
            asset_id="fixture-collection-run-20261008",
            test_name="collected-source-citation-parent",
            result="PASS",
            status=parent_status,
            inputs={"source_ids": [_SOURCE_ID]},
            outputs={"fixture_collection_receipt": "test-only"},
            domain_id=parent_scope["domain_id"],
            subject_id=parent_scope["subject_id"],
            brand_focus_id=parent_scope["brand_focus_id"],
            global_scope=parent_scope["global_scope"],
        )
        parent_ref = f"app_evidence_records:{parent_id}"
        artifact, artifact_path = workspace["work"]._stage_bytes(
            connection,
            raw=raw,
            context=context,
            kind="collected_source",
            source_execution_id=str(_SOURCE_ID),
            extension=".json",
            media_type="application/json",
        )
        collection_metadata = {
            "context": context,
            "owner": owner,
            "provenance": provenance,
            "source_url": _SOURCE_URL,
            "source_fingerprint": source_fingerprint,
            "parsed_text": body,
            "locators": [source_locator],
            "source_artifact_ref": artifact["artifact_id"],
            "source_kind": "collected_source",
            "native_source_binding": {
                "platform": "x",
                "native_id": _NATIVE_ID,
                "stable_source_key": stable_source_key,
                "source_id": _SOURCE_ID if binding_source_id is None else binding_source_id,
                "body_sha256": body_sha256,
                "collection_evidence_ref": parent_ref,
            },
        }
        source_evidence_id = store.record_evidence(
            connection=connection,
            source="collector",
            project="LUMENIS",
            product="CTH",
            feature_id="COLLECTED_SOURCE",
            asset_id=_SOURCE_ID,
            version="collected-source:test-v1",
            test_name="collected-source-citation-fixture",
            result="PASS",
            status="verified",
            inputs={"source_ids": [_SOURCE_ID], "collection_evidence_ref": parent_ref},
            outputs={"native_body_sha256": body_sha256},
            raw_content=body,
            collection_metadata=collection_metadata,
            domain_id=from_scope["domain_id"],
            subject_id=from_scope["subject_id"],
            brand_focus_id=from_scope["brand_focus_id"],
            global_scope=from_scope["global_scope"],
        )
        connection.execute(
            "UPDATE lumenis_shared_artifacts SET note_id=?,evidence_id=? WHERE artifact_id=?",
            (str(_SOURCE_ID if artifact_note_id is None else artifact_note_id),
             str(source_evidence_id), artifact["artifact_id"]),
        )

    return {
        "source_id": _SOURCE_ID,
        "parent_id": parent_id,
        "evidence_id": source_evidence_id,
        "artifact": artifact,
        "artifact_path": artifact_path,
        "raw": raw,
        "body": body,
        "locator": source_locator,
        "source_fingerprint": source_fingerprint,
    }


def _snapshot(workspace, source):
    evidence_rows = []
    for evidence_id in (source["parent_id"], source["evidence_id"]):
        evidence_rows.append(dict(workspace["repo"].query_one(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,)
        )))
    artifact_row = workspace["repo"].query_one(
        "SELECT * FROM lumenis_shared_artifacts WHERE artifact_id=?",
        (source["artifact"]["artifact_id"],),
    )
    return {
        "evidence_rows": evidence_rows,
        "artifact_row": dict(artifact_row) if artifact_row is not None else None,
        "artifact_bytes": source["artifact_path"].read_bytes()
        if source["artifact_path"].is_file() else None,
        "evidence_count": workspace["repo"].query_one(
            "SELECT COUNT(*) FROM app_evidence_records"
        )[0],
        "document_import_count": workspace["repo"].query_one(
            "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT'"
        )[0],
        "canonical_count": workspace["repo"].query_one(
            "SELECT COUNT(*) FROM canonical_data"
        )[0],
    }


def _assert_denial_preserved_source(workspace, source, before):
    after = _snapshot(workspace, source)
    assert after == before
    assert all(store.verify_evidence_record_integrity(row) for row in after["evidence_rows"])
    assert after["document_import_count"] == 0
    assert after["canonical_count"] == 0


def test_collected_source_can_be_located_saved_reopened_and_exported(workspace):
    source = _seed_collected_source(workspace)
    quote = "新品「云海」"
    start = source["body"].index(quote)
    end = start + len(quote)

    export_resource = "document-source-read:v1:" + source["source_fingerprint"]
    workspace["gate"].grant_approval(
        permission.OperationType.DATA_EXPORT.value,
        resource=export_resource,
        duration_minutes=5,
        granted_by="isolated-collected-source-citation-test",
    )
    reopened_source = workspace["documents"].reopen_imported_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert reopened_source["content"] == source["raw"]
    assert reopened_source["source_id"] == source["source_id"]
    assert reopened_source["evidence_id"] == source["evidence_id"]

    located = workspace["documents"].locate_quote(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"],
        start=start, end=end,
    )
    assert located["citation"] == {
        "evidence_id": source["evidence_id"], "start": start,
        "end": end, "quote": quote,
    }
    assert located["locators"] == [source["locator"]]
    assert located["source_url"] == _SOURCE_URL
    assert located["source_fingerprint"] == source["source_fingerprint"]
    assert located["rights"] == "public-reference-only"
    assert located["intended_use"] == "research_reference"

    save_args = {
        "title": "Collected source citation fixture",
        "markdown": f"Research draft cites: {quote}",
        "kind": "research",
        "payload": {"fixture_source_id": source["source_id"]},
        "citations": [located["citation"]],
        "request_id": "request-collected-source-0001",
        "work_id": None,
        "previous_artifact_id": None,
        "actor": workspace["actor"],
        "scope": workspace["scope"],
    }
    save_resource = workspace["work"].work_write_resource(**save_args)
    workspace["gate"].grant_approval(
        permission.OperationType.DATA_EXPORT.value,
        resource=save_resource,
        duration_minutes=5,
        granted_by="isolated-collected-source-citation-test",
    )
    saved = workspace["work"].save_work(**save_args)
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert reopened["document"]["citations"][0]["quote"] == quote
    assert reopened["document"]["citations"][0]["evidence_id"] == source["evidence_id"]

    assert workspace["repo"].query_one(
        "SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='DOCUMENT_IMPORT'"
    )[0] == 0
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM canonical_data")[0] == 0


def _approve_internal_source_use(workspace, source):
    from lumenis.shared.evidence import store

    body_sha256 = hashlib.sha256(source["body"].encode("utf-8")).hexdigest()
    scope_locator = f"app_evidence_records:{source['parent_id']}"
    content_locator = f"app_evidence_records:{source['evidence_id']}"
    parent_binding = {
        "receipt_id": "PO-TEST-SOURCE-USE-20261011",
        "source_id": source["source_id"],
        "source_url": _SOURCE_URL,
        "domain_id": workspace["scope"]["domain_id"],
        "subject_id": workspace["scope"]["subject_id"],
        "brand_focus_id": workspace["scope"]["brand_focus_id"],
        "scope_evidence_ref": scope_locator,
        "source_content_locator": content_locator,
        "derived_content_evidence_ref": content_locator,
        "body_sha256": body_sha256,
        "snapshot_kind": "existing_source_evidence_snapshot",
    }
    marker = {
        "receipt_id": parent_binding["receipt_id"],
        "source_id": source["source_id"],
        "source_url": _SOURCE_URL,
        "domain_id": workspace["scope"]["domain_id"],
        "subject_id": workspace["scope"]["subject_id"],
        "brand_focus_id": workspace["scope"]["brand_focus_id"],
        "scope_evidence_ref": scope_locator,
        "content_evidence_ref": content_locator,
        "body_sha256": body_sha256,
        "allowed_purposes": [
            "internal_research", "short_quote",
            "cth_brief" if workspace["scope"]["domain_id"] == "cth" else "bmp_brief",
        ],
        "allowed_operations": ["read", "save", "revise", "reopen"],
        "rights_state": "UNREVIEWED",
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }
    with workspace["repo"].transaction() as con:
        row = con.execute("SELECT collection_metadata FROM app_evidence_records WHERE id=?",
                          (source["evidence_id"],)).fetchone()
        metadata = json.loads(row[0])
        metadata["provenance"]["rights"] = "UNREVIEWED"
        metadata["provenance"]["approved_internal_source_use"] = marker
        metadata["provenance"]["source_reference_parent"] = parent_binding
        metadata["source_reference_parent"] = parent_binding
        con.execute("UPDATE app_evidence_records SET collection_metadata=? WHERE id=?",
                    (json.dumps(metadata, ensure_ascii=False), source["evidence_id"]))
        store._sign_evidence_record(con, source["evidence_id"])
    return {**marker, "_parent_binding": parent_binding}


def _patch_current_source_view(monkeypatch, workspace, source, marker):
    import canonical_data
    from lumenis.shared.reporting import operational_brief

    row = {
        "source_id": source["source_id"],
        "canonical_id": "can_fixture_collected_source",
        "product_id": "CTH",
        "domain_id": workspace["scope"]["domain_id"],
        "subject_id": workspace["scope"]["subject_id"],
        "brand_focus_id": workspace["scope"]["brand_focus_id"],
        "scope_status": "VERIFIED",
        "scope_evidence_ref": str(source["parent_id"]),
        "source_table": "collector_sources",
        "external_id": _NATIVE_ID,
        "raw_ref": json.dumps({
            "source": "collector",
            "content_evidence_ref": marker["content_evidence_ref"],
            "approved_internal_source_use": marker["_parent_binding"],
        }),
        "content": source["body"],
        "url": _SOURCE_URL,
        "canonical_url": _SOURCE_URL,
    }
    monkeypatch.setattr(canonical_data, "list_scoped_canonical",
                        lambda _con, **_kwargs: {"records": [row]})
    monkeypatch.setattr(operational_brief, "_content_evidence_ref",
        lambda _con, _row, _scope_ref: marker["content_evidence_ref"])


def test_approved_unreviewed_collector_source_use_is_rechecked_for_each_operation(workspace, monkeypatch):
    source = _seed_collected_source(workspace, rights="UNREVIEWED")
    marker = _approve_internal_source_use(workspace, source)
    _patch_current_source_view(monkeypatch, workspace, source, marker)

    calls = []

    def validate_current_source_use(connection, **kwargs):
        assert connection is not None
        calls.append(kwargs)
        return {"rights_state": "UNREVIEWED", **kwargs}

    monkeypatch.setattr(permission, "validate_current_source_use", validate_current_source_use,
                        raising=False)
    quote = "新品「云海」"
    start = source["body"].index(quote)
    citation = {"evidence_id": source["evidence_id"], "start": start,
                "end": start + len(quote), "quote": quote}
    save_args = {
        "title": "Approved internal source-use fixture",
        "markdown": f"Internal research cites: {quote}",
        "kind": "research",
        "payload": {"fixture_source_id": source["source_id"]},
        "citations": [citation],
        "request_id": "request-approved-internal-use-v1",
        "work_id": None,
        "previous_artifact_id": None,
        "actor": workspace["actor"],
        "scope": workspace["scope"],
    }
    resource = workspace["work"].work_write_resource(**save_args)
    workspace["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value,
                                     resource=resource, granted_by="isolated-source-use-test")
    first = workspace["work"].save_work(**save_args)
    artifact_id = first["artifact"]["artifact_id"]
    workspace["work"].read_committed_work(artifact_id, actor=workspace["actor"], scope=workspace["scope"])
    workspace["work"].reopen_work(artifact_id, actor=workspace["actor"], scope=workspace["scope"])

    revise_args = {
        **save_args,
        "markdown": f"Revised internal research cites: {quote}",
        "request_id": "request-approved-internal-use-v2",
        "work_id": first["document"]["work_id"],
        "previous_artifact_id": artifact_id,
        "expected_draft_digest": first["document"]["draft_digest"],
    }
    revised_resource = workspace["work"].work_write_resource(**revise_args)
    workspace["gate"].grant_approval(permission.OperationType.DATA_EXPORT.value,
                                     resource=revised_resource, granted_by="isolated-source-use-test")
    second = workspace["work"].save_work(**revise_args)
    assert second["document"]["version"] == 2
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        workspace["work"].export_work(artifact_id, actor=workspace["actor"], scope=workspace["scope"])

    assert {call["purpose"] for call in calls} == {"internal_research", "short_quote"}
    assert {call["operation"] for call in calls} >= {"read", "save", "revise", "reopen"}
    assert all(call["source_id"] == source["source_id"] for call in calls)
    assert all(call["scope_evidence_ref"] == marker["scope_evidence_ref"] for call in calls)
    assert all(call["content_evidence_ref"] == marker["_parent_binding"]["source_content_locator"]
               for call in calls)
    assert all(call["scope_evidence_ref"] == marker["_parent_binding"]["scope_evidence_ref"]
               for call in calls)
    assert all(call["body_sha256"] == marker["body_sha256"] for call in calls)
    stored = workspace["repo"].query_one("SELECT collection_metadata FROM app_evidence_records WHERE id=?",
                                          (source["evidence_id"],))
    stored_provenance = json.loads(stored[0])["provenance"]
    assert stored_provenance["rights"] == "UNREVIEWED"
    assert stored_provenance["approved_internal_source_use"] == {
        key: value for key, value in marker.items() if key != "_parent_binding"
    }


def test_cth_notes_scope_locator_binds_a_distinct_approved_child_evidence(workspace, monkeypatch):
    import canonical_data

    source_id = "public-http:fixture-notes-source"
    source_url = "https://example.org/approved-notes-source"
    body = "Existing Canonical snapshot text for an internal brief."
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()
    child_evidence_id = 902
    child_ref = f"app_evidence_records:{child_evidence_id}"
    parent = {
        "receipt_id": "PO-TEST-SOURCE-USE-20261011",
        "source_id": source_id,
        "source_url": source_url,
        "domain_id": "cth",
        "subject_id": None,
        "brand_focus_id": None,
        "scope_evidence_ref": "notes:109",
        "source_content_locator": "notes:109",
        "derived_content_evidence_ref": child_ref,
        "body_sha256": body_sha256,
        "snapshot_kind": "existing_canonical_content_snapshot_not_native_capture",
    }
    marker = {
        "receipt_id": parent["receipt_id"],
        "source_id": source_id,
        "source_url": source_url,
        "domain_id": "cth",
        "subject_id": None,
        "brand_focus_id": None,
        "scope_evidence_ref": "notes:109",
        "content_evidence_ref": child_ref,
        "body_sha256": body_sha256,
        "allowed_purposes": ["internal_research", "short_quote", "cth_brief"],
        "allowed_operations": ["read", "save", "revise", "reopen"],
        "rights_state": "UNREVIEWED",
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }
    row = {
        "source_id": source_id,
        "canonical_id": "canonical-notes-source-109",
        "domain_id": "cth",
        "subject_id": None,
        "brand_focus_id": None,
        "scope_evidence_ref": "109",
        "raw_ref": json.dumps({
            "table": "notes", "note_id": source_id, "id": 109,
            "approved_internal_source_use": parent,
        }),
        "content": body,
        "url": source_url,
    }
    monkeypatch.setattr(canonical_data, "list_scoped_canonical",
                        lambda _con, **_kwargs: {"records": [row]})
    calls = []

    def validate_current_source_use(_connection, **kwargs):
        calls.append(kwargs)
        return {"rights_state": "UNREVIEWED", **kwargs}

    monkeypatch.setattr(permission, "validate_current_source_use", validate_current_source_use,
                        raising=False)
    context = workspace["work"].authorize(workspace["actor"], workspace["scope"], action="read")
    evidence = {
        "id": child_evidence_id,
        "asset_id": source_id,
        "content_hash": body_sha256,
    }
    provenance = {
        "context": context,
        "source_url": source_url,
        "parsed_text": body,
        "source_reference_parent": parent,
        "provenance": {
            "rights": "UNREVIEWED",
            "source_url": source_url,
            "source_kind": "approved_internal_source_reference",
            "source_reference_parent": parent,
            "approved_internal_source_use": marker,
        },
    }
    source_binding = {
        "source_id": source_id,
        "canonical_id": row["canonical_id"],
        "scope_evidence_ref": "109",
        "content_evidence_ref": child_ref,
        "source_scope_locator": "notes:109",
        "source_content_locator": "notes:109",
        "evidence_id": child_evidence_id,
        "body_sha256": body_sha256,
    }
    with workspace["repo"].connection() as con:
        assert workspace["work"]._validate_current_approved_source_use(
            con, evidence, provenance, provenance["provenance"], context,
            purpose="cth_brief", operation="save", source_binding=source_binding,
        )
    with workspace["repo"].connection() as con:
        with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
            workspace["work"]._validate_current_approved_source_use(
                con, evidence, provenance, provenance["provenance"], context,
                purpose="bmp_brief", operation="save", source_binding=source_binding,
            )

    assert len(calls) == 1
    assert calls[0]["scope_evidence_ref"] == "notes:109"
    assert calls[0]["content_evidence_ref"] == "notes:109"
    assert marker["content_evidence_ref"] == child_ref
    assert provenance["provenance"]["rights"] == "UNREVIEWED"


def test_approved_source_quote_limit_counts_distinct_quote_text_once(workspace, monkeypatch):
    body = "a" * 200
    source = _seed_collected_source(workspace, rights="UNREVIEWED", body=body)
    marker = _approve_internal_source_use(workspace, source)
    _patch_current_source_view(monkeypatch, workspace, source, marker)

    def validate_current_source_use(_connection, **kwargs):
        return {"rights_state": "UNREVIEWED", **kwargs}

    monkeypatch.setattr(permission, "validate_current_source_use", validate_current_source_use,
                        raising=False)
    context = workspace["work"].authorize(workspace["actor"], workspace["scope"], action="read")
    one_hundred = {"evidence_id": source["evidence_id"], "start": 0, "end": 100, "quote": "a" * 100}
    duplicate = dict(one_hundred)
    with workspace["repo"].connection() as con:
        checked = workspace["work"]._validate_citations(
            con, [one_hundred, duplicate], context, workspace["actor"])
    assert len(checked) == 2
    second_unique = {"evidence_id": source["evidence_id"], "start": 100, "end": 161, "quote": "a" * 61}
    with workspace["repo"].connection() as con:
        with pytest.raises(ValueError, match="SOURCE_USE_QUOTE_LIMIT_EXCEEDED"):
            workspace["work"]._validate_citations(
                con, [one_hundred, second_unique], context, workspace["actor"])
    too_long = {"evidence_id": source["evidence_id"], "start": 0, "end": 161, "quote": "a" * 161}
    with workspace["repo"].connection() as con:
        with pytest.raises(ValueError, match="SOURCE_USE_QUOTE_LIMIT_EXCEEDED"):
            workspace["work"]._validate_citations(con, [too_long], context, workspace["actor"])


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        ("parent_scope", "COLLECTED_SOURCE_PARENT_INVALID"),
        ("parent_status", "COLLECTED_SOURCE_PARENT_INVALID"),
        ("missing_artifact", "DOCUMENT_SOURCE_ARTIFACT_MISSING"),
        ("tampered_artifact", "DOCUMENT_SOURCE_ARTIFACT_INVALID"),
        ("wrong_body", "COLLECTED_SOURCE_ORIGINAL_INVALID"),
        ("wrong_locator", "COLLECTED_SOURCE_LOCATOR_INVALID"),
        ("wrong_source_asset", "COLLECTED_SOURCE_BINDING_INVALID"),
        ("unknown_rights", "WORK_SOURCE_RIGHTS_UNVERIFIED"),
        ("local_permission_revoked", "WORK_PERMISSION_DENIED"),
    ],
    ids=[
        "wrong-parent-scope", "wrong-parent-status", "missing-artifact",
        "tampered-artifact", "wrong-body", "wrong-locator",
        "wrong-source-asset", "unknown-rights", "local-permission-revoked",
    ],
)
def test_collected_source_denials_preserve_source_bytes_and_evidence_history(
    workspace, failure, expected_error,
):
    options = {}
    if failure == "parent_scope":
        options["parent_domain_id"] = "zbmp"
    elif failure == "parent_status":
        options["parent_status"] = "pending"
    elif failure == "wrong_body":
        options["original_body"] = _BODY + "修改后的正文。"
    elif failure == "wrong_locator":
        options["locator"] = {
            "unit": "native-post-body", "json_path": "$.body",
            "start": 1, "end": len(_BODY), "offset_unit": "unicode-codepoint",
        }
    elif failure == "wrong_source_asset":
        options["binding_source_id"] = "fixture-x-other-note-1234567890"
    elif failure == "unknown_rights":
        options["rights"] = "unknown"
    source = _seed_collected_source(workspace, **options)

    if failure == "missing_artifact":
        with workspace["repo"].transaction() as connection:
            connection.execute(
                "DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?",
                (source["artifact"]["artifact_id"],),
            )
    elif failure == "tampered_artifact":
        source["artifact_path"].write_bytes(source["raw"] + b"tampered")

    before = _snapshot(workspace, source)
    if failure == "local_permission_revoked":
        workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
        assert permission.resolve_local_workspace_principal(
            module="reports", action="read"
        ) is None

    with pytest.raises(ValueError, match=expected_error):
        workspace["documents"].locate_quote(
            source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"],
            start=0, end=1,
        )

    _assert_denial_preserved_source(workspace, source, before)


def _seed_approved_internal_source_canonical(workspace, monkeypatch):
    """Build a disposable, registered CTH source for the approved-reference path."""
    import canonical_data
    import subject_registry
    from canonical_data import CanonicalRecord, persist_canonical
    from lumenis.shared.database.business_schema import apply_business_schema

    subject, _ = subject_registry.add_subject({
        "domain_id": "CTH",
        "subject_type": "company",
        "name_en": "Approved Source Regression Venue",
        "name_zh": "授权来源回归测试主体",
    })
    scope = {
        "domain_id": "cth",
        "subject_id": subject["subject_id"],
        "brand_focus_id": None,
        "global_scope": False,
    }
    workspace["scope"] = scope

    source_id = "test-approved-source-reference-20261011"
    canonical_id = "canonical-test-approved-source-reference-20261011"
    source_url = "https://example.org/test-approved-source-reference"
    body = "测试内容仅用于核验授权快照的派生引用与 SavedWork 版本链。"
    body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
        canonical_data.ensure_canonical_table(connection=con)
        cursor = con.execute(
            "INSERT INTO notes (note_id,title,content,url) VALUES (?,?,?,?)",
            (source_id, "Disposable approved-source fixture", body, source_url),
        )
        note_id = int(cursor.lastrowid)
        scope_evidence_id = store.record_evidence(
            connection=con,
            source="isolated-test-canonical-scope",
            project="LUMENIS",
            product="CTH",
            domain_id="cth",
            subject_id=scope["subject_id"],
            global_scope=False,
            feature_id="APPROVED_SOURCE_REFERENCE_SCOPE_FIXTURE",
            asset_id=source_id,
            version="isolated-test-v1",
            result="PASS",
            status="verified",
            inputs={"source_ids": [source_id]},
            outputs={"scope_fixture": True},
        )
        persist_canonical(con, CanonicalRecord(
            canonical_id=canonical_id,
            product_id="CTH",
            domain_id="cth",
            subject_id=scope["subject_id"],
            scope_status="VERIFIED",
            scope_evidence_ref=str(scope_evidence_id),
            source_id=source_id,
            external_id=source_id,
            source_type="note",
            source_table="notes",
            title="Disposable approved-source fixture",
            content=body,
            url=source_url,
            canonical_url=source_url,
            raw_ref=json.dumps({
                "table": "notes", "note_id": source_id, "id": note_id,
            }, ensure_ascii=False, sort_keys=True),
            captured_at="2026-10-11T00:00:00Z",
        ))

    source_locator = f"notes:{note_id}"
    entry = {
        "receipt_id": "PO-20261011-APPROVED-INTERNAL-SOURCE-USE",
        "source_id": source_id,
        "source_url": source_url,
        "canonical_id": canonical_id,
        "domain_id": "cth",
        "subject_id": scope["subject_id"],
        "brand_focus_id": None,
        "scope_evidence_ref": source_locator,
        "content_evidence_ref": source_locator,
        "body_sha256": body_sha256,
        "snapshot_kind": "existing_canonical_content_snapshot_not_native_capture",
        "allowed_purposes": ["internal_research", "short_quote", "cth_brief"],
        "allowed_operations": ["derive_reference", "read", "save", "revise", "reopen"],
        "rights_state": "UNKNOWN",
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }
    monkeypatch.setattr(permission, "_load_source_use_receipt", lambda _receipt_id: {
        "sources": [entry],
    })
    return {
        "source_id": source_id,
        "canonical_id": canonical_id,
        "source_url": source_url,
        "body": body,
        "body_sha256": body_sha256,
        "scope_evidence_id": scope_evidence_id,
        "entry": entry,
        "scope": scope,
    }


def _approved_source_state_snapshot(workspace, source):
    import subject_registry

    with workspace["repo"].connection(read_only=True, wal=False) as con:
        tables = {
            "artifacts": "SELECT * FROM lumenis_shared_artifacts ORDER BY artifact_id",
            "evidence": "SELECT * FROM app_evidence_records ORDER BY id",
            "canonical": "SELECT * FROM canonical_data WHERE canonical_id=?",
            "note": "SELECT * FROM notes WHERE note_id=?",
            "subject": f"SELECT * FROM {subject_registry.TABLE_NAME} WHERE subject_id=?",
        }
        rows = {
            "artifacts": [tuple(row) for row in con.execute(tables["artifacts"]).fetchall()],
            "evidence": [tuple(row) for row in con.execute(tables["evidence"]).fetchall()],
            "canonical": [tuple(row) for row in con.execute(
                tables["canonical"], (source["canonical_id"],)
            ).fetchall()],
            "note": [tuple(row) for row in con.execute(
                tables["note"], (source["source_id"],)
            ).fetchall()],
            "subject": [tuple(row) for row in con.execute(
                tables["subject"], (source["scope"]["subject_id"],)
            ).fetchall()],
        }
    artifact_dir = workspace["root"] / "artifacts"
    rows["artifact_files"] = sorted(
        (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in artifact_dir.iterdir() if path.is_file()
    ) if artifact_dir.exists() else []
    return rows


def _prepare_approved_source_reference(workspace, source, request_id, *, actor=None, scope=None):
    return workspace["documents"].prepare_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id=request_id,
        actor=workspace["actor"] if actor is None else actor,
        scope=source["scope"] if scope is None else scope,
    )


def _confirm_approved_source_reference(workspace, source, request_id, *, actor=None, scope=None):
    actor = workspace["actor"] if actor is None else actor
    scope = source["scope"] if scope is None else scope
    request = {
        "source_id": source["source_id"],
        "canonical_id": source["canonical_id"],
        "expected_body_sha256": source["body_sha256"],
        "request_id": request_id,
    }
    pending = permission.prepare_approved_source_reference_confirmation(
        actor=actor, scope=scope, request=request, gate=workspace["gate"],
    )
    assert pending["allowed"] is True
    assert pending["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_PENDING"
    confirmed = permission.confirm_approved_source_reference_confirmation(
        actor=actor, scope=scope, confirmation_id=pending["confirmation_id"],
        confirmed=True, gate=workspace["gate"],
    )
    assert confirmed["allowed"] is True
    assert confirmed["code"] == "APPROVED_SOURCE_REFERENCE_READY_FOR_RETRY"
    assert confirmed["confirmation_id"] == pending["confirmation_id"]
    assert confirmed["resource"] == pending["resource"]
    assert "approval_token" not in confirmed
    return confirmed


def _seed_active_admin_account(workspace):
    from account.models import ACCOUNT_TABLES_SQL

    with workspace["repo"].transaction() as con:
        con.executescript(ACCOUNT_TABLES_SQL)
        con.execute(
            "INSERT INTO v4_users (id,username,password_hash,role,status) VALUES (?,?,?,?,?)",
            (90210, "approved-source-second-actor", "isolated-test", "admin", "active"),
        )
    return {"id": 90210}


def _approved_source_effect_snapshot(workspace):
    import copy
    from lumenis.system.security.effect_fence import get_effect_fence

    gate = workspace["gate"]
    with gate._approval_lock:
        approvals = copy.deepcopy(gate._approvals)
    fence = get_effect_fence()
    with fence._lock:
        reservations = copy.deepcopy(fence._reservations)
    return approvals, reservations


def _approved_source_database_snapshot(workspace):
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        table_names = [row[0] for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]
        return {
            name: [tuple(row) for row in con.execute(
                'SELECT * FROM "' + name.replace('"', '""') + '"'
            ).fetchall()]
            for name in table_names
        }


def test_approved_internal_source_reference_saves_revises_and_reopens_saved_work(
    workspace, monkeypatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    from lumenis.system.security.permission import OperationType

    _confirm_approved_source_reference(workspace, source, "approved-source-derive-v1")
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id="approved-source-derive-v1",
        actor=workspace["actor"],
        scope=source["scope"],
    )
    _confirm_approved_source_reference(
        workspace, source, "approved-source-derive-replay-v1",
    )
    replay = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id="approved-source-derive-replay-v1",
        actor=workspace["actor"],
        scope=source["scope"],
    )
    assert derived["replayed"] is False
    assert replay["replayed"] is True
    assert replay["evidence_id"] == derived["evidence_id"]

    quote = "派生引用与 SavedWork"
    start = source["body"].index(quote)
    citation = {
        "evidence_id": derived["evidence_id"],
        "start": start,
        "end": start + len(quote),
        "quote": quote,
    }
    assert len(citation["quote"]) <= 160
    save_args = {
        "title": "Approved source reference continuity regression",
        "markdown": f"内部回归引用：{quote}",
        "kind": "research",
        "payload": {"source_id": source["source_id"]},
        "citations": [citation],
        "request_id": "approved-source-saved-work-v1",
        "work_id": None,
        "previous_artifact_id": None,
        "expected_draft_digest": None,
        "actor": workspace["actor"],
        "scope": source["scope"],
    }
    first_resource = workspace["work"].work_write_resource(**save_args)
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=first_resource,
        granted_by="isolated-approved-source-reference-test",
    )
    first = workspace["work"].save_work(**save_args)
    first_artifact_id = first["artifact"]["artifact_id"]

    located = workspace["documents"].locate_quote(
        derived["evidence_id"],
        actor=workspace["actor"],
        scope=source["scope"],
        start=start,
        end=start + len(quote),
    )
    assert located["source_id"] == source["source_id"]
    first_read = workspace["work"].read_committed_work(
        first_artifact_id, actor=workspace["actor"], scope=source["scope"],
    )
    assert first_read["receipt"]["sources"][0]["source_id"] == source["source_id"]

    revise_args = {
        **save_args,
        "markdown": f"修订后仍引用：{quote}",
        "request_id": "approved-source-saved-work-v2",
        "work_id": first["document"]["work_id"],
        "previous_artifact_id": first_artifact_id,
        "expected_draft_digest": first["document"]["draft_digest"],
    }
    revise_resource = workspace["work"].work_write_resource(**revise_args)
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=revise_resource,
        granted_by="isolated-approved-source-reference-test",
    )
    second = workspace["work"].save_work(**revise_args)
    assert second["document"]["version"] == 2
    second_artifact_id = second["artifact"]["artifact_id"]

    for artifact_id, expected_version in (
        (first_artifact_id, 1), (second_artifact_id, 2),
    ):
        reopened = workspace["work"].reopen_work(
            artifact_id, actor=workspace["actor"], scope=source["scope"],
        )
        assert reopened["document"]["version"] == expected_version
        assert reopened["receipt"]["sources"][0]["source_id"] == source["source_id"]

    reopened_source = workspace["documents"].reopen_imported_source(
        derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
    )
    assert reopened_source["content"] == source["body"].encode("utf-8")
    assert reopened_source["sha256"] == source["body_sha256"]
    assert reopened_source["parsed_text"] == source["body"]
    assert reopened_source["text_length"] == len(source["body"])
    assert reopened_source["source_id"] == source["source_id"]

    source_export_resource = "document-source-read:v1:" + reopened_source["sha256"]
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=source_export_resource,
        granted_by="isolated-approved-source-reference-test",
    )
    assert workspace["gate"].is_approved(
        OperationType.DATA_EXPORT.value, source_export_resource,
    ) is True
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        workspace["documents"].reopen_imported_source(
            derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
            _source_use_operation="export",
        )

    saved_export_resource = "saved-work-export:v1:" + workspace["work"]._digest({
        "id": second_artifact_id,
        "sha256": second["artifact"]["sha256"],
        "format": "json",
    })
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=saved_export_resource,
        granted_by="isolated-approved-source-reference-test",
    )
    assert workspace["gate"].is_approved(
        OperationType.DATA_EXPORT.value, saved_export_resource,
    ) is True
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        workspace["work"].export_work(
            second_artifact_id, actor=workspace["actor"], scope=source["scope"],
        )



    withdrawn_revision = {
        **revise_args,
        "markdown": f"第三版在提交前撤回来源：{quote}",
        "request_id": "approved-source-saved-work-v3-source-withdrawn",
        "previous_artifact_id": second_artifact_id,
        "expected_draft_digest": second["document"]["draft_digest"],
    }
    import subject_registry
    from lumenis.system.security.effect_fence import get_effect_fence

    before_withdrawal = _approved_source_state_snapshot(workspace, source)
    fence = get_effect_fence()
    with fence._lock:
        previous_reservations = set(fence._reservations)

    def withdraw_source_before_commit(con, _record, _document):
        changed = con.execute(
            f"UPDATE {subject_registry.TABLE_NAME} SET status='archived' WHERE subject_id=?",
            (source["scope"]["subject_id"],),
        )
        assert changed.rowcount == 1

    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        workspace["work"].save_work(
            **withdrawn_revision, before_commit=withdraw_source_before_commit,
        )
    assert _approved_source_state_snapshot(workspace, source) == before_withdrawal
    latest_after_rollback = workspace["work"].reopen_work(
        second_artifact_id, actor=workspace["actor"], scope=source["scope"],
    )
    assert latest_after_rollback["document"]["version"] == 2
    with fence._lock:
        failed_reservations = [
            value for key, value in fence._reservations.items()
            if key not in previous_reservations
        ]
    assert len(failed_reservations) == 1
    assert failed_reservations[0]["status"] == "failed"

    with workspace["repo"].transaction() as con:
        con.execute(
            f"UPDATE {subject_registry.TABLE_NAME} SET status='archived' WHERE subject_id=?",
            (source["scope"]["subject_id"],),
        )
    with pytest.raises(ValueError, match="WORK_PERMISSION_DENIED"):
        workspace["work"].reopen_work(
            second_artifact_id, actor=workspace["actor"], scope=source["scope"],
        )


def test_approved_source_reference_rejects_a_parent_binding_to_the_wrong_child(
    workspace, monkeypatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)

    _confirm_approved_source_reference(
        workspace, source, "approved-source-wrong-child-v1",
    )
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id="approved-source-wrong-child-v1",
        actor=workspace["actor"],
        scope=source["scope"],
    )

    with workspace["repo"].transaction() as con:
        row = con.execute(
            "SELECT raw_ref,content FROM canonical_data WHERE canonical_id=?",
            (source["canonical_id"],),
        ).fetchone()
        raw_ref = json.loads(row[0])
        raw_ref["approved_internal_source_use"]["derived_content_evidence_ref"] = (
            f"app_evidence_records:{source['scope_evidence_id']}"
        )
        con.execute(
            "UPDATE canonical_data SET raw_ref=? WHERE canonical_id=?",
            (json.dumps(raw_ref, ensure_ascii=False, sort_keys=True), source["canonical_id"]),
        )

    with pytest.raises(ValueError, match="SOURCE_USE_SOURCE_REFERENCE_CHANGED"):
        workspace["documents"].locate_quote(
            derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
            start=0, end=1,
        )
    current = workspace["repo"].query_one(
        "SELECT content FROM canonical_data WHERE canonical_id=?", (source["canonical_id"],)
    )
    assert current[0] == source["body"]


@pytest.mark.parametrize("tamper", ["wrong_signed_asset", "wrong_signed_focus"])
def test_approved_source_reference_rejects_resigned_child_asset_or_focus(
    workspace, monkeypatch, tamper,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)

    request_id = f"approved-source-{tamper}-v1"
    _confirm_approved_source_reference(workspace, source, request_id)
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id=request_id,
        actor=workspace["actor"],
        scope=source["scope"],
    )

    if tamper == "wrong_signed_focus":
        import subject_registry

        other_subject, _ = subject_registry.add_subject({
            "domain_id": "CTH",
            "subject_type": "company",
            "name_en": "Other Approved Source Regression Venue",
            "name_zh": "另一个授权来源回归测试主体",
        })

    with workspace["repo"].transaction() as con:
        row = con.execute(
            "SELECT inputs_json FROM app_evidence_records WHERE id=?",
            (derived["evidence_id"],),
        ).fetchone()
        inputs = json.loads(row[0])
        if tamper == "wrong_signed_asset":
            con.execute(
                "UPDATE app_evidence_records SET asset_id=? WHERE id=?",
                ("approved-source-reference:wrong-signed-child", derived["evidence_id"]),
            )
        else:
            inputs["_lumenis_scope"]["subject_id"] = other_subject["subject_id"]
            con.execute(
                "UPDATE app_evidence_records SET inputs_json=? WHERE id=?",
                (json.dumps(inputs, ensure_ascii=False, sort_keys=True), derived["evidence_id"]),
            )
        store._sign_evidence_record(con, derived["evidence_id"])

    expected_error = (
        "DOCUMENT_SOURCE_ARTIFACT_INVALID"
        if tamper == "wrong_signed_asset" else "WORK_EVIDENCE_CONTEXT_MISMATCH"
    )
    with pytest.raises(ValueError, match=expected_error):
        workspace["documents"].locate_quote(
            derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
            start=0, end=1,
        )


def _seed_bmp_original_source_evidence(workspace):
    """Seed one registered BMP BrandFocus through the shared Evidence writer."""
    import canonical_data
    import subject_registry
    from canonical_data import CanonicalRecord, persist_canonical
    from lumenis.shared.database.business_schema import apply_business_schema

    brand, _created = subject_registry.add_subject({
        "domain_id": "BMP",
        "subject_type": "brand",
        "name_en": "Approved Source Regression Brand",
        "name_zh": "授权来源回归测试品牌",
    })
    scope = {
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": brand["brand_focus_id"],
        "global_scope": False,
    }
    workspace["scope"] = scope
    context = workspace["work"].authorize(workspace["actor"], scope, action="read")
    owner = {key: value for key, value in context.items()
             if key not in {"domain_id", "subject_id", "brand_focus_id", "global_scope"}}

    source_id = "test-bmp-original-source-evidence-20261011"
    canonical_id = "canonical-test-bmp-original-source-evidence-20261011"
    source_url = "https://example.org/test-bmp-original-source-evidence"
    body = "授权来源正文用于验证品牌范围、引用修订和恢复链。"
    raw = body.encode("utf-8")
    body_sha256 = hashlib.sha256(raw).hexdigest()
    source_fingerprint = body_sha256

    with workspace["repo"].transaction() as con:
        apply_business_schema(con)
        canonical_data.ensure_canonical_table(connection=con)
        scope_evidence_id = store.record_evidence(
            connection=con,
            source="isolated-test-canonical-scope",
            project="LUMENIS",
            product="ZBMP",
            feature_id="BMP_APPROVED_SOURCE_SCOPE_FIXTURE",
            asset_id=source_id,
            version="bmp-source-scope:test-v1",
            test_name="bmp-approved-source-scope-fixture",
            result="PASS",
            status="verified",
            inputs={"source_ids": [source_id]},
            outputs={"scope_fixture": "test-only"},
            domain_id=scope["domain_id"],
            subject_id=None,
            brand_focus_id=scope["brand_focus_id"],
            global_scope=False,
        )
        artifact, artifact_path = workspace["work"]._stage_bytes(
            con,
            raw=raw,
            context=context,
            kind="imported_document_source",
            source_execution_id=source_id,
            extension=".txt",
            media_type="text/plain; charset=utf-8",
        )
        metadata = {
            "context": context,
            "owner": owner,
            "source_url": source_url,
            "source_artifact_ref": artifact["artifact_id"],
            "source_fingerprint": source_fingerprint,
            "parsed_text": body,
            "locators": [{
                "unit": "fixture-original-text",
                "start": 0,
                "end": len(body),
                "offset_unit": "unicode-codepoint",
            }],
            "provenance": {
                "source_url": source_url,
                "published_at": "UNKNOWN",
                "captured_at": "UNKNOWN",
                "rights": "UNKNOWN",
                "intended_use": "research_reference",
                "source_kind": "original_source_evidence",
                "content_origin": {
                    "kind": "publisher-material",
                    "claim_type": "source_statement",
                },
            },
        }
        content_evidence_id = store.record_evidence(
            connection=con,
            source="isolated-test-approved-source",
            project="LUMENIS",
            product="ZBMP",
            feature_id="BMP_APPROVED_SOURCE_CONTENT_FIXTURE",
            asset_id=source_id,
            version="bmp-source-content:test-v1",
            test_name="bmp-approved-source-content-fixture",
            result="PASS",
            status="verified",
            inputs={"source_ids": [source_id]},
            outputs={"source_artifact_ref": artifact["artifact_id"]},
            raw_content=body,
            collection_metadata=metadata,
            domain_id=scope["domain_id"],
            subject_id=None,
            brand_focus_id=scope["brand_focus_id"],
            global_scope=False,
        )
        con.execute(
            "UPDATE lumenis_shared_artifacts SET evidence_id=? WHERE artifact_id=?",
            (str(content_evidence_id), artifact["artifact_id"]),
        )
        content_locator = f"app_evidence_records:{content_evidence_id}"
        scope_locator = f"app_evidence_records:{scope_evidence_id}"
        persist_canonical(con, CanonicalRecord(
            canonical_id=canonical_id,
            product_id="ZBMP",
            domain_id="zbmp",
            brand_focus_id=scope["brand_focus_id"],
            scope_status="VERIFIED",
            scope_evidence_ref=str(scope_evidence_id),
            source_id=source_id,
            external_id=source_id,
            source_type="collected_note",
            source_table="app_evidence_records",
            title="Disposable BMP approved-source fixture",
            content=body,
            url=source_url,
            canonical_url=source_url,
            source_platform="UNKNOWN",
            publish_datetime="",
            captured_at="",
            raw_ref=json.dumps({
                "source_id": source_id,
                "scope_evidence_ref": scope_locator,
                "content_evidence_ref": content_locator,
                "source_artifact_ref": artifact["artifact_id"],
            }, ensure_ascii=False, sort_keys=True),
        ))

    expected_signed_scope = store._normalize_record_evidence_scope(
        product="ZBMP",
        domain_id=scope["domain_id"],
        subject_id=None,
        brand_focus_id=scope["brand_focus_id"],
        global_scope=False,
    )
    for evidence_id in (scope_evidence_id, content_evidence_id):
        evidence = dict(workspace["repo"].query_one(
            "SELECT * FROM app_evidence_records WHERE id=?", (evidence_id,),
        ))
        assert store.verify_evidence_record_integrity(evidence)
        assert "brand_focus_id" not in evidence
        assert json.loads(evidence["inputs_json"])["_lumenis_scope"] == expected_signed_scope

    return {
        "source_id": source_id,
        "canonical_id": canonical_id,
        "source_url": source_url,
        "body": body,
        "body_sha256": body_sha256,
        "scope_evidence_id": scope_evidence_id,
        "scope_locator": scope_locator,
        "content_evidence_id": content_evidence_id,
        "content_locator": content_locator,
        "artifact": artifact,
        "artifact_path": artifact_path,
        "scope": scope,
    }


def test_bmp_signed_parent_source_scope_projects_through_saved_work_and_business_brief(
    workspace, monkeypatch,
):
    from lumenis.importer import documents
    from lumenis.shared.reporting import business_brief, operational_brief
    from lumenis.system.security.permission import OperationType

    source = _seed_bmp_original_source_evidence(workspace)
    entry = {
        "receipt_id": "PO-20261011-APPROVED-INTERNAL-SOURCE-USE",
        "source_id": source["source_id"],
        "source_url": source["source_url"],
        "canonical_id": source["canonical_id"],
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": source["scope"]["brand_focus_id"],
        "scope_evidence_ref": source["scope_locator"],
        "content_evidence_ref": source["content_locator"],
        "body_sha256": source["body_sha256"],
        "snapshot_kind": "existing_source_evidence_snapshot",
        "allowed_purposes": ["internal_research", "short_quote", "bmp_brief"],
        "allowed_operations": ["derive_reference", "read", "save", "revise", "reopen"],
        "rights_state": "UNKNOWN",
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }
    receipt = {
        "schema": "lumenis.po-approval-receipt/v1",
        "source_use_schema": "lumenis.approved-internal-source-use/v1",
        "approval_id": entry["receipt_id"],
        "approval_source_type": "direct_product_owner_instruction",
        "approved_by": "Product Owner",
        "approved_at": "2026-10-11",
        "status": "APPROVED",
        "receipt_id": entry["receipt_id"],
        "constraints": ["test-only isolated tmp_path fixture"],
        "scope_manifest": {"source_id": source["source_id"]},
        "sources": [entry],
    }

    def load_test_receipt(receipt_id):
        assert receipt_id == receipt["receipt_id"]
        return receipt

    monkeypatch.setattr(permission, "_load_source_use_receipt", load_test_receipt)

    assert source["artifact_path"].read_bytes() == source["body"].encode("utf-8")
    with workspace["repo"].connection() as con:
        canonical, raw_ref, body = documents._approved_source_canonical(con, entry)
    assert canonical["canonical_id"] == source["canonical_id"]
    assert raw_ref["content_evidence_ref"] == source["content_locator"]
    assert body == source["body"]

    _confirm_approved_source_reference(workspace, source, "bmp-approved-source-derive-v1")
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"],
        canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"],
        request_id="bmp-approved-source-derive-v1",
        actor=workspace["actor"],
        scope=source["scope"],
    )
    derived_ref = f"app_evidence_records:{derived['evidence_id']}"

    with workspace["repo"].connection() as con:
        row_cursor = con.execute(
            "SELECT * FROM canonical_data WHERE canonical_id=?", (source["canonical_id"],),
        )
        row = dict(zip((column[0] for column in row_cursor.description), row_cursor.fetchone()))
        projected_ref = operational_brief._content_evidence_ref(
            con, row, row["scope_evidence_ref"],
        )
    assert projected_ref == derived_ref

    material = {
        "scope": source["scope"],
        "sources": [{
            "source_id": source["source_id"],
            "canonical_id": source["canonical_id"],
            "evidence_ref": str(source["scope_evidence_id"]),
            "content_evidence_ref": projected_ref,
            "source_scope_locator": source["scope_locator"],
            "source_content_locator": source["content_locator"],
            "body_sha256": source["body_sha256"],
            "text": source["body"],
            "text_selection": {
                "method": "fixture_full_text",
                "start": 0,
                "end": len(source["body"]),
            },
            "publish_datetime": None,
            "captured_at": None,
            "source_platform": "UNKNOWN",
        }],
    }
    with workspace["repo"].connection() as con:
        bindings = business_brief._source_use_material(
            material, workspace["actor"], connection=con,
        )
    assert len(bindings) == 1
    assert bindings[0]["source_id"] == source["source_id"]
    assert bindings[0]["evidence_ref"] == derived_ref
    assert bindings[0]["rights"] == "UNKNOWN"

    quote = "品牌范围、引用修订"
    start = source["body"].index(quote)
    located = workspace["documents"].locate_quote(
        derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
        start=start, end=start + len(quote),
    )
    assert located["citation"]["quote"] == quote
    save_args = {
        "title": "BMP signed source scope continuity regression",
        "markdown": f"内部回归引用：{quote}",
        "kind": "research",
        "payload": {"source_id": source["source_id"]},
        "citations": [located["citation"]],
        "request_id": "bmp-approved-source-saved-work-v1",
        "work_id": None,
        "previous_artifact_id": None,
        "expected_draft_digest": None,
        "actor": workspace["actor"],
        "scope": source["scope"],
    }
    first_resource = workspace["work"].work_write_resource(**save_args)
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=first_resource,
        granted_by="isolated-bmp-approved-source-reference-test",
    )
    first = workspace["work"].save_work(**save_args)
    first_artifact_id = first["artifact"]["artifact_id"]

    revise_args = {
        **save_args,
        "markdown": f"修订后仍引用：{quote}",
        "request_id": "bmp-approved-source-saved-work-v2",
        "work_id": first["document"]["work_id"],
        "previous_artifact_id": first_artifact_id,
        "expected_draft_digest": first["document"]["draft_digest"],
    }
    revise_resource = workspace["work"].work_write_resource(**revise_args)
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=revise_resource,
        granted_by="isolated-bmp-approved-source-reference-test",
    )
    second = workspace["work"].save_work(**revise_args)
    assert second["document"]["version"] == 2
    second_artifact_id = second["artifact"]["artifact_id"]

    for artifact_id, expected_version in (
        (first_artifact_id, 1), (second_artifact_id, 2),
    ):
        reopened = workspace["work"].reopen_work(
            artifact_id, actor=workspace["actor"], scope=source["scope"],
        )
        assert reopened["document"]["version"] == expected_version
        assert reopened["receipt"]["sources"][0]["source_id"] == source["source_id"]

    reopened_source = workspace["documents"].reopen_imported_source(
        derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
    )
    assert reopened_source["content"] == source["body"].encode("utf-8")
    assert bindings[0]["source_artifact_ref"] == reopened_source["artifact_ref"]
    source_export_resource = "document-source-read:v1:" + reopened_source["sha256"]
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=source_export_resource,
        granted_by="isolated-bmp-approved-source-reference-test",
    )
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        workspace["documents"].reopen_imported_source(
            derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
            _source_use_operation="export",
        )

    saved_export_resource = "saved-work-export:v1:" + workspace["work"]._digest({
        "id": second_artifact_id,
        "sha256": second["artifact"]["sha256"],
        "format": "json",
    })
    workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=saved_export_resource,
        granted_by="isolated-bmp-approved-source-reference-test",
    )
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        workspace["work"].export_work(
            second_artifact_id, actor=workspace["actor"], scope=source["scope"],
        )


def test_prepare_approved_source_reference_is_read_only_and_issues_no_grant(
    workspace, monkeypatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    database_before = _approved_source_database_snapshot(workspace)
    source_before = _approved_source_state_snapshot(workspace, source)
    effects_before = _approved_source_effect_snapshot(workspace)

    prepared = _prepare_approved_source_reference(
        workspace, source, "approved-source-prepare-readonly-v2",
    )

    assert prepared["prepared"] is True
    assert prepared["resource"] == (
        "approved-internal-source-reference:v2:" + prepared["descriptor_sha256"]
    )
    assert _approved_source_database_snapshot(workspace) == database_before
    assert _approved_source_state_snapshot(workspace, source) == source_before
    assert _approved_source_effect_snapshot(workspace) == effects_before


def test_approved_source_reference_final_fence_denies_confirmation_revoked_after_staging(
    workspace, monkeypatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    confirmation = _confirm_approved_source_reference(
        workspace, source, "approved-source-final-confirmation-revocation-v2",
    )
    database_before = _approved_source_database_snapshot(workspace)
    source_before = _approved_source_state_snapshot(workspace, source)
    stage_source = workspace["documents"]._stage_bytes
    revocations = []

    def revoke_after_real_staging(*args, **kwargs):
        staged = stage_source(*args, **kwargs)
        revocations.append(permission.confirm_approved_source_reference_confirmation(
            actor=workspace["actor"], scope=source["scope"],
            confirmation_id=confirmation["confirmation_id"], confirmed=False,
            gate=workspace["gate"],
        ))
        return staged

    monkeypatch.setattr(workspace["documents"], "_stage_bytes", revoke_after_real_staging)

    with pytest.raises(ValueError, match="WORK_EFFECT_PERMISSION_DENIED"):
        workspace["documents"].create_approved_source_reference(
            source_id=source["source_id"], canonical_id=source["canonical_id"],
            expected_body_sha256=source["body_sha256"],
            request_id="approved-source-final-confirmation-revocation-v2",
            actor=workspace["actor"], scope=source["scope"],
        )

    assert len(revocations) == 1
    assert revocations[0]["allowed"] is False
    assert revocations[0]["code"] == "APPROVED_SOURCE_REFERENCE_CONFIRMATION_CANCELLED"
    assert _approved_source_database_snapshot(workspace) == database_before
    assert _approved_source_state_snapshot(workspace, source) == source_before


def test_approved_source_reference_descriptor_binds_request_and_real_account_actor(
    workspace, monkeypatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    account_actor = _seed_active_admin_account(workspace)

    first = _prepare_approved_source_reference(
        workspace, source, "approved-source-actor-binding-one-v2",
    )
    different_request = _prepare_approved_source_reference(
        workspace, source, "approved-source-actor-binding-two-v2",
    )
    different_actor = _prepare_approved_source_reference(
        workspace, source, "approved-source-actor-binding-one-v2", actor=account_actor,
    )

    assert first["context"]["principal_kind"] == "local_workspace"
    assert first["context"]["principal_ref"] == "workspace:local"
    assert different_actor["context"]["actor_id"] == account_actor["id"]
    assert different_request["request_id"] != first["request_id"]
    assert len({
        first["descriptor_sha256"],
        different_request["descriptor_sha256"],
        different_actor["descriptor_sha256"],
    }) == 3
    assert len({first["resource"], different_request["resource"], different_actor["resource"]}) == 3


@pytest.mark.parametrize(
    ("tamper", "expected_error"),
    [
        ("wrong_scope", "SOURCE_USE_SCOPE_OR_CONTENT_MISMATCH"),
        ("wrong_body_hash", "SOURCE_USE_SCOPE_OR_CONTENT_MISMATCH"),
        ("removed_receipt", "SOURCE_USE_SOURCE_NOT_APPROVED"),
    ],
)
def test_prepare_approved_source_reference_rejects_changed_scope_content_or_receipt(
    workspace, monkeypatch, tamper, expected_error,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    actor = workspace["actor"]
    scope = source["scope"]
    expected_body_sha256 = source["body_sha256"]

    if tamper == "wrong_scope":
        import subject_registry

        other_subject, _ = subject_registry.add_subject({
            "domain_id": "CTH",
            "subject_type": "company",
            "name_en": "Different Registered Source Scope",
            "name_zh": "不同的已注册来源范围",
        })
        scope = {**source["scope"], "subject_id": other_subject["subject_id"]}
    elif tamper == "wrong_body_hash":
        expected_body_sha256 = "0" * 64
    else:
        monkeypatch.setattr(permission, "_load_source_use_receipt", lambda _receipt_id: {
            "sources": [],
        })

    with pytest.raises(ValueError, match=expected_error):
        workspace["documents"].prepare_approved_source_reference(
            source_id=source["source_id"], canonical_id=source["canonical_id"],
            expected_body_sha256=expected_body_sha256,
            request_id=f"approved-source-prepare-reject-{tamper}-v2",
            actor=actor, scope=scope,
        )


@pytest.mark.parametrize("grant_mismatch", ["legacy_v1", "request_id", "principal"])
def test_approved_source_reference_requires_exact_v2_request_grant(
    workspace, monkeypatch, grant_mismatch,
):
    source = _seed_approved_internal_source_canonical(workspace, monkeypatch)
    from lumenis.system.security.permission import OperationType

    if grant_mismatch == "legacy_v1":
        granted_resource = "approved-internal-source-reference:v1:" + hashlib.sha256(
            f"{source['source_id']}\n{source['body_sha256']}".encode("utf-8")
        ).hexdigest()
        request_id = "approved-source-legacy-grant-denied-v2"
        actor = workspace["actor"]
    elif grant_mismatch == "request_id":
        request_id = "approved-source-request-ungranted-v2"
        granted_resource = _prepare_approved_source_reference(
            workspace, source, "approved-source-request-grant-other-v2",
        )["resource"]
        actor = workspace["actor"]
    else:
        request_id = "approved-source-principal-ungranted-v2"
        granted_resource = _prepare_approved_source_reference(
            workspace, source, request_id,
        )["resource"]
        actor = _seed_active_admin_account(workspace)

    workspace["gate"].grant_approval(
        OperationType.DATA_IMPORT.value,
        resource=granted_resource,
        granted_by="isolated-approved-source-reference-test",
    )
    database_before = _approved_source_database_snapshot(workspace)
    source_before = _approved_source_state_snapshot(workspace, source)
    effects_before = _approved_source_effect_snapshot(workspace)

    with pytest.raises(ValueError, match="WORK_EFFECT_PERMISSION_DENIED"):
        workspace["documents"].create_approved_source_reference(
            source_id=source["source_id"], canonical_id=source["canonical_id"],
            expected_body_sha256=source["body_sha256"], request_id=request_id,
            actor=actor, scope=source["scope"],
        )

    assert _approved_source_database_snapshot(workspace) == database_before
    assert _approved_source_state_snapshot(workspace, source) == source_before
    assert _approved_source_effect_snapshot(workspace) == effects_before

def _prepare_approved_focal_bmp_source_for_global_work(workspace, monkeypatch, request_id):
    """Seed a focal BMP source and derive it through the real SourceUse path."""
    source = _seed_bmp_original_source_evidence(workspace)
    entry = {
        "receipt_id": "PO-20261011-APPROVED-INTERNAL-SOURCE-USE",
        "source_id": source["source_id"],
        "source_url": source["source_url"],
        "canonical_id": source["canonical_id"],
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": source["scope"]["brand_focus_id"],
        "scope_evidence_ref": source["scope_locator"],
        "content_evidence_ref": source["content_locator"],
        "body_sha256": source["body_sha256"],
        "snapshot_kind": "existing_source_evidence_snapshot",
        "allowed_purposes": ["internal_research", "short_quote", "bmp_brief"],
        "allowed_operations": ["derive_reference", "read", "save", "revise", "reopen"],
        "rights_state": "UNKNOWN",
        "commercial_state": "UNKNOWN",
        "publication_state": "NOT_APPROVED",
        "training_state": "NOT_APPROVED",
    }
    receipt = {
        "schema": "lumenis.po-approval-receipt/v1",
        "source_use_schema": "lumenis.approved-internal-source-use/v1",
        "approval_id": entry["receipt_id"],
        "approval_source_type": "direct_product_owner_instruction",
        "approved_by": "Product Owner",
        "approved_at": "2026-10-11",
        "status": "APPROVED",
        "receipt_id": entry["receipt_id"],
        "constraints": ["test-only isolated tmp_path fixture"],
        "scope_manifest": {"source_id": source["source_id"]},
        "sources": [entry],
    }

    def load_test_receipt(receipt_id):
        assert receipt_id == receipt["receipt_id"]
        return receipt

    # Only the exact PO receipt bytes are synthetic. Permission validation,
    # current Canonical resolution, source confirmation, and derivation remain real.
    monkeypatch.setattr(permission, "_load_source_use_receipt", load_test_receipt)
    _confirm_approved_source_reference(workspace, source, request_id)
    derived = workspace["documents"].create_approved_source_reference(
        source_id=source["source_id"], canonical_id=source["canonical_id"],
        expected_body_sha256=source["body_sha256"], request_id=request_id,
        actor=workspace["actor"], scope=source["scope"],
    )
    quote = "品牌范围、引用修订"
    start = source["body"].index(quote)
    located = workspace["documents"].locate_quote(
        derived["evidence_id"], actor=workspace["actor"], scope=source["scope"],
        start=start, end=start + len(quote),
    )
    global_scope = {
        "domain_id": "zbmp", "subject_id": None, "brand_focus_id": None,
        "global_scope": True,
    }
    return {
        "source": source,
        "receipt": receipt,
        "derived": derived,
        "citation": located["citation"],
        "quote": quote,
        "global_scope": global_scope,
    }


def _save_approved_focal_source_in_global_work(workspace, source_case, request_id):
    from lumenis.system.security.permission import OperationType

    global_scope = source_case["global_scope"]
    global_workspace = {**workspace, "scope": global_scope}
    save_args = {
        "title": "Approved focal BMP source in GLOBAL work regression",
        "markdown": f"Internal regression citation: {source_case['quote']}",
        "kind": "research",
        "payload": {"source_id": source_case["source"]["source_id"]},
        "citations": [source_case["citation"]],
        "request_id": request_id,
        "work_id": None,
        "previous_artifact_id": None,
        "expected_draft_digest": None,
        "actor": global_workspace["actor"],
        "scope": global_workspace["scope"],
    }
    resource = global_workspace["work"].work_write_resource(**save_args)
    global_workspace["gate"].grant_approval(
        OperationType.DATA_EXPORT.value,
        resource=resource,
        granted_by="isolated-approved-focal-source-global-work-test",
    )
    return global_workspace["work"].save_work(**save_args), global_workspace


def _global_saved_work_bytes_and_rows(workspace, saved):
    work_id = saved["document"]["work_id"]
    with workspace["repo"].connection(read_only=True, wal=False) as con:
        rows = con.execute(
            "SELECT * FROM lumenis_shared_artifacts "
            "WHERE kind='saved_document' AND source_execution_id=? ORDER BY artifact_id",
            (work_id,),
        ).fetchall()
        snapshot = []
        for row in rows:
            record = dict(row)
            path = workspace["root"] / "artifacts" / record["relative_path"]
            snapshot.append((tuple(row), path.read_bytes()))
    return snapshot


def test_approved_focal_bmp_source_saves_and_reopens_in_global_work(workspace, monkeypatch):
    source_case = _prepare_approved_focal_bmp_source_for_global_work(
        workspace, monkeypatch, "approved-focal-bmp-global-source-v1",
    )
    saved, global_workspace = _save_approved_focal_source_in_global_work(
        workspace, source_case, "approved-focal-bmp-global-work-v1",
    )
    artifact_snapshot = _global_saved_work_bytes_and_rows(workspace, saved)
    global_scope = global_workspace["scope"]
    original_scope = source_case["source"]["scope"]

    assert saved["return_ref"]["scope"] == global_scope
    assert saved["document"]["context"]["domain_id"] == "zbmp"
    assert saved["document"]["context"]["global_scope"] is True
    assert saved["document"]["citations"][0]["source_scope"] == original_scope
    assert saved["receipt"]["scope"] == global_scope
    assert saved["receipt"]["sources"][0]["scope"] == original_scope

    reopened = global_workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"], actor=workspace["actor"], scope=global_scope,
    )
    assert reopened["return_ref"]["scope"] == global_scope
    assert reopened["document"]["citations"][0]["source_scope"] == original_scope
    assert reopened["receipt"]["sources"][0]["scope"] == original_scope

    # Approved internal SourceUse still forbids report export, without an export grant.
    with pytest.raises(ValueError, match="SOURCE_USE_PURPOSE_NOT_ALLOWED"):
        global_workspace["work"].export_work(
            saved["artifact"]["artifact_id"], actor=workspace["actor"],
            scope=global_scope, format="json",
        )
    assert _global_saved_work_bytes_and_rows(workspace, saved) == artifact_snapshot


@pytest.mark.parametrize(
    ("withdrawal", "expected_error"),
    [
        ("brand_focus_disabled", "WORK_PERMISSION_DENIED"),
        ("receipt_removed", "SOURCE_USE_SOURCE_NOT_APPROVED"),
        ("canonical_body_changed", "SOURCE_USE_SOURCE_REFERENCE_CHANGED"),
    ],
    ids=["focus-read-revoked", "source-use-receipt-removed", "canonical-body-hash-changed"],
)
def test_global_saved_work_rechecks_focal_source_and_keeps_committed_bytes(
    workspace, monkeypatch, withdrawal, expected_error,
):
    source_case = _prepare_approved_focal_bmp_source_for_global_work(
        workspace, monkeypatch, f"approved-focal-bmp-global-control-{withdrawal}-v1",
    )
    saved, global_workspace = _save_approved_focal_source_in_global_work(
        workspace, source_case, f"approved-focal-bmp-global-work-{withdrawal}-v1",
    )
    artifact_snapshot = _global_saved_work_bytes_and_rows(workspace, saved)
    source = source_case["source"]

    if withdrawal == "brand_focus_disabled":
        import subject_registry

        with workspace["repo"].transaction() as con:
            updated = con.execute(
                f"UPDATE {subject_registry.TABLE_NAME} SET status='inactive' WHERE brand_focus_id=?",
                (source["scope"]["brand_focus_id"],),
            )
            assert updated.rowcount == 1
    elif withdrawal == "receipt_removed":
        source_case["receipt"]["sources"] = []
    else:
        with workspace["repo"].transaction() as con:
            updated = con.execute(
                "UPDATE canonical_data SET content=? WHERE canonical_id=?",
                (source["body"] + " synthetic canonical body tamper", source["canonical_id"]),
            )
            assert updated.rowcount == 1

    with pytest.raises(ValueError, match=expected_error):
        global_workspace["work"].reopen_work(
            saved["artifact"]["artifact_id"], actor=workspace["actor"],
            scope=global_workspace["scope"],
        )
    # A denied source or disallowed SourceUse export returns no report bytes.
    expected_export_error = (
        "WORK_PERMISSION_DENIED"
        if withdrawal == "brand_focus_disabled" else "SOURCE_USE_PURPOSE_NOT_ALLOWED"
    )
    with pytest.raises(ValueError, match=expected_export_error):
        global_workspace["work"].export_work(
            saved["artifact"]["artifact_id"], actor=workspace["actor"],
            scope=global_workspace["scope"], format="json",
        )
    assert _global_saved_work_bytes_and_rows(workspace, saved) == artifact_snapshot
