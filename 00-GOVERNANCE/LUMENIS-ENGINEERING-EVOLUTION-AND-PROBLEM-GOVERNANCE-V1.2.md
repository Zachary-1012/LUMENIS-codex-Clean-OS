# 序境 / LUMENIS｜工程演进与问题治理 V1.2

## Engineering Evolution & Problem Governance
### 非软件工程背景下的 AI-Native 产品研发实践

- 研究周期：2026-08-15 → 2026-09-09
- 当前阶段：Production Convergence
- 文档版本：V1.2
- 文档性质：工程演进记录 / 问题治理方法论 / AI-Native研发案例 / 白皮书基础材料

---

## 01｜项目起点

序境 / LUMENIS 的研发存在一个非常重要的背景：项目发起者在2026年8月15日开始研发时，没有传统软件工程与代码开发经验。

项目不是从“我要学习某一种编程语言”开始，而是从一个真实业务问题开始：如何把分散的平台数据、品牌信息、商业主体、内容、传播、事件与风险，转化为能够真正辅助工作判断的业务能力？

因此最早推动研发的不是技术路线，而是：

`Business Problem → Product Requirement`

随着生成式AI进入研发过程，AI开始承担大量 Research、Architecture Analysis、Code Generation、Refactoring、Debug、Test、Documentation、Repository Audit 与 Automation；人的职责逐渐集中在产品定义、业务规则、能力边界、架构选择、风险判断、优先级、AI行为治理与最终验收。

因此，本项目并不是传统的个人程序员项目，更准确地说，它是一项：

> **AI-Native Software Development Experiment。**

它试图回答一个问题：

> **一个没有传统代码背景的人，能否通过产品判断、AI执行能力和逐步形成的工程治理体系，真正完成Production级软件研发？**

截至2026年9月9日，这个实验仍然处于进行状态。Production Acceptance尚未完成。

---

## 02｜第一阶段：业务驱动的快速原型

项目早期需求来自真实业务：数据采集、主体识别、社交内容监测、舆情发现、趋势分析、报告、内容与营销辅助。

这个阶段最大的优势是：

> **所有功能都来自真实业务需求。**

但由于缺乏传统软件工程经验，早期很容易形成“功能出现 = 功能完成”的认知。

后来实际研发证明：

- 页面存在 ≠ 功能存在
- 代码存在 ≠ 可以Import
- API存在 ≠ 前端正在使用
- 测试存在 ≠ 测试已经执行
- Provider存在 ≠ AI正在ACTIVE
- 仓库存在代码 ≠ Runtime正在运行
- AI说完成 ≠ Production完成

这是整个研发过程第一次重要的工程认知变化。

---

## 03｜AI带来的高速能力扩张

AI大幅降低了实现新能力的时间成本。产品迅速从单一监测工具扩展到 Social Listening、Subject Intelligence、Brand & Market Intelligence、KOS / KOL / KOC、Campaign、Content、Research、Reporting、Event / Case、Evidence、Data Intelligence、AI、Agent、Continuous Learning、Runtime、Browser、Evaluation、Security 与 Governance。

对于传统单人开发而言，这种扩张速度很难在如此短周期完成。

但AI同时产生了新的工程问题：

> **Expansion Speed > Convergence Speed**

即功能增长速度开始超过系统收敛速度。页面、API、数据库表、Agent、Research、测试和设计方案迅速增加，同时谁拥有某个功能、数据到底来自哪里、哪个API是当前版本、新旧实现是否重复、UI是否连接真实Backend、测试是否验证真实链路、当前Runtime到底运行哪份代码，开始变得越来越难判断。

---

## 04｜AI“完成”幻觉

AI辅助研发中最危险的问题之一，不一定是明显报错，更危险的是系统看起来已经完成。

典型情况包括：页面已经出现但数据是假数据；API已经写好但没有真实调用；测试文件已经存在但没有真正执行；AI Provider配置存在但真实请求失败；Agent类存在但执行链没有闭环；Dashboard显示ACTIVE但Runtime没有对应进程；README声称完成但源码已经发生变化；Commit Message声称READY但Runtime没有验证。

因此形成第一条核心治理原则：

> **Implementation Evidence > AI Statement**

以及：

> **File Existence ≠ Capability Existence**

能力必须经过：

`Source → Contract → Runtime → Test → Evidence → Acceptance`

才能真正声明完成。

---

## 05｜Architecture Drift

高速AI研发很快产生第二个核心问题：架构漂移。

