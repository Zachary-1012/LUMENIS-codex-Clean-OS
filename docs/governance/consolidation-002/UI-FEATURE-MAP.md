# UI-FEATURE-MAP · UI 功能地图（Consolidation-002 / ⑥，不含视觉）

> 本图只定「产品→业务域→功能→页面→状态→交互→组件」，**不做视觉施工**（视觉=⑨，一次性做）。
> 现状页面以 `v4_upgrade/*/templates` + `static/index.html`(SPA) + `templates/`(旧SSR) 为准；未开发功能占位，避免后续改导航。
> 视觉方向已锁（⑨执行，本轮不写样式）：侘寂黑白灰为底 + 极少量语义色 + 小状态点 + Token 化 + 低装饰 + 高信息密度 + 强层级 + 精准交互；参考 GPT/Codex 工程产品语言。交互动效参考以屏幕录制 004120 为定死基准（见 docs/reference/ui-research）。

## 1. 目标信息架构（IA，ZBMP 增强层 + CTH 共用一套导航）

```
Workspace 工作区
└─ Brand 品牌（当前品牌切换，不做多租户隔离）
   └─ Project 项目
      └─ Campaign 活动（含 15 周年专题）
         ├─ Monitoring 监测（采集/健康/调度）
         ├─ Content 内容（笔记/评论/导入）
         ├─ Events 事件（列表/图谱/负面评审）
         ├─ Insights 洞察（风险/主体/竞品/传播情报）
         ├─ Reports 报告（日/周/月/专题/导出）
         ├─ AI / Evaluation（Zachary 抽屉/评测，增强层）
         └─ Settings 设置（账号/采集/版本中心/系统）
```
导航四要素：当前在哪 / 下一步能做什么 / 数据属于谁 / 当前状态是什么。禁止同功能多入口、隐藏关键操作、页面间乱跳。

## 2. 页面 → Feature 映射（现状 + 目标状态）

| 页面（现状文件） | IA 归属 | 承载 Feature | 现状状态 | 关键交互（⑥定，⑨实现） |
|---|---|---|---|---|
| 总控 console | Monitoring/总览 | MON-003/004,SYS-001,AI-001 | ACTIVE | 健康小点→点即开对应 Auth Modal（不跳页）；Summary+Status+Recent+Action，不堆 KPI |
| 采集 collect | Monitoring | MON-001/002/005,COLL-001~004 | ACTIVE | 手动采集 Idle/Loading/Success/Error；异常显真实状态非0条；平台独立卡片 |
| 笔记 notes | Content | NOTE-001/002,SUBJ | ACTIVE（SPA+旧SSR并存待收敛） | Toolbar/Search/Filter/Sort/列表/分页；详情 Drawer 不跳离 |
| 事件 events | Events | EVT-001/002/003,RISK | ACTIVE | 列表→详情(Header/Timeline/Relations/Evidence)；状态文字+小点+Icon |
| 报告 report | Reports | RPT-001/002 | ACTIVE | 周期切换/导出二次确认/异步进度 |
| 品牌/案例 brand,cases | Insights | BRAND-001/002/003 | ACTIVE/DEVELOPING | 品牌增删、案例下钻事件库（再添加更新待补） |
| AI 抽屉（全局） | AI/Evaluation | AI-001/002 | ACTIVE/PLANNED | 区分 AI建议/系统事实/人工判断；保留 Model/Prompt/Confidence/Human Override |
| 设置 settings | Settings | AUTH-002,SETT-001,IMP-001 | ACTIVE | 分组苹果风；危险操作二次确认；不可用项 Disabled+原因 |
| 版本中心 version-center | Settings | SYS-002 | ACTIVE（标题bug待修） | 立即保存/检查更新/历史/回滚；同步状态小点 |
| 全局 Auth Modal | 横切 | AUTH-001 | DEVELOPING（主SPA未挂） | 任意页失效弹同一 Modal：平台/账号/状态/原因/二维码/已验证/稍后/恢复态 |
| Workspace/Project/Campaign 层级页 | 顶层 | WS-001 | PLANNED（占位，导航预留） | 面包屑表达数据归属 |
| 外部导入页 | Content | IMP-001 | PLANNED（仅后端3py，无前端） | 拖拽导入/解析进度/错误清单 |

## 3. 统一组件清单（⑨一套复用，禁止每页重造）

Button · IconButton · Input · Select · Search · Tabs · Badge · **StatusDot（●语义小状态点）** · Table · Drawer · Modal · Toast · EmptyState · Loading · ErrorState · Timeline · Metric · Panel · Toolbar · Pagination · ConfirmDialog · SegmentedControl · Breadcrumb · HealthBadge。
现状：`static/css/zb-theme.css` v2.0（609行）已有 Design Token 雏形；index.html 仍引 17 个 CSS link（历史层叠，⑨收敛为单一 token 主题层，旧 CSS 先标 ACTIVE/DUPLICATE/UNUSED，回归后删）。

## 4. 交互状态契约（所有可交互元素必须覆盖）

- 异步：Idle → Loading → Success / Error（错误给原因与下一步，不用空态掩盖）。
- 危险：Confirm → Executing → Result；不可逆二次确认。
- 不可用：Disabled + Reason（tooltip/行内说明）。
- 反馈：点击必有即时视觉/文字反馈；颜色不是唯一状态表达（必须同时有文字/Icon）。
- 状态点语义：●green 健康 · ●amber 告警/降级 · ●red 危险/熔断 · ●blue 信息/进行 · ●gray 未启用。

## 5. 响应式断点矩阵（⑨/E2E 逐格验收，移动端不是缩小桌面）

| 断点 | 390 | 430 | 768 | 1024 | 1280 | 1440 |
|---|---|---|---|---|---|---|
| 导航 | 底部 Tab + Drawer | 底部 Tab | 侧栏可折叠 | 侧栏 | 侧栏 | 侧栏 |
| 表格 | 卡片化/横向滚动 | 同 | 紧凑表 | 全表 | 全表 | 全表+密度档 |
| 弹窗 | bottom sheet | bottom sheet | 居中 Modal | Modal | Modal | Modal |
| 必查 | 导航/表格/弹窗/抽屉/Toolbar/图表/文本/按钮/Overflow/横向滚动 | | | | | |

已知待修（用户实测反馈，⑨一并解决）：手机端与网页端均存在**显示不全/内容裁切**，需在 390/430/1440 实测修复，禁止只在单宽度自测。

## 6. 页面数量与层级原则

- 尽量单页承载（列表+筛选+详情 Drawer），其余按层级跳转，最深不超过 IA 树层级；面包屑恒定。
- 首页只保留 Summary+Status+Recent Activity+Quick Action，不堆 20 个 KPI 卡；详情页不无限套 Card。

## 7. 素材与研究（已隔离，供⑨，不在本轮施工）

- `docs/reference/ui-research/source-videos/`（7 录屏，Git LFS）、`reference-images/`（14 图）、`VIDEO-SOURCE-MANIFEST.md`、`ref_gpt_v2/frames/`（353 抽帧）。
- 004120 定死为交互&动效参考基准之一；Word《z-Brand Core UI视觉&交互逻辑1.0》为需求参考；全网/GitHub 设计与动效实现研究结论在⑨开工前补入本目录。
