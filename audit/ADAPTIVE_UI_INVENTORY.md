# ZBC Adaptive UI Inventory — UI组件清单 + 响应式/动效依赖图

> **G Shard · Adaptive UI + Motion System V1**
> 审计日期：2026-09-07
> 审计范围：D:\Taikoo-monitor-new 全部前端资产
> 状态：VERIFIED

---

## 1. 现有CSS文件清单

| 文件 | 大小 | 职责 | 响应式方式 | 动效 | 状态 |
|------|------|------|-----------|------|------|
| `static/css/zbc-design-v1.1.css` | — | 基础设计令牌（颜色/字体/间距） | 无 | 无 | 保留（基础层） |
| `static/css/xujing-core.css` | — | 序境核心样式 | 无 | 无 | 保留（基础层） |
| `static/css/zbc-layout-v1.1.css` | ~14KB | 布局系统（Sidebar 240px + Topbar 56px + Content） | `@media (max-width:768px/480px)` | transition/shimmer | 保留（兼容层覆盖） |
| `static/css/lumenis-global-design.css` | ~20KB | A Shard视觉设计系统（大圆角/胶囊导航/渐变/KPI/毛玻璃/pill/进度条） | `@media (max-width:768px)` | countUp/shimmer/pulse/progress | 保留（视觉基础层） |
| `static/css/adaptive-layout.css` | ~19KB | **G Shard新增** Container Query Layout Engine + Size Model + Grid + Typography | **@container 为主** | motion token | **新增** |
| `static/css/adaptive-components.css` | ~17KB | **G Shard新增** 自适应组件样式（20+组件） | **@container 驱动** | preset/state/transition | **新增** |

---

## 2. 现有JS文件清单

| 文件 | 大小 | 职责 | 响应式 | 动效 | 状态 |
|------|------|------|--------|------|------|
| `static/js/lumenis-core.js` | — | 核心框架（fetch/auth/i18n基础） | 无 | 无 | 保留 |
| `static/js/lumenis-data.js` | — | 数据层 | 无 | 无 | 保留 |
| `static/js/lumenis-icons.js` | — | 线性图标SVG渲染 | 无 | 无 | 保留 |
| `static/js/lumenis-motion-engine.js` | ~15KB | A Shard动效引擎（countUp/drawAreaChart/fillProgress/stagger/pulse/flashUpdate/slideTab） | IntersectionObserver | 全部动效能力 | 保留（Motion基础层，G扩展复用） |
| `static/js/domain-context.js` | — | 域上下文切换 | 无 | 无 | 保留 |
| `static/js/xujing-viz.js` | — | 可视化（trend/donut/table/kpi/animateNumber） | 无 | animateNumber | 保留 |
| `static/js/ai-assistant.js` | — | AI助手 | 无 | 无 | 保留 |
| `static/js/browser.js` | — | 内置浏览器 | 无 | 无 | 保留 |
| `static/js/adaptive-engine.js` | ~13KB | **G Shard新增** Adaptive Layout Engine JS（Container Query检测/Size Model/Module Registry/Resize处理/Density/Drawer/Modal控制） | ResizeObserver+Container Query | 事件系统 | **新增** |
| `static/js/adaptive-motion.js` | ~14KB | **G Shard新增** Motion System（Token/Preset/State/Transition/Priority，复用LDMotion） | 离屏暂停 | 统一动效API | **新增** |

---

## 3. 现有模板页面清单（31页）

### 3.1 基础模板
| 模板 | 用途 |
|------|------|
| `templates/base.html` | 基础布局（Sidebar+Topbar+Content+Mobile Tabbar），已接入G Shard CSS/JS |

### 3.2 ZBMP域（11页）
| 页面 | 路由 | 主要组件 |
|------|------|---------|
| `zbmp/overview.html` | `/lumenis/zbmp/overview` | KPI×4 / Trend Chart / Industry Bars / TOP10 Table / AI Opportunity — **已注册Module Registry** |
| `zbmp/brand.html` | `/lumenis/zbmp/brand` | Brand列表/详情 |
| `zbmp/content.html` | `/lumenis/zbmp/content` | 内容库 |
| `zbmp/kos.html` | `/lumenis/zbmp/kos` | KOS列表 |
| `zbmp/competition.html` | `/lumenis/zbmp/competition` | 竞品分析 |
| `zbmp/risk.html` | `/lumenis/zbmp/risk` | 风险中心 |
| `zbmp/reports.html` | `/lumenis/zbmp/reports` | 报告中心 |
| `zbmp/evaluation.html` | `/lumenis/zbmp/evaluation` | 评估 |
| `zbmp/intelligence.html` | `/lumenis/zbmp/intelligence` | 情报 |
| `zbmp/podcast.html` | `/lumenis/zbmp/podcast` | 播客 |
| `zbmp/launch.html` | `/lumenis/zbmp/launch` | 启动页 |

