# Z Brand Core（序境-Core｜Production Truth）

> **序境 · 芥子纳须弥** —— 正式产品名「序境」；Z Brand Core 是序境双子星中的**生产核心（序境-Core）**。
> 对外产品 UI / 报告 / 设置页统一使用「序境」；`Zachary` 仅保留为仓库/研发历史标识，不作为产品展示名。
> 双子星：序境-Core（本仓库，生产/业务/数据/运行时） + 序境-Intelligence（Zachary OSAI，AI/研究/知识）。
> 收敛基线：《序境｜双子库全量收敛与产品研发总执行指令》（2026-09-04）；Canonical 规范见 `序境/` 目录。

> **双子星 A｜品牌业务生产、代码开发、测试与执行核心**
>
> **生产边界硬约束（不可编辑）**：CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件（依据 AGENTS.md §2 一套 Core 配置驱动、运行隔离）。
>
> 本 README 是 Z Brand Core 当前有效的产品、架构、业务真相、权限、保护、限制与研发协作白皮书。历史“四库 / 三仓 / 思库 / Research Hub”方案退出当前有效架构，不得作为新开发依据。
>
> **最后重基线：2026-09-04（序境收敛）**
>
> **当前版本事实：以仓库 `VERSION` 为准；当前 `VERSION=5.9.9`。**
>
> **唯一生产双库：序境-Core（本仓）+ 序境-Intelligence（Zachary OSAI）**

---

## 0. 最高级事实：一个 Core、两个模式、双子星

```text
                         双子星研发系统
                              │
              ┌───────────────┴───────────────┐
              ↓                               ↓
        Zachary OSAI                     Z Brand Core
       学习 / 研究 / AI                 生产 / 开发 / 执行
              │                               │
              │ Contract / Technical Plan     │ Code / Test / E2E
              ├──────────────────────────────→│
              │                               │
              │ Evidence / Runtime Results    │
              │←──────────────────────────────┤
              │                               │
              └──────受控双向研发闭环──────────┘
```

Z Brand Core 内部仍坚持：

> **一个 Core、一个生产代码真相、两种受控产品模式。**

- **CTH-POMS**：广州太古汇客户交付/当前主力生产入口。
- **ZBMP**：Core 内的母平台增强能力，通过配置/Feature Gate/Release 逐步开放，不维护第二套 Core 源码。

### 已废止，不得恢复

- 四库架构
- 三仓架构
- 独立思库
- AI-Development-Research-Hub 作为当前研究权威库
- SICI-Core 作为当前第三核心库
- DCC 作为当前第三核心库
- 任何新的第三/第四生产仓

历史组件是否保留，只能通过逐项 Audit 决定：`KEEP / MIGRATE / LEGACY / RETIRE`。不得为了“清爽”直接删除未经验证的生产能力。

---

## 1. Z Brand Core 的唯一职责

Z Brand Core 负责把已经确认的产品/技术要求变成真实可运行的软件：

- 生产代码
- 数据库与迁移
- 采集器与平台 Adapter
- 主体过滤
- 舆情 / 事件 / 风险
- 统计与报告
- API / UI
- Runtime / Health / Recovery
- 测试 / E2E / CI
- Release / 部署
- 生产 Evidence

**ZBC 是生产业务真相源。**

---

## 2. CTH-POMS 与 ZBMP

### CTH-POMS

广州太古汇舆情监测系统，当前主力生产/客户交付入口。

核心能力包括：

- 舆情监测
- 风险预警
- 事件中心
- 负面确认
- 热门话题
- 话题监测
- 笔记搜索
- 数据分析
- 品牌业态
- 官方动态
- 品牌营销案例库
- 舆情日历
- 报告中心
- 系统设置
- Zachary 智能助手
- Auth Recovery

当前主平台为小红书。其他平台只能通过 Adapter 接入，未经完整验证不得接管生产任务。

### ZBMP

Core 内母平台能力，长期支持：

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
- 新客户 Release

CTH-POMS 与 ZBMP 共享 Core，不复制两套长期源码。

---

## 3. 生产业务真相保护｜P0

