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
| 外部模型和数据清单 | 现有来源/rights/Learning 准入 | 官方文档/许可核对已记录在第8节；实际账户额度、数据逐条权利与执行准入仍未证明 |

## 2. 已修复的治理和 Gateway 源码问题

`PRODUCT-POSITIONING-CURRENT.md` 已校准：官网/Web 先行；后续原生 Windows/macOS 与 iOS；Android/Linux 原生客户端移出活跃目标，保留源码/历史；Linux 服务器、CI、跨 OS 和窄屏 Web 不移除。独立设计稿/Figma/DESIGN_READY 不再是编码前提，真实设计与操作质量仍须验收。

Gateway `core.py` 清除退役 Provider 的可执行发现、网络传输、云选择和 fallback，兼容符号/签名及 Git 历史保留。七个 owned binding/execution/status 函数 AST 与修改前一致；没有启动模型或调用 Provider。源码静态证据不代表 Core 已热加载。

已定位但**未修复**的 C2 问题：`ai_task_engine.py` 的 `_execute_analysis` 宣称 rule-based/AI optional，实际上没有完成确定性分析，`_owned_ai_failure_code` 在 AI 缺失时仍转入失败。`_execute_ai_assist` 也有类似文案/状态差异，但它是否属于 AI 专属动作须按真实用户入口判断。普通 data_query 未因可选摘要缺失直接失败。结论：源码不一致 OBSERVED；真实用户影响 NOT VERIFIED；本轮准入不授权修复暂停 C2 的既有业务分支。该缺口已写入原 Owner index，基础任务要求未降低。

## 3. Browser / SYS-06 本轮实际源码

**最新增量状态（2026-10-09 07:52 北京）：** 下表及其后06时记录是前次源码阶段，运行未验收表述由本节末的实际操作结果更新；未完成的完整能力要求不变。

| 路径/已有 Owner | 本轮改变 | 当前状态 |
|---|---|---|
| `ai_browser_runtime.py` / SYSTEM Browser | 短时人工独占租约；frame/target/revision/viewport 和实际图像核验；Agent 与人工动作隔离 | IMPLEMENTED，语法/源码审查；运行未加载 |
| `ai_browser_api.py` / 同一 Browser API | acquire/release/human navigate/action；仅公布 navigate/back/forward/reload/scroll；Evidence读取补齐现有会话owner guard | IMPLEMENTED；AST/Ruff与调用链审查，实际会话运行尚未验证 |
| 现有 SYS-06 client/repository/screen | 服务端能力驱动控件、逐帧绑定、读回、停止/返回分别处理，失败保留真实恢复条件 | 三文件定向 Dart analyze 无问题；用户操作 NOT VERIFIED |
| `browser_use_adapter.py` / 同一 Browser Runtime | 可选关闭状态和真实准入诊断，不实例化第二套 Browser/Provider | 非 working agent；智能执行 UNAVAILABLE |

独立源码审查发现新增异常类误接了 `SessionStatus.CLOSED`，会使关闭/复用抛错并漏清理；已把枚举成员恢复到原 enum，不删除历史证据。未运行单元/集成套件。

本轮仍缺：服务端 Task/Run resolver、typed Source-use/撤权绑定、Owned BaseChatModel 和 Action Firewall 桥、DNS/private-IP/redirect/WebSocket 一体化出口、结果 SavedWork/Artifact 保存重开/恢复、合法远程 Web actor/session transport、点击/输入/选择及完整电脑操作。客户端传来的 task/run ID 保持 UNVERIFIED，不冒充 Evidence。loopback guard 保留；不能为使 Web 看似可用而移除身份边界。

这些缺口不能统称“等 GPU”；其中多项是尚未完成的源码连接。基础人工/确定性 Browser 不依赖 Browser Use 推理准入，批准的完整交互范围保留。

06时增量源码审查发现 `/api/browser/sessions/<session_id>/evidence` 只有模块读取授权，缺少其他会话接口已有的归属检查。现已复用 `_get_session_or_404`，核对 actor、account session、principal，任一不一致返回404后才读取记录；正常归属路径的查询不变。独立审查与AST/Ruff支持该修复，不能据此宣称真实跨会话操作验收通过。现有安全Workspace启动配置不放行Browser接口，普通启动会带起其他服务；当前M Browser预约又明确排除`app.py`。未重启8201、未扩开该配置；完整运行验收需在既有共享预约下补足隔离入口。

### 后续源码修复：观察结果真实性