### 3.3 CTH域（10页）
| 页面 | 路由 | 主要组件 |
|------|------|---------|
| `cth/overview.html` | `/lumenis/cth/overview` | KPI×6 / Trend Chart / Industry Donut / Realtime Feed / Risk Board — **已注册Module Registry** |
| `cth/realtime.html` | `/lumenis/cth/realtime` | 实时流 |
| `cth/events.html` | `/lumenis/cth/events` | 事件中心 |
| `cth/risk.html` | `/lumenis/cth/risk` | 风险预警 |
| `cth/xiaohongshu.html` | `/lumenis/cth/xiaohongshu` | 小红书 |
| `cth/reports.html` | `/lumenis/cth/reports` | 报告 |
| `cth/brands.html` | `/lumenis/cth/brands` | 品牌 |
| `cth/industries.html` | `/lumenis/cth/industries` | 业态 |
| `cth/evidence.html` | `/lumenis/cth/evidence` | 证据链 |
| `cth/launch.html` | `/lumenis/cth/launch` | 启动页 |

### 3.4 System域（9页）
| 页面 | 路由 | 主要组件 |
|------|------|---------|
| `system/runtime.html` | `/lumenis/system/runtime` | 运行时控制 |
| `system/collector.html` | `/lumenis/system/collector` | 采集器 |
| `system/browser.html` | `/lumenis/system/browser` | 内置浏览器 — **已添加侧边栏窄屏Sheet自适应** |
| `system/ai.html` | `/lumenis/system/ai` | AI Gateway — **已添加调用日志表格窄屏重排** |
| `system/database.html` | `/lumenis/system/database` | 数据库 |
| `system/security.html` | `/lumenis/system/security` | 安全 |
| `system/settings.html` | `/lumenis/system/settings` | 设置 |
| `system/evaluation.html` | `/lumenis/system/evaluation` | 评估 |
| `system/adaptive_demo.html` | `/lumenis/system/adaptive-demo` | **G Shard新增** 自适应+动效演示页（新模块接入示例） |

---

## 4. UI组件清单（公共组件）

### 4.1 布局组件
| 组件 | CSS类 | 现有响应式 | G Shard升级 |
|------|-------|-----------|------------|
| App Shell | `.zbc-app` | flex固定 | 保留，`.zbc-content`加container-type |
| Sidebar | `.zbc-sidebar` | 240px固定，<768px隐藏+transform | 保留，兼容层覆盖 |
| Topbar | `.zbc-topbar` | 56px固定 | 保留 |
| Content | `.zbc-content` | padding 24px→16px | **加container-type:inline-size，@container驱动内部布局** |
| Mobile Tabbar | `.zbc-tabbar` | <768px显示 | 保留 |

### 4.2 数据展示组件
| 组件 | CSS类 | 现有响应式 | G Shard升级 |
|------|-------|-----------|------------|
| KPI Card | `.zbc-kpi-card` / `.ld-kpi-card` | auto-fit minmax(200px,1fr) | **`.ad-kpi`新组件+兼容层覆盖grid为内容驱动** |
| Card | `.zbc-card` | 无 | **`.ad-card`新组件+hover/focus/press统一Motion** |
| Table | `.zbc-table` / `.ld-table` / `.xj-table` | 无（横向滚动） | **`.ad-table`新组件：Table→Condensed→List→Data Card四级Reflow** |
| Chart | xjViz渲染 | 固定height | **`.ad-chart`新组件+ZBCMotion.updateChart平滑过渡** |
| Grid | `.zbc-grid-2` / `.zbc-grid-2-equal` | 固定2fr/1fr，<768px变1fr | **兼容层改为@container驱动：1fr→2fr/1fr→3fr/1fr** |
| KPI Grid | `.zbc-kpi-grid` | auto-fit+<768px 2col+<480px 1col | **兼容层改为auto-fit minmax(min(100%,180px),1fr)** |
| List | — | 无 | **`.ad-list`新组件** |
| Timeline | — | 无 | **`.ad-timeline`新组件** |
| Detail | — | 无 | **`.ad-detail`新组件（窄屏label/value堆叠）** |
| Evidence | — | 无 | **`.ad-evidence`新组件** |