不同AI、不同时间、不同Prompt可能读取不同README、历史代码、分支、设计、上下文和旧模板，于是出现已经废弃的架构重新被AI当成当前架构。

典型表现包括旧导航重新出现、旧命名复活、旧页面结构继续开发、新旧API并存、相同功能存在多套实现、新Production Line无法成为唯一体系。

因此逐渐建立：

`Canonical Naming / Canonical Ownership / Feature Registry / Current Product Baseline`

并形成原则：

> **产品必须存在唯一当前事实。**

---

## 06｜能力丢失

架构重构又带来了相反的问题。如果为了清理旧架构直接删除历史代码，很可能同时删除仍然有价值的 Function、Metric、Research、Prompt、Domain Methodology、Language Intelligence、KOS方法、Podcast研究、Evidence Contract、Tests 与 Business Rules。

因此形成一个非常重要的原则：

> **恢复历史能力 ≠ 恢复旧产品。**

正确方式：

`Historical Asset → Source Trace → Current Equivalent Audit → Semantic Dedup → Production Line Mapping → Capability Promotion → Test → Evidence → Regression`

旧代码不再直接恢复成为Runtime，旧资产首先成为 Capability Source。

---

## 07｜Heritage Intelligence

为了避免研发成果随着重构消失，项目进一步建立 LUMENIS Heritage Intelligence Library，用于保存 Research、Platform Intelligence、Language / Content Intelligence、Data / Metric、Domain Methodology、Evidence Contract、Product / UX、AI / Agent、Engineering Governance、Decision Memory、Case / Benchmark、Test / Regression Memory。

其核心原则是：

> **先保住脑子，再决定哪些能力重新进入身体。**

历史资产不是Production Truth，但它是 Knowledge / Evidence / Capability Source。

---

## 08｜Production Truth

随着产品复杂度增加，一个根本问题逐渐暴露：同一个业务事实到底应该有几个答案？

如果UI、API、Report、AI分别计算，最终同一个指标可能产生多个结果。

因此逐渐形成：

`External Data → Evidence → Canonical Data → Function → Metric → Truth Table → View Model → Dynamic Visualization`

UI、AI、Agent、Report都不是Truth Owner，它们只能消费Production Truth。

---

## 09｜Data / Schema / Migration治理

研发过程中逐渐出现字段变化、表结构变化、Migration、INSERT字段不一致、旧表仍被代码引用、测试Schema与Production Schema不同、时间字段语义变化。

由此形成：

> **Schema不是Implementation Detail。**

数据库变化必须进入：

`Schema → Migration → Compatibility → Validation → Rollback → Evidence`

不能继续“运行发现缺什么就临时补什么”。

---

## 10｜Frontend / Backend Drift

研发中出现过页面404、API路径断裂、JavaScript错误、旧Endpoint继续被调用、UI存在但Backend能力改变、Backend存在但UI没有承载。

因此UI验收从“页面能打开”升级为：

`Interaction → API → Backend → Function → Data → Response → Render`

必须真实闭环。

---

## 11｜Runtime Reliability

研发过程中逐渐出现服务异常、多进程、Watchdog重复、Collector状态问题、Browser/CDP问题、Scheduler问题、Worker问题、Last Success不可见、Runtime与代码状态不一致。

因此研发从 Application Development 进入 Runtime Engineering，并加入 Heartbeat、Health、Last Success、Last Failure、Retry、Checkpoint、Resume、Watchdog、Single Instance、Circuit Breaker 与 Runtime Evidence。

核心认知：

> **软件不是代码文件，而是一个持续运行、能够失败、能够恢复并能够解释自己状态的系统。**

---

## 12｜AI Provider真实性

AI Provider存在并不意味着AI正在工作。因此状态被逐渐区分为 CONFIGURED、AVAILABLE、ACTIVE、FALLBACK、DEGRADED、DOWN、NOT_CONFIGURED。

只有经过：

`真实请求 → Response → Runtime Trace → Test → Evidence`

才能声明 ACTIVE。这个原则随后扩展到 Agent、Browser、Collector、Scheduler、Worker与Release。

---

## 13｜Agent执行治理

随着AI从回答问题进入执行动作，风险从AI说错升级为AI执行错。

因此形成：

`Task → Permission → Action Firewall → Effect Fence → Execute → Evidence → Evaluation → Trace`

并明确AI / Agent不能直接拥有Production Truth，高风险动作必须进入Human Approval。

---

## 14｜测试治理

项目历史中已经产生大量测试，但进一步研发证明：

> **Test PASS ≠ Production PASS**

