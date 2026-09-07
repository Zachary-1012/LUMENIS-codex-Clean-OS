# -*- coding: utf-8 -*-
"""
Unit tests for agent_runtime.state_machine
覆盖：状态转换、非法转换拒绝、取消/失败/完成、进度更新、快照、持久化
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_runtime.state_machine import (
    AgentState, AgentStateMachine, StateTransitionError,
    AgentStateStore, AgentStateSnapshot, VALID_TRANSITIONS,
)


class TestAgentStateEnum:
    def test_terminal_states(self):
        assert AgentState.COMPLETED.is_terminal
        assert AgentState.FAILED.is_terminal
        assert AgentState.CANCELLED.is_terminal
        assert not AgentState.IDLE.is_terminal
        assert not AgentState.EXECUTING.is_terminal

    def test_active_states(self):
        assert AgentState.PLANNING.is_active
        assert AgentState.EXECUTING.is_active
        assert AgentState.OBSERVING.is_active
        assert not AgentState.IDLE.is_active
        assert not AgentState.COMPLETED.is_active


class TestStateTransitions:
    def test_valid_transition_idle_to_planning(self):
        sm = AgentStateMachine()
        assert sm.state == AgentState.IDLE
        new_state = sm.transition_to(AgentState.PLANNING)
        assert new_state == AgentState.PLANNING
        assert sm.state == AgentState.PLANNING

    def test_valid_transition_planning_to_executing(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        assert sm.state == AgentState.EXECUTING

    def test_valid_transition_executing_to_observing(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.OBSERVING)
        assert sm.state == AgentState.OBSERVING

    def test_valid_transition_observing_to_replanning(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.OBSERVING)
        sm.transition_to(AgentState.REPLANNING)
        assert sm.state == AgentState.REPLANNING

    def test_valid_transition_replanning_to_executing(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.OBSERVING)
        sm.transition_to(AgentState.REPLANNING)
        sm.transition_to(AgentState.EXECUTING)
        assert sm.state == AgentState.EXECUTING

    def test_valid_transition_executing_to_completed(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.COMPLETED)
        assert sm.state == AgentState.COMPLETED
        assert sm.is_terminal

    def test_valid_transition_executing_to_waiting_approval(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.WAITING_APPROVAL)
        assert sm.state == AgentState.WAITING_APPROVAL

    def test_waiting_approval_to_executing(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.WAITING_APPROVAL)
        sm.transition_to(AgentState.EXECUTING)
        assert sm.state == AgentState.EXECUTING


class TestIllegalTransitions:
    def test_idle_to_executing_illegal(self):
        sm = AgentStateMachine()
        with pytest.raises(StateTransitionError) as exc_info:
            sm.transition_to(AgentState.EXECUTING)
        assert "idle" in str(exc_info.value).lower()
        assert "executing" in str(exc_info.value).lower()

    def test_completed_to_executing_illegal(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.COMPLETED)
        with pytest.raises(StateTransitionError):
            sm.transition_to(AgentState.EXECUTING)

    def test_failed_to_executing_illegal(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.fail("test error")
        with pytest.raises(StateTransitionError):
            sm.transition_to(AgentState.EXECUTING)

    def test_cancelled_to_executing_illegal(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.cancel()
        with pytest.raises(StateTransitionError):
            sm.transition_to(AgentState.EXECUTING)

    def test_planning_to_observing_illegal(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        with pytest.raises(StateTransitionError):
            sm.transition_to(AgentState.OBSERVING)


class TestCanTransition:
    def test_can_transition_to_valid(self):
        sm = AgentStateMachine()
        assert sm.can_transition_to(AgentState.PLANNING)
        assert not sm.can_transition_to(AgentState.EXECUTING)

    def test_can_transition_from_terminal(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.COMPLETED)
        assert not sm.can_transition_to(AgentState.EXECUTING)
        assert not sm.can_transition_to(AgentState.PLANNING)


class TestCancelAndFail:
    def test_cancel_from_planning(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        result = sm.cancel(reason="user cancelled")
        assert result == AgentState.CANCELLED
        assert sm.state == AgentState.CANCELLED

    def test_cancel_from_executing(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.cancel()
        assert sm.state == AgentState.CANCELLED

    def test_cancel_from_terminal_noop(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        sm.transition_to(AgentState.COMPLETED)
        sm.cancel()  # should not change
        assert sm.state == AgentState.COMPLETED

    def test_fail_with_error(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.fail("something went wrong", reason="execution error")
        assert sm.state == AgentState.FAILED
        snapshot = sm.snapshot()
        assert snapshot.error == "something went wrong"

    def test_complete(self):
        sm = AgentStateMachine(goal="test goal")
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING)
        result = sm.complete(reason="all done")
        assert result == AgentState.COMPLETED
        assert sm.state == AgentState.COMPLETED


class TestProgressAndSnapshot:
    def test_update_progress(self):
        sm = AgentStateMachine()
        sm.update_progress(current_step=3, total_steps=10, replan_count=1, retry_count=2, cost=0.5)
        snap = sm.snapshot()
        assert snap.current_step == 3
        assert snap.total_steps == 10
        assert snap.replan_count == 1
        assert snap.retry_count == 2
        assert snap.estimated_cost == 0.5

    def test_transition_metadata_updates_progress(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING)
        sm.transition_to(AgentState.EXECUTING, metadata={"step": 2, "total_steps": 5})
        snap = sm.snapshot()
        assert snap.current_step == 2
        assert snap.total_steps == 5

    def test_snapshot_structure(self):
        sm = AgentStateMachine(agent_id="test_agent", goal="test goal")
        sm.transition_to(AgentState.PLANNING, reason="start")
        snap = sm.snapshot()
        assert snap.agent_id == "test_agent"
        assert snap.goal == "test goal"
        assert snap.state == "planning"
        assert snap.created_at
        assert snap.updated_at
        assert isinstance(snap.transitions, list)
        assert len(snap.transitions) >= 1

    def test_transition_history(self):
        sm = AgentStateMachine()
        sm.transition_to(AgentState.PLANNING, reason="r1")
        sm.transition_to(AgentState.EXECUTING, reason="r2")
        history = sm.transition_history()
        assert len(history) == 2
        assert history[0]["from_state"] == "idle"
        assert history[0]["to_state"] == "planning"
        assert history[1]["from_state"] == "planning"
        assert history[1]["to_state"] == "executing"

    def test_agent_id_auto_generated(self):
        sm1 = AgentStateMachine()
        sm2 = AgentStateMachine()
        assert sm1.agent_id != sm2.agent_id
        assert sm1.agent_id.startswith("agent_")


class TestStateStore:
    def test_save_and_load(self):
        store = AgentStateStore()
        sm = AgentStateMachine(agent_id="agent_1", goal="test")
        sm.transition_to(AgentState.PLANNING)
        store.save(sm.snapshot())
        loaded = store.load("agent_1")
        assert loaded is not None
        assert loaded.agent_id == "agent_1"
        assert loaded.state == "planning"

    def test_load_nonexistent(self):
        store = AgentStateStore()
        assert store.load("nonexistent") is None

    def test_list_active(self):
        store = AgentStateStore()
        sm1 = AgentStateMachine(agent_id="active_1")
        sm1.transition_to(AgentState.PLANNING)
        store.save(sm1.snapshot())

        sm2 = AgentStateMachine(agent_id="done_1")
        sm2.transition_to(AgentState.PLANNING)
        sm2.transition_to(AgentState.EXECUTING)
        sm2.transition_to(AgentState.COMPLETED)
        store.save(sm2.snapshot())

        active = store.list_active()
        assert len(active) == 1
        assert active[0].agent_id == "active_1"

    def test_remove(self):
        store = AgentStateStore()
        sm = AgentStateMachine(agent_id="to_remove")
        store.save(sm.snapshot())
        store.remove("to_remove")
        assert store.load("to_remove") is None

    def test_persist_callback(self):
        persisted = []
        def callback(snapshot):
            persisted.append(snapshot.agent_id)
        sm = AgentStateMachine(agent_id="cb_test", persist_callback=callback)
        sm.transition_to(AgentState.PLANNING)
        assert "cb_test" in persisted


class TestAllStatesHaveTransitions:
    def test_every_state_has_transition_entry(self):
        for state in AgentState:
            assert state in VALID_TRANSITIONS, f"Missing transitions for {state}"

    def test_terminal_states_have_empty_transitions(self):
        assert VALID_TRANSITIONS[AgentState.COMPLETED] == set()
        assert VALID_TRANSITIONS[AgentState.FAILED] == set()
        assert VALID_TRANSITIONS[AgentState.CANCELLED] == set()
