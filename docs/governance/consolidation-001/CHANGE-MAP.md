# ZBC-UNIFIED-PRODUCTION-CONSOLIDATION-001 变更地图

## TASK 基本信息

| 字段 | 内容 |
|------|------|
| **TASK ID** | ZBC-UNIFIED-PRODUCTION-CONSOLIDATION-001 |
| **原始HEAD** | 841ffa9 (v5.9.9) |
| **Checkpoint HEAD** | 39b0ea9 |
| **目标** | 架构收敛 + ZBMP UI/UX升级 + Runtime/Staging + 测试 + Release Gate |
| **UI方向** | GPT & Codex化：黑白灰基础+极少量语义色+小状态点+Token化+低装饰+高信息密度+强层级+精准交互 |
| **原则** | 不重写、不换技术栈、不删生产数据、不破坏后端API、不阻塞CTH上线 |

## 变更范围

### MODIFY（修改）
- static/css/zb-theme.css - 重写为唯一权威主题层（ZBMP Design Token System）
- static/index.html - 调整CSS加载顺序，确保zb-theme.css最后加载
- static/js/app.js - 修复右侧AI面板显示逻辑（如需要）
- static/css/layout-minimal.css - 整合到zb-theme.css（如需要）

### ADD（新增）
- docs/governance/consolidation-001/CHANGE-MAP.md - 本变更地图
- docs/governance/consolidation-001/FINAL-AUDIT.md - 最终审计
- docs/governance/consolidation-001/FINAL-UI-QA.md - UI质量检查
- docs/governance/consolidation-001/FINAL-RUNTIME-REPORT.md - Runtime报告

### READ ONLY（只读，不修改）
- app.py - 核心业务逻辑
- database.py - 数据库操作
- risk_engine.py - 风险引擎
- subject_classifier.py - 主体分类
- event_graph.py - 事件图谱
- collector*.py - 采集器
- data/monitor.db - 生产数据库

### DO NOT TOUCH（绝对不碰）
- 核心主体口径（SUBJECT_WORDS / subject_hit()）
- 时间口径（publish_datetime / captured_at）
- 历史生产数据
- 风险核心判断
- 事件核心判断
- 报告核心判断
- 采集异常处理（不得伪装成0条）
- 运行中的8200/8201/9222进程

## 执行阶段

### Phase A: Design Token System（设计令牌系统）
- [ ] 建立ZBMP Design Token（颜色/间距/圆角/字体/阴影/状态色）
- [ ] 重写zb-theme.css为唯一权威主题层
- [ ] 确保所有组件使用Token，禁止硬编码

### Phase B: Component System（组件系统）
- [ ] Button（主/次/危险/禁用）
- [ ] StatusDot（小圆点状态指示器）
- [ ] Badge（标签/徽章）
- [ ] Card/Panel（卡片/面板）
- [ ] Input/Select/Search（表单控件）
- [ ] Table（数据表格）
- [ ] Tabs（标签页）
- [ ] Drawer/Modal（抽屉/弹窗）
- [ ] Toast（轻提示）
- [ ] EmptyState/Loading/ErrorState（空/加载/错误状态）
- [ ] Timeline（时间线）
- [ ] Metric（指标卡片）

### Phase C: Information Architecture（信息架构）
- [ ] 导航重构（Workspace → Brand → Project → Campaign → Monitoring → Content → Events → Insights → Reports → AI → Settings）
- [ ] 首页升级（Summary + Status + Recent Activity + Action，不是20个KPI卡片）
- [ ] 列表页统一（Toolbar + Search + Filter + Sort + Table + Pagination）
- [ ] 详情页统一（Header + Status + Summary + Main Data + Timeline + Relations + Evidence + Actions）

### Phase D: 修复与清理
- [ ] 修复右侧AI洞察面板显示问题
- [ ] 移除3D机器人等花哨装饰（zachary_robot相关）
- [ ] 移除渐变背景/大阴影/彩色卡片海洋
- [ ] 统一按钮颜色（深灰主按钮，不再用蓝色）
- [ ] 状态点统一为小圆点（green/amber/red/blue/gray）

### Phase E: 响应式与适配
- [ ] 390px（手机）
- [ ] 430px（大屏手机）
- [ ] 768px（平板）
- [ ] 1024px（小屏桌面）
- [ ] 1280px（标准桌面）
- [ ] 1440px（大屏桌面）
- [ ] 检查横向滚动/Overflow/导航/表格/弹窗/图表

### Phase F: 前后端适配
- [ ] 检查所有API路由是否正常
- [ ] 检查UI需要的API是否存在
- [ ] 复用现有API，不新增不必要的端点
- [ ] 检查权限/Feature Gate

### Phase G: 测试与回归
- [ ] Syntax检查
- [ ] Import检查
- [ ] Startup检查
- [ ] Health检查
- [ ] Database检查
- [ ] API检查
- [ ] Routes检查
- [ ] 核心业务检查
- [ ] Frontend检查
- [ ] E2E检查
- [ ] Browser Runtime检查
- [ ] Restart检查
- [ ] Recovery检查
- [ ] Regression检查

### Phase H: 最终审计与Release Gate
- [ ] FINAL-AUDIT.md
- [ ] FINAL-UI-QA.md
- [ ] FINAL-RUNTIME-REPORT.md
- [ ] FINAL-DEPENDENCY-REPORT.md
- [ ] FINAL-CLEANUP-REPORT.md
- [ ] FINAL-RELEASE-REPORT.md
- [ ] Release Gate检查（P0=0, 核心业务PASS, DB PASS, API PASS, UI PASS, E2E PASS, Runtime PASS, Restart PASS, Backup PASS, Rollback PASS, Staging PASS）

## 回滚方案

- Checkpoint: 39b0ea9
- 原始HEAD: 841ffa9
- 回滚命令: `git reset --hard 39b0ea9` 或 `git revert <commit-sha>`
- 所有修改集中在static/css/和static/index.html，不涉及业务代码和数据库

## 风险评估

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| CSS覆盖导致页面样式异常 | 中 | 小步提交，每步测试，保留回滚点 |
| 右侧AI面板修复影响其他功能 | 低 | 只修改显示逻辑，不修改数据逻辑 |
| 移除3D机器人影响用户体验 | 低 | 用户明确要求极简风格，移除花哨装饰 |
| 响应式适配不完整 | 中 | 按6个断点逐一测试 |
| 前后端API不匹配 | 低 | 复用现有API，不新增端点 |

## 核心业务红线（绝对不得修改）

- SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS
- subject_hit() / _subject_sql_and_values()
- aggregate_events() / build_daily_report()
- publish_datetime / captured_at
- 历史数据库 / 历史生产数据
- 风险核心判断 / 事件核心判断 / 报告核心判断
- 采集异常不得伪装成0条