`/observe` 原先会把页面读取失败、无活动页面和部分请求项失败包装为 `ok:true`。
本次在现有两个 Browser 文件内修正：4 KiB 请求上限、严格布尔/整数参数、正文在浏览器端截断后传输、DOM/无障碍返回上限、字段错误与截断标识、截图格式和大小验证、no-store 及明确 `ai_used:false`。元素计数读取失败保持 null；不读取 DOM 表单值。无障碍树在官方 snapshot 返回后裁剪，仅证明返回大小受限，不声称上游获取内存已受限。

URL 原文只用于内存中的精确验证；公开状态、验证结果、失败说明与对应 Evidence 不保留 URL 查询参数或片段。独立审查发现过“去掉查询参数导致验证失败”风险，已将内部比较与公开序列化分开；页面观察失败不能产生验证 PASS。

两文件 AST 通过；Ruff 全文件仍有既存诊断，原始失败回执保留。按同一工具/规则比较修改前后，API 26→25、Runtime 218→216，新增诊断0；这不是全文件 Ruff PASS。未运行单元、集成或替代模块套件。

### 实际无模型手动浏览与 SavedWork 结果

沿既有 M/W6 预约 revision 25 补足了 `app.py` 的隔离验收入口：必须显式选择原安全 Workspace 配置、新建 OS-temp DB、loopback 非生产端口；只开放既有 Browser 和 Shared SavedWork 端点，端点自身 Permission/会话归属仍生效。可选择 OS-temp 编译产物，不覆盖生产 Web build。额外修复安全配置导入时可能加载代理节点和启动健康探测的问题；本次运行日志显示节点数0，未启动该循环；新防护仅完成源码验证，不冒称已在本次进程加载。

真实 Flutter Web 编译成功。首次读取真实 PNG 暴露客户端过滤 viewport 响应头导致预览失败，已在原 transport allowlist 补齐3个确切字段并实际看到页面。租约到期后旧 session 状态会让接管按钮停留禁用，已修复为服务端状态回读；07:55实际在租约过期后恢复接管按钮，重新取得人工租约，随后正常停止，证据为`lease-recovery-ui.json`。无关旧源码/测试诊断保留。

| 真实产品操作 | 实际结果与范围 |
|---|---|
| 开启受控浏览、人工接管、访问网页 | 现有通用产品 Browser 的新隔离 context/page；真实 `https://www.bing.com/` 页面标题“搜索 - Microsoft 必应”及1280×720画面可见；没有使用个人账户 |
| 权限边界 | `python.org` 不在现有允许域内，实际拒绝；没有扩白名单求成功。目标页初次绘制返回202，刷新后得到真实画面；保留失败记录 |
| 无模型创建笔记 | 明确选择CTH，人工输入标题与正文，沿真实 Shared SavedWork 保存；不是原网页导入或正式业务事实 |
| 保存与修订 | work `WORK-64037a2d29eedc39b547f6a3`；v1 `ART-7908bbef538b40cc`，v2 `ART-8c59aca534f1410d`，随后v3；parent/hash链由服务端生成并返回。自动化fill曾追加而非替换文本，实际Ctrl+A重新编辑为v3，v2未抹除 |
| 停止与重开 | 产品界面显示会话已结束；完整刷新Web应用后，从笔记列表打开v3，正文逐字一致；重开v1内容仍与原版一致 |
| 数据与权限 | 全部写入新的临时验收数据库/Artifact目录；来源状态NOT_IMPORTED/NOT_VERIFIED，Task UNBOUND，模型调用0；未写Production DB |

证据：受保护本地路径 `work/m-governance-20261008/browser-agentzero/observation/` 下的 `saved-work-ui-receipts.json`、`ui-outcome-summary.json`、`notes-reopened.png`、`runtime-launch.json`、构建记录及服务日志。原失败和中间版本保留。前端构建使用固定 `56f2aba8` 加确切M文件；Core验收实际使用受保护当前工作树，包含未发布旧区域，不能称纯main或生产同SHA运行。最后代理安全增量未在该进程加载。Production 8201未重启。

上述有界手动笔记链为 OBSERVED。捕获正文成为Source/Evidence、Task/Run绑定、远端Web认证传输、任意点击/输入/选择、完整电脑操作、Browser Use智能执行仍未闭；不标整个SYS-06/J任务ACCEPTED、JOB_CLOSED或RELEASED。后续必要工程连接不能全部归咎于GPU。

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

