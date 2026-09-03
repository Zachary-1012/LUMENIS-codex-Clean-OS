# 序境-Core｜Production Truth

> **序境 · 芥子纳须弥**
>
> 正式产品名：**序境 / Xujing / 서경**
>
> 本仓库是序境双子库中的**生产核心**，负责生产业务、数据、运行时、UI/API、测试与发布。
>
> `Z Brand Core` / `Zachary` 仅作为仓库与历史研发标识，不作为产品展示名。
>
> **当前唯一有效双库：序境-Core + 序境-Intelligence。**
>
> 基线：2026-09-04。版本事实以 `VERSION` 为准。

---

## 1. 双库架构

```text
                         序境
                   芥子纳须弥
                         │
            ┌────────────┴────────────┐
            │                         │
      序境-Core                 序境-Intelligence
    Production Truth          Research & Intelligence
            │                         │
      Code / Data / UI          Research / AI / Contract
      Runtime / Test             Benchmark / Knowledge
            │                         │
            └──── Contract / Evidence ────┘
```

**序境-Core** 是唯一生产业务真相源。Core 不依赖 Intelligence 才能运行。

**序境-Intelligence** 负责研究、AI、技术研发、Benchmark、知识与施工规格。研究结果必须经过 Contract → Implementation → Test → Evidence 才能进入生产。

不得建立第三/第四生产核心库。

---

## 2. 当前产品

### CTH-POMS

广州太古汇舆情监测与品牌传播情报生产入口。

- 舆情监测
- 风险预警
- 事件中心
- 负面确认
- 热点 / 话题
- 笔记搜索
- 数据分析
- 品牌 / 业态
- 官方动态
- 营销案例库
- 舆情日历
- 报告中心
- 系统设置
- AI 辅助

当前主平台为小红书；其他平台必须通过受控 Adapter 接入。

### ZBMP

Core 内母平台能力，不建立第二套 Core。

- 客户 / 品牌 / 竞品 / 项目
- Brand Profile / Monitoring Config
- KOS / KOL / KOC / 普通用户 / 媒体 / 官方
- 内容类型
- 营销 / 传播 / 舆情事件
- 事件关系与生命周期
- 消费者需求
- 品牌对标
- 多平台 Adapter
- AI Shadow / 样本 / 评测
- 客户 Release

---

## 3. Canonical Registry

所有资产统一遵循：

```text
Product
 ↓
Subsystem
 ↓
Module
 ↓
Page
 ↓
Function
 ↓
Data
 ↓
API
 ↓
Runtime
 ↓
File
 ↓
Class / Function
```

所有名称进入 Canonical Registry：

- Product Registry
- Module Registry
- Page Registry
- Function Registry
- Data Registry
- Terminology Registry
- File Registry
- API / Runtime Registry

同一概念只能有一个 Canonical ID。中 / 英 / 韩是同一 ID 的语言表现，不得形成三套功能。

---

## 4. 标准命名

| 层级 | 中文 | English | 한국어 |
|---|---|---|---|
| Brand | 序境 | Xujing | 서경 |
| Philosophy | 芥子纳须弥 | Seed to Infinity | 개자납수미 |
| Product | 序境-Core | Xujing Core | 서경 Core |
| Product | 序境-Intelligence | Xujing Intelligence | 서경 Intelligence |
| Module | 观测 | Observation | 관측 |
| Module | 洞察 | Insight | 인사이트 |
| Module | 行动 | Action | 실행 |
| Module | 研究 | Research | 연구 |
| Module | 智能 | Intelligence | 지능 |
| Module | 知识 | Knowledge | 지식 |
| Module | 系统 | System | 시스템 |

韩文为界面本地化基线；正式商标、版权及法律名称使用前必须进行专业语言与法律审查。

---

## 5. 生产真相保护｜P0

以下内容不可被 AI、研究、外部工具或新模块绕过：

### 太古汇主体边界

保护：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体边界
- `build_daily_report()` 主体边界
- Dashboard / Statistics / Reports 主体口径

不得为了增加数据量弱化主体过滤。

### 时间口径

- `publish_datetime`：内容真实发布时间
- `captured_at`：系统采集时间

正式报告默认使用 `publish_datetime`。无法可靠归一化的相对时间必须标记不确定。

### 数据库

生产数据库为最高保护资产。未经明确 Change Plan 与验证，不得删除、清空、重建或覆盖。新增字段/表优先采用向后兼容迁移；生产、测试、实验数据隔离。

---

## 6. AI 边界

AI 是增强层，不是生产生命线。

即使没有 AI，核心链路必须能够运行：

```text
采集 → 标准化 → 过滤 → 去重 → 事件 → 风险 → 统计 → 报告
```

AI 可以辅助情绪、主题、诉求、摘要、风险解释、评论总结、趋势解释、语义识别、聚类建议与报告润色。

AI 不得单独决定：

- 主体归属
- 真实发布时间
- 统计数量
- 报告周期
- 原始数据真实性
- 最终核心风险口径

AI 输出必须可追溯至原始输入、模型版本、提示版本，并支持人工修正。

---

## 7. 小红书采集安全｜P0

目标：**稳定、低风险、可解释、可恢复、可观察、可审计。**

### 自动采集

仅保留两个自动窗口：

```text
00:00
12:00
```

- 每日各一次
- 自动采集可开启 / 关闭
- 自动能力存在但默认隐藏
- 每窗口执行去重与安全检查
- ShadowPlanner 只能收紧限制，不得放松限制

### 手动采集

其他采集任务默认仅允许手动触发，每次最长 30 分钟，并受同一安全策略约束。

### 合法来源

保留合法账号、合法 API、官方开放能力、授权专业号等合规 Adapter 入口。

不得通过账号、Cookie、IP、代理、验证码规避或提高频率绕过平台安全机制。

