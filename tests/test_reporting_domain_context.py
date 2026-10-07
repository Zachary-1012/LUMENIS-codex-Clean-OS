from __future__ import annotations

import pytest


def _clear_context():
    from domain_isolation import clear_domain_context
    from subject_context import clear_thread_context
    clear_domain_context()
    clear_thread_context()


@pytest.fixture(autouse=True)
def _isolated_context():
    _clear_context()
    yield
    _clear_context()


def test_legacy_report_engine_requires_explicit_bound_reference_subject(monkeypatch):
    from domain_isolation import DomainContext, set_domain_context
    from subject_context import CTH_BRAND_KEY, CTH_SUBJECT_ID, SubjectContext, set_thread_context
    from lumenis.shared.reporting import engine

    _clear_context()
    called = []
    monkeypatch.setattr(engine.db, "get_latest_report", lambda *_args: called.append(True))
    with pytest.raises(ValueError, match="REPORT_DOMAIN_REQUIRED"):
        engine.get_bundle("daily")
    assert called == []

    set_domain_context(DomainContext(domain_id="cth", product_id="CTH"))
    with pytest.raises(ValueError, match="REPORT_REFERENCE_SUBJECT_REQUIRED"):
        engine.generate_report("daily")

    set_domain_context(DomainContext(
        domain_id="cth", product_id="CTH", subject_id=CTH_SUBJECT_ID,
        brand_key=CTH_BRAND_KEY,
    ))
    set_thread_context(SubjectContext(
        subject_id=CTH_SUBJECT_ID, brand_key=CTH_BRAND_KEY, product_id="CTH",
    ))
    assert engine._resolve_legacy_report_scope() == ("cth", "CTH")

    with pytest.raises(ValueError, match="LEGACY_REPORT_DOMAIN_UNSUPPORTED"):
        engine.generate_report("daily", domain_id="zbmp")
