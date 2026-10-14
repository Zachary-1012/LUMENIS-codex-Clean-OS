# 序境 / LUMENIS 全产品规划对照表（替代 plan-map.md）
原规划采样：origin/main `72c96d94`（#35，2026-10-13 18:04 Asia/Shanghai）；当时主路径 `25a08341` 及20处他人在途修改仅为历史基线。当前发布版本和受保护工作树分别见 CURRENT；本文是完整要求，阅读/采用不等于实现或验收。

## 0. 已读文件（证明覆盖范围）
| 文件 | 行数 | 读法 |
|---|---|---|
| README.md | 134 | 全文 |
| AGENTS.md | 1807 | 全文 |
| LUMENIS-CODEX-TAKEOVER-CURRENT.md | 120 | 全文 |
| AI-NATIVE-PRODUCT-CONSTITUTION.md | 92 | 全文 |
| LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md | 749 | 全文 |
| LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md | 1024 | 全文 |
| LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md | 205 | 全文 |
| SECURITY-BOUNDARY-CURRENT.md | 31 | 全文 |
| LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md | 480 | 全文 |
| AI_PROVIDER_FAILOVER_POLICY_V1.0.md | 360 | 全文（文件自己标注为 SUPERSEDED，仅作历史） |
| USER-ADDITIONS-20261004.md | 103 | 全文 |
| config/ai-quota.json | 26 | 全文 |
| LUMENIS-EXPERIENCE-CONSTITUTION.md | 1648 | 全文逐句（a8ffdc2b，10-13 23:xx 补读 1-407、510-1648） |
| LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md | 1515 | 全文逐句（补读 61-1471） |
| SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md | 771 | 全文逐句（补读 1-222、351-771） |
| 44 份屏幕规格＋README＋TEMPLATE（8146 行/781KB） | 8146 | 全文逐句（S1–S16，逐份一批，notes/batch-notes.md） |
| 其余 00-GOVERNANCE 文件（≈7000 行） | ≈7000 | 全文逐句（B1–B9） |
| feature_registry.md/.csv、schema_registry_t4.csv、function_registry_canonical_t4.csv、ROOT-PYTHON-CALLER-INVENTORY-ROUND-02.md | 393/335/737/32/289 | 全文逐行（R1–R5；CSV 全列统计＋逐行，含源码抽查） |

覆盖说明：全部文件已分批逐句/逐行读完，进度见 notes/batch-notes.md。

全文已读合计 5131 行。
| 补读 B5–B9 | CODEX-ZERO-AUTH、R03-CHARTER、GOV-MACHINE.json、LAUNCH、BRAND-ECO、DUAL-CORE、R02-CHARTER、ENG-EVOL、PROD-ACCEPT、THIRD-PARTY | 是（逐行） |
| 44 屏 spec | S1–S16 逐句 | 是 |
| 注册表＋caller 清单 | R1–R5 逐行 | 是 |

## 1. 优先于旧文档的 PO 新指令（与旧文冲突时以新指令为准）
| # | PO 新指令 | 被覆盖的旧文 | 依据 |
|---|---|---|---|
| O1 | 自动采集范围＝全部已登记主体 | GLB:61「太古汇是参考主体」原本没错，但 `.env` 只配了 TKH；ai_filter.py:142-146,245-354、ai_governance.py:48、ai_task_parser.py:152 把太古汇写死了 | PR #36（open） |
| O2 | 所有平台登录统一走产品内弹窗（序境 UI），采集在后台无窗口运行；失效才弹出 | 与 EXP §11.1:478-508（LumenisPlatformRecoverySheet）和 ARCH:117,737 **一致**。现有实现仍会弹外部浏览器，这是实现缺陷，不是规则问题 | A:1799、EXP:441-444 |
| O3 | 研发阶段配置直接改，不问 PO | A:442「新的敏感来源、新权利……须 PO 批准」仍有效；CUR:15「`--apply` 需要 CONFIG_MODIFY 精确审批」→ 研发阶段由开发自己执行（需写回 CURRENT） | PO 直接指令 |
| O4 | CI 全绿即可合并，不等 PO | A:59 原文要求 required checks → merge，与新指令不冲突，只是去掉了等待 PO 这一步 | 已存入 memory |
| O5 | 品牌名只用官网名，并记录来源 URL | 旧种子里的翻译名 | #34 record_official_name |
| O6 | 新增主体由开发自己做端到端测试，并加进 CI | GLB:79-81 原本就要求有真实用户新增路径 | PO 直接指令 |
| O7 | 账号、两类开发者模式、商业六项、视觉、Logo、角色与前端均闭环内，普通工作无账号墙；仅真实用户验证与付费/授权来源上线后 | AGENTS / CURRENT / MASTER-CHECKLIST | PO 2026-10-14直接指令 |

## 2. 全产品模块对照表
负责人：阿康＝前端/采集/主体（F、C1）；阿康1＝后端（C2/C3/C5/C6 的 API 部分）；Codex＝与两人同级，由 PO 分工（A:55）。

| 模块 | 规划要求（出处） | 现状（已核实） | 差距 | 负责 | 阶段 |
|---|---|---|---|---|---|
| **SYSTEM 采集** C1 | 六个主平台都要持续采集：IG/FB/公众号/小红书/抖音/X（GLB:252、A:1605）；不设统一起始日期（GLB:278）；每帖只取一张封面（GLB:419）；采后再做关键词分析（GLB:418）；平台之间同权（ARCH:705）；一个平台故障只影响它自己（A:301）；由调度器持续运行，不靠 Codex 手动触发（GLB:290-297） | 已入库：x 763、public_http 225、douyin 66、xhs 3（停在 9/30）、ig 1；FB 和公众号为 0。`collect_20261013_172257` 状态 BLOCKED，入库 0 条 | 小红书没有绑定香港/国际身份；FB、IG、公众号没有采集；COLLECTOR-P0-01..05、FND-01..03 都没有闭合（SOI:400-411） | 阿康 | 闭环内 |
| SYSTEM 采集身份 | 小红书只能用香港/国际白名单身份，禁止碰大陆个人号和 9222 端口（A:1278-1287）；会话失效时在产品内给出重新登录入口和恢复（A:1272） | 9223 受管浏览器里没有可用登录 | 需要在 9223 的隔离 profile 上完成一次 HK/国际号登录（这一步需要人扫码，属于规则允许的“明确的人工步骤”，A:1634） | 阿康（发起），PO（只扫码） | 闭环内 |
| SYSTEM 平台恢复弹窗 | 统一一个 LumenisPlatformRecoverySheet，支持扫码、受控浏览器登录、验证和冷却状态；只弹一个、按队列排；恢复后由服务端读回健康状态再续跑（EXP:478-508、A:1373） | 没有实现；小红书现在弹外部浏览器 | FND-03 要整体实现：停掉外部弹窗，改成后台 headless 运行，失效时弹 sheet | 阿康（F+C1），阿康1 提供 session API | 闭环内 |
| SYSTEM 内置浏览器 SYS-06 | 产品内显示真实页面，可人工独占接管、停止、返回原任务；外部打开只能由用户主动选；不做通用 OS 控制（A:1794-1805、ARCH:113-120,733-741、EXP:408-467） | #35 已合并实时画面流 | 运行加载和用户验收为 NOT_VERIFIED；任意点击/输入、来源 Artifact、远程安全访问仍未闭合（SOI:981） | 阿康1 | 闭环内 |
| SYSTEM 主体登记 | 用户可以新增、搜索、聚焦、清除主体，默认 GLOBAL/ALL（GLB:27,67-81）；14 个国家分类（GLB:110）；闭环前的数据源＝610 条种子＋太古汇场内分布（GLB:125） | 共 903 个主体；216 条 TENANT_OF 关系待审；#34 官网名功能已合并 | 4 个官网名还没写入，小米待核实；133 条关系候选、78 个暂缓主体、8 个同名暂缓待处理；新增主体还没有端到端测试和 CI | 阿康 | 闭环内 |
| SYSTEM AI Gateway | 唯一 Gateway，只用自有模型；智谱、Ollama、Jev 等已退役，不调用、不探测、不回退（A:907,1074-1086、ARCH:510-517）；基础业务不依赖 AI（ARCH:327） | 返回 UNAVAILABLE 是正确行为；自有模型 NOT_BOUND（SOI:984） | 训练需要 MODEL_TRAIN 权限、确认空闲 GPU，以及配方和数据哈希（A:293-298），目前没有已批准的模型 | 阿康1 | 闭环内（训练需授权） |
| SYSTEM 运行与安全 | 8201 端口、/healthz、监督进程；五层安全护栏（SEC:7-11）；F-01..F-12 审计修复（SOI:956-967） | 8201 健康；ZBrand-HealthGuard 守护任务已装，但 18:00 那次报错 | 查守护报错原因；F-01/02/03/05/06/10 的 P0 未核实 | 阿康1 | 闭环内 |
| **CTH** C3 | 主体→监测、事件、风险→Case→判断→行动→结果→报告→保存/修订/恢复（ARCH:55-62、SOI:676） | 有 SourceBrief 统计；#31 合并的是 WIP（标题标明未完成） | 完整的业务分析、报告和恢复都没有验收 | 阿康1 | 闭环内 |
| **BMP** C3 | 品牌、竞品、创作者、传播、Campaign、评价（ARCH:64-71、SOI:677） | 部分完成 | 同上 | 阿康1 | 闭环内 |
| **Shared 研究** C5 | 不要求先建 CTH/BMP 就能独立研究；引用可定位；SavedWork 有版本（ARCH:73-80） | 有导入、引用、SavedWork；有 DOCX/XLSX/PPTX 校验 | 独立入口、引用撤回、同一版本的真实操作都没有验证 | 阿康1 | 闭环内 |
| Shared 提案/视频/播客 C4 | 三类分别验收：可编辑成品、真实渲染和试听（ARCH:82-111、SOI:683-687） | Timeline、渲染、导出有历史成果；不再要求勾 demo | 独立新建→编辑→导出→重开的完整链没有验收 | 阿康1（后端），阿康（界面） | 闭环内 |
| Shared 检索 | cosine＋BM25＋融合＋cross-encoder 精排（ARCH:153-161） | 没有核实 | 需要真实模型和效果证据 | 阿康1 | 闭环内 |
| **Agent / 自研 AI** C2 | 取消/恢复、Skills 商店、Memory、受控学习（SOI:224,669-672） | 首页聊天提交以前是 `onPressed:null`（UA:28）；#31 正在补 | AI-01 提交链、SH-06 收件箱、决策卡回执 | 阿康1 | 闭环内 |
| **四表面** F | 官网 Astro、Web、Win/macOS、iOS 并行建设、各自验收；后三者共用一套 Flutter 实现（README:54、MSD:17）；打开工作区直接进入聊天首页（ARCH:124）；中英韩三语和无障碍（SOI:230） | 有官网基础版、Flutter Web 和 /workspace | 前端功能与后端并行闭环开发 | 阿康 | 前端功能与视觉风格/logo/角色图均闭环内（与后端并行，按 sketches/UI-STEP-PLAN.md 分步建设） |
| 品牌与角色 | Pim/Bram/Ness/Jas/Aris；AI 水印；logo 带名/不带名两版（UA:90-104） | 已登记 | 随前端分步建设（UI-STEP-PLAN 第 F12 步） | 阿康 | 闭环内 |
| 小插件进度 | 只有一个进度入口，即 CURRENT（CUR:7） | 正在改成读 CURRENT | 需要合 PR | 阿康 | 闭环内 |

## 3. 常见决策的规则答案（直接照做，不要问 PO）
| 遇到的情况 | 规则答案 | 出处 |
|---|---|---|
| Gateway 绑哪个模型？ | 只绑自有模型；没有模型就返回 UNAVAILABLE；禁止回退到第三方 | A:907,1074 |
| 要不要调智谱/豆包？ | 不要，已退役 | ai-quota.json:4、AIPOL:10-16 |
| 平台登录失效怎么办？ | 产品内 RecoverySheet；扫码/登录后服务端读回健康状态再续跑；不弹外部浏览器 | EXP:478-508 |
| 小红书用哪个号？ | 只用香港/国际白名单号；大陆个人号绝对不碰 | A:1280-1287 |
| 遇到验证码/风控？ | 研究合法的恢复方式；不绕过；只停这一个平台，其他继续 | A:1627-1634 |
| 采集范围？ | 全部已登记主体（O1）；按话题和任务语义；不设起始日期 | GLB:278、PR#36 |
| 缺失值？ | 显示“—”加原因；真实的 0 才显示 0 | A:1224-1246 |
| 品牌名？ | 用官网名并记录来源 URL；同名暂缓；不改别人的品牌名 | O5、CUR:15,50 |
| 配置或写库审批？ | 研发阶段开发自己执行，写回 CURRENT（O3）；写前必须先备份 | O3、A:1252 |
| 合并 PR？ | CI 全绿就合并（O4） | A:59 |
| 保护活动分支？ | 不切换或修改 akang/auto-scope-all-subjects；本次在origin/main新分支的临时隔离工作区处理，保留其全部dirty | PO 2026-10-14 |
| 遇到外部 API/框架的 bug？ | 查官方文档和 GitHub，然后自己修 | A:651-674 |
| 要不要新加第三方组件？ | 放在 adapter 后面，许可证查清楚并登记 | A:1503-1526 |
| 训练、花钱、部署？ | 需要 PO 单独授权（真实阻塞） | A:186,1581 |

## 4. README 缺口与替换文案（定义性内容，不写日期进度）
| # | README 现状 | 问题 | 建议替换文案 |
|---|---|---|---|
| R1 | 76-85 阅读顺序缺少机器合同、Multi-Surface、Real Delivery、Global、Positioning、Security | 和 A:450-466 不一致 | 「开发阅读顺序：AGENTS.md → 00-GOVERNANCE/LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json → LUMENIS-CODEX-TAKEOVER-CURRENT.md（唯一接续入口）→ AI-NATIVE-PRODUCT-CONSTITUTION.md → LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md → LUMENIS-EXPERIENCE-CONSTITUTION.md → LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md → LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md → LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md → LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md → SECURITY-BOUNDARY-CURRENT.md → 对应合同与源码」 |
| R2 | 没有写明“唯一闭环入口” | 缺少 PO 要求的唯一化说明 | 「所有开发者（Codex、阿康、阿康1）都从 CURRENT 开工：规则 → CURRENT → 分支 → 测试 → PR → Product Gate + App Gate 全绿 → 合并 → 本地主路径与 origin/main 一致。只用一个本地路径，不建额外 worktree。」 |
| R3 | 118 行“经过审阅的 PR” | 缺少全绿即合并 | 「必需检查全绿即可正常合并；禁止强推和绕过检查。」 |
| R4 | 缺五轮交付顺序 | ARCH:244 有 | 「产品交付按五轮：SYSTEM → CTH → BMP → Shared → Agent Groups/自研 AI；这是研发与验收顺序，不是用户必须走的流程。」 |
| R5 | 缺 AI 路线 | A:907 | 「产品 AI 只经过唯一 SYSTEM AI Gateway 调用序境自有模型；Ollama、智谱、Jev 等已退役，不调用也不回退；模型不可用时如实显示不可用。」 |
| R6 | 缺采集定义 | GLB §10、O1、O2 | 「SYSTEM Collector 对全部已登记主体按话题和任务语义持续采集，六个主平台为 Instagram、Facebook、微信公众号、小红书、抖音、X；采集在后台无窗口运行；平台登录失效时在产品内弹出统一恢复面板，不自动打开外部浏览器；小红书只使用香港/国际授权身份。」 |
| R7 | 107 行只写了 /healthz | 缺端口 | 「Core 默认在本机 8201 端口，健康检查为 http://127.0.0.1:8201/healthz。」 |
| R8 | 结构表缺 `config/`、`data/`（不入库）和 `intelligence_library/` | 结构不全 | 补三行：`config/` 运行配置与种子；`data/monitor.db` 唯一业务库（不入 Git）；`intelligence_library/` 研究资料（历史出处，不作执行规则）。 |
| R9 | 缺主体登记定义 | GLB:27,79 | 「默认范围为 GLOBAL/ALL；用户可以搜索、新增、聚焦、清除商业主体和品牌；选中某个主体不等于获得权限，也不会自动启动采集；品牌名只记录官网名称。」 |

## 5. 44 屏现状（按 frontmatter 状态，2026-10-13 a8ffdc2b 复核）
合计 44：BLOCKED 20｜REVIEWED_FOR_SCOPE_BLOCKED_SLICE 1（BMP-01）｜OWNER_REVIEW 6（BMP-06～11）｜DESIGN_READY 4（ACC-01/03/04、SYS-05）｜APPROVED 1（SYS-01）｜DESIGN_EXPLORATION 5（SYS-02/03/04/07/08）｜IMPLEMENTED_* 7（SH-01～06、SYS-06）｜ACCEPTED 0

| 组 | 屏幕 | 状态 | 主要阻塞 |
|---|---|---|---|
| ACC（4） | 01、03、04 | DESIGN_READY | BLOCKED_PENDING_LIVE_RUNTIME_E2E |
| | 02 | BLOCKED | 缺新增主体写入合同与真实 E2E（ACC-02:224,315） |
| AI（5） | 01～05 | BLOCKED | GAP-029/030；AI-05 以 AI-01 诊断作"显式 fallback"（AI-05:23-40） |
| BMP（11） | 01 | REVIEWED_FOR_SCOPE_BLOCKED_SLICE | GAP-018 |
| | 02～05 | BLOCKED | GAP-019..022 |
| | 06～11（含 08 播客） | OWNER_REVIEW | GAP-023..028 actor→BrandFocus 读取合同；08 正文另记 Shared/C4 播客范围阻塞 |
| CTH（10） | 01～10 | BLOCKED | GAP-005..016 |
| SH（6） | 01 | IMPLEMENTED_CATALOG_ONLY_EVIDENCE_SCOPE_BLOCKED | Evidence 范围 |
| | 02～06 | IMPLEMENTED_SCOPE_GUARDED_*（后端范围/效果/只读未验证） | SH-02 打开原文走 SYS-06 |
| SYS（8） | 01 | APPROVED | latency 无实现（SYS-01:139） |
| | 02、03、04、07、08 | DESIGN_EXPLORATION | 03/04/08 PO 批准 PENDING |
| | 05 | DESIGN_READY | Sys05Screen 仍留旧 no-scope fallback（SYS-05:55） |
| | 06 | IMPLEMENTED_SOURCE_LIVE_NOT_VERIFIED | §0.3 交互目标 OPEN |

