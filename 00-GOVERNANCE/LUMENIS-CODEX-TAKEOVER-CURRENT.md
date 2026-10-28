# 寰意 / OEVIRA — Current source and acceptance

Status: **CURRENT EXECUTION ENTRYPOINT / NO-REDISCOVERY**

本文件只记录当前产品源码与验收边界，并导航到唯一权威文件。开发者开工、暂停、忙闲、模型选择和窗口派工不写入仓库；实际任务以 PO 的当前直接指令为准。历史修复、运行与失败记录保留在原证据和 Git 历史，不复制成当前规则。

## 1. Online reader's current-state snapshot

Implementation publication state: `SOURCE_RETIREMENT_ONLY`
Runtime load state: `NOT_LOADED_OR_NOT_VERIFIED`

以上标识只说明此源码快照属于获批清退，不表示已合并；main 发布必须经 PR 检查、审阅、合并和远端读回。开发分支不等于 main；不以本文件提前宣称合并、运行加载或验收完成。

| 范围 | 当前源码与验收事实 | 对应依据 |
| --- | --- | --- |
| 被否定的前端 | 删除清单中的 79 个 Flutter/Website 呈现文件已退出本次源码；另清除两个混合文件中的旧视觉组件，保留非视觉状态、草稿及数据处理。完整前端要求未撤销，新前端尚未交付。 | [精确清退清单](evidence/round-15/workspace-continuity-20261024.json) 的 `rejected_frontend_retirement_20261028` |
| 清退合并 | PO 允许源码清退按专用门禁合并；按批准清单、原 blob、保留源码与合同验证，不能恢复旧骨架或放入占位页面换取构建通过。 | [直接批准](evidence/approvals/PO-20261028-SOURCE-RETIREMENT.json)；[机器合同](LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json) 的 `frontend_source_retirement` |
| 产品发布 | `BLOCKED`：完整新前端、官网/Web/Windows 构建与同版实际工作验收未完成。源码清退合并不代表产品可用；恢复 ACTIVE 后完整构建、界面与发布门禁仍必需。 | `scripts/audit_tools/experience_gate_mode.py --require-product`；原 Release Gates |
| 业务初始数据 | 新工作区允许为空，不要求内置主体、业务记录、种子或固定语料。用户输入及已获准的导入/采集经原权限与数据链进入产品；已有用户资料不删除。 | [范围与数据合同](LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md)；原 Collector 合同 |
| 保留源码 | 原 Core、CTH/BMP/Shared/SYSTEM、控制器、仓储、平台宿主及接口合同继续保留。源码存在不等于实际能力已经验收。 | [Source Owner Index](LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md) |
| 运行与数据库 | 本次结构和源码清退不证明某个进程已加载该版本，也不执行生产切换或数据删除。历史 Core 恢复结果只对其记录版本有效。 | 原 Runtime、DB、恢复回执 |
| 未发布工作 | 既有未提交/未合并有效工作必须与当前 main 逐项核对，不能因清退 PR 合并而自动算已发布。 | 实际 `git status`、分支差异及 PR，而非旧数量或旧 SHA |

没有预装数据不降低能力验收：采集、分析、创作等仍须以获准真实输入验证，缺少数据不得造零值或虚构成果。空库成功启动不等于采集成功或业务闭环。

## 2. Canonical navigation / 唯一文件导航

