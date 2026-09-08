# AGENTS.md — CorTech Lab / Z-Brand 舆情监测系统协作与接管总指令

> Version: V2.0
> Status: Active
> Purpose: 本文件是 Z-Brand-Core 的长期工程协作宪法，供 ChatGPT 主开发窗口、豆包、本地 Ollama、Codex 及其他辅助开发工具共同遵守。
>
> 核心原则：**先审计、再修改；先兼容、再重构；先旁路、再切换；先验证、再交付。**

## 0. 事实基线与协作角色

本项目不是从零开发。当前真实生产基线来自用户最新可运行源码/工作区；历史聊天、架构文档和 GitHub 均不能替代真实源码事实。

### 主开发窗口

ChatGPT 当前主窗口负责：
- 总体架构与产品路线
- 版本基线与变更决策
- 跨模块依赖判断
- P0/P1/P2 优先级
- 数据模型与接口契约
- 代码审计、方案设计、回归标准
- 汇总辅助窗口、测试结果和变更日志

其他聊天窗口属于辅助研究窗口；其结论必须回收到主窗口和 GitHub 文档，不得自行改变核心架构。

### 本地执行与验证

豆包/本地开发环境负责：
- 读取 GitHub 与本地源码
- 按本文件执行修改
- 本地运行、数据库检查、浏览器 E2E
- 记录真实测试结果
- 提交可审计的代码与变更说明

### Ollama

Ollama 是当前正式 AI Runtime。AI 是增强层，不是系统生命线。

---

# 1. 双产品线

## 产品 A：CorTech-TaikooHui

全称：**CorTech Lab-GuangZhou Taikoo Hui Public Opinion Monitoring System**

定位：广州太古汇客户交付版。
- 单品牌/单项目
- Taikoo Hui Profile 固化
- 主体词、排除词、风险口径锁定
- 独立数据库
- 独立运行，不依赖 Z-Brand 在线服务
- 不暴露研发、实验、样本库、多品牌管理等内部能力
- 以验收通过的 Release 快照为准

## 产品 B：Z-Brand Monitoring Platform

定位：多品牌品牌传播与市场情报母平台。
- 多品牌/竞品
- Brand Profile
- Campaign
- KOS/KOL/KOC/普通用户/媒体/官方传播主体
- 内容库
- 营销事件/传播事件/舆情事件
- 事件关系与生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter
- 账号中心
- Ollama/AI Shadow/样本与评测能力
- 新客户 Release 构建能力

**目标：一套 Core，两种 Release 产物；绝不复制两套 Core 源码长期维护。**

---

# 2. 一套 Core、配置驱动、运行隔离

禁止：
- 复制整套源码形成两个长期独立项目
- 客户版与母平台分别修 Bug
- 为客户版物理删除公共 Core 后维护副本
- 让客户版运行时依赖 Z-Brand 服务

产品差异优先通过：
- Runtime Mode
- Feature Flags
- Brand Profile
- 权限
- 路由白名单
- Build/Release 配置

控制。

推荐模式：
- `CUSTOMER_RELEASE`
- `ZBRAND_PLATFORM`

如果当前源码没有成熟 Build 系统，不得为了理想化工程而破坏 P0 稳定性。先配置驱动，后自动化 Build。

---

# 3. AI 运行时：规则内循环优先，Provider-Agnostic（演进自 Ollama-only）

> **演进注记（2026-09-04，用户批准 MERGE）**：本节早期表述为“正式生产 Ollama-only、不得使用任何云端大模型 API”。
> 依据 `AI_PROVIDER_RUNTIME_POLICY_V1` 与 LUMENIS AI Gateway，现行口径升级为 **Provider-Agnostic**：
> 智谱 GLM 为云端主力（日常 `glm-4.5-air` 关思考、强推理 `glm-5.3`、视觉 `glm-4.6v`、联网 `web-search-pro`），
> ARK / 千问为云端备用，**Ollama / gpt-oss 本地模型为离线兜底，本地确定性规则为最终兜底**。
> 以下三条硬红线不因本次演进而改变，且优先级高于任何模型选择：
> 1. **系统生命线不绑定任何单一 AI Provider**：断网、无 key、任一云厂商不可用时，必须能自动降级到本地模型与确定性规则，主链路不中断；
> 2. **规则与数据是业务最终真值，AI 永远只是增强层**（见本节末“AI 不得单独决定”清单）；
> 3. **任何 API Key 只允许经本地 `.env` / 系统密钥注入，严禁写入源码、前端、Git、模板、DB 初始化脚本、日志、测试**。
> 历史 Ollama 链路与历史外部 AI 代码均保留为兜底/Legacy，不删除。

