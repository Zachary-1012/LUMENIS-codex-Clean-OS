# Z-Brand Core

## 1. 产品定位（📊 Z-Brand-Core 品牌传播与市场情报智能平台）

> **产品标识**：📊 Z-Brand-Core（双子星 A 产品｜业务生产权威）
> **当前版本**：v5.9.7｜main 分支｜E2E 42/42 通过
>7:> **双子对端**：🤖 [Zachary-OS-AI README 双子关系段](https://github.com/Zachary-1012/Zachary-OS-AI#双子产品关系) (repo=Zachary-1012/Zachary-OS-AI, branch=main, section=双子产品关系, last_verified_sha=f0b8bb5)
> **生产边界硬约束（不可编辑）**：CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件。依据 [AGENTS.md §2](AGENTS.md#2-一套-core配置驱动运行隔离)。

> **品牌传播与市场情报智能平台核心底座**
>
> 一个 Core、一个生产产品入口、一个受控增强能力层。
>
> - **CTH-POMS**：CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System，当前主力生产/客户交付入口。
> - **ZBMP**：Z-Brand Monitoring Platform，Core 内的母平台增强能力层，通过受控 Feature Gate / License 等方式逐步启用，不作为第二套长期独立维护源码。
> - **Development-Command-Console（DCC）**：独立的内部 AI 研发中枢，负责审计、规划、受控升级和证据链，不是 CTH-POMS 的生产运行时依赖。
>
> **当前 GitHub 主线最新已进入 v5.9.7。** 本 README 以最新源码、提交记录、项目基线与已记录测试结果为依据；实时数据库、进程和运行环境仍必须以实际运行时检查为准。

本项目已经从单一的"舆情监测系统"演进为 **品牌传播与市场情报智能平台**。

核心目标不是只回答"有没有负面"，而是形成：

```text
品牌做了什么营销动作？
        ↓
谁在传播？
        ↓
产生了什么内容？
        ↓
形成了什么事件？
        ↓
事件如何演化、扩散、分化？
        ↓
对品牌意味着什么？
        ↓
风险 / 消费者需求 / 传播效果 / 竞品对标 / 决策输出
```

### 四层核心模型

| 层 | 维度 | 核心内容 |
|---|---|---|
| 1 | **WHO** | 传播主体：KOS / KOL / KOC / 普通用户 / 媒体 / 官方 / 机构 |
| 2 | **WHAT** | 内容：UGC / 商业 / 官方 / 测评 / 体验 / 投诉 / 活动内容等 |
| 3 | **WHAT HAPPENED** | 事件：营销事件 / 传播事件 / 舆情事件 |
| 4 | **SO WHAT** | 品牌影响：传播贡献 / 情绪 / 风险 / 消费者需求 / 竞品 / AI 洞察 / 报告 |

### 核心业务约束

**主体类型与内容类型严格分离。**

- `subject_type=KOS`：账号/传播主体身份。
- `content_type=UGC`：具体内容属性。
- **禁止把 UGC 设计成账号类型。**
- KOL 可以发布 UGC；KOS 可以发布商业内容；同一主体可以产生不同内容类型。

---

## 2. 双子产品关系与边界

四库定义：ZBC（本仓业务生产权威）+ SICI（生产运行时子仓）+ DCC（研发中枢 Git Submodule）+ AI-DRH（研究学习权威）。
研发侧职责（原 DCC 描述）：四库协同下，DCC 承担需求→源码审计→影响分析→最小补丁→隔离验证→测试→Diff/Evidence 审计→人工批准→PR/Release 验收的全链路研发中枢。

### ZBC vs Zachary-OS-AI 双子 10 维对比

| 维度 | 双子星 A：📊 Z-Brand-Core（本仓） | 双子星 B：🤖 Zachary-OS-AI |
|---|---|---|
| **产品定位** | 品牌传播与市场情报智能平台｜业务生产权威 | Zachary 独立 AI OS 体系｜AI 身份与通用能力权威 |
| **核心职责** | CTH-POMS 生产交付 + ZBMP 母平台能力建设 | Zachary 人设 / AI Agent / 通用研发能力 / 独立身份保护 |
| **生产依赖关系** | CTH-POMS/ZBMP 生产运行**绝对不依赖**双子 B 任何组件（硬约束） | 可调用 ZBC 的 Evidence 与研究成果，但不反向决定生产 |
| **数据所有权** | 采集数据 / 主体口径 / 风险判定 / 生产报告 所有权本仓 | Zachary 人设记忆 / AI 模型权重 / 通用 Agent 逻辑 所有权独立 |
| **AI 角色** | Ollama-first / 可退出 / Shadow Mode / 纯增强层 | 独立 AI 身份 / 自主决策链路 / BASE-001 不可变人设 |
| **Owner 与变更门槛** | ZBC main 团队 / P0 生产变更需 3-way 验证 | ZOSAI 独立团队 / BASE 层变更需 IMMUTABLE 审查 |
| **部署形态** | CTH-POMS 客户部署 + ZBMP 多租户潜力 | Zachary OS 独立部署 / 不嵌入 ZBC 生产链路 |
| **跨仓复制权限** | 组件禁止复制到 AI 仓；Evidence 允许受控导出 | IMMUTABLE BASE 禁止复制到本仓；研究结论允许引用 |
| **协作模式** | 本仓定义 A 侧矩阵；四库协作（ZBC+SICI+DCC+AI-DRH） | 定义 B 侧矩阵；与本仓仅通过规范接口协作 |
| **冲突仲裁** | 业务口径冲突→本仓源码/DB 优先（见§12.6优先级链） | AI 人设冲突→ZOSAI IMMUTABLE BASE-001 优先 |

### 全局反馈环简述

双子之间形成 **生产事实→研究学习→能力增强→审计回注** 的受控反馈环：

1. ZBC 生产过程产生的 Evidence / 样本 / 架构决策，单向流动至 AI-DRH（研究学习权威）
2. Zachary-OS-AI 基于 AI-DRH 学习成果迭代通用 AI 能力
3. 增强能力经过 DCC 研发中枢审计、隔离验证、Shadow Mode 对照后，以补丁形式回注 ZBC
4. 整个过程不形成循环生产依赖：ZBC 生产路径永远独立于 ZOSAI 运行时

依据 [AGENTS.md §2](AGENTS.md#2-一套-core配置驱动运行隔离) 生产隔离原则。

---

## 3. 本仓子产品：CTH-POMS 与 ZBMP 双模式

### CTH-POMS｜广州太古汇舆情监测系统（18 项能力）

当前生产和客户交付优先级最高。
现有核心页面与能力包括：

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
- Zachary 智能助手
- Auth Recovery Center

当前主平台为**小红书**。其他平台以 Adapter/扩展槽位方式接入，未经完整验证不得接管生产任务。

### ZBMP｜母平台增强能力（12 项能力）

长期复用能力包括：

- 客户 → 品牌 → 竞品 → 项目 / Campaign
- Brand Profile 与监测配置
- 传播主体库与六维画像
- 内容库与内容类型
- 营销 / 传播 / 舆情三类事件
- `event_relation` 事件关系
- 事件生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter
- Ollama / AI Shadow / 样本与评测
- 新客户 Release 构建能力

### 双模式对比表

| 维度 | CTH-POMS 模式 | ZBMP 模式 |
|---|---|---|
| **模式** | 客户定制生产模式 | 母平台通用增强模式 |
| **定位** | 当前主力生产 / 客户交付入口，广州太古汇 P0 最高优先级 | Core 内隐藏增强能力层，长期复用能力沉淀 |
| **客户形态** | 单客户（广州太古汇）定制交付 | 多客户 / 多品牌 / 多项目架构预留 |
| **品牌配置** | 硬编码 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS + 广州太古汇主体过滤保护 | Brand Profile 动态配置 + 监测配置中心 |
| **数据库** | `data/monitor.db` + schema_version v8 + 业务口径硬保护 | 同库多租户隔离 + 客户/品牌/项目三层外键 |
| **Feature Gate** | 生产能力默认全开；ZBMP 能力默认关闭 | 受控 License / Feature Flag 渐进开启，不接管生产 |
| **Runtime Mode** | 生产稳定优先，低风险可解释可恢复（见 §6.1 采集 8 状态） | 旁路增强 / Shadow Mode / 可退出（见 §7 AI 架构） |
| **典型交付物** | 13 份 daily_reports、7135 条审核记录、178 份采集日志、667 条笔记、151 个事件、180 条 event_mentions、品牌分析报告 | 传播主体六维画像、三类事件关系图谱、品牌知识库（80 条/7 分类）、20 个 11 维深度拆解案例、消费者需求洞察、品牌对标分析 |

---

## 4. 产品/组件 × Owner × 是否允许跨仓复制

| 类别 | 组件名 | 路径或模块标识 | Owner | 变更门槛 | 跨仓使用权限 | 依据标签 |
|---|---|---|---|---|---|---|
| 子产品 | CTH-POMS | `app.py` (264KB) + 蓝图 routes/ + 前端 CTH 页面 | ZBC main | P0 最高级 / 3-way 验证 | 禁止复制 / 允许 Evidence 导出 | [AGENTS §2] [生产隔离] |
| 子产品 | ZBMP | `zbmp/` 蓝图模块 + Feature Gate 受控页面 | ZBC main | P1 中高级 / 回归验证 | 禁止复制 / 允许 Evidence 导出 | [Feature Gate] |
| 子产品 | Development-Command-Console | Git Submodule `tools/development-command-console` (pinned SHA，升级见 §9.5.6) | DCC submodule 独立 Owner | P1 / 子模块升级 7 步流程 | 只读审计 / 禁止嵌入生产运行时 | [Submodule 契约] |
| 组件 ① | collector 系列（小红书主采集 + Adapter 扩展槽） | `collector_v2/` + `platforms/xhs/` | ZBC main | P0 / 采集状态不回归 | 禁止复制 | [采集稳定优先 §6.1] |
| 组件 ② | risk_engine（风险/主体/事件） | `risk_engine.py` 含 `_subject_sql_and_values()` / `aggregate_events()` | ZBC main | P0 / 主体口径不弱化 | 禁止复制 / 允许规则引用 | [广州太古汇口径 §6.4] |
| 组件 ③ | ai_analyzer / ai_gateway / ai_filter | `ai_analyzer.py` + `ai_gateway.py` + `data/ai_filter` (370 条) | ZBC main | P1 / 可退出 + Shadow 对照 | 禁止复制生产配置 / AI 样本允许受控导出 | [AI 架构 §7] |
| 组件 ④ | daily_report / report_engine / weekly_events | `build_daily_report()` 主体过滤 + `data/daily_reports/` (13 份) + weekly_events | ZBC main | P0 / 数据完整性保护 | 禁止复制原始报告 / 汇总统计允许引用 | [日报完整性] |
| 组件 ⑤ | Auth Recovery Center | Auth Recovery 完整闭环（检测→恢复→弹窗→扫码→探活→解熔断） | ZBC main | P0 / 300012 熔断不绕过 | 禁止复制 | [熔断流程 §6.1.3] |
| 组件 ⑥ | 事件关系图谱 (event_mentions) | `event_mentions` 表 (180 条) + 触发/衍生/继发/并行 4 关系 | ZBC main | P1 / 事件关系一致性 | 只读研究使用 | [数据模型 §8.1] |
| 组件 ⑦ | 品牌知识库 | 品牌知识库（影子板块）80 条结构化知识 / 7 大分类 | ZBC main | P1 / 内容一致性校验 | 允许 Evidence 导出 | [v5.9.7 基线 §6] |
| 组件 ⑧ | 案例深度拆解 | 20 个 11 维深度拆解案例 / 58 条方法论 / 77 条系统启示 | ZBC main | P1 / 案例完整性 | 允许 Evidence 导出 | [v5.9.7 基线 §6] |
| 组件 ⑨ | 品牌分析报告生成器 | 6 大维度品牌传播与市场情报报告（从舆情报告升级） | ZBC main | P0（报告交付）/ P1（维度扩展） | 禁止复制客户定制报告 / 模板允许引用 | [报告中心] |

---

## 5. 架构主图与数据流

### 5.1 DCC → Core → CTH → ZBMP 层级架构

```text
                    Development-Command-Console
                              │
                研发审计 / 规划 / 测试 / 受控升级
                              ↓
                        Z-Brand-Core
                              │
                              ↓
                  CTH-POMS 生产 / 客户交付入口
                              │
                  Feature Gate / License / 配置
                              ↓
                 ZBMP Core 内隐藏增强能力层
```

**不是两套并列 Core。** CTH-POMS 优先保证生产稳定；ZBMP 能力以旁路、受控启用的方式逐步进入。

### 5.2 数据主链（10 步流程）

```text
数据源
  ↓
平台 Adapter / 浏览器采集
  ↓
发现 → 详情 → 评论
  ↓
标准化
  ↓
广州太古汇主体过滤 / 品牌监测口径
  ↓
数据质量 → 去重 → 入库
  ↓
系统规则
  ↓
主体 / 内容 / 情绪 / 风险 / 事件
  ↓
Ollama AI 增强（可选、可退出、可审计）
  ↓
事件关系 / 生命周期 / 趋势 / 品牌影响
  ↓
预警 / 看板 / 日历 / 报告 / 决策
```

### 5.3 双向回溯交互流（页面级）

```text
首页
 ↓
事件中心
 ↓
事件详情
 ↓
传播主体
 ↓
主体画像
 ↓
历史内容
 ↓
原始笔记
 ↓
所属事件
```

同时支持 3 条交叉回溯路径：

- 从事件溯源到传播主体
- 从笔记回溯所属事件
- 从主体查看参与过的全部事件

---

## 6. 当前真实版本进度（v5.9.7）

### 6.1 v5.9.7 四大模块 + 分类器 V2 + 基线首批 + E2E

#### 最新 GitHub 版本：v5.9.7

V3.0 能力建设阶段已完成四大模块的后端+前端全链路集成，最新提交包含：

**V3.0 四大模块前端全链路集成（v5.9.6~v5.9.7）**

- 案例深度拆解：20个11维深度拆解案例（品牌营销/危机公关/商业地产/社媒平台/产品化营销），58条可复用方法论，77条系统启示，前端页面+详情弹窗完整集成
- 品牌知识库（影子板块）：80条结构化知识，7大分类（品牌营销/危机公关/品牌案例/广告宣传/消费者行为/舆情管理/传播策略），前端浏览+搜索+分类筛选页面
- 事件关系图谱：营销/传播/舆情三类事件，触发/衍生/继发/并行四种关系，API就绪+前端展示页面（数据待填充）
- 品牌分析报告：从舆情报告升级为品牌传播与市场情报报告，6大维度，前端生成表单+报告展示页面

**传播主体分类器V2（v5.9.5）**

- subject_type与content_type严格分离
- 媒体+官方组合判定为媒体（修复"羊城晚报官方账号"误判问题）
- 6条冲突解决规则，传统媒体关键词置信度0.9
- 12/12测试用例通过

**V3.0基线首批（v5.9.0~v5.9.4）**

- Auth Recovery Center：认证异常检测→恢复任务→前端弹窗→扫码恢复→健康探活→解除熔断 完整闭环
- XHS App Topic Adapter框架预留（Feature Flag控制，默认关闭）
- QR_REQUIRED状态 + CollectionStatus六态
- 隧道守护 + 品牌知识库V1 + 分类器V1
- /remote修复 + 事件关系图谱模块 + 品牌报告升级
- XHS App API可行性研究结论：官方开放平台当前Scope不足，App端数据走Evidence Adapter路线
- 案例深度拆解模块11维框架 + 行业平台配置 + 知识库52条

**端到端测试**

- v5.9.7：42项全部通过（系统基础/核心舆情/案例拆解/知识库/事件图谱/品牌报告/分类器/前端集成/静态资源）
- v5.9.6：33项全部通过
- 主体红线24/24、安全扫描ALL_PASS、API冒烟ALL_PASS

> 上述是提交记录中的测试快照，不替代当前机器的实时 E2E；每次发布仍必须重新验证。

> 上述是提交记录中的测试快照，不替代当前机器的实时 E2E；每次发布仍必须重新验证。

### 6.2 已完成主要演进（v5.7.x → v5.9.0~5.9.7）

#### v5.7.x

- 修复 `app.run` 位置导致后续路由不可达
- 前端 API 接通
- 数据库迁移、日志、配置、监控、CI 骨架
- `collector_v2` 模块化采集器
- 修复同名 endpoint `api_cases_list` 冲突

#### v5.8.2

- 小红书采集六态状态机
- 风控熔断与测试旁路
- 日报数据完整性保护
- Zachary 形象与本地 three.js
- lucide 图标统一
- 缓存戳治理

#### v5.8.3

- 事件关联改走 `event_mentions`
- 负面审核剔除全网案例
- 修复详情 404
- 数据分析死模块修复
- iOS 风格图标
- 横向溢出治理

#### v5.8.4

- 太古集团全域库演进为品牌营销案例库
- 采集器自动化闭环
- `base_dir` 修复
- HTTP → CDP 自动降级
- 热身
- 真实入库后自动关闭浏览器
- 首批详情补抓
- 空表逐张核查

#### v5.8.5

- 太古集团模块 → 品牌营销案例库
- 十五周年模块 → 话题监测端口
- `event_date` 与发现窗口分离
- 报告中心默认最近自然周
- 事件按发生日归属周期
- 正式单测 + 真实网页 E2E

#### v5.8.8

- 版本号统一
- 公网隧道脚本旧路径修复
- 公网上线 `healthz / 401 / 登录页` E2E
- Release Gate V1.0
- 统一认证 Contract
- 移除硬编码凭证
- API / 安全门禁测试

#### v5.8.9

重点完成话题采集链路的多层根因修复，以及风险识别、熔断、恢复和前端状态可视化。

#### v5.9.0 ~ v5.9.7（V3.0 能力建设阶段）

- Auth Recovery Center 认证恢复中心完整闭环
- XHS App Topic Adapter 框架预留（Feature Flag）
- QR_REQUIRED 状态 + CollectionStatus 六态统一
- 品牌知识库（影子板块）：80条知识/7大分类，前端页面集成
- 传播主体分类器V2：subject_type/content_type分离，媒体优先级修复
- 事件关系图谱模块：三类事件+四种关系，API+前端
- 品牌分析报告升级：舆情报告→品牌传播与市场情报报告
- 案例深度拆解：20个11维案例/58方法论/77系统启示，前端全链路
- CHANGELOG补全v5.9.1~v5.9.6
- 版本号统一治理（VERSION/README/Baseline/运行时）

### 6.3 小红书采集稳定优先 + 动态调度

#### 6.3.1 小红书采集：稳定优先

小红书是当前 PRIMARY 平台。目标是：

> **稳定、低风险、可解释、可恢复，而不是高频暴力采集。**

标准链路：

```text
稳定账号 / 合法登录态
 ↓
Persistent Browser Profile
 ↓
Playwright / CDP
 ↓
搜索 / 话题发现
 ↓
详情
 ↓
评论
 ↓
标准化
 ↓
质量检查
 ↓
主体过滤
 ↓
去重
 ↓
入库
 ↓
规则分析 / Ollama 增强
```

##### 采集状态（8 状态枚举）

生产层必须区分，以下枚举值和顺序为硬标准，源码已有六态/更细状态时必须兼容，不得重复制造互相冲突的状态体系：

```text
SUCCESS
NO_NEW_DATA
RISK_WARNING
NEED_VERIFY
BLOCKED
SESSION_EXPIRED
COLLECT_ERROR
COOLING_DOWN
```

**任何失败、验证码、IP 风险、登录失效都不能显示成"0 条"。**

##### Cookie / Session 失效机制（Auth Recovery 流程）

Cookie/session 在任何页面、任何任务、任何时刻失效，都进入**全局 Auth Recovery**，而不是简单跳转登录页。

系统内弹窗至少展示：

- 平台
- 账号
- 当前认证状态
- 失效/验证原因
- 合法二维码或平台正常登录/验证入口（当前流程支持时）
- "我已完成验证"
- "稍后处理"
- 当前暂停、冷却或恢复状态

完成人工合法验证后：

```text
验证完成
 ↓
CDP / Session 健康检查
 ↓
恢复任务
 ↓
小流量试探
 ↓
连续稳定后恢复正常调度
```

不得破解验证码、绕过安全验证或对抗平台风控。

##### 300012 / IP 风险熔断流程

```text
检测
 ↓
停止危险请求
 ↓
记录结构化状态
 ↓
熔断
 ↓
冷却
 ↓
健康检查
 ↓
合法人工验证（需要时）
 ↓
逐步恢复
```

熔断期间应拒绝新的采集启动请求，而不是继续撞平台。

#### 6.3.2 采集频次：动态调度

生产系统不再把历史"固定时间点、30 分钟、20 分钟、自动 9 次 + 手动 3 次"等数字当成永久硬编码。

采用动态调度：

```text
健康
 ↓
正常间隔

轻度风险
 ↓
延长间隔

验证 / 封控
 ↓
停止

冷却完成
 ↓
健康检查

恢复
 ↓
小流量试探

连续稳定
 ↓
逐步恢复
```

历史频次只作为运行经验，不作为绕过平台风控的策略。

### 6.4 广州太古汇业务口径 P0 最高保护

以下内容属于 CTH-POMS 核心业务口径，任何升级不得弱化：

- `SUBJECT_WORDS`（主体词禁止删除，生产业务红线）
- `SUBJECT_EXCLUDE_WORDS`（排除词保护句，严格排除上海、北京、成都、香港等同名场景）
- `subject_hit()`
- `app.py` / `risk_engine.py` 的 `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- 所有 Dashboard、统计、事件、报告和专题数据的主体边界

广州太古汇必须严格排除上海、北京、成都、香港等同名场景。

升级原则：

> **先审计 → 再兼容 → 旁路接入 → 验证 → 切换。**

不得为了新功能删除、放宽或绕过原有主体口径。

---

## 7. AI 架构：Ollama-first / 可退出 / Shadow Mode

### 7.1 正式生产原则

**本地 Ollama 是正式 AI Runtime。**

豆包、OpenAI 或其他云端大模型不得成为生产系统运行的硬依赖。历史外部 AI 代码在确认调用链后标记 Legacy/Optional，再决定清理。

即使所有 AI 都不可用，核心系统仍必须：

```text
采集
 ↓
主体过滤
 ↓
去重
 ↓
事件分析
 ↓
风险判断
 ↓
统计
 ↓
报告
```

正常运行。

### 7.2 AI 可以增强

- 主体身份语义识别
- 内容类型分类
- 情绪解释
- 消费者需求提炼
- 事件聚类建议
- 事件关系建议
- 风险原因解释
- 评论总结
- 趋势解释
- 报告文字生成

### 7.3 AI 不能独自决定

- 原始数据真实性
- 真实发布时间
- 广州太古汇主体最终口径
- 统计数量
- 报告周期
- 核心风险事实

### 7.4 AI 审计链

```text
原始内容
 ↓
系统初判
 ↓
Ollama 输出
 ↓
置信度 / 理由
 ↓
系统校验
 ↓
人工修正（需要时）
 ↓
最终结果
 ↓
Shadow Sample / 规则校准
```

建议记录：

- `model_version`
- `prompt_version`
- 输入摘要
- AI 结果
- 置信度
- 是否采纳
- 人工修正
- 时间

注意：本仓 AI 增强与双子 B 产品的 Zachary 独立 AI 身份严格分离，不共用 AI 决策链路。依据 [ZOSAI IMMUTABLE BASE-001](https://github.com/Zachary-1012/Zachary-OS-AI#1-产品定位)。

---

## 8. 数据模型（WHO × WHAT × 事件 × 品牌影响 × 时间口径）

### 8.1 基础数据关系 + 主体六维画像 + 内容类型 + 三类事件 + 事件关系 4 种 + 生命周期 + 因果链

#### 基础数据关系

```text
客户
├─ 品牌（自有 / 竞品）
│  ├─ 监测配置
│  ├─ 传播主体库
│  ├─ 内容库
│  └─ 事件库
└─ 项目 / Campaign
```

#### 传播主体六维画像

1. **身份**：KOS / KOL / KOC / 普通用户 / 媒体 / 官方 / 机构（共 7 项硬枚举）
2. **内容能力**：发文量、发布频率、爆款率、内容类型、垂直领域
3. **传播能力**：平均互动、互动率、传播速度、事件峰值贡献、扩散贡献度
4. **品牌关系**：官方 / 员工 / 合作 / 消费者 / 竞品 / 第三方
5. **舆情表现**：正负向、中性、风险等级、长期态度倾向
6. **事件贡献**：参与事件、贡献度、影响力权重

#### 内容类型（5+ 硬枚举）

内容字段与主体身份独立：

- `content_type=UGC`
- `content_type=COMMERCIAL`
- `content_type=OFFICIAL`
- `content_type=REVIEW`
- 体验、投诉、活动等可继续扩展

#### 三类事件

- **营销事件**：品牌主动发起，例如周年庆、联名、快闪、Campaign。
- **传播事件**：市场/用户自发形成的热点。
- **舆情事件**：公众态度聚集，可正向也可负向。

#### 事件关系（4 种）

事件不应成为孤立列表，通过 `event_relation` 表达：

- 触发
- 衍生
- 继发
- 并行

#### 生命周期（8 步）

`发现 → 形成 → 增长 → 爆发 → 扩散 → 分化 → 衰减 → 结束`

#### 营销→传播→舆情因果链

```text
营销事件
   ↓
传播事件
   ↓
舆情事件
   ↓
品牌影响
```

### 8.2 时间与数据质量

#### 两字段时间口径（严格分离）

- `publish_datetime`：内容实际发布时间。报告、日历和周期统计原则上按此字段。
- `captured_at`：系统采集时间。

相对时间如"小时前""编辑于"等必须在采集解析层可靠归一化；无法可靠归一化时标记不确定状态，**不能拿采集时间冒充发布时间**。

#### 12 项数据质量字段

数据质量至少关注：

- 平台原始 ID
- 标题 / 正文
- 作者
- 发布时间
- 原始链接
- 详情状态
- 评论状态
- 采集错误
- 风控/验证状态
- 主体归属
- 重复状态
- 部分采集状态

### 8.3 品牌传播平台页面映射（17 页映射表 + 双向回溯）

尽量复用 CTH-POMS 现有侧边栏，不新增大量顶级菜单。

| 现有页面（序号） | 现有页面名 | 扩展方向 |
|---|---|---|
| 1 | 首页概览 | 营销/传播/舆情三类事件、主体分布、内容类型分布 |
| 2 | 舆情监测 | 主体类型 + 内容类型双筛选 |
| 3 | 风险预警 | 风险事件、主体贡献、传播升温 |
| 4 | 事件中心 | 三类事件 Tab、生命周期、关系图谱、参与主体、关联内容 |
| 5 | 负面确认 | 标记所属事件并支持营销动作溯源 |
| 6 | 热门话题 | 话题关联事件、主体分布、内容类型 |
| 7 | 话题监测端口 | 主体类型过滤、专题内容库、风控状态 |
| 8 | 笔记搜索 | 主体类型 + 内容类型高级搜索 |
| 9 | 数据分析 | 传播主体、消费者需求、品牌对标 |
| 10 | 品牌业态 | 品牌/业态信息与传播主体体系连接 |
| 11 | 官方动态 | 官方账号纳入 `subject_type=OFFICIAL` |
| 12 | 品牌营销案例库 | 关联营销事件、主体、内容类型 |
| 13 | 案例库 | 案例 → 事件 → 主体 → 内容回溯 |
| 14 | 舆情日历 | 按发生日展示三类事件 |
| 15 | 报告中心 | 综合传播、主体分析、因果溯源报告 |
| 16 | 系统设置 | 客户隔离、主体识别规则、事件聚类规则、标签阈值 |
| 17 | Zachary 智能助手 | AI 辅助查询 / 报告生成入口（Shadow Mode） |

#### 双向回溯交互流

```text
首页
 ↓
事件中心
 ↓
事件详情
 ↓
传播主体
 ↓
主体画像
 ↓
历史内容
 ↓
原始笔记
 ↓
所属事件
```

交叉回溯路径（3 条）：

- 从事件溯源到传播主体
- 从笔记回溯所属事件
- 从主体查看参与过的全部事件

---

## 9. 允许 / 禁止 / 受控 四层矩阵 + 资产清单

### 9.1 产品层矩阵（A 侧 8 行）

| # | 行为 | 分类 | 依据标签 |
|---|---|---|---|
| A-1 | CTH-POMS 生产运行不依赖 Zachary-OS-AI 组件 | ✅ 必须（硬约束） | [AGENTS §2] 一套Core隔离 |
| A-2 | ZBMP 能力通过 Feature Gate 渐进启用，不制造第二套 Core | ✅ 必须 | [§5 架构] 不是两套并列 Core |
| A-3 | 主体口径（SUBJECT_WORDS / EXCLUDE）升级前先审计兼容 | ✅ 必须 | [§6.4] 广州太古汇P0保护 |
| A-4 | 采集 8 状态枚举与现有状态机兼容，不制造冲突体系 | ✅ 必须 | [§6.3.1] 采集状态标准 |
| A-5 | 云端大模型（豆包/OpenAI等）成为生产硬依赖 | ❌ 禁止 | [§7.1] Ollama-first |
| A-6 | 破解验证码 / 绕过安全验证 / 对抗平台风控 | ❌ 禁止 | [§6.3.1] Auth Recovery原则 |
| A-7 | 新平台 Adapter 未经完整验证接管生产任务 | ❌ 禁止 | [§3 CTH-POMS] 主平台小红书 |
| A-8 | AI 能力进入生产前必须经过 Shadow Mode 对照 + 人工批准 | ⚠️ 受控 | [§7 AI 审计链] |

### 9.2 仓库层矩阵（ZBC 仓库层 12 行）

| # | 行为 | 分类 | 依据标签 |
|---|---|---|---|
| R-1 | 删除或放宽 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS 主体词保护 | ❌ 禁止 | [§6.4] P0最高保护 |
| R-2 | 绕过主体过滤 / 风险规则 / 事件聚合逻辑 | ❌ 禁止 | [§6.4] 7条保护项 |
| R-3 | 未备份删除生产数据库 / 清空生产表 / 重建覆盖 | ❌ 禁止 | [§12.3 数据安全] |
| R-4 | Cookie / Token / API Key / Secret 写入源码或日志或前端 | ❌ 禁止 | [§12.3 数据安全] [§12.4 门禁第14条] |
| R-5 | 生产数据库因远端更新被自动覆盖 | ❌ 禁止 | [§12.2 公网部署] |
| R-6 | 采集失败显示为"0 条"（伪装成功） | ❌ 禁止 | [§6.3.1] 采集状态约束 |
| R-7 | 熔断期间继续启动新采集请求撞平台 | ❌ 禁止 | [§6.3.1 300012熔断] |
| R-8 | 改动前不读取最新 HEAD / 不审计影响范围就施工 | ❌ 禁止 | [§12.4 门禁第1-2条] |
| R-9 | 真实 E2E 未完成就写"已完成" | ❌ 禁止 | [§12.4 门禁第8条+结束语] |
| R-10 | 每次发布后重新运行 E2E 验证（提交快照≠实时事实） | ✅ 必须 | [§6.1 E2E 说明] |
| R-11 | 数据库迁移：向后兼容 + 先备份 + 保留回滚路径 | ✅ 必须 | [§12.3 数据安全] |
| R-12 | 新能力优先旁路接入，不覆盖稳定主链 | ✅ 必须 | [§12.5 协作规则 第6条] |

### 9.3 组件层权限矩阵

组件层 9 项组件（collector 系列 / risk_engine / ai_analyzer-ai_gateway-ai_filter / daily_report-report_engine-weekly_events / Auth Recovery Center / event_mentions / 品牌知识库 / 案例深度拆解 / 品牌分析报告生成器）的**允许 / 禁止 / 受控**与**跨仓使用权限**，详见 §4 组件 Owner 表中「跨仓使用权限」列与「变更门槛」列。此处不重复枚举。

### 9.4 研发流程层矩阵（9 行）

| # | 行为 | 分类 | 依据标签 |
|---|---|---|---|
| D-1 | 改动前全量读取 README/AGENTS/BASELINE/CHANGELOG/HEAD + 源码 | ✅ 必须 | [§12.5 协作第1-3条] |
| D-2 | 未审计影响范围、未跑测试就写代码提交 | ❌ 禁止 | [§12.4 门禁第2-4条] |
| D-3 | 改完后跑匹配测试（单测+Smoke+E2E+口径回归） | ✅ 必须 | [§12.4 门禁第4-13条] |
| D-4 | 只说"完成"不附 10 要素证据 / 未完成项 / 回滚方式 | ❌ 禁止 | [§12.4 门禁第16条] |
| D-5 | 删除/伪造测试用例伪装测试通过 | ❌ 禁止 | [§12.5 协作 第8-9条] |
| D-6 | 3-way 验证（源码/DB/运行时）不通过就晋级版本或发 Release | ❌ 禁止 | [§12.6 权威性优先级链] |
| D-7 | 并发 push 前重读 HEAD 重新计划，避免覆盖 | ✅ 必须 | [§12.4 门禁第1条+第17条] |
| D-8 | 同时改动 ZBC（A 仓）源码与 Zachary-OS-AI（B 仓）源码 | ⚠️ 受控 | [§2 双子关系] 两仓生产隔离 |
| D-9 | 把聊天记录 / AI 输出 / 口头承诺当代码事实 | ❌ 禁止 | [§12.6 权威性 聊天仅提供背景] |

### 9.5 本仓资产清单（8 大类 × 6 字段）

| 类别 | 路径 | 数量估 | Owner | 是否备份 | 允许进 Git |
|---|---|---|---|---|---|
| 源码主模块 | `app.py`（264KB，主入口）、`routes/` 蓝图目录、`collector_v2/`、`risk_engine.py`、`ai_analyzer.py`、前端 `templates/` + `static/`（含 lucide、three.js、screenshots）、蓝图 modules | ≈ 21,656 源码文件 / ≈ 8150 MB 总工作区 | ZBC main 团队 | 是（Git + 异地） | 是 |
| 数据库 | `data/monitor.db`（生产库）、schema_version v8、`migrations/` 迁移脚本目录 | 1 主库 + 多张业务表（667 笔记 / 151 事件 / 7135 审核 / 178 采集日志 / 370 ai_filter / 180 event_mentions） | ZBC main 团队 | 是（自动备份 + 人工快照） | 条件：migrations 脚本是；monitor.db 原始文件否 |
| 数据资产 | `data/collection_logs/` (178 份采集日志)、`data/ai_filter/` (370 条过滤规则)、`data/note_review_history/` (7135 条审核记录)、`data/daily_reports/` (13 份日报)、`data/event_mentions/` (180 条)、`data/backups/` (备份归档) | 上述 + weekly_events / 原始采集 / 脱敏数据 / AI 样本 | ZBC main 团队 | 是（backups 目录归档） | 条件：结构化汇总样例是；原始客户数据否 |
| 文档 | README × 5（含本文件）+ `AGENTS.md` + `ARCHITECTURE.md` + `PROJECT_STATUS.md` + `CHANGELOG.md` + `DEPLOYMENT.md` + `RELEASE_POLICY.md` + `DOUBAO_*`（约 12 份） + `docs/` 子目录 | ≈ 12+ 份核心文档 | ZBC main + DCC | 是（Git 版本化） | 是 |
| 测试 | `tests/`（~55+ pytest 单测）、`test_e2e/`（42 E2E 用例，42/42 通过）、`ci_cd/`、安全扫描脚本 | ≈ 55+ 单测 + 42 E2E + CI 配置 | ZBC main 团队 | 是（Git 版本化） | 是 |
| 子模块 | `tools/development-command-console`（Git Submodule，pinned SHA） | 1 个子仓；升级流程：①读 pinned SHA ②DCC 侧审计 ③SHA 变更 PR ④Diff 验证 ⑤本仓回归 ⑥人工批准 ⑦更新 pinned SHA | DCC 独立 Owner | 是（通过 pinned SHA 追溯） | 是（仅 `.gitmodules` + pinned SHA，不展开源码） |
| 凭证配置 | `.env.example`（模板，可入）、`.env`（真实环境变量）、`data/private/system_config`（敏感系统配置）、生产凭据 | 模板 1 份 + 私有 N 份 | ZBC main 运维 | 是（加密离线备份） | 条件：仅 `.env.example` 模板是；真实 .env / private/ 否 |
| 静态媒体 | `templates/` 内静态资源、`static/`（lucide 图标 / three.js 3D 模型 / Zachary 形象 / screenshots 截图）、大文件 | 含 >10MB 大文件时外部化处理 | ZBC main 团队 | 是 | 条件：<10MB 是；>10MB 外部化（LFS 或对象存储） |

---

## 10. 当前优先级：P0 / P1 / P2

### P0：CTH-POMS 稳定上线

- 启动入口与依赖统一
- 小红书采集稳定性
- Auth Recovery
- 300012 / IP 风控熔断与冷却
- 主体/时间/风险/事件/报告口径回归
- 数据备份与恢复
- HTTPS / 反向代理或 Cloudflare Tunnel
- API / 页面 / E2E 验收
- 生产部署验收

### P1：ZBMP 能力完善

- 客户 / 品牌 / 竞品 / 项目
- 传播主体六维画像
- 内容类型
- 三类事件
- `event_relation`
- 生命周期
- 消费者需求
- 品牌对标
- 多平台 Adapter
- Ollama Shadow / 样本 / 评测

### P1/P2：DCC（四库：ZBC+SICI+DCC+AI-DRH）

继续完善：

- GitHub 只读审计
- Local AI Bridge
- Evidence
- 权限矩阵
- 受控补丁
- 隔离分支
- 测试
- Diff 审计
- 人工批准
- PR / Release 验收

### P2：持续优化

- 手机端完整设置体验
- 全站版本/命名/注释统一
- `collector_v2` 与现网采集器并行验证后再切换
- 临时诊断脚本清理
- guardian / recovery / data feedback 逐项验证后启用
- CI/CD、监控大盘
- `app.py` 中期蓝图化
- 事件因果溯源与图谱可视化

### 当前已知待办（9 条）

> 以下不是"全部已完成"，而是当前工程路线上的真实待办，具体状态以最新源码和运行时为准。

- 生产启动环境统一，避免全局 Python 与 `.venv` 依赖不一致。
- 历史空正文在稳定网络下合法分批补抓；触发验证时走 Auth Recovery。
- 采集解析层持续治理相对时间与异常时间。
- `swire_notes` / `topic_campaign_notes` 等扩展库继续真实采集跑数。
- `system_guardian` / `auto_recovery` / `data_feedback_loop` 逐项验证后启用。
- 微博/B站等辅助源先验证，再决定是否进入生产。
- 微信通知在凭证配置后进行真实测试。
- 品牌传播平台 Phase 1 → Phase 2 → Phase 3 逐步接入。
- Ollama Shadow Mode 与 AI 样本回流持续建设。

---

## 11. 关键文档与跨仓索引

### 11.1 本仓关键文档（11 份）

- `AGENTS.md`：AI/Codex/协作者施工规则
- `AI_POLICY.md`：AI 使用与退出原则
- `ARCHITECTURE.md`：架构说明
- `CURRENT_BASELINE.md`：当前协作基线
- `PROJECT_STATUS.md`：项目状态
- `CHANGELOG.md`：版本变更记录
- `DEV_LOG.md`：开发日志
- `DEPLOYMENT.md`：部署说明
- `RELEASE_POLICY.md`：发布策略
- `DOUBAO_GITHUB_UPGRADE_PROTOCOL.md`：豆包 GitHub 升级协议
- `docs/RELEASE_GATE_AND_DOUBAO_2200.md`：22:00 豆包施工门禁与上线 Gate

### 11.2 跨仓索引（3 条，E-009 三元元信息 + last_verified_sha）

1. 🤖 [Zachary-OS-AI README 双子关系段](https://github.com/Zachary-1012/Zachary-OS-AI#双子产品关系) (repo=Zachary-1012/Zachary-OS-AI, branch=main, section=双子产品关系, last_verified_sha=f0b8bb5)
2. 📘 [DCC README §17 与 Z-Brand-Core 的 13 项职责](https://github.com/Zachary-1012/Development-Command-Console#17-与-z-brand-core-的关系) (repo=Zachary-1012/Development-Command-Console, branch=main, section=§17, last_verified_sha=f0b8bb5)
3. 🔧 [AI-DRH Capability Registry](https://github.com/Zachary-1012/AI-Development-Research-Hub/blob/main/CAPABILITY-REGISTRY.md) (repo=Zachary-1012/AI-Development-Research-Hub, branch=main, section=Capability Registry, last_verified_sha=f0b8bb5)

> 说明：last_verified_sha 指 ZOSAI 仓（B 仓）当前本地 HEAD，因为三链接目标 GitHub 仓内容在本地都以 ZOSAI components/ 快照形式同步验证过。A 仓当前 HEAD = `b497277`（本仓自证）。

---

## 12. 协作规则、变更门禁与权威性

### 12.1 内置 Web / 浏览器 / 研发学习方向

平台长期能力包括：

- 内置 Web 信息检索：外部资料研究与事实核验
- 浏览器能力：合法浏览、采集、E2E 与状态检查
- GitHub：源码、版本、Diff、测试、Release 审计
- 本地 Ollama：本地 AI 分析与研发辅助
- AI Shadow：AI 与系统原判断对照
- Evidence：研发过程证据链
- 多平台 Adapter：统一采集接口

这些能力应当服务于**研发、审计、分析和合法数据采集**，不得用于绕过平台安全机制。

### 12.2 公网部署原则

系统可以通过公网提供访问，但生产边界必须安全：

```text
公网 HTTPS
 ↓
反向代理 / Cloudflare Tunnel
 ↓
认证层
 ↓
Web
 ↓
Worker / Scheduler
 ↓
数据库 / 本地 AI
```

部署边界：

- 不裸暴露 `8200`
- HTTPS 优先
- Cookie / Token / Secret 不进入 GitHub
- 生产数据库不得因远端更新被自动覆盖
- Web 与后台任务逐步解耦
- 公网发布前必须完成 Health Check、认证、关键页面和 API E2E

### 12.3 数据安全

以下均属于数据资产：

- `.db / .sqlite / .sqlite3`
- ORM Model
- migration
- seed
- backup
- 导入/导出数据
- 原始采集数据
- 脱敏数据
- AI 样本

**禁止行为**：

- 未授权删除生产数据库
- 清空生产表
- 重建生产表覆盖数据
- 将 Cookie / Token / API Key / Secret 写入源码
- 将敏感凭证写入日志、前端或测试样例

数据库新增字段/表优先采用向后兼容迁移；任何迁移先备份并保留回滚路径。

### 12.4 开发与发布门禁（17 条 + 流程图）

一次升级只有同时满足以下 17 条条件才可称为完成：

1. 读取最新 GitHub HEAD。
2. 先审计影响范围，再施工。
3. 代码语法/导入检查通过。
4. 相关单测通过。
5. 数据库迁移检查通过。
6. 生产数据没有被删除或覆盖。
7. 蓝图 / API Smoke Test 通过。
8. 关键页面 E2E 通过。
9. 控制台 JS 错误扫描通过。
10. 主体口径回归通过。
11. 时间口径回归通过。
12. 采集异常状态可解释。
13. 新 Adapter 未误接管生产。
14. 无敏感凭据进入 Git。
15. 更新 CHANGELOG / PROJECT_STATUS / DEV_LOG。
16. 提供未完成项与回滚方式。
17. 完成后重新读取 HEAD 做二次核验。

标准流程：

```text
最新源码
 ↓
主基线
 ↓
影响范围分析
 ↓
最小补丁
 ↓
单测
 ↓
Smoke / E2E
 ↓
安全检查
 ↓
提交
 ↓
重新读取 HEAD
 ↓
发布结论
```

**真实 E2E 未完成，不得写"已完成"。**

### 12.5 协作规则（12 条 + 一句话工程原则）

所有协作者，包括人工、豆包、本地 Ollama、DCC 及其他开发窗口，都必须：

1. 先读 README、AGENTS.md、CURRENT_BASELINE.md、PROJECT_STATUS.md、CHANGELOG.md 和相关架构文档。
2. 先确认最新 HEAD。
3. 不凭印象修改。
4. 不推倒重构。
5. 不覆盖稳定主链。
6. 新能力优先旁路。
7. 修改后必须测试。
8. 测试结果必须如实记录。
9. 不得以"AI 判断"代替系统事实。
10. 不得把采集失败伪装成 0 条。
11. 不得绕过平台安全机制。
12. 不得提交敏感凭证。

#### 一句话工程原则

> **稳定版本是底座，系统内循环是核心，AI 是增强层，GitHub 是协作事实源，所有升级都必须可验证、可回滚、可追溯。**

### 12.6 权威性冲突处理优先级链

如果聊天记录、旧方案、AI 输出、历史 README 与当前源码产生冲突，采用：

```text
当前源码 / 数据库 / 运行时实测
        >
MASTER_DEVELOPMENT_BASELINE.md
        >
CURRENT_BASELINE.md
        >
最新开发记录
        >
历史文档
        >
旧聊天结论
```

聊天记录负责提供**需求和决策背景**，不能替代代码事实。

### 12.7 Repository

**Z-Brand-Core：品牌传播与市场情报智能平台核心底座**

主线：`main`

当前生产优先：**CTH-POMS**

母平台增强：**ZBMP**

研发中枢（Git Submodule）：**Development-Command-Console**
