"""V2 P0 新模块综合测试（OSAI 侧）

覆盖：Skill Execution Contract, Effect Fence / Idempotency
"""
import sys
import pytest

sys.path.insert(0, r"D:\Zachary OS AI")


class TestSkillExecutionContract:
    def test_contract_creation(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Source Audit",
            category="engineering", status="IMPLEMENTED",
        )
        assert c.skill_id == "S01"
        assert c.status == "IMPLEMENTED"

    def test_validate_input_valid(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            input_schema={
                "required": ["repo_path"],
                "properties": {"repo_path": {"type": "string"}},
            },
        )
        result = c.validate_input({"repo_path": "/tmp/repo"})
        assert result["valid"] is True

    def test_validate_input_missing_required(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            input_schema={"required": ["repo_path"]},
        )
        result = c.validate_input({})
        assert result["valid"] is False
        assert "repo_path" in result["errors"][0]

    def test_can_execute_allowed(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            status="IMPLEMENTED", required_permission="READ",
        )
        result = c.can_execute("EXECUTE", [])
        assert result["allowed"] is True

    def test_can_execute_permission_denied(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            status="IMPLEMENTED", required_permission="COMMIT",
        )
        result = c.can_execute("READ", [])
        assert result["allowed"] is False
        assert "permission" in result["reason"]

    def test_can_execute_disabled_skill(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            status="DISABLED",
        )
        result = c.can_execute("EXECUTE", [])
        assert result["allowed"] is False

    def test_can_execute_requires_approval(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(
            skill_id="S01", version="1.0", name="Test",
            status="IMPLEMENTED", requires_approval=True,
        )
        result = c.can_execute("EXECUTE", [], has_approval=False)
        assert result["allowed"] is False
        result2 = c.can_execute("EXECUTE", [], has_approval=True)
        assert result2["allowed"] is True

    def test_to_dict(self):
        from osai_engine.skill_execution_contract import SkillExecutionContract
        c = SkillExecutionContract(skill_id="S01", version="1.0", name="Test")
        d = c.to_dict()
        assert d["skill_id"] == "S01"
        assert "retry" in d
        assert "evidence" in d
        assert "evaluation" in d


class TestEffectFence:
    def test_reserve_new(self):
        from osai_engine.effect_fence import EffectFence, EFFECT_RESERVED
        fence = EffectFence()
        rec = fence.reserve("send_email", {"to": "x@y.com"})
        assert rec.status == EFFECT_RESERVED
        assert rec.effect_id.startswith("eff_")

    def test_idempotent_duplicate(self):
        from osai_engine.effect_fence import EffectFence, EFFECT_DUPLICATE
        fence = EffectFence()
        rec1 = fence.reserve("send_email", {"to": "x@y.com"}, idempotency_key="req-1")
        fence.start(rec1.effect_id)
        fence.commit(rec1.effect_id, {"sent": True})
        rec2 = fence.reserve("send_email", {"to": "x@y.com"}, idempotency_key="req-1")
        assert rec2.status == EFFECT_DUPLICATE
        assert rec2.result == {"sent": True}

    def test_commit(self):
        from osai_engine.effect_fence import EffectFence, EFFECT_COMMITTED
        fence = EffectFence()
        rec = fence.reserve("write_db", {"id": 1})
        fence.start(rec.effect_id)
        result = fence.commit(rec.effect_id, {"written": True})
        assert result.status == EFFECT_COMMITTED
        assert result.result == {"written": True}

    def test_fail_allows_retry(self):
        from osai_engine.effect_fence import EffectFence, EFFECT_FAILED, EFFECT_DUPLICATE
        fence = EffectFence()
        rec = fence.reserve("send_email", {"to": "x@y.com"}, idempotency_key="req-2")
        fence.start(rec.effect_id)
        fence.fail(rec.effect_id, "smtp error")
        # 失败后可以重新 reserve
        rec2 = fence.reserve("send_email", {"to": "x@y.com"}, idempotency_key="req-2")
        assert rec2.status != EFFECT_DUPLICATE

    def test_parameters_hash(self):
        from osai_engine.effect_fence import EffectFence
        h1 = EffectFence.hash_parameters({"a": 1, "b": 2})
        h2 = EffectFence.hash_parameters({"b": 2, "a": 1})
        assert h1 == h2  # 排序后哈希一致

    def test_summary(self):
        from osai_engine.effect_fence import EffectFence
        fence = EffectFence()
        fence.reserve("action1", {})
        s = fence.summary()
        assert sum(s.values()) >= 1


class TestInvocationRecord:
    def test_creation(self):
        from osai_engine.skill_execution_contract import InvocationRecord, new_invocation_id, new_trace_id
        rec = InvocationRecord(
            invocation_id=new_invocation_id(),
            skill_id="S01", skill_version="1.0", trace_id=new_trace_id(),
        )
        assert rec.invocation_id.startswith("inv_")
        assert rec.trace_id.startswith("trace_")
        assert rec.status == "QUEUED"

    def test_complete(self):
        from osai_engine.skill_execution_contract import InvocationRecord, new_invocation_id, new_trace_id
        rec = InvocationRecord(
            invocation_id=new_invocation_id(),
            skill_id="S01", skill_version="1.0", trace_id=new_trace_id(),
        )
        rec.complete("COMPLETED", provider="zhipu", model="glm-4.5-air")
        assert rec.status == "COMPLETED"
        assert rec.provider == "zhipu"
        assert rec.duration_ms is not None

    def test_to_dict(self):
        from osai_engine.skill_execution_contract import InvocationRecord, new_invocation_id, new_trace_id
        rec = InvocationRecord(
            invocation_id=new_invocation_id(),
            skill_id="S01", skill_version="1.0", trace_id=new_trace_id(),
        )
        d = rec.to_dict()
        assert "invocation_id" in d
        assert "skill_id" in d
        assert "status" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