注：SCREEN_SPEC_TEMPLATE 自身 status=DESIGN_EXPLORATION、README 无状态，不计入 44。

## 6. 本轮新发现的差距和文档冲突
| # | 发现 | 出处 | 建议 | 负责 |
|---|---|---|---|---|
| N1 | 旧收敛文件仍写“当前运行面：Zhipu + Local AI 并行” | PRODUCT-CONVERGENCE-MASTER-V1-20260906 | 与 AGENTS:907（退役）冲突。文件头加 SUPERSEDED 标注 | Codex |
| N2 | 双核架构文件写有 Linux 平台、OSAI `git_commit_push` 红线、Windows 硬编码 | INTELLIGENCE-OS-DUAL-CORE-v1.0 | Linux 已移出范围、通用 OS 控制已撤回。标注为历史 | Codex |
| N3 | 主体权限审计显示 IMPLEMENTATION NOT STARTED | SUBJECT-PERMISSION-AUDIT-ROUND-05 | 与 ACC-02 写入合同一起闭合 | 阿康1 |
| N4 | 数据库权威审计显示 LEGACY SMOKE BLOCKED / NOT LIVE VERIFIED | DATABASE-AUTHORITY-AUDIT-ROUND-03 | 对 monitor.db 做一次 live 复核 | 阿康1 |
| N5 | 身份边界审计显示 PACKAGED UI UNVERIFIED | IDENTITY-BOUNDARY-AUDIT-ROUND-04 | 各端打包后验证 | 阿康 |
| N6 | 只有 SHARED-COLLECTOR:229 明确“目前不假设有官方 API”，采集必须靠合法的已授权 R&D 账号、会话、公开页等证明真实数据 | COLLECTOR:229-239 | 写进采集验收口径 | 阿康 |
| N7 | 平台扩展退出合同共 8 条，包括 Manifest、可调用、会话状态、NULL 语义、事务、防重复、如实覆盖、结果到达消费方 | COLLECTOR:336-349 | 六平台逐条对照 | 阿康 |
| N8 | BMP 06-11 的共同根因是没有 actor→BrandFocus 读取合同 | BMP-06:84 等 | 由一份后端合同解锁 6 屏 | 阿康1 |
| N9 | 播客和视频的普通操作验收有逐步清单（波形、混音、导出、重开） | REAL-DELIVERY:1486-1487 | 作为 C4 退出清单 | 阿康1 / 阿康 |
| N10 | 多数屏幕的 Figma 资产状态为 NOT_VERIFIED | 各屏规格 | 与 logo/视觉风格一起闭环内处理（O7） | 阿康 |

## 7. 文档更新（PR #41，取代 #37）
README R1-R9；CURRENT 新增 2026-10-13 PO 直接指令 8 条（含闭环内/后划分），并删除 `--apply` 需 CONFIG_MODIFY 审批的表述；GLOBAL 的 MANUAL 默认上方加研发 AUTO 覆盖说明；3 份旧权威文件标注 SUPERSEDED（N1/N2，以及 ENGINEERING-GOVERNANCE V1.0）。2026-10-14 起产品账号体系闭环内。