### 4.3 交互组件
| 组件 | CSS类 | 现有响应式 | G Shard升级 |
|------|-------|-----------|------------|
| Navigation | `.zbc-nav-item` | 无 | **`.ad-nav`新组件+窄容器图标-only** |
| Tabs | `.ld-tabs` / `.zbc-domain-switch` | 无 | **`.ad-tabs`新组件+横向滚动** |
| Toolbar | — | 无 | **`.ad-toolbar`新组件+窄屏次要组隐藏** |
| Filter/Pill | `.zbmp-time-pill` / `.zbc-tag` | 无 | **`.ad-filter`新组件** |
| Button | `.zbc-btn` | 无 | 保留（A Shard已升级） |
| Form | — | 无 | **`.ad-form`新组件+@container多列** |
| Drawer | — | 无 | **`.ad-drawer`新组件（窄屏变底部Sheet）** |
| Modal | — | 无 | **`.ad-modal`新组件（窄屏变全屏Sheet）** |
| Sheet | — | 无 | **`.ad-sheet`新组件** |
| Panel | — | 无 | **`.ad-panel`新组件** |

### 4.4 状态组件
| 组件 | CSS类 | G Shard升级 |
|------|-------|------------|
| Loading/Skeleton | `.zbc-skeleton` / `.zbc-state-loading` | **`.ad-state`新组件+shimmer** |
| Empty | `.zbc-state-empty` | **`.ad-empty`新组件** |
| Error | `.zbc-state-error` | **`.ad-error`新组件** |
| Progress | `.ld-progress` | **`.ad-progress`新组件+ZBCMotion.updateProgress** |
| Badge/Tag | `.zbc-tag` | **`.ad-badge`新组件** |
| Status Dot | `.zbc-dot` / `.ld-dot` | **`.ad-status-dot`新组件+pulse** |

### 4.5 AI/Browser专用组件
| 组件 | G Shard升级 |
|------|------------|
| AI Panel | **`.ad-ai-layout`：Desktop分栏/Tablet堆叠/Mobile Sheet（@container驱动）** |
| Browser Panel | **`.ad-browser-layout`：Desktop三栏/Tablet双栏+Evidence全宽/Mobile单栏** |
| Browser Sidebar | **窄屏变底部Sheet（@container ad-browser-main）** |

---

## 5. Responsive/Motion Dependency Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     Viewport (window.innerWidth)                 │
│  @media 仅用于：reduced-motion / 设备级行为（如Drawer变Sheet）     │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     .zbc-content (主内容区)    │
              │  container-type: inline-size  │
              │  container-name: ad-content   │
              └──────────────┬──────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    @container (min-width)  @container       @container
          │                  │                  │
┌─────────▼────────┐ ┌──────▼───────┐ ┌────────▼────────┐
│ .zbc-grid-2      │ │ .ad-kpi-grid │ │ .ad-table-wrapper│
│ 2fr 1fr (≥720px) │ │ auto-fit     │ │ Table (≥720px)  │
│ 1fr (<720px)     │ │ minmax(180px)│ │ Condensed(560-720)│
└──────────────────┘ └──────────────┘ │ List (360-560px) │
                                       │ DataCard(<360px) │
                                       └──────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Motion System 依赖链                        │
│                                                              │
│  ZBCMotion (adaptive-motion.js)                              │
│    ├── applyPreset() → Web Animations API / CSS transition   │
│    ├── updateKPI() → LDMotion.countUp() (复用)               │
│    ├── updateChart() → LDMotion.drawAreaChart() + 插值过渡    │
│    ├── updateProgress() → LDMotion.fillProgress() (复用)     │
│    ├── staggerIn() → LDMotion.staggerChildren() (复用)       │
│    ├── flashUpdate() → LDMotion.flashUpdate() (复用)         │
│    ├── pulse() → LDMotion.pulse() (复用)                     │
│    └── slideTab() → LDMotion.slideTab() (复用)               │
│                                                              │
│  Motion Priority: P0业务状态 > P1数据变化 > P2用户交互 > P3装饰 │
│  数据驱动：updateKPI/updateChart/updateProgress 检测旧值==新值 → 不触发 │
│  Reduced Motion: 全部动画→直接设置终态，功能不消失              │
│  性能护栏：IntersectionObserver离屏暂停，无rAF风暴             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                   Module Registry 依赖链                       │
│                                                              │
│  ZBCAdaptive.registerModule(contract)                        │
│    ├── module_id / module_type / data_source                 │
│    ├── min_width / preferred_width / max_width               │
│    ├── priority (P0-P3)                                      │
│    ├── responsive_mode (reflow/hide/scale/scroll)            │
│    ├── motion_mode (full/minimal/none)                       │
│    └── visibility (always/desktop/tablet/mobile/conditional) │
│                                                              │
│  ZBCAdaptive.bindModule(module_id, element)                  │
│    ├── 监听 adaptive:sizechange 事件                          │
│    ├── 自动应用 responsive_mode 和 visibility                │
│    └── 调用 contract.onSizeChange(size, width)               │
│                                                              │
│  已注册模块：ZBMP 8个 + CTH 10个 + Demo 7个 = 25个模块         │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 固定width/height/absolute positioning审计

