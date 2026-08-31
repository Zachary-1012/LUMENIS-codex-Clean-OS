# DCC Page Map（Development Command Console · 研发治理控制台页面地图）

> v1.0 2026-08-31。定位：**研发工程治理控制台**（Feature / Contract / Evidence / Gate / Release / Learning / Architecture Governance）。布局型：工程控制台（类似 Linear/Vercel 工程视图，高密度表格 + 状态流）。DCC 为**独立仓库**，不是 CTH-POMS 运行时依赖；本页图为 IA 规划，落地在 DCC 仓，视觉复用 ZBIP Design System。当前 DCC 本地落后远程 27 提交且有 3 处未整合改动（GAP-11），整合需单独授权。

## 全局框架
- 侧栏：Overview / Features / Capabilities&Owners / Contracts / Evidence / Change Maps / Release Gates / Tasks / Learning / Audit Log。
- Topbar：仓库/分支切换、当前基线版本、CI 状态点、⌘K、人员。
- 权限：Maintainer（读写治理）/ Reviewer（评审）/ Viewer（只读）。

## D1 Governance Overview
- 目标：三仓（ZBC/DCC/SICI）HEAD、Release Gate 状态、P0–P3 计数、待评审变更一览。组件：Metric、仓库 StatusCard、Gate 流水线、最近 Activity Timeline。状态：pass/blocked/wip 语义点。

## D2 Feature Registry（功能总账）
- 目标：Feature→Asset→Owner→Contract→DB→UI→Runtime→Test→Evidence→Release 全链可视。组件：高密度 Table（列可配置）、状态 9 态 Badge（ACTIVE/DEVELOPING/EXPERIMENTAL/PLANNED/RESERVED/LEGACY/DUPLICATE/MIGRATION_REQUIRED/NOT_VERIFIED）、行详情 Drawer（证据链时间线、缺失项 GAP 关联）。交互：缺证项直接标红并禁止升 ACTIVE（状态变更必须有证据）。

## D3 Capability & Ownership
- 目标：唯一 Owner 治理、DUPLICATE_CANDIDATE 比较与迁移流（能力覆盖率/正确性/性能/稳定性/安全/测试/Evidence 评分表）。组件：对比 Table、Owner 迁移向导、回归检查清单。

## D4 Contracts
- 目标：API/数据/采集契约版本化（/api/v1 规范、统一 response/error/pagination/auth）。组件：契约 Table、Diff 视图、兼容性 Badge（breaking 标 danger）。

## D5 Evidence / D6 Release Gates
- Evidence：按 commit/version/env 归档测试结果、日志、截图、trace、API/DB 结果（对应 GAP-08，Evidence 非空、可复现、不过期）。组件：Evidence 时间线、产物预览、重跑按钮。
- Release Gates：P0=0、核心业务/DB/API/UI/E2E/Runtime/Restart/Backup/Rollback/Staging 各项门禁清单，全绿才允许 Production；组件：Gate 看板、阻断原因、回滚入口。

## D7 Change Maps / Tasks / Learning / Audit
- Change Map：一次变更影响模块/仓库/依赖/风险/测试/回滚（TASK ID 标准格式）。Tasks：施工任务看板（一任务一 commit）。Learning：对接 SICI 研究库（VERIFIED 才能进候选）。Audit Log：谁在何时改了治理状态，不可篡改时间线。

## 状态/移动/落地说明
- 全部为高密度工程表格，状态点+文字双表达；移动端只做只读审阅与审批（不做复杂编辑）。
- 落地顺序：ZBP（CTH/ZBMP）稳定上线后再实施 DCC UI；当前仅冻结 IA，避免与 ZBC 运行时耦合。
