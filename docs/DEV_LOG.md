

---

## 2026-09-02 · UI 第二批精修层 zbip-refine（侘寂黑白灰 / 语义小圆点 / 移动重排，Staging 8301）

- **方式**：Strangler 新增最高优先级精修层 `static/css/zbip-refine.css`（最后加载），不改 22 个旧 CSS、不改加载顺序、不改业务 DOM；回滚 = 删该文件与其 `<link>`。仅在 Staging 8301 验证，**未合 main、未动生产 8201**。
- **已完成（已实测，Playwright 独立 chromium 双视口 1440×900 / 390×844）**：
  1. 风险类型彩色填充块 → 语义小圆点+文字：●高风险=红 / ●上升过快=橙 / ●高影响力=蓝（`.alert-type.risk/.rising/.influence::before`），桌面+移动一致。
  2. 手机风险页 `.alert-row` 单行横排改两行栅格（类型·状态·操作一行，标题+meta 一行），标题/meta 完整换行不再省略号截断，"标记已读"不再被右下浮动 badge 遮挡（内容区底部留 88px）。
  3. 手机 Home 覆盖层透出下层旧 page"幽灵字"修复：`#zbHome` z-index 300 + 实底；Ask textarea `overflow:hidden` 去原生上下滚动箭头、placeholder 两行完整可见；手机端隐藏与汉堡重叠的 refreshBtn。
  4. 旧蓝链/蓝文字收敛 stone：`.back-btn`、page-actions 描边按钮、`.alert-status` 全部黑白灰；侧栏旧 `.sidebar-toggle` 三横线折叠按钮在新 Shell 下隐藏（不删源码）；旧空分组标签 `.side-group-label`(ZACHARY OS AI) 隐藏。
  5. 侧栏分组补齐：键盘快捷键(kbShortcutsEntry)、驻场浏览器/内置浏览器/证据看板全部归入「系统」组，最终 6 组 = 总览/监测/分析/品牌资产/产出/系统，无游离项。
  6. 弹窗边缘极淡微光（modal-panel 弱阴影+内高光，仅桌面），分组间距/字距克制化。
- **顺带修复（非本层 CSS，已确认正确一并保留）**：index.html footer 后补 `</main>` 闭合（原 `<main class=content>` L148 缺闭合，right-panel 应在 main 外）。
- **测试**：全量 pytest 238 点全 `.` 无 F/E、exit=0；test_css_balance 通过；CSS 括号 44/44、注释配对；JS 括号平衡。DB schema/数据、五条红线主体口径、采集链零变更。
- **Evidence**：docs/UI/evidence/refine_audit/（desk_home/desk_risk/m_home/m_risk/m_drawer/final_desk_home）。
- **未完成 / 未实测（如实登记）**：
  - 430/768/1024/1280 断点本轮未逐档取图（仅 1440 与 390 实测）；风险预警侧栏红色 31 badge 略贴右缘，待微调。
  - 手机滚动到最后一条时浮动"采集健康"badge 仍可能轻微压标题（已留 88px，需真机滚动复核）。
  - 另一套空导航骨架（概览/品牌/监测/洞察/产出/系统，0 side-item，不在 .side-nav 内、视觉不可见）来源待查，暂不影响。
  - 本层与 Step3/Step4 同在 Staging，**尚未合 main**，等最终验收后一次性合并切生产。



## 2026-09-02 ZBMP Workbench 工作台完整建设（7视图+终端+文件树，Staging 8301+生产8201静态可用）

- **方式**：新增独立页面 static/zbmp-workbench.html，不影响 CTH 主页；布局=左4分组导航+中主内容+下方黑底只读终端+右侧文件树；侘寂黑白灰+语义小圆点。
- **后端 API**：新增 /api/workspace/file（只读文件预览，限200KB/二进制拒绝/敏感文件403/防路径穿越），插入 app.py L5313；复用已有 /api/workspace/file-tree 和 /api/workspace/term（只读白名单 ls/pwd/git只读/clear）。
- **7个视图全部接入真实数据（已实测 Playwright）**：
  1. 工作台：欢迎页'你今天想知道什么？'+快捷按钮
  2. 品牌概览：6 KPI（总笔记604/高风险22/正面310/负面53/总互动289970/总点赞159466）+热门话题TOP8
  3. 实时监测：30条预警（红高风险/橙上升过快/蓝高影响力小圆点+标题+meta）
  4. 事件中心：3 KPI（活跃152/近期负面10/总数50）+25条事件（风险点+状态点+风险分+摘要）
  5. AI洞察：4 KPI+6项AI能力（4可用/2开发中）+云端Provider（通义/OpenAI）+AI仅增强层定位说明
  6. 报告中心：报告能力状态（日报/专报可用，周报/AI开发中）+跳转CTH报告页
  7. 设置：系统设置（版本5.9.9/AI/Auth/自动采集全开启）+采集器状态（9222运行中/今日采集2次）+只读说明+跳转CTH设置页
