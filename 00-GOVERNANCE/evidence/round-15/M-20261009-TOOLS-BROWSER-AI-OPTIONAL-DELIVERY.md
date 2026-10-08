# 序境 / LUMENIS｜2026-10-09 有界源码与准入交付

本记录是现有 Owner/主线的证据，不是第二套规则、蓝图或完成证明。
执行基线为 `274f2742c17550ef421d845c82c066166e2e9826`；本轮开始时本地、fresh origin/main、live main 一致。发布后的精确版本须以 Git 读取，本文件不预填未来 SHA 或 CI 成功。

## 1. 最新授权与五份 V2 材料

最新直接 PO 已暂停 C1，F/C2-C6 仍暂停；M 收尾已获准的工具、Browser/AgentZero、CURRENT 与 A0/B0/C0 准备。未恢复其他窗口，没有新费用、模型切换、外部模型 API、训练、部署或生产数据写入授权。

V2 ZIP SHA-256：`c466e4af2557eeca92d72cf224b0357c39ea0c4af5bd7a14a817bac6e7d36f5c`。完整读取五份文件：统一无 AI 契约 65 行、A 外部模型方案 63 行、B 开放数据方案 68 行、C 自研模型方案 67 行、README 10 行。原包保留，材料不成为仓库指令权威。A0/B0/C0 是来源、许可、权限、依赖和准入准备，不是 C1/C2 窗口编号，也不是 Agent Zero 激活。

| 已采用要求 | 唯一落点 | 结论 |
|---|---|---|
| 七域基础业务无 AI 正常运行 | Product Architecture / Real Delivery；AGENTS 路由，Experience/README 镜像 | OBSERVED：规则已写入；各域实际无 AI 闭环未由此证明 |
| 无 AI 成果优先，AI 增强收益独立，训练第三顺位 | 同一既有 R/J/U 与分层 Gate | OBSERVED：保留完整范围，没有新增验收体系 |
| C2 继续暂停，A0/B0/C0 不自动授予 API/训练/部署 | 现有 PO Receipt / CURRENT / live dispatch | OBSERVED：不启动、不绑定、不导入 |
| 外部模型和数据清单 | 现有来源/rights/Learning 准入 | NOT VERIFIED：附件中的具体版本、许可、免费额度不冒称本轮已逐源重验 |

## 2. 已修复的治理和 Gateway 源码问题

`PRODUCT-POSITIONING-CURRENT.md` 已校准：官网/Web 先行；后续原生 Windows/macOS 与 iOS；Android/Linux 原生客户端移出活跃目标，保留源码/历史；Linux 服务器、CI、跨 OS 和窄屏 Web 不移除。独立设计稿/Figma/DESIGN_READY 不再是编码前提，真实设计与操作质量仍须验收。

Gateway `core.py` 清除退役 Provider 的可执行发现、网络传输、云选择和 fallback，兼容符号/签名及 Git 历史保留。七个 owned binding/execution/status 函数 AST 与修改前一致；没有启动模型或调用 Provider。源码静态证据不代表 Core 已热加载。

已定位但**未修复**的 C2 问题：`ai_task_engine.py` 的 `_execute_analysis` 宣称 rule-based/AI optional，实际上没有完成确定性分析，`_owned_ai_failure_code` 在 AI 缺失时仍转入失败。`_execute_ai_assist` 也有类似文案/状态差异，但它是否属于 AI 专属动作须按真实用户入口判断。普通 data_query 未因可选摘要缺失直接失败。结论：源码不一致 OBSERVED；真实用户影响 NOT VERIFIED；本轮准入不授权修复暂停 C2 的既有业务分支。该缺口已写入原 Owner index，基础任务要求未降低。

## 3. Browser / SYS-06 本轮实际源码