## 8. 2026-10-13 补读新增差距（origin/main a8ffdc2b）
| # | 模块 | 差距 | 出处 | 负责 | 阶段 |
|---|---|---|---|---|---|
| G1 | 内置浏览器/Open Original | SourceTarget v1 仍只绑旧外部适配器，未满足“默认 SYS-06 内置打开” | EXP:773 | 阿康(F)/阿康1(C6) | 闭环内 |
| G2 | 采集平台矩阵 | 需逐平台 PLATFORM LIVE CAPABILITY MATRIX（17 类来源×19 字段），未建 | RD:648-714 | 阿康 | 闭环内 |
| G3 | 失败演练 | 9 类故障演练＋RUNTIME FAILURE MATRIX 未做 | RD:598-639 | 阿康1 | 闭环内 |
| G4 | 权限场景 | 用户A/B 跨 Subject 读、缺 actor 等 8 项验证，随账号体系同步完成 | RD:540-589 | 阿康1 | 闭环内 |
| G5 | 屏幕矩阵 | 44 屏 SCREEN DELIVERY MATRIX 分类未出 | RD:1062-1075 | 阿康 | 闭环内 |
| G6 | 最终七状态 | 7 状态＋3 覆盖维度结论未出具 | RD:1163-1195 | 阿康 | 闭环内 |
| G7 | 研究门 | 每成果卡须含 CONTINUOUS FRONTIER RESEARCH（ADOPT/ADAPT/DEFER/REJECT） | RD:351-359,1297 | 全员 | 闭环内 |
| G8 | Collector | 原生分页游标与 query 级 checkpoint 需分开持久化；只调 search 不算 detail/评论续采 | COL:192-204 | 阿康 | 闭环内 |
| G9 | Collector | CAPTCHA/风控流程 Detect→Stop→Record→熔断→冷却→健康检查→合法验证后恢复 需实证 | COL:564-574 | 阿康 | 闭环内 |
| G10 | 内容学习 | 凉子访谈录 60 集 20/20/20 验收数据集链路未跑 | COL:651-688 | 阿康1 | 闭环内 |
| G11 | ApplicationTrace | 产物须记录 learning_asset/pattern/evidence/model_version/prompt_contract_version | COL:485-507 | 阿康1 | 闭环内 |
| G12 | 视频/播客 | 横向时间轴 pan/seek 分离、轨道同步、平移不改工程 | EXP:1235-1246、RD:1354 | 阿康 | 闭环内 |
| G13 | Read Aloud | 本地朗读 0.75/1/1.25×，单会话，源变更即停 | EXP:1219-1233 | 阿康 | 闭环内 |
| G14 | 智能UI | 9 条逐步交付合同（首个有用结果、分段身份/修订号、旧 run 不覆盖、延迟计量）；新增结果到达动效按Experience §19：原有动效全部保留，真实结果/字体/布局就绪后测量点阵线框并一次揭示；等待用普通骨架，不在切页/每行列表重复；独立全量/随减少动态偏好/关闭选择及立即跳过，未生成/重开不冒充生成 | EXP:1343-1359 | 阿康1(C2/C6)/阿康 | 闭环内 |
| G15 | 三语 | zh-CN/en/ko 任一缺失该屏不得验收 | EXP:643-651 | 阿康 | 闭环内（前端功能，与后端并行） |
| G16 | 性能/无障碍 | 60fps、p95≤16.7ms、WCAG 2.2 AA、200% 字号 | EXP:1083-1089 | 阿康 | 闭环内（含视觉微调） |
| G17 | 训练 | 真实 optimizer step/loss/checkpoint/reload/held-out 才算训练；付费算力需 PO 授权 | RD:1360-1366,1384 | 阿康1 | 闭环内（PO 授权） |
| G18 | 账号/ACC-01/04 | 账号体系：通用邮箱验证码注册、Google 登录（现在启用）、Apple 登录（取得 Apple Developer 账号 $99/年后启用，此前按钮不显示）；登录 OAuth 只用免费方式，属 AGENTS 零授权条款的明文例外；同邮箱不同方式归同一账号；参照 ChatGPT 设置的信息结构（参照结构不是克隆，宪法条款已原位改写；通用/账号/安全-设备与会话-退出所有设备/模型与API/连接器/用量/数据控制/关于）；“改进模型”首次使用时询问，无预设；导出限时链接；删除账号 30 天内可撤销；无通行密钥、无二次验证；不设账号墙，未登录全部功能可用；账号开发与其他研发并行、不阻塞 | EXP:376,1044；PO 2026-10-14 | 阿康1(C)/阿康(F) | 闭环内 |
| G19 | 商业六项 | 数据合规（来源清单、保留期限、脱敏、合规报告）、密钥（安全存储、轮换、撤销）、工作区/租户生命周期（备份、恢复、归档、删除、多成员）、运营（指标、告警、诊断包）→ COMMERCIAL_READY；屏 SYS-04/SYS-08 | RD:1265-1291 | 阿康/阿康1 | 闭环内 |
| G20 | 开发者模式 | 两类：(a) 用户开发者模式——用户可自行开发/修改产品，开启前须接受风险与法律责任自担的协议（协议文本上线前须法务审核，未审核不得启用）；可关闭恢复受限状态；账号数据备份与恢复；(b) 创始人内部开发者模式——一键上传代码更新、跑测试、测试全绿才发布、签名分批自动更新、可回滚 | EXP:1248；PO 2026-10-14 | 阿康1(C)/阿康(F) | 闭环内 |
| G21 | AI 六项 | Chat Memory/Context/Tool Calling/Skill Registry/Evaluation/Model Routing 全 VERIFIED 才算 AI Chat 完成 | AICL:1-60、PA:134 | 阿康1 | 闭环内 |
| G22 | 屏幕状态 | 44 屏：BLOCKED 20＋BMP-01 范围阻塞 1、OWNER_REVIEW 6、DESIGN_READY 4、APPROVED 1、DESIGN_EXPLORATION 5、IMPLEMENTED_* 7；无 ACCEPTED | 各 spec frontmatter | 阿康 | 闭环内 |
| G50 | BYO-API 接口 | AI Gateway 保留一个通用 OpenAI 兼容外部模型接口，用户可选填自购 API key；默认自有模型、产品不主动调第三方、无自动回退；出口：未配置=不调用，配置后仅用户显式选择时调用并留回执 | Gateway | 阿康1 | 闭环内 |
| G51 | A-SYS 采集/浏览器 | 合法登录→后台任务→人工验证→同任务恢复→Evidence/Canonical→前端结果；多平台无窗口重启恢复同版实证 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G52 | A-CTH | 商业问题+时间/预算→有用分析→Decision/Action/实际结果→报告保存重开；数据不足不冒充因果 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G53 | A-BMP | 610/137/185 生产注册、跨品牌权限、品牌-门店-作者归属、真指标报告、关系证据回读 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G54 | A-Shared研究 | 自有资料→索引/查询/引用片段/版本/导出；来源撤回修订可追溯 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G55 | A-Shared制作 | 无前置新建→编辑→预览试听→可编辑工程+成品→导出→重开修订；视频、播客分别验收 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G56 | A-AI-01/Agent | 首页同一对话可持续追加独立任务、补充或停止指定任务，及时确认真实接收，不等待长任务结束；后台沿既有Task/Agent调度，短问答可直接返回。每个子任务保留原actor/scope/来源版本、取消/恢复和可读回成果；AI不阻断无AI业务。界面交付结果/依据/可选动作，不展示私有推理链；对应完整采用与验收见§16 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G57 | A-SH-06 | 现有SH-06承接同一对话后台任务的成果、必要失败与人审，授权见应见、不见越权；点开返回原任务和已提交版本，支持断线后读回。普通进度可查询但不逐步刷消息，结果通知去重；已发/待发/失败与业务完成分别记录，不把通知成功当任务成功 | 审计补录 | 阿康/阿康1 | 闭环内（授权账号随账号体系同步） |
| G58 | A-四表面 | 官网/Web/Win/macOS/iOS 安装启动、工作流、保存恢复、权限、语言分端实测（前端功能与后端并行） | 审计补录 | 阿康/阿康1 | 闭环内 |
| G59 | A-GAP54 | 34 PARTIAL/15 UNSCOPED/4 ABSENT（AI-03 持久对话、SH-01 Pattern 检索、Fact Wall 逐 Claim 验证、SH-01 持久 AI 对话）/1 LOCAL_ONLY | 审计补录 | 阿康/阿康1 | 闭环内 |
| G60 | B 效率 | 记录工时/token/修复次数/任务时长，未测前不宣称提效 | 审计补录 | 阿康/阿康1 | 闭环内起测 |
| G61 | D 组合价值 | 不重复上传/解释品牌时间预算；来源随成品版本传递；上游变更只重做受影响部分；媒体保留可编辑时间轴 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G62 | E2 商业体运营 | 多门店多品牌归属错位、周月报重复 → 可追溯关系、异常/活动可解释、复用来源 | 审计补录 | 阿康/阿康1 | 闭环内首例（CTH） |
| G63 | E2 品牌市场/代理 | 研究→策略→提案→修改→归档跨工具 → 单项目保留引用/版本/审批/工程 | 审计补录 | 阿康/阿康1 | 闭环内首例（BMP+Shared） |
| G64 | E2 内容/播客工作室 | 素材/脚本/时间轴/字幕/渲染割裂 → 独立 Shared 导入编辑试听导出重开 | 审计补录 | 阿康/阿康1 | 闭环内首例（独立 Shared） |
| G65 | E2 独立研究者 | 多国数据去重引用权利成本 → 无外部 AI 可用、权利明确、成本可预测 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G66 | E3 商业模式 | 工作空间订阅/数据包订阅/项目制部署；测 单账户收入、CAC、留存、数据授权与调用成本、单任务算力存储、人工审核、支持工时、使用频率、节省时间 | 审计补录 | 阿康/阿康1 | 测量能力闭环内（并 G48）；付费与授权定价上线后 |
| G67 | E4 价值链 | 本人长期用→痛点→合法任务→成果→有界更新→交付重开→对比原流程→外部复现→付费/留存/融资 | 审计补录 | 阿康/阿康1 | 产品链路闭环内；真实用户验证、付费与融资上线后 |
| G68 | E5 来源授权 | 每来源许可/范围/频率/转载训练权/撤回恢复；不绕反爬验证码 | 审计补录 | 阿康/阿康1 | 闭环前风控开启时验收 |
| G69 | E5 身份可信 | 官方名称 URL、去重冲突、TENANT_OF Evidence、跨域隔离、合规刷新 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G70 | E5 运行成本 | 单任务日志、每平台错误率、人工登录次数、成本、重启恢复时长 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G71 | E5 成果质量 | 跨端真人 E2E、文件可编辑、重开版本正确、满意度/返工 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G72 | E5 竞争分销 | 细分场景可重复优势案例 | 审计补录 | 阿康/阿康1 | 闭环内 |
| G73 | E5 公开仓库 | 依赖许可审查；原始文件/私人会话/密钥不入发布或训练（并 G47） | 审计补录 | 阿康/阿康1 | 立即/闭环内 |
| G75 | H 四闭环 | 工程结构、AI 模型、真实用户工作、商业变现 分别验收，互不替代 | 审计补录 | 阿康/阿康1 | 工程闭环内；AI 模型需训练；商业变现能力闭环内，真实用户与付费验证上线后 |
| G76 | 内容结构（XHS） | Shared 制作提供类型化结构骨架（种草/情绪/知识/活动/短视频 Hook→场景→细节→判断→轻 CTA；短视频 0-3s/3-10s/10-25s/25-40s/40-60s 节奏）与 8 角度标题；出口：用户选类型生成可编辑大纲，非固定模板 | R0914-C01；BMP/KOS 规范在仓 | 阿康/阿康1 | 闭环内（并 G33/G38） |
| G77 | 人设与 Brief | 账号 persona（受众/支柱/口吻/禁区/商业边界/CTA 风格）+ 每条 Brief 字段为 Shared/BMP 对象；KOS/KOL/KOC/UGC 分层任务；评论回复四类受 persona 约束、Risk 转人工 | R0914-C02 | 阿康/阿康1 | 闭环内 |
| G78 | 复盘维度+负样本 | 复盘按 Topic/Hook/Persona/Template/CTA 拆，保留普通/低表现/失败样本；案例逐项附原始URL、日期、市场、平台、方法、分母和证据等级。原帖及可核数据、部分访谈、行业假设、二手线索分开；生成示例不入真实案例池。KOS/员工Persona/线索路径可作可编辑假设，不能把二手收益写成因果或目标KPI；不只按点赞 | R0914-C02/C05 | 阿康/阿康1 | 闭环内 |
| G79 | 播客资产链 | Person→Interview→Story→Human Problem→Asset→Platform→Signal→Learning；Transcript 记录开头30s/问题序列/情绪与洞察峰值时间戳/产出率/失败点；制作闭环 策划→前采→录制→粗剪→补录→精剪→多平台发布→复盘 | R0914-C03；liangzi/podcast 在仓 | 阿康/阿康1 | 闭环内（并 G33 播客） |
| G80 | 文案质检 | 反模板=结构稳定表达变化；8 类表达机制、高奢克制 6 法则作为可选风格；质检清单（标题兑现、具体细节、未证实事实/夸大、语气一致、伪创新、同批重复）在保存/导出前提示 | R0914-C04 | 阿康/阿康1 | 闭环内 |
| G81 | 爆款对照与跨平台 | 爆款研究须含普通/失败样本，相关≠因果；按当前ContentContext重建素材用途/事实，不能复制案例文案、标签、时间或指标。BIL按机制覆盖选择案例，区分品牌健康、社媒热度、UGC、触达质量、文化/购买意图、品牌DNA、本地执行、门店体验、增长、创作者归因及AI发现/传统曝光，不做品牌排名。长内容→章节/短切/金句/人物卡/图文，按平台重做包装，复用故事节点而非成片 | R0914-C05 | 阿康/阿康1 | 闭环内 |
| G82 | 浏览器 Agent 循环 | 内置浏览器动作 Observe→Plan→Act→Verify：observe(URL/readyState/DOM+A11y/必要截图)、verify_action(expected vs actual，失败不报成功)、stall_detect；AI 定位+确定性执行，提取受 schema（约束解码）；离线 benchmark 含 UNACHIEVABLE | R0914-E01/E03；参照 OpenAI | 阿康/阿康1 | 闭环内（并 G32） |
| G83 | Agent 生产控制链 | Intent→既有Orchestrator→有界注册Tool/子任务（schema/actor/scope/风险/Evidence/幂等/版本/预算/单写者）→成果Owner读回→必要人审→受控Effect→Evaluation/Trace；长工作异步回到父任务，短工作不强制委派；Agent无任意COMMIT/DELETE/生产写，派生输出与原始/人工/决定分存，不新增Runtime或队列 | R0914-E01 | 阿康/阿康1 | 闭环内（并 G31） |
| G84 | Provider 失败（按现行规则覆盖） | 自有模型不可用→UNAVAILABLE 可观察状态，无自动回退；BYO-API 仅用户显式选择；确定性采集/统计/报告主链照常 | R0914-E01 vs PO | 阿康/阿康1 | 闭环内（并 G50） |
| G85 | 数据真相链 | External→Evidence→Canonical→确定性函数→Metric→Truth→ViewModel→Report；Metric/Report 单一生产入口；报告事实与 AI 摘要分区并记 snapshot/evidence 引用；人工修正可追溯可撤销 | R0914-E02 | 阿康/阿康1 | 闭环内 |
| G86 | 数据红线 | NO_DATA/UNKNOWN≠0（并 X33）；publish_datetime 与 captured_at 分离；同平台 content_hash+platform_id 去重、跨平台转载 REVIEW；详情失败保留主记录 | R0914-E02 | 阿康/阿康1 | 闭环内 |
| G87 | DB/Runtime 验收 | 运行进程实际 DB 路径一致；clean bootstrap/migration/upgrade/rollback；FK+业务约束；Worker Lease/Heartbeat/Checkpoint/Reaper/Retry/DLQ/Resume 有状态；端口可达≠健康 | R0914-E02/E03 | 阿康/阿康1 | 闭环内（并 G41/G42） |
| G88 | 采集状态机与风控可观测 | STARTING…RECOVERING 合法转换；IP_RISK/CAPTCHA/AUTH_REQUIRED/NETWORK_ERROR/BLOCKED/COOLDOWN 分开、0 条≠成功；验证码不破解→产品内登录弹窗人工恢复；低并发/退避/熔断（研发关、闭环前开）；只留任务需要字段；旧文“持久 Edge/CDP”按现行规则改为内置浏览器同会话后台采集 | R0914-E03 vs PO | 阿康/阿康1 | 闭环内 |
| G89 | API 契约与异常 | 统一 success/error/code/data/status；Auth≠Permission，高危端点（代码执行、配置、删除）强制权限（并 G35）；禁止 except→ok=true+[]/0；写操作 operation_id 幂等 | R0914-E04 | 阿康/阿康1 | 闭环内 |
| G90 | Release Gate 阻断性 | CI 关键检查无 continue-on-error；Gate 覆盖编译/测试/安全/边界/DB 迁移/运行谱系；依赖锁定可复现；测试不改写受控审计产物；安全扫描分级不以误报忽略 | R0914-E04 | 阿康/阿康1 | 闭环内（并 G41/G47） |
| G91 | 研究资产准入 | E0 Candidate→E1→E2→E3 Tested→E4 Validated→Production admitted；研究结论分 事实/推断/建议/已验证/已采用，附“不知道什么”；来源记 URL/commit/日期 | R0914-E05 | 阿康/阿康1 | 闭环内 |
| G92 | Evaluation 五维 | Data/AI/Collector/Report/Runtime 指标（完整度、人工修正率、恢复率、Evidence 覆盖、heartbeat）；unknown≠pass；Badcase/Golden/Regression 闭环，规则/模型升级同集回归 | R0914-E05 | 阿康/阿康1 | 闭环内（训练评估随 G23） |
| G93 | 历史审计引用失效 | eng 包引用的 audit/*、LUMENIS_*_AUDIT_V1.md 等已不在 main；结论按上表吸收，旧状态不外推；不恢复旧文件 | R0914-E06 | 阿康/阿康1 | — |
| G23 | 自有多模态 | gpt-oss-20b 仅文本；视觉/转录/媒体生成无自有模型 | TPCR:91,120,336 | 阿康1 | 闭环内 |
| G24 | Web Workspace | 静态资源 404、回不到 GLOBAL/ALL；v14–v17 仅本地 | R03-CHARTER:65 | 阿康 | 闭环内 |
| G25 | 依赖许可 | 多数依赖 VERIFY_BEFORE_RELEASE（发布阻断）；FFmpeg GPL；flutter_quill 未入 pubspec | TPCR:44-74,225,258,385 | 阿康 | 闭环内 |
| G26 | 状态词表 | 三套并存：PA:465 / GOV-MACHINE.json:177-185 / spec frontmatter | 同左 | 阿康 | 闭环内 |
| G27 | 本地草稿冒充写入 | 播客 draft/render、内容发布、活动收尾、达人 hold、SH-04 导出均仅本地草稿，无执行器/effect fence/Evidence 回执 | BMP-06/07/08:45,80/09/10；SH-04 | 阿康 | 闭环内 |
| G28 | 播客独立制作 | P0-A 播放/B 真实波形/C 录音/D 混音、P1-E/F 未实现；store 不过滤、丢 source ref | BMP-08:5-9,36,193-232 | 阿康1 | 闭环内 |
| G29 | BMP 目录/BrandFocus | _build_bmp02 为策划目录无 lineage；目录 API 仅 CTH；组合/竞品无写 owner；新增主体写合同未定 | BMP-02:48,96,123；ACC-02:31,232-236 | 阿康 | 闭环内 |
| G30 | 实时监测 | SourceTarget 被 Flutter DTO 丢弃；realtime_series/collector 健康无 endpoint；验收仅 3 个主体 | CTH-03:40,51-52,115,122 | 阿康 | 闭环内 |
| G31 | AI 意图执行 | 自有 runtime NOT_BOUND → ANALYZE status=failed；无 execution/Evidence trace GET；历史无 actor 范围 | AI-01:39,47,91 | 阿康1 | 闭环内 |
| G32 | 内置浏览器动作 | click/input/select/upload/download 未实现；loopback guard；仅 workspace:local；RecoverySheet 未接 | SYS-06:75,91,114-118,435-437 | 阿康1 | 闭环内 |
| G33 | 共享创作 | 独立新建要求 vs 仅目录实现；safe-run 禁用；单视频轨；无编码取消/续跑；Discover 仍 exploration | SH-01:5-15,109,203,587,644 | 阿康 | 闭环内 |
| G34 | 注册表失真 | feature_registry 生成于 09-06、9 列全空、31 文件已不存在；function 注册行号/路径过期；schema 快照缺 owner 表；caller 清单基线 c3036aa7 | feature_registry.md:3；function_registry_canonical_t4.csv；schema_registry_t4.csv；CALLER-INVENTORY:9 | 阿康 | 闭环内 |
| G35 | 安全 | /api/settings/developer/execute 对请求体 exec（空 builtins 可绕过）；professional_accounts.access_token 明文列；podcast_ai_runs.prompt 明文；未经批准的临时公网隧道 | settings_module.py:287-311；schema_registry_t4.csv:469,505；临时公网入口删除与调用断开回归 | 阿康 | 立即 |
| G36 | l10n | ACC-01/04、AI-02~05、ACC-02:75 本地兜底文案；CTH-01:103 仅中文；SYS-01:116、AI-01:159 韩语未验；CTH-04~07 缺 key | 同左 | 阿康 | 闭环内 |
| G37 | 规则≠代码漂移 | AUTO_COLLECTION_SCOPE 单太古汇（PR #36）；验收出口：登记主体→后台无窗调度→每平台独立失败/登录弹窗恢复→Evidence 可读、缺字段标未知 | rednote_policy.py；审计 I-P0 | 阿康 | 闭环内（并 G-太古汇） |
| G38 | Shared 独立 | saved_work.authorize 仅 cth/bmp；出口：无 CTH/BMP 前置完成提案/视频/播客 新增/修订/导出/重开/撤权 | saved_work.py | 阿康 | 闭环内（并 G33） |
| G39 | AI-01 状态错位 | 后端 not_executable → Flutter fromResponse FormatException（"响应无效"）；出口：不可执行/待审批/拒绝/失败/完成 五态分别呈现；约束解码兜底格式 | ai_intent；Ai01IntentResult | 阿康1 | 闭环内（并 G31） |
| G40 | 身份绑定 | screen_viewmodel builders（_build_sh02 query_evidence）未绑定 actor；出口：越权样本拒绝回归 | screen_viewmodel.py | 阿康1 | 闭环内 |
| G41 | CI 覆盖 | 必需 CI 缺 ai01 receipt、sh06 inbox、browser frame stream、新主体 E2E，无 flutter test；出口：Product/App Gate 含之 | .github/workflows | 阿康 | 闭环内 |
| G42 | 入库读回 | importer/种子已发布无 DB apply 读回（610/137/185）；Brio 227/244/150 未逐源抽检；出口：apply+计数读回+抽样 hash | import_subject_registry_seed.py | 阿康 | 闭环内 |
| G43 | 闭环判定 | BACKEND_GAP 54/54 PENDING；阶梯 DEFINED→…→JOB_CLOSED(真实产物读回)→RELEASED→OPERATING；CI 绿≠闭环 | BACKEND_GAP.json；machine contract | 阿康 | 闭环内 |
| G44 | 首条正向验收 | CTH、BMP、独立 Shared 各一例：输入→确定性报告/来源/局限→保存修改重开→决策/回执 | Real Delivery | 阿康+阿康1 | 闭环内 |
| G45 | 四端分验 | Web/Win/macOS/iOS 各自启动、浏览器离开返回/停机重开 | Experience | 阿康1 | 闭环内（含视觉风格） |
| G46 | 状态链陈旧 | Slack 17:22 / Issue #17 回执落后 main；出口：Issue #17 单点用最新 SHA 更新，不新建管理系统 | Issue #17 | 阿康 | 闭环内（发帖需 PO 批准） |
| G47 | 公开仓库 | repo public：明文凭据（并 G35）、依赖许可证未核（阻断发布） | security_verification_shardC.md；licenses | 阿康 | 立即/闭环内 |
| G48 | 单位经济 | 每主体采集/存储/推理成本、人工接管率等变量测量 | — | 阿康 | 闭环内 |
| G49.1 | 竞品 Simon Willison LLM | 对方优势：模型调用 CLI/Python、SQLite 日志、嵌入、工具调用、结构化输出；序境差异化：品牌实体+有出处成果+无 AI 连续工作流；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.2 | 竞品 Khoj/Pipali | 对方优势：小团队知识/桌面 AI 研究；序境差异化：小团队做复合产品；不重启通用 OS 控制；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.3 | 竞品 Dify | 对方优势：Workflow/Chatflow、工具、知识检索、检查点、自部署；序境差异化：商业任务语义、证据/权限继承、版本恢复、用户工作量更少；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.4 | 竞品 DataStory 数说故事 | 对方优势：企业数据设施、SocialGPT、EnlightAI、洞察→营销→销售；序境差异化：从可独立工作的明确小场景（商场-门店-品牌）切入；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.5 | 竞品 Brandwatch | 对方优势：消费者研究、搜索情报、社媒管理、达人、媒体情报；序境差异化：来源可信、可编辑业务成果、端到端效率，不比菜单广度；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.6 | 竞品 Meltwater MCP | 对方优势：已购情报接 AI 助手、引用、问答简报、多轮上下文；序境差异化：确定性无 AI 路径+已授权本地资料+可修订制作；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.7 | 竞品 Adobe GenStudio/Content Supply Chain | 对方优势：品牌模板、已批素材、变体、审批、渠道效果；序境差异化：轻量细分专业团队的可编辑提案/视频/播客；验收：固定任务/数据/权利/成本/质量同题实测，只证细分优势不报排名 | 审计 F | 阿康 | 闭环内 |
| G49.0 | 定位 | 合法来源+正确实体关系+可审计事实+无 AI 可完成+可编辑提案/媒体+保存恢复 = 监测→交付垂直整合 | 审计 F | 阿康 | 闭环内 |
| — | 审计口径覆盖 | 冲突以 PO 现行规则为准：默认自有模型，另留一个通用 OpenAI 兼容 BYO-API 接口供用户可选接入自购密钥（产品默认不调第三方、无自动回退）；前端功能与后端并行闭环内；后台采集+内置浏览器(像正常浏览器、可折叠、参照 OpenAI)+全平台产品内登录弹窗；手动采集可选+前端按钮；风控研发关/闭环前开；账号体系、开发者模式、商业六项、视觉风格/logo/角色图均闭环内；上线后仅真实用户验证与付费/授权来源；CI 绿即合并 | CURRENT:11,14,18,49-55（akang/loop-plan-audit） | — | — |

| G94 | 采集优先级（免费数据先行） | 先采全部已登记平台的免费广告/流量与创作者中心数据：小红书、抖音、视频号、快手、B站、微博、微信公众号、Instagram、Facebook、TikTok、YouTube、X 等（registry 现有 adapter）；验收：每平台 PlatformManifest 标注可得字段/取得方式/缺失原因，内置浏览器同会话后台采集，入 Evidence→Canonical，0 条≠成功，失效弹登录 | PO 10-14 | 阿康/阿康1 | 闭环内 |
| G95 | 聚光（小红书付费投放数据） | 需小红书专业号，PO 暂无 → 延后；juguang_api.py 保持未配置=UNAVAILABLE，不伪造；KFS 中的 F（24h 互动>20 再投）仅作方法论 | PO 10-14；BMP-06 | 阿康 | 有专业号后 |
| G96 | 删除临时隧道 | start_tunnel.py 已删（b13），登记/基线/清单引用同删；CHANGELOG 历史不改 | PO 10-14 | 阿康 | 闭环内（已备） |
| G97 | 内容生产链（KOS 规范） | Brief 未完成不生成；Campaign→Series→Post(Title/Hook/Body/CTA/Hashtags/Visual Brief)；版本存 prompt/model/template/输入/校验/人工修改/终稿；模板选择= weighted performance+context fit−risk，权重配置化有版本；一个超级 Prompt 包办禁止 | 02_BMP/KOS_CONTENT_TEMPLATE_EXECUTION_SPEC；FINAL_DATA_PIPELINE | 阿康/阿康1 | 闭环内（并 G76/G77/G80） |
| G98 | 模板注册表 | template_id/版本/状态/input_schema/output_schema/risk_rules；小红书笔记、海报、视频分镜（每镜 visual/台词/时长/目的/素材）、评论回复（自动/建议/必人审三策略） | FINAL_DATA_PIPELINE | 阿康/阿康1 | 闭环内（输出受约束解码 §10） |
| G99 | 创意方法论 L0–L3 | 芥子(原子技巧)→单线公式→多线战役六维(人群/内容/渠道/节奏/场域/预算)→品牌世界观；每层保存父引用、版本及上下文指纹，用户修改只重算实际依赖并显式采用新版本；正向下钻出方案、反向上抽沉淀知识；每判断挂真实信号 | BMP 知识 08 | 阿康/阿康1 | 闭环内 |
| G100 | 调性坐标 | mass/premium/luxury 为强制变量，同一 Big Idea 三调性出不同执行；高奢克制 6 法则仅 luxury 用 | BMP 05/08/15 | 阿康/阿康1 | 闭环内（并 G80） |
| G101 | 反模板创意引擎 | 机制×张力句式×角度×语义角色×预算≥3维组合；批次去重；seed 可复现（禁止就地 shuffle 共享 list）；占位符零残留；情感共鸣手法按主题语义角色白名单（服务类只用写实） | BMP 11/13/14/16 | 阿康/阿康1 | 闭环内 |
| G102 | 主题提取去污染 | 只从真实原生标题/正文提取，标题权重单列；查询主体词及完整品牌名 n-gram 入 stop_terms；系统摘要/合成标记/互动指标字段及其标签词不混入原文词频，保留原文与派生主题的来源关系 | BMP 10/13 | 阿康 | 闭环内 |
| G103 | 三方视角适配 | 同一事实和方案按甲方/乙方/丙方的收益、语言、决策权限重排章节/KPI/下一步，事实不变；各视角明确谁使用、做何决定、下一动作及其依据，不用角色名称替代实际适配 | BMP 12 | 阿康/阿康1 | 闭环内（提案 C4） |
| G104 | 提案结构与导出 | 10 段比稿骨架+4A 叙事弧+One Slide One Job；STP、4P/4C/4R、CDV=TCV−TCC、品牌资产及营销5.0按问题映射已有输入/分析/策略/长期指标，不只贴术语或虚构百分比；预算档 low/mid/high；方案拆解支持 txt/md/json/csv/docx/pptx 上传并导出 Word | BMP 03/05/11/16/17 | 阿康/阿康1 | 闭环内（并 G33） |
| G105 | 营销日历 | 节气/节日/大促/7 垂直行业/海外 26 节点/区域节点；行业×节气×海外交叉；创意自动绑定当月节点；报告带 marketing_nodes；CSV 排期导出 | BMP 17–24 | 阿康/阿康1 | 闭环内 |
| G106 | 平台算法信号 | 停留/完播/重看/私发转发/评论/收藏 > 点赞；创作者内容按 ROI 不按点赞；同创意按平台原生改写 | BMP 07/08 | 阿康/阿康1 | 闭环内（并 G78/G81） |
| G107 | 播客合作评估 | 影响/内容/人群/矩阵/变现五力；6 种合作模式；选题挂营销日历 | BMP 25 | 阿康/阿康1 | 闭环内（并 G79） |

## 9. 与 PO 现行规则冲突的旧文（仍在 main）
| # | 文件:行 | 旧文 | 冲突的 PO 规则 |
|---|---|---|---|
| X1 | ai_provider_matrix_shardB.csv:2-5 | zhipu ACTIVE cloud_primary；ollama ACTIVE local_primary；ark/doubao cloud_fallback | 默认自有模型；删专用 provider，仅留通用 BYO-API 适配器（用户可选），无回退 |
| X2 | AI_PROVIDER_FAILOVER_POLICY_V1.0.md:34,48-110,237-240 | 智谱 L1→豆包 L2→千问→Ollama 回退链 | 同上；文件仅头部 SUPERSEDED，PO 要求整删 |
| X3 | LUMENIS-PRODUCT-CONVERGENCE-MASTER-V1-20260906.md:58 | “当前目标运行面：Zhipu + Local AI 并行” | 同上（头部 SUPERSEDED 标注违反“直接删除”） |
| X4 | LUMENIS-INTELLIGENCE-OS-DUAL-CORE-ARCHITECTURE-v1.0.md:193-202 | Ollama/Zhipu/OpenAI-compatible Provider；“智谱不删除” | 同上；另含 Linux、通用 OS 控制 |
| X5 | api_matrix_shardC.csv:7,24 | /api/ai-governance/status “local fallback”；/api/ai/chat provider | 无回退 |
| X6 | LUMENIS-EXPERIENCE-CONSTITUTION.md:1192 | AI-05 “Provider topology… fallback path” | 无第三方/回退 |
| X7 | contracts/.../AI-05.md:29,39,60,66,79,92 | AI-05→AI-01 “fallback diagnostic” | 仅为诊断读回退，非模型回退；措辞易误导 |
| X8 | SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md:214 | “MANUAL remains the default” | 研发阶段全部已登记主体 AUTO（GLB:33 已覆盖，但此处未改） |
| X9 | LUMENIS-GLOBAL-…-CURRENT.md:35 | “default collection mode is MANUAL” | 同上（与本文件 33 行并存） |
| X10 | LUMENIS-EXPERIENCE-CONSTITUTION.md:1067 | 媒体连接器“No new platform account/login flow is inferred；用 import/replacement 恢复” | 全平台产品内登录弹窗（§11.1 RecoverySheet） |
| X11 | LUMENIS-EXPERIENCE-CONSTITUTION.md:1198 | SYS-06 只写“受控取证”，未写后台无窗口采集＋恢复 | 采集后台内置浏览器 |
| X12 | LUMENIS-AI-PRODUCT-CLOSURE-CHECKLIST-V1.md:§3 | Tool Calling 含“本地程序、外部API” | 通用 OS 控制已撤回（EXP:15）；无第三方 AI |
| X13 | LUMENIS-ENGINEERING-GOVERNANCE-V1.0.md:53 | “AI Gateway 必须保持 Provider-Agnostic” | 限定为：自有模型默认＋单一通用 BYO-API 可选 |
| X14 | RD:337,340,1174；SYS-05.md:152；CTH-05/07.md W-010 | 太古汇作为固定参考覆盖维度/测试主体 | 范围＝全部已登记主体（作为“参考”本身不冲突，测试用例硬编码属差距） |
| X15 | EXP:754、1585 | 文中把参考产品写作“Grok Bot” | 品牌名只用官网名，需按官网核实 |
| X16 | 多份头部 SUPERSEDED/HISTORICAL 标注（AIPOL:4、PCM:3、DUAL:3） | 标注而非删除 | PO：旧规则直接删除，不加作废标注（但已推送内容不改→需 PO 定夺新 PR） |
| X17 | GOV-MACHINE.json:22-28 | peers 仅 Codex/Akang，agent_to_agent_dispatch=false | 阿康→阿康1 派工现行 |
| X18 | GOV-MACHINE.json:311；LAUNCH:150-151 | 合并需当前 head 评审；LAUNCH 禁新分支/常规 PR | CI 全绿即合并；现行分支+PR |
| X19 | LAUNCH:228；TPCR:209 | launcher 保活 9222/9223、Edge 常驻 CDP | 禁 9222；内置浏览器后台采集 |
| X20 | DUAL:109-110,168,193-202；PA:406；ENG-EVOL:199 | 智谱/OpenAI-compatible/云模型、AI Fallback | 只自有模型、无 fallback |
| X21 | CODEX-ZERO-AUTH:136；TPCR:85 | Runway/Higgsfield/OpenArt 媒体 provider；Browser Use 带 posthog+Ollama SDK | 无第三方 AI |
| X22 | BRAND-ECO:20,39 | 引用已不存在的 EXPERIENCE-DESIGN-AUTHORITY-V2 | EXP 为唯一设计权威 |
| X23 | BRAND-ECO:413 | 新生产资产须全部自研 | EXP:1035 允许登记开源组件 |
| X24 | GOV-MACHINE.json:349 | subagents=gpt-6-luna | 仅 Codex 侧；Cursor 规则另定 |
| X25 | SH-02:31,126；CTH-10:9 | 打开原文可显式选外部浏览器 | 内置浏览器（采集已合规；打开原文需 PO 定） |
| X26 | TEMPLATE:17 vs AI-02/03/04、SYS-03/04/08 | spec 仍以 Sol 设计评审为门 | 直接实现，无 DESIGN_READY 前置 |
| X27 | CTH-08:43；CTH-09:43 | 硬编码可信 ID 白名单（CASE-221、EV-7710/7699/7712） | 全部已登记主体、真实 lineage |
| X28 | CTH-02:30-32,58 | 要求 /v4/auth/login Bearer、"请重新登录" | 账号体系闭环内，仍不设账号墙（ACC-02:155、AI-01:57） |
| X29 | BMP-01:18-22 | 先选 BrandFocus 才可用 | GLOBAL_ALL 默认 |
| X30 | BMP-04:7；BMP-08:187；CTH-10:9；SYS-05:28；SYS-06:100-103,217-312；spec README:112 | "superseded/historical provenance"保留旧规则段 | 旧规则直接删除 |
| X31 | CTH-06:135 vs :25,33 | 派生类别"可编辑" vs 屏幕只读 | 自相矛盾，需择一 |
| X32 | AI-05:30 | provider kind=local/optional/generic | 仅自有模型、无 fallback |
| X33 | CTH-01:48；CTH-05:22；trend_api.py:250-255；normalize.py:105,113 | 失败/缺失补 0 | missing≠0 |
| X34 | CTH-01:49 | 无范围 Evidence 查询 + 硬编码 lineage | scope 化 |
| X35 | SYS-02:166；CTH-03:246 | 旧固定起始日期字面量 | 主题驱动、无统一起始日 |
| X36 | CTH-10:87；SH-02:156 | 自有推理未绑定；要求不存在的六平台原生 reader | 默认自有模型 / owner 落地 |
| X37 | AI-01:93；canonical_data.py:870 | 服务端默认 actor=experience_user、domain/product=CTH | GLOBAL_ALL 默认、真实 actor |
| X38 | spec README:32,92,102；SYS-05 全文 | 44 屏全量视觉升级、手绘图标、壁纸/材质迭代现在做 | 前端视觉/logo/角色图闭环内，按 UI-STEP-PLAN 分步做 |
| X39 | SYS-06:9,88,195 | AgentZero/通用 OS 代码"保留为历史" | 已撤回范围应删除 |
| X40 | CTH-03:40,115；swire_group.py:32；ai_analyzer.py:144；schema swire_* 三表 | 太古系/单主体硬编码与验收 | 全部已登记主体 |
| X41 | ark_llm.py:23；ai_api.py api_ark_*；local_ai_client.py:21,29；case_ai_evaluate.py:20；config.py:258 | 豆包/智谱/Ollama 代码与配置键保留 | 删豆包/智谱/Ollama 专用代码，替换为单一通用 BYO-API 适配器；旧通道直接删除 |
| X42 | import_cookies/import_xhs_cookies/xhs_cookie_bridge；dual_pool CookiePool/ProxyPool；dual_account_rotation；xhs_cdp_collector 仿人轨迹；resident_health._cdp_get_cookies | cookie 导入/账号轮换/反检测 | 产品内登录弹窗、内置浏览器后台合规采集、不读 cookie |
| X43 | schema v4_users/sessions/workspace_keys/security_questions | 账号表已建且有数据 | 账号体系闭环内；明文字段清除 |
| X44 | populate_empty_tables.py:63-66 | 写死 relevance_score=0.8 填充 | 不伪造派生值 |
| X45 | feature_registry F-0327~0334 | xhs/RedNote 混用 | 官方品牌名 |
| X46 | brand_logo_auto.py | 自动抓 favicon 作 logo | logo 闭环内由设计产出，不自动抓 favicon；不发远程追踪请求（SH-01:678） |

## 10. 约束解码（结构化输出强制）的落点
| 位置 | 依据 | 落点 |
|---|---|---|
| SYSTEM AI Gateway 推理层（config/ai-owned-foundation.json，gpt-oss-20b APPROVED_FOUNDATION_NOT_TRAINED） | A:907、PA:130 “Structured Output” 为必验项 | Gateway 调用自有模型时按 JSON Schema/语法约束生成（xgrammar/outlines/vLLM guided decoding） |
| Gateway→Core 合同：contracts/experience/viewmodels/VIEWMODEL_REGISTRY.json、actions/ACTION_REGISTRY.json、AI-01..05 viewmodel/actions | EXP:1297-1301,1349 “编译/解码只校验有类型的组件与数据提案” | 用这些注册表生成约束 schema；未完成片段不可点击 |
| 智能UI 分段协议 | EXP:1350 块身份/顺序/修订号 | 每段输出受 schema 约束，修 AI-01“响应无效” |
| 验收 | EXP:1335、RD:223 “schema-valid 响应/AI 产出答案不算完成” | 约束解码只保证格式，不替代真实业务结果验收 |
阶段：闭环内（C2/阿康1）；真正生效需自有模型训练（PO 授权＋GPU）。

## 11. 仓库研究资料升级（2026-10-14，第二轮含 X 帖与 SwiftChat/Intelligent UI，main 96697530；只升级不降级，旧文与现行决策冲突时按现行决策改写）
| # | 能力 | 闭环内验收标准 | 来源 | 归属 |
|---|---|---|---|---|
| G185 | **Skills 商店（完整）** | Discover→Inspect→信任/许可→权限审批→隔离安装/自测→启用→真实执行→Evidence→历史→版本更新/回滚→停用→卸载 全链；支持 LUMENIS `skill.json` 与 Agent Skills `SKILL.md`、本地目录/ZIP/GitHub 精确 revision 来源；未验证项只能 disabled+not_installed；至少 1 个 Skill 真实完成 CTH/BMP 业务任务；前端有安装/启用/停用/更新/卸载按钮（用户可选） | SOI §2-12、RD:717-760、AI-04、docs/architecture/LUMENIS-GITHUB-SKILL-MCP-CONTRACT-V1.md §3、FULL-UPGRADE U19、IC-004/IC-009 | 阿康1 后端 / 阿康 前端并行 |
| G186 | **GitHub 连接器** | 按原设计：用户同意→GitHub App user-to-server 授权/选择安装→外部凭证提供器（不存/不打印 Token）→仓库白名单→只读 GitHub API→GitHub Adapter→Evidence/Canonical/AI/CTH/BMP/Shared；6 态 NOT_CONFIGURED/READY_FOR_AUTHORIZATION/CONNECTED(/user 健康检查)/SESSION_EXPIRED/BLOCKED/PROVIDER_UNAVAILABLE 前端可见；默认 write_enabled=false；授权回调+CSRF state 核验+加密凭证库实测；不依赖产品账号体系（ARCH:557 保留其自身授权） | 同上 §1-2、ARCH:557、AGENTS:1129、github_connector.py、platform_adapters/github.py | 阿康1 / 阿康 |
| G187 | **MCP 接入** | 发现→工具 schema 审查→域/端点白名单→权限审查→人工批准→隔离自测→版本化注册；MCP通过既有类型化业务API，不直达 Cookie/CDP/原始库/未授权外部写；协议版本、凭证audience、范围、Origin/SSRF及取消恢复按§17逐项验收，不因使用SDK或原生JSON-RPC而免除 | 同上 §4 | 阿康1 |
| G188 | 内置浏览器完整能力 | 标签列表/新建/关闭/切换、地址栏、前进后退、书签、历史(上限1000)、Reader 元数据/正文、轻量 A11y DOM、多引擎搜索、strict/allowlist/open 策略门+SSRF；生产 UI（标签栏+地址栏+Reader/DOM 面板、可折叠）实测 | IL/11_前沿研究/AgentOrg/05-IC-052、IC-051、IC-053 | 阿康/阿康1 |
| G176 | 国家/市场/主体关系 | 总部/发源地/法人/经营/营销/场所分开；同 Canonical 多市场；反例验收：Nike 美国品牌∕中国经营并存、罗湖万象城≠万象天地 | IL/07/COUNTRY-MARKET-RELATIONSHIP-NAVIGATION、FULL-UPGRADE U01/U05 | 阿康1 |
| G177 | 场内经营关系 | 主体→项目/场所→门店/业态→品牌/活动，租户关系带来源与有效期；场内门店事件不污染品牌全国 | FULL-UPGRADE U05、CTH-DATA-INTELLIGENCE-ADOPTION | 阿康1 |
| G178 | 自动维护与 freshness | 只处理到期项；幂等/退避/断点/重启恢复；真实定时周期不依赖开发工具，记录失败与恢复 | U04、COLLECTOR-CONTINUITY-RESEARCH | 阿康1 |
| G179 | 正文质量与来源分工 | 官方/媒体证身份事实、社媒证传播/消费者表达；正文抽取小样评测（Trafilatura 对照现有）；会话/无会话逐平台逐字段对比 | U02/U03、COLLECTOR-CONTINUITY | 阿康1 |
| G180 | 平台扩展（同权按用途） | B站公开原生、微博官方 weibo-cli（免费，可作 Skill/MCP 工具）、抖音/视频号/Instagram/TikTok/YouTube 等走统一 PlatformManifest/Session/恢复；不使用付费授权源 | docs/research/2026-platform-crawling-rules.md、IL/07/BILIBILI-PUBLIC-NATIVE、ARCH:536-538 | 阿康1 |
| G181 | 韩语能力 | 语言字段 zh/ko/en；韩文分词(Kiwi/Okt)、空格校正、情感/主题/NER、韩文风险规则；Naver Blog/Cafe、Daum 适配；韩文 UI 预留 30-50% 长度与本地化格式；模型只用自有/BYO（旧文 HyperClova 云端按现行规则不接） | docs/research/korean-nlp-resources.md、research/intelligence/03_*/Korean_Content_Intelligence_Collection | 阿康1/阿康 |
| G182 | 韩剧对白/字幕本地化创作 | 场景先行/潜台词/人物声音/克制/留白；自然度、具体性、潜台词、角色归属、节奏、情绪转折、记忆点、画面适配、余味、原创性十维可编辑审校。敬语及直译/意译/增省译经过语义、人物声音、自然表达、情绪等值、文化、节奏、校对七阶段与原创检查；35/42分是原研究编辑启发，非验证阈值或全创作硬门。作为Shared可选风格，不复刻受限整段字幕；缺失音频参考保留待核，不以文字已读顶替 | docs/content-learning/KDRAMA_*、IL/02/品牌营销知识-13 | 阿康1 |
| G183 | 视频工程交换 | Timeline 交换损失预检（volume/fade/ducking/muted/多音轨/overlay/dissolve/间隙/多轨）→OTIO/FCPXML/EDL 导出（有理时基，30000/1001 等往返测试）；缺时基/重链报 UNKNOWN 不判可交付；字幕/音轨/叠层；剪辑全链见 §14 E1–E11 | IL/01/VIDEO-WORKFLOW-INTERCHANGE-RESEARCH、U14 | 阿康1/阿康 |
| G184 | 播客制作全链 | 选题→嘉宾→提纲→脚本→录音/导入→转写/说话人/章节→文本剪辑→可选配音→混音母带（-16 LUFS±1、真峰≤-1 dBTP）→发布包（音频+show notes+章节+字幕稿+RSS）→切片→复盘；工程细则见 §14 P1–P12 | U15、IC-030、docs/research/PODCAST_MODULE_RESEARCH_V1.md、podcast/research | 阿康1/阿康 |
| G189 | 研究库别名/版本/范围 | 文档/表格/网页/媒体导入；来源定位、引文、别名、版本；检索结果保留范围 | U16 | 阿康1 |
| G108 | AI 弃答与确定性优先 | 确定性计算先行，生成/分类分路，结构化校验；Hybrid+Reranker后核对来源/时间/范围，低支撑有界改写检索，仍不足时交付有依据部分并说明缺口。保留无AI普通检索与业务；§17细化上下文预算和路由验收 | U18 | 阿康1 |
| G109 | Agent 记忆与可靠性 | 复用Experience/Skill/Project记忆与现有Task checkpoint：稳定偏好、任务事实、检索证据和授权状态分开；附来源/时间/范围/版本/更正与失效，用户可查改/忘记，持久化与实际检索分别验收。压缩后重读最新指令/任务/版本/未完项，记忆不扩权限、不恢复旧命令；保持多用户隔离、Critic及失败案例回归。子任务有界上下文与回调，崩溃先核已提交效果再续跑；工作/情节/语义记忆、检索驱逐、纠正/删除传播及压缩保真按§17验证，不删除审计事实；现有接口审查采用mattpocock/skills的实际不变式、调用顺序、错误/取消、配置及性能边界方法；优先修真实调用缝隙，不因技能建议另开设计/代理流程。 | IL/11/AgentOrg/04-IMPROVEMENT-QUEUE IC-001..012、IC-037/043 | 阿康1 |
| G110 | 受控学习晋升 | shadow→promotion，保留集+真实任务均优于旧版才晋升，可回滚 | U20、IL/05/LEARNING-PROMOTION-ENGINE | 阿康1 |
| G111 | 通知/设置/诊断 | 进度来自实际任务状态，可查看和停止；通知复用现有FocusProtector/NotificationRouter与SavedWork通知feed，由真实有用结果、需决定或重要异常触发。普通片段/内部final文本不自动全部广播，通知有范围/收件人/任务版本/去重键/发送回执，失败可恢复；必要审批不因静默被抑制。偏好不改变事实或权限，三语与无障碍完整 | U24 | 阿康/阿康1 |
| G112 | 发布与备份 | 依赖锁定/许可、备份恢复、分平台打包与同 SHA 验证 | U25 | 阿康1 |
| G113 | BMP 创作者合作链 | Creator shortlist→合作 Brief→内容/反馈；适配性/受众证据/合作历史/成本来源分开，不以粉丝数代替 | U11、BMP-DATA-INTELLIGENCE-ADOPTION | 阿康1 |
| G114 | 品牌营销知识库 | 营销日历、全球大促节点、海外算法、奢品安静叙事、品类情绪叙事、比稿方法作为版本化学习资产供 Shared/BMP 调用 | IL/02/品牌营销知识 01-25、IL/09/研究收件箱 | 阿康1 |
| G115 | **Agent 无 Shell 工具集 + 内置浏览器工具** | 注册 6 类无 Shell 工具（读/搜/取网页/结构化抽取/文件产物/受控 HTTP），每个有 schema、读写类别、域白名单、风险级、Evidence、幂等；Agent 在内置浏览器同一登录态内操作页面并经浏览器调用平台 API，权限按任务授予、任务结束 100% 撤销；无代码执行接口；高风险动作人工确认 | X @llqoli 2109988479690244360（SwiftChat：6 no-shell 工具+浏览器集成，模型自发经浏览器访问 API）、aws-samples/swift-chat websearch/appgen、IL/09/AI操作系统研究/09/13、learning-feed/github-benchmarks-02（typed capability） | 阿康1/阿康 |
| G116 | **聊天智能 UI（交互卡片）**（另见 evidence/round-15/INTELLIGENT-UI-ADOPTION-20261008） | 首页聊天按任务渲染已注册文字/决策/表格/表单/图表/证据/比较组件，流式交付已成立的有用内容；长任务期间输入仍可用，多任务结果明确归属，旧回调不覆盖新修订。schema校验，不执行生成HTML/JS，局部操作不强制再调模型，数值由后端提供；保留简洁模式、检查依据、停止/恢复/保存/修订/重开，卡片动作经Permission+Evidence | X @llqoli 2109977435597103363、OpenAI《GPT-6 and Intelligent UI》与 Help 20001598、MCP Apps(SEP-1865)、EXP:1297-1350、evidence/round-15/INTELLIGENT-UI-ADOPTION-20261008 | 阿康（前端）/阿康1 |
| G117 | 舆情事件聚类 | 语义嵌入+增量/密度聚类（HDBSCAN 类）替代纯规则；簇内代表句+摘要；事件可回溯原帖 | docs/reference/CTR-EVENT-CLUSTER-P1-01.md | 阿康1 |
| G118 | 观点/立场绑定 | Stance 绑定 Target/Claim，局部活动态度不外推品牌整体；“用户说了什么/系统推测/证据”三分 | IL/09/research/…OPINION_INTELLIGENCE_UPGRADE_BASELINE_V1、LEARNING-UNITS-REGISTRY | 阿康1 |
| G119 | KOS 漏斗与合规留资 | 三阶漏斗+CPL/成本指标进 KOS 报告；免税等场景标签与分层建议；矩阵号相似度>50% 判搬运预警；AI 参与内容按平台规则自动带披露（“AI辅助生成”说明/#AI创作 话题，用户可见可改不可删）；强监管类目绝对化用语替换提示；矩阵号错峰与行为差异提示；评论回复/私信只生成草稿（不自动发）；私信通为合规留资路径（企业号授权时启用，用户可选） | CTR-KOS-METRICS、CTR-XHS-LEADS、CONTRACT_IC047、KOS-RULES-CONTENT-ENGAGEMENT、KOS-ZHIPU-REPLY（模型改走自有/BYO） | 阿康1 |
| G120 | 营销日历与热点建议 | 国内节气/节日×海外节点×行业×区域矩阵；suggest_hotspot(日期,品类)→节点+情绪主题+调性；排期导出；方案自动带“节点适配” | IL/02/品牌营销知识-17..22 | 阿康1/阿康 |
| G121 | 创意方法引擎 | 约束即创意、SIT 六模板、甲乙丙三方分级适配、手法×主题词适配（功能性主题→写实手法）、反模板 slogan（4–8 词优先、新颖×熟悉的名句重构并做与原句重叠度校验）、实时文化连接/UGC→产品飞轮/世界观营销等 4A 机制、比稿“为什么是我”；L0→L1 公式需 N>10 且显著才晋升；生成文案过合规打标 | IL/02/品牌营销知识-03/08/09/11-14、RESEARCH_2026-09-C-CONSTRAINT、CREATIVE_METHODS_2026 | 阿康1 |
| G122 | 品牌命名与跨市场音义 | 命名流水线；中英韩等跨市场音义/谐音排查（Nova/Bing 反例）作为验收用例 | IL/09/03-RESEARCH/LANGUAGE-BRAND-LIFE/04-05、IC-036 | 阿康1 |
| G123 | 采集限流与健康分级 | jitter+Retry-After；429 作软信号传入限流器；L1 端口/L2 CDP/L3 登录态三层探测（HEALTHY/NEEDS_LOGIN/CDP_DEGRADED/DOWN）+自动恢复；任务级可观测 | GITHUB-FRONTIER-20260903、github-benchmarks-04、P0B-CAPABILITY-CROSSCHECK、ZELL-P0CDEF | 阿康1 |
| G124 | OCR 与多模态取证 | 网页截图/复杂图文 OCR 结构化解析进入 Evidence（自有模型） | XHS-TOPIC-MONITOR-GLOBAL-ADAPTATION、OPEN-SOURCE-MODEL-RESEARCH-2026-09 | 阿康1 |
| G125 | 能力增益评估 | delta.improvement 非空才晋级；Learning Lift；Safety<30 一票阻断；规则命中率/投毒检测/回滚≤5s 指标 | IL/07/工程案例/capability-delta-evaluator、IL/09/AI操作系统研究/10/13 | 阿康1 |
| G126 | Evidence 21 字段 | expected 与 observed 分离，observed 必须本次实测；历史结果不得充当当前状态 | IL/09/engineering研究/V041-EVIDENCE-SCHEMA | 阿康1 |
| G127 | 主动情报 | 系统按历史故障/业务信号主动提示（如采集异常与会话周期相关），只建议不执行 | IL/09/AI操作系统研究/08-proactive-intelligence | 阿康1 |
| G128 | 播客 Idea Vault | 日/周/月三层选题库→研究→脚本→真实声音与剪辑→反馈→知识回流；Whisper 类本地转写+SRT | IL/09/docs/MASTER/FINAL_EXECUTION_COMMAND、docs/research/2026-podcast-ai-landscape | 阿康1/阿康 |
| G129 | 生产服务与迁移 | Windows 用 waitress 作生产入口；DB 变更 Alembic 可逆+有 Gate；测试环境变量隔离 | docs/learning/CASE-STUDIES、SQLITE-ALEMBIC-MIGRATION、TECHNOLOGY-COMPARISON | 阿康1 |
| G130 | **Skills 商店上架内容** | 商店首批：现有 9 项（shared.union_search/video_shotcraft/cangjie/huashu/social_card/last30days + 3 项 SYSTEM 只读审计）逐项评估从 PARTIAL→VERIFIED；旧规划 S01–S72 按业务/研究/AI/数据/运营组逐项登记为候选，含 S36 竞品研究、S61–S66 主体/品牌/舆情/事件/KOS/Campaign 情报；S31 “AI Fallback”按现行规则改为“失败可观察、无自动回退”；AE Method 与 8 个插件包（ai-agents/business/data/engineering-qa/governance/operations/research/source-engineering）按 Agent Skills 标准可安装；S23–S32/S53–S60/S67–S72 只作后台或受限管理插件，安装不直接授予权限；每个 Skill 结论列输入/观察时间/验证状态/剩余未知，实时结论无端点时报 UNVERIFIED；本轮anatomy、diagram-design及mattpocock/skills先作已有能力的许可核验参考；上架仍走G185，不因MIT或星数自动安装。 | 本地 序/序境skill/SKILL-LIST.md、ae-method/README.md、plugins/*、lumenis-team | 阿康1/阿康 |
| G131 | 研究→能力落地表 | 广告法/行业规范→广告识别与主张风险提示；传播/新闻理论→事实核验/替代解释/代表性；SNU 课程→研究设计与评价尺度；推理工程→加载/延迟/缓存/成本计量；Cue/逐帧视听→镜头节奏与可逆交互；每项进入现有能力并在真实任务验证 | 本地 序/审阅交付/规则引用审计与产品蓝图-20261004/01-产品闭环蓝图-待审核.txt §五 | 阿康1/阿康 |
| G132 | J1–J8 闭环出口 | 新增主体可用、关系有 Evidence、六主平台真实单帖接收、刷新独立运行；时间轴滚动/缩放/seek 同步与缺媒体处理；播客试听与音量质量；权重训练/重载/晋升/回滚证据；离开开发工具持续运行 | 同上 §四 | 阿康1/阿康 |
| G133 | 统一平台恢复闭环 | PlatformManifest/PlatformSession/RecoverySheet/SourceTarget 从规范 Future 落到源码与实测 | 本地 序境-audit-reports/20261007-current-status（P1） | 阿康1/阿康 |
| G134 | 语义一致性校验 | Permission/Evidence/终态/lease/同 SHA 发布/等待恢复七项不变量用 property/state-machine 测试；代表性来自抽样框；记忆保持与回溯检索按固定预算对照 | 本地 序境-audit-reports/20261007-semantic-math/REPORT.md §D | 阿康1 |
| G135 | 韩语官方词典与词表 | 韩语分析可选接入国立国语院基础词典官方免费 API（密钥仅服务端）与 4,704 CC BY 4.0 词头作为韩文词表，来源分开标注 | 本地 korean_skill_publish/Korea-Media-Korean-Skill/README.md | 阿康1 |
| G136 | 主张核验门 | 方案/文案中涉及安全、隐私、合规、独家、现货、认证等主张逐条记录“主张/证据来源/适用范围/确认人/审批状态”；未证实主张标“待核实”不作已验证事实；审批记录真实批准者、实际动作、外部结果（不只客户端身份串） | 本地 ae-method/eval/runs/*、probe-local-claim；evidence/round-15/RECTIFICATION-20261010-HISTORY-ADDENDUM | 阿康1 |
| G137 | 状态词汇分离 | UNKNOWN/0/未配置/待验证/就绪/运行/局部完成/已验证/任务闭合/发布/持续运行 分开；同词跨 Owner 带资源/阶段/版本/时间限定 | 本地 20261007-semantic-math/REPORT.md；evidence/round-15/SEMANTIC-CALIBRATION-20261007 | 阿康1/阿康 |
| G138 | 变更影响定位 | 来源撤回/预算/需求变化→定位受影响的判断、报告、文稿、镜头、节目段落→用户明确采用新版→只改相关部分，保留旧版与原因 | 本地 01-产品闭环蓝图 示例三；evidence/round-15/M-PRESTART-BLUEPRINT…、INTELLIGENT-UI-ADOPTION-20261008 | 阿康1/阿康 |
| G139 | 话题词条库 | 按平台×品牌/商业主体建立话题词条库，按采集任务语义编写话题；版本化扩充，不伪造热榜 | evidence/round-15/full-product-audit-20261003/USER-ADDITIONS-20261004、CONTINUITY-RULE-RECEIPT-20261004 | 阿康1 |
| G140 | 零授权自立采集矩阵 | 6 平台×12 能力逐项给公开页/RSS/开放文件/自主解析路径并按自立度排序；验收需真实字段值落库，HTTP 200 不算通过 | evidence/round-06/ZERO-AUTH-MATRIX-20261008、GLOBAL-DATA-SOURCE-RESEARCH-20261013、PUBLIC-ACQUISITION-RESEARCH-20261008 | 阿康1 |
| G141 | 官网内容体系（功能部分） | 能力、解决方案、成果案例、帮助、信任、更新、下载各栏目；只讲已验证能力或标明示例；三语 | evidence/round-15/full-product-audit-20261003/WEBSITE-ADAPTATION | 阿康 |
| G142 | 少滚动交互 | 除官网外非必要不上下滑动（工作区一屏内完成主要操作） | USER-ADDITIONS-20261004 | 阿康 |

## 12. 找回的遗失能力（研究资料中设计过、规划里缺失或被弱化）
| 能力 | 原状态 | 找回为 | 来源 |
|---|---|---|---|
| Skills 商店 | 仅第62行与 G21 提及；AI-04 被写成只读目录 | G185 全生命周期 | SOI §2-12、RD:751 |
| GitHub 连接器 | 规划完全缺失 | G186 | LUMENIS-GITHUB-SKILL-MCP-CONTRACT-V1 |
| MCP 接入 | 缺失 | G187 | 同上 §4 |
| 内置浏览器书签/历史/Reader/多引擎搜索 | 仅浏览器动作循环 | G188 | IC-052 |
| 国家/市场关系 | 缺失 | G176 | COUNTRY-MARKET |
| 韩语舆情与本地化创作 | 只有界面三语 | G181/G182 | korean-nlp、KDRAMA |
| 视频 OTIO/EDL 交换 | 缺失 | G183 | VIDEO-WORKFLOW |
| 播客转写/响度/章节 | 弱化 | G184 | U15 |
| 弃答、记忆分层、Checkpoint、Critic | 缺失 | G108/G109 | U18、IC 队列 |
| 微博官方 CLI / B站公开源 | 缺失 | G180 | crawling-rules、BILIBILI |
| Agent 无 Shell 工具+浏览器 API | 只有浏览器动作循环 G82 | G115 | X 帖 a、SwiftChat |
| 聊天智能 UI 卡片 | 仅 §10 约束解码与 AI-01 分段 | G116 | X 帖 b、OpenAI Intelligent UI |
| 语义事件聚类 | 缺失 | G117 | CTR-EVENT-CLUSTER |
| KOS 漏斗/留资/搬运检测/回复草稿 | 缺失 | G119 | CTR-KOS、CTR-XHS-LEADS、KOS 系列 |
| 营销日历/热点建议 | 规划仅“日历”字样 | G120 | 品牌营销知识-17..22 |
| 创意方法引擎 | 只有反模板质检 G80 | G121 | 品牌营销知识 |
| 品牌命名音义排查 | 缺失 | G122 | LANGUAGE-BRAND-LIFE |
| 三层健康探测/429 软信号 | 缺失 | G123 | P0B、benchmarks-04 |
| OCR 取证 | 缺失 | G124 | XHS-TOPIC-MONITOR |
| 能力增益/Learning Lift | 缺失 | G125 | capability-delta |
| 主动情报 | 缺失 | G127 | AI操作系统研究/08 |
| 播客 Idea Vault | 缺失 | G128 | FINAL_EXECUTION_COMMAND |
| S01–S72 Skill 目录与 9 项现有 Skill | 规划未列 | G130 | 序境skill/SKILL-LIST.md |
| AE Method/8 插件包 | 未列 | G130 | 序境skill/ae-method、plugins |
| 研究→能力落地表（广告法/传播/SNU/推理工程/Cue） | 未列 | G131 | 01-产品闭环蓝图-待审核 §五 |
| 统一平台恢复源码闭环 | 只在 G51 概述 | G133 | 20261007-current-status |
| 主张核验与真实审批人 | 缺失 | G136 | ae-method eval、RECTIFICATION |
| 状态词汇分离 | 散见 X33 | G137 | semantic-math |
| 变更影响定位与局部修订 | 只有 G54 撤回可追溯 | G138 | 产品闭环蓝图 示例三 |
| 话题词条库 | 缺失 | G139 | USER-ADDITIONS-20261004 |
| 零授权采集矩阵 | 缺失 | G140 | ZERO-AUTH-MATRIX |
| 官网内容体系 | 只有四表面 | G141 | WEBSITE-ADAPTATION |
| 非必要不滚动 | 缺失 | G142 | USER-ADDITIONS-20261004 |
| Skill 输出含输入/观察时间/验证状态/未知；无实例报 UNVERIFIED；S23–S32/S53–S60/S67–S72 只作后台受限插件 | 缺失 | 并入 G130 | 序境skill/plugins/*/SKILL.md、SKILL-LIST §三 |
| 数学引擎与统计模型落地 | 只有加权打分与固定阈值；无数据时返回 0/50 | G143–G159 | daily.py、alert_engine.py、本地 semantic-math |
| OpenAI Math 主引擎与九项主算法/产品闭环/训练增益 | §13 初版遗漏，只列经典库 | §13 重构、G160–G165 | OPENAI-MATH-ADOPTION、REGISTER v2 |
| 公开数据 MMM/归因（财报/统计/刊例） | 初版依赖用户输入 | G166–G169、G151/G149 改写 | 太古地产中报、SEC/DART API |

