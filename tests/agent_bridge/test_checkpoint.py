# -*- coding: utf-8 -*-
"""
Unit tests for agent_bridge.checkpoint
覆盖：检查点保存加载、rehydrate 恢复、resume 继续、
与 DurableAdapter Checkpoint 兼容、文件 backend
"""
import sys
import os
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_bridge.checkpoint import (
    BridgeCheckpoint,
    CheckpointStore,
    rehydrate,
    resume,
)
from agent_runtime.durable_adapter import Checkpoint as DurableCheckpoint


# ──────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def memory_store():
    store = CheckpointStore(backend="memory")
    yield store
    store.clear()


@pytest.fixture
def file_store():
    tmpdir = tempfile.mkdtemp(prefix="bridge_cp_test_")
    store = CheckpointStore(backend="file", directory=tmpdir)
    yield store, tmpdir
    store.clear()


@pytest.fixture
def sample_checkpoint():
    return BridgeCheckpoint(
        checkpoint_id="bcp_test_001",
        agent_id="agent_001",
        task_id="task_001",
        step_index=2,
        state="executing",
        plan_snapshot={"steps": [{"action": "采集"}, {"action": "分析"}]},
        context={"key": "value", "nested": {"a": 1}},
        metadata={"source": "test"},
    )


# ──────────────────────────────────────────────────────────────
# 1. 检查点保存加载测试
# ──────────────────────────────────────────────────────────────

class TestCheckpointSaveLoad:
    def test_save_and_load_memory(self, memory_store, sample_checkpoint):
        """内存 backend 保存和加载。"""
        cid = memory_store.save(sample_checkpoint)
        assert cid == "bcp_test_001"

        loaded = memory_store.load(cid)
        assert loaded is not None
        assert loaded.checkpoint_id == "bcp_test_001"
        assert loaded.agent_id == "agent_001"
        assert loaded.state == "executing"
        assert loaded.step_index == 2
        assert loaded.context["key"] == "value"

    def test_load_nonexistent_returns_none(self, memory_store):
        """加载不存在的检查点返回 None。"""
        assert memory_store.load("nonexistent") is None

    def test_save_and_load_file(self, file_store, sample_checkpoint):
        """文件 backend 保存和加载。"""
        store, tmpdir = file_store
        cid = store.save(sample_checkpoint)
        loaded = store.load(cid)
        assert loaded is not None
        assert loaded.checkpoint_id == "bcp_test_001"
        assert loaded.plan_snapshot["steps"][0]["action"] == "采集"

    def test_file_backend_creates_file(self, file_store, sample_checkpoint):
        """文件 backend 实际创建 JSON 文件。"""
        store, tmpdir = file_store
        store.save(sample_checkpoint)
        files = os.listdir(tmpdir)
        assert len(files) == 1
        assert files[0].endswith(".json")

    def test_list_all(self, memory_store):
        """列出所有检查点。"""
        for i in range(3):
            cp = BridgeCheckpoint(
                checkpoint_id=f"bcp_{i}",
                agent_id=f"agent_{i % 2}",
                task_id="task_common",
                state="running",
            )
            memory_store.save(cp)
        all_cps = memory_store.list()
        assert len(all_cps) == 3

    def test_list_by_agent_id(self, memory_store):
        """按 agent_id 过滤。"""
        for i in range(3):
            cp = BridgeCheckpoint(
                checkpoint_id=f"bcp_{i}",
                agent_id=f"agent_{i % 2}",
                state="running",
            )
            memory_store.save(cp)
        agent0 = memory_store.list(agent_id="agent_0")
        assert len(agent0) == 2
        assert all(c.agent_id == "agent_0" for c in agent0)

    def test_delete(self, memory_store, sample_checkpoint):
        """删除检查点。"""
        memory_store.save(sample_checkpoint)
        assert memory_store.load("bcp_test_001") is not None
        assert memory_store.delete("bcp_test_001") is True
        assert memory_store.load("bcp_test_001") is None

    def test_delete_nonexistent(self, memory_store):
        """删除不存在的检查点返回 False。"""
        assert memory_store.delete("nonexistent") is False

    def test_load_returns_deep_copy(self, memory_store, sample_checkpoint):
        """加载返回深拷贝，修改不影响存储。"""
        memory_store.save(sample_checkpoint)
        loaded = memory_store.load("bcp_test_001")
        loaded.context["key"] = "MUTATED"
        reloaded = memory_store.load("bcp_test_001")
        assert reloaded.context["key"] == "value"


