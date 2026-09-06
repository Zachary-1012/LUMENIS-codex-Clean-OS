# ZBC/LUMENIS 双库边界检查报告 (Boundary Check Report)

> 生成时间: 2026-09-07 00:31:07
> 检查器版本: 1.0.0
> 扫描生产文件: 922
> 生产表数量: 74

## 1. 总览 (Summary)

**总违规数: 22**

### 按严重度

| 严重度 | 数量 |
|--------|------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 11 |
| LOW | 0 |
| INFO | 11 |

### 按检查项

| 检查项 | 违规数 |
|--------|--------|
| B1: ZBC 直接 import OSAI | 1 |
| B2: OSAI 直接连接 ZBC DB | 1 |
| B3: OSAI 直接写 ZBC 生产表 | 0 |
| B4: app 启动依赖 OSAI | 0 |
| B5: 跨库交互 Contract/Artifact | 10 |
| B6: Skill/Agent Permission Gate | 5 |
| B7: PENDING 资产生产引用 | 5 |
| B8: 凭证安全（辅助） | 0 |

## 2. 关键违规详情 (CRITICAL / HIGH)

*无 CRITICAL/HIGH 违规*

## 3. 中低优先级违规 (11 项)

| # | 严重度 | 检查项 | 文件 | 行号 | 原因 |
|---|--------|--------|------|------|------|
| 1 | MEDIUM | B1-DIRECT-IMPORT | tests\_s07_scan.py | 6 | 直接 from OSAI 导入: osai_engine.skills.source_skills |
| 2 | MEDIUM | B6-PERMISSION | agent_boundary.py | 0 | Agent/Skill 执行入口未引用 Permission Gate |
| 3 | MEDIUM | B6-PERMISSION | lumenis_skill_adapter.py | 0 | Agent/Skill 执行入口未引用 Permission Gate |
| 4 | MEDIUM | B6-PERMISSION | account\skills.py | 0 | Agent/Skill 执行入口未引用 Permission Gate |
| 5 | MEDIUM | B6-PERMISSION | tests\test_agent_combined_shardB.py | 0 | Agent/Skill 执行入口未引用 Permission Gate |
| 6 | MEDIUM | B6-PERMISSION | tests\test_lumenis_skill_invoke.py | 0 | Agent/Skill 执行入口未引用 Permission Gate |
| 7 | MEDIUM | B7-PENDING-REF | lumenis_skill_adapter.py | 112 | 生产代码引用未验证资产: CANONICAL_REGISTRY |
| 8 | MEDIUM | B7-PENDING-REF | scripts\p1c_part1_copy_assets.py | 358 | 生产代码引用未验证资产: DESIGN_PHILOSOPHY_SEED_MUSTERY_TAIJI_V1 |
| 9 | MEDIUM | B7-PENDING-REF | tests\test_l5_fault_injection.py | 517 | 生产代码引用未验证资产: test_results_l5 |
| 10 | MEDIUM | B7-PENDING-REF | tests\test_report_audit.py | 3 | 生产代码引用未验证资产: report_audit |
| 11 | MEDIUM | B7-PENDING-REF | tests\test_skill_agent_boundary.py | 638 | 生产代码引用未验证资产: CANONICAL_REGISTRY |

## 4. 信息项 (11 项)

- [B2-OSAI-DB] N/A:0 — OSAI 路径不存在或未指定: None
- [B5-CONTRACT] agent_runtime_adapter.py:7 — subprocess 调用 OSAI（合规模式）: - 禁止 Runtime 硬耦合：通过 subprocess 调用 OSAI，不直接 import osai
- [B5-CONTRACT] agent_runtime_adapter.py:14 — subprocess 调用 OSAI（合规模式）: ZBC API → AgentRuntimeAdapter → subprocess → OSAI agen
- [B5-CONTRACT] agent_runtime_adapter.py:88 — subprocess 调用 OSAI（合规模式）: """通过 subprocess 调用 OSAI Python，返回 JSON。fail-close。"""
- [B5-CONTRACT] lumenis_frontend.py:425 — subprocess 调用 OSAI（合规模式）: Cross-Core: 通过 subprocess 调用 OSAI evidence reader，
- [B5-CONTRACT] lumenis_skill_adapter.py:8 — subprocess 调用 OSAI（合规模式）: ZBC API → CrossCoreSkillAdapter → subprocess → OSAI ca
- [B5-CONTRACT] lumenis_skill_adapter.py:75 — subprocess 调用 OSAI（合规模式）: """通过 subprocess 调用 OSAI Python 执行脚本，返回 JSON。
- [B5-CONTRACT] lumenis_skill_adapter.py:228 — subprocess 调用 OSAI（合规模式）: """真实执行：ZBC → subprocess → OSAI SkillInvoker。
- [B5-CONTRACT] tests\test_osai_boundary_audit.py:276 — subprocess 调用 OSAI（合规模式）: 但该模块导入时零副作用（仅定义 CrossCoreSkillAdapter 类），OSAI subproce
- [B5-CONTRACT] scripts\audit_tools\boundary_check.py:155 — subprocess 调用 OSAI（合规模式）: "ZBC 生产代码禁止直接 import OSAI 运行时，应通过 subprocess/contract 
- [B5-CONTRACT] scripts\audit_tools\boundary_check.py:165 — subprocess 调用 OSAI（合规模式）: "ZBC 生产代码禁止直接 from osai_* 导入，应通过 subprocess/contract 交

---

## 5. 处置原则

- **CRITICAL**: 立即修复，阻断合并
- **HIGH**: 本迭代修复
- **MEDIUM**: 排入下迭代
- **LOW/INFO**: 记录跟踪
- 所有违规遵循 DENY+AUDIT+可定位原因原则

*本文件由 scripts/audit_tools/boundary_check.py 自动生成，请勿手动编辑。*