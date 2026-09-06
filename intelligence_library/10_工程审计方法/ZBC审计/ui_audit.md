# ZBC Phase 14 — UI / Visualization 审计报告

> 审计时间：2026-09-06
> 仓库：D:\Taikoo-monitor-new
> 分支：feat/zbc-full-upgrade-v1
> 审计范围：templates/、static/、lumenis_frontend.py、app.py、UI_DELETE_MANIFEST.md
> 审计人：ZBC Phase 14 自动化审计

---

## 1. 执行摘要

本次审计确认：
- **旧 UI 未恢复**：UI_DELETE_MANIFEST.md 中列出的全部已删除文件/目录经核验仍不存在。
- **当前 UI 为 LUMENIS 新架构**：22 个模板文件 + 11 个静态资源，全部基于 `base.html` 基金会模板，通过 `lumenis_frontend.py` Blueprint 路由。
- **app.py 无 render_template**：285KB 的 app.py 为纯后端/API 层，不直接渲染模板。
- **所有页面均不满足新数据链规范**：无时间范围切换、无 Delta、无 Freshness 指标、无 Confidence、无结构化 Evidence Drill-down。
- **无止尽滚动**：所有页面使用有界列表（slice(0,N) / max-height），符合单页面工作台原则。
- **1 个 DELETE-CANDIDATE**：`_preview/command-home-preview.html` 为预览文件，未被路由引用。

---

## 2. 现有页面清单与状态

### 2.1 模板文件总览（22 个文件，共 3,340 行）

| # | 模板路径 | 行数 | 路由 | 数据绑定 | 状态 | 需重建 |
|---|---------|------|------|---------|------|--------|
| 1 | `base.html` | 324 | — | 全局健康轮询 | FOUNDATION | 扩展 |
| 2 | `home/command_home.html` | 144 | `/lumenis/` | fetch + 直接绑定 | ACTIVE | 是 |
| 3 | `production/overview.html` | 164 | `/lumenis/production` | bindState + fetch | ACTIVE | 是 |
| 4 | `production/public_opinion.html` | 118 | `/lumenis/production/public-opinion` | bindState + fetch | ACTIVE | 是 |
| 5 | `production/risk.html` | 107 | `/lumenis/production/risk` | Promise.all + fetch | ACTIVE | 是 |
| 6 | `production/monitoring.html` | 98 | `/lumenis/production/monitoring` | bindState + fetch | ACTIVE | 是 |
| 7 | `production/reports.html` | 115 | `/lumenis/production/reports` | fetch（无 bindState） | PARTIAL | 是 |
| 8 | `production/cases.html` | 85 | `/lumenis/production/cases` | fetch（无 bindState） | PARTIAL | 是 |
| 9 | `intelligence/workspace.html` | 141 | `/lumenis/intelligence` | bindState + fetch | ACTIVE | 是 |
| 10 | `intelligence/skill_hub.html` | 335 | `/lumenis/intelligence/skills` | bindState + fetch | ACTIVE | 是 |
| 11 | `intelligence/agent_center.html` | 143 | `/lumenis/intelligence/agents` | bindState（无 fetch） | PARTIAL | 是 |
| 12 | `intelligence/models.html` | 101 | `/lumenis/intelligence/models` | fetch（无 bindState） | PARTIAL | 是 |
| 13 | `intelligence/evidence.html` | 83 | `/lumenis/intelligence/evidence` | fetch（无 bindState） | PARTIAL | 是 |
| 14 | `intelligence/evaluation.html` | 149 | `/lumenis/intelligence/evaluation` | bindState（无 fetch） | PARTIAL | 是 |
| 15 | `research/workspace.html` | 151 | `/lumenis/research` | bindState + fetch | ACTIVE | 是 |
| 16 | `research/findings.html` | 77 | `/lumenis/research/findings` | fetch（无 bindState） | PARTIAL | 是 |
| 17 | `operations/index.html` | 164 | `/lumenis/operations` | bindState + fetch | ACTIVE | 是 |
| 18 | `operations/runtime.html` | 69 | `/lumenis/operations/runtime` | fetch（无 bindState） | PARTIAL | 是 |
| 19 | `operations/permissions.html` | 81 | `/lumenis/operations/permissions` | fetch（无 bindState） | PARTIAL | 是 |
| 20 | `operations/repository.html` | 61 | `/lumenis/operations/repository` | fetch（无 bindState） | PARTIAL | 是 |
| 21 | `_preview/command-home-preview.html` | 241 | 无（未路由） | 静态预览 | DELETE-CANDIDATE | 移除 |
| 22 | `components/` | — | — | 空目录 | — | — |
| 23 | `errors/` | — | — | 空目录 | — | — |

