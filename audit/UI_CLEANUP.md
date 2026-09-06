# UI Cleanup Audit — 旧UI代码清理审计

> 日期：2026-09-07
> 执行者：OrganizerAgent (A Shard)
> 触发：用户明确要求"UI/UX升级完成后，旧的UI代码必须删掉，防止覆盖显示不全以及不更新"

## 一、清理原则

1. **删除前审计**：检查每个旧UI文件是否被新UI完全替代、是否还有其他模块引用、删除后是否有路由404
2. **完全替代→DELETE**：新UI已实现相同功能且测试通过
3. **生产依赖→KEEP**：旧UI仍被生产路由引用且新UI未就绪
4. **不删除生产核心**：舆情监测/风险预警/事件中心等仍在使用的页面
5. **不删除数据库/配置/采集相关代码**

## 二、已删除文件清单

### 2.1 旧CSS文件（10个，被lumenis-global-design.css替代）

| 文件 | 大小 | 删除原因 |
|------|------|----------|
| static/css/lumenis.css | - | 旧设计系统聚合器，@import所有下方文件，仅被_preview引用 |
| static/css/lumenis-tokens.css | - | 旧设计令牌，仅被lumenis.css @import |
| static/css/lumenis-tokens-v2.css | - | 旧设计令牌v2，仅被lumenis.css @import |
| static/css/lumenis-reset.css | - | 旧reset，仅被lumenis.css @import |
| static/css/lumenis-layout.css | - | 旧布局，仅被lumenis.css @import |
| static/css/lumenis-components.css | - | 旧组件，仅被lumenis.css @import |
| static/css/lumenis-core-components.css | - | 旧核心组件，仅被lumenis.css @import |
| static/css/lumenis-motion.css | - | 旧动效，被lumenis-motion-engine.js替代 |
| static/css/lumenis-responsive.css | - | 旧响应式，仅被lumenis.css @import |
| static/css/xujing-dual-domain.css | - | 未被任何模板引用 |

### 2.2 旧模板目录（6个，21个文件，被双域模板替代）

| 目录 | 文件数 | 删除原因 |
|------|--------|----------|
| templates/home/ | 1 | command_home.html，独立遗留页面，不继承base.html |
| templates/intelligence/ | 7 | workspace/skill_hub/models/evidence/evaluation/agent_center/library，独立遗留 |
| templates/production/ | 6 | overview/public_opinion/risk/monitoring/cases/reports，独立遗留 |
| templates/operations/ | 4 | index/runtime/permissions/repository，独立遗留 |
| templates/research/ | 2 | workspace/findings，独立遗留 |
| templates/_preview/ | 1 | command-home-preview.html，预览文件，仅引用旧lumenis.css |

### 2.3 旧路由（20条，从lumenis_frontend.py移除）

移除的路由：
- `/lumenis/` (改为重定向到/lumenis/cth/overview)
- `/lumenis/intelligence`
- `/lumenis/production`
- `/lumenis/production/public-opinion`
- `/lumenis/production/risk`
- `/lumenis/operations`
- `/lumenis/intelligence/skills`
- `/lumenis/intelligence/agents`
- `/lumenis/intelligence/evaluation`
- `/lumenis/research`
- `/lumenis/intelligence/models`
- `/lumenis/intelligence/evidence` (页面路由，API路由/api/intelligence/evidence保留)
- `/lumenis/production/monitoring`
- `/lumenis/production/cases`
- `/lumenis/production/reports`
- `/lumenis/research/findings`
- `/lumenis/operations/runtime`
- `/lumenis/operations/permissions`
- `/lumenis/operations/repository`

lumenis_frontend.py从764行缩减到632行，移除132行。

### 2.4 测试文件更新

- `tests/test_lumenis_frontend_foundation.py`：完全重写，从测试旧lumenis CSS/模板改为测试新设计系统+双域模板+动效引擎

## 三、保留文件清单（生产UI）

### 3.1 保留的CSS（4个）

| 文件 | 用途 |
|------|------|
| static/css/zbc-design-v1.1.css | 基础设计（色彩/排版/组件） |
| static/css/zbc-layout-v1.1.css | 布局（侧边栏/顶栏/内容区） |
| static/css/xujing-core.css | 核心样式 |
| static/css/lumenis-global-design.css | **新增**全局设计系统（8素材设计语言） |

### 3.2 保留的模板（双域生产UI）

| 目录 | 用途 |
|------|------|
| templates/base.html | 基础模板（已接入新设计系统+动效引擎） |
| templates/zbmp/ | ZBMP域（11页） |
| templates/cth/ | CTH域（10页，含升级后的xiaohongshu.html） |
| templates/system/ | System域（7页） |
| templates/auth/ | 登录页 |
| templates/auth_recovery_modal.html | Auth恢复弹窗 |

### 3.3 保留的路由

- `/lumenis/healthz`
- `/lumenis/api/skills/*` (4条API路由)
- `/lumenis/api/intelligence/evidence` (API路由)
- `/lumenis/zbmp/*` (11条)
- `/lumenis/cth/*` (10条)
- `/lumenis/system/*` (7条)
- `/api/domain/*` (domain_api_bp, 4条)

## 四、验证结果

1. **healthz**: 200 OK `{"ok":true,"service":"taikoo-monitor","version":"5.9.9"}`
2. **前端基础测试**: `tests/test_lumenis_frontend_foundation.py` 1 passed in 0.48s
3. **Jinja2模板语法**: base.html, cth/xiaohongshu.html, zbmp/content.html 全部通过
4. **无render_template引用已删除模板**: 验证通过
5. **旧CSS无残留引用**: base.html不再引用lumenis.css
6. **根路径重定向**: `/lumenis/` → 302重定向到`/lumenis/cth/overview`

## 五、新增UI资产

### 5.1 全局设计系统
- `static/css/lumenis-global-design.css` (20KB)：10大设计语言元素（大圆角卡片/胶囊导航/渐变图表/大数字KPI/薄荷绿主色/毛玻璃浮层/线性图标/深色卡片/pill标签/圆角进度条）+ 平台品牌色 + 动效令牌 + 响应式

### 5.2 动效引擎
- `static/js/lumenis-motion-engine.js` (15KB)：数字count-up/渐变面积图绘制/进度条填充/卡片级联进入/状态脉冲/数据更新闪烁/导航滑动 + IntersectionObserver懒触发 + prefers-reduced-motion支持

### 5.3 页面升级
- `templates/cth/xiaohongshu.html`：平台品牌头部(小红书红)+KPI大数字count-up+表格/卡片双视图切换+pill标签+动画进度条
- `templates/zbmp/content.html`：平台品牌色指示器(小红书/抖音/B站/微博)+KPI count-up+平台原生字段显示
- `templates/base.html`：接入lumenis-global-design.css + lumenis-motion-engine.js

## 六、风险与回滚

- 所有删除文件在Git中可恢复（分支lumenis-dual-domain-v3）
- 如发现旧路由仍被外部引用，可从Git恢复lumenis_frontend.py对应路由
- 新设计系统为增量叠加，不修改zbc-design-v1.1.css/zbc-layout-v1.1.css，可随时移除lumenis-global-design.css回退
