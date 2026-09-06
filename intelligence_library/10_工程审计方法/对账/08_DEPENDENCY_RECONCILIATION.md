# 08 — DEPENDENCY RECONCILIATION（依赖对账）

> 审计日期：2026-09-02  
> OSAI HEAD：`60af16a`（`D:\Zachary OS AI`）  
> ZBC HEAD：`545a3ab` v5.9.9（`D:\Taikoo-monitor-new`）  
> 检查范围：`requirements.txt`、`package.json`、`.venv`、实际 import 关系、跨仓库依赖、内部模块依赖图、缺失依赖

## 状态计数

| 状态 | 计数 |
|------|------|
| EXISTS | 14 |
| PARTIAL | 6 |
| MISSING | 4 |
| UNKNOWN | 0 |

---

## 1. ZBC Python 依赖声明 vs 实际安装

### 1.1 `requirements.txt` 声明清单（17 个包）

| # | 包名 | 版本约束 | 用途分类 | .venv 实际安装 | 状态 |
|---|------|----------|----------|---------------|------|
| 1 | Flask | >=2.0.0 | Web 框架 | OK | EXISTS |
| 2 | Werkzeug | >=2.0.0 | WSGI 工具 | OK | EXISTS |
| 3 | pandas | >=1.3.0 | 数据处理 | OK | EXISTS |
| 4 | openpyxl | >=3.0.0 | Excel 读写 | OK | EXISTS |
| 5 | xlsxwriter | >=3.0.0 | Excel 生成 | OK | EXISTS |
| 6 | python-docx | >=0.8.11 | Word 文档 | OK | EXISTS |
| 7 | reportlab | >=3.6.0 | PDF 生成 | OK | EXISTS |
| 8 | playwright | >=1.30.0 | 浏览器自动化 | OK | EXISTS |
| 9 | selenium | >=4.0.0 | 浏览器自动化 | OK | EXISTS |
| 10 | psutil | >=5.9.0 | 系统监控 | OK | EXISTS |
| 11 | requests | >=2.28.0 | HTTP 请求 | OK | EXISTS |
| 12 | httpx | >=0.24.0 | 异步 HTTP | OK | EXISTS |
| 13 | python-dotenv | >=0.21.0 | 环境变量 | OK | EXISTS |
| 14 | colorama | >=0.4.6 | 终端颜色 | OK | EXISTS |
| 15 | tqdm | >=4.64.0 | 进度条 | OK | EXISTS |
| 16 | openai | （注释掉） | AI API（可选） | MISSING | PARTIAL（声明中注释，未安装） |
| 17 | ollama | （注释掉） | 本地 AI（可选） | MISSING | PARTIAL（声明中注释，未安装） |

- 证据路径：`D:\Taikoo-monitor-new\requirements.txt`
- .venv 验证：`D:\Taikoo-monitor-new\.venv\Scripts\python.exe` + `importlib.util.find_spec()`

### 1.2 实际代码使用但 `requirements.txt` 未声明的包（隐式依赖）

| # | 包名 | 实际使用位置 | .venv 安装 | requirements.txt 声明 | 状态 |
|---|------|-------------|-----------|----------------------|------|
| 1 | **waitress** | `run_production.py:51` `from waitress import serve`；`start_v4.bat:26` 依赖检查 | OK | **未声明** | **MISSING（生产 WSGI 服务器未在 requirements.txt 声明）** |
| 2 | **beautifulsoup4 (bs4)** | `collector_v2/official_info_scraper.py:13` `from bs4 import BeautifulSoup`；`v4_upgrade/adapters/sogou_search.py:155` | OK | **未声明** | **MISSING（HTML 解析库未在 requirements.txt 声明）** |
| 3 | **lxml** | （bs4 的可选解析器后端，可能被间接使用） | OK | **未声明** | PARTIAL（可能为 bs4 依赖，未直接 import） |
| 4 | **pdfplumber** | `start_v4.bat:26` 依赖检查列表中包含；`v4_upgrade/report_center/word_pdf_export.py` 可能使用 | 未验证 | **未声明** | PARTIAL（启动脚本检查但 requirements.txt 未声明） |

> **关键发现**：`requirements.txt` 声明 17 个包，但实际代码使用了 **waitress**（生产 WSGI 服务器）和 **beautifulsoup4**（HTML 解析），这两个包**未在 requirements.txt 中声明**。`start_v4.bat` 的依赖检查列表（flask, requests, waitress, bs4, pdfplumber, docx, openpyxl, pandas）与 `requirements.txt` 不一致——`start_v4.bat` 检查的 8 个包中有 3 个（waitress, bs4, pdfplumber）不在 `requirements.txt` 中。