因此测试体系逐渐扩展为：

`Unit → Integration → Contract → Browser → Runtime → Failure Recovery → E2E → Production Acceptance`

甚至pytest能不能完成Collection，本身也是Repository Integrity的一部分。

---

## 15｜Environment Truth Gate

2026年9月9日，Windows开发环境进行了系统性检测、判断、安装、配置、验证、修复、再验证。

最终环境层达到：

**Environment / Toolchain = READY**

包括Windows、Git、Python、venv、Node、PowerShell、VS Code、ripgrep、Codex、PATH、WebSocket、Dependency、Disk与Memory。

Codex Doctor最终达到22 OK / 0 FAIL，仅保留一个涉及Defender策略、未擅自修改的Warning。

因此形成：

> **Environment Truth Gate**

以后任何故障必须先回答：这是Environment问题，还是Repository问题？不能用修改源码掩盖环境错误，也不能用“环境问题”掩盖源码缺陷。

---

## 16｜资源治理

环境审计发现C盘曾仅剩约8GB、可用内存曾严重不足、Ollama模型后台占用大量资源、多个AI与浏览器同时运行。

随后进行了Temp清理、C盘恢复到约65GB、Ollama停止与禁自启、模型保留、Agent并发限制、Cache迁移、D盘工具集中。

因此形成：

> **Resource Budget Discipline**

研发环境治理不仅包括Python / Node / Git，也包括CPU / Memory / Disk / Process / Concurrency。

---

## 17｜Ollama：Dependency Evidence

Ollama治理是一个典型案例。发现其后台运行、模型加载、高内存、高CPU、自动启动，但审计没有直接卸载，而是先确认当前无活跃客户端、Codex主链不依赖Ollama、模型属于空转、模型与配置仍具有未来价值。

因此执行：

`Stop → Disable Autostart → Preserve Model → Preserve Configuration → Preserve Recovery`

形成原则：

> **不要因为资产当前没用就删除，必须先获得Dependency Evidence。**

---

## 18｜Codex执行能力与治理边界

Codex开发机当前拥有较高本机执行能力，这提高了Repository Audit、Code Modification、Test、Runtime、Git与Automation效率。

但形成另一个重要原则：

> **Execution Permission ≠ Product Authority**

Codex即使能够访问整台开发机，也不能因此绕过Production Truth、Repository Rule、Permission、Approval、Evidence、Git Governance与Release Gate。能力越强，治理要求越高。

---

## 19｜Repository Integrity Gate

环境稳定后，LUMENIS-Command暴露了一个真实问题：`lumenis_command.evidence`源码包缺失。

影响包括agents、api、engine、services导入失败，pytest collection exit 4，backend serve无法启动。

由于Environment已经验证READY，因此可以明确：

> **这是Repository Integrity Issue，而不是Environment Failure。**

由此建立Repository Integrity Gate：进入Runtime前必须验证Package存在、Import Graph完整、Dependency完整、CLI可执行、Test Collection正常、Source没有异常丢失、当前main没有Dependency断裂。

---

## 20｜Evidence Package恢复

缺失的Evidence包没有通过“随便写一个文件”解决，而是采用：

`真实生产调用点 + 已存在测试 = 行为契约`

恢复EvidenceStore与SQLiteEvidenceStore，包括Evidence、Task、Approval、Audit、Agent Run、Session、Message、Tool Call等持久化能力。

截至当前恢复阶段：

- 新包Ruff：0问题
- 定向测试：65 PASS
- 原4个Import失败子包恢复
- pytest不再在最初Collection阶段直接崩溃

但Unit全量在约68%处出现稳定挂起；Serve尚未验证；Integration / E2E / Security / Independence尚未全部复跑；尚未Commit；尚未Merge。

因此正确状态仍然是：

> **READY WITH WARNINGS**

而不是RECOVERED COMPLETE。

---

## 21｜`.gitignore`：真正更深层的根因

Evidence恢复过程中进一步发现`.gitignore`存在裸规则`evidence/`，它不仅可能忽略运行产生的Evidence目录，同时也会匹配`src/lumenis_command/evidence/`源码目录。

这意味着：

> **文件存在于电脑 ≠ 文件存在于Git。**

甚至：

> **本地测试通过 ≠ 源码会进入GitHub。**

Evidence包可以在磁盘存在、可以Import、可以通过测试，但仍然因为Ignore Rule不会被Git跟踪。

这提供了当前Evidence包从main消失的一个关键机制性解释。因此问题已经从Missing File升级为：

