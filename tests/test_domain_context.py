# -*- coding: utf-8 -*-
"""Test DomainContext — domain identity carrier with product_id/domain_id integration.

Verifies:
1. DomainContext.from_product() correctly maps product_id to domain_id
2. DomainContext.from_domain() correctly maps domain_id to product_id
3. Domain selection does not invent or replace a Subject
4. SYSTEM_DOMAIN exists with correct properties
5. DOMAINS dict contains cth, zbmp, system
6. product_to_domain / domain_to_product mapping functions
7. Thread-local get/set/clear DomainContext
8. domain_summary() returns all domains
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from domain_isolation import (
    DomainContext, SYSTEM_DOMAIN, CTH_DOMAIN, ZBMP_DOMAIN, DOMAINS,
    product_to_domain, domain_to_product,
    get_domain_context, set_domain_context, clear_domain_context,
    domain_summary,
    DOMAIN_CTH, DOMAIN_ZBMP, DOMAIN_SYSTEM,
    PRODUCT_CTH, PRODUCT_ZBMP, PRODUCT_SYSTEM,
)
from subject_context import CTH_BRAND_KEY


class TestDomainContextConstruction:
    """DomainContext construction and mapping."""

    def test_from_product_cth(self):
        ctx = DomainContext.from_product(PRODUCT_CTH)
        assert ctx.domain_id == DOMAIN_CTH
        assert ctx.product_id == PRODUCT_CTH

    def test_from_product_zbmp(self):
        ctx = DomainContext.from_product(PRODUCT_ZBMP)
        assert ctx.domain_id == DOMAIN_ZBMP
        assert ctx.product_id == PRODUCT_ZBMP

    def test_from_product_system(self):
        ctx = DomainContext.from_product(PRODUCT_SYSTEM)
        assert ctx.domain_id == DOMAIN_SYSTEM
        assert ctx.product_id == PRODUCT_SYSTEM

    def test_from_domain_cth(self):
        ctx = DomainContext.from_domain(DOMAIN_CTH)
        assert ctx.product_id == PRODUCT_CTH
        assert ctx.domain_id == DOMAIN_CTH

    def test_from_domain_zbmp(self):
        ctx = DomainContext.from_domain(DOMAIN_ZBMP)
        assert ctx.product_id == PRODUCT_ZBMP

    def test_from_domain_system(self):
        ctx = DomainContext.from_domain(DOMAIN_SYSTEM)
        assert ctx.product_id == PRODUCT_SYSTEM

    def test_cth_preserves_explicit_subject(self):
        """CTH supports non-reference subjects without silently changing identity."""
        ctx = DomainContext(domain_id=DOMAIN_CTH, product_id=PRODUCT_CTH,
                            brand_key="other_venue", subject_id="OTHER_VENUE")
        assert ctx.brand_key == "other_venue"
        assert ctx.subject_id == "OTHER_VENUE"

    def test_zbmp_allows_custom_subject(self):
        """ZBMP DomainContext allows custom brand_key (multi-brand platform)."""
        ctx = DomainContext(domain_id=DOMAIN_ZBMP, product_id=PRODUCT_ZBMP,
                            brand_key="hainan_cdf", subject_id="HAINAN_CDF")
        assert ctx.brand_key == "hainan_cdf"
        assert ctx.subject_id == "HAINAN_CDF"

    def test_post_init_rejects_conflicting_identity(self):
        """A conflicting pair cannot be silently corrected."""
        with pytest.raises(ValueError, match="DOMAIN_PRODUCT_MISMATCH"):
            DomainContext(domain_id=DOMAIN_ZBMP, product_id=PRODUCT_CTH)


class TestMappingFunctions:
    """product_to_domain and domain_to_product."""

    def test_product_to_domain_cth(self):
        assert product_to_domain(PRODUCT_CTH) == DOMAIN_CTH

    def test_product_to_domain_zbmp(self):
        assert product_to_domain(PRODUCT_ZBMP) == DOMAIN_ZBMP

    def test_product_to_domain_system(self):
        assert product_to_domain(PRODUCT_SYSTEM) == DOMAIN_SYSTEM

    def test_product_to_domain_unknown_rejected(self):
        with pytest.raises(ValueError, match="INVALID_PRODUCT_ID"):
            product_to_domain("UNKNOWN")

    def test_domain_to_product_cth(self):
        assert domain_to_product(DOMAIN_CTH) == PRODUCT_CTH

    def test_domain_to_product_zbmp(self):
        assert domain_to_product(DOMAIN_ZBMP) == PRODUCT_ZBMP

    def test_domain_to_product_system(self):
        assert domain_to_product(DOMAIN_SYSTEM) == PRODUCT_SYSTEM


class TestSystemDomain:
    """SYSTEM_DOMAIN definition."""

    def test_system_domain_exists(self):
        assert SYSTEM_DOMAIN.domain_id == DOMAIN_SYSTEM
        assert SYSTEM_DOMAIN.product_id == PRODUCT_SYSTEM
        assert SYSTEM_DOMAIN.is_protected is False

    def test_system_domain_shared_resources(self):
        """SYSTEM domain must share infrastructure resources."""
        shared = SYSTEM_DOMAIN.shared_resources
        assert "ai_gateway" in shared
        assert "database" in shared
        assert "logger" in shared

    def test_domains_dict_contains_all_three(self):
        assert DOMAIN_CTH in DOMAINS
        assert DOMAIN_ZBMP in DOMAINS
        assert DOMAIN_SYSTEM in DOMAINS
        assert len(DOMAINS) == 3


class TestThreadLocalDomainContext:
    """Thread-local get/set/clear DomainContext."""

    def test_set_and_get(self):
        ctx = DomainContext.from_domain(DOMAIN_ZBMP)
        set_domain_context(ctx)
        try:
            got = get_domain_context()
            assert got is not None
            assert got.domain_id == DOMAIN_ZBMP
        finally:
            clear_domain_context()

    def test_clear(self):
        ctx = DomainContext.from_domain(DOMAIN_CTH)
        set_domain_context(ctx)
        clear_domain_context()
        # After clear, there is no bound domain.
        got = get_domain_context()
        assert got is None

    def test_thread_isolation(self):
        """DomainContext must be thread-local."""
        results = {}

        def worker(domain_id, name):
            ctx = DomainContext.from_domain(domain_id)
            set_domain_context(ctx)
            import time
            time.sleep(0.05)
            got = get_domain_context()
            results[name] = got.domain_id
            clear_domain_context()

        t1 = threading.Thread(target=worker, args=(DOMAIN_CTH, "thread_cth"))
        t2 = threading.Thread(target=worker, args=(DOMAIN_ZBMP, "thread_zbmp"))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results["thread_cth"] == DOMAIN_CTH
        assert results["thread_zbmp"] == DOMAIN_ZBMP


class TestDomainSummary:
    """domain_summary() returns all domain info."""

    def test_domain_summary_returns_all_domains(self):
        summary = domain_summary()
        assert "domains" in summary
        assert DOMAIN_CTH in summary["domains"]
        assert DOMAIN_ZBMP in summary["domains"]
        assert DOMAIN_SYSTEM in summary["domains"]

    def test_domain_summary_has_current_domain(self):
        summary = domain_summary()
        assert "current_domain" in summary
        assert "current_product" in summary
