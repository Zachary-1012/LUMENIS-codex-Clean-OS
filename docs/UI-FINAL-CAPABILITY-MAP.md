# UI-FINAL-CAPABILITY-MAP（UI 一次性施工能力地图）

> 2026-08-31。用途：把全部 Feature 映射到「平台→产品→模块→页面→功能→子功能→操作→状态→权限→数据→API→Runtime」，**未完成功能也占位**，使 UI 施工不再因新增功能反复改信息架构。本轮只做映射，不改 UI。
> 平台层：Z-Brand Intelligence Platform（顶层）；产品层：ZBP（含 CTH-POMS 主生产 + ZBMP 增强层）；DCC/SICI 不在本 Runtime，无本系统页面。
> 权限：Guest / Member / Admin / Owner。状态点统一：●green 正常 ●amber 预警 ●red 危险/熔断 ●blue 信息 ●gray 未启用/占位。视觉方向：侘寂黑白灰 + 极少量语义色（仅状态/关键操作），Token 化，详见 learning/ 与设计基线（本轮不施工）。

## 顶层 IA（单页为主，层级跳转）
工作台 Console（首页，单页）├ 监测采集 Collect ├ 事件/笔记/报告 Insights ├ Zachary AI ├ 品牌库 Brand(ZBMP) ├ 系统 System（健康/版本/设置/账号）。全局浮层：Auth Recovery Modal、AI 抽屉、Toast、Command Palette。**原则：核心状态首页一屏可达，详情按层级抽屉/二级页，不整页跳转。**

## 1. 工作台 Console（首页 /v4/console）
| 模块 | 功能(Feature) | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| 全局状态中心 | 平台健康小点(MON-004) | 看各平台健康；点小点直接开对应 Auth Modal | ●状态机 | Member+ | collection_logs | /api/platform-health | 主链 |
| 监测概览 | 笔记/事件/风险计数(MON-001/EVT/RISK) | 时间窗切换、下钻 | green | Member+ | notes/events 计数 | /api/stats*,/api/events* | 主链 |
| 15周年专题卡 | MON-002 | 进入专题、进度 | green/amber | Member+ | topic_campaign_notes | /api/topic-campaign/* | 主链 |
| 调度影子卡 | MON-003 | 查看决策/next_run（门控前只读） | blue(影子) | Admin | schedule_decisions | /api/collect/schedule-status | 旁路影子 |
| 最近活动 | 事件/采集时间线(EVT-002) | 查看关系、跳转详情 | green | Member+ | event_graph_* | /api/event-graph/* | 主链 |
| 快捷操作 | 手动采集/生成报告/打开AI | 主操作+危险二次确认 | — | Member+ | — | 对应 API | 主链 |

## 2. 监测采集 Collect（/v4/collect）
| 模块 | 功能 | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| 小红书(PRIMARY) | MON-001 关键词/指定ID/评论 | 启停、单次运行(自动30m/手动20m为历史参考非硬编码)、看结果 | 状态机8态 | Member 启/Admin 配 | notes/comments/collection_logs | /api/collect* | 主链+CDP9222 |
| 抖音(SECONDARY) | COLL-001 | **占位**：未验证不启用，显示 gray「未接管」 | gray 占位 | Admin | - | registry | 旁路 enabled=false |
| Instagram/Google | COLL-002/003 | 占位/实验标记 | gray/blue | Admin | - | registry | 旁路 |
| 全网搜索 | MON-005 | 关键词、结果复核 | blue 实验 | Member+ | web_* | /api/web-* | 旁路 |
| Cookie 保险库 | COLL-004 | 状态查看（不显示明文）、导入/持久 Profile | ●会话态 | Owner | data/cookies(json,非库) | 内部 | 主链 |
| 代理池 | (补丁能力) | 代理健康/切换（稳定代理补丁） | ● | Admin | proxy 配置 | /api/proxy* | 主链 |
| 空正文回填 | NOTE-002 | **占位**：待稳定网络，显示进度 | gray PLANNED | Admin | notes | - | 旁路 |

## 3. 事件 / 笔记 / 报告 Insights
| 页面 | 功能 | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| 笔记库 | NOTE-001 | 列表/筛选/去重视觉/详情/导出；主体命中标记 | green | Member+ | notes(957) | /api/notes* | 主链 |
| 主体双维度 | SUBJ-002 | subject_type/content_type 筛选（落库贯通前先占位禁用并提示） | amber DEVELOPING | Member+ | notes(待加列) | /api/subject-classifier/types | 旁路 |
| 事件流 | EVT-001 | 列表/聚合/严重度/生命周期 | green | Member+ | events(427) | /api/events* | 主链 |
| 事件图谱 | EVT-002 | 三类(营销/传播/舆情)+四关系(触发/衍生/继发/并行)图，未完成关系占位 | amber | Member+ | event_graph_*(16/1) | /api/event-graph/* | 主链 |
| 负面评审 | EVT-003 | 评审队列/确认/驳回；两套 API 收敛前固定走唯一 Owner 视图 | green | Admin | note_review_history(8327) | negative/event-review | 主链 |
| 风险 | RISK-001/002 | 风险等级、熔断/冷却态、300012 识别（非0条） | ● | Member 看/Admin 控 | events/xhs_circuit | /api/risk* | 主链 |
| 报告 | RPT-001/002 | 日/周/月/专题生成、导出 pdf/xlsx/docx；publish_datetime 口径 | green | Member+ | events/notes | /api/report* | 主链 |
| 外部导入 | IMP-001 | **占位**：importer 后端部分就绪，前端入口待建 | gray PLANNED | Admin | 无专表 | 待建 | 旁路 |

## 4. Zachary AI（全局抽屉 + /ai）
| 模块 | 功能 | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| AI 对话/分析 | AI-001 | 对任意模块内容分析、摘要、分类、报告润色；区分「AI建议/系统事实/人工」 | green(Ollama) | Member+ | ai_*/v4_ai_shadow | /api/ai* | 主链,Ollama-only |
| AI 兜底 | AI-001 | Ollama 不可用时全链仍可跑，AI 区域显式 gray 降级 | ● | Member+ | - | - | 规则兜底 |
| AI Web Worker | AI-002 | **占位**：Cookie≠API，仅研究稿 | gray PLANNED | Owner | - | - | 无 |

