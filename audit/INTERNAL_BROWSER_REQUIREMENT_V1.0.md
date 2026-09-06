# 内置 AI 浏览器 + 导航安全边界需求 V1.0

> 落盘时间：2026-09-06
> 来源：用户指令
> 优先级：P1（当前 UI 改版验证完成后接入）

## 一、核心需求

1. **所有采集必须在系统内部浏览器完成**，不允许跳出系统调用用户外部浏览器
2. **页面不能跳转出系统**，除非使用者（用户）明确同意
3. **内置 AI 浏览器**要接入前端，用户可在系统内查看/操作采集页面

## 二、当前现状（源码审计）

### 已有基础
- `internal_browser.py`（22KB）：CDP 控制层，有 navigate/click/type/scroll/screenshot/evaluate
- `browser_surface.py`（49KB）：导航安全层，已有三档模式 strict/allowlist/open，默认 allowlist
  - `_is_internal_host()` 判断内部主机
  - `_domain_allowed()` 域名白名单
  - `evaluate_navigation()` 导航评估
  - 白名单文件：data/private/browser_allowlist.json
- CDP 浏览器实例：9222（小红书主）、9223（备用）、9224（通用浏览），由 start_production.ps1 启动管理

### 缺口
1. **采集器未走内部浏览器统一层**：collector.py / xhs_cdp_collector.py 直连 CDP 9222，没有经过 internal_browser.py / browser_surface.py 抽象
2. **前端外部跳转**：risk.html 两处"原文链接" target="_blank" 直接跳外部平台（小红书等），无确认
3. **前端无内置浏览器界面**：用户无法在 LUMENIS 系统内直接看到采集浏览器画面
4. **导航模式默认 allowlist**：用户要求"不跳出系统除非同意"，应默认 strict 或增加确认机制

### 前端外部链接审计（7处，真正需处理2处）
| 文件 | 行 | 内容 | 是否需处理 |
|---|---|---|---|
| events.html:355 | openEventModal | 模态框 | 否 |
| reports.html:323 | window.open(filePath) | 系统内部文件 | 否 |
| reports.html:336 | openGenerateWizard | 模态框 | 否 |
| risk.html:359 | openRiskModal | 模态框 | 否 |
| **risk.html:97** | 原文链接 target="_blank" | **跳外部平台** | **是** |
| reports.html:327 | window.open(download_url) | 系统下载 | 否 |
| **risk.html:382** | 原文链接 target="_blank" | **跳外部平台** | **是** |

## 三、执行要求

### 3.1 导航安全边界
- 默认导航模式从 allowlist 改为 **strict**（INTERNAL_BROWSER_NAV_MODE=strict）
- strict 模式下，任何外部域名跳转必须弹出确认对话框："即将离开序境系统访问 {domain}，是否继续？"
- 用户确认后在内部浏览器新 Tab 打开，不用系统默认浏览器
- 危险协议（javascript:/data:/file:）一律拦截

### 3.2 采集器收敛到内部浏览器层
- collector.py / xhs_cdp_collector.py / collector_automation.py 的 CDP 连接统一走 internal_browser.py
- browser_surface.evaluate_navigation() 作为每次导航的前置门禁
- 采集目标域名（小红书/微博/B站/知乎等）加入 browser_allowlist.json
- 保留 9222/9223/9224 CDP 实例作为底层执行器，但上层必须经过统一抽象

### 3.3 前端内置 AI 浏览器
- SYSTEM 域新增"内置浏览器"页面（或在 Collector 页面内嵌）
- 通过 internal_browser.capture_screenshot() 实时显示采集浏览器画面
- 支持：查看当前 Tab 列表、切换 Tab、刷新、导航到指定 URL（经 evaluate_navigation 门禁）
- 采集过程可视化：用户能看到采集器当前在哪个页面、在做什么

### 3.4 外部链接处理
- risk.html 两处原文链接：点击时不直接 target="_blank"，改为调用内部浏览器在系统内打开
- 所有模板审查：新增外部链接必须经过导航门禁，不允许裸 target="_blank"

## 四、验收标准
- [ ] 导航模式默认 strict，外部跳转有确认对话框
- [ ] 采集器 CDP 连接经过 internal_browser 统一层
- [ ] 前端有内置浏览器界面，能实时看到采集画面
- [ ] risk.html 原文链接在系统内部浏览器打开
- [ ] 无未经确认的外部跳转
- [ ] 危险协议全部拦截