最初的窗口获取失败已恢复。真实VS Code窗口中已观察到以下本地语言服务结果，证据为保护路径内`editor-ui-acceptance.json`与`editor-language-recovery.json`，不是安装推断或模块套件：

| 语言 | 实际编辑器观察 | 状态 |
|---|---|---|
| Python | Path成员的absolute/as_uri/exists/glob等补全；未完成表达式显示2个语法错误，修正后撤销语法错误 | OBSERVED |
| Dart/Flutter | Directory成员及类型补全；`app/lib/main.dart`的LumenisApp通过F12跳到实际类构造器 | OBSERVED |
| PowerShell | Get-ChildItem与Path参数补全；PowerShell7.6.5语言状态；缺失右花括号产生1条错误，补齐后撤销 | OBSERVED |
| Astro/TypeScript | 字符串成员补全；将string赋给number时准确报告ts2322，line2/col7；改回string后撤销 | OBSERVED |

发现并修复三项真实本机问题：正在运行的Code指向不存在的扩展目录（用本地junction接回已有持久目录，没有重复下载安装）；PowerShell语言服务未正确选择已安装的7.6.5（仅指定其语言服务路径）；Dart排除项误用不展开的`${workspaceFolder}`，导致扫描历史副本（改为工作区相对路径并仅重启分析服务）。历史诊断洪泛停止，真实app仍能导航；最终仍显示15条旧SYS-06测试源码接口诊断及1条临时Python告警，未删除、执行或隐藏它们。普通代码补全使用本地语言服务，未请求生成式补全。全仓类型正确性、每种语言所有重构动作和额外网络遥测审计不在这些观察的证明范围。

本轮没有重启VS Code主应用、电脑或产品服务，没有绕过信任。一次F8被PowerShell扩展解释成运行选择并向终端提交空行，未执行函数体或非空命令；之后直接使用Problems面板。该操作记录保留，不把它描述为完全没有终端交互。实际产品源码未因编辑器演示而修改。

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

四种语言编辑器补全已有第5C节实证，Browser本地Web手动笔记链已有第3节实证。完整Browser/SYS-06的Source/Task、远程认证及电脑操作，Browser Use智能桥，Agent Zero GUI资源/协议/Outcome，C2 AI-optional正常分析修复仍未闭。本轮不恢复暂停窗口、不申请付费或以HTTP 200/安装/CI代替真实结果。

## 6. 四层独立结论

| 层 | 真实证据与结论 |
|---|---|
| SOURCE | 本轮规则与有界改动存在，适用语法/静态/源码安全和机器治理检查；正式发布以 exact Git/CI 读取为准 |
| RUNTIME | 本轮 read-only health 为 5.9.9、DB dependency ok；原 PID/boot 保持，未重启加载新改动；Owned NOT_BOUND，无新 GUI/Browser Use 服务 |
| DATABASE | 本轮没有执行 Production DB 写入/迁移；不能据此声称其他 Owner 的历史数据验收或全库逐字未变 |
| USER OUTCOME | 工具预览/构建/回滚/拒绝及四语言编辑器补全可复核；隔离本地Web Browser手动笔记保存/修订/停止后重开为OBSERVED；完整Browser/GUI及七域无AI业务闭环仍未验收，不标JOB_CLOSED/RELEASED/OPERATING |

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

## 9. 无 AI 的页面链接操作增量

基线为 `dc16ab2bea21c7a8250a74078aae29368cce0c41`，本机、fresh origin/main、live main 于2026-10-09 08:54北京一致，divergence 0/0。原有79个tracked dirty及2个untracked仍是受保护未发布工作；不是本批全部成果。M只修改既有Browser、SYS-06、两条隔离验收入口与当前状态说明，不恢复任何暂停窗口。

### 实际发现及修复范围

- 从真实Bing首页取得可见链接列表，但首次打开被 `BROWSER_LINK_STALE` 拒绝；立即刷新再列出也出现 `BROWSER_FRAME_STALE`。运行反馈显示动态页面像素与严格整帧hash比较冲突，不能把拒绝路径当正常成果。
- 链接操作采用原会话/人工租约/画面身份及服务器生成的不透明ID。重新解析对应链接的索引、地址、文字、可见性；页面身份与捕获时URL仍须一致。仅此明确链接选择不要求无关动画像素完全相等；原有其他操作保持严格画面核查。
- 公开目标初检不足以阻止重定向到本地/内网。新增的主文档Request阶段检查在该次导航期间逐跳应用原目标策略；不以请求后的检查冒充事前阻止。不执行DOM点击、表单、任意JS或客户端任意selector。子资源、WebSocket及导航完成后的脚本网络隔离不属于本次已实现保证。
- 运行使用fresh临时数据库和实际Flutter Web构建，端口8326；原8201/PID61948未重启，未修改Production DB。Core基于受保护的工作树，而非纯净main，因此运行收据不冒称纯main同SHA验收。

