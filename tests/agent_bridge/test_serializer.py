# -*- coding: utf-8 -*-
"""
Unit tests for agent_bridge.serializer
覆盖：序列化往返、JSON 往返、迁移环境、空状态、权限上下文保留、证据链保留
"""
import sys
import os
import json
import copy
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_bridge.serializer import (
    RunBundle,
    serialize_run,
    deserialize_run,
    migrate_run,
)


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def sample_loop_state():
    return {
        "agent_id": "agent_001",
        "task_id": "task_001",
        "status": "running",
        "goal": "分析舆情",
        "current_step": 2,
        "metrics": {"steps": 5, "completed": 2},
        "plan": {"steps": [{"action": "采集"}, {"action": "分析"}]},
    }


@pytest.fixture
def sample_memory():
    return {
        "working_memory": {"key": "value"},
        "episodic": [{"event": "step1_done"}],
        "semantic": {"concept": "definition"},
    }


@pytest.fixture
def sample_evidence():
    return [
        {"evidence_id": "ev_001", "type": "collection", "content": "采集到 100 条", "score": 0.95},
        {"evidence_id": "ev_002", "type": "risk", "content": "发现高风险", "score": 0.88},
    ]


@pytest.fixture
def sample_identity():
    return {
        "agent_name": "taikoo_monitor",
        "role": "舆情分析",
        "brand": "广州太古汇",
    }


@pytest.fixture
def sample_permission():
    return {
        "allowed_operations": ["read", "analyze"],
        "denied_operations": ["write_production"],
        "risk_level": "medium",
    }


# ──────────────────────────────────────────────────────────────
# 1. 序列化往返测试
# ──────────────────────────────────────────────────────────────

class TestSerializeDeserializeRoundTrip:
    def test_full_round_trip(self, sample_loop_state, sample_memory, sample_evidence):
        """serialize → deserialize 往返不丢失数据。"""
        bundle = serialize_run(
            sample_loop_state,
            memory=sample_memory,
            evidence=sample_evidence,
            source_env="local",
        )
        restored = deserialize_run(bundle)

        assert restored["state"]["agent_id"] == "agent_001"
        assert restored["state"]["task_id"] == "task_001"
        assert restored["state"]["status"] == "running"
        assert restored["memory"]["working_memory"]["key"] == "value"
        assert len(restored["evidence"]) == 2
        assert restored["evidence"][0]["evidence_id"] == "ev_001"

    def test_serialize_extracts_from_loop_state(self, sample_loop_state):
        """未显式传 memory/evidence 时从 loop_state 提取。"""
        state = copy.deepcopy(sample_loop_state)
        state["memory"] = {"extracted": True}
        state["evidence"] = [{"id": "ev_extracted"}]

        bundle = serialize_run(state)
        assert bundle.memory_snapshot["extracted"] is True
        assert len(bundle.evidence_chain) == 1

    def test_deserialize_includes_bundle_metadata(self, sample_loop_state):
        """deserialize 结果包含 bundle 元信息。"""
        bundle = serialize_run(sample_loop_state, source_env="remote_worker")
        restored = deserialize_run(bundle)
        assert "_bundle" in restored["state"]
        assert restored["state"]["_bundle"]["source_env"] == "remote_worker"
        assert restored["state"]["_bundle"]["bundle_id"] == bundle.bundle_id


# ──────────────────────────────────────────────────────────────
# 2. JSON 往返测试
# ──────────────────────────────────────────────────────────────

class TestJsonRoundTrip:
    def test_to_json_from_json(self, sample_loop_state, sample_evidence):
        """to_json → from_json 往返。"""
        bundle = serialize_run(sample_loop_state, evidence=sample_evidence)
        json_str = bundle.to_json()
        restored = RunBundle.from_json(json_str)

        assert restored.bundle_id == bundle.bundle_id
        assert restored.agent_id == bundle.agent_id
        assert len(restored.evidence_chain) == 2
        assert restored.source_env == bundle.source_env

    def test_json_is_valid(self, sample_loop_state):
        """to_json 输出是合法 JSON。"""
        bundle = serialize_run(sample_loop_state)
        json_str = bundle.to_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["agent_id"] == "agent_001"
        assert "bundle_id" in parsed

    def test_from_dict_ignores_unknown_fields(self):
        """from_dict 忽略未知字段（向后兼容）。"""
        data = {
            "bundle_id": "b1",
            "agent_id": "a1",
            "unknown_field": "should_be_ignored",
            "another_new_field": 123,
        }
        bundle = RunBundle.from_dict(data)
        assert bundle.bundle_id == "b1"
        assert bundle.agent_id == "a1"
        assert not hasattr(bundle, "unknown_field")