历史外部 AI 代码不得贸然删除：先审计调用链，标记 Legacy/Optional，默认关闭，确认不影响核心后再清理。

严禁将任何 API Key 写入：源码、前端、Git、模板、数据库初始化脚本、日志或测试样例。

系统必须做到：

`没有 AI → 仍可采集 → 仍可过滤 → 仍可去重 → 仍可事件分析 → 仍可风险判断 → 仍可统计 → 仍可报告`

系统主判断来自：规则、数据、主体过滤、时间口径、去重、风险规则、事件规则、统计、质量、证据链。

Ollama 可辅助：情绪解释、主题分类、用户诉求、事件摘要、风险原因、评论总结、趋势解释、报告润色、主体/内容语义识别、事件聚类建议。

AI 不得单独决定：广州太古汇归属、真实发布时间、统计数量、报告周期、原始数据真实性、最终核心风险口径。

AI 输出必须可记录、可追溯、可人工修正；修正结果可沉淀为规则/样本。

---

# 4. 数据库与数据资产：最高保护级别

任何 `.db/.sqlite/.sqlite3`、迁移、SQL、seed、备份、历史数据库、导入导出文件、ORM Model 都属于数据资产。

**未经用户明确授权，不得删除、清空、重建或覆盖生产数据库。**

新增表/字段必须优先采用向后兼容迁移，不得破坏历史数据。

至少保护现有业务实体（实际名称以源码为准）：
- notes
- comments
- events
- daily_reports
- crawl_logs
- keywords
- campaign/brand/profile
- risk
- AI 运行/反馈记录
- 其他实际存在业务表

数据库必须区分生产、测试、实验域；客户 Release 禁止携带其他品牌测试数据、AI 实验数据。

---

# 5. 广州太古汇主体口径：P0 不得弱化