# ──────────────────────────────────────────────────────────────
# 2. rehydrate 恢复测试
# ──────────────────────────────────────────────────────────────

class TestRehydrate:
    def test_rehydrate_restores_state(self, memory_store, sample_checkpoint):
        """rehydrate 从检查点恢复运行状态。"""
        memory_store.save(sample_checkpoint)
        state = rehydrate("bcp_test_001", store=memory_store)

        assert state["checkpoint_id"] == "bcp_test_001"
        assert state["agent_id"] == "agent_001"
        assert state["task_id"] == "task_001"
        assert state["step_index"] == 2
        assert state["state"] == "executing"
        assert state["status"] == "restored"
        assert "restored_at" in state

    def test_rehydrate_preserves_context(self, memory_store, sample_checkpoint):
        """rehydrate 保留 context。"""
        memory_store.save(sample_checkpoint)
        state = rehydrate("bcp_test_001", store=memory_store)
        assert state["context"]["key"] == "value"
        assert state["context"]["nested"]["a"] == 1

    def test_rehydrate_nonexistent_raises(self, memory_store):
        """rehydrate 不存在的检查点抛 KeyError。"""
        with pytest.raises(KeyError, match="checkpoint not found"):
            rehydrate("nonexistent", store=memory_store)

    def test_rehydrate_with_default_store(self, sample_checkpoint):
        """使用默认 store 时 rehydrate 正常工作。"""
        from agent_bridge.checkpoint import _default_store
        _default_store.save(sample_checkpoint)
        try:
            state = rehydrate("bcp_test_001")
            assert state["agent_id"] == "agent_001"
        finally:
            _default_store.delete("bcp_test_001")


# ──────────────────────────────────────────────────────────────
# 3. resume 继续测试
# ──────────────────────────────────────────────────────────────

class TestResume:
    def test_resume_restores_and_advances(self, memory_store, sample_checkpoint):
        """resume 恢复状态并推进 step_index。"""
        memory_store.save(sample_checkpoint)
        state = resume("bcp_test_001", store=memory_store)

        assert state["status"] == "resumed"
        assert state["step_index"] == 2
        assert state["next_step_index"] == 3
        assert "resumed_at" in state

    def test_resume_merges_new_context(self, memory_store, sample_checkpoint):
        """resume 合并新上下文。"""
        memory_store.save(sample_checkpoint)
        new_context = {"new_key": "new_value", "key": "overridden"}
        state = resume("bcp_test_001", new_context=new_context, store=memory_store)

        assert state["context"]["new_key"] == "new_value"
        assert state["context"]["key"] == "overridden"
        # 原有嵌套 context 保留
        assert state["context"]["nested"]["a"] == 1

    def test_resume_creates_resume_checkpoint(self, memory_store, sample_checkpoint):
        """resume 创建恢复检查点用于审计。"""
        memory_store.save(sample_checkpoint)
        state = resume("bcp_test_001", store=memory_store)

        assert "resume_checkpoint_id" in state
        resume_cp = memory_store.load(state["resume_checkpoint_id"])
        assert resume_cp is not None
        assert resume_cp.state == "resumed"
        assert resume_cp.metadata["resumed_from"] == "bcp_test_001"

    def test_resume_nonexistent_raises(self, memory_store):
        """resume 不存在的检查点抛 KeyError。"""
        with pytest.raises(KeyError):
            resume("nonexistent", store=memory_store)


# ──────────────────────────────────────────────────────────────
# 4. 与 DurableAdapter Checkpoint 兼容测试
# ──────────────────────────────────────────────────────────────

