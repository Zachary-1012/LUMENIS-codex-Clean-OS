# XHS Topic Monitor Global Adaptation Plan V2

> 日期：2026-08-31
> 类型：生产基线适配方案（先契约、后实现）
> 目标：在不打断当前 UI/视觉升级的前提下，将临时 10×10 话题监测接入统一 Scheduler，并为未来 Official API / Licensed Provider / Evidence Source 保留无损切换能力。

## 1. 当前代码审计结论

### 已存在、无需推倒重做

- `platform_adapters/base.py`：已有统一 Adapter / CollectionResult / CollectionStatus 契约。
- `platform_adapters/registry.py`：已有 Adapter 注册机制。
- `platform_adapters/scheduling/`：已经存在平台独立、配置驱动的动态调度策略；设计目标是不写死固定时钟/固定次数。
- `platform_adapters/xhs.py`：继续作为现有 Web 主 Adapter，不改其主体采集链路。
- `platform_adapters/xhs_app_topic.py`：已有 App Topic Adapter 框架和 Feature Flag，可保留为未来合法数据源接入口，但不得实现私有 API 逆向/签名破解。
- Core 的标准化、主体过滤、去重、风险/事件链路继续复用，不建立第二条独立业务流水线。

## 2. 必须改的地方

### A. Topic Monitor 调度层

将历史 `topic_campaign` 固定小时/固定次数逻辑降级为 legacy，不再作为生产调度入口。

新的业务预算：

- `strategy = temporary`
- `max_batches_per_day = 10`
- `max_new_items_per_batch = 10`
- `dedup = true`
- 时间由统一 Scheduler 决策，不固定具体时刻。
- 10×10 是当前临时业务预算，不是永久平台策略，也不是风控保证。

### B. Source Adapter

建立 Source Priority：

1. `official_api`
2. `licensed_provider`
3. `approved_evidence`
4. `temporary_browser`

上层 Topic Monitor 不直接依赖具体来源。

### C. Session / Browser

只改稳定性与生命周期：

- persistent profile
- session validator
- crash recovery
- manual re-auth state
- no repeated login probing

不得把浏览器层改造成反检测/规避工具。

## 3. 不需要大改的部分

### 后端

不需要重写 Core 主链路。

保持：

`source -> normalize -> subject filter -> quality -> dedup -> persist -> risk/event -> knowledge/AI`

只在 Source Adapter 和 Scheduler 之间增加统一 Topic Source Contract。

### 数据库

优先复用现有 note/source/dedup/event 字段。

只有在当前 schema 不足以记录 `source_type/provider/captured_at/confidence` 时才做增量 migration；禁止为了本方案重建现有表。

### AI

不进入采集调度决策。

AI 只做已有的增强分析/分类/知识处理。

## 4. 前端/UI/UX影响评估

### 结论：不需要大动。

当前 UI/视觉升级可以继续进行。

本方案只要求增加一个稳定的业务状态契约：

- `临时监测` 标识
- `今日批次 / 今日新内容` 状态
- `数据源`（Official / Provider / Evidence / Temporary Browser）
- `Session` 健康状态
- `暂停/熔断`状态
- `下一次任务`状态

这些应该作为现有页面的增量信息层，不改变现有导航层级、视觉体系和主要交互。

## 5. 前端与当前 UI 升级并行规则

当前正在进行的 UI/视觉/层级升级可以继续，不需要暂停。

硬约束：

1. 后端 API contract 不因 UI 美化而改变。
2. Topic Monitor 只增加字段，不删除现有字段。
3. 前端通过状态/数据源标签消费新字段。
4. 现有页面路由、导航层级、核心交互不重构。
5. 若未来 Provider/API 切换，前端不应感知具体采集实现。

## 6. 风险隔离

国内 XHS 主账号当前为 WARNING / NOT_BANNED：临时业务策略可以继续作为任务配置，但不把 10×10 描述为“不会触发风控”的保证。

香港 RedNote 账号为受限状态：不得作为自动化测试目标。

两条硬限制：

- 不自动执行改变账号状态的点赞/评论/发布等动作。
- 不实施任何平台风控规避。

## 7. 实施顺序

P0：Topic Source Contract + Scheduler 接入
P0：旧固定时钟逻辑隔离
P1：10×10 临时业务预算
P1：Dedup/Provenance/Source metadata
P1：Session Validator/Browser Health
P2：Official API / Licensed Provider Adapter
P2：Evidence Adapter
P3：未来数据源自动择优

## 8. 验收标准

- 当前 UI 升级不回退。
- 当前生产主链路不改变。
- 旧固定时钟不再成为 Topic Monitor 生产入口。
- 临时 10×10 可配置、可关闭、可替换。
- 新数据源无需修改 Risk/Event/Knowledge 上层。
- 重复内容不重复进入分析链。
- Session 失效只进入人工重新认证状态，不循环登录。
- API/Provider/Evidence 任一未来接入时可替换 Browser Source。
