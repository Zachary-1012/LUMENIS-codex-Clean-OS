# UI 设计系统 + 浏览器会话保活｜GitHub 研究（2026-09-03）

> 目的：为 ZBIP 快捷按钮层级 / 状态点语义 / RedNote 登录保活提供外部先例依据
> 全部为架构/模式学习，未复制任何第三方代码

## A. 按钮层级（Button Hierarchy）模式

### 1. Oxi Design System（github.com/project-oxi/.github/blob/main/DESIGN.md）
- Primary/Secondary/Ghost 三级：Primary = "Single CTA per screen"（每屏唯一主操作）
- Primary：`bg-interactive-primary` + hover 降透明度 90% + active 80%，禁用 opacity-40
- 启示：**每屏一个深色主按钮**，其余为次要。ZBIP 主页"进入智能问答"应为主按钮。

### 2. fission-theme（docs.rs/fission-theme）
- ButtonHierarchy 枚举：Primary / SecondaryColor / SecondaryGray / TertiaryColor / TertiaryGray / LinkColor / Elevated
- 启示：按钮是**层级系统**而非单个样式，颜色+灰度双维度区分

### 3. ByteCap / Kanban Design System
- Primary：h-10 + shadow + hover 变深（bg-indigo-600）+ scale 0.98 按压反馈
- transition 0.15s ease
- 启示：**hover 变深 + 按压 scale 0.98 + 微阴影** 是最佳微交互

### 4. 37C3 styleguide
- Flat buttons，secondary = 彩色文字 + 深色 border
- 启示：次要按钮保持低调（白底/浅灰字）

### ZBIP 落地（已完成）
- `.zb-chip[data-q="cockpit"]`（进入智能问答）= #1C1917 深底白字 + hover #292524 + scale 0.98
- 其余 3 个 chip 保持白底灰字
- 实测：primaryBg rgb(28,25,23)、其余 rgb(255,255,255) 通过

## B. 状态点（Status Indicator）模式

### Oxi Design System 语义色
- 交互语义色体系（interactive-primary 等）+ status 语义
- 启示：状态用**语义色**表达，而非单一颜色

### ZBIP 六语义状态点体系（已建立，zbip-shell.css）
- `.zb-dot` + `.zb-dot-ok(绿)/warn(黄)/risk(橙)/crit(红)/info(蓝)/unknown(灰)`
- 外圈光晕（box-shadow ring）+ `.zb-dot-pulse` 呼吸动画
- 实测：zb-dot-risk = rgb(249,115,22) #f97316 通过
- 遵循用户"彩色小圆点标识重要程度"设计需求

## C. 浏览器会话保活（Session Keepalive）模式

### 1. x-session-keeper（github.com/29-Cu/x-session-keeper）★最贴近
- **self-heal**：systemd Restart=always + 夜间重启 timer（浏览器永不僵死）
- **session-watch**：每隔几分钟通过 CDP **只读检查**是否仍登录；登出/僵死 → 发通知
- 启示：ZBIP RedNoteLoginKeepalive 的 should_login_today / check_login_status / mark_login_success 与该模式一致；可补充"定时只读检查 + 登出通知"

### 2. sessionkeeper（github.com/dragoshont/sessionkeeper）
- 定时唤醒，交换即将过期的凭证；只在**真正失效**时通知用户登录
- 启示：登录动作应**人工触达**（扫码），系统只做检测与提醒——与"系统内弹窗扫码"一致

### 3. agent-browser / playwright-cli-sessions（github.com/Marshall-Sun/agent-browser）
- `--session-name` 自动保存/恢复 cookies+localStorage；持久 profile + CDP 附加
- 启示：持久 profile 是会话存续的基础（ZBIP 已用 CDP 9222/9223 持久浏览器）

### 4. claude-browser-crawl-cdp（github.com/gruncode/claude-browser-crawl-cdp）
- 真实持久登录浏览器 + CDP 附加，不碰个人浏览器，站点视为"真实用户"
- 启示：印证 ZBIP CDP 持久浏览器方案的正确性

### ZBIP 现状对照
- ✅ CDP 9222/9223 在线（持久 profile）
- ✅ RedNoteLoginKeepalive（check/mark/should_login_today）+ /api/xhs/rednote/keepalive
- ✅ 系统内扫码弹窗（#xhsLoginModal）
- ⏳ 可增强：定时只读检查 + 登出自动通知（登记，不擅改）

## 关联
- LR 关联：本文件为 UI/运维研究增量
- 落地：zbip-shell.css（Primary chip + 六语义点）、本轮 UI 验证
