# UI/UX HARD RESET — Delete Manifest
> Date: 2026-09-04 | Status: ACTIVE | Owner: 序境-Core / ZBC
> 原则：先扫描→分类→删除→Core Audit→Test→Commit→Push
> 严禁删除：Product Definition / Architecture / Domain Logic / Business Logic / API / Data Model / Database / Runtime / AI Capability / Security / Tests / Research / Git History

---

## 分类标准

- **DELETE**: 明确无业务价值、已废弃、纯UI实现、机器人UI、备份文件
- **MERGE**: 与新实现重复，需合并后删除旧版
- **KEEP**: 包含核心业务逻辑，需保留UI层但重构
- **ARCHIVE**: 设计研究资产，归档到/design-system/research/

---

## ZBC — DELETE 清单

### 1. 备份文件（明确可删，无业务价值）

| 文件 | 大小 | 原因 |
|---|---|---|
| static/index.html.bak-d3 | 136KB | 旧备份 |
| static/index.html.bak-dualkeep | 132KB | 旧备份 |
| static/index.html.bak-ibrowser | 135KB | 旧备份 |
| static/js/brand_hub.js.bak-koscollect | 12.5KB | 旧备份 |
| static/js/brand_hub.js.bak-refactor | 20.5KB | 旧备份 |
| static/js/brand_hub.js.bak-ui | 16.4KB | 旧备份 |
| static/js/zachary_robot_enhanced.js.bak-aifix | 28.4KB | 旧备份 |

**小计: 7文件 / 381KB**

### 2. 机器人相关UI（Robot UI/Avatar/Animation/Interaction/Renderer，AI Core保留）

| 文件 | 大小 | 原因 | 替代 |
|---|---|---|---|
| static/js/zachary_robot.js | 34.8KB | Robot UI/Avatar/Animation | AI Core在intelligence.py |
| static/js/zachary_robot_enhanced.js | 33.8KB | Robot UI增强 | 同上 |
| static/js/zachary_3d.js | 7.8KB | Robot 3D动画 | 删除 |
| static/js/zachary_png_face.js | 2KB | Robot头像 | 删除 |
| static/js/zachary_system_knowledge.js | 11.9KB | Robot知识库UI | 内容迁移到Lifecycle |
| zachary_robot_widget.html | 10.7KB | Robot小部件页面 | 删除 |

**小计: 6文件 / 101KB**

### 3. 废弃/演示HTML页面（无业务路由引用）

| 文件 | 大小 | 原因 |
|---|---|---|
| static/creative-mobile.html | 8.7KB | 废弃移动端创意页 |
| static/mobile.html | 8.7KB | 旧移动端入口（已被响应式替代） |
| static/preview.html | 8.7KB | 旧预览页 |
| static/taiji-state-demo.html | 4.6KB | 太极状态演示页 |
| static/zb-preview.html | 8.3KB | 旧ZB预览页 |
| static/api-keys.html | 10.8KB | 旧API密钥页（安全风险，应删除） |
| static/topic_campaign.html | 5.8KB | 旧话题活动页 |

**小计: 7文件 / 55.6KB**

### 4. 旧CSS实现（已被xujing-core.css统一替代）

| 文件 | 大小 | 原因 | 替代 |
|---|---|---|---|
| static/css/style.css | 85.4KB | 旧全局样式（含.modal冲突定义3处） | xujing-core.css |
| static/css/components.css | 31.6KB | 旧组件样式 | xujing-core.css |
| static/css/layout.css | 22.8KB | 旧布局样式 | xujing-core.css |
| static/css/mobile.css | 20KB | 旧移动端样式 | xujing-core.css响应式 |
| static/css/ui_optimized.css | 13.7KB | 旧UI优化样式 | xujing-core.css |
| static/css/zbip-components.css | 18KB | 旧ZBIP组件 | xujing-core.css |
| static/css/zbip-tokens.css | 10.2KB | 旧ZBIP token | tokens.css + xujing-core.css |
| static/css/zbip-panels.css | 8.7KB | 旧ZBIP面板 | xujing-core.css |
| static/css/v3_modules.css | 9.3KB | 旧v3模块样式 | xujing-core.css |
| static/css/brand_hub.css | 7.9KB | 旧品牌中心样式 | xujing-core.css |
| static/css/internal_browser.css | 6.4KB | 旧内置浏览器样式 | xujing-core.css |
| static/css/taiji-state.css | 5.4KB | 旧太极状态样式 | 删除（taiji演示已删） |
| static/css/evidence_dashboard.css | 4KB | 旧证据看板样式 | xujing-core.css |
| static/css/osai-shell.css | 3.6KB | 旧OSAI shell样式 | xujing-core.css |
| static/css/nomi_global_drag.css | 0.9KB | 旧nomi拖拽样式 | 删除 |
| static/css/case_deep_analysis.css | 12.1KB | 旧案例分析样式 | 需检查引用 |
| static/css/architecture_dashboard.css | 11.3KB | 旧架构看板样式 | 需检查引用 |
| static/css/resident_health.css | 11KB | 旧驻场健康样式 | 需检查引用 |

