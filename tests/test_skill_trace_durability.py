"""Skill completion requires durable readback, without invoking any AI provider.

Boundary fixtures isolate permission/fence/evidence; these tests establish the
trace contract, not real authorization or provider quality.
"""
import json
import sqlite3

import pytest
from lumenis.shared.agents.skills import execution


@pytest.fixture
def chain(monkeypatch, tmp_path):
    path = tmp_path / "skill-traces.sqlite3"
    import account.models
    monkeypatch.setattr(account.models, "get_db", lambda: sqlite3.connect(path))
    monkeypatch.setattr(execution, "check_permission", lambda *a, **k: {"allowed": True})
    monkeypatch.setattr(execution, "action_firewall", lambda *a, **k: {"allowed": True})
    monkeypatch.setattr(execution, "effect_fence", lambda *a, **k: {"allowed": True})
    monkeypatch.setattr(execution, "_reserve_package_execution", lambda *a, **k: None)
    monkeypatch.setattr(execution, "record_execution_evidence", lambda *a, **k: {"ok": True})
    return path


def _run():
    return execution.run_execution_chain(
        "local.test", task="Compute deterministic count", user_id=1,
        handler=lambda ctx: {"status": "completed", "count": 3},
    )


def test_builtin_result_reopens_from_real_sqlite_without_model(chain):
    result = _run()
    assert result.status is execution.ExecutionStatus.COMPLETED
    with sqlite3.connect(chain) as conn:
        row = conn.execute(
            "SELECT status, output_json FROM skill_executions WHERE execution_id=?",
            (result.execution_id,),
        ).fetchone()
    assert row[0] == "completed"
    assert json.loads(row[1])["result"]["count"] == 3


def test_builtin_trace_failure_cannot_claim_completed(chain, monkeypatch):
    import account.models
    def unavailable():
        raise sqlite3.OperationalError("isolated disk unavailable")
    monkeypatch.setattr(account.models, "get_db", unavailable)
    result = _run()
    assert result.status is execution.ExecutionStatus.FAILED
    assert result.error == "SKILL_EXECUTION_TRACE_FINALIZATION_FAILED"
    assert result.execute_result["result"]["count"] == 3  # Preserve executed output for recovery.


def test_trace_failure_preserves_original_business_failure(chain, monkeypatch):
    monkeypatch.setattr(execution, "write_trace", lambda *a, **k: False)
    result = execution.run_execution_chain(
        "local.test", handler=lambda ctx: {"status": "failed", "error": "input invalid"},
    )
    assert result.status is execution.ExecutionStatus.FAILED
    assert result.error != "SKILL_EXECUTION_TRACE_FINALIZATION_FAILED"


def test_complete_large_trace_is_not_replaced_by_digest(tmp_path, monkeypatch):
    import json
    from lumenis.shared.agents.skills.execution import (
        SkillExecutionContext, ExecutionStatus, write_trace, query_executions)
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'large-trace.sqlite'))
    original = {'text': '长内容完整保留' * 30000}
    ctx = SkillExecutionContext(skill_id='fixture.local', status=ExecutionStatus.COMPLETED,
                                execute_result={'success': True, 'result': original})
    assert write_trace(ctx)
    row = query_executions(execution_id=ctx.execution_id, strict=True)[0]
    assert json.loads(row['output_json'])['result'] == original


def test_trace_size_limit_is_explicit_before_success():
    import pytest
    from lumenis.shared.agents.skills.execution import _trace_json
    with pytest.raises(ValueError, match='SKILL_TRACE_PAYLOAD_TOO_LARGE'):
        _trace_json({'text': 'large'}, limit=2)