class TestDurableCompatibility:
    def test_bridge_checkpoint_fields_align(self):
        """BridgeCheckpoint 字段与 Durable Checkpoint 完全对齐。"""
        durable_fields = {f.name for f in DurableCheckpoint.__dataclass_fields__.values()}
        bridge_fields = {f.name for f in BridgeCheckpoint.__dataclass_fields__.values()}
        assert durable_fields == bridge_fields

    def test_from_durable_checkpoint_instance(self):
        """可从 Durable Checkpoint 实例构建 BridgeCheckpoint。"""
        durable = DurableCheckpoint(
            checkpoint_id="cp_durable",
            agent_id="agent_d",
            task_id="task_d",
            step_index=5,
            state="completed",
            plan_snapshot={"done": True},
            context={"result": "ok"},
        )
        bridge = BridgeCheckpoint.from_durable_checkpoint(durable)
        assert bridge.checkpoint_id == "cp_durable"
        assert bridge.agent_id == "agent_d"
        assert bridge.state == "completed"
        assert bridge.step_index == 5

    def test_to_durable_checkpoint_dict(self, sample_checkpoint):
        """BridgeCheckpoint 可导出为 Durable Checkpoint 兼容 dict。"""
        cp_dict = sample_checkpoint.to_durable_checkpoint_dict()
        # 可以用 DurableCheckpoint 的字段来验证
        durable = DurableCheckpoint(**cp_dict)
        assert durable.checkpoint_id == "bcp_test_001"
        assert durable.agent_id == "agent_001"
        assert durable.state == "executing"

    def test_roundtrip_durable_bridge(self):
        """Durable → Bridge → Durable 往返。"""
        original = DurableCheckpoint(
            agent_id="a1", task_id="t1", step_index=3, state="running",
            context={"k": "v"},
        )
        bridge = BridgeCheckpoint.from_durable_checkpoint(original)
        restored_dict = bridge.to_durable_checkpoint_dict()
        restored = DurableCheckpoint(**restored_dict)

        assert restored.agent_id == original.agent_id
        assert restored.task_id == original.task_id
        assert restored.step_index == original.step_index
        assert restored.state == original.state
        assert restored.context == original.context


# ──────────────────────────────────────────────────────────────
# 5. JSON 序列化测试
# ──────────────────────────────────────────────────────────────

class TestCheckpointJson:
    def test_to_json_from_json(self, sample_checkpoint):
        """BridgeCheckpoint JSON 往返。"""
        json_str = sample_checkpoint.to_json()
        restored = BridgeCheckpoint.from_json(json_str)
        assert restored.checkpoint_id == sample_checkpoint.checkpoint_id
        assert restored.context == sample_checkpoint.context
        assert restored.plan_snapshot == sample_checkpoint.plan_snapshot

    def test_json_is_valid(self, sample_checkpoint):
        """to_json 输出是合法 JSON。"""
        json_str = sample_checkpoint.to_json(indent=2)
        parsed = json.loads(json_str)
        assert parsed["checkpoint_id"] == "bcp_test_001"
        assert parsed["state"] == "executing"


# ──────────────────────────────────────────────────────────────
# 6. Store 初始化测试
# ──────────────────────────────────────────────────────────────

class TestStoreInit:
    def test_invalid_backend_raises(self):
        """无效 backend 抛 ValueError。"""
        with pytest.raises(ValueError, match="unsupported backend"):
            CheckpointStore(backend="invalid")

    def test_file_backend_requires_directory(self):
        """文件 backend 需要 directory。"""
        with pytest.raises(ValueError, match="directory is required"):
            CheckpointStore(backend="file")

    def test_file_backend_creates_directory(self):
        """文件 backend 自动创建目录。"""
        tmpdir = os.path.join(tempfile.gettempdir(), f"bridge_test_{os.getpid()}")
        if os.path.exists(tmpdir):
            import shutil
            shutil.rmtree(tmpdir)
        store = CheckpointStore(backend="file", directory=tmpdir)
        assert os.path.exists(tmpdir)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
