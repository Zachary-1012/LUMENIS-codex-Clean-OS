# 会话接续清单 / Session Handoff — 2026-09-02 00:55

> 用途：任何新会话/新窗口接手 Z-Brand-Core(ZBC) 时先读本文件，5 分钟对齐现场，不丢进度、不重复劳动。
> 权威顺序：当前源码/数据库/运行时实测 > 基线文档 > 开发记录 > 聊天结论。

## 1. 此刻运行态（实测）
| 对象 | 状态 | 说明 |
|---|---|---|
| 8201 | UP，**生产 v5.9.9**（run_supervised 看门狗，约10s 自动拉起） | 主生产，Basic Auth Zachary/ID082610 |
| 8200 | UP | 旧直跑实例（双实例技术债，见 LAUNCHERS.md） |
| 9222 | UP | Edge CDP 真人采集通道（小红书本轮已重新扫码登录，登录态有效） |
| 11434 | UP | Ollama 服务（已改走 127.0.0.1:10808 代理，qwen2.5:7b 下载中 3.3MB/s） |
| 8301 | down | 轻量 Staging，按需起 |

改 .py 后只杀 app 父进程树 `taskkill /PID <app_pid> /T /F` 让看门狗拉起；**绝不全局 taskkill python**。Flask 静态实时读盘，改 CSS/JS/HTML 只需 Ctrl+F5。

## 2. 本轮已完成并推送（本地=远程=17268a1，走 10808 代理，禁 force）
| Commit | 内容 | 验证 |
|---|---|---|
| 67d288a | 浅色莫兰迪动态启动系统标杆 `static/launch-screens/morandi/zbp-hub.html`（散落浮动小窗→环绕→CTH扩散/ZBMP全白逆回收，双端零溢出） | 四阶段截图+390/桌面零横向溢出 |
| c83c5f9 | 真人采集：human-2.1 行为画像(skip秒退/skim浅读/normal/deep)+赞藏评享计数；robust_goto 修复冷导航挂起（先落 explore 再真人键盘搜索） | 真实 3/3 详情：normal23.2s/24.0s+skip1.5s，interactions_made=0 |
| 818175e | 四库源码级拆解+Zachary AI 整合蓝图 `docs/research/FOUR-REPO-...-20260902.md` | 纯文档 |
| 17268a1 | **云端脱敏安全修复** intelligence.py：中文紧邻数字时 `\b` 失效致身份证/银行卡漏脱敏，改 `(?<!\d)…(?!\d)` 环视 | 手机/身份证(含X)/19位银行卡/邮箱全脱敏，业务数字零误伤；155 用例全绿 |

更早基线：a533c6b（真人采集首版+脱敏顺序）、fb3ce75/6d1989c（pytest9 兼容，155 全绿）、28d930b（深色启动页，保留）。

## 3. 四库本地路径与定位（本轮全部就位）
| 仓库 | 本地路径 | HEAD | 定位 |
|---|---|---|---|
| ZBC | `D:\Taikoo-monitor-new` | 17268a1(=远程) | 唯一生产：CTH-POMS 主力交付 + ZBMP 内部增强层；Flask+SQLite(data\monitor.db 53表)+Playwright |
| DCC | `D:\Development-Command-Console` | b0de3c5 | 工程治理：tools(research/learning/promote)+CI+24份协议；无业务无生产数据 |
| SICI | `D:\SICI-Core` | 8e724e1 | 移动优先 PWA 操作面（纯前端，无服务端运行时） |
| AI-D | `D:\AI-Development-Research-Hub` | 930c646 | 共享研发/学习/Shadow/能力成熟度；Zachary AI 成长模型 12 份 ADR 在此 |

整合结论：DCC/SICI/AI-D **不是 CTH 生产运行时依赖**，可 monorepo 分包整合为 zachary-ai（packages/governance、packages/research-hub、apps/mobile-surface + design-tokens + contracts）；**ZBC 保持独立生产仓**，仅契约/Evidence 弱协作。详见拆解蓝图第 3 节，待用户拍板仓库名/时机/历史保留方式。
注意：SICI/AI-D 旧文档把 DCC 写成 "DDC"，整合时统一为 DCC。ZBC 内还嵌套 `tools/development-command-console`(gitlink 77dd1e41) 是旧副本，本轮未动。

