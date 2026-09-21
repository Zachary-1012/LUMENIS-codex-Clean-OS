# Z-Brand 集成与研发优先级基线

> **HISTORICAL / PROVENANCE ONLY / NOT CURRENT AUTHORITY**
> This file preserves historical engineering provenance; it does not define current product architecture, source ownership, implementation, runtime or release state. Use the current [`LUMENIS Product Architecture`](../../../00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) and [`LUMENIS Source Owner Index`](../../../00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md).

> 生效日期：2026-08-30
> 适用：Development-Command-Console（内部 AI 研发中枢）
> 对应业务仓库：Zachary-1012/Z-Brand-Core

## 1. 定位

Development-Command-Console 是 Z-Brand 的内部 AI 研发中枢，不是 CTH-POMS 的生产运行时依赖，也不是独立对外产品。

它服务于 Z-Brand-Core 的持续研发、审计、测试、版本治理和受控升级。

## 2. Z-Brand-Core 正确架构

```text
Development-Command-Console
        │
        │ 研发审计 / 任务 / 测试 / 受控升级
        ▼
Z-Brand-Core
        │
        ▼
CTH-POMS
当前生产 / 客户交付入口
        │
        │ 合法 Key / License / Feature Gate
        ▼
ZBMP
Core 内隐藏增强能力层
```

ZBMP 不应被当成第二套长期独立源码或第二个并列生产项目。它属于 Core 内的受控能力层，当前不拆解、不复制 Core。

## 3. 当前开发优先级

### P0 — CTH-POMS

CTH-POMS 优先尽快稳定落地上线。任何研发中枢任务不得因为增加自动化、重构或实验能力而降低 CTH-POMS 上线优先级。

### P1 — ZBMP

ZBMP 在不影响 CTH-POMS 的前提下持续建设，优先采用旁路、Shadow、Feature Gate 和向后兼容方式。

### P1/P2 — Development-Command-Console

继续同步建设内部研发能力，但必须保持安全边界：
- READ / TASK / AUDIT = ALLOW
- TEST = CONTROLLED
- WRITE / DEPLOY = DENY

后续自动化应优先走：

`需求 → 分析 → 补丁候选 → 隔离分支 → 自动测试 → Diff 审计 → 人工批准 → PR → 验收`

不得直接取得生产写权限、自动 Merge 或自动部署。

## 4. 不可破坏的 Z-Brand-Core 规则

研发中枢对 Core 的任何分析、补丁或任务合同都必须保护：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 语义
- 历史生产数据库和业务数据
- 现有风险、事件、报告核心判断

AI/Adapter/第三方采集异常不得被包装成“0 条数据”。

## 5. AI 边界

Z-Brand-Core 正式生产 AI Runtime 为本地 Ollama。研发中枢可以辅助分析和生成工程任务，但不能把 AI 当作业务事实来源，也不能因为 AI 能力而绕过 Core 的业务红线。

## 6. GitHub 工作流

研发中枢的 GitHub 能力默认先保持只读审计。任何未来写操作必须：

1. 明确任务合同
2. 明确 Must Preserve / Forbidden
3. 产生可审计 Diff
4. 通过自动化测试
5. 通过核心口径回归
6. 人工确认后再进入 PR/合并流程

GitHub 不是生产覆盖源，远端变更不得自动覆盖本地正在运行的生产代码。
