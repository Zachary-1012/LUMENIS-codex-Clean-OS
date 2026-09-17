# 序境 / LUMENIS
# Skill 信息源接入与无 Cookie 采集桥接契约 V1

> 状态：研究结论已冻结，桥接实现按本契约增量执行。  
> 目的：把外部 Skill 的“信息源接入方法”纳入序境，而不是把外部仓库源码复制进生产核心。  
> 产品边界：CTH、BMP、Shared Capability、SYSTEM；不产生第四条产品线。

## 0. 本轮事实基线

| 对象 | 真实证据 | 当前结论 |
| --- | --- | --- |
| `Zachary-Skill` | `https://github.com/Zachary-1012/Zachary-Skill`，`main@487b3d6da41181b892772f638a6c267204a8626e` | 已读取并完成构建、测试、MCP smoke；不是序境生产 Truth Owner |
| TrendHub 覆盖 | `src/sources/index.ts`、`src/sources/domestic.ts`、`src/sources/international.ts` | 38 个平台/趋势信源目录；公共端点、RSS、聚合源和国际公开端点的组合 |
| TrendHub 工具 | `src/tools/definitions.ts`、`manifest.json` | 19 个 MCP 工具；工具返回结构化情报/分析脚手架，不替代序境事实库 |
| TrendHub 默认范围 | `src/tools/definitions.ts:22,38-40` | 当前是 10 个“核心平台”默认值，不等于全部 38 个；序境不能照搬该默认值 |
| TrendHub 源失败 | `src/sources/index.ts:68-114` | 逐源隔离、回退或返回 `missing/degraded`；不能把 CI PASS 当成所有源在线 |
| TrendHub 本地状态 | `src/store/history.ts`、`src/store/reliability.ts`、`src/store/snapshot.ts` | 快照、有限历史、可靠性在本地保存；写入失败不应伪造成功 |
| 序境公共源 | `platform_adapters/web_rss.py:17-113` | 已存在无 Cookie、无 Key 的 Google News RSS 适配器，状态会显式返回 |
| 序境平台入口 | `v4_upgrade/adapters/registry.py:35-76` | `platforms=None` 时遍历全部已注册平台，并逐平台返回状态 |
| 序境 Skill 预检 | `skill_package_runtime.py:110-462` | 支持来源识别、manifest 校验、精确 Git revision；当前不等于已安装/已执行 |
| 序境 Skill 登记 | `account/skills.py:128-217` | 通过验证的本地/ZIP/SKILL.md 只能登记为 `disabled + not_installed` |
| MCP 当前边界 | `skill_package_runtime.py:401-409`、`tests/test_skill_package_runtime.py:226-236` | MCP 仍需 discovery、权限审批、隔离自测；不得伪造已接入 |

本文件不改变以上事实，也不把“覆盖目录”“代码存在”“构建通过”改写成“平台实时可用”。

### 0.1 专业产品能力基准（研究后转译为序境约束）

本轮对 Brandwatch Consumer Intelligence、Sprinklr Listening/Insights、Meltwater
Media Intelligence 的公开产品资料做了能力级对照；只提炼产品机制，不复制界面、代码或供应商实现。
共同的专业基线不是“接入越多越好”，而是：

| 能力基线 | 序境转译 | 事实边界 |
| --- | --- | --- |
| 多源统一观察 | Source Catalog → Adapter → Evidence → Canonical | 不允许各业务域私建采集真相 |
| 信号可靠性与缺失可见 | source status、quality、latency、failure class、history sufficiency | 缺失不等于 0；AI 不补事实 |
| 观察到行动 | Event → Case → Risk → Decision → Action → Outcome → Evaluation | 外部写动作始终经过人工审批/Effect Fence |
| 内容工作流 | Evidence/Trend → Brief → Content Candidate → Review | 内容草案不等于已发布内容 |
| 组织化工作 | CTH/BMP/Shared 共用事实链，按领域显示不同 View Model | 不产生第四产品线 |
| AI 接入可控 | Skill/MCP 是受控能力源，Permission/Trace/Evaluation/Audit 独立存在 | Skill/MCP 不拥有 Production Truth |

研究依据：

- Brandwatch Consumer Intelligence / Suite：<https://www.brandwatch.com/suite/>。
- Sprinklr Social Listening：<https://www.sprinklr.com/help/articles/what-is-social-listening/transform-extensive-data-into-actionable-insights-with-social-listening/63f76dece02459133724ae4a>。
- Meltwater Media Intelligence：<https://www.meltwater.com/en>。
- Agent Skills specification：<https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx>。
- MCP Tools / Resources / Transports：<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>、<https://modelcontextprotocol.io/specification/2025-11-25/server/resources>、<https://modelcontextprotocol.io/specification/2025-11-25/basic/transports>。

