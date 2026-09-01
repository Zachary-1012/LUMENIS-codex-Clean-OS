# 跨仓交接单：豆包 → GPT（事故 #001 · 用户裁决 A 方案）

- 日期：2026-09-01
- 方向：Doubao（本职 SICI/AI-D）→ GPT（Z-Brand-Core Owner）
- 性质：豆包曾跨仓在本仓库提交 4 次，构成「协作事故 #001 职责串台」；用户裁决采用 **A 方案：全部保留，交 GPT 审阅接管**，不回滚。
- 授权依据：用户在 2026-09-01 明确选择「A 保留，交 GPT 审阅接管」，并指示「完成后继续执行 A」。本文件是该授权下**唯一新增物**，不改动任何既有代码。
- 基准：本交接基于 rebase 后的远程 HEAD `0d0a27d`；4 个提交均已确认存在于 `origin/main`（同时存在于 `origin/feat/zb-runtime-preflight`）。

> 豆包声明：自本交接起，豆包对 Z-Brand-Core **只读不写**；下列代码的后续保留 / 调整 / 回滚 / 挂路由，全部由 GPT 决策。如需豆包配合，须经用户当次授权。

---

## 一、总览（4 个提交）

| SHA | 时间 | 模块 | 规模 | 验证状态 | 接管优先级 |
|---|---|---|---|---|---|
| `8524e15` | 02:14 | v4_upgrade/report_center 标准化报告中心（新增 6 文件） | +1365 | 导入通过、Word 导出实测成功；**未挂 HTTP 路由** | P1 审阅后决定挂载方式 |
| `7640934` | 03:05 | v4_upgrade/adapters/base.py 增量增强 | +175 / -11 | 10 项验证通过、20 适配器零改动 | P2 兼容良好，可保留观察 |
| `e23c5bc` | 03:19 | app.py 启用 unified_logger（+11/-1） | +11/-1 | 本地重启 E2E 14/14、日志 JSON 验证 | **P0 请重点确认启动链路** |
| `06fd0c8` | 03:34 | static/js/modal_simplify.js 弹窗精简补丁（+index.html 1 行引用） | +208 | 三弹窗本地实测、控制台 0 报错 | P1 与前端重构的覆盖关系需对齐 |

---

## 二、逐项交接明细

### 1) `8524e15` 标准化报告中心（新增目录，未改既有文件）

新增文件（纯增量，目录 `v4_upgrade/report_center/`）：

| 文件 | 行数 | 职责 |
|---|---|---|
| standard_taxonomy.py | 234 | 12 类事件 / 4 级风险 / 4 种情感 / 7 类传播主体 / 5 种报告周期 / 4 种事实状态 |
| cth_phrases.py | 166 | 太古汇专属话术：调性「温暖精致有仪式感」、标题三角度、正文五段式、笔记目的公式、活动节点 |
| zbmp_phrases.py | 131 | 通用品牌话术，6 行业适配、多品牌对比 |
| report_generator.py | 507 | CTH+ZBMP 双模式 9 模块报告；空数据不据空下结论、单一指控不当事实 |
| word_pdf_export.py | 287 | python-docx 生成 Word；PDF 走 docx2pdf → reportlab 双路径 |
| __init__.py | 40 | 包导出 |

- 已验证：模块全部导入通过；`data/exports/广州太古汇_daily_20260901_021350.docx` Word 导出实测成功；修复过 1 处 bug（Paragraph 无 font 属性，改 runs[0].font.size）。
- **NOT_VERIFIED / 待 GPT 决策**：
  1. **尚未接入任何 Flask 蓝图/HTTP 路由**，目前只能 Python 直接调用；是否挂路由、挂在哪个蓝图，由 GPT 定。
  2. 与既有 `daily_report.py / brand_report_generator.py / export_report.py / report_engine.py` 是「增强」还是「最终替换」未定，豆包未改动这些既有文件。
  3. PDF：docx2pdf 依赖本机 Word（本机 Word COM 调用失败过），reportlab 回退路径**未实测**，请 GPT 在目标部署环境验证。
  4. 月报 / 年报模板尚未深化。
- 回滚方式：整目录为纯新增，直接删除 `v4_upgrade/report_center/` 即可，不影响既有系统。

### 2) `7640934` adapters/base.py 增量增强（同文件内增量，接口不变）

- 新增：`RateLimiter` 令牌桶（默认 30 次/分、burst=5）、`AdapterMetrics`（成功率/P95/熔断·限流·降级次数/最近错误）、三级 `Fallback`（handler>最近成功缓存>失败）、`safe_collect()` 永不抛异常入口。
- 兼容性：**保留原 `search()/collect()` 签名与无参初始化方式**，20 个现存适配器零改动；原文件备份在 `v4_upgrade/adapters/base_backup_v589.py`。
- 已验证：10 项单元验证全通过。
- NOT_VERIFIED：未做长时间真实采集压测；令牌桶默认阈值是否适配各平台实际频控，请 GPT 结合采集实践校准。
- 回滚方式：用 `base_backup_v589.py` 覆盖回 base.py 即可。

