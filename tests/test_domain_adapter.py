# -*- coding: utf-8 -*-
"""Test DomainAdapter — ZBMP/CTH field isolation and round-trip conversion.

Verifies:
1. ZBMPAdapter strips CTH-only fields (taikoo_hui_specific, xhs_subject_match, etc.)
2. CTHAdapter strips ZBMP-only fields (multi_brand_config, brand_profiles, etc.)
3. CTHAdapter preserves the exact Subject and does not invent a focus
4. Domain mismatch raises ValueError (ZBMP adapter rejects CTH record and vice versa)
5. Round-trip conversion preserves core fields
6. get_adapter() factory returns correct adapter by domain_id
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from canonical_data import CanonicalRecord, PRODUCT_CTH, PRODUCT_ZBMP
from domain_adapter import (
    ZBMPAdapter, CTHAdapter, get_adapter, adapt_to_domain,
    ZBMPRecord, CTHRecord, CTH_ONLY_FIELDS, ZBMP_ONLY_FIELDS,
)
from domain_isolation import DOMAIN_CTH, DOMAIN_ZBMP


class TestZBMPAdapter:
    """ZBMP adapter must strip CTH-only fields."""

    def test_zbmp_adapter_strips_cth_fields(self):
        """ZBMP adapter output must not contain any CTH-only field keys."""
        rec = CanonicalRecord(product_id=PRODUCT_ZBMP, title="test zbmp", content="content")
        adapter = ZBMPAdapter()
        result = adapter.to_domain(rec)
        result_dict = result.to_dict()
        for field in CTH_ONLY_FIELDS:
            assert field not in result_dict, f"ZBMP output leaked CTH-only field: {field}"

    def test_zbmp_adapter_rejects_cth_record(self):
        """ZBMP adapter must raise ValueError when given a CTH record."""
        rec = CanonicalRecord(product_id=PRODUCT_CTH, title="cth record")
        adapter = ZBMPAdapter()
        with pytest.raises(ValueError, match="Domain mismatch"):
            adapter.to_domain(rec)

    def test_zbmp_adapter_preserves_core_fields(self):
        """ZBMP adapter must preserve core fields (title, content, url, etc.)."""
        rec = CanonicalRecord(
            product_id=PRODUCT_ZBMP,
            title="Test Title",
            content="Test Content",
            url="https://example.com/test",
            author_name="test_author",
            sentiment="positive",
            risk_level="low",
        )
        adapter = ZBMPAdapter()
        result = adapter.to_domain(rec)
        assert result.title == "Test Title"
        assert result.content == "Test Content"
        assert result.url == "https://example.com/test"
        assert result.author_name == "test_author"
        assert result.sentiment == "positive"
        assert result.domain_id == DOMAIN_ZBMP
        assert result.product_id == PRODUCT_ZBMP

    def test_zbmp_round_trip(self):
        """ZBMP round-trip: to_domain -> from_domain preserves core identity."""
        rec = CanonicalRecord(product_id=PRODUCT_ZBMP, title="Round Trip", content="data")
        adapter = ZBMPAdapter()
        domain_rec = adapter.to_domain(rec)
        back = adapter.from_domain(domain_rec)
        assert back.product_id == PRODUCT_ZBMP
        assert back.domain_id == DOMAIN_ZBMP
        assert back.title == "Round Trip"
        assert back.content == "data"


class TestCTHAdapter:
    """CTH adapter strips ZBMP-only fields and preserves CTH scope identity."""

    def test_cth_adapter_strips_zbmp_fields(self):
        """CTH adapter output must not contain any ZBMP-only field keys."""
        rec = CanonicalRecord(product_id=PRODUCT_CTH, title="test cth")
        adapter = CTHAdapter()
        result = adapter.to_domain(rec)
        result_dict = result.to_dict()
        for field in ZBMP_ONLY_FIELDS:
            assert field not in result_dict, f"CTH output leaked ZBMP-only field: {field}"

    def test_cth_adapter_rejects_zbmp_record(self):
        """CTH adapter must raise ValueError when given a ZBMP record."""
        rec = CanonicalRecord(product_id=PRODUCT_ZBMP, title="zbmp record")
        adapter = CTHAdapter()
        with pytest.raises(ValueError, match="Domain mismatch"):
            adapter.to_domain(rec)

    def test_cth_adapter_preserves_subject_without_inventing_focus(self):
        rec = CanonicalRecord(product_id=PRODUCT_CTH, title="test", subject_id="SUBJECT-A")
        adapter = CTHAdapter()
        result = adapter.to_domain(rec)
        assert result.subject_id == "SUBJECT-A"
        assert result.brand_key == ""

        no_focus = adapter.to_domain(CanonicalRecord(product_id=PRODUCT_CTH, title="global"))
        assert no_focus.subject_id == ""
        assert no_focus.brand_key == ""

    def test_cth_round_trip(self):
        """CTH round-trip preserves core identity."""
        rec = CanonicalRecord(product_id=PRODUCT_CTH, title="CTH Round Trip")
        adapter = CTHAdapter()
        domain_rec = adapter.to_domain(rec)
        back = adapter.from_domain(domain_rec)
        assert back.product_id == PRODUCT_CTH
        assert back.domain_id == DOMAIN_CTH
        assert back.subject_id == ""
        assert back.title == "CTH Round Trip"

    def test_cth_round_trip_preserves_exact_subject(self):
        rec = CanonicalRecord(
            product_id=PRODUCT_CTH, domain_id=DOMAIN_CTH,
            subject_id="SUBJECT-B", title="Focused CTH",
        )
        back = CTHAdapter().from_domain(CTHAdapter().to_domain(rec))
        assert back.subject_id == "SUBJECT-B"


class TestAdapterFactory:
    """Adapter factory and convenience functions."""

    def test_get_adapter_cth(self):
        adapter = get_adapter(DOMAIN_CTH)
        assert isinstance(adapter, CTHAdapter)

    def test_get_adapter_zbmp(self):
        adapter = get_adapter(DOMAIN_ZBMP)
        assert isinstance(adapter, ZBMPAdapter)

    def test_get_adapter_unknown_fails_closed(self):
        with pytest.raises(ValueError, match="INVALID_DOMAIN_ID"):
            get_adapter("unknown_domain")

    def test_get_adapter_system_has_no_business_adapter(self):
        with pytest.raises(ValueError, match="No domain adapter"):
            get_adapter("system")

    @pytest.mark.parametrize("domain_id", ["cth", "CTH"])
    def test_get_adapter_accepts_registered_cth_aliases(self, domain_id):
        assert isinstance(get_adapter(domain_id), CTHAdapter)

    def test_to_domain_rejects_contradictory_domain_product_pair(self):
        rec = CanonicalRecord(product_id=PRODUCT_CTH, domain_id=DOMAIN_ZBMP)
        with pytest.raises(ValueError, match="CanonicalRecord domain/product identity"):
            CTHAdapter().to_domain(rec)

    def test_from_domain_rejects_mutated_cross_domain_identity(self):
        value = CTHRecord(product_id=PRODUCT_ZBMP, domain_id=DOMAIN_ZBMP, subject_id="SUBJECT-A")
        with pytest.raises(ValueError, match="Domain mismatch"):
            CTHAdapter().from_domain(value)

    def test_adapt_to_domain_zbmp(self):
        rec = CanonicalRecord(product_id=PRODUCT_ZBMP, title="adapt test")
        result = adapt_to_domain(rec, DOMAIN_ZBMP)
        assert isinstance(result, ZBMPRecord)
        assert result.domain_id == DOMAIN_ZBMP

    def test_adapt_to_domain_cth(self):
        rec = CanonicalRecord(product_id=PRODUCT_CTH, title="adapt test")
        result = adapt_to_domain(rec, DOMAIN_CTH)
        assert isinstance(result, CTHRecord)
        assert result.domain_id == DOMAIN_CTH
