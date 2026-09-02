# 广州太古汇舆情监测系统 v4.2 Windows / Local / Remote

这是一个**不需要服务器**的本地动态舆情监测系统：Flask + SQLite + Playwright/Chromium。默认只监听本机；需要手机局域网或远程访问时再显式开启。**本项目已移除千瓜采集链路，以小红书浏览器采集为唯一数据源。**

## 这版重点修复

- 修复全新 SQLite 数据库首次插入必报 `no column named status` 的致命问题。
- 增加旧数据库自动迁移：`status / last_seen_at / is_taikoo_verified / verify_reason`。
- 修复“上海太古汇”误判：**排除词先于直接关键词**，排除词一票否决。
- 采集入库前统一做广州太古汇主体验证。
- 修复旧版 `mark_disappeared_notes()` 会把其他关键词/历史笔记误标为消失的问题：现在只接受明确的快照 ID 集合。
- 修复重复采集统计：区分新增与更新。
- 防止多个采集任务并发启动 Chromium，避免 profile 锁冲突。
- 不再把 `events_config.json` 的静态事件直接展示成“实时事件”；`/api/events` 改为从真实采集笔记按话题聚合。
- 不再依赖 APScheduler：内置本地后台调度，每 30 分钟自动采集，每天 23:55 生成周期报告。
- 修复前端缺失 `css/style.css` / `js/app.js` 导致页面不可用的问题。
- 导出改为本地 CSV，不依赖不存在的后端 Excel API。
- 修复旧 Pipeline 对不存在的 `collect_comments_stable.js` / `generate_all_reports()` 的依赖。
- Playwright 改为项目依赖，不再硬编码 `/usr/bin/chromium-browser`。
- Cookie 注入改为环境变量，**不再把真实登录 Cookie 写在源码里**。
- 增加 `/api/backup` 本地数据库备份接口。

## 安装

```bash
pip install -r requirements.txt
npm install
npx playwright install chromium
```

## Cookie / 登录

推荐使用你自己的本地浏览器登录态。不要把真实 Cookie 提交到 Git 或聊天记录。

如果必须注入 Cookie：

```bash
export XHS_COOKIES_JSON='[{"name":"web_session","value":"你的值","domain":".xiaohongshu.com","path":"/"}]'
npm run inject
```

也可以直接使用同一个 Chromium profile，让 Playwright 复用已经登录的会话。

## 启动

```bash
python3 app.py
```

打开：

```text
http://127.0.0.1:8200
```

系统启动后会在后台自动：

- 每 30 分钟采集一次
- 采集前后进行广州太古汇主体过滤
- 自动入库/去重
- 自动分析未分析笔记
- 自动生成日报/周报/月报/年报
- 每天 23:55 再生成一次周期报告

电脑休眠、关机或 Python 进程退出期间不会采集；恢复运行后会重新开始计时。

## 手动采集

```bash
node xhs_search.js --keyword "广州太古汇" --output data/collect.json --max-scroll 6
python3 seed_data.py data/collect.json
```

或直接调用系统 API：

```bash
curl -X POST http://127.0.0.1:8200/api/collect \
  -H 'Content-Type: application/json' \
  -d '{"keywords":["广州太古汇","太古汇 投诉","太古汇 停车"],"max_scroll":6}'
```

## 数据库

数据库：`data/monitor.db`，SQLite 单文件。系统启动会自动迁移旧数据库，不要求你删库重建。

建议定期备份：

```bash
curl -X POST http://127.0.0.1:8200/api/backup
```

## 当前分析能力

当前项目中的 `ai_analyzer.py` 是**本地规则分析器**，不依赖外部 AI API。它提供情感、风险、话题、分类、摘要等本地分析能力。

如果以后需要接入真实 LLM，可以在这个接口层增加 provider；但不接 API 也能完整运行。

## 静态版

`generate_static.py` 保留用于历史兼容，但**不属于当前系统主流程**。本项目以 Flask 动态页面 + SQLite 为准，不要求生成 `output.html`。

## 重要说明

本系统默认只保留通过广州太古汇主体验证的笔记。验证逻辑会先检查排除城市/商场词，再检查太古汇关键词；这是为了避免“上海太古汇”等同名场景进入广州数据集。

## v4.2 优化

- Windows 一键启动脚本：`start_windows.bat`。
- 局域网访问脚本：`start_lan.bat`。
- 远程访问预留：`start_remote_cloudflare.bat`，无需购买服务器。
- 支持 `TAIKOO_HOST` / `TAIKOO_PORT`。
- 远程访问可启用 HTTP Basic Auth：`TAIKOO_AUTH_USER` / `TAIKOO_AUTH_PASSWORD`。
- 增加 `/healthz` 健康检查。
- SQLite 备份改为 Online Backup API，避免直接复制 WAL 数据库导致不一致。
- 自动清理超过 30 份旧备份。
- 不再主动删除 Chromium profile 锁文件，避免 Windows 上误删活动 profile 锁。
- 自动采集按半小时槽位运行，重启不会立刻重复抓取。
- 保持动态 Flask + SQLite，不生成静态主站。

详细 Windows 步骤见 `QUICK_START_WINDOWS.md`。


## v5.0 智能舆情升级

- 历史笔记增加 AI/规则复核：相关性、可信度、事实依据、正/中/负面、风险原因、事件提示。无关内容不物理删除，标记为 `irrelevant` 并从主看板统计中隐藏。
- 新增 `web_mentions / events / feedback_keywords` 三类数据：公开网页发现、跨平台事件、网页事件关键词反哺。
- 自动采集顺序调整为：**公开网页发现 → 提取事件关键词 → 小红书回搜 → AI复核 → 跨平台事件聚合 → 报告**。
- AI provider 支持 Qwen / OpenAI-compatible / DeepSeek；没有 Key 时自动回退本地规则。
- 中英韩翻译通过 `/api/translate` 提供；配置 AI 后可实时翻译。
- `python reprocess.py --limit 5000 --web-limit 120` 可对历史数据库做一次智能刷新。
- `start_remote_5g.bat` 通过 Cloudflare Quick Tunnel 提供 5G 远程访问；公网务必配置 Basic Auth。

详细升级步骤见 `UPGRADE_V5_WINDOWS.md`。

## v5.3 UI / 交互升级

- 系统名称固定为：**广州太古汇·舆情监测系统**。
- 首页恢复第一版左侧导航与核心模块分布，并采用更克制的 iOS / Apple 风格视觉与微交互。
- 所有主要入口支持 hover / 轻点说明、按压反馈、平滑滚动、右侧详情抽屉与轻量 Toast。
- 热门话题新增正面 / 中性 / 负面方向，不再只显示负面舆情。
- 热门话题支持直接跳转小红书搜索：`广州太古汇 + 话题`。
- 新增 `/api/hot-topics` 接口；不改变原有 notes / web_mentions / events 核心数据结构。

升级说明见：`UPGRADE_V5.3_WINDOWS.md`。

运行说明书：`广州太古汇·舆情监测系统_v5.3_明日运行说明书.docx`。