## 1. 研究结论：真正要学习的不是“免 Cookie 爬取”

`Zachary-Skill` 的可复用方法是五个层次的组合：

```text
可登记的信息源目录
    ↓
按来源类型选择公共 Adapter（API / RSS / HTML / 国际公开端点）
    ↓
统一结构化结果 + dataQuality + note
    ↓
本地快照 / 有界历史 / Source Reliability
    ↓
MCP tools / 内容简报 / 趋势分析
```

它并没有证明“任意网站都可以无条件读取”。严格的产品化表述应为：

> 序境允许接入任意**被登记、被允许、可验证、可追溯**的信息源；其中公共信息源可以在无 Cookie、无平台账号、无第三方 Key 的模式下运行。需要登录、Session、签名或浏览器的源，才进入授权运行模式。任何源不可用时，保留失败事实，不用 AI 或默认值补齐。

这同时满足“平台可扩展”和“Production Truth 不被污染”。

## 2. 六个领域的能力细化

### 2.1 信息源目录领域：Source Catalog

| 项目 | 契约 |
| --- | --- |
| Name | `source_id`、展示名、平台/媒体/仓库类别 |
| Owner | SYSTEM 管理目录；CTH 使用采集结果；BMP/Shared 不能私建源目录 |
| Input | `source_id`、source type、endpoint/template、query、平台范围、Subject Context |
| Output | `SourceAttempt`：source、provider、endpoint 摘要、captured_at、质量、耗时、失败分类、revision/digest（如有） |
| Database | 运行元数据进入既有 `web_runs/web_sources`；业务事实先进入 Evidence，再进入 Canonical Data；不增加 Vendor 专属事实表 |
| API | 复用既有 Adapter / `secondary_collection`；Skill/MCP 通过受控桥接调用，不直连 DB |
| Frontend | CTH 的信息源选择与状态；设置中的 Skill 来源管理；BMP 只显示已经进入 Canonical 的市场视图 |
| Permission | `network` + `specific_domains`；Cookie/Session 是可选 `browser/session` 权限，默认不授予 |
| Test | 公开源无凭证运行、超时、空结果、非 JSON、源失效、来源污染、秘密不回显 |

来源类型必须显式区分：

```text
public_api_json   = 公开 JSON/API，不需要账号
rss_atom          = RSS/Atom 订阅，来源 URL 可追溯
public_html       = 公开页面解析，只读、限速、选择器可版本化
repository        = GitHub/代码仓库只读信息源，使用 allowlist + revision
authorized_session= 合法授权 Session/Browser Worker，独立状态机
optional_vendor   = 可替换供应商，Key 为空时不得阻塞公共源
```

### 2.2 平台适配领域：Platform Adapter

平台不是 Provider，Provider 也不是产品线。统一关系：

```text
LUMENIS
  → PlatformAdapter
      → Provider（public / session / optional vendor）
```

每个平台必须逐项声明并实现/返回状态：

```text
search / detail / comments / author / author_posts / healthcheck
```

“未实现”“未配置”“需要登录”“源暂时失败”分别使用不同状态，不得折叠为 0 条数据。

手动采集与自动采集使用同一 `CollectionRequest` 和同一 Adapter：

```text
manual  → 人工触发 → Adapter → Evidence
scheduled → 调度器 → 同一 Adapter → Evidence
```

两者的差异仅在触发者、调度策略和权限，不得复制两套采集实现。无平台选择时，序境选择全部已注册平台；每个平台仍独立返回 `SUCCESS / EMPTY / AUTH_REQUIRED / BLOCKED / PROVIDER_UNAVAILABLE / ...`。

### 2.3 无 Cookie 公共信息源领域：Public Source Mode

无 Cookie 模式的最小链路：

```text
Source Catalog
  → public endpoint / RSS / public page
  → timeout + retry + rate limit
  → schema validation
  → normalized item
  → source provenance
  → Evidence
```

强制规则：

1. 不读取、不注入、不猜测 Cookie；
2. 不把 HTTP 200 当成业务成功，必须验证响应类型、字段和条目数；
3. 不把缺少互动字段的 RSS 记录补成 0；缺失值保持 `null/UNKNOWN`；
4. 每次尝试记录 `source/provider/collected_at/data_quality/failure_class`；
5. 单一源失败只能影响本源，不得拖垮其他平台；
6. 公共源不能绕过平台政策、访问控制或 robots/服务条款边界；
7. 公开源是默认可选路径，Session/浏览器不是默认前置条件。