## 13. 数学模型驱动的智能（现有 OpenAI Math owner；研究采用与运行验收分开）
**主引擎：** 固定上游 `openai/math@fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb`（v2 ZIP SHA-256 92e0d179…07aa，Apache-2.0），九 family 102/103/104/107/113/114/115/139/140 已在 `lumenis/shared/evaluation/openai_math_papers/`（16 个类型化 operation，`dispatch.py` 无 eval/exec/shell/网络/模型调用）经 `agent_runtime/openai_math_paper_handler.py`→Task/API→SourceBrief→Permission→SavedWork/Artifact 接入；C2 `lumenis/system/ai_gateway/research/openai_math_papers/`（Gibbs 113 小型策略 train/evaluate，数据24/6/8冻结，既有120-step训练和独立评价回执已核：已训练、未上线）；Lean/Mathlib/Comparator 仅作为版本固定的本地证明工具；当前正式重放状态按采用记录及精确回执核对，不能从本规划推定完成。现状：九项一般主算法、全产品闭环、LLM 训练/新任务增益 **OPEN**。规则：**只有数学条件实际匹配的代码才采用对应算法或证明**；不匹配时用已有确定性方法或下列经典统计补充并记录理由。来源：00-GOVERNANCE/evidence/round-15/OPENAI-MATH-ADOPTION-20261007.md、THIRD-PARTY-COMPONENT-REGISTER.md §2026-10-10 OpenAI Math v2、ARCH:88-92/398、SOI:9-14/231/322。
**补充层：** 经典统计/计量开源库（BSD/MIT/Apache）只在 OpenAI Math 无匹配数学条件处使用，与主引擎同一 Math Engine 注册表、Evidence、版本、弃答规则。
通用原则：数学确定性计算，AI 只解释；每个输出带 模型ID@版本、输入 Evidence 引用、样本量、区间/置信度、数据状态（COMPLETE/PARTIAL/INSUFFICIENT/NO_DATA）；样本不足返回 INSUFFICIENT 并弃答，不补 0、不给中性默认；全部本地开源可商用许可；广告花费等经营数据只来自用户自填或已采集，不接付费源；用户编辑业务目标、时间、预算与约束；后端选择适用方法，方法/假设可检查，不能要求用户逐个选择论文、模型或内部参数才能完成任务。
| # | 能力 | 闭环内验收标准 | 来源/依据 | 归属 |
|---|---|---|---|---|
| G143 | **数学引擎层（Math Engine）** | 复用现有lumenis/shared/evaluation/openai_math_papers注册表与Shared Evaluation owner；登记id/版本/许可/假设/输入输出/最小样本/误差/随机性。冻结输入与运行环境，确定性结果按合同复现；浮点按声明容差而非跨环境虚诺逐位一致。派生计算回执引用原始Evidence，不能覆写来源事实；供既有Task/Gateway/Agent调用，无AI也能给有效结果。方法按业务条件后台选择，版本升级保留对照与回滚 | canonical_metrics.py、§10、G115/G116/G125、本地 semantic-math 报告“先固定语义再验证实现” | 阿康1 |
| G144 | **现有指数纠偏（只升级）** | `calculate_risk_index` 无数据返回 0、`neg_ratio` 不可算按 0 计入 → 改为 NO_DATA/INSUFFICIENT；`calculate_brand_health_score` 无数据返回 50 → NO_DATA；KOS 评分/归因系数、ctr_predictor 启发式参数登记为 v1 并标“启发式未校准”，在 G150 校准后才可称“预测” | lumenis/shared/reporting/daily.py:38-130、kos_metrics.py、kos_attribution.py、ad_intelligence/models/ctr_predictor.py、G86 | 阿康1 |
| G145 | 趋势/异常/拐点 | STL 分解+EWMA/CUSUM 告警+变点检测（PELT）替代固定“环比≥200%/阈值”；ETS/ARIMA 短期预测带区间；CTH 事件、BMP 声量、舆情日报；回测：历史注入异常召回≥0.8、误报率可报告；<14 个点返回 INSUFFICIENT | statsmodels(BSD)、ruptures(BSD-2)、statsforecast(Apache-2.0)；alert_engine.py 阈值 | 阿康1 |
| G146 | 小样本置信与排序 | Beta-Binomial/Wilson 区间显示所有比率（负面率、互动率、转化率）；经验贝叶斯收缩用于 KOS/创作者/门店排行，避免小样本冲顶；界面显示 n 与区间 | scipy(BSD)；G119 KOS 排行 | 阿康1/阿康 |
| G147 | 传播扩散 | 事件级 Hawkes 自激过程估计“爆发强度/半衰期/预计峰值”；新品/话题 Bass 曲线拟合（创新/模仿系数）；样本不足（<30 条带时间戳）弃答；回测：前 50% 时间预测后 50% 累计量误差报告 | tick(BSD-3) 或 scipy 自实现；docs/reference/CTR-EVENT-CLUSTER | 阿康1 |
| G148 | 影响力网络 | 转发/提及/合作关系图上 PageRank/HITS/中介中心性，输出 KOL/KOC/KOS 影响力与桥接者；无关系边则 NO_DATA；与粉丝数分开展示 | networkx(BSD) | 阿康1 |
| G149 | 归因与因果（公开数据优先） | 多触点 Markov/Shapley 归因用已采集公开行为路径（曝光→互动→搜索/到店公开信号），用户自填转化为可选增强；活动效果用 DiD/合成控制（对照门店/品牌/时段）；uplift 仅在有对照时；输出带区间与“相关≠因果”标注，前提不满足（平行趋势检验失败）则拒答 | dowhy(MIT)、pysyncon(MIT)、causalml(Apache-2.0)、shap(MIT)；G81 | 阿康1 |
| G150 | 评分校准与预测区间 | 所有“概率/预测”经 isotonic/Platt 校准（ECE 报告）；预测给 conformal 区间（覆盖率在保留集达名义±5%）；CTR 预测器从启发式升级为校准模型后才显示概率 | scikit-learn(BSD)、MAPIE(BSD-3) | 阿康1 |
| G151 | 营销组合与预算（公开数据自上而下，见 G166–G169） | 不依赖用户输入：用财报营销费用、公开刊例×已采集曝光估算的渠道花费代理、公开销售/客流/租金为结果，按 品牌/集团×季度/半年/年 运行 Bayesian MMM（adstock+饱和），输出渠道贡献/边际 ROI 区间与预算再分配（凸优化，用户设约束）；用户自填数据为可选细化输入；期数不足（季度<12 期）或渠道无变化则 INSUFFICIENT；样本外 MAPE 报告 | Meridian(Apache-2.0)/PyMC-Marketing(Apache-2.0)、cvxpy(Apache-2.0)；BMP Campaign | 阿康1 |
| G152 | 内容实验与选择 | Thompson Sampling 多臂老虎机做标题/封面/文案多版本选择（用户启用时）；A/B 用贝叶斯或序贯检验并显示停止条件 | mabwiser(Apache-2.0) 或 numpy 自实现；G78/G121 | 阿康1 |
| G153 | 主题/情感/立场校准 | BERTopic+HDBSCAN 主题（并 G117）；情感/立场分类器在人工标注保留集报告 F1 与校准曲线，低置信标 UNKNOWN 不计入比率；中/英/韩分别评估 | BERTopic(MIT)、hdbscan(BSD-3)；G118、G181 | 阿康1 |
| G154 | 实体消歧 | Fellegi-Sunter 概率匹配做品牌/门店/账号同一性（并 G176）；低于阈值进人工确认队列；精确率/召回在标注集报告 | splink(MIT) | 阿康1 |
| G155 | 新颖度与信息量 | 内容/话题相对历史分布的 KL/惊奇度与 embedding 距离，标“新话题/新角度”；创作反模板（G80）用重复度/新颖度量化 | scipy、numpy | 阿康1 |
| G156 | 份额与口碑指数 | SOV（声量份额，带分母与平台覆盖）、净情感/类 NPS 指数（推荐/贬损比例+区间）；SOM 仅在用户提供销售时计算；竞品同口径（G49 竞品证明复用） | canonical_metrics.py | 阿康1/阿康 |
| G157 | 多准则决策 | AHP（一致性比 CR<0.1）/TOPSIS 做选址、选号、方案比稿排序，权重由用户设定并可保存；展示敏感性 | pymcdm(MIT) 或 numpy | 阿康1/阿康 |
| G158 | 运筹与组合（与 G160 113/114/102 衔接） | 达人组合/排期在预算与覆盖约束下用整数规划（OR-Tools Apache-2.0）；数学计数/采样只作用于满足各论文假设的可行对象，不能产生真实采集总体代表性或覆盖保证，也不替代优化器；均值收益博弈类只按G161的有证据shadow范围评估 | 本地 序境-audit-reports/20261007-semantic-math/research-113-115、102-104-107；ortools | 阿康1 |
| G159 | 数学结果的 AI 呈现 | AI 只读取数学引擎结构化输出生成解释，必须引用模型ID@版本与区间；不得改写数值；卡片显示“方法/样本/置信/局限”，用户可切换简洁；解释图可采用anatomy同模型驱动几何/说明、diagram-design按语义选图的方法；后端业务结果/版本统一驱动图形、标签、三语可访问文本及导出，不给用户摆算法选择面板。 | §10、G116、G108 弃答 | 阿康/阿康1 |
| G160 | **OpenAI Math 九项一般主算法（主引擎 OPEN 项）** | 九family原要求完整保留并区分算法/证明：102复杂度归约与主定理重放；103受资源界约束的概率近似/去随机化；104有限博弈获胜集与对应复杂度；107张量提取/证书与实际乘法；113一般图计数采样与熵面结构；114拟阵/整数多拟阵oracle公共基；115固定边际表的近似或精确采样；139一般势一阶oracle采样；140有限状态回归内存下界。每项分别固定假设、输入表示、输出、复杂度和原文证明，记录完整/有限子实现/原创适配/未完成，不把困难性证明当求解器。小规模基线、反例、正式命题重放与真实产品适配分开，详见本节全文审阅裁决 | OPENAI-MATH-ADOPTION §九项主算法 | C2/C5 Math（阿康1） |
| G161 | OpenAI Math 产品落点（按采用文档 Owner 表） | SYSTEM/C1：104仅在任务可建成有限博弈且概率经授权日志核实时shadow评估，重启需核前缀累计损失；115在准确边际/容量条件下生成可行表，真实采集覆盖/分母独立核验；139查询与总成本分账、140只在匹配有限状态Gaussian任务时适用下界。CTH/BMP/C3：102/113/114区分困难性/可行性/优化/计数，creator↔岗位普通指派用既有精确匹配/min-cost flow，实际图/拟阵/整数次模rank对象满足假设才用113/114，不泛称方案数/脆弱性。Shared/C5：SourceBrief冻结问题/含义/假设/hash；BM25+余弦向量+融合+cross-encoder依独立检索证据（Recall@k/MRR/NDCG），不冒称115/140推导。Agent/C2：Comparator七项不变量，求解器与模型训练收益分账；C4来源/版本不变。F显示有用结果、来源/假设/范围/缺失/时间/限制和下一步，不要求用户挑论文/内部参数。每个适用落点用无AI正常任务验保存/修订/重开/恢复，再单独验AI增益 | OPENAI-MATH-ADOPTION 跨 Owner 表、2026-10-09/10-12 节 | 阿康1/阿康 |
| G162 | 基础分析不等 AI | `ai_task_engine._execute_analysis` 产生真实确定性计算结果；`_owned_ai_failure_code` 不再要求 AI 完成基础分析；AI 为可选增强 | OPENAI-MATH-ADOPTION 2026-10-09 节 | 阿康1 |
| G163 | 数学驱动自研 AI（训练与新任务增益）— OPEN | 按采用文档 6 步：问题/约束/验证器 → rights 与 train/val/新任务隔离 → 复用免费 Kaggle 成果 → 已核验约束/奖励接入训练入口 → checkpoint 重载、同基座同预算前后对照、模型独立与模型+求解器分报 → 经唯一 Gateway 进入产品成果；Gibbs 113 小型参数策略既有120-step及6/8验证/holdout回执已核：已训练、未上线；仅合成有限图，不计为LLM训练或业务收益，G163仍OPEN；AirLLM固定源码同时含分层推理与LoRA训练，作为现有C2低显存资源候选：先核精确gpt-oss版本、MXFP4/结构/依赖、RAM/显存/磁盘与吞吐，远程模型代码须固定审核；没有同模型实测不采用4GB/70B宣传结论，不替换基座/Provider或自动训练。 | OPENAI-MATH-ADOPTION §数学驱动自研 AI | C2（阿康1） |
| G164 | Lean/Comparator 证明重放 | 按固定Lean/Mathlib/Comparator版本与论文命题逐项实际重放，包括113 MatchingEntropyBounds；核准允许公理、输入命题/库/源码hash和错误日志；历史比较记录不自动迁移为当前PASS，未重放项保持OPEN。证明工具不进入产品Runtime | REGISTER §OpenAI Math v2、ADOPTION §固定正式证明 | 阿康1 |
| G165 | 上游撤回/修订跟踪 | 定期核对 openai/math 撤回与修订（如 10-07 撤回三稿），所用 family 若被撤回则对应 operation 自动标 REVOKED 并停止新计算 | ADOPTION v2 节 | 阿康1 |
| G166 | **公开财报数据管线** | 采集上市公司年报/中报/季报：HKEX 披露易、上交所/深交所、SEC EDGAR（XBRL frames：SellingAndMarketingExpense/MarketingAndAdvertisingExpense/ifrs AdvertisingExpense，免 key）、韩国 OpenDART（免费 key）；抽取 营销/销售费用、分部收入、零售额、租户销售增速、客流描述、出租率、租金收入；每数值带 文件/页码/期间/币种/口径（附注 vs 主表），未披露=MISSING | 例：太古地产 2026 中报披露广州太古汇零售额 +9%、租金 +11%、出租率 100%（未单列客流）；SEC EDGAR API 文档；OpenDART 指南 | 阿康1 |
| G167 | 申报主体↔登记主体关联（通用） | 以官方名称/证券代码/LEI/统一社会信用代码/子品牌与场所归属关系把申报主体映射到已登记品牌/集团/商业体（不硬编码任何主体）；集团级数据按披露口径下放到品牌/项目时必须有分部或项目披露，否则只在集团级使用 | G176、G154、subject_registry | 阿康1 |
| G168 | 花费代理估计 | 渠道花费代理＝公开刊例价/CPM/CPC 区间（平台公开价目与费率披露）×已采集曝光/内容量×商单/广告识别概率，输出区间而非点值；公开活动披露（新闻稿、获奖案例、招标公告）作锚点；无刊例或无曝光则 MISSING | G119 广告识别、ad_intelligence 平台页、IL/02 品牌营销知识 | 阿康1 |
| G169 | 自上而下 MMM 与宏观控制 | 按 集团/品牌×季度（中报/年报对齐）建模：因变量为申报收入/零售额/租户销售；自变量为财报营销费用、G168 花费代理、已采集声量；控制变量用国家统计局社零（月）、CPI（月）、文旅/假日出游、商务局商圈客流公开转引；输出贡献与 ROI 后验区间，滚动样本外检验；期数不足→INSUFFICIENT；用户自填明细可作可选更细粒度层 | Meridian/PyMC-Marketing（Apache-2.0）、NBS、G141/G140 零授权 | 阿康1 |


