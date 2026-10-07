"""Unknown Evidence scope must remain unassigned until a domain is selected."""
import hashlib

import pytest

from domain_isolation import DomainContext, clear_domain_context, set_domain_context
from subject_context import SubjectContext, clear_thread_context, set_thread_context
from lumenis.shared.evidence.chain import (
    Evidence,
    EvidenceStore,
    _resolve_evidence_identity,
    list_evidence_by_domain,
)


@pytest.fixture(autouse=True)
def no_selected_domain():
    clear_domain_context()
    clear_thread_context()
    yield
    clear_domain_context()
    clear_thread_context()


def test_evidence_value_defaults_do_not_claim_cth():
    raw = "unassigned source"
    evidence = Evidence(
        evidence_id="ev_unassigned",
        source_type="web",
        source_url="https://example.test/source",
        raw_content=raw,
        content_hash=hashlib.sha256(raw.encode()).hexdigest(),
        captured_at="2026-10-08T00:00:00Z",
    )

    assert evidence.domain_id == ""
    assert evidence.product_id == ""
    assert evidence.subject_scope == ""


def test_evidence_write_and_domain_query_require_selection(tmp_path):
    database = str(tmp_path / "evidence.sqlite")
    store = EvidenceStore(database)

    with pytest.raises(ValueError, match="EVIDENCE_DOMAIN_REQUIRED"):
        store.add_evidence(
            source_type="web",
            source_url="https://example.test/source",
            raw_content="unassigned source",
        )
    with pytest.raises(ValueError, match="EVIDENCE_DOMAIN_REQUIRED"):
        list_evidence_by_domain(database)

    set_domain_context(DomainContext.from_product("BMP"))
    assert list_evidence_by_domain(database) == []


def test_explicit_bmp_alias_query_resolves_to_canonical_domain(tmp_path):
    database = str(tmp_path / "evidence.sqlite")
    store = EvidenceStore(database)
    store.add_evidence(
        source_type="web",
        source_url="https://example.test/bmp",
        raw_content="authorized brand scope",
        domain_id="zbmp",
        product_id="BMP",
    )

    rows = list_evidence_by_domain(database, domain_id="BMP", product_id="ZBMP")

    assert len(rows) == 1
    assert rows[0]["domain_id"] == "zbmp"
    assert rows[0]["product_id"] == "ZBMP"


def test_explicit_bmp_identity_does_not_inherit_bound_cth_focus():
    set_domain_context(DomainContext.from_domain("system"))
    set_thread_context(SubjectContext(subject_id="TAIKOO", brand_key="", product_id="CTH"))

    _domain, _product, scope = _resolve_evidence_identity(
        domain_id="zbmp", product_id="ZBMP",
    )

    assert scope == "GLOBAL / ALL"


def test_default_system_skill_execution_records_explicit_system_evidence(tmp_path, monkeypatch):
    from lumenis.shared import evidence as evidence_package
    from lumenis.shared.agents.skills import execution

    store = EvidenceStore(str(tmp_path / "skill-evidence.sqlite"))
    monkeypatch.setattr(evidence_package, "EvidenceStore", lambda: store)
    context = execution.SkillExecutionContext(
        skill_id="zbc.skill_registry_snapshot",
        task="Read skill registry status",
        input_payload={"status": "registered"},
    )

    result = execution.record_execution_evidence(context)

    assert result["ok"] is True
    evidence = store.get_evidence(result["evidence_id"])
    assert evidence.domain_id == "system"
    assert evidence.product_id == "SYSTEM"
    assert evidence.subject_scope == "GLOBAL / ALL"
