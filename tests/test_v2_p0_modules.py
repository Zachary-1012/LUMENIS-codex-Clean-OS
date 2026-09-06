"""V2 P0 新模块综合测试（ZBC 侧）

覆盖：Provider Registry, Subject Context, Domain Isolation, Repository Registry
"""
import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProviderRegistry:
    def test_zhipu_active(self):
        from provider_registry import provider_status, ACTIVE
        assert provider_status("zhipu") == ACTIVE

    def test_ollama_available(self):
        from provider_registry import provider_status, AVAILABLE
        assert provider_status("ollama") == AVAILABLE

    def test_ark_active_fallback(self):
        from provider_registry import provider_status, ACTIVE_FALLBACK
        assert provider_status("ark") == ACTIVE_FALLBACK

    def test_qwen_not_configured(self):
        from provider_registry import provider_status, NOT_CONFIGURED
        assert provider_status("qwen") == NOT_CONFIGURED

    def test_openai_disabled(self):
        from provider_registry import provider_status, DISABLED
        assert provider_status("openai") == DISABLED

    def test_deepseek_disabled(self):
        from provider_registry import provider_status, DISABLED
        assert provider_status("deepseek") == DISABLED

    def test_active_providers(self):
        from provider_registry import active_providers
        active = active_providers()
        assert "zhipu" in active
        # ollama=AVAILABLE, ark=ACTIVE_FALLBACK 不在 active 列表，但在可用链中
        assert "qwen" not in active

    def test_unknown_provider_disabled(self):
        from provider_registry import provider_status, DISABLED
        assert provider_status("nonexistent") == DISABLED


class TestSubjectContext:
    def test_cth_default(self):
        from subject_context import get_subject_context, CTH_BRAND_KEY, PRODUCT_CTH
        ctx = get_subject_context()
        assert ctx.brand_key == CTH_BRAND_KEY
        assert ctx.product_id == PRODUCT_CTH

    def test_cth_protection(self):
        from subject_context import get_subject_context, assert_cth_protection
        ctx = get_subject_context()
        assert_cth_protection()  # 不应抛异常

    def test_subject_to_dict(self):
        from subject_context import get_subject_context
        ctx = get_subject_context()
        d = ctx.to_dict()
        assert "subject_id" in d
        assert "brand_key" in d
        assert "product_id" in d

    def test_thread_context(self):
        from subject_context import (set_thread_context, get_thread_context,
                                     clear_thread_context, get_subject_context)
        ctx = get_subject_context()
        set_thread_context(ctx)
        assert get_thread_context() is not None
        clear_thread_context()
        assert get_thread_context() is None

    def test_current_scope(self):
        from subject_context import current_scope
        scope = current_scope()
        assert "product" in scope
        assert "subject" in scope


class TestDomainIsolation:
    def test_cth_domain_protected(self):
        from domain_isolation import get_domain
        cth = get_domain("cth")
        assert cth.is_protected is True

    def test_zbmp_domain_not_protected(self):
        from domain_isolation import get_domain
        zbmp = get_domain("zbmp")
        assert zbmp.is_protected is False

    def test_isolated_resources(self):
        from domain_isolation import CTH_DOMAIN
        assert "database" in CTH_DOMAIN.isolated_resources
        assert "subject_words" in CTH_DOMAIN.isolated_resources

    def test_shared_resources(self):
        from domain_isolation import CTH_DOMAIN
        assert "ai_gateway" in CTH_DOMAIN.shared_resources
        assert "skill_registry" in CTH_DOMAIN.shared_resources

    def test_cross_domain_shared_allowed(self):
        from domain_isolation import cross_domain_access_allowed
        assert cross_domain_access_allowed("cth", "zbmp", "ai_gateway") is True

    def test_cross_domain_isolated_denied(self):
        from domain_isolation import cross_domain_access_allowed
        assert cross_domain_access_allowed("cth", "zbmp", "database") is False

    def test_domain_summary(self):
        from domain_isolation import domain_summary
        s = domain_summary()
        assert "domains" in s
        assert "current_domain" in s


class TestRepositoryRegistry:
    def test_registry_file_exists(self):
        path = os.path.join(r"D:\Taikoo-monitor-new", "repo_registry.json")
        assert os.path.isfile(path)

    def test_registry_valid_json(self):
        path = os.path.join(r"D:\Taikoo-monitor-new", "repo_registry.json")
        with open(path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        assert "repositories" in reg
        assert len(reg["repositories"]) >= 2

    def test_registry_has_zbc_and_osai(self):
        path = os.path.join(r"D:\Taikoo-monitor-new", "repo_registry.json")
        with open(path, "r", encoding="utf-8") as f:
            reg = json.load(f)
        roles = [r["role"] for r in reg["repositories"]]
        assert "production_core" in roles
        assert "intelligence_core" in roles


class TestSkillAdapterNoHardcode:
    def test_no_d_zachary_hardcode(self):
        path = os.path.join(r"D:\Taikoo-monitor-new", "lumenis_skill_adapter.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert r"D:\Zachary OS AI" not in content
        assert "D:\\\\Zachary" not in content

    def test_adapter_has_repo_registry_support(self):
        path = os.path.join(r"D:\Taikoo-monitor-new", "lumenis_skill_adapter.py")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "repo_registry.json" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