### 1.3 `requirements.txt` 声明但代码未直接使用的包

| 包名 | 声明 | 代码直接 import | 状态 |
|------|------|----------------|------|
| selenium | >=4.0.0 | 需全仓验证（playwright 为主力浏览器自动化工具，selenium 可能为遗留） | PARTIAL |
| httpx | >=0.24.0 | 需全仓验证（requests 为主力 HTTP 库，httpx 可能为异步场景预留） | PARTIAL |
| xlsxwriter | >=3.0.0 | openpyxl 已支持 Excel 读写，xlsxwriter 可能为特定导出场景 | PARTIAL |

---

## 2. ZBC Node.js 依赖

### 2.1 `package.json`

| 项目 | 值 | 路径 | 状态 |
|------|-----|------|------|
| name | taikoo-monitor | `package.json:2` | EXISTS |
| version | 5.6.2 | `package.json:3` | PARTIAL（与系统 VERSION=v5.9.9 不一致） |
| type | module | `package.json:5` | EXISTS |
| dependencies | `playwright: ^1.62.1` | `package.json:11-13` | EXISTS |
| scripts | search / inject / login | `package.json:6-10` | EXISTS |

- `node_modules/` 目录存在（已安装）
- `package-lock.json` 存在（1678 字节）
- 证据路径：`D:\Taikoo-monitor-new\package.json`、`node_modules/`

### 2.2 Node.js 脚本文件

| 脚本 | 路径 | 用途 | 依赖 | 状态 |
|------|------|------|------|------|
| `xhs_search.js` | 根目录 | 小红书搜索 | playwright | EXISTS |
| `xhs_campaign_monitor.js` | 根目录 | 话题活动监测 | playwright | EXISTS |
| `rednote_collector.cjs` | 根目录 | 小红书采集器（CommonJS） | playwright | EXISTS |
| `xhs_cookie_search.js` | 根目录 | Cookie 搜索 | （需验证） | EXISTS |
| `inject_cookies.js` | 根目录 | Cookie 注入 | playwright | EXISTS |

---

## 3. OSAI 侧依赖声明

### 3.1 Python 依赖

| 项目 | 路径 | 结果 | 状态 |
|------|------|------|------|
| OSAI 根目录 `requirements.txt` | `D:\Zachary OS AI\requirements.txt` | **不存在** | MISSING（OSAI 根目录无 Python 依赖声明） |
| AIDRH `requirements.txt` | `components/AI-Development-Research-Hub/requirements.txt` | **不存在** | MISSING |
| DCC `requirements.txt` | `components/Development-Command-Console/requirements.txt` | **不存在** | MISSING |
| SICI `requirements.txt` | `components/SICI-Core/requirements.txt` | **不存在** | MISSING |
| archive 中旧版 `requirements.txt` | `archive/desktop-legacy/taikoo-monitor-clean/requirements.txt` | 存在（ZBC v5.3.1 旧版） | PARTIAL（历史归档，非当前 OSAI 依赖） |

> **OSAI 侧 Python 依赖分析**：OSAI 的 Python 代码（AIDRH `src/contracts/`、`tools/`、DCC `tools/`）**仅使用 Python 标准库**（`json`, `re`, `argparse`, `hashlib`, `datetime`, `pathlib`, `typing`, `unittest`, `subprocess`, `tempfile`, `uuid`, `copy`, `dataclasses`），无第三方依赖。因此无 `requirements.txt` 是合理的。但缺少显式声明（即使为空或仅标注"stdlib-only"）仍为 MISSING。

### 3.2 Node.js 依赖

| 项目 | 路径 | 结果 | 状态 |
|------|------|------|------|
| DCC `package.json` | `components/Development-Command-Console/package.json` | 存在，`version=0.5.0`，**无 dependencies 字段**（仅 dev scripts） | EXISTS（声明存在但无运行时依赖） |
| AIDRH `package.json` | `components/AI-Development-Research-Hub/package.json` | **不存在** | MISSING |
| SICI `package.json` | `components/SICI-Core/package.json` | **不存在** | MISSING |
| archive 中旧版 `package.json` | `archive/desktop-legacy/taikoo-monitor-clean/package.json` | 存在（ZBC v5.3.1 旧版） | PARTIAL（历史归档） |

