# ZBC × OSAI Agent Runtime 实施计划（草案）

## 基于 ZBC 能力审计（zbc_capability_matrix.md）

### 已有可复用模块（15个，禁止重写）
1. permission_gate — 权限门/fail-closed/operation注册
2. action_firewall — 动作防火墙（在skill_execution_chain中）
3. effect_fence — 效果围栏（在skill_execution_chain中）
4. evidence_chain/evidence_store — 证据链
5. ai_task_engine — AI任务执行（checkpoint/retry/recover）
6. runtime_guardian — 运行时守护/circuit_breaker
7. ai_gateway/provider_registry — AI网关/智谱GLM
8. skill_registry/skills_registry — 技能注册
9. skill_execution_contract/chain — 技能执行契约链
10. lumenis_skill_adapter — 技能适配器
11. trace/ai_task_trace — 执行追踪
12. evaluation — 评估系统
13. human_approval — 人工审批
14. durable_execution — 持久执行（pause/resume/cancel）
15. memory_optimizer — 内存优化（非长期记忆）

### 需补齐的 MISSING 项（3个）
1. **Observation Layer** — 环境感知层（Agent感知当前状态/数据/工具可用性）
2. **Replanning** — 重规划（任务失败后调整策略而非同参数retry）
3. **Trajectory Evaluation** — 轨迹评估（评估Agent执行路径质量）

### 需深化的 PARTIAL 项（4个）
1. **Agent Loop 预算控制** — max_steps/max_time/max_cost/max_retries/max_replans
2. **分层 Memory** — Working/Task/Episodic/Semantic/Skill/Learning（当前只有ai_task_evidence/feedback_keywords等零散表）
3. **Tool Router** — 统一工具路由（219个API路由无统一路由层）
4. **Planner** — 任务规划器（当前有task_parser但非Goal-driven Planner）

### 实施优先级
- P0: Observation Layer + Agent Loop预算控制（安全基线）
- P1: Replanning + 分层Memory + Tool Router
- P2: Trajectory Evaluation + Planner深化 + Learning Loop

### 与 OSAI 对齐方式（Contract，无运行时依赖）
- OSAI = Intelligence/Reasoning/Planning/Memory/Learning（通过Contract提供规划/推理/记忆接口）
- ZBC = Production Truth/Data/Tools/Execution/Effect Boundary（执行层）
- Contract接口：Goal → Plan → Execute → Observe → Replan → Evaluate → Learn
