# ZBC 已有资产统一适配执行单 V1.0（先梳理复用→统一适配→修补，禁止重复造轮子）

> 唯一主库 D:\Taikoo-monitor-new。原则：ZBC 已开发完的功能/规则/UI 先梳理复用，在**当前双域架构与现有设计体系**上统一适配、修补调整；UI 后置、按现架构现设计增量更新，不重建设计体系、不恢复旧 UI、不引新库替代自研件。

## 一、功能规则模块（均已存在，只做适配/接入/修补，不重写）
| 模块 | 行数 | 适配动作 |
|---|---|---|
| subject_rules.py（SUBJECT_WORDS/EXCLUDE/subject_hit 红线） | 284 | 绝对保护，迁移重判复用，不改判定语义 |
| risk_engine.py / collector_guard/risk_engine.py | 902/307 | 双域策略接入，unknown 不并 negative、critical≠high |
| kos_engine.py / kos_metrics.py / kos_attribution.py | 1402/621/188 | 复用引擎；metrics/attribution **去固定公式，改平台官方规则+研究成果驱动、可配置可延展** |
| canonical_data.py / canonical_metrics.py / data_boundary.py | 1082/277/225 | 历史数据过 canonical 管线、按双域打标 |
| evidence_chain.py / data_quality_gate.py / compliance_gate.py | 1167/245/133 | 接入主链，质量门禁每步校验+失败记录 |
| domain_isolation.py / subject_classifier.py / subject_context.py | 264/356/325 | 双域隔离复用，任务/数据不丢域身份 |
| evaluation_system.py / evaluation_dimensions.py | 476/705 | 复用，按域出评估 |
| ui_view_model.py | 824 | **函数驱动可视化：零调用→接入**，后端函数→view model→前端，禁写死 |
| daily_report.py / report_engine.py / report_export | 959/408/435 | 双报告体系接入，补 ZBMP 六类报告 |
| alert_engine.py | 443 | 复用接入 |

## 二、UI / 设计资产（按现架构现设计更新，不重建）
- 设计 token：`static/css/lumenis-tokens-v2.css`（以 v2 为准）、lumenis-tokens.css；样式体系 lumenis-reset/layout/components/core-components/motion/responsive、zbc-design-v1.1、xujing-core/dual-domain——**在其上增量改，不另起 Design System**。
- 标准与契约文档（已写过，直接遵循）：docs/design/LUMENIS-UI-STANDARD-v1.0.md、LUMENIS-UI-UX-MASTER-v1.0.md、ZBC_UI_UX_LANGUAGE_V2.md、docs/UI-INTERACTION-SYSTEM-V1、docs/UI_UX_NON_REGRESSION_CONTRACT（**UI 不回退契约必须守**）、docs/learning/ui/MOTION-INTERACTION-PATTERNS、ZBIP-UI-MOTION-UPGRADE-BLUEPRINT、docs/reference/apple-ui-reference。
- 动效/横向叠层：复用 lumenis-motion.css、static/js/carousel.js（同级卡片横向叠层滑动），不重写。
- 双域模板：templates/zbmp|cth|system|auth 现有架构上补功能页，不回退 production/intelligence 旧 IA。

## 三、线性图标——复用自研 lumenis-icons.js，禁止引新图标库/重画
- 现有 `static/js/lumenis-icons.js` 已符合规范：24×24 viewBox、**1.5px 线性描边、fill=none、currentColor、圆头线帽**，注册表 licon(name)，已有导航/操作/状态数十个。
- 动作：全站图标统一改走 licon()；**左导航小红书实心红块、任何 emoji/实心块替换为线性图标**（在 paths 注册表补 xiaohongshu/douyin/weibo/bilibili/zhihu 等线性品牌图标，品牌色只作描边或小色点，不铺实心块）；统一 1.5px、24px、文字标签；缺图标只在该注册表增补，不引入 lucide/heroicons/iconfont 等外部库。

## 四、中英韩三语——先核实现有机制再扩展，不另起 i18n 框架
- 语言相关已命中 lumenis-core.js、lumenis-data.js、base.html 及 38 个模板：**先读清现有语言机制**，在其上映射 zh-CN/en/ko 三套词条、可见文案走 key 不硬编码；语言切换放 设置-外观、默认中文、持久化、整页即时切换不混排。
- 韩文复用 intelligence_library/OSAI/ADRH 三语库并母语校对，没把握标 missing 回退中文，禁止机翻硬编。

## 五、标准用名——复用已有术语文档成唯一术语表
- 以 docs/INGESTION_AND_TERMINOLOGY_STANDARD_20260902.md、docs/NAMING-TERMINOLOGY-COMMENT-RUNTIME-GUARDRAILS-V1、docs/PRODUCT_NAMING_BASELINE.md + audit/PRODUCT_TERMINOLOGY_I18N_LINEARICON_V1.0.md 合并成唯一《产品术语表》；面向用户层去 ZBC/OSAI/SYS 等内部代号（序境LUMENIS/品牌智能/太古汇智能/系统），首页「ZBC 生产真相×OSAI 智能推理」类文案按术语表替换。

## 六、函数驱动真实数据——复用 lumenis-data.js，清掉占位
- `static/js/lumenis-data.js` 已是真实 API 绑定层（绑 /api/system/health/summary、/api/ai/status、/api/risk-alerts、/api/collect/schedule-status、/api/evidence/list、/api/stats，无数据 empty、错误 error、**绝不静默成 0/假绿**）。
- 动作：首页 `source: health/summary…`、`Provider: detecting…` 占位全部接到这套真实绑定；新增页同模式，由后端函数供数，禁 Mock/写死/静态成功。

## 七、执行顺序
1) 各组先按本单核对"已有资产位置"，确认复用路径，再动手；真缺失才新建并注明依据。2) 阶段一保功能/规则/数据/链路/前后端契约，UI 只做必要接线。3) 阶段二在当前 token+模板架构上统一做：licon 线性化、术语替换、三语切换、动效与横向叠层、函数驱动灌满真实数据。4) 全程守 UI 不回退契约与双域隔离。
