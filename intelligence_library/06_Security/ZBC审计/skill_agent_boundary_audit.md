# ZBC Phase 13 — Skill / Agent 边界规范审计报告

> 生成时间：2026-09-06
> 分支：feat/zbc-full-upgrade-v1
> HEAD：5e0ccd0
> 审计范围：Skill 元数据规范、Agent 权限边界、现有模块适配、测试验证
> 遵循原则：AGENTS.md §13 修改安全协议（先审计、再修改；先旁路、再切换；先验证、再交付）

---

## 1. 现有 Skill/Agent 模块审计表

| # | 模块 | 路径 | 状态 | 职责 | 风险点 | Phase 13 处理 |
|---|------|------|------|------|--------|---------------|
| 1 | .skills-router/ | `.skills-router/` | EMPTY / PLACEHOLDER | 预留 Skill 路由目录，仅含空 `rednote/` 子目录 | 无实际代码，无风险 | 不修改，保留为未来 Skill 路由扩展点 |
| 2 | Lumenis Skill Adapter | `lumenis_skill_adapter.py` | ACTIVE | ZBC → OSAI Canonical Registry 跨仓只读适配器；通过 subprocess 调用 OSAI | 无 SkillMetadata 模型；invoke_skill 默认最小权限（READ/AUDIT/ANALYZE 等），不含 COMMIT/PUSH | 新增 `to_skill_metadata()` / `list_skills_as_metadata()` 兼容层；添加 `_MODULE_STATUS="ACTIVE"` 标记 |
| 3 | Function Registry | `function_registry.py` | ACTIVE | 函数/数据目标映射与统一检索层；FUNCTION_MAP 14 项功能映射 | 无 Skill 注册概念；纯查询路由，无写操作 | 新增 `register_functions_as_skills()` 将 FUNCTION_MAP 注册为 LOW 风险 READ_ONLY Skill |
| 4 | Dev Exec Core | `dev_exec_core.py` | ACTIVE | GAP-04 三 run-code 统一收口核心；guard_func 注入 + 审计日志 + 代码指纹 | exec 在受限命名空间执行；已有 guard_func 但无 AgentBoundary 层 | 新增 `agent_boundary_check()` 可选旁路检查（fail-open 兼容现有 guard_func） |
| 5 | Agent Security | `agent_security.py` | LEGACY | Prompt Injection 五层防御（输入净化/指令检测/参数校验/输出过滤/蜜罐） | 已标记 Legacy；全局权限由 permission_gate.py + security_boundary.py 编排 | 保留全部功能；添加 `_MODULE_STATUS="LEGACY"` 及 Legacy 原因说明 |
| 6 | Schema Registry | `schema_registry.py` | ACTIVE | 只读 DB Schema 反射 + CREATE 声明来源映射 | 与 Skill/Agent 边界无直接关系 | 不修改（非本次范围） |
| 7 | CI/CD | `ci_cd.py` | ACTIVE | 自动化测试/构建/部署/发布 | 与 Skill/Agent 边界无直接关系 | 不修改（非本次范围） |
| 8 | Lumenis Contract Adapter | `contracts/lumenis_adapter.py` | ACTIVE | 生产核心只读契约适配；含 LUMENIS_RED_LINES（Skill无无限权限、Agent不绕过HUMAN_APPROVAL） | 只读，无风险 | 不修改（已包含红线约束，与本次目标一致） |

### 审计结论

- **无模块被删除**：所有现有模块保留，仅添加兼容层。
- **无 SUBJECT_WORDS / subject_hit() 修改**：主体口径未触碰。
- **无生产数据库变更**：本次不涉及 DDL/DML。
- **Agent 无超级权限路径**：现有 agent_security.py 的 ALLOWED_TOOLS 白名单仅含只读工具；lumenis_skill_adapter 的 invoke_skill 默认权限不含 COMMIT/PUSH/HUMAN_APPROVAL。

---

## 2. skill_registry.py 核心 API

### 2.1 枚举

