"""Private KOS operations retain exact identity/scope, immutable versions and no external effects."""
import pytest
from tests.test_saved_document_workflow import workspace


def test_private_ledger_versions_scope_replay_and_tamper(workspace):
    import kos_ops
    ws = workspace
    scope = {"domain_id": "zbmp", "subject_id": None, "brand_focus_id": "BRAND-PRIVATE", "global_scope": False}
    import subject_registry
    with ws["repo"].transaction() as con:
        subject_registry.ensure_schema(con)
        con.execute("""INSERT INTO lumenis_subject_registry
            (subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh,
             name_en_norm, name_zh_norm, created_at, updated_at, status)
            VALUES ('TEST-SUBJECT', 'BRAND-PRIVATE', 'BMP', 'brand', 'Private', '测试',
                    'private', '测试', 'now', 'now', 'active')""")
    args = dict(actor=ws["actor"], scope=scope, author_id="manual-prospect", operation="lead", payload={"contact_name": "Synthetic person"}, request_id="private-lead-001")
    with pytest.raises(kos_ops.ScopedOperationApprovalRequired) as required:
        kos_ops.write_scoped_operation(**args)
    ws["gate"].grant_approval("db_write", resource=required.value.resource, granted_by="isolated-test-user")
    first = kos_ops.write_scoped_operation(**args)
    assert first["operation"]["version"] == 1
    assert first["external_effect"] == "not_performed"
    assert kos_ops.write_scoped_operation(**args)["replayed"]
    read = kos_ops.read_scoped_operations(actor=ws["actor"], scope=scope, author_id="manual-prospect")
    assert read["items"][0]["payload"] == {"contact_name": "Synthetic person"}
    stale = {**args, "request_id": "private-lead-002"}
    ws["gate"].grant_approval("db_write", resource=kos_ops.scoped_operation_resource(**stale), granted_by="isolated-test-user")
    with pytest.raises(ValueError, match="VERSION_CONFLICT"):
        kos_ops.write_scoped_operation(**stale)
    revision = {**args, "request_id": "private-lead-003", "expected_version": 1, "payload": {"contact_name": "Revised synthetic"}}
    ws["gate"].grant_approval("db_write", resource=kos_ops.scoped_operation_resource(**revision), granted_by="isolated-test-user")
    second = kos_ops.write_scoped_operation(**revision)
    assert second["operation"]["parent_sha256"] == first["operation"]["sha256"]
    assert second["operation"]["version"] == 2
    with ws["repo"].transaction() as con:
        con.execute("UPDATE kos_operations SET note=replace(note, 'Revised synthetic', 'Tampered synthetic') WHERE action='scoped_lead' AND note LIKE '%private-lead-003%'")
    with pytest.raises(ValueError, match="INTEGRITY_FAILED"):
        kos_ops.read_scoped_operations(actor=ws["actor"], scope=scope)


def test_scope_revocation_and_remote_transport_deny_without_write(workspace):
    import kos_ops
    import subject_registry
    ws = workspace
    with ws["repo"].transaction() as con:
        subject_registry.ensure_schema(con)
        for index in (1, 2):
            con.execute("""INSERT INTO lumenis_subject_registry
                (subject_id, brand_focus_id, domain_id, subject_type, name_en, name_zh,
                 name_en_norm, name_zh_norm, created_at, updated_at, status)
                VALUES (?, ?, 'BMP', 'brand', ?, ?, ?, ?, 'now', 'now', 'active')""",
                (f"S{index}", f"B{index}", f"Brand{index}", f"品牌{index}", f"brand{index}", f"品牌{index}"))
    scope = {"domain_id": "zbmp", "subject_id": None, "brand_focus_id": "B1", "global_scope": False}
    args = dict(actor=ws["actor"], scope=scope, author_id="same-author", operation="lead", payload={"contact_name": "Private B1"}, request_id="scope-private-001")
    resource = kos_ops.scoped_operation_resource(**args)
    token = ws["gate"].grant_approval("db_write", resource=resource, granted_by="isolated-test-user")
    kos_ops.write_scoped_operation(**args)
    assert not kos_ops.read_scoped_operations(actor=ws["actor"], scope={**scope, "brand_focus_id": "B2"})["items"]
    ws["gate"].revoke_approval(token)
    with pytest.raises(kos_ops.ScopedOperationApprovalRequired):
        kos_ops.write_scoped_operation(**args)
    with ws["app"].test_request_context("/", environ_overrides={"REMOTE_ADDR": "203.0.113.10"}):
        with pytest.raises(ValueError, match="PERMISSION_DENIED"):
            kos_ops.read_scoped_operations(actor=ws["actor"], scope=scope)
    with ws["repo"].transaction() as con:
        con.execute("UPDATE lumenis_subject_registry SET status='inactive' WHERE brand_focus_id='B1'")
    with pytest.raises(ValueError, match="PERMISSION_DENIED"):
        kos_ops.read_scoped_operations(actor=ws["actor"], scope=scope)