| 路径/已有 Owner | 本轮改变 | 当前状态 |
|---|---|---|
| `ai_browser_runtime.py` / SYSTEM Browser | 短时人工独占租约；frame/target/revision/viewport 和实际图像核验；Agent 与人工动作隔离 | IMPLEMENTED，语法/源码审查；运行未加载 |
| `ai_browser_api.py` / 同一 Browser API | acquire/release/human navigate/action；仅公布 navigate/back/forward/reload/scroll | IMPLEMENTED；旧 Permission/actor/session 边界保留 |
| 现有 SYS-06 client/repository/screen | 服务端能力驱动控件、逐帧绑定、读回、停止/返回分别处理，失败保留真实恢复条件 | 三文件定向 Dart analyze 无问题；用户操作 NOT VERIFIED |
| `browser_use_adapter.py` / 同一 Browser Runtime | 可选关闭状态和真实准入诊断，不实例化第二套 Browser/Provider | 非 working agent；智能执行 UNAVAILABLE |

独立源码审查发现新增异常类误接了 `SessionStatus.CLOSED`，会使关闭/复用抛错并漏清理；已把枚举成员恢复到原 enum，不删除历史证据。未运行单元/集成套件。

本轮仍缺：服务端 Task/Run resolver、typed Source-use/撤权绑定、Owned BaseChatModel 和 Action Firewall 桥、DNS/private-IP/redirect/WebSocket 一体化出口、结果 SavedWork/Artifact 保存重开/恢复、合法远程 Web actor/session transport、点击/输入/选择及完整电脑操作。客户端传来的 task/run ID 保持 UNVERIFIED，不冒充 Evidence。loopback guard 保留；不能为使 Web 看似可用而移除身份边界。

这些缺口不能统称“等 GPU”；其中多项是尚未完成的源码连接。基础人工/确定性 Browser 不依赖 Browser Use 推理准入，批准的完整交互范围保留。

## 4. Agent Zero 本轮实际源码与硬阻塞

现有 Task Engine 增加显式、默认禁用的 GUI executor 分支；`agent_runtime/agent_zero_gui_executor.py` 使用注入的既有 Permission/Gateway/Scope/Artifact 合同、固定镜像、一次性 attempt claim、歧义结果不重放和历史保留取消。没有第二队列、数据库或 Agent Runtime。

独立源码审查指出取消持锁、取消能力字段和 worker completed 被通用验证器过早认可的问题；新增分支已修复：逐任务 RLock/CAS 不跨 worker I/O 持锁，请求总期限 5 秒；统一 `cancel_preserves_history` 并要求按 idempotency key 取消。结果通过既有 `TrajectoryEvaluator` 的绑定 Outcome contract 验证；缺验收器先拒绝准入，目标未验证不写成功。异步提交仍需现有 Owner 的真实 reconciliation/恢复绑定，当前未部署，不能宣称即时取消或完整恢复已实证。

资源 OBSERVED：工作站约 15.3 GiB 总 RAM，本轮采样约 1.34 GiB 可用；无可用 Docker CLI/Engine，Ubuntu WSL2 停止。MIT Agent Zero v2.13 amd64 镜像记录固定 digest `sha256:1ab9d73c448ba44d1a569803be8ae586b092fa3dedb7422061b61e9cdf877e88`，仅登记，未下载/运行。没有重启、提权、停止未知进程、公开端口或挂载私人目录。

运行绑定与真实隔离 worker 协议尚不存在，executor 不配置、不启动。`RESOURCE_BLOCKED`、`BINDINGS_NOT_CONFIGURED` 与 Owned inference UNAVAILABLE 是不同问题。无模型不应阻断正常人工文件/电脑任务；当前 GUI 基础执行器本身仍未完成，不能借 AI 不可用掩盖。

## 5. 免费研发工具交付 A–I

### A/B. 版本、安装和复用

| 资源 | 实际版本/动作 | 边界 |
|---|---|---|
| VS Code | 1.141.0；本轮期间由外部更新，M 未主动升级 App | 扩展持久目录与 App 安装目录分离 |
| Python/Pylance/Ruff | 2026.8.0 / 2026.4.1 / 2026.84.0；Ruff binary 0.16.9 | 官方语言服务；Pylance 免费 VS Code 使用许可，不是开源模型 |
| Dart/Flutter extensions | 3.144.0 | 官方 Dart Code；复用既有 SDK，不换生产版本 |
| PowerShell/Astro extensions | 2025.4.0 / 2.16.20 | 官方 Marketplace，许可证和包版本已核 |
| PowerShell / PSScriptAnalyzer | 7.6.5 / 1.24.0 | 复用本地工具，无新调度框架 |
| Python / Node / Codex CLI / Dart | 全局 3.14.7、项目 3.13.15 / 24.20.0 / 0.161.0 / 3.13.4 | 现有安装，不修改默认模型/账号/网络 |