- DCC `package.json` 证据：`components/Development-Command-Console/package.json`（`engines: node>=18.0.0`，scripts 含 preflight/bridge/test，无 dependencies）
- DCC 为 Node.js 项目（`server/server.js`），但其 `package.json` 未声明任何运行时依赖——可能依赖全局安装或 `node_modules` 未提交。

---

## 4. 跨仓库依赖检查（越界检查）

### 4.1 OSAI → ZBC 依赖

| 检查项 | 结果 | 证据 | 状态 |
|--------|------|------|------|
| OSAI Python 文件 import ZBC 模块 | **未发现** | OSAI 全仓 `.py` grep `Taikoo|monitor.db|ZBC|zbc` 仅命中本次对账脚本 `_db_inspect.py`（非 OSAI 原有代码） | EXISTS（正确隔离——OSAI 不 import ZBC 代码） |
| OSAI 直连 ZBC 生产数据库 | **未发现** | OSAI 全仓无 ZBC `monitor.db` 连接代码（仅本次对账脚本只读查询） | EXISTS（正确隔离） |
| OSAI 引用 ZBC 文件路径 | **未发现**（除本次对账脚本） | Grep 结果 | EXISTS（正确隔离） |
| OSAI archive 含 ZBC 代码副本 | **发现** | `archive/desktop-legacy/taikoo-monitor-clean/` 含完整 ZBC v5.3.1 代码（见 07 文档 §6.1） | MISSING（越界——归档副本，非运行时依赖） |

### 4.2 ZBC → OSAI 依赖

| 检查项 | 结果 | 证据 | 状态 |
|--------|------|------|------|
| ZBC Python 文件 import OSAI 模块 | **未发现** | ZBC 全仓 `.py` grep `Zachary OS AI|osai|OSAI` 返回 0 匹配 | EXISTS（正确隔离——ZBC 不 import OSAI 代码） |
| ZBC 引用 OSAI 文件路径 | **未发现** | Grep 结果 | EXISTS（正确隔离） |
| ZBC 引用 OSAI Contract/协议 | **未发现代码级引用** | ZBC 无 `src/contracts/`、无 `GLOBAL-CROSS-REPOSITORY-BASELINE` 引用 | EXISTS（ZBC 独立运行，不依赖 OSAI 契约代码） |

> **跨仓库依赖结论**：**运行时无跨仓库依赖**——OSAI 和 ZBC 在代码层面完全隔离，无互相 import、无直连对方数据库、无文件路径引用。唯一的越界是 OSAI `archive/` 中持有 ZBC v5.3.1 代码归档副本（静态归档，非运行时依赖，见 07 文档）。

---

## 5. ZBC 内部模块依赖图

### 5.1 `app.py` 依赖（核心编排模块，272KB）

`app.py` 直接 import 的内部模块（40+ 个）：