### 全文审阅裁决：26 份固定数学稿，不把理论承诺搬成业务事实

2026-10-14已连续读完本地26份PDF对应全文提取文本（正文、附录及参考文献；逐份路径/行数见既有 `sketches/CREATION-COVERAGE-20261014.md`）。这是全文研究，未声称逐页公式图像校对、独立证明或新训练。上游复核到 [1581d4c](https://github.com/openai/math/commit/1581d4cbdd69a0faf34b2089614fe2a814316a6a)：相对固定fd4aeeb仅两笔工作流提交，所审论文没有新字节变化；[官方历史](https://github.com/openai/math/blob/1581d4cbdd69a0faf34b2089614fe2a814316a6a/history.md)所记撤回/修订仍须逐稿适用。官网声明与模型生成稿不是独立有效性证明。九family完整要求不缩减，已提供有限实现继续复用；不能为普通业务硬套不匹配定理。

| 既有 family / 原文性质 | 必须满足的实际条件与输出 | 序境适配及不能冒称的内容 |
|---|---|---|
| 102：UGT、Max-Cut、DFVS、Min-UnCut、Vertex Cover困难性 | 固定gap/有限字母表/指定图类的归约与复杂度定理；102保留正式证明重放 | 约束优化方法选择和可承诺精度；不是业务分析算法、求解器或训练能力 |
| 103：L/RL/BPL去随机化 | 多项式时间、logspace且每条随机带停机的机，显式资源界；精度q时空间O(log n+q)、时间poly(n)·2^O(q) | 复用有限预算/误差分配/证书/全生命周期内存核算；不是RAG、上下文压缩或任意业务正确性保证 |
| 104：确定/随机/随机节点/Parity均值收益博弈 | 有限无死端图，玩家/机会节点、整数reward、有证据有理概率、liminf或其期望；各稿目标与复杂度独立 | 只对自然满足映射的有界任务shadow比较；小折扣/证书/前缀累计损失与重启分别核验，不把传播或ROI随意视作博弈；整数化/估计误差另计 |
| 107：Nine Fourths、Complex matrix、Staggered extraction | 复数/特定域、张量与字符构造、精确证书、渐近算术复杂度；非构造性存在与可实施方案分开 | 不能直接承诺现有硬件提速、bit成本、数值稳定性或任意尺寸收益；先具体程序/规模/环境比较 |
| 113：FPRAS与Entropy Face | 有限简单图、合法完美匹配面/边际；相对误差、失败概率或总变差界，零计数单独处理 | 计数/采样/熵各自有输入契约；熵不是业务质量，采样不是平台真实总体覆盖，理论多项式不保证低延迟 |
| 114：Matroid / Polymatroid公共基 | 同ground set与同rank、精确独立性oracle；多拟阵需规范化单调整数次模rank/二进制容量 | 普通达人/岗位指派先用既有匹配/优化；不把任意业务筛选器伪称拟阵oracle |
| 115：有界单元与精确均匀表 | 固定行列边际/单元上界（含0）及可行性；近似TV与精确采样不同；精确法期望多项式仍有罕见长分支 | 只生成条件可行表，不证明数据代表性；超时/取消不能冒称精确样本，无硬实时保证 |
| 139：强log-concave采样 | 已知mode、正规化势与梯度、I≤Hessian≤2I、精确一阶oracle和固定TV目标；查询模型条件严格 | 分开计oracle次数、内部计算、bit精度与墙钟成本；少查询不等于产品提速，不适用于任意资料分布 |
| 140：Gaussian回归内存下界六稿 | 有限状态单遍、无噪声Gaussian样本、球面参数、成功率/角误差和M=o(d²)条件 | 内存/样本复杂度边界，不是LLM记忆、Reranker或训练配方；后验/副本恒等仅在原分布条件下使用 |

数学采用、有限运行、正式证明和自研模型增益分账。普通CTH/BMP分析不等待九稿全部重放；无匹配数学条件仍完成原有确定性业务。G163保留已训练未上线的Gibbs有限实验及未闭的checkpoint重载/真实新任务对照，不据此升级模型或发布状态。

## 14. 剪辑与播客工程能力（2026-10-14 创作研究全读后升级；自有模型默认，BYO API 仅用户选择，不可用即显示「不可用」不切换；手动路径始终可用）
来源缩写：VWI=IL/01/VIDEO-WORKFLOW-INTERCHANGE-RESEARCH；PMR=docs/research/PODCAST_MODULE_RESEARCH_V1；PAL=docs/research/2026-podcast-ai-landscape；BMK25=品牌营销知识-25；LZ=liangzi-interview-record-v1；KOS=KOS_CONTENT_TEMPLATE_EXECUTION_SPEC；CUE=本地 Cue 逐帧审计；R07=ROUND-07-LOCAL-VIDEO-TIMELINE-CORE；PSW=PODCAST-PLAN-SAVED-WORK。
本轮六项开源来源、精确版本、代码/资源许可及源码位置统一见 `THIRD-PARTY-COMPONENT-REGISTER.md` 的“2026-10-14 六项开源采用”。Artcraft用于既有编辑/保存恢复质量，Hyperframes用于可选图文视频素材；独立创作继续接受用户自己的稿件与获准素材，CTH/BMP联动可选。外来方法使用序境视觉，原有动效不减；研究采用、源码接入和用户成果分别验收。
| # | 能力 | 工程管线与组件 | 输入→输出 | 质量门与验收（可测） | 屏 | 依据 |
|---|---|---|---|---|---|---|
| E1 | 素材入库探测 | ffprobe → SHA-256 → 源 fps/时基/CFR·VFR/音频流表 → rights=unknown；重开工程时重新指纹，字节/时长/流表变化即拒绝（Timeline.from_dict 现有能力）；借鉴Artcraft可编辑场景/时间线快照与过期异步结果隔离：已有Timeline/Artifact同一父版本保存，成功后独立读回；失败保留待保存修改，重开不丢素材/选区，AI生成不作为人工制作前提。 | 本地媒体→MediaAsset | 100% 资产有哈希/时长/时基；VFR 标注；序列化无绝对路径 | SH-01、BMP-06 | R07、VWI §5 |
| E2 | 文本剪辑 | 自有 ASR 运行时（WhisperX 类：VAD+词级对齐）→ 删词即删段，同一 Timeline | 视频/音频→逐词稿+剪切 | 删词剪点误差 ≤1 帧；保留集上报告 CER/WER 与词时间误差中位数（数值随评测出，不预设）；撤销还原 | SH-01、BMP-06 | Descript、WhisperX、PAL |
| E3 | 自动粗剪 | 静音检测（FFmpeg silencedetect/auto-editor 思路）+ 语气词表 + 镜头检测（PySceneDetect，BSD-3）→ 剪辑提议 | 素材→提议 Timeline | 提议需用户确认；词内零切；边距可调（默认 0.15s）；与人工剪对照报告保留率 | SH-01、BMP-06 | VWI、PySceneDetect |
| E4 | 字幕（优先实施：现 renderer 拒绝 TimedOverlay，字幕进不了成片） | 逐词稿 → 断行（中文默认≤14 字/行，可调）→ SRT/WebVTT/ASS → FFmpeg subtitles 烧录或外挂 | 稿→字幕文件/成片 | 同步误差 ≤100ms；renderer 接受 overlay（现拒绝须先修）；三语字幕；样式可编辑 | SH-01、BMP-06 | VWI §5、R07 |
| E5 | 多画幅重排 | 9:16/16:9/1:1/4:5 预设 → 主体感知裁切 + 安全区 + 版式重排（非拉伸） | 一个 Timeline→多画幅成片 | 像素比 1:1 不拉伸；字幕与标题在安全区内；16:9 用桌面素材重排 | SH-01、BMP-06 | CUE、品牌营销知识-24 |
| E6 | B-roll 建议 | 逐词稿关键词 → 用户已授权素材库检索 → 候选插入 | 稿+素材库→插入提议 | 只用授权素材并显示权利状态；不联网抓取 | BMP-06 | VWI §5 |
| E7 | 混音与响度 | AudioMix（音量/淡入淡出/ducking）→ 降噪 → loudnorm 两遍线性 → 真峰检测 | 多轨→混音 | 目标响度按平台预设可选并显示实测值；真峰 ≤ 目标；不重复施加增益 | SH-01、BMP-06、BMP-08 | FFmpeg loudnorm、VWI |
| E8 | 渲染导出与交换 | FFmpeg H.264/AAC 成片 + OTIO/FCPXML 导出前损失预检（G183，J5-INTERCHANGE-LOSS-PREFLIGHT：只读、确定性、逐项 code/严重度/受影响 clip，无结果不得判 PASS）；分发用 FFmpeg 二进制须先定许可（GPL/LGPL 构建）；Hyperframes作为现有C4可选HTML字幕/图解/片头素材渲染候选，输出经ffprobe/指纹后进入既有MediaAsset→Timeline→Artifact；不替换现有FFmpeg。固定帧率/时基/字体/素材及输出尺寸，实际逐帧渲染就绪后编码；脚本/资源/网络沿既有隔离许可，取消只清理本任务。源HTML保持可编辑，重开/修订需可重渲染。 | Timeline→成片/工程 | 成片可播放可重开；预检列全部损失；取消不改项目 | SH-01、SH-04 | VWI §6 |
| E9 | 脚本与分镜 | 视频短脚本模板（0–3s Hook…，时长按平台参数）→ 每镜 visual/台词/时长/目的/素材 | Brief→分镜表 | Brief 未完成不生成；事实挂 Evidence 或 UNKNOWN | BMP-06 | KOS §4E、G98 |
| E10 | 产品演示视频 | 真实界面录屏 → 「操作 A→状态 B→结果 C」镜头语法 → 交互节奏（0.5–2s 一变化）→ 局部放大/指针波纹；短版按完整动作闭环重切（不截半个动作）；产品未验收前演示片冻结 | 录屏→演示片 | 必须是真实操作录屏；横竖各自录制；附镜头表与可编辑工程 | SH-01 | CUE |
| E12 | 参考片逐帧学习 | 顺序解码全部帧 → 相邻帧亮度差/变化面积/边缘密度 → 峰值候选 + 0.5s 接触表人工核对 → 镜头/交互拆解表 | 参考视频→镜头表 | 全帧计数与已看帧数如实记录；采样不得称逐帧完成；只学节奏与交互语法，不复用商标/角色/音乐 | BMP-06、SYS-07 | Cue 逐帧审计、VIDEO-OWNER-HANDOFF |
| E11 | 封面/缩略图 | 关键帧候选 + 封面三元素（人群词+行业词+视觉钩子）→ 多版本 | 成片→封面组 | 文案兑现正文；可选 Thompson 多版本（G152）；AI 图标注 | BMP-06 | KOS-RULES §3.5 |
| P1 | 选题库 | 日/周/月 Idea Vault + 营销日历节点 + 评论区高频问题 → 选题卡；十信号确定性打分（AI 只建议信号，公式归规则），任一信号缺失返回「需补输入」且分数为空，显式 0 保留为观测值 | 信号→选题 | 每题挂来源；热度缺失显示「数据缺失」 | BMP-08 | G128、PAL、BMK25 |
| P2 | 嘉宾匹配 | 嘉宾知识库（领域/过往节目/观点）→ 向量相似度排序 | 选题→嘉宾候选 | 显示匹配理由；用户选择 | BMP-08 | PAL §2.4 |
| P3 | 前采与提纲 | 嘉宾三标准 Gate（独特体验且有公共价值/有表达能力与意愿/能引发共鸣，人工门控）→ 明线+暗线提纲 → 问题架构/追问深度模板（LZ 24 维）；录制八步 SOP（约人→提纲→拍摄间→开场→叫停→追问→结束→剪辑）作为可选流程，不固定成模板 | 选题+嘉宾→提纲 | 提纲可编辑、版本化 | BMP-08 | LZ、PMR |
| P4 | 脚本 | 单人/双人对话脚本生成，事实来自 Evidence | 资料→脚本 | 事实句 100% 有来源或 UNKNOWN；标「AI 生成」 | BMP-08 | PAL §2.2、内容学习源合同 §8 |
| P5 | 录音/导入 | 多轨录音或导入 → 真实波形 | 声音→音轨 | 波形来自真实采样；音频流显式选择 | BMP-08 | G28、PSW |
| P6 | 转写/说话人/章节 | 自有 ASR + 说话人分离（pyannote community-1 类）+ 段落/章节 | 音轨→逐词稿+说话人+章节 | 保留集报告 DER 与 CER；说话人可手动改名合并 | BMP-08 | PMR、PAL、WhisperX |
| P7 | 文本剪辑 | 同 E2/E3（删词即剪、去语气词/长停顿）；原文与校对稿分开保存，改稿不等于改音频；每次编辑带 revision+内容摘要，过期基线拒绝；多音频流必须显式选流；按说话人分轨仅为轮次分轨，不是声源分离 | 稿→剪辑 | 同 E2/E3 | BMP-08 | Descript |
| P8 | 配音（可选） | 自有 TTS 运行时，多音色；声音克隆仅本人授权 | 脚本→配音轨 | 用户选择才启用；标「AI 配音」；无授权不克隆 | BMP-08 | PAL §2.2、CosyVoice(Apache-2.0) 作候选权重 |
| P9 | 混音母带 | BGM ducking → 降噪 → loudnorm 两遍线性 I=-16 TP=-1 → 写响度元数据 | 多轨→母带 | 实测 -16 LUFS ±1、真峰 ≤ -1 dBTP（ITU-R BS.1770） | BMP-08 | Apple 音频要求、FFmpeg |
| P10 | 发布包 | MP3/M4A + show notes + 可编辑七件套（plan.json/script.txt/原文 VTT/校对 VTT/chapters.json 1.2.0/corrections.json/metadata.json）+ 章节 JSON + 字幕稿 VTT/SRT + 封面 + RSS（podcast:transcript/podcast:chapters） | 母带→发布包 | 发布需用户确认；RSS 校验通过；不自动发布 | BMP-08、SH-04 | Podcasting 2.0、Apple Transcripts |
| P11 | 切片与跨平台 | 先出 2–3 分钟卡段（小故事闭环+金句）→ 故事节点→切片候选→9:16 音频图/引语卡→各平台重包装 | 节目→切片组 | 每切片挂时间码与来源；平台包装各不同 | BMP-08、BMP-06 | 内容研究 05、LZ E 层 |
| P12 | 分析与学习 | story_node_density/emotion_peak_density/insight_density/question_quality/interview_yield/asset_reuse/retention 曲线（有平台数据时）；每次运行记 run_id/pipeline/model/prompt/input_hash | 节目+观测→指标 | AI 派生指标标注非权威；跨平台不互推；缺数据=缺失 | BMP-08、SH-05 | PMR §5-6 |
| P13 | 研究阅读器与学习晋升 | 研究分级（事实/观察/模式/假设/验证/可迁移/不可照搬）；证据侧抽屉不打断阅读位置；学习候选需证据，≥2 次验证才晋升，出现反例即否决；指标不混用不同平台分母 | 案例→可复用规则 | 无证据结论标「未核实」；AI 建议不自动成为事实 | BMP-08、SH-05 | podcast/research、learning.py、research_pipeline.py |
| G170 | 内容学习源合同落地 | Narrative/Copy/Visual/Motion/Campaign/Evaluation 六个模式注册表 + ContentLearningAsset；按 Brief 范围检索不全文注入；事实墙（事实→Evidence，创意→模式，未知→UNKNOWN）；13 段生产链 Brief→…→Learning保留父引用、版本、上下文指纹及变更依赖；中韩英按语义意图重写不直译 | Brief→原创产物 | 合同 §14 十项验收全过 | BMP-06、SH-05 | LUMENIS-CONTENT-CREATION-LEARNING-SOURCE-CONTRACT-V1 |
| G171 | 内容审核与客户解释 | ContentReview 9 维（平台/节点/品牌/情绪一致/视觉叙事/话题/搜索/商业/风险）→ READY/NEEDS_REVISION/BLOCKED/NOT_VERIFIED；视觉叙事 7 角色；话题 5 层；每次 2–4 个候选附取舍；专业理由+客户版解释 | 候选→审核结论 | 推荐与已验证表现分开显示；不承诺流量池 | BMP-06 | CONTENT-INTELLIGENCE-SPEC-v1 |
| G172 | 创作者→AI 发现观测 | Creator→Content→AI 引用/推荐观测，链接类型 direct/source/thematic/unknown；指标不合并成单分 | 观测→分层指标 | 共现不作因果；Unknown 不转 Missing | BMP-05 | GLOBAL_BIL_CREATOR_AI_DISCOVERY_V1 |
| G173 | 出海视频矩阵 | TikTok/IG Reels/YT Shorts/KOC 金字塔/店铺闭环 + 7 区域营销节点自动带入视频脚本 | 区域+节点→脚本与矩阵 | 节点来自营销日历数据；各平台重写包装 | BMP-06、BMP-07 | 品牌营销知识-24 |
| G174 | 播客现有代码违反「缺失≠0」的待修项 | ① podcast/intelligence/topic_score.py 旧版信号默认 0.0 并夹取，应并入 topic_scoring.py（缺失=需补输入）后删除旧版；② breakout.py 基线≤0 返回 normal，应返回「基线缺失」；③ podcast_routes /content-yield 引用不存在的 content_yield 模块，应补实现或下线该路由并显式报不可用；④ podcast_store.upsert_entity 缺 observed_at 时填当前时间，应拒绝或标未知；⑤ test_podcast_smoke 授予全局审批 '*'，应改为最小范围；⑥ 实体路由在有域/焦点/操作者列的迁移前保持 503 | 读码 2026-10-14 | 阿康1(C) | 闭环内 |
| G175 | 能力分层验收 | 凡学习/创作能力按 SOURCE→RUNTIME→DATABASE→TEST→USER OUTCOME 分层报告；自动化 PASS 不得表述为用户已达成效果；外部数据集按许可证署名（如 CC BY 4.0）并标改动；第三方密钥只放服务端私有变量；文化内容不把刻板印象当规则 | KMS AUDIT-52、EDUCATION-OUTCOME-GATE、NONCOMMERCIAL-SOURCES | 阿康1(C) | 闭环内（USER OUTCOME 属真实用户验证，闭环后） |

## 16. 同一对话承接长期工作：逐项核实与现有能力采用

本节完整承接2026-10-14 PO提供的person-like agent分析；其产品问题不缩减，但把官方声明、公开源码、个人反馈与商业/技术推断分开。不是新增产品、IM服务、Agent Runtime、调度器或电脑控制。以下均为研究采用与闭环要求，不能写成当前运行完成。

| 原文命题/问题 | 核实结论 | 现有序境落点与验收 |
|---|---|---|
| Instinct是personal agent；Muse可能也是 | Instinct官网明称personal assistant；Meta官方明确Muse是personal agent，不需保留“可能”。个人定位不证明只做私人小事 | 保持序境商业运营/品牌市场定位及独立Shared制作；面向真实工作目标，不能改成私人管家产品 |
| Grok Bot不是且不想是personal agent，承接办公/创业/长任务 | 官方称持久AI teammates，公开工作案例和跨任务协作支持“范围更广”；“不想是”属动机推断，不能替厂商断言 | G56/G83覆盖研究、业务分析、制作等已有长任务；由成果而非角色数量定义完成 |
| Instinct抽佣、Meta交互广告、Bot订阅，因此偏好多烧token | Instinct条款含付费/订阅，没有取得“主要抽佣”依据；Meta明说Muse对话/VM数据不共享给广告系统；Bot含订阅额度及可选额外用量，但用量增加不等于利润增加 | 不把未经证实的商业动机写入序境策略。SYS-08沿真实用量/预算/用户授权，优化每个有效成果成本，不为消耗额度委派或发消息 |
| person-like一类；祖宗是OpenClaw；几乎无限能力装进IM | person-like可作交互分析名称，不是官方统一分类；没有证据证明上述闭源产品继承OpenClaw代码；能力有工具/权限/资源边界 | 采用易懂对话入口，不宣传万能或无边界，不取消原架构导航及独立业务/制作入口 |
| 人有记忆；LLM无状态且上下文有限 | 单次推理上下文与产品外部持久记忆分开；长对话不能靠无限追加上下文解决 | G109复用agent_memory、Shared Learning、Task checkpoint：有来源的偏好/任务/资料分层检索，更正/失效/删除传播；记忆不产生Canonical事实或授权 |
| session列表造成负担，一个session又难承载多需求；豆包案例 | 会话过载是需验收的问题；“唯一国民级”及多数用户不知道新会话未取得可靠总体证据。Muse主聊天仍保留侧聊，不等于强制所有内容混在一个上下文 | 首页一个输入可追加多个任务，任务身份/范围/版本独立；按需打开历史、项目或分支，不强迫新会话；也不把不同任务混作同一事实/权限 |
| 推理耗时造成发送后被迫等候 | 官方支持在工作中继续发消息与后台工作；实际延迟/满意度仍须序境实测 | 输入不锁死，及时给真实接收/必要范围澄清；主对话能继续，长工作在已有后台执行；记录首个有用反馈/最终成果时间而非假进度 |
| 单入口并发、不展示推理中间态、直接交付、鼓励异步 | 采用不展示私有思维链；官网同时保留任务活动、授权和结果。不能误解为隐藏所有进度或永不回复 | G56/G111：可看实际状态/停止/改优先级，默认少打扰；有用部分结果可交付并声明范围，最后给真实成果/依据/局限/后续动作 |
| IM像与人交代多事，做完通知；用户不应学复杂workflow | 官网支持自然对话和长期任务，但安全/权限仍有确定控件 | 输入问题与材料即可沿已有Owner处理；真实任务卡/停止/审批/修订入口清楚，不暴露论文选择、内部run ID或代理配置作为必填 |
| Instinct无头、iMessage；Muse/Bot相同设计；市场反响好 | Instinct首页主打text/call，但条款也含App/工作区，不能绝对说无客户端；Muse/Bot有各自客户端。个别反馈不能证明总体市场反响 | 采用低心智入口和异步方式，不照搬渠道、外部帐号或UI；用户期待用目标任务走查验证，不按下载量或轶事替代 |
| 主loop及时回复、长时间idle，绝大多数交给subagent | OpenClaw可核非阻塞spawn与完成交回；Grok公开异步handoff但没有证明其所有任务内部delegate实现或原提示词 | G83在已有Task Engine/Agent Runtime内分离对话接收与长任务执行；重I/O/长计算可有界委派，短问答/确定性轻操作直接做。idle是可响应的结果，不是人为目标；有并发/预算/深度/单写者限制 |
| 子任务完成回调唤醒主loop | 公开文档有completion handoff；接收、执行、提交、成果验收、通知分别发生 | 原actor/task/attempt/version校验、取消栅栏、幂等回调、Owner成果读回、原会话路由；恢复先核已提交结果，旧回调不能复活取消任务或覆盖新版本 |
| final assistant text自动发声会让模型不能闭嘴 | 这是可验证的设计风险，不是所有模型必然行为；OpenClaw存在NO_REPLY和独立delivery控制 | 在现有通知/回复边界将内部摘要与用户可见消息分开；低价值过程留状态，重要完成/失败/请求决定才送达；用户主动问进度仍应答 |
| senduser是唯一voice、text只是snippet | 未找到可验证的Grok官方源码/提示词来确认该引文；保留为PO提出的采用方向，不冒称逆向还原 | 用现有NotificationRouter/消息投递合同实现单一可见发送边界；最终文本不能绕过它双发。确定schema、收件人/会话/权限/事件版本/去重键、回执与失败恢复；只含可公开摘要，不输出隐藏思考 |
| 群聊/私聊同构；自主选择发言，优于全员回答或强制@ | Grok帮助支持普通群消息自主回应、可选@/Reply；不同敏感动作仍有私密确认差异 | 沿已批准Agent Groups/多人能力复用同一task/result/delivery协议，私聊与群聊仅参与者/可见范围不同；不新建群聊产品。不能把群成员当授权者，避免共享私聊记忆/凭据；@是可选指向，明确分工防重复 |
| 社区反馈如何进入产品 | Cursor论坛有无直观运行信号、跨Bot联络失败；Muse社区有表现下降的抱怨和不同解释，均是个案，原因/发生率未独立证明 | 增加真实验收：任务交接不丢、结果消息不漏不重、可看运行状态、错误不假成功、纠正后不反复引用旧记忆；不用个案宣称竞品普遍失败 |

### 现有源码落点及完成出口

本轮固定eaa20ac源码审阅：`agent_runtime/loop.py`已有同步run/cancel和持久恢复检查，`agent_runtime/durable_adapter.py`复用Task Engine；`agent_memory/`和`lumenis/shared/learning/memory.py`已有记忆/学习生命周期；`agent_focus/notification.py`已有静默进度/重要信号/人工决定三级及去重/限频；`lumenis/shared/reporting/delivery_preferences.py`与`experience_runtime.read_reporting_notifications`已有成果通知feed；AI-01经现有Skill execution提交，SH-06有授权任务投影。**这些源码存在不证明非阻塞多任务、可靠完成唤醒或完整跨端交付已经接通。** 未接线项继续归G56/G57/G83/G109/G111/G116，不新增平行管理清单或假接口。

统一工程出口：用户先交研究A，再交独立创作B，随后修订A/停止B；同一输入区始终可用，A/B来源和范围隔离；网络中断或Core重启后读回原任务，已提交成果不重复产生，取消B后的旧回调无效；A给可用Artifact与引用，能保存、修订、重开；只给必要且去重的通知，授权请求不能被静默吞掉；群内不暴露私聊资料。无模型时原业务/手工制作仍可完成；若当前Owner接口缺失，修接口并实操验收，不用模型口头回报填空。Web、Windows/macOS、iOS分别验中英韩/无障碍/后台生命周期；关闭客户端不等于宿主Core继续运行，离线/休眠能力按实际运行边界如实显示。

### 固定来源、权利和采纳边界

- Grok Bot：[定位](https://docs.x.ai/grok-bot/overview)、[消息与协作](https://docs.x.ai/grok-bot/chat-and-collaboration)、[成果](https://docs.x.ai/grok-bot/files-and-results)、[权限](https://docs.x.ai/grok-bot/approvals-security-and-privacy)、[用量计费](https://cursor.com/help/grok-bot/plans)。公开官方说明，2026-10-14读取；ADAPT操作方法，不复制界面/资产/私有实现。
- Muse：[官方发布与隐私边界](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)、[设计原文](https://introducing.muse.ai/)、[安全工程](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)。ADAPT低打扰、任务透明及受控浏览器接管；其VM/终端/OS能力不进入序境。
- Instinct：[官网](https://instinct.com/)、[条款](https://instinct.com/terms)。只采用简单入口方法，不引入其交易/训练/数据条款；商业模式动机保持未证实，不作为产品决策事实。
- OpenClaw固定[c86d0f8](https://github.com/openclaw/openclaw/tree/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336)：[memory](https://github.com/openclaw/openclaw/blob/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336/docs/concepts/memory.md)、[sessions](https://github.com/openclaw/openclaw/blob/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336/docs/concepts/session-tool.md)、[announce](https://github.com/openclaw/openclaw/blob/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336/docs/tools/subagents/announce.md)、[spawn源码](https://github.com/openclaw/openclaw/blob/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336/src/agents/tools/sessions-spawn-tool.ts)、[silence源码](https://github.com/openclaw/openclaw/blob/c86d0f80023d8dc22dcd1f8ed1cc1b7271414336/src/auto-reply/tokens.ts)。MIT许可，活跃维护；仅原理ADAPT，未安装/复制源码或建第二Runtime，不采用其自动模型切换。客户端相似或名称相同的Muse开源库不能证明Meta Muse血缘。
- 个案：[Cursor跨Bot联络](https://forum.cursor.com/t/chief-of-staff-unable-to-communicate-with-other-bots/173238)、[状态可见性](https://forum.cursor.com/t/grok-bot-no-glanceable-working-finishing-signal-unless-the-pointer-is-on-the-bot-icon/168456)、[Muse讨论](https://www.reddit.com/r/MuseAgent/comments/1x2dtux/muse_getting_dumber/)。用于形成针对性恢复验收，不作为官方能力/根因/总体满意率。来源含动态内容，不把宣传或未经核实用户评论升级为Canonical事实。


## 17. 长图工程建议：逐项理解、原理核验与现有能力适配

来源为PO于2026-10-14提交的长图（原图1110×9850；保留原件）。图中实际编号为1–7、9、10、13–15；8、11、12未出现，不补写成已收到要求。以下覆盖引言、每项“构建/为什么/用途”，区分建议、上游证据与序境采用；不把夸张或未测数字变成事实。全部沿本规划原条目/现有Owner落实，不建立第二Runtime、向量真相、研发调度器或验收体系。新增生成动效与本节分开：原有动效、触发、风格和设置全部保留。

| 原图内容与完整意图 | 原文/源码核实与需纠正的推断 | 序境采用、实际落点与完成出口 |
| --- | --- | --- |
| 引言：通读Anthropic源码控制工程文，用于两种开发者模式/工程治理；研究Claude、OpenAI、Grok、Muse公开实现提升产品 | Scion是Anthropic特定大仓库/大量并发变更下的内部实现；文章不等于公开了可安装Scion，也未证明序境需要替换Git。不可把其他团队规模、性能、发布策略搬为本产品结论 | ADAPT：复用不可变提交/父版本/内容hash、可重建派生索引、小范围审查及缓存失效思想；现有branch→PR→当前组合版本CI/审查→合并→远端读回保持。两种开发者模式沿既有沙箱/变更预览/签名更新/回滚，不赋任意写库、修改权限或上线能力；不安装源码管理系统、不降低合并门禁 |
| 1 动态上下文组装器，产品：预算工作记忆、工具schema、检索文档；防上下文溢出，“提示工程已死/#1杀手” | 官方将上下文工程视为提示工程延伸，非取消提示；没有本产品故障排行证据。长上下文仍受相关性/噪声影响 | G83/G108/G109：既有Agent/Task/Gateway请求组装按已选模型真实窗口预留输出与工具结果，分别计量规则、任务状态、schema、检索预算；原始引用按需载入，保留最新PO/用户约束、未完任务、actor/scope/版本及副作用回执。压缩不能删需求、改模型或丢函数调用配对。超预算可解释拒绝/缩短可选上下文。验超长资料、压缩恢复、未知模型上限及旧指令不复活 |
| 2 持久状态机，研发Codex/阿康：checkpoint、指数退避、人工Slack审批；Temporal或LangGraph DAG支撑长任务/崩溃恢复 | 持久checkpoint与跨会话store不同；RAM示例不能重启恢复。重试本身不保证外部效果只发生一次，也不证明所有任务必需DAG框架 | G83/G109：复用Task Engine、agent_runtime/durable_adapter.py及原预约/续接；保存task/attempt/lease、已提交成果、下一步与累积预算，重试有上限/退避/取消。人工审批关联真实发起者/动作/范围/版本/有效期；Slack仅在既有连接已授权并接通时承载通知与审批回执，不新增连接或授予审批权；普通消息/代理ACK不构成批准。验崩溃重启不重复写、撤权后拒绝、旧审批/过期回调不生效。仅借鉴，不安装Temporal/LangGraph或新后台队列 |
| 3 原始MCP服务/客户端，产品及研发：JSON-RPC、范围凭证、数据库与API工具、减少私有包装 | MCP规范并不要求抛弃官方SDK；手写协议不天然安全或更可扩展。协议标准化不能消除业务授权；上游明确反对token透传 | G187及mcp_skill_runtime.py/mcp_discovery.py：复用版本化工具schema、注册与类型化业务API；禁止暴露原始SQL、库句柄、Cookie或CDP凭证。验证协商版本、请求ID、结果/error、超时/取消、参数边界、凭证audience、Origin/回环与SSRF。工具清单可见不等于可调用，数据权限逐次验证；既有SDK/适配层可保留 |
| 4 系统一级分诊，产品：95%快速类型化决策模型，5%重量推理；控制单位经济 | 95/5是提案中的比例，不是官方通用最优或实测值；快/便宜不证明足够正确。产品模型路由与研发窗口手选模型不是同一设置 | G108、唯一Gateway：确定性业务直接计算；按任务类型、风险、输入大小、已准入模型能力与用户选择作显式路由，记录原因/真实用量/质量与延迟。只有已授权服务可执行，不自动切provider/充值/降模型，未知资源显示不可用且不堵基础链。同题同质量比较后才能采纳比例；保存原模型/recipe版本，升级路径需实际可用 |
| 5 自我修正RAG，产品及研发：批判搜索结果、重写模糊查询、薄弱时明确弃答；知道何时再搜 | Contextual Retrieval支持补充块级语境、BM25+embedding和重排；它不等于自动实现自我纠错，论文/厂商收益不可套用。模型自信不是证据充分性 | G108/G109及现有Importer/Research：保持向量余弦+BM25→cross-encoder重排→来源/范围/时间核验；原文与派生块语境分开，新增上下文不得伪造事实。检索重试有预算、去重、结束原因；矛盾/撤回/弱证据给可用部分、引用及缺口。普通关键词/精确引用无AI可用，不冒称完整Hybrid。验多语同名主体、精确ID、失效来源、无支持、重写不扩权及真实资料检索效果 |
| 6 三层记忆，产品：工作草稿、情节摘要、语义向量与重要性评分/驱逐；避免失忆和无限膨胀 | 三层是可采用设计；“第五轮必失败”无通用证据。持久保存、检索召回和压缩保真分别成立 | G109复用agent_memory/working.py、episodic.py、semantic.py和Shared Learning；任务/用户/组织范围分离，重要性由版本化规则与证据决定。驱逐仅控制检索缓存/工作上下文，不擅删Canonical、审计与成果历史；更正/忘记/撤权传到摘要及索引并可读回。semantic.py当前词项打分不算已具向量语义检索。验重启恢复、冲突记忆、跨用户拒绝及检索预算，不新建记忆数据库 |
| 7 轨迹CI，研发：工具序列对黄金DAG评分，偏离阻PR；定位最终答案隐藏的过程错误 | 轨迹帮助追责，但单条黄金调用顺序会误拒等价安全路径；执行轨迹不是私有推理链。分数不能代替真正成果 | G83/G134、lumenis/shared/evaluation/trajectory.py及原CI：按任务声明允许动作/关键偏序/权限拒绝/幂等/取消/成果读回不变量；等价路径可通过，安全越界或缺必要提交拒绝。轨迹与当前组合源码、输入/版本、独立OutcomeAssertion绑定，脱敏保留失败。单位/集成回归和真实E2E分开；不因新分数取消原门禁或把他人旧回执迁给新组合版本 |
| 9 实时语音打断，现有产品语音升级：VAD、亚1秒中断、SSE/WebSocket及感知延迟 | Realtime官方区分WebRTC与WebSocket；SSE仅服务端下行，不能单独承担双向音频。停止生成、停止播放、截断未播放上下文是不同动作；亚1秒需实际测量 | 现有owned_speech.py、Read Aloud/AI-01及媒体Owner：用户发起、录音权限、转写可修订；按实际transport实现打断/停止音频队列/清理未听内容、重连及任务返回，记录p50/p95打断和首音时延。现有Whisper离线评估或本地朗读不等于实时对话已接通；无模型保留手写/编辑/播放，不自动开麦/接外部语音API。隐私、语言/平台可用性及音视频成品验收保持独立 |
| 10 DPO反馈飞轮，产品：点踩→偏好对→夜间LoRA；利用真实失败/边缘案例 | DPO需要同一输入下preferred/non-preferred成对回答及可信偏好；点踩单独只有负反馈。DPO目标与LoRA参数化是不同维度；夜间不是训练授权 | 现有Shared Learning/training_review.py及C2：原输出/纠正/来源/模型版本和同意分存，补齐人审偏好对，过滤隐私/权益/重复/错标签，独立held-out防泄漏。精确MODEL_TRAIN授权及免费资源验证后才可训练，checkpoint重载/新任务对照/安全回归/晋升回滚分别验收。保留夜间批处理作为获准任务的调度选项，默认不自动触发训练，不改生产模型 |
| 13 计算机使用回退，研发及产品适配：REST失败404后无头浏览器，处理遗留门户 | 404可能是路径/版本/权限掩码错误，不能自动视为允许浏览器；有API失败不说明网页登录同等授权 | 沿已批准Browser/Collector能力核对API错误、原任务范围与来源许可后，才选择已有受控浏览器适配。401/403/429、挑战、会话失效各走原恢复，不能绕认证/限速；写动作先核外部回执避免重复。产品仍无通用OS/电脑控制；研发工具使用也不能扩大个人会话权限。验合法匿名网页、既有获准会话、人工接管/返回、取消恢复 |
| 14 PII解掩码，产品：进入上下文前敏感数据替换UUID，生成后恢复并审计；保护客户数据 | 可逆替换是去标识化而非匿名化；Presidio示例明确共享映射非线程安全，不能原样投入多用户并发。Regex/token遮盖不证明所有PII已检测 | 既有安全入口/Permission/Gateway：最小化字段，按租户/用户/任务绑定映射；映射不进模型、日志或公共成果。只对已认证且仍有权的接收者恢复已知占位符，模型新造UUID/跨任务映射拒绝。脱敏审计记录版本/动作不含原秘密；撤权/删除策略覆盖缓存。验中文/英文/韩文、结构化与文档输入、并发隔离、误报漏报与恢复失败；不宣称绝对防泄漏 |
| 15 公共架构拆解，研发日志及进度审计：3个已发布深度剖析、系统图、成本/延迟基准、ADR | 文章数量不等于产品质量；缺同口径实测不能写提升百分比。内部私库发布与向公共互联网发布是不同授权 | 沿现有规划/审计记录形成三份可审阅案例：上下文与恢复；资料检索到成果；受控浏览器与权限。每份给真实输入/数据流、版本、实测口径、失败和取舍，未知标未测；只发布已获准且脱敏的内容，未获公开授权不外发，不为凑篇数新建治理体系。原产品验收仍以用户任务为准 |

### 一手来源、固定源码与采用边界

核对日期2026-10-14。以下是针对具体机制的阅读，不声称逐字读完各仓库所有源码；研究/规则采用不等于功能实现或运行通过。

- [Anthropic源码控制工程](https://www.anthropic.com/engineering/redesigning-source-control)（2026-10-13）与[上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)（2025-09-29）：内容寻址、派生索引和上下文按需加载/压缩；原规模/收益只属原案例。
- [LangGraph持久化](https://docs.langchain.com/oss/python/langgraph/persistence)：checkpoint/store、内存与持久恢复区别；仅对照现有机制，未引入依赖。[MCP 2025-11-25 transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)及[安全规范](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)：固定协议版本，不混用draft。
- [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval)：块语境、BM25+embedding及reranking；保留序境已批准cosine/cross-encoder要求，其实验百分比不写为序境收益。
- [OpenAI DPO](https://developers.openai.com/api/docs/guides/direct-preference-optimization)及[Realtime交互](https://developers.openai.com/api/docs/guides/realtime-conversations)：从官方文档MCP获取正文；只采用方法/事件语义，不启用收费API。
- [Claude Agent SDK Python@f33ec2b](https://github.com/anthropics/claude-agent-sdk-python/tree/f33ec2b1e31abf9d6a285eb286e13336f283a00e)：已读LICENSE、README及permission callback例子。LICENSE为MIT，README另列Commercial Terms，不能把SDK代码许可等同服务免费。`allowed_tools`是自动允许列表，不移除工具；例子的宽泛只读/命令放行不照搬。可借鉴类型化权限回调、工具错误与会话快照版本；不安装/启动Claude客户端。
- [OpenAI Agents Python@5eb47a5](https://github.com/openai/openai-agents-python/tree/5eb47a5bdeab8ba9f6087de288c7e606816c76c6)：核对sessions与guardrails中相关段落；MIT。审批恢复保持同一session/store，不能叠加两个会话真相；并行输入guardrail可能晚于工具效果，因此序境Permission在效果前同步生效。会话保存不能把拒绝输出/原凭据带入下次上下文；现有Owner适配，不引入第二SDK运行体系。
- [Grok Build@2bdd1d6](https://github.com/xai-org/grok-build/tree/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8)：已读README、`crates/codegen/xai-grok-config-types/src/permission.rs`；一方Apache-2.0、vendored组件各守原许可。遗漏action默认Deny、未知工具拒绝反序列化可作为验收反例；不是Grok Bot完整服务源码或产品权限替代。不安装、不读取外部会话、不上传仓库。
- [Muse官方安全工程](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse)：采用代理与权限/凭据隔离、显式接管/审批思想；对应既有Permission/Effect Fence/受控浏览器，不复制VM/OS能力。此次官方页面与关联GitHub检索未核得Muse agent完整官方开源实现；同名词向量MUSE、音乐bot和第三方复刻不是它。未核得源码保持NOT_VERIFIED，但已核官方工程原则继续落地，不虚构代码血缘。
- [Presidio@2523c7b](https://github.com/microsoft/presidio/tree/2523c7b74a469270c5c78bb253f140eafca21e31)，MIT；已读`docs/samples/python/pseudonymization.ipynb`说明与映射设计。借鉴占位符/反向映射及并发风险；未安装模型或替换现有安全Owner。

### 当前代码与验收缺口（本次固定基线ed212ce3）

`agent_runtime/loop.py`/`durable_adapter.py`已有恢复scope校验、累积预算和checkpoint；`agent_memory/working.py`已有短期记录和显式持久失败计数，episodic/semantic已有检索但词项匹配不能冒称向量检索。`mcp_skill_runtime.py`已有受控安装、注册调用及人工审批检查。`lumenis/shared/evaluation/trajectory.py`已有确定性操作评分和独立OutcomeAssertion，不能把操作分数当用户成果通过。`owned_speech.py`是固定离线Whisper评估适配，Read Aloud是用户发起本地朗读；完整双向实时语音尚不能从这两者推出。`training_review.py`已有精确MODEL_TRAIN人审资源，不能用新图覆盖它。checkpoint当前识别凭据的遮盖不是通用多语PII识别证明。

以上缺口落在本表对应原G项和现有Owner；要求仍全部保留。闭环验收分别取得基础无AI结果、增强效果、恢复/撤权、运行组合版本、模型训练/晋升证据；此研究提交不把任何未运行能力改成ACCEPTED。