| 枚举 | 值 | 说明 |
|------|-----|------|
| `RiskLevel` | LOW / MEDIUM / HIGH / CRITICAL | Skill 风险等级 |
| `ExecutionPolicy` | READ_ONLY / AUDIT_ONLY / APPROVAL_REQUIRED / AUTO_EXECUTE | 执行策略 |
| `EvaluationStatus` | PLANNED / PARTIAL / EVALUATED / DEPRECATED | 评估状态 |

### 2.2 SkillMetadata（数据类）

必填字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `skill_id` | str | 唯一标识，格式 `^[a-z][a-z0-9_.]{2,63}$` |
| `version` | str | 语义版本，建议 x.y.z |
| `owner` | str | 负责人/团队 |
| `permission_level` | str | 所需权限等级（READ/AUDIT/HUMAN_APPROVAL 等） |
| `input_schema` | dict | JSON Schema 风格输入定义（非空） |
| `output_schema` | dict | JSON Schema 风格输出定义（非空） |
| `risk_level` | RiskLevel | 风险等级 |
| `execution_policy` | ExecutionPolicy | 执行策略 |
| `evidence_contract` | str | 证据契约描述 |
| `evaluation_status` | EvaluationStatus | 评估状态 |

可选字段：`description`, `tags`, `created_at`, `prohibited_actions`

方法：`to_dict()`, `from_dict()`

### 2.3 SkillRegistry（类）

| 方法 | 说明 |
|------|------|
| `validate(meta)` | 验证 SkillMetadata 完整性与合规性，返回 `{valid, errors, warnings}` |
| `register(meta, force=False)` | 注册 Skill，验证不通过则拒绝（force=True 仅限开发环境） |
| `get(skill_id)` | 查询单个 Skill |
| `has(skill_id)` | 是否存在 |
| `list_all()` | 列出所有 Skill |
| `list_by_risk(risk)` | 按风险等级筛选 |
| `list_by_policy(policy)` | 按执行策略筛选 |
| `list_requiring_approval()` | 列出所有需人工审批的 Skill |
| `can_auto_execute(skill_id)` | 检查是否可自动执行（不需审批） |
| `stats()` | 返回注册表统计 |

### 2.4 硬约束（validate 强制）

1. **CRITICAL 风险不能 AUTO_EXECUTE**：必须是 APPROVAL_REQUIRED 或 AUDIT_ONLY。
2. **HIGH 风险不能 AUTO_EXECUTE**：必须是 APPROVAL_REQUIRED 或更严格。
3. **prohibited_actions 必须包含核心项**：bypass_permission_gate, write_production_data, execute_high_risk_shell, bypass_audit_trail。
4. **元数据中不得包含高风险 shell 模式**：rm -rf, sudo, format, mkfs, fork bomb 等。
5. **input/output_schema 必须非空 dict**。

### 2.5 内置只读 Skill（3 个，全部 LOW + READ_ONLY）

- `zbc.subject_authority_read` — 只读主体口径状态（计数，不暴露词表内容）
- `zbc.skill_registry_snapshot` — 只读 Skill 注册表统计
- `zbc.agent_boundary_audit` — 只读 Agent 边界审计

### 2.6 进程级单例

`get_skill_registry()` → 返回全局 SkillRegistry 单例（含内置 Skill）。

---

## 3. agent_boundary.py 核心 API

### 3.1 枚举

| 枚举 | 值 | 说明 |
|------|-----|------|
| `AgentRole` | READER / AUDITOR / ANALYST / DEVELOPER / OPERATOR / SUPER_ADMIN | Agent 角色 |
| `Permission` | READ / AUDIT / ANALYZE / RESEARCH / PLAN / PATCH_PREVIEW / TEST / VERIFY / WRITE / DELETE / EXECUTE / HUMAN_APPROVAL / COMMIT / PUSH | 权限 |
| `ActionDecision` | ALLOW / DENY / REQUIRE_APPROVAL | 操作决策 |
| `ApprovalStatus` | PENDING / APPROVED / REJECTED / EXPIRED | 审批状态 |

### 3.2 AgentIdentity（数据类）

