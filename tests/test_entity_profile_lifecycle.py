import copy, hashlib
import pytest
from tests.test_saved_document_workflow import workspace


def _register(ws):
    import subject_registry

    with ws["repo"].transaction() as con:
        subject_registry.ensure_schema(con)
    subject, _ = subject_registry.add_subject(
        {
            "domain_id": "BMP",
            "subject_type": "brand",
            "name_en": "Synthetic profile entity",
            "name_zh": "合成资料实体",
            "industry": "test",
            "keywords": [],
        }
    )
    return {
        "domain_id": "zbmp",
        "subject_id": None,
        "brand_focus_id": subject["brand_focus_id"],
        "global_scope": False,
    }


def _manifest(scope):
    text = "Synthetic profile entity official research page"
    return {
        "schema": "lumenis.entity-profile-assertions/v1",
        "entity": scope,
        "request_id": "profile-import-0001",
        "version": 1,
        "parent_sha256": None,
        "imported_at": "2026-10-17T04:47:00Z",
        "sources": [
            {
                "id": "source-1",
                "source_url": "https://example.com/synthetic",
                "capture_method": "ASSISTED_WEB_TOOL_TEXT_EXTRACT",
                "reviewed_on": "2026-10-17",
                "origin_captured_at": None,
                "extract_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "excerpt": text,
                "excerpt_sha256": hashlib.sha256(text.encode()).hexdigest(),
                "source_range": {
                    "unit": "extracted-page-text",
                    "start": 0,
                    "end": len(text),
                },
                "rights": "UNKNOWN",
            }
        ],
        "assertions": [
            {
                "id": "a1",
                "field": "official_site",
                "value": "https://example.com/synthetic",
                "source_id": "source-1",
                "claim_type": "source_statement",
            }
        ],
        "review": {},
    }


def test_profile_admission_versions_review_conflict_reopen_and_revocation(workspace):
    from lumenis.importer import entity_profiles as profiles

    ws = workspace
    scope = _register(ws)
    manifest = _manifest(scope)
    kwargs = dict(actor=ws["actor"], scope=scope)
    prepared = profiles.prepare_profile(manifest, **kwargs)
    with pytest.raises(ValueError, match="WORK_EFFECT_PERMISSION_DENIED"):
        profiles.import_profile(manifest, **kwargs)
    token = ws["gate"].grant_approval(
        "data_import",
        resource=prepared["resource"],
        granted_by="synthetic-explicit-approval",
    )
    first = profiles.import_profile(manifest, **kwargs)
    assert profiles.import_profile(manifest, **kwargs)["replayed"]
    current = profiles.read_profiles(**kwargs)
    assert current["current"]["evidence_id"] == first["evidence_id"]
    assert current["adopted_fields"]["official_site"] is None
    second = copy.deepcopy(manifest)
    second.update(
        version=2,
        parent_sha256=current["current"]["sha256"],
        request_id="profile-import-0002",
    )
    second["assertions"].append(
        {
            "id": "a2",
            "field": "official_site",
            "value": "https://example.com/alternative",
            "source_id": "source-1",
            "claim_type": "source_statement",
        }
    )
    second["review"] = {"official_site": "a1"}
    approval = profiles.prepare_profile(second, **kwargs)
    ws["gate"].grant_approval(
        "data_import", resource=approval["resource"], granted_by="synthetic-review"
    )
    profiles.import_profile(second, **kwargs)
    reread = profiles.read_profiles(**kwargs)
    assert len(reread["versions"]) == 2 and reread["conflicts"]
    assert (
        reread["adopted_fields"]["official_site"]["state"]
        == "REVIEW_ADOPTED_SOURCE_STATEMENT"
    )
    assert reread["training_eligible"] is False and reread["source_rights"] == "UNKNOWN"
    stale = copy.deepcopy(second)
    stale["request_id"] = "profile-import-stale"
    approval = profiles.prepare_profile(stale, **kwargs)
    ws["gate"].grant_approval(
        "data_import", resource=approval["resource"], granted_by="synthetic"
    )
    with pytest.raises(ValueError, match="VERSION_CONFLICT"):
        profiles.import_profile(stale, **kwargs)
    ws["gate"].revoke_approval(token)
    with pytest.raises(ValueError, match="WORK_EFFECT_PERMISSION_DENIED"):
        profiles.import_profile(manifest, **kwargs)