以下是最高保护对象，任何 AI、研究方案、外部工具、采集器优化都不能绕过：

### 太古汇主体过滤

必须保护：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体边界
- `build_daily_report()` 主体边界
- 下游统计 / Dashboard / 报告的主体口径

**不得为了增加采集量而弱化主体过滤。**

### 时间口径

必须区分：

- `publish_datetime`：内容真实发布时间
- `captured_at`：系统采集时间

正式日报/周报/月报/日历默认按 `publish_datetime`。无法可靠归一化的相对时间必须标记不确定，不能伪装成精确时间。

### 数据库

生产 DB 是最高保护资产。

未经明确 Change Plan 与验证，不得：

- 删除
- 清空
- 重建
- 覆盖
- 破坏历史数据

新增字段/表优先采用向后兼容迁移。生产、测试、实验数据必须隔离。

---

## 4. AI 边界

当前 AI 为**增强层**，不是系统生命线。

即使没有 AI，系统也必须能够：

```text
采集 → 标准化 → 过滤 → 去重 → 事件 → 风险 → 统计 → 报告
```

Ollama / AI 可以辅助：

- 情绪解释
- 主题分类
- 用户诉求
- 事件摘要
- 风险原因
- 评论总结
- 趋势解释
- 报告润色
- 语义识别
- 事件聚类建议

AI 不得单独决定：

- 太古汇归属
- 真实发布时间
- 统计数量
- 报告周期
- 原始数据真实性
- 最终核心风险口径

AI 输出必须可追溯、可人工修正、可回溯到原始输入与模型/提示版本。

---

## 5. 小红书采集｜当前 P0

小红书是当前主平台。

目标不是暴力高频，而是：

> **稳定、低风险、可解释、可恢复、可观察、可审计。**

现有采集能力不得因为新架构而直接推倒；应在已验证 Collector 基础上增量升级为 Resident Runtime。

目标：

```text
系统启动
 ↓
XHS Preflight
 ↓
Session 有效？
 ├─ YES → Resident READY
 └─ NO  → 系统内 AUTH_REQUIRED
               ↓
           正常扫码/登录
               ↓
           Session Verify
               ↓
              READY
               ↓
          Resume Task
```

### 双身份硬白名单

唯一允许进入采集任务的身份：

```text
XHS_CN_PRIMARY
XHS_RETINAUT
```

必须做到：

- 独立 Browser Profile
- 独立 Cookie Jar / Session
- Identity → Task 强绑定
- 未知身份 DENY
- 第三身份 DENY
- 任意 Cookie 路径注入 DENY

两个账号只能用于正常授权身份之间的任务隔离、连续性与故障处理；不得用账号切换规避平台安全、限流、验证码或封禁。遇安全信号：`STOP → COOLDOWN → HUMAN REVIEW`。

### Auth Recovery

Session 失效不得简单跳外部登录页，应由系统内 Auth 状态中心触发授权弹窗：

```text
AUTH_REQUIRED
 ↓
系统内 XHS Auth Modal
 ↓
用户完成正常扫码/登录
 ↓
Session Verify
 ↓
READY
 ↓
恢复暂停任务
```

未验证成功必须保持暂停/冷却，不得将失败伪装为“0 条数据”。

---

## 6. Resident AI Browser Runtime

小红书 Collector 的下一阶段不是另写一个爬虫，而是：

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

AI Browser 的执行边界：

```text
Intent
 ↓
Planner
 ↓
Policy
 ↓
Typed Browser Tool
 ↓
Identity-bound Runtime
 ↓
Evidence
```

禁止 LLM 直接获得无限制浏览器、Cookie、文件系统或生产写入权限。

网页中的文字、评论、搜索结果等全部属于不可信数据，不能成为系统指令。

---

## 7. Collector / Platform Adapter 架构

统一目标：

```text
BasePlatformAdapter
 ├─ XiaohongshuAdapter
 ├─ WeiboAdapter
 ├─ BilibiliAdapter
 └─ FutureAdapter
```

平台 Adapter 负责：

- 正常登录/授权
- 搜索
- 详情
- 评论
- 平台字段
- 平台 ID
- 原始 URL

