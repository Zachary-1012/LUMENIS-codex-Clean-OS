# ZBIP 四产品统一「架构 / 规则 / UI视觉 / 交互」收敛指令

> **文档版本**：v1.0
> **生效日期**：2026-09-01
> **适用范围**：CTH-POMS / ZBMP / DCC / SICI / AI-D
> **执行原则**：一套母规范 + 各自按产品职责适配，不是把四个产品做成一样

---

## 【ZBIP 四产品统一收敛任务｜Architecture + Rules + UI/UX】

请基于当前仓库真实代码、当前 HEAD、已有 README、现有功能与最新 ZBIP_UNIFIED_README.md 执行本次收敛。

本任务不是推翻重做，也不是大规模重构。

**核心目标**：
在不破坏现有功能、不影响当前开发进度、不改变已经确认的生产规则的前提下，对当前项目进行：
1. 架构收敛
2. 功能归属收敛
3. 规则收敛
4. 数据流收敛
5. UI视觉收敛
6. 交互逻辑收敛
7. 页面层级收敛
8. 动效收敛
9. Light / Dark 双主题收敛
10. Mobile-first 体验收敛

**最终形成**：
"同一产品家族、不同产品职责、不同信息架构"。

---

## 一、最高原则

必须先读取当前仓库真实状态，再执行。

**禁止**：
- 凭记忆改代码
- 根据旧截图猜当前状态
- 覆盖已有功能
- 删除已有能力
- 大规模重构
- 为了视觉统一改变业务逻辑
- 为了视觉统一改变数据库结构
- 修改无关模块
- 把四个产品强行做成相同页面
- 把不同 Owner 的能力复制到本仓库
- 把未验证功能标记为完成

任何不确定内容：标记为 NOT_VERIFIED。

如果发现当前代码与本指令、README 或既有基线存在冲突：**STOP**。先记录：
- 【冲突位置】
- 【当前实际实现】
- 【基线要求】
- 【影响范围】
- 【建议方案】

不得自行扩大修改范围。

---

## 二、四产品永久定位

**统一平台**：Z-Brand Intelligence Platform，简称 ZBIP

### 四产品（5个产品身份，4个仓库）

| # | 产品 | 仓库 | 核心职责 |
|---|---|---|---|
| 1 | CTH-POMS | Z-Brand-Core | 广州太古汇舆情监测生产系统：监测、采集、舆情、风险、事件、报告、生产数据 |
| 2 | ZBMP | Z-Brand-Core | Z-Brand Monitoring Platform：品牌、市场、传播、竞品、消费者、事件、洞察、报告 |
| 3 | DCC | DDC（待建） | Development Command Console：研发治理、任务、审计、Evidence、测试、Release、版本与风险控制 |
| 4 | SICI | SICI-Core | 手机端 AI 开发执行控制台：Code、Run、Preview、Test、Git、Deploy、Browser Surface |
| 5 | AI-D | AI-D（待建） | AI 开发研究与学习中枢：Research、Experiment、Benchmark、Shadow、Evidence、Case、Learning、Capability |

**注意**：
- 视觉可以统一
- 交互原则可以统一
- 设计系统可以统一
- 但是：产品职责不能混合、信息架构不能强行相同、核心数据不能互相复制、Owner 不能混乱

---

## 三、统一架构收敛

统一采用：

```
UI Layer
  ↓
Interaction Layer
  ↓
Application / Feature Layer
  ↓
Domain Layer
  ↓
Data / Service Layer
  ↓
Adapter / External Layer
```

要求：每一层职责明确。

**禁止**：
- UI 直接操作数据库
- 页面直接承担复杂业务逻辑
- 采集器直接决定品牌业务规则
- AI 直接决定生产事实
- 研究代码直接进入生产 Runtime
- DCC 直接承担业务生产
- SICI 直接承担研究逻辑
- AI-D 直接修改生产核心

---

## 四、功能归属

统一遵守：
- CTH-POMS：生产监测
- ZBMP：品牌与市场情报
- DCC：工程治理
- SICI：手机开发执行
- AI-D：研究学习

**共享能力**：必须确定唯一 Owner。其他产品通过 API / Contract / Adapter / Evidence / Capability Registry 使用。禁止复制核心实现。

---

## 五、UI视觉母规范

四个产品必须属于同一个 ZBIP Design System。

**母风格**：GPT / Codex + Apple + Linear，但最终形成 ZBIP 自有视觉语言。不是复制任何第三方页面或代码。

### 视觉基础

