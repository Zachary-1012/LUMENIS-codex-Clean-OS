# -*- coding: utf-8 -*-
"""
agent_research.specialist 单元测试
==================================
覆盖：专家注册/查找、默认专家列表、注销、启用过滤、按角色筛选。
"""
import pytest

from agent_research.specialist import Specialist, SpecialistRegistry, default_specialists


class TestDefaultSpecialists:
    """默认专家列表测试。"""

    def test_default_specialists_returns_three(self):
        """默认专家列表应返回 3 个专家。"""
        specialists = default_specialists()
        assert len(specialists) == 3

    def test_default_specialists_ids(self):
        """默认专家应包含 analyst / critic / validator。"""
        ids = {s.specialist_id for s in default_specialists()}
        assert ids == {"analyst", "critic", "validator"}

    def test_default_specialists_all_enabled(self):
        """默认专家全部启用。"""
        assert all(s.enabled for s in default_specialists())

    def test_default_specialists_have_capabilities(self):
        """默认专家应有非空 capabilities。"""
        for s in default_specialists():
            assert len(s.capabilities) > 0


class TestSpecialistRegistry:
    """专家注册表测试。"""

    def test_registry_initialized_with_defaults(self):
        """注册表初始化时应包含 3 个默认专家。"""
        registry = SpecialistRegistry()
        assert len(registry.list()) == 3

    def test_register_custom_specialist(self):
        """注册自定义专家后可通过 get 查找。"""
        registry = SpecialistRegistry()
        custom = Specialist(
            specialist_id="data_scientist",
            name="数据科学家",
            role="analyst",
            domain="statistics",
            capabilities=["statistical_analysis"],
            priority=5,
        )
        registry.register(custom)
        retrieved = registry.get("data_scientist")
        assert retrieved is not None
        assert retrieved.name == "数据科学家"
        assert retrieved.priority == 5

    def test_unregister_existing(self):
        """注销已存在的专家应返回 True。"""
        registry = SpecialistRegistry()
        result = registry.unregister("analyst")
        assert result is True
        assert registry.get("analyst") is None

    def test_unregister_nonexistent(self):
        """注销不存在的专家应返回 False。"""
        registry = SpecialistRegistry()
        result = registry.unregister("nonexistent_id")
        assert result is False

    def test_list_enabled_only(self):
        """enabled_only=True 应仅返回启用的专家。"""
        registry = SpecialistRegistry()
        # 禁用一个专家
        critic = registry.get("critic")
        critic.enabled = False
        registry.register(critic)
        enabled = registry.list(enabled_only=True)
        assert len(enabled) == 2
        assert all(s.enabled for s in enabled)

    def test_list_sorted_by_priority(self):
        """list 应按 priority 升序排序。"""
        registry = SpecialistRegistry()
        priorities = [s.priority for s in registry.list()]
        assert priorities == sorted(priorities)

    def test_by_role(self):
        """按角色筛选专家。"""
        registry = SpecialistRegistry()
        analysts = registry.by_role("analyst")
        assert len(analysts) == 1
        assert analysts[0].specialist_id == "analyst"

    def test_get_nonexistent_returns_none(self):
        """查找不存在的专家返回 None。"""
        registry = SpecialistRegistry()
        assert registry.get("no_such_expert") is None

    def test_specialist_to_dict(self):
        """Specialist.to_dict() 应返回可序列化字典。"""
        sp = default_specialists()[0]
        d = sp.to_dict()
        assert isinstance(d, dict)
        assert d["specialist_id"] == sp.specialist_id
        assert d["name"] == sp.name