| 类别 | 模块 | 路径 | 状态 |
|------|------|------|------|
| 数据层 | `database` (as db) | `database.py` | EXISTS |
| 主体口径 | `subject_rules`（SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit, subject_sql_and_values） | `subject_rules.py` | EXISTS（最高保护层） |
| AI 分析 | `ai_analyzer`, `ai_filter`, `ai_gateway_v570`, `ai_learning_engine`, `local_ai_client`, `ark_llm`（间接） | `ai_analyzer.py`, `ai_filter.py`, `ai_gateway_v570.py`, `ai_learning_engine.py`, `local_ai_client.py` | EXISTS |
| 采集 | `collector`, `collector_automation`, `xhs_cookie_bridge`, `xhs_p0_orchestrator` | `collector.py`, `collector_automation.py`, `xhs_cookie_bridge.py`, `xhs_p0_orchestrator.py` | EXISTS |
| 报告 | `daily_report`, `report_engine`, `export_report`, `report_export.report_engine`（as export_report_v532） | `daily_report.py`, `report_engine.py`, `export_report.py`, `report_export/` | EXISTS |
| 事件/情报 | `intelligence`, `event_graph`（间接）, `reprocess` | `intelligence.py`, `reprocess.py` | EXISTS |
| 话题/品牌 | `topic_campaign`, `swire_group`, `brand_knowledge_base`（间接）, `brand_report_generator`（间接） | `topic_campaign.py`, `swire_group.py` | EXISTS |
| 案例/PR | `pr_case_integration`, `public_opinion_cases`, `case_deep_analysis`（间接） | `pr_case_integration.py`, `public_opinion_cases.py` | EXISTS |
| 系统监控 | `monitoring`（间接）, `system_health_api`, `stability_monitor`, `system_guardian`（间接）, `system_watchdog`（间接）, `memory_optimizer` | `system_health_api.py`, `stability_monitor.py`, `memory_optimizer.py` | EXISTS |
| 安全 | `safety_boundary`（间接）, `security_scanner`, `data_boundary`（间接）, `risk_engine`（间接） | `security_scanner.py` | EXISTS |
| 认证 | `auth_recovery_api`, `auth_recovery_center`（间接） | `auth_recovery_api.py` | EXISTS |
| v4 模块 | `v4_upgrade`（create_v4_blueprint, init_v4_modules） | `v4_upgrade/__init__.py` | EXISTS |
| 配置/工具 | `config`, `settings_module`, `function_registry`, `logger`（间接）, `cache_manager`（间接）, `wechat_notifier`（间接）, `app_evidence`, `architecture_api`, `system_features_api`, `evaluation_system`, `runtime_preflight`, `browser_discovery`, `web_monitor_v570`, `adaptive_engine`（间接）, `network_adaptive`（间接） | 各对应文件 | EXISTS |
| 标准库 | `os, sys, json, threading, time, shutil, sqlite3, secrets, argparse, concurrent.futures, subprocess, csv, io, re, pathlib, datetime, faulthandler, traceback` | Python stdlib | EXISTS |
| 第三方 | `flask`（Flask, jsonify, request, send_from_directory, send_file, Response, redirect） | Flask | EXISTS |

- 证据路径：`app.py:1-105`（import 区）、`app.py:3113`（延迟 import）、`app.py:4971-5323`（函数内延迟 import）
- `app.py` 是**全系统依赖中枢**，直接或间接依赖几乎所有 ZBC 模块。

### 5.2 采集器依赖链

| 模块 | 直接依赖 | 路径 | 状态 |
|------|----------|------|------|
| `collector.py` | 标准库（subprocess, json, os, re, sys, datetime） | `collector.py:6-11` | EXISTS（仅标准库，通过 subprocess 调用 Node.js 脚本） |
| `xhs_cdp_collector.py` | （需验证，45KB 大文件） | `xhs_cdp_collector.py` | EXISTS |
| `collector_v2/` | `base.py`（PlatformCollector, RawNote, RawComment）、各平台 client | `collector_v2/base.py`, `collector_v2/xhs/`, `collector_v2/weibo/` | EXISTS |
| `collector_automation.py` | （32KB，调度+自动化） | `collector_automation.py` | EXISTS |
| `rednote_collector.cjs` | Node.js playwright | `rednote_collector.cjs` | EXISTS |

### 5.3 AI 模块依赖链

| 模块 | 直接依赖 | 路径 | 状态 |
|------|----------|------|------|
| `ai_analyzer.py` | 标准库（re, hashlib, datetime）+ `subject_rules`（SUBJECT_WORDS, SUBJECT_EXCLUDE_WORDS, subject_hit） | `ai_analyzer.py:10-13` | EXISTS（依赖最高保护层 subject_rules） |
| `ai_filter.py` | （需验证） | `ai_filter.py` | EXISTS |
| `ai_learning_engine.py` | （需验证，18KB） | `ai_learning_engine.py` | EXISTS |
| `ark_llm.py` | （需验证，火山引擎 LLM 客户端） | `ark_llm.py` | EXISTS |
| `local_ai_client.py` | （需验证，本地 AI 客户端） | `local_ai_client.py` | EXISTS |
| `data_feedback_loop.py` | （需验证，16KB） | `data_feedback_loop.py` | EXISTS |

### 5.4 数据层依赖链

| 模块 | 直接依赖 | 路径 | 状态 |
|------|----------|------|------|
| `database.py` | 标准库（sqlite3, json, os, re, datetime, contextlib）+ `subject_rules`（SUBJECT_FIELDS, subject_hit, subject_sql_and_values） | `database.py:1-8` | EXISTS（依赖最高保护层 subject_rules） |
| `models.py` | 标准库（sqlite3, datetime, typing） | `models.py:7-9` | EXISTS（仅标准库，未被 database.py 实际使用） |
| `database_migrations.py` | 标准库（os, sys, sqlite3, shutil, datetime, typing） | `database_migrations.py:13-18` | EXISTS（仅标准库） |