必须保护现有源码中的：
- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `app.py` / `risk_engine.py` 中 `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- 所有下游 SQL、Dashboard、日报/周报/月报、专题统计的主体边界

不得为了“增加采集量”而取消或弱化主体过滤。

已有词表以实际源码为最终准绳。文档中的词表只是保护性基线，不得覆盖源码中已经扩展的词表。

广州太古汇与上海/北京/成都/香港等同名或相似场景必须严格隔离。

---

# 6. 时间口径

必须分离：
- `publish_datetime`：内容真实发布时间
- `captured_at`：系统采集时间

日报、周报、月报、舆情日历、活动周期统计默认按 `publish_datetime`。

“编辑于”“小时前”等相对时间不能未经归一化直接进入正式统计口径；无法可靠归一化时应标记不确定状态。

---

# 7. 小红书采集与 Auth：稳定、可恢复、不可静默

小红书是当前主平台。目标不是高频暴力采集，而是稳定、低风险、可解释、可恢复。

标准链路：
`账号/Cookie → 持久化浏览器上下文 → Playwright/CDP → 搜索发现 → 详情 → 评论 → 标准化 → 质量 → 主体过滤 → 去重 → 入库`

搜索、详情、评论必须分层；详情失败不得等同于“没有舆情”，评论失败不得静默丢弃笔记。

### 官方账号只读保护（硬红线，2026-09-03 用户明令）
- 无论浏览器当前登录的是哪个账号（**包括广州太古汇官方账号**），一切自动采集 / 登录保活 / 内置浏览器自动流程对账号**一律只读**：仅可打开页面、读取 cookie/会话、读取公开内容、探测登录态。
- **永久禁止**任何作用于账号的写操作或交互：关注 / 取关、点赞、收藏、发表评论、私信、发布 / 转发、改资料或设置、退出登录、切换账号、点击 follow/like/collect/comment/publish/logout 等任何社交动作按钮——即使页面已登录也不允许。
- 登录只能由用户本人在系统内浏览器手动扫码；“展开评论 / 滚动浏览”是只读允许项，“发表评论 / 点赞”是写操作禁止项。
- 新增任何浏览器自动化前，必须先确认不含上述账号写操作；code review 以此为必检项。

## 7.1 风控

遇到验证码、安全验证、300012、IP 风险、安全限制页、登录验证页：
- 识别
- 停止危险请求
- 记录状态
- 熔断
- 冷却
- 健康检查
- 在合法人工验证完成后恢复

**不得破解验证码、绕过平台安全验证、对抗或规避平台风控。**

## 7.2 Auth 体验是全局能力

Cookie/session 在任何页面、任何任务、任何时间失效时，不得简单跳转到孤立登录页。

系统应通过全局 Auth 状态中心触发系统内弹窗，至少包含：
- 平台
- 当前账号
- 当前状态
- 失效/验证原因
- 对应二维码或合法登录/验证入口（由平台正常流程提供）
- “我已完成验证”
- “稍后处理”
- 当前任务暂停/恢复状态

验证完成后自动健康检查并恢复任务；未完成则保持暂停/冷却，不得把失败伪装成 0 条。

## 7.3 采集状态

系统至少能表达：
- `SUCCESS`
- `NO_NEW_DATA`
- `RISK_WARNING`
- `NEED_VERIFY`
- `BLOCKED`
- `SESSION_EXPIRED`
- `COLLECT_ERROR`
- `COOLING_DOWN`

如果源码已有更完整六态/多态状态机，优先兼容并扩展，不得重复制造冲突状态。

---

# 8. 多平台 Adapter

目标：
`BasePlatformAdapter → XiaohongshuAdapter / WeiboAdapter / BilibiliAdapter / FutureAdapter`

平台层负责登录/授权、搜索、详情、评论、平台字段、平台 ID、原始 URL；上层统一负责标准化、去重、主体过滤、质量、风险、事件、分析和报告。

不得为新平台复制整套系统。

---

# 9. 品牌传播与市场情报新板块

这是 Z-Brand 与客户版未来共同演进的 Core 能力，但客户版只开放经过验证的业务子集。

核心维度：

`WHO = 传播主体`
`WHAT = 内容`
`WHAT HAPPENED = 事件`
`SO WHAT = 品牌影响`

## 9.1 传播主体

统一纳入：
- KOS
- KOL
- KOC
- 普通用户
- 媒体
- 官方
- 机构

**主体身份与内容属性严格分开。**

`subject_type = KOS/KOL/KOC/...`
`content_type = UGC/商业/官方/测评/体验/投诉/活动内容/...`

禁止：`user_type=UGC` 这种把内容属性当账号类型的设计。

## 9.2 六维主体画像

1. 身份
2. 内容能力
3. 传播能力
4. 品牌关系
5. 舆情表现
6. 事件贡献

识别结果可由规则+Ollama辅助，必须支持人工修正和置信度记录。

## 9.3 三类事件

- 营销事件：品牌主动发起
- 传播事件：市场/用户自发形成热点
- 舆情事件：公众态度聚集，可正可负

事件必须支持生命周期：发现→形成→增长→爆发→扩散→分化→衰减→结束（不同事件类型允许语义差异）。

事件不是孤立列表；必须逐步建设 `event_relation`，记录触发、衍生、继发、并行等关系。

目标因果链：
`营销事件 → 传播事件 → 舆情事件 → 品牌影响`

---

# 10. 页面与交互原则

当前既有菜单应尽量复用：
- 首页概览
- 舆情监测
- 风险预警
- 事件中心
- 负面确认
- 热门话题
- 话题监测端口
- 笔记搜索
- 数据分析
- 品牌业态
- 官方动态
- 品牌营销案例库
- 案例库
- 舆情日历
- 报告中心
- 系统设置

新能力优先作为既有页面内部扩展，不无理由增加大量顶级菜单。

交互必须支持：
`概览 → 下钻 → 详情 → 回溯 → 溯源分析`

事件、主体、内容之间必须支持双向回溯：
- 事件 → 主体 → 历史内容
- 内容 → 所属事件
- 主体 → 参与事件

移动端不能只做到“不溢出”，后续需继续完成合理的分组、弹窗、层级和跳转体验。

---

# 11. 数据分析与报告

分析必须区分：
- 内容量
- 事件量
- 传播贡献
- 风险
- 消费者需求
- 品牌影响

报告默认不把采集窗口误当发布时间窗口。

未来支持：
- 营销传播综合报告
- 传播主体分析报告
- 事件因果溯源报告
- 现有舆情日报/周报/月报

任何分析结论必须能追溯到统计周期、事件、内容和原始证据。

---

# 12. 双产品 Release 与版本血缘

客户版必须是经过验证的 Release 快照，不得运行时依赖 Z-Brand。

每次客户交付必须记录：
- Core 基线版本
- Brand Profile
- 规则/配置变更
- 数据库迁移
- 测试结果
- Release 时间
- 已知限制

推荐血缘：
`Z-Brand Core → 验证 Release → Customer Profile → 独立客户包`

短期允许配置驱动裁剪；成熟后再实现一键 Build 两种产物。

---

# 13. 修改安全协议

任何修改必须遵循：

`审计 → 备份/确认 → 最小修改 → 单测 → E2E → 真实数据验证 → 回归 → CHANGELOG → 交付`

### P0
启动、数据库、主体口径、采集主链路、Auth、数据真实性、核心报告、现有页面稳定性。

### P1
传播主体、三类事件、event_relation、数据质量、动态调度、权限、Release 结构、Ollama 正式接入。

### P2
自动 Build、完整多品牌、完整事件图谱、深度移动端、CI/CD、性能与监控深化。

不得因为 P1/P2 功能破坏 P0。

---

# 14. 测试与验收

修改后至少执行与变更范围匹配的：
- Python 单测
- 数据库迁移测试
- API smoke test
- 浏览器 E2E
- 关键页面检查
- 主体口径回归
- 时间口径回归
- 采集状态回归
- Auth 恢复回归
- 报告周期回归

测试失败时必须记录真实错误，不得通过删除测试、屏蔽异常或伪造结果“修复”。

---

# 15. Git / GitHub 规则

GitHub `Z-Brand-Core` 是工程协作与版本血缘中心。

提交前必须检查：
- 是否误加入 Cookie、Token、API Key、个人隐私
- 是否误加入生产数据库
- 是否误加入测试垃圾
- 是否破坏 AGENTS/文档
- 是否存在重复 Core
- 是否更新 CHANGELOG/状态文档

敏感凭证只允许通过本地 `.env`/系统密钥管理，不进入 Git。

---

# 16. 交付输出格式

每次完成任务后，向主开发窗口报告：

1. 修改了什么
2. 为什么修改
3. 修改了哪些文件
4. 数据库是否变化
5. 测试了什么
6. 测试结果
7. 未完成项
8. 风险/已知限制
9. Git commit
10. 下一步建议

禁止只回复“完成”“已修复”而不提供可审计结果。

---

# 17. 最终不可违反的项目原则

> **稳定版本优先于漂亮重构。**
>
> **真实源码优先于历史印象。**
>
> **系统内循环优先于 AI。**
>
> **客户 Release 必须独立运行。**
>
> **一套 Core，两个产品，不复制两套长期维护代码。**
>
> **数据失败必须显式，不得静默成 0 条。**
>
> **Cookie/session 失效必须在系统内可见、可处理、可恢复。**
>
> **任何新能力先旁路验证，再进入主链路。**

---

# 100. Heritage Intelligence Retrieval Gate（2026-09-09 增补）

> 本节是对当前工程协作流程的增量约束，不改变 Production Truth，不把历史知识直接视为当前事实。

## 100.1 强制前置检索

Codex / Agent 在执行任何涉及产品功能、数据、平台、UI/UX、AI/Agent、Runtime、安全、测试、架构或重构的任务前，必须先读取：

1. `heritage_intelligence/README.md`
2. `heritage_intelligence/ASSET_REGISTRY.md`
3. `heritage_intelligence/ASSET_GOVERNANCE.md`
4. `heritage_intelligence/SOURCE_MAP.md`
5. 与当前任务域对应的 Heritage 资产、Decision Memory、Regression Memory

禁止只读 README / AGENTS / 当前源码后直接重构而忽略 Heritage。

## 100.2 定向检索，不做无差别全文灌入

任务域映射：
- UI/UX → Product/UX + Data Presentation + Decision Memory
- 数据/指标/表格 → Data/Metrics + Evidence/Contracts + Decision Memory + Regression Memory
- 平台 → Platform Intelligence + Domain + Compliance/Contract
- 韩语/内容/i18n → Language & Content Intelligence
- KOS/Podcast/舆情/Campaign/Research/Operations → Domain Methodology + Data + Contract
- AI/Agent → AI & Agent Intelligence + Engineering Governance
- Runtime/Security/Release → Engineering Governance + Regression Memory

Codex 应检索相关资产，而不是每次把整个 Heritage Library 全量塞入上下文。

## 100.3 当前事实优先级

必须遵守：

`Current Production Truth > Current Verified Architecture > Applicable Heritage Asset > Superseded / Reference-only Asset`

Heritage 结论必须回到当前源码、当前测试、当前数据契约和当前运行证据中复核。

## 100.4 Heritage → Capability Promotion

若历史资产仍具有当前价值，Codex 必须判断其属于：
- DESIGN_ENHANCEMENT
- FUNCTION_ENHANCEMENT
- DATA_ENHANCEMENT
- PLATFORM_ENHANCEMENT
- AI_ENHANCEMENT
- ENGINEERING_ENHANCEMENT
- REFERENCE_ONLY
- NOT_APPLICABLE

任何提升为当前 Capability 的资产必须经过：
`Heritage Retrieval → Current Fit → Decision → Implementation → Test → Evidence → Regression → Release Gate`

## 100.5 禁止事项

- 禁止因旧分支落后、文件未被 Runtime 引用而直接判定无用。
- 禁止把旧代码/旧数据库/旧 API/旧 UI/旧 Provider 因进入 Heritage 而自动恢复。
- 禁止 Heritage 绕过 Production Truth、Evidence、测试或 Release Gate。
- 禁止重新发明已有且仍有效的研究、Contract、Metric、Decision 或 Regression 规则而不先检索其历史资产。
