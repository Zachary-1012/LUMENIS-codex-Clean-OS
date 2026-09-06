# ZBC 资产去留 · 用户决策记录 V1.0

> 决策时间：2026-09-06
> 依据：ZBC_OPTIMIZATION_MIGRATION_INVENTORY_V1.0.md 待确认清单
> 状态：A3 待用户最终拍板；其余已决策；用户另有一项核对，核对完才启动 P1

## A. 前端功能/组件
- A1 红点提醒 badge_manager：保留回补（无争议推进）
- A2 微博/B站辅助数据源 auxiliary_sources：保留回补（无争议推进）
- **A3 Zachary 3D 悬浮机器人：【用户已拍板=改成轻量 AI 助手入口】** 废弃 3D 拟物球/three.js/液晶脸/nomi 拖拽形态；保留 system_knowledge 系统问答能力，改造为右下角轻量 AI 助手入口，风格对齐 Design System V1.1。
- A4 弹窗精简 modal_simplify：理念融入新组件（无争议推进）
- A5 启动屏 launch-screens：保留并按新设计重做（无争议推进）

## B. 产品域边界（用户明确：独立，不并入）
- **B1 DCC 研发治理控制台：保持独立仓库，不并入 ZBC，只共享设计系统**
- **B2 SICI 智能研究学习平台：平台保持独立不并入；但其研究资产/文档并入 ZBC 统一资料库**
- B3 流转门禁 SICI(VERIFIED)→DCC(工程候选)→ZBC(生产)：保留这条证据门规则

## C. 主库杂项目录（用户：按我建议）
- C1 ref_gpt_v2（353文件）：保留，提取有用部分，先不删
- C2 staging（84文件）：确认无独有内容后归档（归档不删除）
- C3 archive / 99-ARCHIVE / backups（62文件）：保留归档不动
- C4 00-GOVERNANCE / 02-ARCHITECTURE / contracts / core（85文件）：并入统一资料库 governance 子库
- C5 dependencies / 2026-08-30 / 2026-09-01（空目录）：删除空壳
- C6 deliverables（2文件）：检查内容后保留

## D. 其他
- **D1 播客 podcast：用户明确"补回前端，很重要，对应功能和资料不能丢"**
  - 主库 podcast 目录还在，旧分支丢失23个文件需回补
  - learning-feed 里的播客方法论研究资料同步纳入资料库
  - 前端在新三域结构中找到合适位置（ZBMP Content 或 SYSTEM，回补时确认）
- D2 Nivellea 等候选命名：长期研究候选，不进生产/命名

## 启动条件
用户已全部拍板并指令"开始执行下一轮"（2026-09-06）。原团队 run 已 sealed，新建 OrganizeAgent 执行。

## 权威研究汇编蓝图（用户上传，最高优先）
- audit/OSAI_ZBC_研究汇编总目录_20260906.docx（916段/30卷），基于 GitHub Zachary-1012/Zachary-OS-AI main @ 2387501（645文件/2.4MB）逐文件核对
- 统一资料库按其最终建议 13 目录结构组织（00总览/01ZBC专项/02ZBMP/03CTH/04OSAI核心/05Runtime/06Security/07Data-Evidence/08UI-UX/09ResearchHub/10工程审计/11前沿/12落地索引），与既有7子库映射融合
- "12_研究→ZBC落地索引"五态：已落地/已实现待验证/可直接复用/建议转化/仅研究不应转化
- 铁边界：OSAI = Intelligence Core，不拥有 Production Truth，**禁止成为 ZBC runtime 依赖**；研究→人工评审(Evidence→Evaluation→Human Feedback→Validation)→才准入生产
- **版本缺口**：本地 D:\Zachary OS AI HEAD=09a627a（633文件，shard-B/D 本地线），不含 2387501，比权威 main 少12文件 → 需从 GitHub 拉取 Zachary-OS-AI main 补齐后再整合，不能只靠本地副本