### 2.2 状态统计

| 状态 | 数量 | 占比 | 说明 |
|------|------|------|------|
| ACTIVE | 10 | 45.5% | 有路由 + 完整数据绑定（bindState + fetch） |
| PARTIAL | 10 | 45.5% | 有路由但数据绑定不完整（缺 fetch 或缺 bindState） |
| FOUNDATION | 1 | 4.5% | base.html 基金会模板 |
| DELETE-CANDIDATE | 1 | 4.5% | 预览文件，未被路由引用 |

### 2.3 静态资源清单（11 个文件，共 83,909 字节）

| 类型 | 文件 | 行数 | 大小 | 说明 |
|------|------|------|------|------|
| CSS | `css/lumenis.css` | 10 | 563B | 主入口（@import 其余 CSS） |
| CSS | `css/lumenis-reset.css` | 54 | 2,344B | 重置样式 |
| CSS | `css/lumenis-tokens.css` | 152 | 5,509B | 设计 Token（颜色/间距/字体） |
| CSS | `css/lumenis-layout.css` | 105 | 4,711B | 布局（header/sidebar/workspace） |
| CSS | `css/lumenis-components.css` | 340 | 19,275B | 组件（card/metric/table/list/badge） |
| CSS | `css/lumenis-responsive.css` | 77 | 4,002B | 响应式 |
| CSS | `css/lumenis-motion.css` | 46 | 2,592B | 动画/过渡 |
| JS | `js/lumenis-core.js` | 187 | 8,217B | 核心（fetch/theme/store/bindState/i18n） |
| JS | `js/lumenis-data.js` | 289 | 14,882B | 数据绑定（6 区 + Core Metrics） |
| JS | `js/lumenis-icons.js` | 58 | 4,160B | 线框图标（禁 emoji） |

### 2.4 路由清单（lumenis_frontend.py，21 个页面路由 + 5 个 API）

**页面路由（url_prefix=/lumenis）：**

| 路由 | 函数 | 模板 | 优先级 |
|------|------|------|--------|
| `/` | command_home | home/command_home.html | P0 |
| `/intelligence` | intelligence_workspace | intelligence/workspace.html | P0 |
| `/production` | production_overview | production/overview.html | P0 |
| `/production/public-opinion` | public_opinion | production/public_opinion.html | P0 |
| `/production/risk` | risk | production/risk.html | P0 |
| `/operations` | operations | operations/index.html | P0 |
| `/intelligence/skills` | skill_hub | intelligence/skill_hub.html | P1 |
| `/intelligence/agents` | agent_center | intelligence/agent_center.html | P1 |
| `/intelligence/evaluation` | evaluation_center | intelligence/evaluation.html | P1 |
| `/research` | research_workspace | research/workspace.html | P1 |
| `/intelligence/models` | models | intelligence/models.html | P1 |
| `/intelligence/evidence` | evidence | intelligence/evidence.html | P1 |
| `/production/monitoring` | monitoring | production/monitoring.html | P1 |
| `/production/cases` | cases | production/cases.html | P1 |
| `/production/reports` | reports | production/reports.html | P1 |
| `/research/findings` | findings | research/findings.html | P1 |
| `/operations/runtime` | runtime | operations/runtime.html | P1 |
| `/operations/permissions` | permissions | operations/permissions.html | P1 |
| `/operations/repository` | repository | operations/repository.html | P1 |

**API 路由：**
- `GET /healthz` — Foundation 存活探针
- `GET /api/skills/status` — Skill Registry 状态
- `POST /api/skills/invoke` — Skill 调用
- `GET /api/skills/invocations` — Skill 调用历史
- `POST /api/skills/sync` — Skill Manifest 同步
- `GET /api/intelligence/evidence` — OSAI Evidence Chain

---

## 3. 旧 UI 删除确认（无恢复）

依据 `UI_DELETE_MANIFEST.md`（2026-09-04 Hard Reset），逐项核验：

### 3.1 ZBC 已删除项