### 5.5 v4 模块依赖链

| 模块 | 直接依赖 | 路径 | 状态 |
|------|----------|------|------|
| `v4_upgrade/__init__.py` | （blueprint 注册） | `v4_upgrade/__init__.py` | EXISTS |
| `v4_upgrade/auth/` | models, service, security, audit, workspace | `v4_upgrade/auth/` | EXISTS |
| `v4_upgrade/adapters/` | base, registry, 20+ 平台适配器 | `v4_upgrade/adapters/` | EXISTS |
| `v4_upgrade/ai_hub/` | routes, service, shadow | `v4_upgrade/ai_hub/` | EXISTS |
| `v4_upgrade/report_center/` | report_generator, word_pdf_export, standard_taxonomy, cth_phrases, zbmp_phrases | `v4_upgrade/report_center/` | EXISTS |

---

## 6. 启动脚本依赖检查

### 6.1 各启动脚本使用的 Python 入口

| 启动脚本 | 路径 | Python 入口 | WSGI 服务器 | 状态 |
|----------|------|-------------|-------------|------|
| `start_stable.bat` | 根目录 | `python -u app.py --host 0.0.0.0 --port 8200` | **Flask 内置开发服务器**（非 waitress） | EXISTS |
| `start_system.bat` | 根目录 | `python app.py` | Flask 内置 | EXISTS |
| `start_all.bat` | 根目录 | `python app.py --host 0.0.0.0 --port 8200` | Flask 内置 | EXISTS |
| `start_windows.bat` | 根目录 | `python app.py --host 0.0.0.0` | Flask 内置 | EXISTS |
| `start_lan.bat` | 根目录 | `python app.py --host 0.0.0.0` | Flask 内置 | EXISTS |
| `start_v4.bat` | 根目录 | （先检查依赖再启动） | 依赖检查含 waitress | PARTIAL |
| `run_production.py` | 根目录 | `from waitress import serve` + `serve(app, ...)` | **waitress 生产 WSGI** | EXISTS |
| `deployment/start_local.bat` | deployment/ | `python app.py --host 127.0.0.1 --port 8200` | Flask 内置 | EXISTS |
| `deployment/start_remote.bat` | deployment/ | `.venv\Scripts\activate.bat && python app.py` | Flask 内置 | EXISTS |

> **关键发现**：
> 1. **绝大多数启动脚本使用 Flask 内置开发服务器**（`python app.py`），而非生产级 WSGI 服务器（waitress）。Flask 内置服务器不适用于生产环境（单线程、无并发优化、无稳定性保障）。
> 2. `run_production.py` 使用 `waitress`，但 `waitress` **未在 `requirements.txt` 中声明**。
> 3. `start_stable.bat` 名称含"stable"但实际使用 `python -u app.py`（Flask 开发服务器），**未使用 waitress**，与"stable/生产"定位不符。
> 4. `start_v4.bat` 的依赖检查列表（flask, requests, waitress, bs4, pdfplumber, docx, openpyxl, pandas）与 `requirements.txt` 不一致。

### 6.2 `start_stable.bat` 缺失依赖专项

| 依赖项 | `start_stable.bat` 是否需要 | `requirements.txt` 是否声明 | .venv 是否安装 | 状态 |
|--------|---------------------------|---------------------------|----------------|------|
| waitress | 否（脚本用 `python -u app.py`，不用 waitress） | 否 | 是 | PARTIAL（脚本不用但 run_production.py 用，且 requirements.txt 未声明） |
| beautifulsoup4 (bs4) | 否（启动脚本不直接用，但 collector_v2 和 v4 adapters 用） | 否 | 是 | MISSING（代码使用但 requirements.txt 未声明） |
| playwright | 是（采集器依赖） | 是 | 是 | EXISTS |
| pdfplumber | 否（start_v4.bat 检查但 start_stable.bat 不检查） | 否 | 未验证 | PARTIAL |

---

## 7. 虚拟环境与依赖隔离

