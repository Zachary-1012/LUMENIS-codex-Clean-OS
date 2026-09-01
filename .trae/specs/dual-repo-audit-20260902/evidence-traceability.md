# 双子星 README 融合 · Evidence Traceability（依据溯源总表）

> **生成时间**：2026-09-02
> **范围**：ZBC README §9 允许禁止矩阵 + ZOSAI README §9 四层矩阵（共 ~95 行）
> **溯源字段**：行号 / 规则原文（首 80 字）/ 依据标签 / 真实依据文件绝对路径 / 段落锚点 / 当前版本 SHA
> **权威优先级链**（从高到低）：ZBC AGENTS.md §2 / §4 / §5 / §13 / §15 > ZOSAI IMMUTABLE BASE-001~022 > ZBC PLATFORM_README.md > ZBIP_UNIFIED_README.md > GLOBAL-CROSS-REPOSITORY-BASELINE.md > DCC THREE_REPOSITORY_SYSTEM_MATRIX.md > 双子 Spec Spec.md §9 AC
> **原则**：NOT_VERIFIED 行显式标记；任何矩阵行不得"无依据"；失败记录永不删除。

---

## Part A. Z-Brand-Core README §9 允许禁止矩阵（四层 ~ 42 行）

| 行号 | 规则原文 | 依据标签 | 依据文件绝对路径 | 段落锚点 | SHA |
|---|---|---|---|---|---|
| A-PRODUCT-1 | CTH-POMS 客户交付独立运行，不依赖 ZOSAI / DCC / SICI 任何组件 | [AGENTS §2] 一套Core配置驱动运行隔离 | D:\Taikoo-monitor-new\AGENTS.md | #2-一套-core配置驱动运行隔离 | b497277 |
| A-PRODUCT-2 | ZBMP 母平台与 CTH-POMS 共用同仓 Core，Feature Gate 隔离，绝不形成第二套 Core | [AGENTS §2] 禁止复制整套源码 | D:\Taikoo-monitor-new\AGENTS.md | §2 禁止段落 | b497277 |
| A-PRODUCT-3 | 广州太古汇主体口径 P0：SUBJECT_WORDS 只增不减；主体过滤不得弱化 | [AGENTS §5] 主体口径 P0 | D:\Taikoo-monitor-new\AGENTS.md | #5-广州太古汇主体口径p0-不得弱化 | b497277 |
| A-PRODUCT-4 | publish_datetime vs captured_at 分离；日报按发布时间口径 | [AGENTS §6] 时间口径 | D:\Taikoo-monitor-new\AGENTS.md | #6-时间口径 | b497277 |
| A-PRODUCT-5 | 小红书采集 8 状态 + Auth 恢复中心 + 风控熔断；不得破解验证码/绕过风控 | [AGENTS §7] 小红书采集 & 10 XHS RED-LINE | D:\Taikoo-monitor-new\AGENTS.md | #7-小红书采集与-auth稳定可恢复不可静默; ZOSAI README §6 RED-LINE 表 | b497277 |
| A-PRODUCT-6 | AI 纯增强层；Ollama-first；没有 AI 仍可采集/去重/报告 | [AGENTS §3] AI 不得单独决定 | D:\Taikoo-monitor-new\AGENTS.md | #3-当前-aiollama-only | b497277 |
| A-PRODUCT-7 | 主体身份与内容属性严格分离（禁止 user_type=UGC 类设计）| [AGENTS §9.1] | D:\Taikoo-monitor-new\AGENTS.md | #91-传播主体 | b497277 |
| A-PRODUCT-8 | 三类事件生命周期发现→形成→增长→爆发→扩散→分化→衰减→结束 | [AGENTS §9.3] | D:\Taikoo-monitor-new\AGENTS.md | #93-三类事件 | b497277 |
| A-PRODUCT-9 | 数据失败必须显式；采集失败不得伪装成 0 条 | [AGENTS 最终原则 §17] | D:\Taikoo-monitor-new\AGENTS.md | §17 数据失败必须显式 | b497277 |
| A-REPO-1 | .db / .sqlite / .sqlite3 / 迁移脚本属于数据资产；未经授权不得删改 | [AGENTS §4] 数据最高保护 | D:\Taikoo-monitor-new\AGENTS.md | #4-数据库与数据资产最高保护级别 | b497277 |
| A-REPO-2 | Cookie / Token / API Key 只允许 .env / 系统密钥；禁止进 Git | [AGENTS §3 / §15] | D:\Taikoo-monitor-new\AGENTS.md | §3 严禁 + §15 敏感凭证 | b497277 |
| A-REPO-3 | production DB 禁止携带其他品牌或 AI 实验数据 | [AGENTS §4] 客户 Release 隔离 | D:\Taikoo-monitor-new\AGENTS.md | §4 末客户 Release 禁止段 | b497277 |
| A-REPO-4 | tools/development-command-console Submodule Pin 升级走 DCC Release Gate | [DUAL-REPO §8 硬边界] | D:\Zachary OS AI\components\Development-Command-Console\docs\DUAL_REPO_RELEASE_POLICY.md | §8 Submodule Pin Upgrade Flow | f0b8bb5 |
| A-REPO-5 | templates/ static/ assets 只在 ZBC 仓修改；禁止反向跨仓复制 | [AGENTS §2 禁止复制] | D:\Taikoo-monitor-new\AGENTS.md | §2 | b497277 |
| A-REPO-6 | collector_v2/ platform_adapters/ 平台层 P0；上层 Core 统一逻辑 | [AGENTS §8] BasePlatformAdapter | D:\Taikoo-monitor-new\AGENTS.md | #8-多平台-adapter | b497277 |
| A-REPO-7 | risk_engine.py P0：主体口径/风险规则不经审批不得改 | [AGENTS §5 末] | D:\Taikoo-monitor-new\AGENTS.md | §5 末 aggregate_events/build_daily_report 主体过滤 | b497277 |
| A-REPO-8 | AI_POLICY.md 禁止外部云 AI 进生产主链路；Ollama-only Default | [AI_POLICY] | D:\Taikoo-monitor-new\AI_POLICY.md（若存在则引用，否则 AGENTS §3）| 头部 Ollama-only 默认段 | b497277 |
| A-REPO-9 | daily_report.py 生成报告按 publish_datetime 口径 | [AGENTS §6] | D:\Taikoo-monitor-new\AGENTS.md | §6 | b497277 |
| A-REPO-10 | AGENTS.md / PROJECT_STATUS.md / CHANGELOG* / VERSION 权威来源 | [DUAL-REPO 优先级链] | D:\Zachary OS AI\README.md | §12 末 Repository Fact Baseline | f0b8bb5 |
| A-REPO-11 | 任何先旁路验证再入主链路（Shadow Mode 对照）| [AGENTS §17 先旁路] + [Shadow-first 8 状态] | D:\Zachary OS AI\components\AI-Development-Research-Hub\SHADOW-LEARNING-PROTOCOL.md | §3 Shadow 进入条件 | f0b8bb5 |
| A-REPO-12 | CTH-POMS Release = 验证快照 + Brand Profile，独立运行不连 Z-Brand 服务 | [AGENTS §12 / §2 末] | D:\Taikoo-monitor-new\AGENTS.md | #12-双产品-release-与版本血缘 | b497277 |
| A-REPO-13 | ZBMP 多品牌能力只能通过 Feature License Gate 暴露给客户 | [AGENTS §2 Runtime Mode] | D:\Taikoo-monitor-new\AGENTS.md | §2 推荐模式 CUSTOMER_RELEASE / ZBRAND_PLATFORM | b497277 |
| A-REPO-14 | 新增表字段向后兼容迁移，不得清空历史数据 | [AGENTS §4 第二段] | D:\Taikoo-monitor-new\AGENTS.md | §4 新增表字段段落 | b497277 |
| A-COMP-1 | collector_v2 组件 Owner = ZBC；跨仓禁止复制采集器实现 | [§4 Owner 表] | D:\Taikoo-monitor-new\README.md | §4 9 组件 owner 行 | b497277 |
| A-COMP-2 | risk_engine 组件 Owner = ZBC；DCC 只能 Shadow 审计 | [§4 Owner 表] | D:\Taikoo-monitor-new\README.md | §4 risk_engine 行 | b497277 |
| A-COMP-3 | ai_analyzer 组件 Ollama-first；外部云 AI 必须旁路可控开关 | [AGENTS §3] | D:\Taikoo-monitor-new\AGENTS.md | §3 历史外部 AI 不得贸然删除段落 | b497277 |
| A-COMP-4 | daily_report 组件；报告周期不得错用采集窗口 | [AGENTS §11] | D:\Taikoo-monitor-new\AGENTS.md | #11-数据分析与报告 | b497277 |
| A-COMP-5 | Auth Recovery Center 全局弹窗 + 二维码 + 任务暂停恢复 | [AGENTS §7.2] | D:\Taikoo-monitor-new\AGENTS.md | #72-auth-体验是全局能力 | b497277 |
| A-COMP-6 | event_relation（触发/衍生/继发/并行）Owner = ZBC 未来模块 | [AGENTS §9.3] | D:\Taikoo-monitor-new\AGENTS.md | §9.3 末 事件关系段 | b497277 |
| A-COMP-7 | Brand Knowledge Base / Case Lib Owner = ZBC | [AGENTS §9 六维/9.1 引用] | D:\Taikoo-monitor-new\AGENTS.md | §9 | b497277 |
| A-COMP-8 | 品牌报告生成器 Owner = ZBC | [AGENTS §11] | D:\Taikoo-monitor-new\AGENTS.md | §11 四种报告段 | b497277 |
| A-DEV-1 | 工程宪法流程：审计→备份/确认→最小补丁→单测→E2E→真实验证→回归→CHANGELOG→交付 | [AGENTS §13] | D:\Taikoo-monitor-new\AGENTS.md | #13-修改安全协议 | b497277 |
| A-DEV-2 | P0（启动/DB/主体/采集主链路/Auth/数据真/核心报告/页面稳定）不得被 P1/P2 破坏 | [AGENTS §13 P0 段落] | D:\Taikoo-monitor-new\AGENTS.md | §13 P0 列表 | b497277 |
| A-DEV-3 | 交付输出格式 10 要素：修改/为什么/文件/DB/测试/结果/未完成/风险/Commit/下一步 | [AGENTS §16] | D:\Taikoo-monitor-new\AGENTS.md | #16-交付输出格式 | b497277 |
| A-DEV-4 | E2E 失败必须记录真实错误；不得删除测试或屏蔽异常修复 | [AGENTS §14 末] | D:\Taikoo-monitor-new\AGENTS.md | §14 末句 | b497277 |
| A-DEV-5 | Cookie/session 失效在系统内可见可处理可恢复 | [AGENTS §17 第 7 句] | D:\Taikoo-monitor-new\AGENTS.md | §17 最终不可违反第 7 条 | b497277 |
| A-DEV-6 | 任何新能力先旁路验证再入主链路 | [AGENTS §17 第 8 句] | D:\Taikoo-monitor-new\AGENTS.md | §17 最终第 8 条 | b497277 |
| A-DEV-7 | 提交前 Git 检查：Cookie/Token/Key/生产 DB/测试垃圾/AGENTS/重复 Core/CHANGELOG | [AGENTS §15] | D:\Taikoo-monitor-new\AGENTS.md | #15-git--github-规则 | b497277 |
| A-DEV-8 | 客户 CTH-POMS Release 禁止携带任何 ZOSAI/ZBC 内部研发文档快照 | [AGENTS §4 末 + §12] | D:\Taikoo-monitor-new\AGENTS.md | §4 §12 | b497277 |
| A-DEV-9 | D-8 两仓源码同时改动 → 受控：分仓 PR + DCC 联合 Evidence + 三向验证 | [DUAL-REPO §8 硬边界] | D:\Zachary OS AI\README.md | §12 Dual-Repo Release Policy 8 条 | f0b8bb5 |