未安装 Ollama、Tabby、LM Studio 或模型权重；没有 Copilot 付费、第二补全 Agent、GPU 或账户。自动 format/fix-on-save、测试发现、重型自动任务、AI 补全触发保持禁用。实际发行版本、来源、LICENSE 和本机配置 preimage 保存在私有工具回执中。

### C. 编辑器补全

已配置 Python、Dart/Flutter、PowerShell、Astro/TS/JS 的本地语言服务。实际编辑器 UI 验收 **NOT VERIFIED**：用户已恢复窗口，但 UI bridge 仍返回不能取得窗口 process ID，无法观察补全列表或诊断。没有重新要求用户操作、绕过 trust 或重启/丢失其窗口。扩展已安装不等于验收 A 通过。

### D/E. 可调用任务与执行分工

VS Code 原生 Tasks 或 `pwsh -NoProfile -File scripts/local_development.ps1` 调用 snapshot、check、diff、format-preview、获准 format-apply/rollback、locale-preview、build website/flutter-web。用法在 `.codex/README.md`；没有自动模型/测试/Git/产品服务调用。

VS Code 负责本地补全、导航、诊断；PowerShell/Python 负责确定性有界检查、生成预览、构建和回执；当前 Codex Owner 负责业务/权限/语义与实际产品验收；M/W6 负责既有集成。选择 Owner 不是授予写权限。

### F. 实际执行、幂等、恢复与效率

下列均为真实本地工具任务，不是产品 E2E：

| 实际动作 | 回执 | 结果 |
|---|---|---|
| 六工具文件静态检查 | `20261008T211317.080507Z-check-ad2cdb42.json` | exit 0 |
| Astro 官网构建 | `20261008T193738.532535Z-build-dd2bb60e.json` | 实际编译成功，约 121.444 秒；不证明官网内容/交互完成 |
| 同输入重复构建 | `20261008T195634.324338Z-build-2f8ba1d8.json` | exact-input/output cache；约 5.498 秒，没有再次调用构建命令 |
| 现有 locale generator 重复预览 | `20261008T195654.935984Z-locale-preview-ecf381e6.json` | 相同输出，没有覆盖产品文件 |
| 格式写入后的实际回滚 | `20261008T194946.284797Z-rollback-f7e4449c.json` | 恢复 exact preimage |
| 再次格式预览 | `20261008T195914.821068Z-format-preview-9439c159.json` | changed=false，不制造源码差异 |
| 越权 C1 文件写入拒绝 | `20261008T202519.921904Z-format-apply-4c4958d9.json` | exit 2：路径不在当前 M 预约，文件前后 hash 相同 |

工具自身 model_calls=0；没有可信旧 Token 基线，不声称总体额度节省百分比。失败回执保留，实际恢复另记成功，不改写旧失败。

发布前源码审查另发现混合“已改变/未改变”格式批次的异常恢复索引不一致，恢复函数现在按索引筛选实际备份的 changed paths，保留 exact postimage/CAS 拒绝。该修复的源码检查与此前真实单文件回滚回执分别记录，不能把前一回执冒称已验证新的混合失败恢复操作。

### G/H. 安全与回滚

自动写入必须有当前 HEAD、原文件 hash、精确 Owner RESERVED 路径及原预约 hash。私有 intent/backup 先落地，之后仅写允许文件；rollback 只还原 exact postimage。发现 source/HEAD/预约变化立即拒绝，不能扩大 manifest。这个进程锁不锁定外部编辑器；不能证明无其他 writer 时不得自动写。

工具配置可在无后续用户改动时按私有 preimage 回滚或禁用原生 Tasks；仅移除本轮扩展，不恢复整个旧 Profile。格式 grant 随预约或 HEAD 变化失效，必须重新核准，不自动迁移授权。