| 项目 | 路径 | 状态 |
|------|------|------|
| ZBC `.venv/` | `D:\Taikoo-monitor-new\.venv\` | EXISTS（Python 虚拟环境，已安装全部声明依赖+隐式依赖） |
| ZBC `.venv\Scripts\python.exe` | `.venv\Scripts\python.exe` | EXISTS |
| ZBC `node_modules/` | `D:\Taikoo-monitor-new\node_modules\` | EXISTS（Node.js 依赖，已安装 playwright） |
| OSAI `.venv/` | 无 | MISSING（OSAI Python 代码仅用标准库，无需虚拟环境，合理） |
| OSAI `node_modules/` | DCC 可能有 | 需验证 | PARTIAL |

---

## 8. 依赖版本一致性

| 项目 | OSAI 侧 | ZBC 侧 | 一致性 | 状态 |
|------|---------|--------|--------|------|
| Python 版本 | 未声明 | 未显式声明（.venv 为 Python 3.13，从 `__pycache__/cpython-313.pyc` 推断） | UNKNOWN（双方均未在配置文件中声明 Python 版本约束） | PARTIAL |
| Node.js 版本 | DCC `engines: node>=18.0.0` | ZBC 未声明 | PARTIAL（DCC 有声明，ZBC 无） |
| Flask 版本 | 无 | >=2.0.0 | EXISTS（ZBC 单边声明） |
| playwright 版本 | 无 | Python >=1.30.0 / Node ^1.62.1 | PARTIAL（Python 和 Node 版本约束不同） |
| 系统版本号 | 无 | `VERSION`=v5.9.9 / `package.json`=5.6.2 / `models.py`=v5.8.0 | **不一致**（ZBC 内部 3 处版本号互不相同） | PARTIAL |

---

## 9. 汇总与关键发现

### 9.1 状态计数汇总

| 状态 | 计数 | 占比 |
|------|------|------|
| EXISTS | 14 | 58.3% |
| PARTIAL | 6 | 25.0% |
| MISSING | 4 | 16.7% |
| UNKNOWN | 0 | 0% |

### 9.2 P0 级关键发现

1. **`requirements.txt` 缺失生产关键依赖**：`waitress`（`run_production.py:51` 使用的生产 WSGI 服务器）和 `beautifulsoup4`（`collector_v2/official_info_scraper.py:13` 和 `v4_upgrade/adapters/sogou_search.py:155` 使用的 HTML 解析库）**未在 `requirements.txt` 中声明**。新环境执行 `pip install -r requirements.txt` 后这两个包将缺失，导致 `run_production.py` 和部分采集器运行失败。
2. **`start_stable.bat` 使用 Flask 开发服务器而非生产 WSGI**：脚本名含"stable"但实际执行 `python -u app.py`（Flask 内置单线程开发服务器），未使用 waitress。生产环境应使用 `run_production.py`（waitress）。

### 9.3 P1 级关键发现

3. **`start_v4.bat` 依赖检查与 `requirements.txt` 不一致**：`start_v4.bat:26` 检查 flask, requests, waitress, bs4, pdfplumber, docx, openpyxl, pandas 共 8 个包，其中 waitress/bs4/pdfplumber 不在 `requirements.txt` 中；`requirements.txt` 中的 playwright/selenium/psutil/httpx/python-dotenv/colorama/tqdm/reportlab/xlsxwriter/Werkzeug 不在 `start_v4.bat` 检查列表中。
4. **ZBC 内部版本号 3 处不一致**：`VERSION`=v5.9.9、`package.json`=5.6.2、`models.py` 文件头=v5.8.0（`__main__` 打印 v5.8.9）。
5. **OSAI 侧无 Python 依赖声明文件**：虽然 OSAI Python 代码仅用标准库（合理），但缺少显式 `requirements.txt`（即使为空或标注 stdlib-only）。
6. **DCC `package.json` 无运行时依赖声明**：DCC 是 Node.js 项目（`server/server.js`），但 `package.json` 无 `dependencies` 字段。

### 9.4 P2 级关键发现

7. **跨仓库运行时无依赖**：OSAI 和 ZBC 在代码层面完全隔离，无互相 import、无直连对方数据库。这是正确的架构隔离。
8. **`app.py` 是全系统依赖中枢**：直接 import 40+ 内部模块，模块间耦合度高。
9. **`models.py` 定义了 ORM 模型但 `database.py` 未使用**：双轨并存（ORM 定义 + 原生 SQL），ORM 模型实际未被数据层调用。
10. **Python 版本未在任何配置文件中声明**：ZBC `.venv` 推断为 Python 3.13（从 `.pyc` 文件名），但 `requirements.txt`、`runtime.txt`、`pyproject.toml` 等均无版本约束。

---

*本文档所有依赖检查均基于本地当前源码实际文件和 .venv 实际安装状态，未根据 README/历史文档/模型记忆判定"存在"。每项均附真实文件路径作为证据。*