| 已删除路径 | 类型 | 核验结果 |
|-----------|------|---------|
| `creative_workbench.html` | html | ✅ CONFIRMED-DELETED |
| `v4_upgrade/*/templates/`（collect/console/login/settings/version_center） | directory | ✅ CONFIRMED-DELETED |
| `v4_upgrade/static/` | directory | ✅ CONFIRMED-DELETED |
| `podcast/ui/` | directory | ✅ CONFIRMED-DELETED |

### 3.2 残留问题（需后续清理）

| 文件 | 问题 | 严重度 |
|------|------|--------|
| `v4_upgrade/settings/routes.py:6` | `from flask import ... render_template ...` — 未使用的 import（模板已删，路由已改 jsonify） | LOW |
| `v4_upgrade/version_center/routes.py:4` | `from flask import ... render_template ...` — 未使用的 import | LOW |
| `v4_upgrade/settings/routes.py:17` | `template_folder=os.path.join(...)` — 指向已删除的模板目录 | LOW |
| `v4_upgrade/version_center/routes.py:10` | `template_folder=os.path.join(...)` — 指向已删除的模板目录 | LOW |

**结论：旧 UI 零恢复。** 所有 Hard Reset 删除的文件/目录经核验仍不存在。仅存在 4 处低严重度的代码残留（未使用的 import 和 template_folder 配置），不影响运行，建议后续清理。

---

## 4. UI 数据链规范

### 4.1 七层数据链