RSS/Atom 统一以订阅 URL、条目 GUID/link、发布时间和源名称组成最小证据；原文内容是否读取，由来源允许范围和当前能力契约决定。

### 2.4 Skill 包与安装领域：Skill Lifecycle

Skill 包只是可验证能力包，不直接成为生产源。生命周期固定为：

```text
SOURCE
 → DISCOVER
 → DETECT
 → PARSE
 → VALIDATE
 → COMPATIBILITY
 → SECURITY
 → PERMISSION_PREVIEW
 → DEPENDENCY_RESOLUTION
 → QUARANTINE_INSTALL
 → BUILD
 → SELFTEST
 → HEALTHCHECK
 → REGISTER
 → ENABLE
 → AVAILABLE
```

每一阶段必须有独立状态和证据。当前序境已落地的是来源识别、manifest/SKILL.md 校验、Git revision 解析和禁用登记；远程下载、隔离安装、MCP capability discovery、工具 schema 审查、真实执行仍不能标记为完成。

标准 `SKILL.md` 只描述能力与使用说明；脚本、依赖、网络和外部动作必须经过序境自己的权限与隔离门。Skill 的说明文字不能授权它访问 Cookie、数据库或外部写操作。

### 2.5 MCP 工具领域：MCP Transport / Tool Surface

MCP 是传输和工具协议，不是产品线、不是权限系统、不是 Skill Registry。接入时必须分开：

```text
MCP Client
  → discovery（tools/list / resources/list）
  → schema / annotation review
  → allowlist + permission
  → isolated call
  → output validation
  → Evidence / Trace / Evaluation
```

对 `Zachary-Skill` 的实际映射：

| TrendHub 工具族 | 序境归属 | 是否产生 CTH 事实 |
| --- | --- | --- |
| `list_platforms`、`list_categories` | SYSTEM / Shared source discovery | 否，只有目录元数据 |
| `get_trending`、`xhs_hot_topics` | CTH 采集候选 / Shared trend intelligence | 需重新写入序境 Evidence 才能成为事实 |
| `source_reliability`、`trend_change_alerts` | SYSTEM / Shared evaluation | 否，属于源质量和分析结果 |
| `analyze_topic`、`trend_intelligence`、`benchmark_trend_lead` | Shared / AI Enhancement | 否，AI/规则不能覆盖 Production Truth |
| `list_templates`、`get_template`、`get_content_brief` | Shared Content Creation | 产出草案/简报，必须经过事实与人工审核 |
| `take_snapshot` | Skill 本地状态 | 不直接写序境数据库，需通过受控 Evidence bridge |

序境不得让 MCP 工具直达：Collector Session、Cookie、CDP、raw DB、发布接口或隐藏的业务规则。

### 2.6 Evidence / Canonical / UI 领域

所有来源最后必须进入同一条真相链：

```text
External Data
  → SourceAttempt
  → Evidence(source/provider/collected_at/quality)
  → Canonical Data（只做确定性归一化）
  → CTH/BMP/Shared View Model
  → UI / Report
```

AI 可以做摘要、分类、主题提取、创作简报和候选解释，但不得覆盖：

```text
original fact / subject ownership / metric definition / risk boundary / decision authority
```

UI 必须显示真实状态：`OK / DEGRADED / MISSING / AUTH_REQUIRED / NOT_CONFIGURED / UNKNOWN`，不能把 Skill 返回的示例、模板或历史快照渲染成当前业务数据。

## 3. 序境产品线映射

| 产品线 | 可以消费什么 | 不能拥有什么 |
| --- | --- | --- |
| CTH｜商业运营 | 平台采集、Evidence、事件、Case、Risk、Decision、Action、公共源与授权源状态 | 不把 Skill 结果直接当 Production Truth；不把 Vendor 写进业务契约 |
| BMP｜品牌市场 | Brand/Campaign/Content/KOS/KOL/KOC/Audience/Evaluation，以及 CTH 已验证的市场证据 | 不建立第二采集器、第二 Evidence、第二 Canonical Truth |
| Shared Capability | Trend Intelligence、Content Creation、Evaluation、Learning Asset、AI Enhancement、Skill 工具 | 不拥有主体事实、平台会话、业务规则、发布权 |
| SYSTEM | Source Catalog、Skill Registry、MCP discovery、Runtime、Permission、Audit、Settings | 不把 MCP/Skill 变成第四产品线 |