## 4. 本地 AI 接入（已完成 ✅）
- .env（不入库）：`AI_PROVIDER=auto`、`LOCAL_AI_PREFERRED=ollama`、`OLLAMA_BASE_URL=http://127.0.0.1:11434`、`OLLAMA_MODEL=qwen2.5:7b`、`ALLOW_CLOUD_AI=true`。
- 自动顺序：本地(Ollama>LMStudio>llama.cpp)优先；本地无且 ALLOW_CLOUD_AI 才走 zhipu→qwen→deepseek→ark→openai；**云端发送前强制 redact_for_cloud（本轮已加固），本地 ollama 不脱敏不出网**。
- 模型 qwen2.5:7b(4.7GB) 已下载完成：官方源直连仅 12KB/s，让 `ollama serve` 带 `HTTPS_PROXY=http://127.0.0.1:10808` 重启后提速到 3.3MB/s 拉完（经验：以后拉模型走代理）。
- **已验证**：/api/ai/status = provider ollama / model qwen2.5:7b / runtime local；/api/ai/chat 端到端 21s 本地应答、provider=ollama、不出内网（staging\test_e2e_local_ai.py）。
- 注意：当前 ollama serve 是带 10808 代理的后台进程；若电脑重启后托盘自启的是无代理 serve，模型已在本地、推理无需联网，不影响使用（仅再拉新模型时需带代理）。

## 5. 未完成清单（按优先级）
### P1（近期）
2. 莫兰迪标杆批量套用到 CTH/ZBMP/DCC/SICI/AI-D 启动页；主系统 static\css\splash.css（现深色v2）对齐浅色——**UI 方向用户要求先暂停，等收敛蓝图拍板再施工**。
3. ZBC 前端层叠收敛（实测 29 CSS + 25 JS，app.js 113KB、style.css 79KB 等）：唯一 design token + 唯一主题层，先登记引用矩阵再合并，不直接删。
4. topic_campaign 固定时钟(9/11/13/15/17/19)收口进 Dynamic Scheduler。
### P2（不阻塞上线，P0=0）
5. GAP-02 aggregate_events/build_daily_report 纯函数测试；GAP-08 Evidence 落库；GAP-09 负面确认 API 收敛；GAP-10 报告12旧路由收敛；GAP-21 importer 前端入口。
6. 话题 browse/discussion Web 端无数据保持 0（不伪造）；App Evidence 小程序上传当前手动填字段，研究本地 OCR。
7. Node 话题采集 xhs_campaign_monitor.js 仍固定 scrollBy+2.5s，未真人化（改前先读它与 v4_upgrade\adapters\human_browser.py）。
8. app.py 258KB/195 路由按 blueprint 渐进抽取（不重写）；app_backup_v589.py 等备份归 backups/ 标 LEGACY。
### 长期
9. 学习反哺影子知识库：全球品牌营销/整合传播/舆情公关案例（对标阳狮/WPP/奥美、阿那亚/天目里、广州太古汇15年）、社媒人类行为剖析，深度拆解入 AI-D research-hub。
10. zachary-ai monorepo 整合执行（待拍板，见拆解蓝图第5节）。
### 等用户拍板
- 启动页三套(dark/浅色侘寂/morandi)最终收敛（最新口头=浅色莫兰迪）；AI-D 正式英文名；ZBMP tagline 位置；固定公网域名需 Cloudflare token（GAP-16，现 trycloudflare 随机）；Staging 轻量8301 vs Docker（倾向轻量）。

## 6. 操作红线（不可违反）
- 主体口径 SUBJECT_WORDS/EXCLUDE/subject_hit/_subject_sql_and_values、风险/事件/报告核心、publish_datetime/captured_at、历史生产库——不改不弱化；采集异常不伪装成0。
- 小红书：只识别不绕过；只采集赞藏评享**计数**，绝不赞/评/藏/关注/发布（interactions_made 必须=0）；登录/扫码必须用户本人，AI 不代填不绕风控。
- git：走 10808 代理；push 前先 fetch，分叉用 rebase 保双方历史；**禁 force**；注意自动巡检会并发"自动保存版本"提交（会把工作区改动一并 commit，属正常）。
- 测试用主 venv `D:\Taikoo-monitor-new\.venv\Scripts\python.exe`；JSON 接口勿用 PowerShell IWR（编码误报），用 urllib 带 Basic；复杂 python 写独立 .py（here-string 易吃引号）；本仓 Edit 工具易失败，改用 staging\patch_*.py。

## 7. 本轮临时脚本/证据（staging\，已 gitignore，不入库）
- 真人：smoke_human3.py/.out（3/3 零互动证据）、patch_human.py、test_human_offline.py、xhs_login_check.py
- 导航：patch_nav.py；脱敏：patch_redact.py、test_redact.py、test_redact2.py
- 盘点：zbc_inventory.py、pytest_result2.xml（155全绿）、e2e_quick.py、check_two_api.py、check_risk.py
- 莫兰迪：verify_mor*.py、diag_*.py、mor_1~6_*.png；Ollama：ollama_pull*.err/log、ollama_serve.*