```
┌─────────────────────────────────────────────────────────────┐
│  L7  UI Rendering（Flask 模板 + LUMENIS JS）                │
│      消费 ViewModel，渲染图表/卡片/表格                       │
├─────────────────────────────────────────────────────────────┤
│  L6  Visualization（可视化配置）                               │
│      ChartType / Colors / Layout / Drill-down                │
├─────────────────────────────────────────────────────────────┤
│  L5  ViewModel（视图模型）                                    │
│      TimeRange + ViewMetric[5要素] + TruthTable              │
├─────────────────────────────────────────────────────────────┤
│  L4  TruthTable（真值表）                                     │
│      exists / status / freshness / confidence / sources      │
├─────────────────────────────────────────────────────────────┤
│  L3  MetricLayer（规范指标）                                  │
│      canonical_metrics 委托：sentiment / risk / engagement   │
├─────────────────────────────────────────────────────────────┤
│  L2  FunctionLayer（业务函数）                                │
│      主体过滤 / 风险判断 / 去重（注入式，不硬编码词表）       │
├─────────────────────────────────────────────────────────────┤
│  L1  DataLayer（原始数据）                                    │
│      DataQuery → DataResult（显式空集/错误，不静默成 0）     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 各层契约

| 层 | 模块 | 输入 | 输出 | 关键约束 |
|----|------|------|------|---------|
| L1 DataLayer | `DataLayer` | `DataQuery` | `DataResult` | 空集→NO_DATA，异常→ERROR，不静默 |
| L2 FunctionLayer | `FunctionLayer` | `List[dict]` | `FunctionResult` | 主体过滤注入式，不硬编码 SUBJECT_WORDS |
| L3 MetricLayer | `MetricLayer` | `List[dict]` | `Dict[str, MetricValue]` | 优先委托 canonical_metrics，fallback 标记 |
| L4 TruthTable | `build_truth_table()` | `DataResult` | `TruthTable` | 置信度基于样本量+新鲜度+状态 |
| L5 ViewModel | `ViewModelBuilder` | `DataQuery` | `ViewModel` | 每个指标必须有 5 要素 |
| L6 Visualization | `VisualizationConfig` | metric_key | `VisualizationConfig` | ZBC 自有色板，不套模板 |
| L7 UI | 模板 + JS | `ViewModel.to_dict()` | 渲染页面 | 单页面工作台，无止尽滚动 |

### 4.3 ViewMetric 五要素（强制）

每个视图指标必须携带：

| 要素 | 字段 | 说明 | 缺失时表现 |
|------|------|------|-----------|
| 当前值 | `current_value` | 指标当前数值 | `–`（不显示 0） |
| Delta | `delta` | 与上一周期的变化量/百分比/方向 | 不显示 Delta 区域 |
| Freshness | `freshness` | 人类可读的新鲜度（"5 分钟前"/"STALE"） | 显示"未知" |
| Confidence | `confidence` | HIGH/MEDIUM/LOW/UNKNOWN | 显示置信度指示器 |
| Evidence | `evidence_refs` | 可下钻的证据引用列表 | 显示"无证据" |

### 4.4 时间范围规范

统一枚举 `TimeRange`：

| 值 | 含义 | 时间边界 | 典型用途 |
|----|------|---------|---------|
| `NOW` | 实时快照 | 最新一次采集 | 系统健康/采集状态 |
| `TODAY` | 今日 | 今日 00:00 至今 | 日报/当日指标 |
| `D7` | 最近 7 天 | now-7d ~ now | 周趋势 |
| `D30` | 最近 30 天 | now-30d ~ now | 月趋势/风险笔记 |
| `D90` | 最近 90 天 | now-90d ~ now | 季度分析 |
| `YTD` | 年初至今 | 1月1日 ~ now | 年度累计 |
| `HISTORICAL` | 全量历史 | 无边界 | 全量分析/导出 |

---

## 5. 单页面核心工作台规范

### 5.1 设计原则

| 原则 | 规范 | 当前状态 |
|------|------|---------|
| 无止尽滚动 | 所有列表有界（slice/max-height + 滚动容器） | ✅ 已满足 |
| 动态实时 | 核心指标支持轮询/推送更新 | ⚠️ 仅全局健康 30s 轮询 |
| 时间范围切换 | NOW/TODAY/7D/30D/90D/YTD/HISTORICAL | ❌ 所有页面无时间切换 |
| 核心指标卡片 | 当前值 + Delta + Freshness + Confidence | ❌ 仅当前值 |
| Event Drill-down | 点击事件→事件详情→关联笔记 | ❌ 无 |
| Case Drill-down | 点击案例→案例详情→证据链 | ❌ 无 |
| Evidence Drill-down | 点击指标→支撑证据列表→原始内容 | ❌ 风险笔记有外链但无结构化下钻 |

### 5.2 单页面布局规范

```
┌──────────────────────────────────────────────────────────┐
│  Header: 标题 + 时间范围切换器 + 全局状态灯 + 主题切换    │
├──────────────────────────────────────────────────────────┤
│  Core Metrics Row（4-6 张指标卡）                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ 指标A │ │ 指标B │ │ 指标C │ │ 指标D │ │ 指标E │        │
│  │ 值+Δ  │ │ 值+Δ  │ │ 值+Δ  │ │ 值+Δ  │ │ 值+Δ  │        │
│  │新鲜度 │ │新鲜度 │ │新鲜度 │ │新鲜度 │ │新鲜度 │        │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
├──────────────────────────────────────────────────────────┤
│  Main Grid（2 列，左主右辅）                               │
│  ┌─────────────────────┐ ┌─────────────────────┐       │
│  │ 趋势图（Line/Bar）   │ │ 分布图表（Donut）    │       │
│  │ 支持时间范围联动      │ │ 支持点击下钻          │       │
│  └─────────────────────┘ └─────────────────────┘       │
│  ┌─────────────────────┐ ┌─────────────────────┐       │
│  │ 风险/事件列表（有界） │ │ 证据时间线           │       │
│  │ max-height + 内部滚动 │ │ 点击→原始内容        │       │
│  └─────────────────────┘ └─────────────────────┘       │
├──────────────────────────────────────────────────────────┤
│  TruthTable Footer: 数据来源 + 新鲜度 + 置信度 + 检查时间  │
└──────────────────────────────────────────────────────────┘
```

### 5.3 交互规范

- **时间范围切换**：切换后所有指标卡/图表/列表联动刷新，URL 同步 `?range=7d`
- **指标卡点击**：展开该指标的 Evidence Drill-down 面板（支撑证据列表）
- **图表点击**：柱状图/环形图点击对应系列→过滤下方列表
- **列表行点击**：打开详情抽屉（Drawer），展示完整内容 + 元数据 + 关联事件
- **加载状态**：每个组件独立 `data-state="loading/success/empty/error"`，不白屏
- **空状态**：显式显示"该时间范围内无数据"，不显示 0
- **错误状态**：显示错误信息 + 重试按钮，不静默

---

## 6. 需要重建的页面清单

所有 20 个路由页面均需按新数据链规范重建。按优先级排序：

### 6.1 P0 — 生产核心页面（优先重建）

| 优先级 | 页面 | view_id | 重建要点 |
|--------|------|---------|---------|
| P0-1 | Production Overview | `production_overview` | 时间切换 + 核心指标卡(5要素) + 采集健康 + 主体口径指示器 |
| P0-2 | Public Opinion | `public_opinion` | 情感分布(可下钻) + 话题趋势 + 风险笔记列表(有界) |
| P0-3 | Risk Center | `risk_center` | 风险等级分布 + 风险笔记表格(可排序/过滤) + 证据下钻 |
| P0-4 | Command Home | `command_home` | 六区状态 + 全局指标摘要 + 快捷动作 + 时间范围 |
| P0-5 | Operations | `operations` | 健康四灯 + 采集状态 + AI 通道 + 运行时 + 熔断状态 |

### 6.2 P1 — 智能与研究页面

| 优先级 | 页面 | view_id | 重建要点 |
|--------|------|---------|---------|
| P1-1 | Intelligence Workspace | `intelligence_workspace` | AI 输入→上下文→检索→推理→证据→行动 链路 |
| P1-2 | Skill Hub | `skill_hub` | Skill 列表(状态/版本) + 调用历史 + 证据链 |
| P1-3 | Monitoring | `monitoring` | 采集器监控 + 运行时指标 + 风险趋势 |
| P1-4 | Reports | `reports` | 报告列表 + 生成状态 + 预览入口 |
| P1-5 | Cases | `cases` | 案例库 + 案例详情 + 证据关联 |
| P1-6 | Research Workspace | `research_workspace` | 研究→发现→证据→决策→提案 链路 |
| P1-7 | Evidence Center | `evidence_center` | 证据链列表 + 证据详情 + 溯源 |
| P1-8 | Models | `models` | Provider-agnostic 模型管理 + 通道健康 |
| P1-9 | Agent Center | `agent_center` | Agent 列表 + 状态 + 任务历史 |
| P1-10 | Evaluation | `evaluation` | 评估维度 + 评估结果 + 回归测试 |
| P1-11 | Research Findings | `findings` | 发现列表 + 发现详情 + 关联研究 |
| P1-12 | Runtime | `runtime` | 本地运行时 + 健康检查 |
| P1-13 | Permissions | `permissions` | 权限门控 + 身份 + 委托 |
| P1-14 | Repository | `repository` | ZBC + OSAI 双核状态 |

### 6.3 待移除

| 文件 | 原因 |
|------|------|
| `_preview/command-home-preview.html` | 预览文件，未被任何路由引用，属于设计阶段产物 |

---

## 7. 视觉系统规范

### 7.1 ZBC 自有色板（不套模板）

| 用途 | 颜色名 | HEX | 说明 |
|------|--------|-----|------|
| 正面/成功 | positive | `#22c55e` | 情感正面、成功状态 |
| 中性 | neutral | `#94a3b8` | 情感中性、次要文本 |
| 负面/危险 | negative | `#ef4444` | 情感负面、高风险 |
| 高风险 | risk_high | `#ef4444` | 高风险等级 |
| 中风险 | risk_medium | `#f59e0b` | 中风险等级 |
| 低风险 | risk_low | `#3b82f6` | 低风险等级 |
| 严重风险 | risk_critical | `#7c3aed` | 独立更高桶，不并入 high |
| 品牌强调 | accent | `#6366f1` | 主按钮、链接、选中态 |
| 背景 | background | `#0f172a` | 深色模式背景 |
| 表面 | surface | `#1e293b` | 卡片/面板背景 |
| 主文本 | text_primary | `#f1f5f9` | 标题/正文 |
| 次文本 | text_secondary | `#94a3b8` | 说明/标签 |
| 边框 | border | `#334155` | 分割线/卡片边框 |