**小计: 18文件 / 282KB（需逐步验证引用后删除）**

### 5. 旧UI JS实现（纯UI/交互/渲染，业务逻辑已迁移）

| 文件 | 大小 | 原因 | 替代 |
|---|---|---|---|
| static/js/ui_interactions_v5.8.0.js | 40.8KB | 旧v5.8交互层 | xujing-ui.js + app.js |
| static/js/design-v9-interactions.js | 13.6KB | 旧v9设计交互 | xujing-ui.js |
| static/js/modal_simplify.js | 12.8KB | 旧弹窗简化 | xujing-core.css #modal协议 |
| static/js/xj-shine.js | 4.4KB | 旧shine动效 | xujing-core.css silver-shimmer |
| static/js/xj-reveal.js | 1.7KB | 旧reveal动效 | xujing-core.css |
| static/js/nomi_global_drag.js | 3.7KB | 旧nomi拖拽 | 删除 |
| static/js/podcast.js | 6.6KB | 旧播客模块 | 需检查引用 |
| static/js/auxiliary_sources.js | 3.8KB | 旧辅助来源 | 需检查引用 |
| static/js/local_import.js | 2.2KB | 旧本地导入 | 需检查引用 |
| static/js/badge_manager.js | 8.3KB | 旧徽章管理 | 需检查引用 |
| static/js/keyboard_shortcuts.js | 13.5KB | 旧快捷键 | 需检查引用 |

**小计: 11文件 / 111KB（需逐步验证引用后删除）**

---

## ZBC — KEEP 清单（含核心业务逻辑，不可删）

| 文件 | 大小 | 原因 |
|---|---|---|
| static/index.html | 152.5KB | 主页面，含21个page-section |
| static/js/app.js | 114.8KB | 主应用逻辑+路由+状态管理 |
| static/js/frontend_enhancement.js | 58.1KB | 前端增强（含业务逻辑） |
| static/js/zbmp-workbench.js | 52.7KB | ZBMP工作台（独立产品） |
| static/js/kos_dashboard.js | 40.2KB | KOS看板（核心业务） |
| static/js/system_controls.js | 33.2KB | 系统控制（核心Runtime） |
| static/js/case_deep_analysis.js | 27.1KB | 案例分析（核心业务） |
| static/js/architecture_dashboard.js | 24KB | 架构看板（核心Runtime） |
| static/js/zbip-shell.js | 22.8KB | ZBIP shell（核心UI框架） |
| static/js/v3_modules.js | 21.8KB | v3模块（核心业务） |
| static/js/app_evidence.js | 20.9KB | 证据看板（核心业务） |
| static/js/brand_hub.js | 19.9KB | 品牌中心（核心业务） |
| static/js/lifecycle-center.js | 19.9KB | V3生命周期中心（核心） |
| static/js/auth_recovery_poller.js | 19.2KB | Auth恢复（核心安全） |
| static/js/swire_group.js | 16.9KB | 太古汇集团（核心业务） |
| static/js/system_features_ui.js | 16.8KB | 系统功能UI（核心） |
| static/js/resident_health.js | 16KB | 驻场健康（核心Runtime） |
| static/js/xj-chat.js | 15.4KB | AI聊天（核心AI UI） |
| static/js/xujing-viz.js | 15.3KB | 可视化（核心数据展示） |
| static/js/zbip-panels.js | 14.1KB | ZBIP面板（核心UI） |
| static/js/internal_browser.js | 10.9KB | 内置浏览器（核心Runtime） |
| static/js/pr_case_integration.js | 10.7KB | 公关案例整合（核心业务） |
| static/js/zbip_motion.js | 8KB | 动效表驱动（核心Motion） |
| static/js/xujing-nav.js | 7.5KB | 6大域导航（核心IA） |
| static/js/xujing-icons.js | 7.2KB | Icon函数层（核心UI） |
| static/js/xujing-ui.js | 6.8KB | UI组件（核心UI） |
| static/js/xujing-i18n.js | 6.4KB | 国际化（核心） |
| static/js/taiji-state.js | 5.3KB | 太极状态（核心Runtime） |
| static/js/evidence_dashboard.js | 4.9KB | 证据看板（核心业务） |
| static/js/xujing-crossfilter.js | 4.5KB | 交叉过滤（核心数据） |
| static/css/xujing-core.css | 63.8KB | 统一视觉权威层（核心） |
| static/css/tokens.css | 15KB | Design Token（核心） |
| static/zbmp-workbench.html | 43.4KB | ZBMP工作台（独立产品） |
| static/creative-workbench.html | 23.1KB | 创意工作台（核心） |