首次失败操作保存在既有私有证据目录的 `link-navigation/ui-initial-attempts.json`；原始运行日志保留为 `initial-runtime-*.log/json`。构建产物main.dart.js SHA256为 `58988eeda7cdc70107306dac4a8840da48c3d921d0924a0799ee56570ee4162a`，首次launch记录中的旧build hash为启动当时的观察，未被改写成最终构建。

静态与运行证据分别记录。未执行单元/集成/Widget或换名模块套件。本次不改变A0/B0/C0的准备边界、C2暂停、Provider禁用或七域无AI优先原则；完整SYS-06及Browser Use/Agent Zero仍有第5I节所列缺口。

### 修后真实操作结果（2026-10-09 09:04–09:15，北京时间）

| 实际操作 | 结果与证据边界 |
|---|---|
| 从Bing首页打开服务器列出的“图片”链接 | 当前画面列出22个链接；选择后显示真实“必应图像”页面，同一session `bs_211bb32d45e8` 的revision从1到2，`ai_used=false`；截图 `01-real-link-destination.png` 与运行请求时间对应 |
| 人工记录当前观察并保存 | v1 `ART-e7c52608c0104408`，sha256 `5120cc61f48a493e45442c72b720b80df098fa2f896a023c3dccbbda20a65af2`；BMP/ALL下普通SavedWork，不是Source/Evidence/Canonical导入 |
| 补充观察保存新版本 | v2 `ART-d96b666569fc4b88`，sha256 `0ade779602a20ae7c2afac951d75a32a3514cfc8ce27311474580771e54d5d00`，parent指向v1；本次实际编辑是追加补充，未把它描述为局部文字替换验收 |
| 结束产品浏览会话、刷新并换全新操作浏览器后重开 | 实际UI读回v2正文与parent/hash，再打开v1确认原文保留；截图 `05-reopened-version-2.png`、`06-old-version-1-preserved.png` 及 `saved-work-reopen-receipts.json`；没有重建已保存结果 |
| 工具异常恢复 | 一次操作工具等待超时导致REPL重置；保留既有产品成果，用已安装Playwright重新建立独立操作浏览器完成读回。Flutter未聚焦的语义输入值为空，聚焦后能读回实际正文；未将该工具读值当成产品数据丢失 |
| 停止与保护 | 受控会话由产品“结束会话”关闭；验收操作浏览器关闭；仅停止已核身份的8326隔离Core及其launcher，原8201/PID61948保持 |

固定修后Runtime源码SHA256：`d1dbe57af89d26588c612c006871b837912224f2a35814b0f1ddb2bd3298cd5f`。最终实际构建119.9秒成功；定向Dart分析无诊断。Python AST通过；Ruff与同文件基线比较，API25→25、Runtime216→216，新增诊断0，历史诊断未删。现有AI宪章、Experience权威/anti-template/44屏规格、机器治理静态门通过，不代表整个产品完成。

结论：这个本地无AI链接导航＋人工笔记连续性增量为 **OBSERVED**。Source/Task仍未绑定，Artifact为既有staged/pending状态，未提升为业务事实、模型训练数据或对外发布成果。恶意重定向、跨账号与全面恢复的真实对抗验收仍 **NOT VERIFIED**；本次前置主文档检查有源码审查，不能冒称完整网络隔离已验收。Production Runtime未加载，完整SYS-06/七域业务均不标JOB_CLOSED。

## 10. 现有连接的执行准入裁决

2026-10-09 09:24–09:26（北京）在 `d847a28e29323c9555bbe9b8ebd04728cc496076` 上定向读取现有连接及依赖；没有再次扫描全仓、运行模块测试或调用模型。该提交的 Product Gate `37869002503`、App Gate `37869002603` 已成功；本节后续发布不继承为 same-SHA PASS。本次只把核实出的具体断点写回既有入口，未新增产品候选或恢复暂停窗口。

