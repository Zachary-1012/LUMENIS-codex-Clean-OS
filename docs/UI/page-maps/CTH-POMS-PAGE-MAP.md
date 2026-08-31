# CTH-POMS Page Map（广州太古汇舆情监测系统 · 页面地图）

> v1.0 2026-08-31，配套 ZBIP-DESIGN-SYSTEM / COMPONENT-SYSTEM / FEATURE-FINAL-VERIFICATION-MATRIX。定位：**舆情风险驾驶舱**（实时·风险·事件·报告）。布局型：Dashboard。每条含 目标/用户/数据/组件/交互/状态/权限。Feature 状态以验证矩阵为准，未完成项在 IA 中占位不删除。

## 全局框架（所有页共用）
- Sidebar 导航：总览 / 监测采集 / 事件 / 笔记库 / 报告 / Zachary AI / 品牌库(ZBMP) / 系统。Topbar：面包屑 + ⌘K + 全局状态中心（各平台 StatusDot，点击直接开对应 AuthRecoveryModal）+ AI + 账号。
- 全局浮层：AuthRecoveryModal、AIChatDrawer、Toast、CommandMenu。权限角色：Guest（只看公开概览）/ Member（看+常规操作）/ Admin（配置/评审/导出）/ Owner（密钥/版本/账号/高危）。

## P1 总览 Console `/v4/console`（首页，单页）
- 目标：一屏回答「监测是否健康 / 有无新风险 / 今天发生什么 / 下一步做什么」。
- 用户：Member+。数据：notes/events/collection_logs/schedule_decisions/event_graph 计数与时间线。
- 组件：Metric×≤7（克制）、StatusCenter 平台小点、风险 Timeline、调度影子卡（只读，门控前）、15 周年专题卡、快捷操作 Toolbar。
- 交互：点状态点→AuthModal；点指标→抽屉下钻（不跳页）；手动采集/生成报告走确认；时间窗 Segmented。
- 状态：平台八态语义点；无新数据=unknown「暂无新数据」非 0 条；熔断=danger 显示冷却。
- 权限：Member 看，Admin 触发操作。关联 Feature：MON-001/002/003/004、EVT-002、RISK、SYS-001。

## P2 监测采集 `/v4/collect`
- 目标：按平台管理采集任务、看清“为什么这轮没采”。
- 用户：Member 看 / Admin 配置。数据：collection_logs、schedule_decisions、xhs_circuit、cookies(json)、proxy。
- 组件：平台分组 ListRow（小红书 PRIMARY / 抖音·IG·Google 占位灰点 / 未来平台 RESERVED）、任务表（keyword/status/items/started/finished/next_run/decision）、调度策略抽屉、Cookie 保险库状态（脱敏）、代理池健康。
- 交互：启停单次任务（自动/手动时长为历史参考非硬编码）；查看某关键词 scheduler_decision；失效就地弹 AuthModal；不跨平台连坐（小红书熔断不影响其它平台行）。
- 状态：SUCCESS/NO_NEW_DATA/RISK_WARNING/NEED_VERIFY/BLOCKED/AUTH_FAILED/NETWORK_ERROR/COOLING_DOWN 八态 + resume 时间；300012/IP 风险=danger 熔断冷却，不重试不绕验证。
- 权限：Admin 改策略，Owner 管 Cookie/代理。关联：MON-001/003/004/005、COLL-001..004、NOTE-002（占位）。

## P3 事件中心 `/v4/events`
- 目标：事件聚合、关系演进、负面评审闭环。
- 组件：Toolbar（类型/严重度/状态/时间筛选）+ 事件 Table + 关系图 RelationGraph 抽屉 + 评审 Drawer。
- 交互：行点击开详情抽屉（Header/状态/摘要/时间线/关系/Evidence/操作）；评审通过/驳回写 note_review_history；关系标注 触发/衍生/继发/并行（EVT-002 未全，占位禁用并提示）。
- 状态：Detected/Reviewing/Confirmed/Processing/Resolved/Archived，StatusDot+文字。
- 权限：Member 看，Admin 评审。关联：EVT-001/002/003、SUBJ-002（双维度筛选，落库贯通前占位）。

## P4 笔记库 `/v4/notes`
- 目标：原始笔记/评论检索、去重与主体命中核查。
- 组件：Toolbar + 高密度 Table（标题/作者/主体命中/风险/发布时间 publish_datetime/采集时间 captured_at，二者分列不混淆）+ 详情 Drawer（正文/评论/二级评论/证据）。
- 交互：搜索、筛选、批量导出；主体命中可溯源到 subject_hit；空正文回填进度（NOTE-002 占位）。
- 状态：去重标记、回填状态。权限：Member+。关联：NOTE-001/002、SUBJ-001/002。

## P5 报告中心 `/v4/reports`
- 目标：日/周/月/专题报告生成与导出。
- 组件：报告列表 Table + 生成向导 Modal（周期/主体/时间口径默认 publish_datetime）+ 报告预览 Drawer + 导出（pdf/xlsx/docx，多实现收敛后走唯一 Owner）。
- 交互：生成→进度 Toast→预览；导出二次确认范围。状态：生成中/成功/失败（失败给原因非空白）。权限：Member 生成，Admin 导出。关联：RPT-001/002（统计唯一走 build_daily_report）。

## P6 Zachary AI（全局抽屉 + `/ai` 页）
- 目标：对任意模块内容做分析/摘要/分类/报告润色，区分系统事实与 AI 建议。
- 组件：AIChatDrawer、模型/置信度标注、Ollama 状态点。状态：可用/降级 gray（无 AI 业务照常）。权限：Member+。关联：AI-001，AI-002 占位。

## P7 系统区
- 健康中心 `/v4/health`：/healthz 五要素（app/db/scheduler/fs/browser）+ 看门狗/自愈状态（SYS-001）。Admin。
- 版本中心 `/v4/version-center`：当前版本/GitHub 同步点/历史/立即保存/检查更新/回滚（SYS-002；标题 bug 修复后版本号准确）。Owner。
- 公网隧道 `/v4/network`：隧道开关/地址/固定域名占位（SYS-003，gray 规划中）。Owner。
- 账号与安全 `/v4/auth`：登录、安全问答、三级权限、会话、Auth 恢复任务列表（AUTH-001/002；主 SPA 挂全局弹窗=施工前置 GAP-03）。Owner/Admin。
- 设置 `/v4/settings`：主体词（红线只读提示）、密钥脱敏、调度参数；**高危 run-code 三入口收口后只留单一受控入口并审计**（GAP-04）。Owner。

## 页面级状态/空态/移动规则
- 每个列表页必须四态（有数据/筛选无结果/加载骨架/错误），异常不得显示 0 条。
- 移动端：Sidebar→底部 Tab+抽屉，Table→卡片，Modal→全屏 sheet，Auth 流程手机可扫码恢复（依赖公网链路）。
- 六断点 390/430/768/1024/1280/1440 逐页截图 Evidence。
