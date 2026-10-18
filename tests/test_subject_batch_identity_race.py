"""Isolated simulation of a second writer between batch conflict read and insert."""

from tests.test_saved_document_workflow import workspace


def test_batch_one_name_conflict_between_read_and_write(workspace, monkeypatch):
    import subject_registry as registry
    from lumenis.system.security.permission import PermissionLevel

    ws = workspace
    with ws["repo"].transaction() as con:
        registry.ensure_schema(con)
    ws["gate"].grant_permission(PermissionLevel.HUMAN_APPROVAL)
    ws["app"].register_blueprint(registry.subject_registry_bp)
    entries = [
        {
            "baseline_id": "synthetic-race",
            "identity": {
                "domain_id": "BMP",
                "subject_type": "brand",
                "name_en": "Synthetic collision",
                "name_zh": "原名",
                "industry": "test",
                "keywords": [],
            },
        }
    ]
    client = ws["app"].test_client()
    preview = client.post(
        "/api/settings/subjects/batch", json={"entries": entries, "mode": "prepare"}
    ).get_json()
    assert preview["ok"], preview
    original = registry.add_subject
    called = False

    def interleaved(identity, **kwargs):
        nonlocal called
        if not called:
            called = True
            original({**identity, "name_zh": "并发异名"})
        return original(identity, **kwargs)

    monkeypatch.setattr(registry, "add_subject", interleaved)
    reply = client.post(
        "/api/settings/subjects/batch",
        json={
            "entries": entries,
            "mode": "apply",
            "confirm": True,
            "confirmed_resource": preview["resource"],
        },
    ).get_json()
    assert reply["ok"], reply
    assert reply["results"][0]["status"] == "IDENTITY_CONFLICT", reply
    rows = registry.list_subjects("BMP")
    assert len([r for r in rows if r["name_en"] == "Synthetic collision"]) == 1
