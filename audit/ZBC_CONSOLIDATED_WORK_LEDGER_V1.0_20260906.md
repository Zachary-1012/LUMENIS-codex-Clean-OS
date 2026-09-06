# ZBC 新增·补回·适配·优化·修复 整合总账 V1.0

> 2026-09-06 整合，供用户核对无遗漏；团队 o_0001rZI3gM0 后台并行推进（当前约8%）
> 来源：用户指令 + OSAI研究汇编30卷 + 功能映射530 + 旧分支580c2cf差异 + 三仓规则 + 用户决策
> 状态：⬜待办 / 🔄进行 / ✅完成

## A. 补回——曾经有、重写/整合中掉线的（后端多在，前端重新接线）
| # | 项 | 去向 | 优先级 | 状态 |
|---|---|---|---|---|
| A1 | 案例深度分析 case_deep_analysis | CTH Events/Evidence | P1 | 🔄 |
| A2 | PR案例集成 pr_case_integration/engine | ZBMP Content/Competition | P1 | 🔄 |
| A3 | 太古集团 swire_group | CTH Overview | P1 | ⬜ |
| A4 | 话题活动 topic_campaign | CTH Events | P1 | ⬜ |
| A5 | App证据 app_evidence | SYSTEM/Evidence | P1 | ⬜ |
| A6 | 架构仪表盘 architecture_dashboard | SYSTEM Runtime | P1 | ⬜ |
| A7 | 系统控制 system_controls/features_ui | SYSTEM | P1 | ⬜ |
| A8 | ZBMP工作台/面板/外壳 zbmp-workbench/panels/shell | ZBMP全域 | P1 | ⬜ |
| A9 | 红点提醒 badge_manager（铃铛未读/负面待审30s） | base全局 | P1 | 🔄 |
| A10 | 微博/B站辅助数据源 auxiliary_sources | 采集发现页 | P1 | ⬜ |
| A11 | 键盘快捷键 Ctrl+/ 帮助窗口 | base.html | P1 | 🔄(js已建) |
| A12 | **播客 podcast 前端+23丢失文件+方法论资料（用户强调重要）** | ZBMP Content优先 | P1 | ⬜ |
| A13 | 启动屏 launch-screens(cth/zbmp desktop+mobile)重做 | 全局 | P1 | ⬜ |

## B. 新增——本轮全新要建
| # | 项 | 说明 | 优先级 | 状态 |
|---|---|---|---|---|
| B1 | 轻量AI助手入口（A3决策） | 废3D球，保留系统问答能力，右下角入口接intelligence网关 | P1 | ⬜ |
| B2 | intelligence_library 统一资料库 | 13目录骨架已建+intelligence_assets新表(不碰62表)+检索API | P1 | 🔄(骨架已建) |
| B3 | 研究→ZBC五态落地索引 | 已落地/待验证/可复用/建议转化/仅研究 | P1 | ⬜ |
| B4 | 域前缀API /api/zbmp /api/cth /api/system + 兼容层 | 双域契约 | P1 | ⬜ |
| B5 | ZBMP Competition 竞品独立页 | 核心差异化(代码待建) | P1 | ⬜ |
| B6 | ZBMP风险策略 | 与CTH风险阈值分离 | P1 | ⬜ |
| B7 | 双产品切换器 ZBMP↔CTH（重载上下文/权限/数据） | 全局 | P1 | ⬜ |
| B8 | 内置AI浏览器界面（SYSTEM Collector内嵌实时采集画面） | P1 | P1 | ⬜ |
| B9 | 外部跳转使用者确认弹窗 + 危险协议拦截 | 安全 | P1 | ⬜ |
| B10 | 公关15外部标杆案例(C-01~15)+6话术+ACT+日报5板块 | CTH报告 | P1 | 🔄探查完 |

## C. 拿回整合——研究资产/优化代码（外部→受治理副本，原件不动）
| # | 来源 | 内容 | 动作 | 状态 |
|---|---|---|---|---|
| C1 | OSAI线上main@2387501(645文件) | 30卷研究（本地缺12文件，线上补齐） | 复制+元数据索引 | 🔄(clone受阻,fallback本地+线上补) |
| C2 | AI-Development-Research-Hub(99) | Research Hub/cases/protocols | 入09/10卷 | ⬜ |
| C3 | 本地Zachary OS AI(633) | 语言库/品牌营销25/AI研究15/KOS/序境 | 入对应卷 | ⬜ |
| C4 | 00-GOVERNANCE/02-ARCHITECTURE/contracts/core(85) | 治理/契约/架构 | 入00总览/06/10 | ⬜ |
| C5 | SICI-Core三优化模块 | dual_pool/unified_logger/base_adapter_enhanced | 评估缺则接入 | P2 ⬜ |
| C6 | GPT/Codex旧CSS(design-v9 30K+zb-gpt 72K) | 质感token提取融入V1.1 | P1-B | ⬜ |
| C7 | learning-feed播客方法论 | 随A12入资料库 | ⬜ |

## D. 适配——融合到新架构/双域/三仓，不回退旧UI
- D1 所有回补功能改用 xjViz 函数驱动+真实API，不照搬旧JS
- D2 资料库每条资产打 product 归属：ZBC / GGI / SHARED；**GGI专属真相不混入ZBC**
- D3 OSAI六条红线：不成为runtime依赖、不拷业务代码、走Admission准入(CANDIDATE→…→ADMITTED)
- D4 modal_simplify渐进展开理念融入新弹窗组件（不留独立补丁）
- D5 DCC/SICI/lumenis-command 平台独立不并入，仅研究文档入资料库；NSFW不纳入
- D6 ZBMP Growth整合进Overview+Brand Tab；CTH Brands/Industries整合为Overview Tab+Real-time筛选器

## E. 优化——体验/设计/质量
- E1 Design System V1.1：吸收GPT/Codex中性底质感，品牌色#0F766E，三域色，浅色默认可切深色，Inter+Noto Sans SC，收小字号
- E2 KOS kos_metrics/kos_attribution 固定公式→平台规则驱动、可延展（不写死系数）
- E3 runtime_guardian(零调用)接入采集主链；permission_gate(仅2处)写操作全面接入
- E4 ui_view_model(零调用)函数驱动动态可视化全页面接入、30s轮询
- E5 ai_channel 与runtime_guardian重复CircuitBreaker收敛；safety_boundary与security_boundary重复收敛
- E6 collector_v2/v4_upgrade部分未接入模块评估接入主链

## F. 修复——bug/断链/遗留
- F1 SYSTEM AI页3区域HTTP404（AI调用日志/OWASP安全门/AI评估，API路径对齐）
- F2 清理底部残留旧tab栏(Overview/Real-time/Events/Risk/System)
- F3 CTH Reports首个统计卡片空标题
- F4 全17页六态回归(Loading/Empty/Error/Success/Degraded/Permission)+截图
- F5 数据精准红线：缺失null不用0、publish/collected时间分离、content_hash去重、失败显式记录、AI与原始数据分离（上轮已修overview.stats/notes，继续全链路核查）
- F6 app.py BOM编码、Flask模板缓存(debug=False重启)等收口

## G. 外部BLOCKED（非代码可解，明确标注不伪造VERIFIED）
极光/Meta Ads/巨量引擎/X Ads 缺凭证+代理；Cloudflare tunnel缺账号域名；微信通知缺公众号凭证；微博/B站cookie-free登录缺cookies。

## 目录动作（用户已决策）
删空壳(dependencies/2026-08-30/2026-09-01)；staging核对后归档99-ARCHIVE(非删)；ref_gpt_v2保留提取；archive/backups不动；deliverables检查留。
