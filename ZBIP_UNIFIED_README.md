# ZBIP Unified Baseline

> Z-Brand Intelligence Platform（ZBIP）四库统一架构、产品定位、Mobile Design System、Browser Runtime、采集 Adapter 与研发协作基线。
>
> 本文件是跨仓库融合基线；不替换本仓库原 README，不改变既有业务代码，不削弱既有生产规则。

## 1. 四库总定位

| 仓库 | 产品/系统 | 中文定位 | Owner职责 |
|---|---|---|---|
| `Z-Brand-Core` | **CTH-POMS** / **ZBMP** | 广州太古汇舆情监测系统 / Z-Brand Monitoring Platform | 业务生产与品牌传播、市场情报 |
| `Development-Command-Console` | **DCC** | 开发指挥控制台 | 研发审计、计划、验证、Evidence、Release、Learning |
| `SICI-Core` | **SICI** | 手机端 AI 开发执行控制台 | Code / Run / Preview / Test / Git / Deploy |
| `AI-Development-Research-Hub` | **AI-D** | AI 开发研究与学习中枢 | Research / Experiment / Shadow / Case / Benchmark / Evidence / Capability |

四库不是四套互相复制的系统，而是：

```text
ZBIP
├── 业务生产：CTH-POMS / ZBMP
├── 工程治理：DCC
├── 开发执行：SICI
└── 研究学习：AI-D
```

共享能力只能有唯一 Owner；其他仓库通过 Contract / Adapter / API / Evidence 使用，不复制核心实现。

## 2. Mobile-first 母设计系统

CTH-POMS、ZBMP、DCC、SICI、AI-D 的移动端体验必须属于同一设计家族。

### 视觉母体

**GPT / Codex × Apple × Linear** 的设计哲学，形成 ZBIP 自有视觉语言，不复制第三方代码或品牌。

统一：
- 黑 / 白 / 灰为主体
- Soft Light / Deep Dark 双主题
- Linear Icon
- 统一 Typography / Radius / Border
- 彩色小圆点作为状态签名
- 克制的 Surface / Frosted Glass 使用
- 高信息密度但低视觉噪声

颜色只用于：Status、Active、Risk、Progress、重要 CTA。

### Icon

- 线性、单色、统一 Stroke / Weight / Size
- 使用 currentColor 思路
- 禁止页面自行创造不一致的彩色图标体系

### Interaction

统一支持：
- Tap / Long Press / Swipe
- Push Navigation
- Bottom Sheet / Drawer
- Pull to Refresh
- Infinite Scroll
- Skeleton / Progressive Loading
- Context Menu / Command Menu
- Loading / Empty / Error / Offline / Retry

### Motion

- 100–180ms：快速反馈
- 180–280ms：普通状态转换
- 280–420ms：页面 / Sheet
- Spring：Sheet / Toggle / Panel / Drag

动效服务于反馈、层级和物理感，不做无意义装饰动画。

## 3. 信息架构：统一母体、产品不同

```text
CTH-POMS → 风险 / 舆情驾驶舱
ZBMP     → 品牌 / 市场情报工作台
DCC      → 研发治理控制台
SICI     → 开发执行控制台
AI-D     → 研究学习工作台
```

四者视觉统一，但不能因为统一视觉而合并业务职责。

## 4. Browser Runtime

长期采用可替换的浏览器执行层：

```text
Mobile UI
  ↓
Browser Surface
  ↓
Browser Session Layer
  ↓
受控 Browser Worker
  ↓
Chromium / Playwright / CDP
  ↓
目标网站
```

手机端负责 UI、Preview、操作、状态与 Evidence 展示；Browser Worker 负责真实浏览器执行。

浏览器能力用于合法浏览、研发 E2E、状态检查与经授权的数据获取；不得用于绕过验证码、封禁、访问限制或平台安全机制。

## 5. “模拟真人浏览”定义

这里的“模拟真人浏览”只定义**用户体验层**：

- 自然滚动与惯性
- 内容流
- 图片渐进加载
- 视频预览
- 正文展开
- 评论展开
- 点赞 / 收藏状态反馈
- 返回 / 下拉刷新
- Loading / Empty / Error 状态

不得将 UI 模拟与规避平台风控混为一谈。

## 6. RedNote / XHS Dual-Source Adapter V2

小红书/RedNote 不直接耦合到 CTH-POMS 业务层，而进入 Adapter：

```text
CTH-POMS
  ↓ Collection Contract
Platform Adapter
  ├── RedNote Adapter
  └── XHS Adapter
        ↓
Approved Browser / API / Source
        ↓
Raw Evidence
        ↓
Normalizer
        ↓
Quality Gate
        ↓
Subject Gate
        ↓
Dedup
        ↓
Database
```