没有批量暂存/覆盖、reset、clean、强推、秘密/生产 DB 发布。原 C1、M icon、F 源码、研究和历史测试保留；本轮只有精确工具/Browser/Gateway/现行规则进入索引。完整运行树仍有其他未验收 dirty，不能称整仓 clean 或所有候选已集成。

### I. 未闭项目

实际编辑器补全验收、Browser/SYS-06 运行用户操作及保存重开、Browser Use 智能桥、Agent Zero GUI 资源/协议/Outcome、C2 AI-optional 正常分析修复均未闭。本轮不依次恢复暂停窗口、不申请付费或以 HTTP 200/安装/CI 代替真实结果。

## 6. 四层独立结论

| 层 | 真实证据与结论 |
|---|---|
| SOURCE | 本轮规则与有界改动存在，适用语法/静态/源码安全和机器治理检查；正式发布以 exact Git/CI 读取为准 |
| RUNTIME | 本轮 read-only health 为 5.9.9、DB dependency ok；原 PID/boot 保持，未重启加载新改动；Owned NOT_BOUND，无新 GUI/Browser Use 服务 |
| DATABASE | 本轮没有执行 Production DB 写入/迁移；不能据此声称其他 Owner 的历史数据验收或全库逐字未变 |
| USER OUTCOME | 工具的实际预览/构建/回滚/拒绝可复核；编辑器补全和产品 Browser/GUI 完整用户闭环 NOT VERIFIED；不标 JOB_CLOSED/RELEASED/OPERATING |

最终采用 OBSERVED / INFERRED / NOT VERIFIED。规则已统一不等于业务已修好；只在真实结果通过既有验收时使用 ACCEPTED。

## 7. 唯一路由发布补齐

前一有界源码提交为 `6793a0695fde5bf638b8ab9ffc2d323ff2d520dc`，最终核对发现根 AGENTS.md 的同轮政策修改尚未进入该提交。本次仅补齐根路由并同步 CURRENT 的规则发布状态；未混入旧 icon/F/C1 本地成果。最新暂停、七域无 AI 要求与 A0/B0/C0 准备边界一致，保留原审批回执与全部未完成要求。精确 HEAD/origin/live 与各 SHA 的 CI 结果由实际发布读回确定；没有重启加载或生产数据操作。

独立只读复核另指出 Owner Index 顶部旧“恢复/Astra、不暂停”调度措辞仍可能误导，已明确替换为当前暂停和保留职责，历史政策来源继续保留；不恢复任何窗口。

## 8. A0 / B0 / C0 官方来源与准入核查增量

取证日期：2026-10-09，北京时间；本轮来源复核基线为 `ec92c0c3f1a8c1284d94c40a79788989f1e1117a`。该 SHA 的 Product/App Gate 已实际 SUCCESS，分别为 runs `37847212517` / `37847212402`；本次资料增量的后续 SHA 仍需其自己的 CI。此前第1节的“本轮未逐源重验”是先前观察，以下新增只读官方来源核查取代相应准备状态，不将原包改写为已获训练/调用授权。

### A0：来源已核，外部路线全部 OFF