| 字段 | 说明 |
|------|------|
| `agent_id` | 唯一标识 |
| `role` | 角色（Agent 不能是 SUPER_ADMIN） |
| `permission_scope` | 权限集合（自动合并角色默认权限，自动移除 denylist） |
| `allowed_tools` | 工具白名单（空则用默认白名单） |
| `denied_tools` | 工具黑名单（自动合并默认黑名单） |
| `is_human` | 是否人类（SUPER_ADMIN 仅限人类） |

**硬约束（__post_init__ 强制）**：
- Agent（is_human=False）不能持有 SUPER_ADMIN 角色。
- Agent 永远不能持有 COMMIT / PUSH / DELETE 权限（AGENT_PERMISSION_DENYLIST）。
- allowed_tools 与 denied_tools 互斥（denylist 优先）。
- 默认角色 AUDITOR → 权限仅 READ + AUDIT。

方法：`has_permission(perm)`, `can_use_tool(tool_name)`, `to_dict()`

### 3.3 ActionFirewall（类）

操作防火墙，fail-close 决策链：

1. **高风险前缀** → REQUIRE_APPROVAL：delete_, drop_, grant_, revoke_, truncate_, rm_, sudo_, format_, escalate_, bypass_, modify_subject, write_production 等。
2. **高风险正则** → DENY：rm -rf, sudo, DROP TABLE, DELETE FROM, TRUNCATE, GRANT ALL, fork bomb, 磁盘覆盖, chmod 777, **SUBJECT_WORDS =**（主体词表修改）。
3. **工具黑名单** → DENY。
4. **工具白名单** → DENY（不在白名单内）。
5. **写操作权限检查** → DENY（无 WRITE/EXECUTE 权限时）。
6. **其余** → ALLOW。

方法：`check(identity, action, tool_name, params, description)`, `decision_log`

### 3.4 ApprovalManager（类）

人工审批管理：

| 方法 | 说明 |
|------|------|
| `request(identity, action, ...)` | 创建审批请求（30 分钟 TTL） |
| `approve(request_id, approver)` | 人类批准 |
| `reject(request_id, approver, reason)` | 人类拒绝 |
| `is_approved(request_id)` | 检查是否已批准（含过期检查） |
| `list_pending()` | 列出待审批请求 |

### 3.5 IdempotencyGuard（类）

操作幂等性保护：相同 (agent_id, action, params_hash) 在 300 秒窗口内只执行一次。

方法：`check(agent_id, action, params)`, `cleanup()`

### 3.6 AgentBoundary（门面类）

组合 Identity + Firewall + Approval + Idempotency 的统一入口：

| 方法 | 说明 |
|------|------|
| `create_agent(agent_id, role, ...)` | 创建 Agent（默认 AUDITOR，不能 SUPER_ADMIN） |
| `create_human(agent_id, role, ...)` | 创建人类操作员（可 SUPER_ADMIN） |
| `check_action(identity, action, ...)` | 完整检查：幂等性 → 防火墙 |
| `request_approval(...)` | 申请人工审批 |
| `execute_with_approval(identity, action, executor, ...)` | 带审批的执行入口（fail-close） |
| `stats()` | 边界统计 |

### 3.7 默认工具白/黑名单

- **白名单（19 个）**：search_notes, get_events, get_notes, query_database, get_daily_report, get_stats, get_brand_info, analyze_sentiment, analyze_trend, generate_report, summarize_content, classify_content, audit_skill, audit_agent, verify_data, check_health, skill_registry_snapshot, get_skill_metadata, agent_boundary_audit, get_agent_identity
- **黑名单（13 个）**：delete_note, delete_event, drop_table, truncate_table, execute_shell, run_command, exec_code, eval_code, modify_subject_words, write_production_db, grant_permission, revoke_permission, escalate_privilege, disable_audit, commit_code, push_code, merge_branch

---

## 4. 修改文件列表