- **CTH主页入口**：顶栏新增'ZBMP 工作台'按钮（▦ icon），点击跳转 /static/zbmp-workbench.html。
- **终端**：黑底三色圆点，只读白名单命令，↑↓历史切换，可折叠，调用 /api/workspace/term。
- **文件树**：右侧可展开目录树，点击文件调用 /api/workspace/file 预览内容，敏感文件（.env/cookie/token等）403拒绝。
- **响应式**：桌面1440+手机390/430实测无横向溢出；≤1023抽屉导航，≤760隐藏文件树+顶栏只留icon。
- **AI视图防阻塞**：用 Promise.allSettled + 4秒超时替代 Promise.all，防止云端API慢导致页面卡死。
- **测试**：Playwright独立chromium双视口（1440/390/430）实测7视图全部渲染成功、数据真实、0 console error；全量pytest主体口径红线29 passed；import OK；双healthz 200；只读路由安全。
- **Evidence**：docs/UI/evidence/refine_audit/（zbmp_desk/zbmp_mobile/zbmp_monitor_real/zbmp_brand_real/zbmp_events_real/zbmp_ai_real/zbmp_settings_real/cth_topbar_zbmp_entry/zbmp_workbench_final/zbmp_mobile_390/zbmp_mobile_430 等截图）。
- **Git**：全部在 main 分支开发并推送，本地=远程=ab43ad9（含自动巡检提交）；一任务一commit，敏感正则反查通过，DCC子模块未add。
- **未完成 / 未实测（如实记录）**：
  - 8201生产需重启才能加载 /api/workspace/file 和 /api/workspace/term 新API（静态页面已可用，6个数据视图用现有CTH API全可用）；按'不允许关闭'约定未主动重启8201。
  - ZBMP工作台的AI洞察KPI因云端/api/ai/status响应慢（>4秒）显示降级状态（AI能力和Provider硬编码数据正常显示）。
  - 终端Tab补全仅preventDefault，未实现实际补全；↑↓历史已实现。
  - 文件树搜索/过滤未实现；侧栏搜索与Ctrl+K合并未做。
  - Dark模式未迁移到ZBMP工作台（当前仅Light主题）。
  - Feature Registry / FEATURE-FINAL-VERIFICATION-MATRIX 尚未补登ZBMP工作台7个新Feature。
  - ui/staging-foundation分支的Step3/Step4 override换肤层尚未合main（zbip-refine.css精修层已在main替代其功能）。

## 2026-09-02 小红书采集合规优化

- 恢复话题活动: 广州太古汇十五周年 paused→active
- 建立 note_type 三级分类: topic(64)/opinion(388)/event(505), 共957条
- 事件笔记自动关联: 505条笔记与events表关联(event_mentions)
- 新增 note_type_backup 列备份原值
- 数据库变更不入库(.gitignore), 仅记录日志
## 2026-09-03 · collector_guard 采集合规增强：jitter + Retry-After + 修复 429 吞信号 bug（GitHub 研究驱动）

### 背景
持续链接 GitHub 研究（Scrapling AutoThrottle / Polite Scraper 五习惯）发现：① 采集固定间隔有"节拍器效应"（机器特征）；② 无 Retry-After 响应头感知。

### 改动（纯增强、可回滚、不改语义）
1. `collector_guard/analyzer.py`：`classify` 增 `retry_after=None` 参数；**修复 429 分支未 return 导致频控信号被吞的真实 bug**（429 下空响应→误判 EMPTY、有内容→误判 HEALTHY），429 现在立即返回 WARNING/RATE_LIMITED 并回填 retry_after。
2. `collector_guard/rate_limiter.py`：`wait_slot` 加 jitter（`random.uniform(0.7,1.3)`，构造参数 `jitter=True` 默认开可关）；`on_failure(retry_after=None)` 冷却时长取 `max(退避, retry_after)`（服务端指示优先，非法值静默忽略）。
3. `collector_guard/guard.py`：`_after_fail` 透传 `cls.get('retry_after')` 给 `on_failure`。

### 测试（已实测）
- 新增 `tests/test_guard_jitter_retryafter.py` 7 用例：jitter 范围 / jitter 可关回归 / retry_after 覆盖 / 更长者胜 / 非法忽略 / analyzer 回填 / 缺省无键。
- 全量回归 479+7 passed，零失败零 error。

### 红线确认
未弱化任何主体过滤 / 时间口径 / 熔断联动；jitter 与 Retry-After 均为更礼貌更合规；拒绝 stealth/bypass（守合规红线）。

### 研究沉淀
- ZBC `docs/learning/GITHUB-FRONTIER-20260903-COLLECTOR-AIGATEWAY-OBSERVABILITY.md`
- LEARNING-REGISTRY 新增 LR-20260903-003~009
- OSAI `learning-feed/github-benchmarks-04-collector-ai-observability-20260903.md`
- BACKLOG 新增 T-P1G-01 / T-P0D-03（观察）