- **主色**：Black / White / Gray
- **彩色只承担**：Status / Active / Risk / Progress / Important CTA
- **尤其保留**："彩色小圆点"作为 ZBIP 状态视觉签名
  - ● Success / ● Active / ● Warning / ● Risk / ● Offline / ● Processing

**禁止**：大量使用彩色卡片、大面积渐变、廉价发光、堆叠阴影。

### Typography

统一：标题层级 / 正文 / 辅助文字 / 数字 / 标签 / 状态 / 按钮
建立明确：H1 / H2 / H3 / Body / Caption / Label / Metric
不要每个页面自行定义字号。

### Radius

统一：Button / Card / Input / Sheet / Panel / Modal 圆角体系。不要一个页面一个圆角。

### Border

优先：细 Border / 低对比度 Surface / 层级差异。减少厚重阴影。

---

## 六、Icon 系统

统一 Linear Icon：
- 单色 / 统一 Stroke / 统一 Weight / 统一 Size / currentColor
- 状态通过颜色表达
- 不使用无意义的 Emoji 作为正式 UI Icon
- 不混用大量不同图标风格

建立：Icon Size Token / Icon Stroke Token / Icon Color Token，所有产品复用。

---

## 七、Light / Dark

必须双主题。

- **Light**：白色/浅灰 Surface，黑色文字，低对比度 Border，彩色状态点
- **Dark**：黑色/深灰 Surface，白色文字，低对比度 Border，彩色状态点

要求：不能只是简单反色。必须重新处理 Surface / Border / Text / Secondary Text / Input / Card / Sheet / Modal / Navigation / Status，保证可读性、层级、对比度、触控可见性。

---

## 八、Mobile-first

- DCC / SICI / AI-D：优先手机端
- CTH-POMS / ZBMP：也必须采用统一 Responsive Design System

手机不是桌面页面缩小版。必须考虑：单手操作、拇指区域、Bottom Navigation、Bottom Sheet、Swipe、Long Press、Pull Refresh、Horizontal Scroll、Keyboard、Safe Area、不同屏幕尺寸。

---

## 九、统一交互语言

统一：Tap / Long Press / Swipe / Drag / Pull Refresh / Bottom Sheet / Drawer / Context Menu / Command Menu / Progressive Loading / Skeleton / Infinite Scroll

统一状态：Loading / Empty / Error / Offline / Retry / Success / Warning / Risk / Processing

任何操作都应该有反馈：点击 → visual feedback → processing → result。不能点击以后没有任何反馈。

---

## 十、动效系统

建立统一 Motion Tokens：
- 快速反馈：100–180ms
- 普通状态：180–280ms
- 页面/Sheet：280–420ms
- Spring：Sheet / Toggle / Panel / Drag

动效只服务：反馈、层级、状态、空间关系、物理感。

**禁止**：无意义动画、过度动画导致性能下降。低端手机必须能够正常运行。

---

## 十一、页面架构

每个页面必须先回答：WHO / WHAT / WHY / ACTION

页面结构优先：
```
Navigation
  ↓
Context
  ↓
Primary Information
  ↓
Primary Action
  ↓
Secondary Information
  ↓
Detail
  ↓
History / Evidence
```

避免：所有东西都放 Dashboard、一页塞几十个卡片、功能没有层级。

---

## 十二、四产品布局差异

| 产品 | 重点 | UI 应该 |
|---|---|---|
| CTH-POMS | 风险/舆情/趋势/事件/监测/报告 | 信息密度高，状态清晰，风险优先 |
| ZBMP | 品牌/市场/传播/消费者/竞品/洞察 | 工作台化，探索性，关系化，分析化 |
| DCC | 任务/审计/版本/Evidence/Release/风险 | 控制台化，状态明确，操作精准，审计可追溯 |
| SICI | Code/Run/Preview/Test/Git/Deploy | 执行效率优先，编辑效率优先，操作路径短 |
| AI-D | Research/Experiment/Benchmark/Shadow/Evidence/Learning | 研究工作台，实验可追踪，证据可验证，知识可沉淀 |

---

## 十三、Browser Surface

统一设计：
```
Mobile UI
  ↓
Browser Surface
  ↓
Browser Session
  ↓
Browser Worker
  ↓
Chromium / Playwright / CDP
```

Browser Surface 必须与普通页面视觉统一。重点：浏览、滚动、返回、刷新、页面状态、Loading、Error、Offline、Evidence。

"模拟真人浏览"仅指 UI/UX：自然滚动、惯性、内容流、图片渐进加载、视频预览、正文展开、评论展开、点赞/收藏状态反馈、返回、刷新。

**不得**把 UI 模拟变成：验证码绕过、封禁绕过、访问限制绕过、平台风控规避。

---

