# SICI Page Map（SICI-Core · 智能研究学习平台页面地图）

> v1.0 2026-08-31。定位：**研究实验平台**（Research / Experiment / Runtime / Knowledge）。布局型：实验工作台（知识库 + 研究流 + 实验记录）。SICI 为**独立仓库**（当前为纯静态站点形态），不是 CTH-POMS 运行时依赖；本页图为 IA 规划，落地在 SICI 仓，视觉复用 ZBIP Design System。研究成果状态达 VERIFIED 才允许进入 DCC 工程候选、再进 ZBC。

## 全局框架
- 侧栏：Research Home / Knowledge Base（LEARNING-REGISTRY）/ Case Studies / Tech Comparison / Architecture Patterns / Experiments / Runtime Sandbox / Findings→DCC。
- Topbar：研究状态筛选、来源可信度、⌘K。
- 权限：Researcher（研究/实验）/ Reviewer（验证定级）/ Viewer。

## S1 Research Home
- 目标：研究队列总览，按 A–S 方向（Feature Registry/治理/Evidence/Observability/依赖图/浏览器自动化/采集/调度/E2E/自愈/AI Agent/学习库/设计系统/多仓治理）分类。组件：研究 Kanban（NEW→RESEARCHING→VERIFIED→CANDIDATE→ADOPTED / REJECTED）、方向 Panel。

## S2 Knowledge Base
- 目标：沉淀学习资产（对应 ZBC docs/learning：REGISTRY/CASE-STUDIES/TECH-COMPARISON/ARCHITECTURE/EVIDENCE/BROWSER/TESTING/DEPLOYMENT，及 ui/ 设计研究）。组件：知识条目 Table/详情 Drawer，字段=Research ID/项目/来源/license/架构/技术栈/优缺点/适用/是否采用/成本/风险/关联 Feature/Evidence/日期。**聊天记录不算学习库，必须落档。**

## S3 Case Studies / S4 Technology Comparison
- Case：逐案例卡片 + 一手数据（star/license/最近 push，标注抓取日期，NOASSERTION 以 LICENSE 原文为准）。
- Tech Compare：11 维评分表（正确性/性能/稳定性/安全/资源/维护成本/复杂度/扩展/商业风险/迁移成本/兼容性），结论分 ADOPT / REFERENCE-ONLY / REJECT（如本轮：waitress ADOPT(Win)、Celery/Scrapy/Nx REJECT、Backstage 仅借模型）。

## S5 Experiments / S6 Runtime Sandbox
- 目标：候选技术/原型在隔离沙箱实验（不接触生产库/生产 Cookie/生产浏览器 Profile）。组件：实验记录（假设/步骤/环境/结果/复现命令/证据）、沙箱运行状态点。实验失败也留档，不伪造结论。

## S7 Findings → DCC
- 目标：VERIFIED 研究打包为「工程候选」推给 DCC 评审，附证据与迁移/回滚评估；未 VERIFIED 不得进入工程。组件：流转向导、关联 DCC Change Map、状态追踪。

## 状态/移动/落地说明
- 研究状态用统一语义点；知识条目强调来源与日期、可追溯、可证伪。
- 移动端以阅读/检索/批注为主，实验编辑在桌面。
- 落地顺序：作为 ZBC/DCC 的外部研究大脑，先内容（docs/learning 已起步）后界面；不与生产 Runtime 耦合。