Core 上层负责：

- 标准化
- 去重
- 质量
- 主体过滤
- 风险
- 事件
- 统计
- 报告

不得为了新平台复制整套系统。

采集状态至少能够表达：

`SUCCESS / NO_NEW_DATA / RISK_WARNING / NEED_VERIFY / BLOCKED / SESSION_EXPIRED / COLLECT_ERROR / COOLING_DOWN`

如果现有源码存在更完整状态机，必须兼容扩展，不得制造第二套互相冲突的状态定义。

---

## 8. Health / Recovery / Evidence

系统必须能发现：

> “进程还活着，但采集已经死了。”

至少记录：

```text
browser_alive
page_alive
session_valid
runtime_last_heartbeat
collector_last_start
collector_last_success
collector_last_error
pending_auth
circuit_state
last_evidence_id
```

每次采集必须形成非敏感 Evidence：

```text
collection_id
identity_id
task_id
start_at
end_at
runtime_version
collector_version
parser_version
result_count
filtered_count
duplicate_count
error_count
policy_snapshot
health_snapshot
verification_status
```

Cookie / Token / Session / API Key 等不得进入 Evidence 或 Git。

---

## 9. 品牌传播与市场情报模型

核心链路：

```text
WHO → WHAT → WHAT HAPPENED → SO WHAT
```

### WHO

KOS / KOL / KOC / 普通用户 / 媒体 / 官方 / 机构。

### WHAT

UGC / 商业 / 官方 / 测评 / 体验 / 投诉 / 活动等。

**主体身份与内容类型严格分离。**

### WHAT HAPPENED

- 营销事件：品牌主动发起
- 传播事件：市场/用户形成热点
- 舆情事件：公众态度聚集

支持事件生命周期与 `event_relation`。

### SO WHAT

传播贡献 / 情绪 / 风险 / 消费者需求 / 竞品 / AI 洞察 / 报告。

---

## 10. 权限矩阵

| 能力 | ZBC | OSAI | ChatGPT | Trae/豆包 |
|---|---|---|---|---|
| 生产源码 Owner | **ALLOW** | 禁止越界 | 审计/设计 | 按授权执行 |
| 生产 DB | **CONTROLLED** | DENY | 设计/Review | 仅按 Change Plan |
| 主体口径 | **P0 Owner** | DENY | Review | 仅按明确计划 |
| 研究 | ALLOW | **OWNER** | **OWNER/LEAD** | 辅助 |
| 代码执行 | **OWNER** | 不直接执行 ZBC | 设计/Review | **执行端** |
| Cookie/Token 导出 | DENY | DENY | DENY | DENY |
| 第三 XHS 身份 | DENY | DENY | DENY | DENY |
| Production Release | CONTROLLED | 不直接执行 | Gate | 执行 |
| 测试/E2E | ALLOW | 可研究 | 设计标准 | EXECUTE |

---

## 11. ChatGPT / Trae / 豆包施工策略

### ChatGPT

负责：

- 全局审计
- 架构
- 深度研究
- P0/P1/P2
- Contract
- 施工策略
- 风险
- Review
- 最终变更判断

### Trae / 豆包

负责：

- 读取真实源码
- 实际写代码
- 执行测试
- 浏览器 E2E
- 数据库检查
- 运行验证
- Diff
- Commit / Push

执行端必须遵守当前 README、AGENTS、Change Plan 与明确任务指令；发现架构冲突必须停止，不得自行改变 Owner 或新增架构。

### 标准循环

```text
ChatGPT
  ↓ Audit / Research / Architecture / Contract
Trae / 豆包
  ↓ Code / Test / E2E / Evidence
ChatGPT
  ↓ Review / Correct / Next Plan
Trae / 豆包
  ↓ Code / Verify
```

---

## 12. 统一施工 Gate

重要任务默认：

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

- 先审计，再修改
- 先兼容，再重构
- 先旁路，再切换
- 先验证，再交付
- 最小补丁优先
- 已验证能力不得无证据重写
- 失败不得伪装为成功
- `NOT_VERIFIED` 不得冒充 `PASS`

---

## 13. 当前问题优先级