## 5. 品牌库 Brand（ZBMP 增强层）
| 模块 | 功能 | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| 品牌管理 | BRAND-001 | 增删改、品牌档案 | green | Admin | brand_knowledge | /api/brand* | 主链 |
| 案例库 | BRAND-002 | 案例卡片/详情/下钻 | green | Member+ | case_deep_analysis | /api/cases* | 主链 |
| 太古/怡和专题 | BRAND-003 | 专题视图，**空表空态占位** | amber DEVELOPING | Member+ | swire_*(空) | /api/swire* | 旁路 |
| 工作区层级 | WS-001 | Workspace/Brand/Project/Campaign 层级导航 **占位** | gray PLANNED | Admin | 待建 | - | 无 |

## 6. 系统 System
| 页面 | 功能 | 子功能/操作 | 状态 | 权限 | 数据 | API | Runtime |
|---|---|---|---|---|---|---|---|
| 健康中心 | SYS-001 | /healthz 五要素(app/db/scheduler/fs/browser)、看门狗、自愈 | green | Admin | - | /healthz,/api/system/health | 主链 |
| 版本中心 | SYS-002 | 当前版本/GitHub 同步态/历史/保存/回滚；修复标题 bug(GAP-15) | green | Owner | - | /v4/version-center/* | 主链 |
| 公网隧道 | SYS-003 | 隧道开关/地址/固定域名占位(gray) | ● | Owner | - | - | 进程 cloudflared |
| 账号/Auth | AUTH-001/002 | 登录、安全问答、三级权限、会话；**全局 Auth Modal 挂主 SPA(GAP-03)** | ● | 全角色 | v4_users/sessions/auth_recovery_tasks | /v4/auth/*,/api/auth-recovery/* | 主链 |
| 设置 | SETT-001 | 主体词/密钥(脱敏)/调度参数；**高危 run-code 三入口收口(GAP-04)** | green | Owner | system_config | /api/settings/* | 主链 |
| 未来平台 | FUT-001 | 微博/B站/快手/贴吧/知乎开关，**全部 gray 占位、enabled=false** | gray RESERVED | Owner | - | registry | 不运行 |

## 7. 全局浮层与交互态（所有页面统一）
- **Auth Recovery Modal（不跳页）**：平台/账号/状态/失效原因/二维码或合法验证入口/「我已完成验证」「稍后处理」/任务暂停态/恢复态；A 登录失效=弹码，B NEED_VERIFY=人工验证，C IP_RISK/300012=熔断冷却（不可伪装成扫码可解）。手机公网同样在当前页弹。
- 统一组件：Button/IconButton/Input/Select/Search/Tabs/Badge/**StatusDot**/Table/Drawer/Modal/Toast/EmptyState/Loading/ErrorState/Timeline/Metric/Panel；状态 Idle/Loading/Success/Error + Disabled 必带原因；危险操作二次确认。
- 响应式断点必验：390 / 430 / 768 / 1024 / 1280 / 1440；移动端非桌面缩放，表格/弹窗/抽屉/图表 Overflow 处理。
- 空态：PLANNED/RESERVED/空表统一 EmptyState 占位（如 IMP-001/WS-001/FUT-001/swire 空表），**不得因未完成从 IA 删除，也不得显示成「0 条舆情」**。

## 施工就绪判断（事实，不代用户拍板）
- IA 与占位已可覆盖全部 34 Feature（含 11 个非 ACTIVE 的合理占位），新增功能可在本层级内挂点，无需重排导航。
- 开工前置：GAP-03（主 SPA 挂 Auth Modal）、CSS Token 单层收敛（避免 17 个旧 CSS 再次覆盖新 UI 的根因）；施工在 Staging(8301) 进行，生产 8201 不动；后端 API 冻结、同期不改业务（一任务一 commit）。