### 安全状态

```text
SCHEDULE
 ↓
PREFLIGHT
 ↓
POLICY CHECK
 ↓
IDENTITY / SESSION CHECK
 ↓
COLLECT
 ↓
VALIDATE
 ↓
EVIDENCE
```

安全信号：`STOP → COOLDOWN → HUMAN REVIEW`。

失败不得伪装成“0 条数据”。

---

## 8. Resident Browser Runtime

```text
Resident Browser Runtime
 ├─ Browser Profile
 ├─ Identity Manager
 ├─ Session Manager
 ├─ Auth Lifecycle
 ├─ Task Scheduler
 ├─ Collector
 ├─ Health / Heartbeat
 ├─ Circuit Breaker
 ├─ Recovery
 └─ Evidence
```

Session 失效：

```text
AUTH_REQUIRED
 ↓
系统内 Auth Modal
 ↓
正常扫码 / 登录
 ↓
Session Verify
 ↓
READY
 ↓
Resume Task
```

身份必须显式白名单、与任务强绑定；未知身份拒绝执行。

---

## 9. Platform Adapter

```text
BasePlatformAdapter
 ├─ XiaohongshuAdapter
 ├─ WeiboAdapter
 ├─ BilibiliAdapter
 └─ FutureAdapter
```

Adapter 负责平台差异；Core 负责标准化、主体过滤、去重、事件、风险、统计与报告。

不得为了新增平台复制整套系统。

---

## 10. Health / Recovery / Evidence

至少维护：

- browser_alive
- page_alive
- session_valid
- runtime_last_heartbeat
- collector_last_start
- collector_last_success
- collector_last_error
- pending_auth
- circuit_state
- last_evidence_id

重要运行形成非敏感 Evidence。Cookie、Token、Session、API Key、Password 不得进入 Git 或 Evidence。

---

## 11. UI / UX 信息架构

```text
工作台
├─ 观测
│  ├─ 舆情
│  ├─ 事件
│  ├─ 热点
│  └─ 采集
├─ 洞察
│  ├─ 数据分析
│  ├─ 趋势
│  ├─ 品牌
│  ├─ 竞品
│  └─ 风险
├─ 行动
│  ├─ KOS
│  ├─ Campaign
│  ├─ 任务
│  └─ 执行
├─ 报告
│  ├─ 日报
│  ├─ 周报
│  ├─ 月报
│  ├─ 专报
│  └─ 导出
└─ 系统
   ├─ 数据源
   ├─ 账号
   ├─ AI
   ├─ 权限
   ├─ 安全
   └─ 设置
```

视觉原则：

- 侘寂、克制、清晰
- 线性 Icon / 小型功能 Icon
- 操作优先，美感服务效率
- 禁止巨大 Logo
- 禁止巨大 Icon
- 禁止大字报
- 禁止无限套卡片
- 不允许模组破坏合理信息密度
- 动态可视化必须服务数据理解
- 图表 → 数据 → 记录 → Evidence 可追溯
- 中 / 英 / 韩响应式适配，禁止翻译造成布局溢出

---

## 12. 数据、报告与导出

有数据页面统一：

```text
Header
 ↓
KPI / Summary
 ↓
Filter / Search / Scope
 ↓
Visualization
 ↓
Data Table
 ↓
Detail / Evidence / Provenance
```

标准决策报告：

```text
问题 → 事件 → 影响 → 风险 → 证据 → 建议
```

日报 / 周报 / 月报 / 专报使用统一数据母模型；内容稿件不固定死模板，根据目标、受众、场景动态生成。

---

## 13. 文件治理

目标结构：

```text
序境/
├─ 00-GOVERNANCE
├─ 01-PRODUCT
├─ 02-ARCHITECTURE
├─ 03-DESIGN
├─ 04-DATA
├─ 05-RUNTIME
├─ 06-REPORT
├─ 07-RESEARCH
├─ 08-AUDIT
└─ 99-ARCHIVE
```

文件处理状态：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE`。

历史资产先审计再处理，不得为了整洁误删生产能力、数据或有效知识。

正式文件名体现职责，不堆砌品牌词。

注释统一：**短、准、必要；优先说明约束、原因或风险。**

---

## 14. 已废止架构

以下不属于当前开发架构：

- 四库架构
- 三仓架构
- 独立思库
- Research Hub 作为第三核心库
- SICI-Core 作为第三核心库
- DCC 作为第三生产核心库
- 新建第三 / 第四生产仓

历史资产是否删除必须逐项 Audit。

---

## 15. 研发与发布协议

```text
Audit
 → Research
 → Architecture Review
 → Dev Plan
 → Implement
 → Test
 → Evidence
 → Review
 → Promotion
```

原则：

1. 先审计，再修改。
2. 先兼容，再重构。
3. 先旁路，再切换。
4. 先验证，再交付。
5. 最小变更优先。
6. 已验证生产能力不得无证据重写。
7. Evidence 优先于主观判断。
8. 新模块必须先进入 Canonical Registry。
9. 破坏性 Rename / Migration / Delete 必须经过确认与验证。

---

## 16. 零号序列

零号序列是最高级研发治理基线。

任何产品、架构、规则、权限、数据、安全与命名变更必须遵循零号序列。

未经明确授权与二次确认，不得改变零号序列。

---

## 17. 当前状态

本 README 只保留**当前有效事实、执行边界与开发入口**。历史过程、旧架构和重复说明不作为当前开发依据，应进入对应 Archive / Audit 文档。

开始任务前：

1. 阅读 `序境/` Canonical Registry。
2. 阅读 `00-GOVERNANCE/`。
3. 阅读本 README。
4. 阅读对应 Contract / Specification。
5. 阅读相关 Test / Evidence。