| 文件职责 | 唯一入口 |
| --- | --- |
| 执行约束 | [AGENTS.md](../AGENTS.md) |
| 原则层 | [The Product Owner's lightweight AI-native constitution](AI-NATIVE-PRODUCT-CONSTITUTION.md) |
| 机器治理、门禁与批准 | [LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json](LUMENIS-GOVERNANCE-MACHINE-CONTRACT-V1.json) |
| 产品架构与领域边界 | [Product Architecture](LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md) |
| 完整实施要求与原 ID | [主规划](LOOP-PLAN-20261014/product-plan-full.md)、原 requirements/coverage 与 [采用交接](evidence/round-15/source-adoption-20261018/EXISTING-OWNER-WORK-HANDOFF.json) |
| 体验、完整草图与界面合同 | [00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md](LUMENIS-EXPERIENCE-CONSTITUTION.md)、[完整草图](LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md)、[Screen Specifications](../contracts/experience/screen-specifications/) |
| 表面角色及设备条件 | [Multi-Surface Decision](LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md) |
| 文件布局、源码职责与调用导航 | [00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md](LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md) §3 |
| 真实成果及退出条件 | [00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md](LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md) |
| 主体、来源及数据范围 | [00-GOVERNANCE/LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md](LUMENIS-GLOBAL-UNIVERSE-CONTEXT-DATA-MATURITY-CURRENT.md) |
| 来源返回合同 | [source-target-contract-v1.json](../contracts/experience/source-target-contract-v1.json) |
| 跨产品合同 | [00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md](CROSS-REPO-CANONICAL-REGISTRY-V1.md)、[00-GOVERNANCE/LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json](LUMENIS-GGI-CROSS-PRODUCT-CONTRACT-V1.json) |
| 安全边界 | [SECURITY-BOUNDARY-CURRENT.md](SECURITY-BOUNDARY-CURRENT.md) |
| 开发入口与工具参数 | [CONTRIBUTING.md](../CONTRIBUTING.md)、[仓库工程工具](../.codex/README.md) |

跨产品合同 v1.1.0 指纹为 `68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`，它是协议身份，不是实时源码版本。工具链版本从原 manifest/lockfile 读取，不在此重复常量。

### CURRENT CONFIGURATION / TOOLCHAIN CONVERGENCE

`app/toolchain.json` 与包内锁文件是构建输入。`.env.example` is documentation only，不覆盖实例私有配置。local private C2 runtime specification 只描述对应实例，实际模型装载、权利和运行版本须单独读回；仓库中不复制私密配置。

## 3. Current owner continuation

以下列出原职责与仍需实际核验的能力，不记录任何人的执行状态，也不建立第二套任务或产品范围。完整要求及消费者以 AGENTS.md 和 Source Owner Index 的原成果卡为准。

| 原源码职责 | 能力与验收边界 |
| --- | --- |
| C1 / W1 | 任务针对性取数、明确选择的监测、受控浏览器上下文；中国境内经营主体/品牌关系、原生字段与时间、Source/Evidence/Canonical、持久游标、刷新、失败续接及真实采集结果。注册或可导入不等于采集完成。 |
| C2 / W2 | 唯一 Gateway、Agent、Skills、长期上下文、授权 BM25/向量召回/融合/重排、评价与受控学习。GPU 训练路线已撤回；现有获准推理及可选 CPU 专项学习按 Architecture §6/J27 独立准入与验收。 |
| C3 / W3 | CTH 经营及 BMP 品牌市场的专业分析、决策、动作和效果；内部制作、外部执行、人工行动、预算/实支/退款各自保真，来源变化及保存/修订/恢复连续。 |
| C4 / W4 | Brief 驱动的原创提案与内容、视频及播客后期；精确时间线、多轨、编辑、专业输出、工程交换、取消、重开及恢复。不恢复独立图片编辑器。 |
| C5 / W5 | 资料导入、研究分析、引用、文档对象、报告与导出服务当前任务；SavedWork、版本、通知及来源撤回连续。不是强制独立研究/文稿产品。 |
| C6 / W6 | 共享接口集成、运行身份、DB 一致性备份/恢复、依赖、安装/更新/回滚及同版交付；不得以健康接口或 CI 代替业务可用性。 |
| F | 全新像素赛博＋植物生态＋复古未来主义，满天星 Logo 与五植物角色；任务布局、三语、完整可选动效、键盘/IME/读屏与窄屏；官网为展示与真实入口，不能含产品试用沙盒。被否定的呈现不再作为实现基线。 |
| M | 原职责内的差异审阅、跨 Owner 集成与实际验收；不以源码、测试数、文档或工程角色数量代替产品完成。 |

本次源码清退没有把任何一行能力签成完成。全部有效原 G/R/J/U、requirements/coverage、213 项交互及 PE 专业要求继续由原规划和合同维护，不在 CURRENT 复制另一份清单。Web/Windows 优先、官网按原范围交付，macOS/iOS 客户端及设备验收按当前 PO 条件；共同能力不因设备后置而删除。

## 4. Source, runtime and acceptance / 版本核验

当前源码以实际 Git 读回为准：`git rev-parse HEAD`、fresh `git rev-parse origin/main`、独立 GitHub main、`git status` 和 `git rev-list --left-right --count HEAD...origin/main` 分别核对。不要把本文件内任何历史 SHA 当当前版本，也不要把磁盘源码 hash 当进程已加载证明。

源码清退的准确基线、被移除文件 blob 与本地未发布文件区别记录在原 [workspace continuity](evidence/round-15/workspace-continuity-20261024.json)。既有研究及功能缺口继续沿 [Source Adoption](LUMENIS-SOURCE-ADOPTION-V1.json)、[专业增强规格](evidence/round-15/professional-enhancement-20261024.md)、原 Owner 卡及 Issue #17 追溯。既有失败记录仍是失败，旧构建和旧操作证据不能签收当前组合。

发布完成要求按原 Real Delivery/Release Gates 执行：同版受管理源码、必需检查、实际加载身份与数据库、专业用户工作、保存/修订/重开/恢复、正确导出、安装与更新恢复。源码清退状态只允许本次获批的工程合并，产品发布保持阻塞。
