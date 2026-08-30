# Z-Brand 架构决策记录 · 2026-08-30

> 类型：增量架构决策记录（ADR）
> 目的：在不修改现有生产业务代码的前提下，固定当前已确认的开发关系与优先级。
> 本文件不替代源码事实；若与当前源码、数据库或运行时实测冲突，以实测为准。

## 1. 当前总体结构

```text
Development-Command-Console
        │
        │ 内部 AI 研发中枢：审计 / 规划 / 测试 / 受控升级
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

- CTH-POMS 与 ZBMP 不拆成两套长期维护的 Core 源码。
- ZBMP 不是独立外部运行时服务，不得成为 CTH-POMS 的运行时依赖。
- Development-Command-Console 独立仓库、独立版本、独立部署；服务整个 Z-Brand 的研发，不进入 CTH-POMS 生产运行时。

## 2. 当前开发优先级

### P0：CTH-POMS 尽快稳定落地上线

优先处理：
- 启动与依赖统一
- 小红书采集稳定性、Auth Recovery、风控熔断与冷却
- 主体 / 时间 / 风险 / 事件 / 报告口径回归
- 数据安全、备份与恢复
- HTTPS / 反向代理或 Cloudflare Tunnel 公网边界
- 关键 API、页面、E2E 验收
- 生产部署与上线验收

任何新增能力只要可能影响 P0，都必须旁路、默认关闭或延后。

### P1：ZBMP 持续优化完善

继续在现有 Core 内增量建设，不拆 Core、不复制生产数据库、不建立第二套长期维护源码。

建设方向：
- 客户 / 品牌 / 竞品 / 项目 / Campaign
- Brand Profile 与监测配置
- 传播主体六维画像
- 内容类型
- 营销 / 传播 / 舆情三类事件
- event_relation 与事件生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter
- Ollama / AI Shadow / 样本与评测
- 新客户 Release 构建能力

ZBMP 默认不影响 CTH-POMS；授权、Feature Gate、Runtime Mode 等能力必须先设计为可控、可回滚、可审计。

### P1/P2：Development-Command-Console 同步建设

继续演进为内部 AI 研发中枢，目标闭环：

`需求 → 影响分析 → 受控补丁 → 隔离分支 → 测试 → Diff 审计 → 人工批准 → PR/Release 验收`

当前安全边界不改变：
- READ / TASK / AUDIT = ALLOW
- TEST = CONTROLLED
- WRITE / DEPLOY = DENY

不得为了自动化直接开放生产写入、自动 Merge 或自动部署。

## 3. 增量开发硬约束

本 ADR 只增加架构约束，不要求回写或重构现有生产主链。

任何后续补丁必须：
1. 先读取最新源码、当前基线与实际运行状态；
2. 明确影响范围和冲突点；
3. 采用最小新增/旁路方式；
4. 不删除、不覆盖生产数据；
5. 不弱化广州太古汇主体口径；
6. 不改变 publish_datetime / captured_at 语义；
7. 不让 ZBMP、AI 或新 Adapter 接管未经验证的生产链路；
8. 完成相关测试、回归、安全扫描后再进入主线；
9. 提供变更记录与回滚方式；
10. 提交后重新读取 HEAD 做二次核验。

## 4. P0 业务红线

不得修改、弱化、绕过现有源码中的：
- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `app.py` / `risk_engine.py` 中 `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- 所有下游 SQL、Dashboard、报告、专题统计的主体边界
- 历史生产数据库与业务数据
- 现有风险、事件、报告核心判断

采集异常、验证码、IP 风险、Session 失效不得伪装为“0 条”。

## 5. AI 边界

- 正式生产 AI Runtime：本地 Ollama。
- 没有 AI 时，核心采集、过滤、去重、事件、风险、统计和报告仍应运行。
- AI 只能作为增强层，不能单独成为事实生命线。
- 新模型优先 Shadow Mode，记录模型 / Prompt / 结果 / 置信度 / 采纳与人工修正。
- 历史外部 AI 代码在确认调用链前保持 Legacy/Optional，不贸然删除。

## 6. 数据与商业化边界

当前研发可以围绕真实业务场景进行设计和验证；商业化前必须完成公司/客户授权、原始数据与脱敏数据边界、统计特征与模型资产边界、留存/删除/导出规则以及依赖许可证/SBOM等审计。

不得把真实客户或公司敏感数据提交 GitHub。

## 7. 与现有历史文档的关系

仓库中存在早期阶段文档，其中部分仍描述“产品 A / 产品 B”或“ZBMP 预留独立数据库”等历史方案。这些内容保留为历史记录，不应覆盖当前决策。

当前有效关系以：
- 当前源码 / 数据库 / 运行时实测
- `docs/MASTER_DEVELOPMENT_BASELINE.md`
- `CURRENT_BASELINE.md`
- 本 ADR

为准；历史文档只用于追溯演进过程。

## 8. 成功定义

当前阶段不追求一次性完成全部规划功能。

**CTH-POMS 先稳定上线；ZBMP 在不影响 CTH-POMS 的前提下持续增强；Development-Command-Console 同步成为安全、可审计、可回滚的内部研发中枢。**