| 连接 | 已核实的现有代码 | 当前裁决与继续条件 |
|---|---|---|
| Browser → Task/Run | `ai_browser_runtime.py:AIBrowserRuntime.__init__/_resolve_task_trace` 将客户端 task/run 保持 UNVERIFIED；`ai_browser_api.py:create_session` 没有服务端任务解析。Collector TaskQueue 的 run/lease 只属于实际采集任务 | **OBSERVED：通用 Browser 任务解析路径缺失。** 由既有任务 owner 解析真实 actor/task/run/状态后才能绑定；不能套用 Collector lease 或把客户端声明升级成授权 |
| Browser → Source/use → Gateway | `owned_service.py:OwnedServiceRequest/SourceUseDecision/run_owned_request` 已要求 domain/scope、真实 Evidence refs、来源策略与版本 hash；Browser 会话权限和本地 principal 只是既有浏览访问边界 | **OBSERVED：Browser 的 captured-source/use 决策生产者缺失。** 已存 business Brief 校验器不适用于任意新网页。保留真实 Source/Evidence 及适用使用许可后再调用原 typed Gateway；不得把 URL/正文/状态布尔值当权限 |
| Browser Use → SYSTEM Action | 当前可选 adapter 仅报告 readiness；没有实例化 Browser Use Agent 或 BaseChatModel/action bridge | **NOT VERIFIED：智能浏览未实现。** 上游 Tools 支持自定义动作，但这不能证明所有动作、观察、网络流量都已受现有 Firewall 控制；当前文档没有给出可直接替换的 pinned 安全桥。保留确定性人工 Browser 路径 |
| Agent Zero → Worker | `agent_runtime/agent_zero_gui_executor.py` 请求 `/api/lumenis/v1/capabilities` 及 task execute/cancel；未找到该 Worker 实现、`AgentZeroDependencies(...)` 构造绑定或启动时 `configure_agent_zero_gui_executor(...)` 调用 | **OBSERVED：执行器与 stock API 尚未接通。** 不能把原始 `/api_message`、日志/终止/文件 API 当作已满足任务级范围、幂等、取消和成果合同。后续必须沿既有 owner 实现匹配桥与真实回读；不能只安装镜像后宣布可用 |
| Agent Zero → 人工桌面与成果 | 现有 `_preflight` 要求 owned Gateway；这是 AI 任务执行器。未实现独立人工桌面 session/frame/lease；`_persist_artifacts` 仅 PNG/JPEG/TXT/JSON | **OBSERVED：无AI人工GUI和可编辑文档保存仍缺。** 不移除 AI 任务的模型门来冒充人工路径；需沿 SYSTEM/Artifact 复用现有会话与保存合同，之后实际创建、保存、重开、修改文件验收 |
| 当前宿主资源 | 09:26:32 主机总内存15,707 MiB，可用950 MiB；host PATH未发现Docker；WSL列出Ubuntu/Stopped/v2 | **RESOURCE_BLOCKED：未具备已核验隔离GUI运行环境。** 本轮没有启动WSL探查其内部Engine，也没有证明任意远端Engine不存在；不得为释放资源强停现有服务或越权安装。无容器/可见桌面/人工操作验收 |

Context7本次上游资料指向 Browser Use `main` 的 Tools/Agent说明；它属于接口研究，不冒称0.13.10逐文件兼容或安装验证。仓库现有pin及许可记录保持，本次没有新增依赖、改变Gateway、启用Provider或下载模型。

原Core 8201/PID61948、boot `f176d88a59e8438eb03bd56e38195bf1` 仍健康且未重启；该health只证明进程/DB依赖响应，不证明新源码已加载。81个原有受保护dirty/untracked文件在本轮只读核查与文档修改前冻结hash，交付前再次核对；生产DB未写。

执行结论：A0/B0/C0来源与准入准备已经记录，外部路线保持OFF；无AI手动Browser的第9节成果保留。完整 Browser Use/Agent Zero、C2分析无AI修复、七域正常业务验收仍未完成。C1/F/C2-C6保持暂停；现有任务材料与未完成源码保留，不以新增占位代码、UNAVAILABLE回复或一份研究记录代替实现。

发布纠正：本节首个文档提交 `66070a04` 的 Product Gate `37870192239` 失败，原因是 CURRENT 的 publication state 沿用了上批 `PUBLISHED_SOURCE_VERIFIED`，与该提交仅含文档的事实不符。后续纠正为现有 `RULES_ONLY_PUBLICATION`，重新执行相应静态治理门；不删除/降级检查，不改写失败记录，不补入无关源码凑成源码提交。上一批 `d847a28e` 的行为源码与真实操作证据不受本次文档状态错误影响。