**小计: 38文件 / 780KB**

---

## ZBC — ARCHIVE 清单（设计研究资产）

| 内容 | 位置 | 归档目标 |
|---|---|---|
| Design Philosophy | docs/UI/ | design-system/research/ |
| 14条UI规范 | docs/UI/XUJING-UI-STANDARD.md | design-system/research/ |
| 6大域IA定义 | docs/UI-FINAL-CAPABILITY-MAP.md | design-system/research/ |
| Motion Principles | zbip_motion.js MotionTable | design-system/research/ |
| Apple/HIG Research | OSAI学习记录 | design-system/research/ |
| Token体系 | tokens.css | design-system/research/ |

---

## OSAI — DELETE 清单

> OSAI = 序境-Intelligence，主要是Research/AI，UI实现较少

需扫描后补充。

---

## 执行计划（分阶段，每步验证）

### 阶段A: 安全删除（无依赖，立即执行）
1. 删除7个.bak备份文件（381KB）
2. 删除6个机器人UI文件（101KB）
3. 删除7个废弃HTML页面（55.6KB）
4. **验证**: healthz 200 + 首页可访问 + 21页面存在

### 阶段B: 旧CSS清理（需验证引用）
1. 扫描每个CSS的引用情况
2. 确认无引用后删除
3. **验证**: 页面无404 + 布局正常

### 阶段C: 旧UI JS清理（需验证引用）
1. 扫描每个JS的引用情况
2. 确认无引用后删除
3. **验证**: 无JS报错 + 功能正常

### 阶段D: Core Audit
1. Product Core PASS
2. Business Logic PASS
3. API PASS
4. Data PASS
5. Runtime PASS
6. AI Core PASS
7. Lifecycle PASS
8. Security PASS
9. Tests PASS

---

## 风险提示

1. **app.js (114.8KB)** 同时包含UI渲染和业务逻辑，不可直接删除
2. **index.html (152.5KB)** 是主页面，包含21个page-section，不可删除
3. **旧CSS删除前必须验证引用**，否则页面布局崩溃
4. **旧JS删除前必须验证引用**，否则功能失效
5. **机器人UI删除后**，需确认AI聊天(xj-chat.js)仍正常工作
6. **每阶段删除后必须验证**，不得一次性全删

---

## 状态追踪

| 阶段 | 状态 | 验证 |
|---|---|---|
| 扫描 | ✅ COMPLETE | 47JS+21CSS+11HTML+7BAK |
| 分类 | ✅ COMPLETE | DELETE/MERGE/KEEP/ARCHIVE |
| 阶段A删除 | ⏳ PENDING | - |
| 阶段B删除 | ⏳ PENDING | - |
| 阶段C删除 | ⏳ PENDING | - |
| Core Audit | ⏳ PENDING | - |
| Commit | ⏳ PENDING | - |
| Push | ⏳ PENDING | - |
| Remote Verify | ⏳ PENDING | - |