| 资源 | 官方观测与必要校准 | 当前裁决 |
|---|---|---|
| OpenAI | ChatGPT 与 API Platform 计费分离；订阅不能当作无限 API 配额。[官方计费](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform) | OFF；不调用/新建 Key |
| Anthropic | Claude 订阅/API 分开；部分订阅有条件 API credits，不能概括为全部免费或无限。[计费说明](https://support.claude.com/en/articles/9876003-i-have-a-paid-claude-subscription-pro-max-team-or-enterprise-plans-why-is-claude-api-usage-billed-separately-from-my-paid-claude-plan)、[credits](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers) | OFF；账号资格、费用和用途未准入 |
| xAI | 使用量计费，数据留存/无训练承诺有适用条件，不能从聊天订阅推导产品 API。[价格](https://docs.x.ai/developers/pricing)、[数据处理](https://docs.x.ai/developers/faq/security) | OFF |
| Groq | 配额按模型/organization；公开表不是本账户额度保证。默认不保留推理内容仍有可靠性/滥用等例外。[限额](https://console.groq.com/docs/rate-limits)、[数据](https://console.groq.com/docs/your-data)、[协议](https://console.groq.com/docs/legal/services-agreement) | OFF；不写死附件中的固定免费额度/转售授权 |
| Gemini | 免费输入/输出可能用于改进且被人工审阅；地区规则及不得开发竞争模型的条款需遵守。[条款](https://ai.google.dev/gemini-api/terms.md)、[地区](https://ai.google.dev/gemini-api/docs/available-regions) | OFF；不外发客户/隐私/凭据，不自动蒸馏 |
| Cloudflare Workers AI | 当前文档有10,000 Neurons/日，但部分模型需付费；不是任意模型永久免费。[计费](https://developers.cloudflare.com/workers-ai/platform/pricing/)、[数据](https://developers.cloudflare.com/workers-ai/platform/data-usage/) | OFF；账号/模型配额未经实际准入 |
| OpenRouter | 免费方案公开50请求/日；被路由的下游 Provider 有独立数据政策。[价格](https://openrouter.ai/pricing/)、[隐私](https://openrouter.ai/privacy) | OFF；不以中间商承诺代替下游 rights |
| Manus API | 创建/管理异步 Agent task，不能作为普通 chat model 的同义替换。[概览](https://open.manus.im/docs/v2/introduction)、[生命周期](https://open.manus.im/docs/v2/task-lifecycle) | OFF；不授予外部 Agent 会话/DB/电脑权限 |
| Meta Muse Spark | 官方 Model API 已 public preview，并列 Muse Spark1.3；Standard 与允许数据训练的 Contributor 不同。附件“API未证实”已过时，不能误标 UNKNOWN，也不能视为账号可用。[API](https://dev.meta.ai/products/meta-model-api)、[模型/分层](https://dev.meta.ai/docs/models) | OFF；账号/地区/零成本及数据准入仍 NOT VERIFIED |

以上仅读公开文档，没有调用推理接口或发送产品数据。A0默认禁用与现有 owned-only 策略保持；A1实际调用、账号/BYOK、外部数据和效果仍需独立批准，不把新的来源目录变成 Provider 或 fallback。

### B0：十项候选卡核对，零数据集导入/训练

| 精确候选/官方来源 | 公开标签及当前未决项 | 用途/裁决 |
|---|---|---|
| [OpenThoughts-Agent-SFT-100K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K) | Apache-2.0；卡称GLM-4.7-AWQ教师和多来源任务。上游/教师输出权、PII、评测重叠未逐条证明 | Agent训练候选；REVIEW_REQUIRED，历史教师名不激活退役Provider |
| [OpenThoughts-Agent-RL-5K](https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-RL-5K/raw/main/README.md) | Apache-2.0；可执行任务的源码/测试上游权利及评测重叠未核 | RL候选；REVIEW_REQUIRED，B2未准 |
| [SWE-smith-trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories/raw/main/README.md) | MIT；Claude3.7轨迹，任务仓库及教师条款另审 | 修复轨迹候选；REVIEW_REQUIRED，不能冒称CTH/BMP领域训练 |
| [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing) | 结构化数据CC0；其他文字/媒体不同，个人实体仍有隐私/用途边界 | 知识事实候选，经现有Source/Entity核验；不是自动SFT准入 |
| [Overture Places](https://docs.overturemaps.org/guides/places/)、[归属](https://docs.overturemaps.org/attribution/) | 按来源CDLA-Permissive-2.0/Apache-2.0/CC0；具体release/来源/归属未选定 | 地点/实体事实候选；REVIEW_REQUIRED，名称匹配不建立商业关系 |
| [Mozilla Common Voice/MDC](https://mozilladatacollective.com/)、[官方目录](https://commonvoice.mozilla.org/en/datasets) | 公开CC0表述；具体语种/版本、MDC下载/分发条款和个人录音用途待核。总控直接terms页面仅返回JS，完整现行条款 NOT VERIFIED | 语音候选；REVIEW_REQUIRED，镜像不作为已准来源 |
| [Tulu-3-SFT-mixture](https://huggingface.co/datasets/allenai/tulu-3-sft-mixture) | ODC-BY集合含非商业子集及另行约束输出，不能整体商用推定 | 完整商业训练HOLD；按子集权利再审 |
| [stack-v3-train](https://huggingface.co/datasets/HuggingFaceCode/stack-v3-train) | ODC-BY；原仓库许可保留，检测/PII过滤不是完全保证 | 代码预训练候选；REVIEW_REQUIRED，本轮不下载 |
| [FineWeb2](https://huggingface.co/datasets/HuggingFaceFW/fineweb-2) | ODC-BY/Common Crawl；网页原权、残留PII和污染未获逐项审查 | 预训练候选；REVIEW_REQUIRED，非零成本闭环必需 |
| [Dolma3.5精确卡：allenai/dolma3.5_pool](https://huggingface.co/datasets/allenai/dolma3.5_pool) | ODC-BY且卡指研究/教育；混合网页/论文/代码/OCR及合成教师权利未全审 | 商业训练HOLD，不扩大为已批准全文语料 |

本轮只读取官方卡/许可元数据；网页自动显示的预览不被导入或作为训练样本。未下载数据集文件或样本包，未选择固定dataset revision/文件hash，未写生产Evidence/Canonical。集合标签不等于全部上游/教师商业训练权；没有任何候选标记 training_eligible=true。B1取样/去重/PII/held-out准备和B2训练仍分别未授权。

现有 `training_review.py` / `training_cases.py` 已要求单独MODEL_TRAIN精确批准、reviewer target、rights/source Evidence和scope一致。当前 rights output 只接受 purpose/rights_disposition 两项，并不替代这些外部候选的逐源/teacher/PII/benchmark审查；不能把本表直接塞入已批准训练记录。C5/C2恢复并获精确准入后沿原Source/Evidence保存版本化元数据及批准映射，不新增表/数据库/网关。

### C0：固定模型与四层事实

| 层 | 本轮可核事实 | 仍未证明 |
|---|---|---|
| SOURCE | `config/ai-owned-foundation.json`仍为gpt-oss-20b，revision `6cee5e81ee83917806bbde320786a8fb61efebee`，APPROVED_FOUNDATION_NOT_TRAINED；manifest SHA256 `8139a5398fcdcd34103dd94d1e0cb54f0196f9a826b234317451ac58d553a666`。只读取固定revision的LICENSE/USAGE_POLICY，11357/200字节及hash均与原pin一致 | 当前权重/adapter/checkpoint物理文件没有由本次许可核查验证；不改模型pin或recipes |
| RUNTIME | 05:38北京只读现有 `/api/ai/status`：owned、NOT_BOUND、UNAVAILABLE/OWNED_RUNTIME_NOT_BOUND，generation_probe=false、fallback=false | 无真实模型生成/训练准入；没有加载/重启/调用Provider |
| DATABASE | `data/monitor.db`以mode=ro/query_only读取聚合：ai_task23（ready6/succeeded17）、shared_artifacts941 | 该路径与运行进程所选DB未独立读回；计数不能证明训练、rights、用户成果或941个有效作品 |
| USER OUTCOME | `_execute_analysis`“AI optional”与实际AI失败门的源码断点已定位，原七域无AI要求完整保留 | C2暂停，普通业务分支未获修复授权；真实无AI分析/保存/重开未通过验收，不能伪造规则结果 |

固定LICENSE hash：`58d1e17ffe5109a7ae296caafcadfdbe6a7d176f0bc4ab01e12a689b0499d8bd`；USAGE_POLICY hash：`d6387ef7985019c45db8d9801e6ac5fd9f98f02b9f1c56f8c5af80c3e8f385d0`。[固定模型](https://huggingface.co/openai/gpt-oss-20b/tree/6cee5e81ee83917806bbde320786a8fb61efebee)、[官方模型说明](https://openai.com/index/introducing-gpt-oss/)。官方16GB内存运行描述不是“本机剩余1GB就能训练/常驻”的证明；本次不下载权重、不调用Ollama/LM Studio、不启动GPU。

TRL/vLLM是未来可复用的训练/服务工具文档，不是本轮安装或启用授权；文档中的默认下载/服务命令未执行。[TRL](https://huggingface.co/docs/trl/index)、[vLLM](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/)。准入准备的完成与 SOURCE/运行/DB/用户成果真实闭环分别记录，当前不能标三方案运行 ACCEPTED。