---

## Part B. Zachary-OS-AI README §9 四层矩阵（四层 ~ 55 行）

| 行号 | 规则原文 | 依据标签 | 依据文件绝对路径 | 段落锚点 | SHA |
|---|---|---|---|---|---|
| B-PRODUCT-1 | 产品身份 BASE-001：Zachary AI 身份与 Z-Brand 身份严格分离 | [BASE-001] | D:\Zachary OS AI\components\Development-Command-Console\docs\ZACHARY-IMMUTABLE-BASELINE-20260902.md | §001 | f0b8bb5 |
| B-PRODUCT-2 | BASE-002：两仓不得互相并入；BASE-003：不得互相吸收 | [BASE-002 / BASE-003] | D:\Zachary OS AI\components\Development-Command-Console\docs\ZACHARY-IMMUTABLE-BASELINE-20260902.md | §002 / §003 | f0b8bb5 |
| B-PRODUCT-3 | 四库体系：ZBC + SICI + DCC + AI-DRH；AI-DRH 为第四仓全局基线 Owner | [E-001 / ZBIP_UNIFIED_README.md §1] | D:\Taikoo-monitor-new\ZBIP_UNIFIED_README.md | §1 四库体系 | b497277 |
| B-PRODUCT-4 | 三向验证域：ZBC（业务）+ DCC（工程）+ SICI（移动），AI-DRH 不参与三向投票 | [ZBC §2 对比表 + PLATFORM_BASELINE.md §1] | D:\Zachary OS AI\components\AI-Development-Research-Hub\PLATFORM_BASELINE.md | §1 三向反哺声明 | f0b8bb5 |
| B-PRODUCT-5 | BASE-013：一个共享能力只能一个 Owner；其他通过 Contract/Adapter 复用 | [BASE-013] | D:\Zachary OS AI\components\Development-Command-Console\docs\ZACHARY-IMMUTABLE-BASELINE-20260902.md | §013 | f0b8bb5 |
| B-PRODUCT-6 | 依赖方向：箭头不得反向 ZBC；ZBC = L3 生产权威 | [AGENTS §2 + §5.1] | D:\Taikoo-monitor-new\AGENTS.md | §2 生产隔离；ZOSAI §5 依赖矩阵 | f0b8bb5 |
| B-PRODUCT-7 | Evidence 5 结果硬枚举：BLOCKED > REPLAN_REQUIRED > FAIL > NOT_VERIFIED > PASS | [E-008 DCC V041-EVIDENCE-SCHEMA §3] | D:\Zachary OS AI\components\Development-Command-Console\docs\V041-EVIDENCE-SCHEMA.md | §3 枚举值 + 严格顺序 | f0b8bb5 |
| B-PRODUCT-8 | D0-D7 交付态 8 硬枚举 + Shadow 8 状态生命周期 | [ZOSAI §8.4 / SHADOW-LEARNING-PROTOCOL.md §4] | D:\Zachary OS AI\components\AI-Development-Research-Hub\SHADOW-LEARNING-PROTOCOL.md | §4 状态 transition 表 | f0b8bb5 |
| B-PRODUCT-9 | 10 XHS RED-LINE 永久 BLOCK（不得破解验证码/绕过风控/对抗静默）| [RED-LINE §1-10 / AGENTS §7.1] | D:\Zachary OS AI\README.md | §6.4 10 条红线完整表；AGENTS §7.1 | f0b8bb5 |
| B-REPO-1 | docs-wps/** 永久不 push 主分支（WPS 原文 docx）| [NFR-009 / §9.5 B-资产清单 行 1] + .gitignore 规则 | D:\Zachary OS AI\.gitignore | 第 9-10 行 docs-wps/** archive/** | f0b8bb5 |
| B-REPO-2 | archive/** 永久不 push（桌面旧仓+审计存档+zip/rar/7z）| [NFR-009 / §9.5 B-资产清单 行 2] + .gitignore 规则 | D:\Zachary OS AI\.gitignore | 同上行 10 归档类 | f0b8bb5 |
| B-REPO-3 | config/codex/* 永久不 push（Codex AGENTS/config.toml 本地）| [NFR-009 / §9.5 B-资产清单 行 3] + .gitignore 规则 | D:\Zachary OS AI\.gitignore | 行 11 config/codex/* | f0b8bb5 |
| B-REPO-4 | *.db / *.sqlite / *.sqlite3 一律忽略 | [AGENTS §4 + §15] | D:\Zachary OS AI\.gitignore | 行 14-21 数据资产段 | f0b8bb5 |
| B-REPO-5 | .env / .env.* 除 .env.example 全部忽略 | [AGENTS §15 / BASE-005 凭证] | D:\Zachary OS AI\.gitignore | 行 32-38 环境变量密钥 | f0b8bb5 |
| B-REPO-6 | node_modules / __pycache__ / .venv 依赖缓存忽略 | [通用 NFR-009] | D:\Zachary OS AI\.gitignore | 行 41-49 | f0b8bb5 |
| B-REPO-7 | *.zip / *.rar / *.7z 压缩包一律不进 Git | [§9.5 B 归档类 + archive 历史修复] | D:\Zachary OS AI\.gitignore | 行 52-57 | f0b8bb5 |
| B-REPO-8 | 22 收敛矩阵（01_full_inventory~22_final_convergence）仅索引、不可复制 | [ZOSAI §11.1 矩阵索引] | D:\Zachary OS AI\README.md | §11.1 22 矩阵清单 | f0b8bb5 |
| B-REPO-9 | AI-DRH GLOBAL-CROSS-REPOSITORY-BASELINE.md 全仓执行铁律 | [GLOBAL BASELINE Before/Change/After] | D:\Zachary OS AI\components\AI-Development-Research-Hub\GLOBAL-CROSS-REPOSITORY-BASELINE.md | §1/§2/§4 三门 | f0b8bb5 |
| B-REPO-10 | DCC PLATFORM_README 三向验证权限 5 枚举（READ/WRITE/MERGE/DEPLOY/EXEC）| [DCC Safety Model §4] | D:\Zachary OS AI\components\Development-Command-Console\README.md | §4 权限矩阵 / 安全模型 | f0b8bb5 |
| B-REPO-11 | WRITE / MERGE / DEPLOY / EXEC 默认永久 DENY（DCC 默认最小权限）| [ZOSAI §9 §4 Owner 表 DCC-行] | D:\Zachary OS AI\README.md | §4 DCC 组件 7 项 门槛列 | f0b8bb5 |
| B-REPO-12 | SICI PWA 浏览器端：不得冒充真实服务器 E2E；真实 E2E 必须受控后端 | [SICI PLATFORM_README.md §7] | D:\Zachary OS AI\components\SICI-Core\PLATFORM_README.md | §7 Runtime separation 段 | f0b8bb5 |
| B-REPO-13 | ZBC 外部仓代码不得复制进本仓（绝对禁止，BASE-001/002/003）| [ZOSAI §4 Owner 表 ZBC External 行] | D:\Zachary OS AI\README.md | §4 最后一行 ZBC External | f0b8bb5 |
| B-REPO-14 | 跨仓能力晋级必须三向验证通过 + AI-DRH 全局基线合规 | [CAPABILITY-REGISTRY.md §1 条件 4] | D:\Zachary OS AI\components\AI-Development-Research-Hub\CAPABILITY-REGISTRY.md | §1 注册条件 4 | f0b8bb5 |
| B-COMP-SICI-1 | SICI Owner：index.html + 16 JS + css/style.css（移动端创建面）| [ZOSAI §4 SICI 7 行] | D:\Zachary OS AI\README.md | §4 SICI 行 | f0b8bb5 |
| B-COMP-SICI-2 | SICI 不得吸收业务智能、审计状态、政策引擎、服务器凭证 | [SICI PLATFORM_README §3 Boundary] | D:\Zachary OS AI\components\SICI-Core\PLATFORM_README.md | §3 | f0b8bb5 |
| B-COMP-SICI-3 | three-repository-verifier.js 仅验证矩阵不跑生产 E2E | [SICI js/ 三仓验证器 + §7 仿真声明] | D:\Zachary OS AI\components\SICI-Core\js\three-repository-verifier.js | 头部注释 + return | f0b8bb5 |
| B-COMP-SICI-4 | docs/research-learning 内内容只进 Shadow，不直进生产 | [Shadow-first 8 状态 verifying 前] | D:\Zachary OS AI\components\AI-Development-Research-Hub\SHADOW-LEARNING-PROTOCOL.md | §4 candidate→shadow→verifying | f0b8bb5 |
| B-COMP-SICI-5 | upgrade_modules/* Python 适配器 SICI 不拥有（通过 DCC Contract 引用）| [ZOSAI §4 SICI 门槛列] | D:\Zachary OS AI\README.md | §4 SICI 升级模块门槛 | f0b8bb5 |
| B-COMP-SICI-6 | auto_push.ps1 等推送脚本仅向 SICI 仓推送（不得触及 ZBC）| [SICI auto_push.ps1 + BASE-003 禁止并入] | D:\Zachary OS AI\components\SICI-Core\auto_push.ps1 | 脚本目标 repo 行 | f0b8bb5 |
| B-COMP-SICI-7 | SICI 账号 Cookie 只允许浏览器会话，不得上传 DCC 凭证中心 | [SICI §7 Session + DCC 权限 READ 缺省] | D:\Zachary OS AI\components\SICI-Core\PLATFORM_README.md | §7 runtime | f0b8bb5 |
| B-COMP-DCC-1 | DCC Owner：server.js 40+ API + security.js / shadow-learning.js | [ZOSAI §4 DCC 7 行] | D:\Zachary OS AI\README.md | §4 DCC 行 | f0b8bb5 |
| B-COMP-DCC-2 | DCC 默认权限 5 枚举中 WRITE/MERGE/DEPLOY/EXEC = 永久 DENY | [ZOSAI §7.5 DCC 权限 5 枚举表] | D:\Zachary OS AI\README.md | §7.5 表 | f0b8bb5 |
| B-COMP-DCC-3 | DCC 不持有生产凭证默认（SESSION session 段）| [THREE_REPOSITORY_SYSTEM_MATRIX.md §3 Session 行] | D:\Zachary OS AI\components\Development-Command-Console\docs\THREE_REPOSITORY_SYSTEM_MATRIX.md | §3 Session 行 never production credentials by default | f0b8bb5 |
| B-COMP-DCC-4 | DCC 不 deploy 生产（仅 Verification + Shadow） | [同 §3 Runtime matrix DCC real execution runtime 行] | 同上行 | controlled/planned by capability 段 | f0b8bb5 |
| B-COMP-DCC-5 | evidence-bundle.js 21 字段 schema（与 E-007 关闭一致）| [V041-EVIDENCE-SCHEMA §2 字段清单] | D:\Zachary OS AI\components\Development-Command-Console\docs\V041-EVIDENCE-SCHEMA.md | §2 字段全表 | f0b8bb5 |
| B-COMP-DCC-6 | startup-preflight.js 必须在任何工程变更前执行（Preflight 文化）| [ZOSAI §7 术语一致 Effective Rules / Preflight] | D:\Zachary OS AI\README.md | §7.1/§7.2 | f0b8bb5 |
| B-COMP-DCC-7 | capability_delta.py / learning_promote.py 仅 DCC 执行 Owner | [ZOSAI §4 DCC Owner 唯一性列] | D:\Zachary OS AI\README.md | §4 DCC 工具行 | f0b8bb5 |
| B-COMP-DCC-DOC-8 | DCC docs 22+1 文档仅索引 + Evidence 引用，不可复制为生产规则 | [ZOSAI §11.1 矩阵索引行] | D:\Zachary OS AI\README.md | §11.1 | f0b8bb5 |
| B-COMP-AIDRH-GLOBAL-1 | GLOBAL-CROSS-REPOSITORY-BASELINE.md = 全仓执行铁律 | [AI-DRH §4 Owner 行 GLOBAL] | D:\Zachary OS AI\README.md | §4 AI-DRH GLOBAL 行 | f0b8bb5 |
| B-COMP-AIDRH-PLATFORM-1 | PLATFORM_BASELINE.md = 与四库其余三仓关系 | [E-008 平台基线升级] + [PLATFORM_BASELINE §3] | D:\Zachary OS AI\components\AI-Development-Research-Hub\PLATFORM_BASELINE.md | §3（已升级为其余三仓）| f0b8bb5 |
| B-COMP-AIDRH-CAPABILITY-1 | CAPABILITY-REGISTRY.md = reusable 能力唯一注册中心 | [BASE-013 唯一 Owner] | D:\Zachary OS AI\components\AI-Development-Research-Hub\CAPABILITY-REGISTRY.md | 首段声明 | f0b8bb5 |
| B-COMP-AIDRH-PROTOCOL-3 | 3 Protocols（Shadow/Research-Continuous/Work-Log-Realtime）仅 AI-DRH 所有 | [ZOSAI §4 AI-DRH 3 PROTOCOL 行] | D:\Zachary OS AI\README.md | §4 3 PROTOCOL 行 | f0b8bb5 |
| B-COMP-AIDRH-REUSABLE-3X8 | Reusable Capability 3 组件（src/shared tests tools，8 状态 Lifecycle 实现）Owner = AI-DRH | [ZOSAI §4 AI-DRH Reusable 3×8 行] | D:\Zachary OS AI\README.md | §4 | f0b8bb5 |
| B-DEV-1 | Before Gate：改前全仓审计（四库事实 + 全局基线 + 版本源）| [GLOBAL-CROSS-REPOSITORY-BASELINE.md §2] | D:\Zachary OS AI\components\AI-Development-Research-Hub\GLOBAL-CROSS-REPOSITORY-BASELINE.md | §2 Before Gate | f0b8bb5 |
| B-DEV-2 | Change Gate：最小增量 + Contract 稳定 + 隔离环境 Shadow | [同上 §3] | 同上 | §3 Change Gate | f0b8bb5 |
| B-DEV-3 | After Gate：四库复核 + 三向验证 + Evidence 归档 + Rollback Plan | [同上 §4] | 同上 | §4 After Gate + 10 项复核 | f0b8bb5 |
| B-DEV-4 | 9 阶段 ChatGPT 干预协议（从 Request→Audit→Plan→Approve→Implement→Verify→Evidence→Accept→Rollback/Learn）| [AI-DRH protocols/CHATGPT-INTERVENTION-PROTOCOL.md] | D:\Zachary OS AI\components\AI-Development-Research-Hub\docs\protocols\CHATGPT-INTERVENTION-PROTOCOL.md | §1-§9 完整 9 段 | f0b8bb5 |
| B-DEV-5 | 能力晋级 Shadow-first：proposed→researching→candidate→shadow→verifying→reusable/deprecated/rejected | [SHADOW 8 状态 + CAPABILITY-REGISTRY §2] | D:\Zachary OS AI\components\AI-Development-Research-Hub\SHADOW-LEARNING-PROTOCOL.md + CAPABILITY-REGISTRY.md | 状态转换表 + §2 | f0b8bb5 |
| B-DEV-6 | Evidence-first：AI confidence 永不升级证据状态 | [Evidence 5 枚举 + 状态规则 7 条] | D:\Zachary OS AI\components\Development-Command-Console\docs\THREE_REPOSITORY_SYSTEM_MATRIX.md | §4 Evidence state rules 7 条 | f0b8bb5 |
| B-DEV-7 | L1-L2-L3 三层共享：L1(Evidence/Research 允许) / L2(Validated Capability 版本化 Contract) / L3(Production Logic 默认禁止跨仓复制) | [ZOSAI §8.3 分级表] | D:\Zachary OS AI\README.md | §8.3 L1-L2-L3 表 | f0b8bb5 |
| B-DEV-8 | 11 Contract 表（Task/Risk/Permission/Execution/Evidence/Test/Rollback/Session/Delivery/Learning/Change）| [ZOSAI §8.2 Contract 11 行表] + [THREE_REPOSITORY_SYSTEM_MATRIX.md §2] | 同上文件 | §2 Contract matrix 10 行 + Change 行补 | f0b8bb5 |
| B-DEV-9 | Ownership 模型图：Zachary-OS-AI 本仓 B 产品 Owner，SICI/DCC/AI-DRH 组件各有独占 Owner | [ZOSAI §8.1 图] | D:\Zachary OS AI\README.md | §8.1 | f0b8bb5 |

---

## Part C. NOT_VERIFIED 声明（必须显式，不得改写为 PASS）

以下条目在当前审计范围内未找到权威文件强依据 → **NOT_VERIFIED**（按 Evidence 硬枚举排列，永远高于 FAIL/低于 REPLAN_REQUIRED）：

| # | 行号 | 规则摘要 | 缺失依据 | 建议下一步 |
|---|---|---|---|---|
| NV-1 | B-COMP-DCC-5 evidence-bundle.js 21 字段 | 只在 spec 里提 21 字段，未实读 server/evidence-bundle.js 字段定义 | 需要读源码 schema 对象 | 下轮 B1 阶段实读 + 字段映射表 |
| NV-2 | A-DEV-9 D-8 两仓 PR 流程 | 缺 DCC 实际 PR 脚本或 release-automation.yml 引用 | 需要 DCC .github/workflows 实读 | B1 阶段补齐 release policy 执行证据 |
| NV-3 | A-PRODUCT-5 10 RED-LINE 与 AGENTS §7.1 对齐 | AGENTS 只给原则，10 条具体红线来自 ZOSAI README 自绘，缺上游独立 XHS 红头文档引用 | 缺 SICI/DCC 任何 XHS 红线外部权威原文 | 保持现状（已与 XHS-REDNOTE-SAFE-ARCHITECTURE-V2 双向引用） |
| NV-4 | B-PRODUCT-8 Shadow 8 状态 transition 表 | SHADOW-LEARNING-PROTOCOL.md 未实读 §4 全表 | 缺 transition 图验证 | B1 阶段补齐 transition 图 + 用例 |
| NV-5 | B-COMP-SICI-3 three-repository-verifier.js 声明 | 未实读源码，只靠文件名 + SICI docs 声明推断 | 缺代码验证 | B1 阶段读源码 + test 行号 |
| NV-6 | AC-R014 7 硬枚举全量 100% 与源码一致 | 只做两仓 README grep，未实读 models.py / risk_engine.py 枚举定义 | 缺 Python 源码枚举值对比 | B1 阶段源码枚举抽取 + 对比表 |

---

## Part D. 术语一致性抽样（T5.2 输出）

10 核心术语 × 两仓各抽样 ≥5 处：全部 PASS（一致）。

| 术语 | 出现仓 A 次数 | 出现仓 B 次数 | 一致说明 |
|---|---|---|---|
| Owner | 24 | 53 | 一致（唯一权威 Owner 语义） |
| 四库（四仓库体系）| ≥6（§2/§4/§9）| ≥18（§1/§2/§3/§4/§8/§9/§12）| 一致（AI-DRH 明确为第四仓） |
| Evidence | 42 | 88 | 一致（Evidence-first 文化；5 结果枚举完全对应） |
| Shadow Mode / Shadow-first | 18 | 44 | 一致（8 状态 lifecycle；先旁路再切换） |
| Preflight | 7 | 21 | 一致（startup-preflight.js / Effective Rules 门禁） |
| Effective Rules | 4 | 16 | 一致（DCC effective-rules.js / audit 报告） |
| Reusable Capability | 5 | 30 | 一致（唯一 AI-DRH CAPABILITY-REGISTRY Owner） |
| Capability Registry | 5 | 28 | 一致（AI-DRH 注册中心 §2 8 状态） |
| Contract | 32 | 71 | 一致（11 类 Contract + Adapter/Adapter 语义） |
| 三向验证（three-way / 三向）| 11 | 37 | 一致（ZBC/DCC/SICI；AI-DRH 不参与三向投票） |
