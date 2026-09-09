# Heritage Source Map

## Current baseline
- `Zachary-1012/LUMENIS-codex-Clean-OS` — 当前纯净生产基线；作为 Current Production Truth 的承载仓，不把 Heritage 当作 Runtime。

## Historical / capability sources
- `Zachary-1012/Z-Brand-Core` — 历史主产品、Learning/Research、数据呈现、平台研究、Domain 方法、UI/UX、Evidence、Audit、Regression、历史研究分支的主要来源。
- `Zachary-1012/Zachary-OS-AI` — AI/Agent、Learning/Memory、Architecture Research、Research Adoption、跨仓 Intelligence 研发来源。
- `Zachary-1012/global-growth-intelligence` — Research Pipeline、Taxonomy、Evidence、Intelligence Service、Shared Intelligence Boundary 参考来源；产品 Runtime 保持独立。
- `Zachary-1012/lumenis-command` — Audit、ADR、Evidence-driven Engineering、Verification Gate、Security/Deployment、Repository Boundary 的工程知识来源。

## High-risk historical branch families

### Korean / K-drama / Fansub / Translation
- `research/kdrama-fansub-study*`
- `research/kdrama-fansub-translation-2023-2026-*`
- `research/kdrama-fansub-translation-2023-2026-final`
- `research/kdrama-fansub-translation-2023-2026-research*`
- `feat/i18n-ko-en-zh-v6-research*`

这些分支视为一个完整的 Korean Content Intelligence Collection，不能只读取单个 `final` 分支。

## Historical directories requiring inventory

### Z-Brand-Core
- `docs/learning/`
- `docs/research/`
- `docs/reference/`
- `docs/MASTER/`
- `intelligence_library/09_Research-Hub/`
- `intelligence_library/10_工程审计方法/`
- `intelligence_library/11_前沿研究/`
- `contracts/`
- `audit/`
- `序境/08-AUDIT/`
- Domain implementation + tests/evidence tied to KOS, Podcast, platform, tables/metrics, Truth/Contract.

### Zachary-OS-AI
- `03-RESEARCH/`
- `00-GOVERNANCE/`
- Architecture / Research Adoption / Agent / Learning / Memory / Evaluation related assets.

### global-growth-intelligence
- `ggi/pipeline/research_pipeline.py`
- `ggi/pipeline/taxonomy.py`
- `ggi/core/evidence.py`
- `ggi/intelligence/service.py`
- `07-CONTRACTS/`

### lumenis-command
- `docs/audit/`
- `docs/adr/`
- `docs/p0/`
- `docs/constitution/`
- deployment / verification / evidence assets.

## Retrieval rule
Source Map 是检索入口，不是迁移清单。每个任务应先通过 Registry 找资产，再通过 Source Map 回源核验。