## 十四、RedNote / XHS

采集业务归属：CTH-POMS / ZBMP。采用 Adapter。

当前运行策略：
- RedNote 香港/国际入口：主要采集来源
- 国内 XHS：暂缓几天
- 后续：两个有授权来源交叉采集

Adapter 流程：
```
Source → Raw Evidence → Normalize → Quality Gate → Subject Gate → Dedup → Database
```

采集失败必须真实记录。**禁止**：把失败显示为 0 条数据、伪装 SUCCESS。

---

## 十五、CTH-POMS生产红线

以下逻辑绝对不能因为本次 UI / 架构收敛被削弱：
- SUBJECT_WORDS
- SUBJECT_EXCLUDE_WORDS
- subject_hit()
- _subject_sql_and_values()
- aggregate_events()
- build_daily_report()
- Dashboard / 统计 / 事件 / 报告 / 主体过滤

广州太古汇必须继续严格排除其他城市同名场景。任何修改必须先说明影响。

---

## 十六、AI规则

AI 是增强层，不是生产事实 Owner。

生产：规则 + 数据 + 事件 + 风险 + 统计 负责最终生产口径。

AI 可以辅助：分类、语义分析、事件聚类、趋势解释、消费者需求、报告文字、研究建议。

但 AI 不能独自决定：原始事实、统计数字、主体最终口径、风险最终事实、生产报告事实。

---

## 十七、Evidence

每次执行必须产生：
【任务】【Baseline】【HEAD】【Remote HEAD】【修改范围】【未修改范围】【文件清单】【Owner】【依赖】【风险】【测试】【实际结果】【Evidence】【NOT_VERIFIED】【Commit SHA】【下一步】

不能只说"完成"或"通过"。

---

## 十八、执行方式

本次任务必须分阶段执行。

### Phase 1：读取
读取 README / ZBIP_UNIFIED_README.md / 目录结构 / 核心代码 / 路由 / 组件 / 数据模型 / 数据库 / 测试 / 配置 / 现有 UI。
输出：【当前架构图】【功能总览】【功能归属】【页面总览】【当前UI问题】【当前交互问题】【当前技术债】

### Phase 2：收敛
建立 Architecture Map / Feature Map / Ownership Map / Data Flow Map / UI Map / Interaction Map / Motion Map / Design Token Map。禁止立即大改代码。

### Phase 3：UI/UX
先统一 Design Tokens（Typography/Icon/Color/Spacing/Radius/Border/Motion/Light-Dark），再统一 Navigation/Layout/Components/States，最后才进入具体页面。

### Phase 4：开发
只修改必要文件。优先复用/抽象/Adapter/Token/Component，避免复制粘贴。

### Phase 5：测试
至少：启动测试、路由测试、组件测试、交互测试、Light/Dark、Responsive、Mobile、Error、Empty、Loading、核心功能回归。有 Browser 则进行真实 E2E。

### Phase 6：交付
必须输出：【完成】【未完成】【NOT_VERIFIED】【修改文件】【架构变化】【UI变化】【交互变化】【动效变化】【测试结果】【风险】【Commit SHA】【下一步】

---

## 十九、最重要的执行规则

这次不是"重新设计一个漂亮页面"，而是把整个 ZBIP 四产品逐步收敛成：
一个设计系统 + 四套产品信息架构 + 清晰 Owner + 清晰数据流 + 清晰功能边界 + 统一交互语言 + 统一 Motion + 统一 Light/Dark + 统一 Mobile Experience。

最终效果：用户一眼就知道这是同一个 ZBIP 产品家族。但进入不同产品以后：
- CTH-POMS 像舆情驾驶舱
- ZBMP 像品牌情报工作台
- DCC 像研发控制中心
- SICI 像手机开发执行环境
- AI-D 像研究学习工作台

本次执行：先收敛，再设计，再实现，再测试。

**禁止**：
- 跳过架构与规则收敛直接大规模改 UI
- 为了 UI 好看破坏业务
- 为了架构漂亮破坏生产
- 为了快速完成制造假 Evidence

以真实仓库代码和真实测试结果为最终依据。

---

## 仓库与产品映射说明

实际是 **4个仓库、5个产品/系统身份**：
- Z-Brand-Core 仓库包含 CTH-POMS + ZBMP 两个产品身份
- SICI-Core 仓库 = SICI 产品
- DDC 仓库 = DCC 产品（待建本地克隆）
- AI-D 仓库 = AI-D 产品（待建本地克隆）

执行逻辑是一套，但每个仓库只执行属于自己的部分。

---

*文档维护：Zachary | 最后更新：2026-09-01*