def test_profile_cannot_change_scope_or_forge_bytes(workspace):
    from lumenis.importer import entity_profiles as profiles
    import subject_registry

    ws = workspace
    scope = _register(ws)
    manifest = _manifest(scope)
    other, _ = subject_registry.add_subject(
        {
            "domain_id": "BMP",
            "subject_type": "brand",
            "name_en": "Another profile entity",
            "name_zh": "另一资料实体",
            "industry": "test",
            "keywords": [],
        }
    )
    foreign = {**scope, "brand_focus_id": other["brand_focus_id"]}
    with pytest.raises(ValueError, match="MANIFEST_INVALID"):
        profiles.prepare_profile(manifest, actor=ws["actor"], scope=foreign)
    corrupted = copy.deepcopy(manifest)
    corrupted["sources"][0]["excerpt"] = "changed bytes"
    with pytest.raises(ValueError, match="CAPTURE_INVALID"):
        profiles.prepare_profile(corrupted, actor=ws["actor"], scope=scope)
    prepared = profiles.prepare_profile(manifest, actor=ws["actor"], scope=scope)
    ws["gate"].grant_approval(
        "data_import", resource=prepared["resource"], granted_by="synthetic"
    )
    profiles.import_profile(manifest, actor=ws["actor"], scope=scope)
    assert profiles.read_profiles(actor=ws["actor"], scope=foreign)["current"] is None
    with ws["repo"].transaction() as con:
        con.execute(
            "UPDATE lumenis_subject_registry SET status='inactive' WHERE brand_focus_id=?",
            (scope["brand_focus_id"],),
        )
    with pytest.raises(ValueError, match="PERMISSION_DENIED"):
        profiles.read_profiles(actor=ws["actor"], scope=scope)


def test_profile_report_projection_keeps_typed_sources_and_checks_original_bytes(
    workspace,
):
    from lumenis.importer import entity_profiles as profiles
    from lumenis.shared.reporting.operational_brief import build_scoped_source_brief
    import shared_artifacts

    ws = workspace
    scope = _register(ws)
    manifest = _manifest(scope)
    kwargs = dict(actor=ws["actor"], scope=scope)
    prepared = profiles.prepare_profile(manifest, **kwargs)
    ws["gate"].grant_approval(
        "data_import", resource=prepared["resource"], granted_by="synthetic-review"
    )
    imported = profiles.import_profile(manifest, **kwargs)
    with ws["repo"].connection(read_only=True, wal=False) as con:
        brief = build_scoped_source_brief(
            con,
            product_id="ZBMP",
            global_scope=False,
            actor_ref=ws["actor"].principal_ref,
            entity_label="Synthetic profile entity",
            brand_focus_id=scope["brand_focus_id"],
        )
        foreign = build_scoped_source_brief(
            con, product_id="ZBMP", global_scope=False,
            actor_ref="actor:99999", entity_label="Synthetic profile entity",
            brand_focus_id=scope["brand_focus_id"],
        )
        assert "profile_research" not in foreign["records"][0]
        research = brief["records"][0]["profile_research"]
        assert research["assertions"] == manifest["assertions"]
        assert research["review"] == {}
        assert research["references"][0]["url"] == "https://example.com/synthetic"
        assert research["fact_verification"] == "NOT_ESTABLISHED"
        assert brief["records"][0]["source_url"] is None
        row = con.execute(
            "SELECT relative_path FROM lumenis_shared_artifacts WHERE kind='imported_document_source' AND evidence_id=?",
            (str(imported["evidence_id"]),),
        ).fetchone()
    original = shared_artifacts.artifact_root() / row[0]
    original.write_bytes(b"corrupted retained original")
    with ws["repo"].connection(read_only=True, wal=False) as con:
        with pytest.raises(ValueError, match="DOCUMENT_SOURCE_ARTIFACT_INVALID"):
            build_scoped_source_brief(
                con,
                product_id="ZBMP",
                global_scope=False,
                actor_ref=ws["actor"].principal_ref,
                entity_label="Synthetic profile entity",
                brand_focus_id=scope["brand_focus_id"],
            )


@pytest.mark.parametrize("field", ["reviewed_on", "source_as_of"])
def test_profile_calendar_dates_are_real_dates(workspace, field):
    from lumenis.importer import entity_profiles as profiles

    scope = _register(workspace)
    manifest = _manifest(scope)
    manifest["sources"][0][field] = "2026-02-30"
    with pytest.raises(ValueError, match="SOURCE_DATE_INVALID"):
        profiles.prepare_profile(manifest, actor=workspace["actor"], scope=scope)