### 当前运行安排

- **RedNote 国际/香港入口：当前主要采集来源。**
- **国内 XHS：暂缓几天，待账号/平台环境稳定后恢复。**
- 长期形成两个有授权来源的冗余采集入口。
- 不通过账号轮换、高频切换或技术手段规避平台封控。
- Source 健康状态必须可观察；异常时进入暂停/冷却/人工恢复，而不是伪装成功。

### 数据目标

逐步覆盖：搜索、话题、笔记、正文、作者、发布时间、标签、点赞、收藏、评论、回复、图片、视频，并为每条记录保留 source、source_url、collected_at、collection_method、source_account、evidence_id、raw snapshot、normalized record 等证据字段。

### 失败状态

至少区分：
`SUCCESS` / `NO_NEW_DATA` / `RISK_WARNING` / `NEED_VERIFY` / `BLOCKED` / `SESSION_EXPIRED` / `COLLECT_ERROR` / `COOLING_DOWN`。

真实失败、验证、封控和网络异常不得显示为“0条数据”或伪装 PASS。

## 7. CTH-POMS 生产红线

本仓库既有主体口径是最高优先级，任何跨仓库融合不得弱化：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `app.py` / `risk_engine.py` `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- Dashboard / 统计 / 事件 / 报告主体边界

广州太古汇必须严格排除其他城市同名场景。

新增能力只能：审计 → 兼容 → 旁路 → 验证 → 切换；禁止为了新功能删除、放宽或绕过旧口径。

## 8. ZBMP 能力边界

ZBMP 是 Z-Brand-Core 内的增强能力层，不形成第二套长期独立 Core。

能力包括：
- 客户 → 品牌 → 竞品 → 项目 / Campaign
- Brand Profile / 监测配置
- 传播主体六维画像
- 内容库 / content_type
- 营销 / 传播 / 舆情三类事件
- `event_relation` 与生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter
- Ollama / AI Shadow / 样本 / 评测
- 新客户 Release 构建能力

主体类型与内容类型严格分离。

## 9. AI 边界

生产核心逻辑不能依赖外部大模型。

```text
规则 / 数据 / 事件 / 风险 / 统计
        ↓
生产主判断
        ↓
Ollama / AI 增强（可选、可退出、可审计）
```

AI 可辅助：主体语义识别、内容分类、情绪解释、消费者需求、事件聚类建议、评论总结、趋势解释、报告文字等。

AI 不独自决定：原始数据真实性、发布时间、主体最终口径、统计数量、报告周期、核心风险事实。

## 10. Evidence / Release

四库统一遵守：

```text
Baseline
 ↓
HEAD / Snapshot
 ↓
Impact Analysis
 ↓
Change Plan
 ↓
Controlled Execution
 ↓
Test / E2E
 ↓
Evidence
 ↓
Security Gate
 ↓
Cross-repository Compatibility
 ↓
Release Candidate
 ↓
人工批准
```

每次变更固定记录：

- 本次任务
- 当前 Baseline
- 当前 HEAD / Remote HEAD
- 修改范围 / 未修改范围
- 文件清单
- Owner / 依赖 / 兼容关系
- 风险
- 测试命令
- 实际测试结果
- Evidence
- NOT_VERIFIED
- Commit SHA
- 下一步

不能把 AI 推测、模拟 E2E、历史测试快照写成当前真实 PASS。

## 11. 四库协作原则

- 只增不破坏已有基线。
- 不跨 Owner 复制核心逻辑。
- 不顺手修改无关模块。
- 不在没有实时 HEAD / Evidence 时宣称完成。
- 生产系统与研究 Shadow 隔离。
- UI 统一不等于业务合并。
- Adapter 失败不能拖垮业务核心。
- 任何重大变更必须可回滚。

## 12. 当前施工优先级

1. CTH-POMS：修复、补全、稳定上线；不做无边界优化。
2. ZBMP：在既有 Core 能力上持续收敛与完善。
3. DCC：Mobile UI + 研发治理 / Evidence / Release 完善。
4. SICI：Mobile UI + Code / Run / Preview / Test / Git / Browser Surface。
5. AI-D：Mobile UI + Research / Shadow / Evidence / Learning。
6. Browser Runtime：作为可替换基础能力逐步接入。
7. RedNote/XHS Adapter V2：当前 RedNote 主用，国内 XHS 暂缓恢复。

## 13. 变更规则

本文件只定义跨仓库融合基线；具体仓库的原 README、生产代码、数据库、测试和已有协议继续有效。

发生冲突时：

**永久基线 / 生产安全红线 > 仓库 Owner 规则 > 本跨仓库融合说明 > 新增建议。**

任何新增能力先归层级、定 Owner、定 Contract，再开发。