# ──────────────────────────────────────────────────────────────
# 3. 迁移环境测试
# ──────────────────────────────────────────────────────────────

class TestMigrateRun:
    def test_migration_preserves_state(self, sample_loop_state, sample_memory):
        """迁移后所有状态保留。"""
        bundle = serialize_run(sample_loop_state, memory=sample_memory, source_env="local")
        migrated = migrate_run(bundle, "remote_gpu")

        assert migrated.agent_id == bundle.agent_id
        assert migrated.task_id == bundle.task_id
        assert migrated.memory_snapshot == bundle.memory_snapshot
        assert migrated.state_snapshot["status"] == "running"
        assert migrated.identity == bundle.identity

    def test_migration_updates_env(self, sample_loop_state):
        """迁移更新 env 标记。"""
        bundle = serialize_run(sample_loop_state, source_env="local")
        migrated = migrate_run(bundle, "remote_gpu")

        assert migrated.source_env == "local"  # 原 target_env 为空，所以 source_env 不变
        assert migrated.target_env == "remote_gpu"

    def test_migration_creates_new_bundle_id(self, sample_loop_state):
        """迁移生成新的 bundle_id。"""
        bundle = serialize_run(sample_loop_state)
        migrated = migrate_run(bundle, "remote")
        assert migrated.bundle_id != bundle.bundle_id

    def test_migration_records_history(self, sample_loop_state):
        """迁移记录历史。"""
        bundle = serialize_run(sample_loop_state)
        migrated = migrate_run(bundle, "remote")
        assert "migration_history" in migrated.state_snapshot
        history = migrated.state_snapshot["migration_history"]
        assert len(history) == 1
        assert history[0]["from_bundle"] == bundle.bundle_id
        assert history[0]["to_env"] == "remote"

    def test_multiple_migrations(self, sample_loop_state):
        """多次迁移累积历史。"""
        b1 = serialize_run(sample_loop_state, source_env="local")
        b2 = migrate_run(b1, "remote_a")
        b3 = migrate_run(b2, "remote_b")
        assert len(b3.state_snapshot["migration_history"]) == 2


# ──────────────────────────────────────────────────────────────
# 4. 空状态测试
# ──────────────────────────────────────────────────────────────

class TestEmptyState:
    def test_serialize_empty_state(self):
        """空状态序列化不抛异常。"""
        bundle = serialize_run({})
        assert bundle.agent_id == ""
        assert bundle.task_id == ""
        assert bundle.state_snapshot == {}
        assert bundle.memory_snapshot == {}
        assert bundle.evidence_chain == []

    def test_deserialize_empty_bundle(self):
        """空 bundle 反序列化返回空结构。"""
        bundle = RunBundle()
        restored = deserialize_run(bundle)
        assert restored["state"]["_bundle"]["bundle_id"] == bundle.bundle_id
        assert restored["memory"] == {}
        assert restored["evidence"] == []

    def test_serialize_none_state(self):
        """None 状态等价于空 dict。"""
        bundle = serialize_run(None)
        assert bundle.state_snapshot == {}


# ──────────────────────────────────────────────────────────────
# 5. 权限上下文保留测试
# ──────────────────────────────────────────────────────────────

class TestPermissionPreservation:
    def test_permission_preserved_in_bundle(self, sample_loop_state, sample_permission):
        """权限上下文保留在 bundle 中。"""
        bundle = serialize_run(sample_loop_state, permission_context=sample_permission)
        assert bundle.permission_context["allowed_operations"] == ["read", "analyze"]
        assert bundle.permission_context["risk_level"] == "medium"

    def test_permission_preserved_after_deserialize(self, sample_loop_state, sample_permission):
        """反序列化后权限上下文保留。"""
        bundle = serialize_run(sample_loop_state, permission_context=sample_permission)
        restored = deserialize_run(bundle)
        assert restored["permission"]["denied_operations"] == ["write_production"]

    def test_permission_preserved_after_migration(self, sample_loop_state, sample_permission):
        """迁移后权限上下文保留。"""
        bundle = serialize_run(sample_loop_state, permission_context=sample_permission)
        migrated = migrate_run(bundle, "remote")
        assert migrated.permission_context == sample_permission


