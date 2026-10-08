"""Canonical identity admission; all persistence uses a disposable database."""
from types import SimpleNamespace
import sqlite3

import pytest

from canonical_data import (
    CanonicalRecord, collected_note_to_canonical, ensure_canonical_table,
    note_to_canonical, persist_canonical, web_mention_to_canonical,
)


def test_unknown_product_rejected_before_domain_fallback():
    with pytest.raises(ValueError):
        CanonicalRecord(product_id="OTHER")


@pytest.mark.parametrize("product", [None, "", " CTH", "SYSTEM", 0])
def test_explicit_invalid_product_never_becomes_cth(product):
    with pytest.raises(ValueError):
        CanonicalRecord(product_id=product, domain_id="cth")


@pytest.mark.parametrize("domain", [None, "system", "unknown", " cth", 0])
def test_explicit_invalid_domain_is_rejected(domain):
    with pytest.raises(ValueError):
        CanonicalRecord(product_id="CTH", domain_id=domain)


@pytest.mark.parametrize("product,domain", [("CTH", "zbmp"), ("BMP", "cth")])
def test_conflicting_identity_is_rejected_at_construction(product, domain):
    with pytest.raises(ValueError):
        CanonicalRecord(product_id=product, domain_id=domain)


def test_declared_cth_compatibility_default_is_preserved():
    record = CanonicalRecord()
    assert (record.product_id, record.domain_id) == ("CTH", "cth")
    assert record.scope_status == "UNASSIGNED"
    assert record.scope_evidence_ref == ""


@pytest.mark.parametrize("product", ["BMP", "bmp", "ZBMP", "zbmp"])
def test_known_bmp_alias_uses_existing_storage_identity(product):
    record = CanonicalRecord(product_id=product)
    assert (record.product_id, record.domain_id) == ("ZBMP", "zbmp")


@pytest.mark.parametrize("converter", [note_to_canonical, web_mention_to_canonical])
@pytest.mark.parametrize("raw_identity", [
    {"product_id": "OTHER"}, {"product_id": None},
    {"product_id": "ZBMP"}, {"domain_id": "zbmp"},
])
def test_inbound_row_cannot_discard_unknown_or_conflicting_identity(converter, raw_identity):
    with pytest.raises(ValueError):
        converter({"note_id": "native", "source_id": "native", **raw_identity})


@pytest.mark.parametrize("converter", [note_to_canonical, web_mention_to_canonical])
def test_inbound_bmp_alias_preserves_declared_focus_without_verifying(converter):
    record = converter({"note_id": "native", "source_id": "native", "product_id": "BMP",
                        "domain_id": "zbmp", "brand_focus_id": "BRAND-PENDING"}, product_id="BMP")
    assert (record.product_id, record.domain_id, record.brand_focus_id) == ("ZBMP", "zbmp", "BRAND-PENDING")
    assert record.scope_status == "UNASSIGNED"
    assert record.scope_evidence_ref == ""


def test_collected_typed_identity_is_not_discarded():
    with pytest.raises(ValueError):
        collected_note_to_canonical(SimpleNamespace(product_id="OTHER", raw_data={}))


def test_native_product_sku_is_not_reinterpreted_as_lumenis_identity():
    record = collected_note_to_canonical(SimpleNamespace(raw_data={"product_id": "retail-sku"}))
    assert (record.product_id, record.domain_id) == ("CTH", "cth")


@pytest.mark.parametrize("field,value", [("product_id", "OTHER"), ("product_id", ""),
                                          ("domain_id", "zbmp"), ("domain_id", "")])
def test_persistence_rechecks_mutated_identity_without_writing(tmp_path, field, value):
    record = CanonicalRecord(canonical_id="invalid-mutation")
    setattr(record, field, value)
    with sqlite3.connect(tmp_path / "isolated.sqlite3") as connection:
        ensure_canonical_table(connection=connection)
        with pytest.raises(ValueError):
            persist_canonical(connection, record)
        assert connection.execute("SELECT count(*) FROM canonical_data").fetchone()[0] == 0
        assert record.content_hash == ""
