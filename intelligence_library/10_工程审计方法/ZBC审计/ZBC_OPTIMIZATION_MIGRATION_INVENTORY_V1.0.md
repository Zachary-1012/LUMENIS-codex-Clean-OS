# ZBC 优化代码/研究资产迁移融合清单 V1.0

> 落盘时间：2026-09-06
> 目标：把散落在各仓库/旧分支的 ZBC 研究资料、优化代码、前端功能迁入当前 lumenis-dual-domain-v3 并适配融合，不丢失、不搞混
> 当前主库：D:\Taikoo-monitor-new @ de8d5d6（Design System V1.1，18页重写+函数驱动可视化）

## 一、外部研究仓库（→ Intelligence 资料库，详见 INTELLIGENCE_LIBRARY_ARCHITECTURE_V1.0.md）
- D:\AI-Development-Research-Hub（99文件/524KB）：案例库/研究/证据/影子学习
- D:\Zachary OS AI（03-RESEARCH语言库39 + learning-feed品牌营销46 + ai-os-research技术研究20 + research-inbox25 + 序境27）
- 太古汇运营资料：**用户明确要求不动，排除**

## 二、旧分支前端功能回补清单（staging=580c2cf 有、当前 HEAD 无）
> 背景：Design System V1.1 重写建立三域结构（zbmp/cth/system），旧扁平模板(templates/events.html/index.html/notes.html/report.html)被替代=正确；但下列**功能性 JS 对应的功能不能丢**，必须在新三域 UI 重新接线。

### 2.1 后端模块仍在（KEEP），前端需重新接线
| 功能 | 后端模块(在) | 旧前端JS(重写后丢) | 回补到新位置 |
|---|---|---|---|
| 案例深度分析 | case_deep_analysis.py ✅ | case_deep_analysis.js | CTH Events/Evidence |
| PR案例集成 | pr_case_integration.py + pr_case_engine.py ✅ | pr_case_integration.js | ZBMP Content/Competition |
| 太古集团 | swire_group.py ✅ | swire_group.js | CTH Overview |
| 话题活动 | topic_campaign.py ✅ | topic_campaign.js(根+static/js) | CTH Events |
| App证据 | app_evidence.py ✅ | app_evidence.js | SYSTEM/Evidence |
| 架构仪表盘 | (后端在) | architecture_dashboard.js | SYSTEM Runtime |
| 系统控制 | (后端在) | system_controls.js + system_features_ui.js | SYSTEM |
| 前端增强/交互 | (设计层) | frontend_enhancement.js + design-v9-interactions.js + modal_simplify.js | base.html 全局 |
| ZBMP工作台/面板/外壳 | (后端在) | zbmp-workbench.js + zbip-panels.js + zbip-shell.js | ZBMP 全域 |
| v3模块 | (后端在) | v3_modules.js | 按需 |

### 2.2 纯前端/待确认是否需要
- badge_manager.py 后端也无 → 确认徽章功能是否保留，若保留需前后端一起补
- auxiliary_sources.py 后端也无 → 确认辅助来源功能是否保留
- nomi_global_drag（全局拖拽）→ 评估是否保留
- zachary_robot / zachary_3d / three.min.js / zachary_png_face（3D机器人组件，旧装饰）→ 用户未要求，默认废弃，如需保留单独确认

### 2.3 键盘快捷键（确认丢失，P1 回补）
- 旧实现：static/js/keyboard_shortcuts.js（13.6KB，Ctrl+/ 唤起帮助窗口，commit a01d301）
- 现状：新 templates/base.html 0 匹配，功能在重写中丢失
- 动作：把 keyboard_shortcuts.js 适配新三域结构后重新接入 base.html

## 三、GPT/Codex 设计风格资产（供 Design System V1.1 吸收，不直接覆盖）
> 用户明确要求 OpenAI/Codex/GPT 底色，旧分支已有成熟实现可提取 token，避免重新摸索
- static/css/design-v9-gpt-codex.css（30KB）→ 提取配色/间距/圆角/阴影 token，与 V1.1 深青绿 #0F766E 融合
- static/css/zb-gpt-theme.css（72KB）→ 提取深浅双主题变量
- static/css/tokens.css / tokens-minimal.css / ZBIP_DESIGN_TOKENS.css / zbip-tokens.css → 设计 token 对照
- 原则：吸收其 GPT/Codex 质感骨架，品牌色用序境深青绿，不照搬旧配色；不允许回退到旧 UI

## 四、UI 设计研究文档（→ 资料库 methodology/design 子库）
- docs/UI/COMPONENT-SYSTEM.md 组件系统
- docs/UI/ZBIP-DESIGN-SYSTEM.md 设计系统
- docs/UI/STEP4-WORKBENCH-IA.md 工作台信息架构
- docs/UI/UI-EVIDENCE-PROCESS.md UI证据流程
- docs/UI/page-maps/：CTH-POMS / DCC / SICI / ZBMP 四个页面地图
- docs/PRODUCTION_BASELINE_2026-08-31(V3).md 生产基线

## 五、SICI-Core 优化模块（D:\SICI-Core，59文件/352KB）
- upgrade_modules/base_adapter_enhanced.py 基础适配器增强
- upgrade_modules/dual_pool.py 双连接池
- upgrade_modules/unified_logger.py 统一日志
- upgrade_modules/接入指南.md
- docs/：能力注册表/有效规则/运行时预检/持续研究策略/三仓矩阵/小红书安全研究系列(XHS-REDNOTE-SAFE-ARCHITECTURE-V2等)
- 动作：评估3个优化模块是否已在主库（dual_pool/unified_logger/base_adapter），未接入则适配融合；研究文档入资料库

## 六、其他待评估仓库
- D:\Development-Command-Console（105文件/772KB，protocols/server/js/css）→ tools/development-command-console 旧分支有，评估是否为 DCC 产品域代码
- D:\repo-audit（24文件，内含SICI-Core审计）→ 审计报告入资料库
- D:\Taikoo-security（1133文件/461MB，feat/keyboard-shortcuts-modal 旧完整副本）→ 与 staging 同源，作为安全参考，不整体迁移
- D:\audit-four-source（9786文件/4.1GB，四源原始包）→ 原始证据，体积大，只入索引不迁移文件
- D:\data（collector_history.json + monitor.db）→ 历史采集数据，评估是否并入数据备份

## 七、融合原则（防止搞乱）
1. 当前主库 de8d5d6 是唯一事实基线，所有外部资产只做"增量接入/适配融合"，不覆盖、不回退新架构
2. 研究文档→intelligence_library/；功能代码→适配后进入对应三域模块；设计token→提取融入 Design System
3. 每个回补功能必须：后端在→前端新接线→真实API→浏览器验证，不允许功能静默消失
4. 迁移前在本清单勾选登记，迁移后浏览器验证，证据留痕
5. 拿不准是否保留的（zachary_robot装饰等）单列，不擅自删除也不擅自接入，等用户确认

## 八、执行优先级
- P1：键盘快捷键回补 + 2.1 表格9项功能在新UI重新接线（防止功能丢失）
- P1：GPT/Codex CSS token 提取融入 V1.1
- P2：259研究文件迁入 intelligence_library + 元数据索引
- P2：SICI-Core 3优化模块评估接入
- P3：其他仓库文档入索引、DCC评估
