# -*- coding: utf-8 -*-
"""Test Subject Context Isolation — Shard D / Team 1

Verifies:
1. get_active_brand() defaults to CTH (guangzhou_taikoo_hui)
2. brand_scope context manager switches brand locally and restores after
3. Thread context is isolated between threads
4. CTH protection blocks non-CTH brand switch when ZBC_PRODUCT_ID=CTH
5. subject_hit() respects brand scope (Guangzhou vs Chengdu isolation)
"""
import os
import sys
import threading
import pytest

# Ensure repo root on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSubjectContextIsolation:
    """Product/Subject/Scope isolation tests."""

    def test_default_brand_is_cth(self):
        """Default active brand must be Guangzhou Taikoo Hui (CTH)."""
        from subject_context import clear_thread_context, get_subject_context
        clear_thread_context()
        # Ensure no env override
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            ctx = get_subject_context()
            assert ctx.brand_key == "guangzhou_taikoo_hui"
            assert ctx.product_id == "CTH"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_get_active_brand_returns_cth_default(self):
        """subject_rules.get_active_brand() must return CTH by default."""
        from subject_context import clear_thread_context
        from subject_rules import get_active_brand
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            assert get_active_brand() == "guangzhou_taikoo_hui"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_brand_scope_switches_and_restores(self):
        """brand_scope must switch brand locally and restore after exit."""
        from subject_context import clear_thread_context, get_thread_context, brand_scope
        from subject_rules import get_active_brand
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            assert get_active_brand() == "guangzhou_taikoo_hui"
            with brand_scope("hainan_cdf"):
                assert get_active_brand() == "hainan_cdf"
                ctx = get_thread_context()
                assert ctx is not None
                assert ctx.brand_key == "hainan_cdf"
            # After exit, restored to default (no thread context)
            assert get_thread_context() is None
            assert get_active_brand() == "guangzhou_taikoo_hui"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_brand_scope_nested(self):
        """Nested brand_scope must restore correctly."""
        from subject_context import clear_thread_context, brand_scope
        from subject_rules import get_active_brand
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            with brand_scope("hainan_cdf"):
                assert get_active_brand() == "hainan_cdf"
                with brand_scope("tokyo_dfs"):
                    assert get_active_brand() == "tokyo_dfs"
                assert get_active_brand() == "hainan_cdf"
            assert get_active_brand() == "guangzhou_taikoo_hui"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_thread_isolation(self):
        """Brand context must be thread-local (no cross-thread leakage)."""
        from subject_context import clear_thread_context, brand_scope, get_thread_context
        from subject_rules import get_active_brand
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        results = {}

        def worker(brand, key):
            try:
                with brand_scope(brand):
                    results[key] = get_active_brand()
            except Exception as e:
                results[key] = f"ERROR: {e}"

        try:
            t1 = threading.Thread(target=worker, args=("hainan_cdf", "t1"))
            t2 = threading.Thread(target=worker, args=("tokyo_dfs", "t2"))
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            assert results.get("t1") == "hainan_cdf"
            assert results.get("t2") == "tokyo_dfs"
            # Main thread unaffected
            assert get_active_brand() == "guangzhou_taikoo_hui"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_cth_protection_blocks_brand_switch(self):
        """When ZBC_PRODUCT_ID=CTH, brand_scope must reject non-CTH brands."""
        from subject_context import clear_thread_context, brand_scope
        clear_thread_context()
        old_product = os.environ.get("ZBC_PRODUCT_ID")
        old_brand = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            os.environ["ZBC_PRODUCT_ID"] = "CTH"
            with pytest.raises(PermissionError):
                with brand_scope("hainan_cdf"):
                    pass
            # CTH brand itself is allowed
            with brand_scope("guangzhou_taikoo_hui"):
                from subject_rules import get_active_brand
                assert get_active_brand() == "guangzhou_taikoo_hui"
        finally:
            if old_product:
                os.environ["ZBC_PRODUCT_ID"] = old_product
            else:
                os.environ.pop("ZBC_PRODUCT_ID", None)
            if old_brand:
                os.environ["ZBC_ACTIVE_BRAND"] = old_brand

    def test_subject_hit_brand_isolation(self):
        """subject_hit() must respect brand scope: Guangzhou vs Chengdu."""
        from subject_context import clear_thread_context, brand_scope
        from subject_rules import subject_hit
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            # Default CTH: Guangzhou Taikoo Hui should hit
            assert subject_hit(title="广州太古汇周末活动") is True
            # Chengdu Taikoo Li should NOT hit CTH (exclude words)
            assert subject_hit(title="成都太古里新店开业") is False
            # Hainan CDF brand: should hit Hainan content
            with brand_scope("hainan_cdf"):
                assert subject_hit(title="海南中免免税店") is True
                assert subject_hit(title="广州太古汇") is False  # different brand
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old

    def test_subject_policy_info_brand_scoped(self):
        """subject_policy_info() must return brand-scoped metadata."""
        from subject_context import clear_thread_context, brand_scope
        from subject_rules import subject_policy_info
        clear_thread_context()
        old = os.environ.pop("ZBC_ACTIVE_BRAND", None)
        try:
            info = subject_policy_info()
            assert info["active_brand"] == "guangzhou_taikoo_hui"
            with brand_scope("hainan_cdf"):
                info2 = subject_policy_info()
                assert info2["active_brand"] == "hainan_cdf"
        finally:
            if old:
                os.environ["ZBC_ACTIVE_BRAND"] = old


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