# ──────────────────────────────────────────────────────────────
# 6. 证据链保留测试
# ──────────────────────────────────────────────────────────────

class TestEvidenceChainPreservation:
    def test_evidence_preserved_in_bundle(self, sample_loop_state, sample_evidence):
        """证据链保留在 bundle 中。"""
        bundle = serialize_run(sample_loop_state, evidence=sample_evidence)
        assert len(bundle.evidence_chain) == 2
        assert bundle.evidence_chain[0]["evidence_id"] == "ev_001"
        assert bundle.evidence_chain[1]["content"] == "发现高风险"

    def test_evidence_preserved_after_json_roundtrip(self, sample_loop_state, sample_evidence):
        """JSON 往返后证据链保留。"""
        bundle = serialize_run(sample_loop_state, evidence=sample_evidence)
        restored = RunBundle.from_json(bundle.to_json())
        assert len(restored.evidence_chain) == 2
        assert restored.evidence_chain[0]["score"] == 0.95

    def test_evidence_preserved_after_migration(self, sample_loop_state, sample_evidence):
        """迁移后证据链保留。"""
        bundle = serialize_run(sample_loop_state, evidence=sample_evidence)
        migrated = migrate_run(bundle, "remote")
        assert len(migrated.evidence_chain) == 2
        assert migrated.evidence_chain[1]["evidence_id"] == "ev_002"

    def test_deep_copy_prevents_mutation(self, sample_loop_state, sample_evidence):
        """bundle 使用深拷贝，外部修改不影响 bundle。"""
        bundle = serialize_run(sample_loop_state, evidence=sample_evidence)
        sample_evidence[0]["content"] = "MUTATED"
        assert bundle.evidence_chain[0]["content"] == "采集到 100 条"


# ──────────────────────────────────────────────────────────────
# 7. 与 Durable Checkpoint 兼容测试
# ──────────────────────────────────────────────────────────────

class TestDurableCheckpointCompatibility:
    def test_to_durable_checkpoint_dict(self, sample_loop_state):
        """RunBundle 可导出为 Durable Checkpoint 兼容 dict。"""
        bundle = serialize_run(sample_loop_state, source_env="local")
        cp_dict = bundle.to_durable_checkpoint_dict()

        # 字段对齐检查
        assert "checkpoint_id" in cp_dict
        assert "agent_id" in cp_dict
        assert "task_id" in cp_dict
        assert "step_index" in cp_dict
        assert "state" in cp_dict
        assert "plan_snapshot" in cp_dict
        assert "context" in cp_dict
        assert "created_at" in cp_dict
        assert "metadata" in cp_dict

    def test_from_durable_checkpoint(self):
        """可从 Durable Checkpoint dict 构建 RunBundle。"""
        cp_dict = {
            "checkpoint_id": "cp_001",
            "agent_id": "agent_001",
            "task_id": "task_001",
            "step_index": 3,
            "state": "executing",
            "plan_snapshot": {"steps": []},
            "context": {
                "identity": {"name": "test"},
                "memory": {"k": "v"},
                "state": {"extra": "data"},
                "evidence": [{"id": "e1"}],
                "permission": {"level": "low"},
                "source_env": "local",
            },
            "created_at": "2026-09-07T10:00:00Z",
            "metadata": {},
        }
        bundle = RunBundle.from_durable_checkpoint(cp_dict)
        assert bundle.bundle_id == "cp_001"
        assert bundle.agent_id == "agent_001"
        assert bundle.state_snapshot["status"] == "executing"
        assert bundle.state_snapshot["step_index"] == 3
        assert bundle.identity["name"] == "test"
        assert len(bundle.evidence_chain) == 1

    def test_roundtrip_through_durable_checkpoint(self, sample_loop_state):
        """RunBundle → Durable Checkpoint dict → RunBundle 往返。"""
        bundle = serialize_run(sample_loop_state, source_env="local")
        cp_dict = bundle.to_durable_checkpoint_dict()
        restored = RunBundle.from_durable_checkpoint(cp_dict)

        assert restored.agent_id == bundle.agent_id
        assert restored.task_id == bundle.task_id
        assert restored.source_env == "local"
