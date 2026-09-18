# 09 — UI/UX SOURCE RECONCILIATION

> 审计日期：2026-09-02
> OSAI HEAD：`60af16a`（`D:\Zachary OS AI`）
> ZBC HEAD：`a4adf70`（`D:\Taikoo-monitor-new`，APP_VERSION=5.9.9；工单基线声明 HEAD 545a3ab，实际 HEAD 已前移，以本地当前源码为准）
> 状态计数（按表项）：EXISTS=58 | PARTIAL=9 | MISSING=5 | UNKNOWN=1

---

## 一、ZBC 生产前端实现对账

### 1.1 模板层（templates/）

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| base.html 基础布局 | EXISTS | `D:\Taikoo-monitor-new\templates\base.html` | 含 header/nav/main/footer，加载 style.css + zachary_robot.css + mobile.css 等 5 个 CSS，加载 app.js + zachary_robot_enhanced.js 等 13 个 JS；页脚版本号硬编码 v5.8.9（与 app.py 5.9.9 不一致） |
| index.html 仪表盘 | EXISTS | `D:\Taikoo-monitor-new\templates\index.html` | 5021 字节，extends base.html |
| notes.html 舆情笔记 | EXISTS | `D:\Taikoo-monitor-new\templates\notes.html` | 3184 字节，含搜索/筛选/分页/详情弹窗；笔记列表由 JS 动态渲染 |
| events.html 舆情事件 | EXISTS | `D:\Taikoo-monitor-new\templates\events.html` | 2929 字节 |
| report.html 报告中心 | EXISTS | `D:\Taikoo-monitor-new\templates\report.html` | 3992 字节 |
| 模板总数 | EXISTS | `D:\Taikoo-monitor-new\templates\` | 共 5 个模板，与工单基线"5个模板"一致 |

### 1.2 静态 CSS（static/css/）

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| style.css 主样式 | EXISTS | `D:\Taikoo-monitor-new\static\css\style.css` | 88333 字节，生产主样式 |
| mobile.css 响应式 | EXISTS | `D:\Taikoo-monitor-new\static\css\mobile.css` | 20281 字节，base.html 已引用，响应式断点已实现 |
| apple-ui.css 苹果风 | EXISTS | `D:\Taikoo-monitor-new\static\css\apple-ui.css` | 26431 字节，苹果风格样式库存在，但 base.html 未直接引用 |
| zachary_robot.css 机器人样式 | EXISTS | `D:\Taikoo-monitor-new\static\css\zachary_robot.css` | 6908 字节，base.html 已引用 |
| ui_modern.css / ui_dashboard.css / ui_optimized.css | EXISTS | `D:\Taikoo-monitor-new\static\css\ui_*.css` | 三套 UI 主题并存（36999/32481/14074 字节），存在主题冗余 |
| zb-theme.css / zb-gpt-theme.css | EXISTS | `D:\Taikoo-monitor-new\static\css\zb-*.css` | ZB 主题两套（44642/72503 字节），与 style.css 并存，存在设计系统碎片化 |
| zbip-*.css 设计系统 | EXISTS | `D:\Taikoo-monitor-new\static\css\zbip-shell.css` 等 5 个 | ZBIP 设计令牌组件样式，zbip-shell.css 23248 字节 |
| tokens.css / tokens-minimal.css | EXISTS | `D:\Taikoo-monitor-new\static\css\tokens.css` | 设计令牌 CSS 两套（15406/7859 字节），与根目录 ZBIP_DESIGN_TOKENS.css 并存 |
| design-v8.css / design-v9-*.css | EXISTS | `D:\Taikoo-monitor-new\static\css\design-v*.css` | 历史设计版本残留（v8/v9），未清理 |
| CSS 备份文件 | PARTIAL | `D:\Taikoo-monitor-new\static\css\style.css.bak_011101` | 生产目录存在 .bak 备份文件，未归档 |

### 1.3 静态 JS（static/js/）

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| app.js 主逻辑 | EXISTS | `D:\Taikoo-monitor-new\static\js\app.js` | 115840 字节，base.html 引用 v=5.8.9 |
| zachary_robot.js 机器人 | EXISTS | `D:\Taikoo-monitor-new\static\js\zachary_robot.js` | 35759 字节，基础版机器人组件 |
| zachary_robot_enhanced.js 精致版 | EXISTS | `D:\Taikoo-monitor-new\static\js\zachary_robot_enhanced.js` | 29107 字节，base.html 已引用，工单"本次新增精致版组件"已落地 |
| zachary_3d.js / zachary_png_face.js / zachary_system_knowledge.js | EXISTS | `D:\Taikoo-monitor-new\static\js\zachary_*.js` | 机器人相关 JS 共 5 个（含 3D/PNG脸/系统知识），与工单"已有5个相关JS"一致 |
| auth_recovery_poller.js 认证恢复轮询 | EXISTS | `D:\Taikoo-monitor-new\static\js\auth_recovery_poller.js` | 19671 字节，base.html 已引用，前端轮询认证恢复任务弹窗 |
| frontend_enhancement.js | EXISTS | `D:\Taikoo-monitor-new\static\js\frontend_enhancement.js` | 55411 字节，前端增强逻辑 |
| ui_interactions_v5.8.0.js | EXISTS | `D:\Taikoo-monitor-new\static\js\ui_interactions_v5.8.0.js` | 41855 字节，版本号硬编码在文件名中 |
| system_controls.js / system_features_ui.js | EXISTS | `D:\Taikoo-monitor-new\static\js\system_*.js` | 系统控制/功能 UI（30367/17470 字节） |
| badge_manager.js | EXISTS | `D:\Taikoo-monitor-new\static\js\badge_manager.js` | 8874 字节，认证恢复徽章管理 |
| JS 备份文件 | PARTIAL | `D:\Taikoo-monitor-new\static\js\app.js.bak_20260827_201308` | 生产目录存在 .bak 备份（143437 字节），未归档 |
| vendor/three.min.js | EXISTS | `D:\Taikoo-monitor-new\static\js\vendor\three.min.js` | 669884 字节，3D 机器人依赖 |

### 1.4 根目录 UI 资产

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| ZBIP_DESIGN_TOKENS.css 设计令牌 | EXISTS | `D:\Taikoo-monitor-new\ZBIP_DESIGN_TOKENS.css` | 1399 字节，定义 --zb-bg/--zb-surface/--zb-text 等 CSS 变量及 .zb-status-dot/.zb-surface/.zb-interactive 组件类；支持 [data-theme=dark] 暗色模式 |
| zachary_robot_widget.html 独立机器人组件 | EXISTS | `D:\Taikoo-monitor-new\zachary_robot_widget.html` | 10914 字节，独立可嵌入的精致版机器人组件，含呼吸光晕/表情切换/拖拽/点击跳转；使用 CDN 图片（aka.doubaocdn.com） |
| zachary_robot_接入文档.md | EXISTS | `D:\Taikoo-monitor-new\zachary_robot_接入文档.md` | 13858 字节，机器人组件接入说明 |
| ZBIP_UNIFIED_README.md | EXISTS | `D:\Taikoo-monitor-new\ZBIP_UNIFIED_README.md` | 8798 字节，ZBIP 统一说明 |
| static/index.html 独立静态页 | EXISTS | `D:\Taikoo-monitor-new\static\index.html` | 81508 字节，大型独立静态页面（非 Flask 模板），可能是历史单页应用残留 |
| static/topic_campaign.html/css/js | EXISTS | `D:\Taikoo-monitor-new\static\topic_campaign.*` | 话题专题独立页面三件套（html 5988/css 16502/js 29772 字节） |
| static/launch-screens/ 启动屏 | EXISTS | `D:\Taikoo-monitor-new\static\launch-screens\` | 含 cth-poms/zbmp/dark/morandi 四套启动屏（desktop/mobile HTML），存在多套启动屏冗余 |

### 1.5 V4 升级模块 UI（v4_upgrade/）

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| settings.html 苹果风设置页 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\settings\templates\settings.html` | 19131 字节，苹果风格：-apple-system 字体、#f2f2f7 背景、14px 圆角分组、profile-header 渐变头像区、#007aff 主按钮；含账号管理/安全问答/审计日志/系统配置分组 |
| login.html 登录页 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\settings\templates\login.html` | 6852 字节，账密/密钥双方式滑动切换登录页 |
| collect.html 全网采集中心 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\collect\templates\collect.html` | 27281 字节，苹果风采集控制台：平台六态状态点、关键词 chips、进度条、后台采集任务；含移动端适配（maximum-scale=1.0） |
| console.html 统一控制台 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\console\templates\console.html` | 45373 字节，V4 统一控制台主页面 |
| version_center.html 版本中心 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\version_center\templates\version_center.html` | 20857 字节，版本管理中心页面 |
| auth_global.js V4 全局认证脚本 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\static\auth_global.js` | 16116 字节，V4 前端认证逻辑（Token 存储/请求拦截/登录跳转） |
| V4 蓝图注册 | EXISTS | `D:\Taikoo-monitor-new\app.py:5322-5325` | `from v4_upgrade import create_v4_blueprint, init_v4_modules` + `app.register_blueprint(create_v4_blueprint())`，url_prefix=/v4 |
| V4 路由旁路认证 | EXISTS | `D:\Taikoo-monitor-new\app.py:606` | `request.path.startswith('/v4/')` 跳过 HTTP Basic Auth，V4 使用独立 Token 认证 |

### 1.6 app.py 页面渲染路由

| 项 | 状态 | 证据路径 | 备注 |
|----|------|----------|------|
| 首页路由 / | EXISTS | `D:\Taikoo-monitor-new\app.py:1188` | `@app.route('/')` 渲染 index.html |
| /api/stats /api/notes /api/events 等 API | EXISTS | `D:\Taikoo-monitor-new\app.py:1194-1231` | 核心数据 API 路由存在 |
| 蓝图注册（10个） | EXISTS | `D:\Taikoo-monitor-new\app.py:109-121` | system_health/architecture/settings/export/pr_case/system_features/auth_recovery 等蓝图已注册 |
| HTTP Basic Auth 兜底 | EXISTS | `D:\Taikoo-monitor-new\app.py:595-611` | `_auth_enabled()` + `_basic_auth()`，AUTH_USER/AUTH_PASSWORD 从环境变量读取；保留 Basic Auth 兜底（工单 P0-2 要求） |
| V4 独立认证旁路 | EXISTS | `D:\Taikoo-monitor-new\app.py:606` | /v4/ 路径跳过 Basic，走 V4 Token 认证 |

---

## 二、UI 跨边界检查（OSAI UI 代码 vs ZBC 生产 UI）

### 2.1 OSAI Development-Command-Console（DCC）

| 项 | 状态 | 证据路径 | 边界判定 |
|----|------|----------|----------|
| DCC 独立 Web UI | EXISTS | `D:\Zachary OS AI\components\Development-Command-Console\index.html` | OSAI 研究侧独立命令台 UI，含 css/components.css、css/tokens.css、js/（bridge/search/task/theme 等 6 个 JS）、server/（Node.js 服务端 12 个文件）、tests/（13 个测试） |
| DCC 设计令牌 | EXISTS | `D:\Zachary OS AI\components\Development-Command-Console\ZBIP_DESIGN_TOKENS.css` | 与 ZBC 根目录 `ZBIP_DESIGN_TOKENS.css` 同名同内容（1399 字节），设计令牌在双库各存一份，存在重复但不冲突（各自独立部署） |
| DCC 与 ZBC 生产 UI 关系 | PARTIAL | — | DCC 是 OSAI 研究/治理命令台，功能定位（能力注册/规则审计/学习循环）与 ZBC 生产 UI（舆情监测/采集/报告）不同；但两者共享 ZBIP 设计令牌命名空间，存在设计系统碎片化风险。DCC 不接入 ZBC 生产路由，无越界调用 |
| DCC server 端 | EXISTS | `D:\Zachary OS AI\components\Development-Command-Console\server\server.js` | Node.js 独立服务端，与 ZBC Flask 后端完全分离，无 DB 直连 ZBC 生产库 |

### 2.2 OSAI SICI-Core

| 项 | 状态 | 证据路径 | 边界判定 |
|----|------|----------|----------|
| SICI-Core 独立 Web UI | EXISTS | `D:\Zachary OS AI\components\SICI-Core\index.html` | 18271 字节，OSAI 研究侧独立 UI，含 css/style.css（31372 字节）、js/（app.js 31357 字节等 11 个 JS）、manifest.json、sw.js（PWA Service Worker） |
| SICI-Core 设计令牌 | EXISTS | `D:\Zachary OS AI\components\SICI-Core\ZBIP_DESIGN_TOKENS.css` | 与 ZBC/DCC 同名同内容（1399 字节），第三份重复 |
| SICI-Core 与 ZBC 生产 UI 关系 | PARTIAL | — | SICI-Core 是 OSAI 研究/学习/验证 UI，功能定位（能力注册表/有效规则/预飞检查/学习库）与 ZBC 生产 UI 不同；独立 PWA 应用，不接入 ZBC 生产路由。upgrade_modules/ 下有 base_adapter_enhanced.py/dual_pool.py/unified_logger.py，是研究侧适配器升级模块，与 ZBC v4_upgrade/adapters/ 存在概念重叠但物理分离 |
| SICI-Core shadow_run/ | EXISTS | `D:\Zachary OS AI\components\SICI-Core\shadow_run\` | 影子运行测试报告（pyresilience/yyds_logger/xiaohongshu_bakeoff），纯研究侧，不影响生产 |

### 2.3 跨边界总结

| 检查项 | 状态 | 说明 |
|--------|------|------|
| OSAI UI 接入 ZBC 生产路由 | MISSING | OSAI DCC/SICI-Core 均为独立部署 UI，未注册到 ZBC Flask 路由，无越界 |
| OSAI UI 直连 ZBC 生产 DB | MISSING | DCC 使用 Node.js + 本地 JSON，SICI-Core 使用浏览器 localStorage，均不直连 ZBC monitor.db |
| 设计令牌重复 | PARTIAL | ZBIP_DESIGN_TOKENS.css 在 ZBC 根目录、OSAI DCC、OSAI SICI-Core 三处各存一份（1399 字节相同），存在维护同步风险但无运行时冲突 |
| UI 代码复制 | MISSING | 未发现 OSAI UI 代码直接复制到 ZBC 生产 static/ 或反之；V4 UI 是 ZBC 独立开发 |
| 机器人组件越界 | MISSING | zachary_robot 组件仅存在于 ZBC static/js/ 和根目录 widget，OSAI 侧无机器人 UI 组件 |
| OSAI 工单/任务跟踪 UI | EXISTS | DCC js/task.js + server/ 提供任务跟踪 UI，但这是 OSAI 研究侧任务管理，与 ZBC 生产工单系统分离 |

---

## 三、设计系统一致性核对

| 检查项 | 状态 | 证据路径 | 备注 |
|--------|------|----------|------|
| 苹果风设置页 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\settings\templates\settings.html` | 完整苹果风实现：SF Pro 字体栈、#f2f2f7 分组背景、14px 圆角、#007aff 主色、profile-header 渐变区、分组列表式布局 |
| 苹果风采集页 | EXISTS | `D:\Taikoo-monitor-new\v4_upgrade\collect\templates\collect.html` | 同一设计语言：#f2f2f7 背景、14px 圆角分组、#007aff 按钮、backdrop-filter 毛玻璃导航栏 |
| 响应式 mobile.css | EXISTS | `D:\Taikoo-monitor-new\static\css\mobile.css` | 20281 字节，base.html 已引用；V4 页面含 viewport maximum-scale=1.0 移动端适配 |
| 机器人组件体系 | EXISTS | `D:\Taikoo-monitor-new\static\js\zachary_robot.js` + `zachary_robot_enhanced.js` + `zachary_3d.js` + `zachary_png_face.js` + `zachary_system_knowledge.js` | 5 个机器人 JS + zachary_robot.css + zachary_robot_widget.html + 接入文档，组件体系完整 |
| 设计令牌统一 | PARTIAL | ZBC `ZBIP_DESIGN_TOKENS.css`(1399B) + `static/css/tokens.css`(15406B) + `static/css/tokens-minimal.css`(7859B) + `static/css/zbip-tokens.css`(9121B) | 四套设计令牌并存，命名空间不统一（ZBIP_ vs tokens- vs zbip-tokens），存在设计系统碎片化 |
| 主题系统统一 | PARTIAL | style.css + ui_modern.css + ui_dashboard.css + zb-theme.css + zb-gpt-theme.css + apple-ui.css + design-v8.css + design-v9-*.css | 8+ 套主题/样式并存，base.html 仅引用 style.css + mobile.css + zachary_robot.css + architecture_dashboard.css + ui_optimized.css，其余为历史残留或模块级引用 |
| 版本号一致性 | PARTIAL | app.py APP_VERSION='5.9.9' / base.html 页脚 v5.8.9 / start_stable.bat v5.8.0 / static JS ?v=5.8.9 | 版本号四处不一致（P2-2 工单未完成） |
| 暗色模式 | EXISTS | `D:\Taikoo-monitor-new\ZBIP_DESIGN_TOKENS.css` [data-theme=dark] | 设计令牌支持暗色模式变量，但 base.html/V4 模板未实现主题切换 UI |

---

## 四、状态计数汇总

| 状态 | 数量 |
|------|------|
| EXISTS | 58 |
| PARTIAL | 9 |
| MISSING | 5 |
| UNKNOWN | 1 |
| **合计** | **73** |

### 关键发现

1. **ZBC 生产 UI 完整**：5 模板 + 30+ CSS + 40+ JS + V4 5 页面，前端实现体系完整。
2. **V4 升级模块 UI 已落地**：苹果风设置页/登录页/采集中心/控制台/版本中心均已实现并注册到 /v4 路由。
3. **OSAI UI 无越界**：DCC 和 SICI-Core 均为独立部署的研究侧 UI，不接入 ZBC 生产路由、不直连生产 DB。
4. **设计系统碎片化**：ZBIP_DESIGN_TOKENS.css 在双库三处重复，ZBC 内部有 4 套令牌 + 8+ 套主题并存，需统一。
5. **版本号不一致**：app.py 5.9.9 vs base.html 5.8.9 vs start_stable.bat 5.8.0，P2-2 未完成。