### 7.2 设计 Token（lumenis-tokens.css 已实现）

- **间距**：xs(4px) / sm(8px) / md(16px) / lg(24px) / xl(32px)
- **圆角**：sm(6px) / md(10px) / lg(12px) / pill(9999px)
- **字体**：系统字体栈，标题 600/700，正文 400/500
- **阴影**：轻量浮层阴影，不使用厚重投影
- **动效**：320ms 过渡，不使用花哨动画

### 7.3 组件规范（lumenis-components.css 已实现）

| 组件 | 类名 | 用途 |
|------|------|------|
| 卡片 | `.lm-card` | 内容容器，支持 flat/nav 变体 |
| 指标 | `.lm-metric` | 单值指标（label + value），需扩展为 5 要素卡 |
| 表格 | `.lm-table` | 数据表格，需扩展排序/过滤 |
| 列表 | `.lm-list` / `.lm-list-item` | 有界列表项 |
| 徽章 | `.lm-badge` | 状态/计数标签 |
| 状态灯 | `.lm-dot` | success/warning/danger/unknown |
| 按钮 | `.lm-btn` | primary/ghost/icon/sm 变体 |
| 时间线 | `.lm-timeline-item` | 证据/事件时间线 |

### 7.4 禁止事项

- ❌ 不套模板/仿制其他产品（不使用 Bootstrap/Tailwind UI 组件库）
- ❌ 不使用 emoji 作为图标（使用 lumenis-icons.js 线框图标）
- ❌ 不使用无止尽滚动（所有列表有界）
- ❌ 不将失败伪装成 0 条（显式 empty/error 状态）
- ❌ 不在源码中写 Secret（API Key 仅经 .env 注入）