> **Version Control Governance Failure。**

---

## 22｜Git Ignore Governance

由此形成新的治理原则：

> **Source Existence必须同时验证Working Tree与Version Control Truth。**

新的验证链：

`Disk → Working Tree → Ignore Rule → Git Index → HEAD → Remote → Runtime`

任何Production Source都不能只验证“电脑上有没有这个文件”，还必须验证Git是否真正跟踪它。

因此建立Git Ignore Governance Gate。对于evidence、data、runtime、cache、artifact、build等容易同时存在源码目录和运行产物目录的名称，`.gitignore`必须使用精确路径规则，而不能轻易使用可能误伤源码的宽泛规则。

---

## 23｜Anti Test-Green Illusion

如果为了让pytest变绿而随便补兼容类、修改测试、Skip失败测试、全局增加Timeout、Fake返回、Mock真实Runtime，都可能得到绿色测试，但并没有真正恢复系统。

因此形成：

> **Production Truth, not Test Green Illusion。**

正确顺序：

`Root Cause → Contract → Implementation → Test → Runtime → Evidence`

测试是Evidence的一部分，测试不是目标本身。

---

## 24｜68% Hang：从“失败”进入Failure Attribution

Evidence恢复以后，Unit测试已经可以运行，但全量测试稳定在约68%出现Hang。

由于Environment已经READY，Evidence定向测试已经PASS，因此下一步必须回答：

`哪个File → 哪个Test Case → 哪个Call → 哪个Lock / Thread / Network / Resource / Wait Condition`

导致Hang。

这标志着问题处理方法从Fix Error进一步升级为：

> **Failure Attribution。**

不是“哪里红就改哪里”，而是找到真正导致系统无法继续运行的责任点。

---

## 25｜Release Truth

代码、页面和测试都很多，仍然不能自动产生Release。真正Release至少需要Source SHA、Build、Artifact、Product Profile、Schema、Migration、Runtime Config、Tests、Canary、Rollback与Lineage。

因此：

> **READY不是一句状态文字，它必须可以被机器和Evidence证明。**

---

## 26｜AI-Native研发的结构性风险

回看整个过程，问题并不是AI不会写代码。事实上AI已经能够极快地产生代码。

真正的问题是：

> **AI非常擅长Local Completion，但复杂软件需要Global Correctness。**

即：

`Local Optimization ≠ Global Correctness`

AI越能快速写页面、API、测试、重构、增加功能，整个系统越需要Architecture、Canonical Ownership、Production Truth、Evidence、Governance、Regression与Release Control。

---

## 27｜非软件工程背景的真实代价

没有传统软件工程经验意味着早期较难判断什么是真P0、什么只是UI、什么是Architecture、Runtime、Schema、Dependency、Repository Integrity、Version Control、真正测试与真正Release。

因此早期更容易形成：

`Add Feature → Problem → AI Fix → New Implementation → More Complexity`

但这并不意味着必须先成为传统程序员才能继续，真正需要形成的是：

> **Engineering Judgment。**

---

## 28｜人的角色正在发生变化

最早的问题是“能不能做这个功能？”，后来变成“为什么坏了？”，进一步变成“你说完成了，有什么Evidence？”。

现在开始变成：这是Environment还是Repository？这个文件为什么没有进入Git？它属于当前Production Line吗？旧能力Current Equivalent在哪里？Runtime真的ACTIVE吗？pytest为什么在68%停住？这个状态是代码声明还是Runtime Truth？这个版本可以Rollback吗？

因此人的核心能力逐渐变成：

`Product Judgment + Architecture Judgment + Verification Judgment + Failure Attribution + AI Governance`

---

## 29｜问题 → 治理机制

| 实际问题 | 形成的治理机制 |
|---|---|
| AI声称完成但无法证明 | Evidence / Runtime Verification |
| 页面存在但能力不存在 | Capability Verification |
| 新旧架构混用 | Current Product Baseline |
| 历史能力丢失 | Heritage Intelligence |
| 重复实现 | Canonical Ownership |
| 数据口径漂移 | Production Truth |
| UI/API不一致 | Contract / E2E |
| AI假ACTIVE | ACTIVE Evidence Gate |
| Agent执行风险 | Permission / Action Firewall |
| 环境与源码责任混淆 | Environment Truth Gate |
| Package缺失 | Repository Integrity Gate |
| 本地有文件但GitHub没有 | Git Ignore Governance |
| 为了测试绿而假修复 | Anti Test-Green Illusion |
| 测试Hang无法定位 | Failure Attribution |
| 资源长期失控 | Resource Budget Discipline |
| 未确认依赖就删除组件 | Dependency Evidence |
| Release不可证明 | Release Lineage / Acceptance Gate |