| # | 文件 | 操作 | 说明 |
|---|------|------|------|
| 1 | `skill_registry.py` | **新增** | SkillMetadata + SkillRegistry + 风险等级 + 执行策略 + 内置只读 Skill |
| 2 | `agent_boundary.py` | **新增** | AgentIdentity + ActionFirewall + ApprovalManager + IdempotencyGuard + AgentBoundary |
| 3 | `lumenis_skill_adapter.py` | **适配** | 新增 `to_skill_metadata()` / `list_skills_as_metadata()`；添加 `_MODULE_STATUS` 标记 |
| 4 | `function_registry.py` | **适配** | 新增 `register_functions_as_skills()` 将 FUNCTION_MAP 注册为 LOW 风险 READ_ONLY Skill |
| 5 | `dev_exec_core.py` | **适配** | 新增 `agent_boundary_check()` 可选旁路检查 |
| 6 | `agent_security.py` | **适配** | 添加 `_MODULE_STATUS="LEGACY"` 及 Legacy 原因说明（功能全部保留） |
| 7 | `tests/test_skill_agent_boundary.py` | **新增** | 83 个测试用例，覆盖 11 个测试类 |
| 8 | `_phase13_adapt.py` | **新增（临时）** | 模块适配脚本，可在验证后删除 |

**未修改**：SUBJECT_WORDS, subject_hit(), app.py, risk_engine.py, database.py, 生产数据库, .skills-router/

---

## 5. 测试运行结果

### 5.1 新增测试（test_skill_agent_boundary.py）

```
collected 83 items
tests/test_skill_agent_boundary.py ...... [100%]
83 passed in 0.71s
```

### 5.2 测试覆盖分类

| 测试类 | 用例数 | 覆盖内容 |
|--------|--------|----------|
| TestSkillMetadataCompleteness | 10 | 必填字段、格式校验、schema 非空、禁止行为、shell 模式检测、roundtrip |
| TestSkillRegistry | 8 | 注册/拒绝/查询/按风险筛选/按策略筛选/统计/全局单例内置 Skill |
| TestHighRiskSkillRequiresApproval | 7 | CRITICAL/HIGH 不能 AUTO_EXECUTE、CRITICAL 必须审批、can_auto_execute、list_requiring_approval |
| TestActionFirewall | 11 | delete/drop/grant 前缀拦截、rm -rf/sudo/DROP TABLE/SUBJECT_WORDS 正则拦截、工具黑白名单、写权限检查、决策日志 |
| TestAgentNoSuperPermission | 7 | Agent 不能 SUPER_ADMIN、人类可以、默认 READ+AUDIT、denylist 强制、DEVELOPER 无 WRITE/COMMIT |
| TestToolAllowlist | 7 | 白/黑名单非空、互斥、denied_tools 合并、can_use_tool、extra 合并、extra 不能覆盖 denylist |
| TestApprovalManager | 6 | 创建/批准/拒绝/不存在/待审批列表/过期 |
| TestIdempotencyGuard | 5 | 首次不重复/二次重复/不同参数/不同 Agent/清理 |
| TestAgentBoundaryIntegration | 5 | 创建默认 Agent、防火墙+幂等组合、无审批拒绝、有审批执行、全局单例 |
| TestExistingModuleAdapters | 10 | lumenis to_skill_metadata、function_registry 注册、dev_exec boundary_check、agent_security Legacy 标记且功能保留 |
| TestAgentNoSuperPermissionComprehensive | 5 | 全角色遍历：无 SUPER_ADMIN、无 DELETE/COMMIT/PUSH、防火墙拦截 sudo/主体修改 |

### 5.3 回归测试（现有相关模块）

```
tests/test_agent_security.py  20 passed
tests/test_dev_exec_audit.py   6 passed
tests/test_dev_exec_guard.py   9 passed
tests/test_lumenis_adapter.py  7 passed
合计：42 passed, 0 failed
```

---

## 6. Agent 不能超级权限验证结果

### 6.1 角色级验证

| 角色 | 可被 Agent 持有 | 默认权限 | 含 WRITE | 含 DELETE | 含 COMMIT | 含 PUSH |
|------|-----------------|----------|---------|-----------|-----------|---------|
| READER | 是 | READ | 否 | 否 | 否 | 否 |
| AUDITOR | 是 | READ + AUDIT | 否 | 否 | 否 | 否 |
| ANALYST | 是 | READ/AUDIT/ANALYZE/RESEARCH/PLAN | 否 | 否 | 否 | 否 |
| DEVELOPER | 是 | READ/AUDIT/ANALYZE/RESEARCH/PLAN/PATCH_PREVIEW/TEST/VERIFY | 否 | 否 | 否 | 否 |
| OPERATOR | 是 | READ/AUDIT/VERIFY/TEST | 否 | 否 | 否 | 否 |
| SUPER_ADMIN | **否（Agent 禁止）** | — | — | — | — | — |