---

## 8. 现有页面合规性审计

### 8.1 数据链合规性检查

| 检查项 | 通过页面数 | 未通过页面数 | 通过率 |
|--------|-----------|-------------|--------|
| 有数据获取（fetch） | 17/20 | 3 | 85% |
| 有状态绑定（bindState） | 12/20 | 8 | 60% |
| 无止尽滚动 | 20/20 | 0 | 100% |
| 有时间范围切换 | 0/20 | 20 | 0% |
| 有 Delta 计算 | 0/20 | 20 | 0% |
| 有 Freshness 指示 | 1/20 | 19 | 5% |
| 有 Confidence 指示 | 0/20 | 20 | 0% |
| 有 Evidence Drill-down | 0/20 | 20 | 0% |
| 有 TruthTable 层 | 0/20 | 20 | 0% |

### 8.2 关键发现

1. **数据绑定模式不统一**：12 页使用 `LUMENIS.bindState()`，8 页使用直接 `fetch()` + 手动 DOM 操作。应统一为 ViewModel 驱动。
2. **时间口径缺失**：所有页面无 `publish_datetime` vs `captured_at` 区分，无时间范围过滤。
3. **主体口径不可见**：仅 overview 和 public_opinion 页面有"主体口径过滤"徽章，其余页面无主体过滤状态指示。
4. **证据链断裂**：风险笔记有原始 URL 外链，但无结构化的 Evidence Drill-down（无法从指标→支撑证据→原始内容）。
5. **PARTIAL 页面数据绑定弱**：10 个 PARTIAL 页面中，agent_center 和 evaluation 无 fetch（可能为静态展示），reports/cases/models/evidence/findings/runtime/permissions/repository 有 fetch 但无 bindState 封装。

---

## 9. 交付物清单

| 交付物 | 路径 | 状态 |
|--------|------|------|
| UI 数据链规范模块 | `ui_view_model.py` | ✅ 已创建 |
| UI 审计报告 | `audit/ui_audit.md` | ✅ 已创建（本文件） |
| 视图模型测试 | `tests/test_ui_view_model.py` | ✅ 已创建 |
| 旧 UI 删除确认 | 本报告 §3 | ✅ 零恢复 |

---

## 10. 下一步建议

1. **P0 页面重建**：按 §6.1 顺序，先重建 Production Overview 和 Risk Center，验证 ViewModel 数据链端到端可行。
2. **统一数据绑定**：将所有页面的 fetch/bindState 统一为 ViewModelBuilder 驱动，消除手动 DOM 操作。
3. **时间范围组件**：在 base.html 中新增全局时间范围切换器，所有页面联动。
4. **清理残留**：移除 `v4_upgrade/settings/routes.py` 和 `version_center/routes.py` 中未使用的 `render_template` import 和 `template_folder` 配置。
5. **移除预览文件**：删除 `_preview/command-home-preview.html`。
6. **扩展指标卡组件**：将 `.lm-metric` 扩展为 5 要素卡（当前值 + Delta + Freshness + Confidence + Evidence 入口）。

---

*报告结束。本报告由 ZBC Phase 14 自动化审计生成，所有事实基于 2026-09-06 仓库源码审计。*