### P0

1. 双子星架构事实收敛
2. OSAI ↔ ZBC Contract 收敛
3. 小红书 Resident AI Browser Runtime
4. 双身份硬白名单与独立 Profile/Session
5. 系统内 Auth Modal
6. Health / Heartbeat / Recovery / Circuit Breaker
7. Evidence / Provenance
8. 24h / 72h / 7d 长驻验证

### P1

- `/architecture`
- `/event-graph`
- 移动体验继续收敛
- 更多平台 Adapter
- 更成熟的 AI Browser Benchmark

### P2

- 非阻断重构
- 视觉增强
- 性能优化
- 实验性能力

---

## 14. 历史能力迁移

历史四库体系里的代码不能直接视为“必须删除”。逐项判断：

```text
历史能力
 ↓
Audit
 ↓
KEEP / MIGRATE / LEGACY / RETIRE
 ↓
OSAI 或 ZBC
```

研究/AI/通用能力优先归 OSAI；生产业务能力归 ZBC；共享能力通过 Contract / Adapter / Evidence 协作。

---

## 15. 最终不可变原则

1. **Z Brand Core 是生产业务与代码执行核心。**
2. **Zachary OSAI 是 AI 学习、研究与技术研发大脑。**
3. **只维护双子星两个核心私库。**
4. **不恢复四库，不恢复独立思库，不新增第三核心库。**
5. **CTH-POMS / ZBMP 的生产真相由 ZBC 掌握。**
6. **主体过滤、时间口径、数据库和生产数据属于 P0 保护对象。**
7. **AI 是增强层，不得取代业务真相。**
8. **小红书双身份严格白名单：`XHS_CN_PRIMARY` + `XHS_RETINAUT`。**
9. **敏感凭证永不进入 Git / Evidence。**
10. **跨库优先 Contract / Adapter，不复制核心实现。**
11. **ChatGPT 负责架构/研究/Review；Trae 与豆包负责代码执行。**
12. **所有重要变更遵循 Audit → Research → Architecture → Plan → Implement → Test → Evidence → Review → Promotion。**

> **Z Brand Core 不再等待第三方研发中枢替它执行。确认后的技术方案直接进入 ZBC 的开发施工链；OSAI 负责持续学习和研究，ZBC 负责把成熟能力真正做进产品。**

**Status: ACTIVE / DUAL-REPOSITORY BASELINE / FOUR-REPOSITORY MODEL RETIRED**

---

## 16. 跨仓关系锚点（双子星库 Contract）

1. 🤖 [Zachary-OS-AI README 双子关系段](https://github.com/Zachary-1012/Zachary-OS-AI#双子产品关系) (repo=Zachary-1012/Zachary-OS-AI, branch=main, section=双子产品关系, last_verified_sha=2fbdfba)
2. 📘 [DCC README §17 与 Z-Brand-Core 的 13 项职责](https://github.com/Zachary-1012/Development-Command-Console#17-与-z-brand-core-的关系) (repo=Zachary-1012/Development-Command-Console, branch=main, section=§17, last_verified_sha=2fbdfba)
3. 🔧 [AI-DRH Capability Registry](https://github.com/Zachary-1012/AI-Development-Research-Hub/blob/main/CAPABILITY-REGISTRY.md) (repo=Zachary-1012/AI-Development-Research-Hub, branch=main, section=Capability Registry, last_verified_sha=2fbdfba)

> 说明：last_verified_sha 指 ZOSAI 仓（B 仓）权威基线 commit（`2fbdfba` = README 12节 + .gitignore + 6 组件 E-008 四库术语升级，稳定锚点不因后续 CHANGELOG/commit 变更而漂移）；三链接目标 GitHub 仓内容在本地都以 ZOSAI components/ 快照形式同步验证过。A 仓当前最终 HEAD（README 融合 + 资产清单 + 四层矩阵 + E-001~E-009 + CHANGELOG 开工/结束）= `065eaa6`（**最终 SHA 若因后续 amend 变动，以 `git log -1 --oneline` 输出为唯一权威；锚点 last_verified_sha=2fbdfba 保持不变**）。
