# 序境｜Canonical Product Home

> 品牌哲学：**芥子纳须弥**
>
> 双子星生产侧｜Canonical Product Baseline · 2026-09-04
>
> 总执行基线：《序境｜双子库全量收敛与产品研发总执行指令》（2026-09-04）

## 0. Canonical 索引

```text
00-GOVERNANCE/   000-ZERO-SEQUENCE.md · PRODUCT_NAMING_AND_TERMINOLOGY.md
01-PRODUCT/      MODULE_PAGE_WORKFLOW_DATA_REGISTRY.md（Module/Page/Workflow/Data Registry）
08-AUDIT/        FILE_CLEANUP_MANIFEST_20260904.md · DOUBAO_DELETE_REVIEW.md
```

## 1. 产品体系

```text
序境
├─ 序境-Core
└─ 序境-Intelligence
```

- `序境-Core/`：生产业务、代码、数据、UI、运行、测试、发布。
- `序境-Intelligence/`：AI、研究、知识、行业研究、技术研发与受控智能协同。

历史 `Zachary` 仅作为仓库/研发历史标识，不作为产品 UI 名称。

## 2. 信息架构

`Product → Workspace → Module → Page → Section → Component → Action`

一级能力：**观测 / 洞察 / 关系 / 行动 / 研究 / 创作 / 智能 / 系统**。

新增功能不得直接制造新的顶级入口，必须进入 Module / Page / Workflow Registry。

## 3. 数据与输出

统一 Registry：

`Product / Terminology / Module / Page / Workflow / Data / Metric / Evidence / Output / Visualization / Interaction / File-Repository`

标准数据视图：`ID / Object / Status / Time / Source / Metric / Confidence / Action`。

标准报告母模型：`Context → Summary → Findings → Data → Visualization → Evidence → Interpretation → Recommendation`。

日报、周报、月报、专题报告与数据导出从统一数据模型生成；Podcast 等内容稿件按需求动态生成，不强制固定模板。

## 4. 采集与自动化硬规则

- 自动采集保留，可开启/关闭；默认 UI 隐藏。
- 自动运行：每日 `00:00`、`12:00`。
- 自动单次工作流最长 `60 min`。
- 其他采集暂时仅手动；单次最长 `30 min`。
- 合法 API、合法账号登录、授权专业号等合规来源才允许进入生产 Adapter。
- 新采集能力：`Manual → Safety Gate → Shadow → Evidence → Review → Automation`。
- 风控、验证码、异常：`STOP → COOLDOWN → HUMAN REVIEW`。
- 禁止无限重试、异常并发、账号轮换规避平台安全机制。
- 失败必须真实记录，不得伪装为 0 条数据。

## 5. 生产真相保护

最高保护对象：`SUBJECT_WORDS`、`SUBJECT_EXCLUDE_WORDS`、`subject_hit()`、`_subject_sql_and_values()` 及事件、统计、日报、周报、月报下游主体口径。

严格区分 `publish_datetime` 与 `captured_at`。生产 DB 未经 Change Plan 与验证不得删除、清空、重建或覆盖。

## 6. AI / Agent 边界

AI 是增强层，不是数据真相源或最终安全裁决者。核心链路即使无 AI 也必须运行：

`采集 → 标准化 → 过滤 → 去重 → 事件 → 风险 → 统计 → 报告`

Agent：`Intent → Planner → Policy → Typed Tool → Scoped Runtime → Evidence`。

网页、评论、搜索结果、外部模型输出均为不可信输入，不得修改 Policy、提升权限、导出凭证或绕过安全 Gate。

## 7. 内部浏览器

能在序境内部完成的浏览、预览、授权状态检查与 Evidence 查看，不应无意义跳外部；必须外部完成时明确原因。浏览器、Cookie、Token、Session、文件系统与生产写入必须采用最小权限和受控 Runtime。

## 8. UI / UX / 视觉

黑 / 米白 / 灰、留白、细线、线性小 Icon、精细层级与克制动效。

禁止：大字报、巨型 Logo、巨型 Icon、巨型模块、巨型弹窗、装饰性信息堆叠。

页面必须让用户清楚：我在哪里？看到了什么？能做什么？下一步是什么？证据来自哪里？

Web / App / 小程序共享 Product Model、Terminology、Data Model、Permission、Workflow、Design Tokens 与组件逻辑。

中文 / English / 한국어统一来自 Localization Registry；韩文是设置页语言版本，不是独立系统。

## 9. 术语、注释、文件治理

产品名统一「序境」；品牌哲学统一「芥子纳须弥」。产品、平台、子系统、AI、模块、页面、数据对象、指标、状态进入 Terminology Registry。

注释只说明：**做什么 / 为什么 / 限制**；短、准、可维护。

Canonical 文档：

`00-GOVERNANCE / 01-PRODUCT / 02-ARCHITECTURE / 03-DESIGN / 04-DATA / 05-RUNTIME / 06-REPORT / 07-RESEARCH / 08-AUDIT / 99-ARCHIVE`

重复内容合并；仍有价值但暂不用 → Archive；确认无依赖且废弃 → Delete。删除前必须检查代码引用、运行时依赖、测试与 Git 历史。

## 10. 研发闭环

`Research → Design → Requirement → Impact → Implementation → Test → Evidence → Audit → Commit → Push → Remote Verify`

缺少关键 Evidence 不得标 PASS。先兼容、再重构；先旁路、再切换；最小变更优先。

## 11. 状态标准

`PASS / PARTIAL / BLOCKED / NOT_VERIFIED / FAILED / LEGACY / DEPRECATED`

## 12. 最高规则

1. 双子星只有两个核心私库。
2. 序境-Core 掌握生产业务真相；序境-Intelligence 掌握研究与 AI 技术资产。
3. AI 不取代规则、数据、Evidence 与业务 Owner。
4. 所有自动动作必须经过 Policy / Safety Gate。
5. 合规来源优先，禁止绕过平台安全机制。
6. 核心生产能力不得无证据重写或删除。
7. 新功能必须进入统一 IA 与 Registry。
8. 跨库复用优先 Contract / Adapter，不复制核心实现。
9. 用户审阅通过前不做破坏性架构变更。