### 3) `e23c5bc` app.py 启用 unified_logger（**唯一改到生产入口，P0 请重点审**）

- 改动：仅在 app.py 第 42 行 `sys.path.insert` 之后插入约 11 行 `patch_logging()` 调用，**try-except 包裹**，启用失败不阻断启动；原文件备份 `app_backup_v589.py`。
- 机制：只拦截模块名 collector/analyzer/audit/risk/v4_upgrade 走 yyds-logger，其余仍走标准 logging；`APP_ENV=prod` 时输出 JSON（含 request_id/process/thread/time）。
- 依赖前提：**运行所用解释器必须装 `yyds-logger` 与 `win32-setctime`**。豆包已在 `.venv` 装入（yyds-logger 0.8.1 / win32_setctime 1.20）；若用全局 Python 且未装，会静默回退标准 logging（不报错但无 JSON 日志）。这是之前踩过的坑：只装全局、venv 没装会「显示已启用实则未生效」。
- 已验证：本地绑定 127.0.0.1:8200 重启，E2E 14/14 PASS；`logs/collector.log` 产出标准 JSON 非空。
- 请 GPT 重点确认：①启动链路在 GPT 的运行方式下是否同样生效；②统一日志与 GPT 既有日志体系是否重复/冲突；③venv 与全局依赖口径。
- 相邻文档：`docs/ZBIP_UNIFIED_CONVERGENCE.md`（ZBIP 十九章收敛母规范）在相邻提交中，非本 SHA 的 stat 范围，一并知晓。
- 回滚方式：删除 app.py 中该 try-except 块（或用 app_backup_v589.py 对照恢复）。

### 4) `06fd0c8` 弹窗精简补丁（纯前端增量）

- 新增 `static/js/modal_simplify.js`（206 行），并在 `static/index.html` 的 app.js 之后加 1 行 `<script>` 引用。
- 设计：**不改 app.js 源文件**，在加载末尾覆盖 `openNote / openEvent / openCaseDetail` 三个函数，做「核心信息外露 + 次要信息 `<details>` 折叠」，数据不删除；自带 Light/Dark 与 768px 响应式样式。
- 已验证：本地 127.0.0.1:8200 实测三弹窗折叠/展开正常、补丁函数确实覆盖、控制台 0 报错；与 GPT 的 `ebb9a0a mobile design token layer` rebase 后无冲突。
- **对齐提醒（重要）**：补丁是「后置覆盖」关系。若 GPT 后续重构 app.js 中这三个 open* 函数或改其字段，需同步评估本补丁——要么删除补丁让新函数直接生效，要么同步更新补丁；否则可能出现两套渲染逻辑。
- 回滚方式：删除 index.html 那 1 行引用并删除 modal_simplify.js 即完全恢复 app.js 原弹窗。

---

## 三、CTH 生产红线确认（豆包未触碰）

以上 4 个提交均**未修改**下列 CTH 生产红线逻辑，请 GPT 复核：

- `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()` / `_subject_sql_and_values()`
- `aggregate_events()` / `build_daily_report()`
- 主体过滤口径（广州太古汇严格排除其他城市同名场景）、Dashboard 统计、历史数据与 15 周年专题。

base.py 与 app.py 的改动均为「外壳增量 / 启动补丁」，未改主体业务判定；报告中心与弹窗为纯新增。

---

## 四、建议 GPT 的审阅顺序

1. **P0** `e23c5bc` app.py 启动链路 + 运行解释器依赖（影响能否正常起服务）。
2. **P1** `06fd0c8` 前端补丁与你正在进行的前端迭代的覆盖关系。
3. **P1** `8524e15` 报告中心是否挂 HTTP 路由、与既有报告模块的关系定位。
4. **P2** `7640934` base.py 增强（兼容良好，压测校准阈值即可）。

---

## 五、关联材料

- 事故完整复盘（SICI 本职仓库，已推送）：SICI-Core `docs/CROSS-REPO-OWNERSHIP-INCIDENT-2026-09-01.md`，commit `46079f2`。
- 飞书《AI营销/品牌/舆情模块与Shadow Run验证成果汇总 v3.0》文末「负面案例 #001」。
- 遵循新规则：《ZBIP｜四产品总执行规则》Git 四项身份绑定、双 Push；《SICI｜统一工单执行协议》。

## 六、豆包后续边界

- Z-Brand-Core：只读。不再新增 / 修改任何文件，上述模块的演进归 GPT。
- 豆包本职回到 SICI-Core，按《统一安全架构运行预检工单 v1》SICI 页签的 4 张工单推进（Service Worker 缓存白名单=已完成；Runtime Preflight、Effective Rules=P0 待开发；Shared Capability=P1 待开发），开工前先建「GitHub→Effective Rules→Excel 工单→源码」映射，不直接写代码。
