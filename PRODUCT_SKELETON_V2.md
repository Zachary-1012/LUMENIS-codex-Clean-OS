# LUMENIS Product Skeleton V2

状态：AUDIT BASELINE（2026-09-08）

## 产品树

```text
LUMENIS
├── CTH · Subject Intelligence
│   ├── Overview
│   ├── Subject / Topic / Event
│   ├── Risk / Public Sentiment
│   ├── Report
│   └── Evidence
├── BMP · Brand Intelligence
│   ├── Overview
│   ├── Brand / Campaign / Audience
│   ├── KOS / KOL / KOC
│   ├── Evaluation
│   └── Insight
└── SYSTEM · Runtime Infrastructure
    ├── Runtime / Collector
    ├── AI Gateway
    ├── Database
    ├── Browser / Security / Permission
    └── Settings
```

不新增第四业务域。Shared Capability 与 Agent/AI 是跨域能力，不提升为业务域。

## Domain Boundary

- CTH 的事实边界由 Subject、时间口径、质量、风险、事件和 Evidence 规则确定。
- BMP 复用统一事实层，以 Brand、Campaign、Audience、传播主体和评估 View Model 展示。
- SYSTEM 只承载运行基础设施，不承载业务结论。
- KOS 使用 Canonical Data Layer；CTH 作为来源/影响/Evidence，BMP 作为品牌资产/传播效果/合作分析。

## Navigation

业务导航固定为 `CTH / BMP / SYSTEM → Module → Page`。evaluation、launch、data-center、xiaohongshu、workspace 等页面必须通过模块内入口或 System/Developer 暴露，不得因为存在路由就自动成为一级导航。

## Data Flow

```text
External Source
→ Raw / Evidence
→ Subject + Scope Filter
→ Dedup / Quality
→ Canonical Data
→ Metric / Truth Table / View Model
→ UI / Report / Export / AI enhancement
```

## User Journey

`Overview → Filter / Context → Trend / Distribution → Event / Insight → Evidence → Action → Detail → Backtrace`

## Current Match

当前骨架为 `PARTIAL`：README、治理架构和 UIUX 审计已确认三域方向；导航重复入口、旧兼容路由和部分页面归属仍需增量收敛。后续修改必须先建立 route/function/component/data contract 映射，再迁移或删除。

## Evidence

- `README.md`
- `ARCHITECTURE.md`
- `AGENTS.md`
- `00-GOVERNANCE/LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0.md`
- `docs/UI_UX_NON_REGRESSION_CONTRACT.md`
- `UIUX_AUDIT_REPORT.md`