这些机制不是为了制造复杂架构，它们全部来源于真实研发中已经发生的问题。

---

## 30｜研发方法的五次变化

### Phase 1 — Prompt-driven Development

`Requirement → Prompt → AI Code`

核心问题：“能不能做出来？”

### Phase 2 — Feature-driven Development

`Feature → More Feature → Integration`

核心问题：“还缺什么？”

### Phase 3 — Audit-driven Development

`Source → Audit → Test → Runtime`

核心问题：“它到底有没有？”

### Phase 4 — Evidence-driven Engineering

`Claim → Evidence → Verification`

核心问题：“有什么证据证明是真的？”

### Phase 5 — Production Convergence

`Recover → Reconcile → Verify → Converge → Release`

核心问题：“如何把过去高速产生的研发资产收敛成一个唯一、真实、稳定的Production Product？”

---

## 31｜当前研发方法论

序境未来研发不再采用：

`Prompt → Code → Done`

而采用：

`Requirement → Environment Truth Gate → Repository Integrity Gate → Current State Audit → Heritage Retrieval → Research → Evidence → Architecture Decision → Implementation → Git Tracking Verification → Contract Test → Runtime Verification → E2E → Evidence → Regression → Release Gate → Production Acceptance`

AI仍然承担大量执行，但是：

> **AI不再拥有宣布自己完成的权力。完成由Evidence决定。**

---

## 32｜当前阶段

截至2026年9月9日，序境已经不能简单称为Prototype。它已经拥有产品架构、多领域能力、Data Truth、Evidence、AI、Agent、Research、Runtime、Governance、Heritage与Tests。

但仍然不能称为Production Complete，因为还需要完成Capability Recovery、Repository Integrity、Data / Schema Reconciliation、Runtime Verification、E2E、Release Lineage与Production Acceptance。

因此当前最准确状态是：

> **Production Convergence。**

---

## 33｜当前最大风险已经变化

早期最大的风险是：做不出来。

现在最大的风险是：

> **做出来太多，但没有完全收回来。**

因此当前研发原则必须从Build More切换为：

`Recover → Reconcile → Verify → Converge → Release`

---

## 34｜当前Evidence恢复的下一步

当前LUMENIS-Command恢复链应严格保持：

`修复 .gitignore 规则 → 证明Evidence源码进入Git Tracking → 定位Unit 68% Hang → Root Cause修复 → Unit全量 → Integration → Security → Independence → E2E → Serve → Health → Git Diff Audit → Controlled Commit → Independent Verification → Merge Decision`

在这条链完成前，不得声明Evidence Recovery Complete。

---

## 35｜这一实践目前能够证明什么

它不能证明“任何没有代码经验的人都可以在25天做出Production软件”。

但它已经能够支持一个更有价值的判断：

> **生成式AI显著降低了复杂软件实现的门槛，但没有消除软件工程。**

相反，当Implementation越来越便宜，新的稀缺资源开始变成：

`Judgment / Context / Architecture / Governance / Verification / Failure Attribution`

---

## 36｜未来白皮书意义

序境未来真正值得记录的不只是做出了哪些功能，更值得记录的是一个非软件工程背景的人，在AI深度参与软件研发以后，如何经历：

`Creation → Expansion → Failure → Drift → Audit → Governance → Evidence → Convergence`

并逐渐建立自己的AI-Native Engineering体系。

这使序境不仅是一项产品研发，同时正在形成一个真实案例：

> **Non-Engineer × AI × Production Engineering**

---

# 结语

2026年8月15日开始时，最重要的问题是：

> **AI能不能帮我把这个东西做出来？**

到2026年9月9日，问题已经发生根本变化：

> **这个系统如何证明自己是真的？**

从Environment，到Repository；从Git，到Runtime；从Evidence，到Production Truth；从Heritage，到Release；这些治理机制最终都指向同一个问题：

> **当代码越来越容易生成以后，我们如何知道软件是真的？**

序境目前给出的答案正在逐渐清晰：不是相信AI，不是相信页面，不是相信代码数量，不是相信测试文件，不是相信Commit Message，而是建立：

> **Evidence-driven AI Engineering。**

让每一个重要能力都能够被追溯、运行、测试、验证、解释、恢复和证明。

这才是从AI生成软件走向Production Engineering真正的分界线。
