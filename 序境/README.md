# 序境｜生产产品库

> 品牌哲学：芥子纳须弥

本目录是 Z-Brand-Core 内产品级文档、规范、注册表与架构入口的唯一 canonical home。

## 子产品

- `序境/序境-Core/` — 生产核心：运行时、数据、UI、工作流、安全与部署
- `序境/序境-Intelligence/` — 智能协同：AI、研究、分析、创作与受控辅助

## 规则

1. 产品名统一使用「序境」；历史 `Zachary` 仅作为研发/仓库历史标识。
2. 新功能必须先进入 Module / Page / Workflow / Data / Permission / Safety Registry。
3. 自动能力必须经过 Runtime Safety Gate；未经批准不得自动运行。
4. 文档只保留唯一事实来源；重复内容迁移至 Archive 前必须检查引用。
5. 中文、English、한국어共享同一 Localization Registry，不建立第三套产品。
6. UI 遵循小图标、细线、留白、克制动效；禁止大字报、大 Logo、大 Icon、大模块。
7. 未经证据验证不得标记 PASS；局部测试 PASS 不代表全库 PASS。

## Canonical 文档结构

- `00-GOVERNANCE/` 治理、术语、命名、权限、安全
- `01-PRODUCT/` 产品模型、模块、页面、交互
- `02-ARCHITECTURE/` 架构、依赖、通信、边界
- `03-DESIGN/` Design Tokens、Icon、UI/UX、品牌哲学
- `04-DATA/` Data / Metric / Evidence Registry
- `05-RUNTIME/` 运行时、采集、Gate、恢复
- `06-REPORT/` 报告与导出模板
- `07-RESEARCH/` 研究与行业知识
- `08-AUDIT/` 审计证据与收敛记录
- `99-ARCHIVE/` 已确认暂不用但不可丢失的历史资产

历史根目录文件暂不删除，避免在未完成依赖验证前造成破坏；后续按 Registry 逐项归位。