### 6.2 强制约束验证

| 约束 | 验证方式 | 结果 |
|------|----------|------|
| Agent 不能创建为 SUPER_ADMIN | `AgentIdentity(role=SUPER_ADMIN, is_human=False)` 抛 ValueError | PASS |
| AgentBoundary.create_agent(SUPER_ADMIN) 抛 ValueError | 直接调用 | PASS |
| 人类可以持有 SUPER_ADMIN | `AgentIdentity(role=SUPER_ADMIN, is_human=True)` | PASS |
| 即使显式授予 COMMIT/PUSH/DELETE 也被移除 | `AgentIdentity(permission_scope={COMMIT,PUSH,DELETE})` 后检查 | PASS |
| 所有 Agent 角色均无 DELETE 权限 | 遍历 5 个 Agent 角色 | PASS |
| 所有 Agent 角色均无 COMMIT 权限 | 遍历 5 个 Agent 角色 | PASS |
| 所有 Agent 角色均无 PUSH 权限 | 遍历 5 个 Agent 角色 | PASS |
| ActionFirewall 对所有 Agent 拦截 sudo | 遍历 5 个角色 + description="sudo ..." | PASS |
| ActionFirewall 对所有 Agent 拦截 SUBJECT_WORDS 修改 | 遍历 5 个角色 + description="SUBJECT_WORDS = []" | PASS |

### 6.3 结论

**Agent 在任何角色下都无法获得生产超级权限。** 默认权限为 READ + AUDIT，最高角色 DEVELOPER 也仅含 PATCH_PREVIEW/TEST/VERIFY，不含 WRITE/DELETE/COMMIT/PUSH。高风险操作（delete_/drop_/grant_/sudo/主体修改）被 ActionFirewall 拦截为 REQUIRE_APPROVAL 或 DENY，必须经人类审批。

---

## 7. 风险与已知限制

| # | 风险/限制 | 等级 | 说明 | 缓解措施 |
|---|-----------|------|------|----------|
| 1 | dev_exec_core.py 的 agent_boundary_check 为可选旁路 | LOW | 现有 guard_func 仍是主闸门；boundary_check 为附加层，不可用时 fail-open | 后续可在 app.py 端点中强制接入 |
| 2 | SkillRegistry 为内存注册表 | LOW | 进程重启后需重新注册；无持久化 | 后续可接入 DB 或文件持久化 |
| 3 | ApprovalManager 为内存审批 | LOW | 进程重启后审批状态丢失；30 分钟 TTL | 后续可接入 DB 持久化 |
| 4 | .skills-router/ 为空目录 | INFO | 预留扩展点，无实际代码 | 未来 Skill 路由实现时填充 |
| 5 | 未修改 SUBJECT_WORDS / subject_hit() | INFO | 按任务要求禁止修改 | 主体口径由 subject_rules.py 锁定 |

---

## 8. 未完成项 / 下一步建议

1. **P1**：在 app.py 的 dev 执行端点中强制接入 `agent_boundary_check()`（当前为可选旁路）。
2. **P1**：将 lumenis_skill_adapter 的 OSAI Skill 自动注册到 SkillRegistry（当前仅提供转换方法）。
3. **P2**：SkillRegistry / ApprovalManager 持久化到 DB。
4. **P2**：.skills-router/ 实现实际 Skill 路由逻辑。
5. **P2**：在 CI/CD 中加入 Skill 元数据合规检查（注册前验证）。

---

## 9. Git 状态

- **未执行 git commit**（按任务要求禁止）。
- 变更文件：8 个（2 新增核心 + 4 适配 + 1 测试 + 1 临时脚本）。
- 分支：feat/zbc-full-upgrade-v1 @ 5e0ccd0。

---

*报告结束。所有测试通过，Agent 无超级权限，Skill 有完整元数据规范。*