| 位置 | 现有固定值 | G Shard处理 |
|------|-----------|------------|
| `.zbc-sidebar` | width:240px | 保留（侧边栏固定宽度是设计决策） |
| `.zbc-topbar` | height:56px | 保留 |
| `.zbc-search` | width:240px | <768px→140px（已有） |
| `.ld-content-card__cover` | height:160px | 保留（封面图固定高度合理） |
| `.browser-sidebar` | width:320px | **窄屏变底部Sheet，不再固定宽度** |
| KPI value | font-size:24-44px | **改为clamp()流式尺寸** |
| Table td | height:44px | **Reflow后取消固定高度** |

---

## 7. 现有动画/loading/skeleton审计

| 动画 | 位置 | 类型 | G Shard处理 |
|------|------|------|------------|
| shimmer | `.zbc-skeleton` / `.ld-skeleton` | CSS infinite | 保留，reduced-motion时关闭 |
| pulse | `.ld-dot--pulse` | CSS infinite | 保留，reduced-motion时关闭 |
| progress-shimmer | `.ld-progress__bar::after` | CSS infinite | 保留，reduced-motion时关闭 |
| countUp | `LDMotion.countUp` | JS rAF | **复用，ZBCMotion.updateKPI封装，真变才动** |
| drawAreaChart | `LDMotion.drawAreaChart` | JS stroke-dashoffset | **复用，ZBCMotion.updateChart加插值过渡** |
| fillProgress | `LDMotion.fillProgress` | JS width transition | **复用，ZBCMotion.updateProgress封装** |
| stagger | `LDMotion.staggerChildren` | JS setTimeout | **复用，ZBCMotion.staggerIn封装** |
| xjViz.animateNumber | `xujing-viz.js` | JS rAF | 保留（现有页面使用） |
| browser-spin | `browser.html` | CSS infinite | 保留，reduced-motion时关闭 |

---

## 8. Design Token合并状态

| Token类别 | 现有来源 | G Shard新增 | 冲突处理 |
|-----------|---------|------------|---------|
| 颜色 | `--l-*` / `--d-*` / `--ld-*` | 无新增（复用） | 无冲突 |
| 圆角 | `--ld-radius-*` | `--ad-radius-sm/md/lg/xl` | 追加，不覆盖 |
| 间距 | 无统一token | `--ad-space-xs/sm/md/lg/xl/2xl` | 新增 |
| 密度 | 无 | `--ad-density-compact/normal/comfortable` | 新增 |
| 字体 | `--ld-text-kpi*` / `--ld-text-eyebrow` | `--ad-font-display/heading/title/body/caption/metric/label`（clamp流式） | 追加，不覆盖 |
| 动效 | `--ld-motion-*` / `--ld-ease-*` | `--ad-motion-*` / `--ad-ease-*` | 追加，不覆盖 |
| 断点 | 无（硬编码768/480） | `--ad-bp-narrow/medium/wide/ultrawide` | 新增，基于容器非视口 |

---

## 9. 结论

- **现有UI组件总数**：约30类公共组件
- **G Shard新增自适应组件**：20类（`.ad-*`前缀）
- **兼容层覆盖**：`.zbc-grid-2` / `.zbc-grid-2-equal` / `.zbc-kpi-grid` / `.zbc-card__body` 等现有类自动获得Container Query驱动的自适应能力
- **无三套页面**：所有页面共用同一套base.html和组件，通过Container Query自动重排
- **无模块自定义breakpoint**：统一使用`--ad-bp-*` token和@container
- **动效统一**：所有新动效通过ZBCMotion统一API，复用LDMotion底层能力