## 4. 平台覆盖的正确状态模型

“什么平台都可以”在工程上拆成三层，而不是一个布尔值：

| 层 | 含义 | 例子 |
| --- | --- | --- |
| Capability catalog | 产品允许登记和选择的平台/信源 | 小红书、抖音、B站、微博、知乎、Instagram、RSS、未来新增平台 |
| Adapter capability | 该平台的 search/detail/comments/author/... 真实实现情况 | `implemented / not_supported` |
| Runtime readiness | 当前源是否可用、是否需要授权、是否被策略禁用 | `SUCCESS / NEED_VERIFY / AUTH_REQUIRED / NOT_CONFIGURED / DOWN` |

当前小红书香港账号是 Runtime evidence，不是产品 capability 的上限。大陆/其他平台的运行策略可以暂时关闭，但关闭只改变 Runtime readiness，不删除平台目录、Adapter 契约或未来扩展位。

## 5. 研究后的执行顺序

### P0：Source Contract 收敛

- 将公共源、RSS、公开页面、仓库源、授权 Session、Optional Vendor 统一为来源类型；
- 保留现有 Adapter、Evidence、Canonical、`web_runs/web_sources`；
- 将默认无平台选择定义为全部已注册能力，并保留逐平台失败状态；
- 先实现无 Cookie 公共源验收，再处理需要 Session 的平台；
- 测试：无凭证启动、公共 RSS 真实/模拟源、空结果、超时、schema 错误、单源故障隔离。

### P1：Skill / MCP Bridge

- 复用现有 `skill_package_runtime` 和 `skills_registry`，不建第二注册表；
- 补齐远程 Skill 的 pinned revision → manifest discovery → quarantine install → isolated build/selftest；
- MCP 使用 stdio / Streamable HTTP 的正式 Client；
- 对 `tools/list`、`resources/list`、tool schema、annotations、output schema 做验证；
- 所有调用通过既有 Permission → Firewall → Effect Fence → Evidence → Evaluation → Trace；
- `Zachary-Skill` 首个接入对象定位为 Shared 的 Trend Intelligence / Content Brief Provider，不能直接写 CTH/BMP Truth。

### P2：产品应用闭环

- CTH：信息源选择、手动采集、自动采集、源可靠性、Evidence 链路和事实状态；
- BMP：消费同一条市场证据，按 Brand/Campaign/Content/KOS/Audience/Evaluation 展示；
- Shared：将 TrendHub 的简报、模板、趋势和未来信号接入内容制作流；
- SYSTEM：Skill/MCP 来源安装、权限、健康、禁用、版本、审计和失败恢复；
- UI：不另起普通 SaaS 页面，使用序境主界面与两业务领域的层级；动态只服务于趋势、风险、事件、证据和行动反馈。

## 6. 本轮验收结果与未完成项

已验证：

```text
Zachary-Skill main revision = 487b3d6da41181b892772f638a6c267204a8626e
TrendHub build/test/smoke = PASS
TrendHub MCP tools = 19
序境 Skill/secondary collection focused tests = 35 passed
GitHub revision resolution = PASS
当前序境 HEAD = 19c50b2b765ae8ca1df2334304050d1bb5c1f2b5
当前序境与 origin/main = 0 0
```

仍未标记完成：

```text
Zachary-Skill 已作为外部 Skill 进入序境生产执行链
远程 Skill 隔离安装与依赖缓存
MCP tools/list 与 tools/call 的序境正式 Client
38 个 TrendHub 源全部实时在线
其他平台的真实运行状态全部通过
CTH/BMP UI 已完成该桥接后的真实页面验收
```

## 7. 研究依据

- `Zachary-Skill`：<https://github.com/Zachary-1012/Zachary-Skill>（本轮锁定 `main@487b3d6`）
- Agent Skills specification：<https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx>
- MCP Tools specification：<https://modelcontextprotocol.io/specification/2025-11-25/server/tools>
- MCP Resources specification：<https://modelcontextprotocol.io/specification/2025-11-25/server/resources>
- MCP Transports specification：<https://modelcontextprotocol.io/specification/2025-11-25/basic/transports>
- RSS 2.0 specification：<https://www.rssboard.org/rss-specification>

以上研究只提炼协议和架构方法，不复制外部仓库实现，不把外部研究或 Skill 输出升级为序境生产事实。
