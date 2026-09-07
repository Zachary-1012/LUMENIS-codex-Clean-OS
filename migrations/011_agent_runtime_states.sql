-- Migration: 011_agent_runtime_states.sql
-- Purpose: Agent Runtime 状态持久化表
-- Date: 2026-09-07
-- Note: 此脚本不自动执行，需人工确认后手动执行。
--       向后兼容：不修改现有表，仅新增表。

-- Agent Runtime 状态表（Agent 实例级状态持久化）
CREATE TABLE IF NOT EXISTS agent_runtime_states (
    agent_id        TEXT PRIMARY KEY,              -- Agent 唯一标识
    state           TEXT NOT NULL DEFAULT 'idle',  -- idle/planning/executing/observing/replanning/waiting_approval/completed/failed/cancelled
    goal            TEXT DEFAULT '',               -- 自然语言目标
    task_id         TEXT DEFAULT '',               -- 关联 ai_task.task_id
    current_step    INTEGER DEFAULT 0,             -- 当前步骤索引
    total_steps     INTEGER DEFAULT 0,             -- 总步骤数
    replan_count    INTEGER DEFAULT 0,             -- 重规划次数
    retry_count     INTEGER DEFAULT 0,             -- 重试次数
    elapsed_seconds REAL DEFAULT 0.0,              -- 已运行秒数
    estimated_cost  REAL DEFAULT 0.0,              -- 估算成本（美元）
    error           TEXT DEFAULT NULL,             -- 错误信息
    transitions_json TEXT DEFAULT '[]',            -- 状态转换历史（JSON 数组，最近50条）
    plan_json       TEXT DEFAULT NULL,             -- 当前计划快照（JSON）
    context_json    TEXT DEFAULT NULL,             -- 上下文快照（JSON）
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 索引：按状态查询活跃 Agent
CREATE INDEX IF NOT EXISTS idx_agent_runtime_states_state
    ON agent_runtime_states(state);

-- 索引：按 task_id 查询
CREATE INDEX IF NOT EXISTS idx_agent_runtime_states_task_id
    ON agent_runtime_states(task_id);

-- 索引：按更新时间查询（清理过期记录）
CREATE INDEX IF NOT EXISTS idx_agent_runtime_states_updated_at
    ON agent_runtime_states(updated_at);

-- 说明：
-- 1. 本表为 Agent Runtime Core 的可选持久化层，不创建也不影响功能（内存态可正常运行）
-- 2. 复用 runtime_guardian_workers 表也是可行方案，但独立表更清晰
-- 3. 所有字段均为可选，向后兼容
-- 4. 不修改 monitor.db 的任何现有表或字段
