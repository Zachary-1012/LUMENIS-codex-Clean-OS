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
    omit_child_parent_ref=False,
):
    """Create test-only signed Collection and source Evidence plus the original Artifact bytes."""
    from_scope = workspace["scope"]
    context = workspace["work"].authorize(workspace["actor"], from_scope, action="read")
    owner = {key: value for key, value in context.items()
             if key not in {"domain_id", "subject_id", "brand_focus_id", "global_scope"}}
    body = _BODY
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
            inputs={"source_ids": [_SOURCE_ID], **({} if omit_child_parent_ref else {"collection_evidence_ref": parent_ref})},
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


@pytest.mark.parametrize('tamper', ['body','block_map','original_resource_sha256','artifact_bytes','quote','actorless'])
def test_browser_snapshot_citation_subset_and_tampering(workspace,monkeypatch,tamper):
    from tests.test_browser_extract_saved_work import _admitted_snapshot,_approve_source_use
    from lumenis.shared.reporting import saved_work
    from lumenis.importer.documents import _source_bytes
    ws=workspace;obj,cap,args,source,token=_admitted_snapshot(ws,monkeypatch)
    _approve_source_use(ws,source)
    if tamper=='quote':
        with pytest.raises(ValueError,match='WORK_CITATION_UNGROUNDED'):
            saved_work.save_work(title='Forged quote',kind='research',markdown='FORGED',payload={},
                citations=[{'evidence_id':source['evidence_id'],'start':0,'end':6,'quote':'FORGED'}],
                request_id='browser-forged-quote-0001',actor=ws['actor'],scope=ws['scope'])
        return
    with ws['repo'].connection() as con:
        evidence=dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?',(source['evidence_id'],)).fetchone())
        evidence['provenance']=json.loads(evidence['collection_metadata'])
        if tamper=='actorless':
            with pytest.raises(ValueError,match='CURRENT_ACTOR_REQUIRED'):
                saved_work._verified_evidence(con,source['evidence_id'],evidence['provenance']['context'])
            return
        raw,record=_source_bytes(con,evidence)
    import shared_artifacts
    path=shared_artifacts.artifact_root()/record['relative_path']
    value=json.loads(raw)
    if tamper=='artifact_bytes':
        path.write_bytes(raw+b' ')
    else:
        if tamper=='body': value['body']='forged body'
        elif tamper=='block_map': value['block_map'][0]['end']+=1
        else:value['original_resource_sha256']='a'*64
        changed=_json_bytes(value)
        path.write_bytes(changed)
        # Even a re-signed artifact/metadata claim cannot bypass snapshot projection validation.
        with ws['repo'].transaction() as con:
            digest=hashlib.sha256(changed).hexdigest()
            meta=evidence['provenance'];meta['source_fingerprint']=digest
            con.execute('UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?',
                (digest,len(changed),record['artifact_id']))
            con.execute('UPDATE app_evidence_records SET collection_metadata=? WHERE id=?',
                (json.dumps(meta),source['evidence_id']))
            store._sign_evidence_record(con,source['evidence_id'])
    with pytest.raises(ValueError):
        ws['documents'].locate_quote(source['evidence_id'],actor=ws['actor'],scope=ws['scope'],start=0,end=1)


def test_signed_native_fixture_without_child_parent_link_is_rejected(workspace):
    source = _seed_collected_source(workspace, omit_child_parent_ref=True)
    before = _snapshot(workspace, source)
    with pytest.raises(workspace["work"].SavedWorkError, match="COLLECTED_SOURCE_PARENT_INVALID"):
        workspace["documents"].locate_quote(source["evidence_id"], actor=workspace["actor"],
            scope=workspace["scope"], start=0, end=2)
    assert _snapshot(workspace, source) == before
