# OA-ANT-20261018-01｜序境产品工作方式升级研究

版本：1.0；访问与静态核对日期：2026-10-18 UTC。范围：OpenAI / Anthropic 官方工程、产品与开发文档；序境指定候选源码及 V2/V2.1。状态：RESEARCH_ONLY / NOT_IMPLEMENTED / NOT_RUNTIME_VERIFIED。

## 1. 问题与结论

目标不是复制聊天框、公司管理制度或多agent模板，而是减少用户完成经营分析、品牌营销、独立研究、媒体创作及系统维护时的重复说明、等待、返工和失控风险，同时提高可用成果质量。

建议采用“确定性可完成的工作 + 有界AI增强 + 可恢复成果 + 人工决策边界”。沿现有 C1–C6/F 和 canonicalOwner 接线；不新造任务平台、真相库、UI运行时或Owner。用户始终面对同一业务任务、原始证据、可修改成果与下一步操作；AI提案不是Production Truth，保存草稿不是发布，工具回执不是业务成功。

最值得优先验证的四件事：
1. 同一工作可从无AI路径完整完成，AI只增强明确的步骤，失败后不丢已有成果。
2. 任务能跨关闭/重开继续，副作用去重，取消后的晚到结果不能复活任务。
3. 多任务空间把“需要我决定、异常、可用成果”分开，降低用户审阅成本，而不是增加对话数量。
4. 每次声称完成都附同版本来源、可读回成果及实际结果证据，质量、成本与人工时间一起衡量。

## 2. 原始来源、版本与证据等级

完整 URL、发布日期/版本、访问日期见 SOURCES.json。公开页面为访问日快照，不宣称固定SDK发布版本；本研究没有下载、安装或升级SDK。SDK文档可以说明接口设计，不能证明已安装版本支持它。

- A：正式产品/开发文档，可证明文档化能力与限制，不能证明序境接线。
- B：厂商公开工程案例，可证明其自述的特定实践，不能当独立复现实验。
- C：厂商内部调查/研究，须保留样本、场景、测量及自报偏差。
- D：版本化公开协议规范。MCP 是社区协议规范，不冒称ISO认证；其规范要求与厂商建议分开。
- L：本轮本地静态源码证据；文件/测试存在不等运行通过。
- P：本报告产品适配建议与待实验假设，不是外部厂商已验证结论。

OpenAI来源包括2026-02-11 Harness engineering、Agents SDK审批/Session/Tracing、Structured Outputs、Plugins安全及ChatGPT Projects。Anthropic来源包括2024-12-19基础编排、2025-06-13多agent研究、2025-09-29上下文工程、2025-11-26长任务harness、2026-01-09评估、2026-04-08 Managed Agents、Projects/Artifacts，以及2025-12-02和2026-10-16内部工作研究。2024文章已明确提示工具格局变化，本研究同时核了2026工程演进，未停在旧模板。

## 3. 方法与真实源码基线

先读指定 source/VERSION（5.9.9）、依赖声明、Source Owner Index、V2 MASTER_REGISTER、V2.1 CORRECTION；再核执行/记忆/权限/成果具体源码和测试定义；然后访问官方文档，比对可借鉴机制及不适用前提。未运行产品、测试、模型调用、采集、迁移或远端写入。源码清单及SHA-256见 LOCAL_EVIDENCE.json；它只固定本轮读到的文件，不把候选版本名当整体Git提交。

依赖观测：requirements-browser-use.txt声明 openai==2.26.0、anthropic==0.76.0；主requirements.txt中openai是注释的可选依赖。不能据此断言任何运行环境安装了它们。当前Gateway core.py明确仅有获准 owned runtime 路由，旧provider选择及_chat不可重新激活。因此这里借鉴机制，不建议接入外部模型、绕开唯一Gateway或设默认云回退。

本轮确认已有基础：
- ai_task_engine.py:92–103 已有 pending/parsing/awaiting_approval/ready/running/succeeded/failed/cancelled/dlq/unknown；unknown要求停止、证据与人工处理。
- agent_runtime/state_machine.py 已有实例级合法状态转换、终态不可重入；不能再用另一套状态名替换Task truth。
- agent_runtime/durable_adapter.py:5 起明确复用TaskEngine；207–231校验checkpoint格式和身份；300起写checkpoint，386起整任务终态提交；存在脱敏导致不可恢复的明确原因。
- agent_runtime/loop.py:79–94有20步、300秒、2.0成本上限、3重试、2重规划、60秒单步配置。194–196明确同步工具没有硬单步中断，不能把配置当执行保证。
- agent_memory/base.py:bind_task/_binding_context基于服务器任务和当前actor重查scope及子结果读权限；不能以session ID充当授权。
- mcp_discovery.py:239–303校验JSON Schema并固定审阅合同hash；发现不授予安装、启用、执行权限。
- shared_artifacts.py:67/85/250起使用canonical存储、注册及hash；不应把模型沙箱临时文件直接当交付库。
- tests/test_agent_runtime_http_binding.py:132已有进程在工具checkpoint后退出、重开不重复副作用的测试定义；本轮没有重跑，不能声称当前候选通过。

这些是“已有源码基础/待同版实际验收”，不是“全部缺失”。未找到本报告建议的端到端注意力指标、统一业务实验及完整四表面证据，故记 NOT_VERIFIED，而非断言仓库绝对没有。

## 4. 编号研究结论与产品适配

### OA-ANT-R01：任务编排应按问题选复杂度
问题：简单筛选、导入、保存也依赖AI，或每个请求默认多人agent，增加等待和费用。
来源：S01（Anthropic工程建议）、S02（其研究产品案例）。工作流是代码预设路径，agent是动态规划；简单方案先行。S02所述90.2%改善来自其内部研究评估，约15倍聊天token并非通用性价比结论。
反例：模型临时猜调用链去保存报表，或让多个agent重复下载同一资料再互相总结。代码能校验的时间/币种/求和不能交给多数投票。
适配：C2借现有router/loop区分规则执行、单次增强、可并行研究；C3/C5提供输入与产物合同。F用自然业务问题入口，后台显示真实步骤与需要用户决定的点，不要求用户选模型或论文。
验证：同一CTH月度简报任务分别跑确定性基线、单增强、有限并行；固定数据、权限、时限、质量门槛；记录总耗时、人工编辑分钟、错误数、重复检索量及成本。只有收益超过新增审阅成本才扩复杂度。当前为待实验，不能据厂商结果承诺节省比例。

### OA-ANT-R02：结构化工具合同与AI UI是同一个可信边界
问题：看似精美的生成UI可调用不存在动作、产生超权操作或丢用户编辑。
来源：S09 Structured Outputs说明结构约束及拒绝/不完整分支；S10要求最小权限和服务器防御。结构合法不等语义真实、权限足够或副作用获准。
适配：沿V2.1的Core/ViewModel、现有原生组件/Action合同，模型只提出允许类型的呈现计划；严格校验schemaVersion、task/run/attempt、sourceRefs、allowedActionId和结果版本。现有Owner再次解析事实、权限和动作；拒绝执行模型HTML/JS、SQL或任意端点。未知字段/来源/动作拒绝并退回现有确定性视图。
验证：恶意工具描述、额外字段、过期来源、伪权限、乱序patch、旧attempt等负例；不改变dirty输入、播放头或选区。用户价值是减少错误操作和整页重做；指标为被覆盖用户编辑数=0、未注册动作执行数=0、局部修订耗时。

### OA-ANT-R03：持久任务、执行器、上下文必须解耦
问题：关闭窗口、工具进程退出或上下文压缩后，任务重跑、结果遗失或被误判完成。
来源：S03上下文工程、S04长任务实验、S05 Managed Agents工程案例。后者将持久session、harness、sandbox分开；这是架构借鉴，不是要求采购服务。其TTFT改善是其自身迁移测量，不能承诺序境同样比例。
适配：保留TaskEngine事实、DurableAdapter checkpoint、Artifact结果。压缩摘要只作索引，原始授权/来源/结果事件需能按权限回读；执行器替换不换task identity。恢复先检查权利、输入/工具版本及执行回执，再继续尚未完成步骤。不要因为日志写了done就设成功。
反例：已发出外部写入但网络断开时一律重试，可能重复发布；若没有可核对回执应UNKNOWN并停下，而非猜成功或失败。
验证：分别在执行前、请求发送后、远端确认前、checkpoint后、成果登记前杀进程；不重复副作用、部分成果可读、无法判定不继续。源码已有有限测试，跨业务/四表面/真实运行还需证明。

### OA-ANT-R04：审批是绑定具体动作的持久状态
问题：等待期间目标或参数变化、成员被撤权，旧批准却执行新动作。
来源：S06 OpenAI Agents SDK支持中断、持久化RunState、批准/拒绝后继续，并提醒存储版本标记避免定义变化导致恢复不兼容。
适配：仍由现有Permission/Action Firewall/Effect Fence裁决；批准绑定actor、scope、operation、resource、paramsHash、inputVersion、toolContractHash、expiry和task attempt。任何实质改变按原政策重新批准。审批存服务端，客户端只提交决策引用；不自动采用SDK的always_approve策略。执行前重新核撤权。
验证：审批后改金额/接收方/来源版本、重复点击、越账号批准、升级工具、超时后重放，均不可产生未批准副作用。指标为授权边界错误=0、用户重复批准次数和等待时长；便利来自减少无意义重复，不能来自扩大授权。

### OA-ANT-R05：多任务工作空间与精确上下文
问题：用户每个对话重复提供材料，或跨项目记忆带来污染/泄漏。
来源：S07是会话历史机制；S11/S12是产品文档中的项目上下文/共享/记忆控制。这些产品语义不等安全隔离证明，也不能复制其默认到序境。
适配：workspace→现有project/subject/task引用，而不是把所有聊天合成一个全局记忆。页面展示当前范围、使用的资料、记忆是否参与及来源版本；任务切换不丢未保存编辑。共享或复制项目默认只带配置，资料/历史必须按已授权选择。引用轻量ID，按任务检索原文；重新读取时核当前scope与撤权。独立Shared任务仍可空白开始，不强制先建经营项目。
验证：两个成员、两个项目、同名品牌、已撤来源、从A移至B的任务、权限变化后的历史摘要/导出缓存。指标为范围污染=0、重新解释次数、检索点击和恢复上下文时间。既有memory/base已重查授权；前后端全链实际证据未验。

### OA-ANT-R06：成果应可重开、修订、对比与交接
问题：结果只留在聊天里，或一个链接指向即将消失的沙箱文件。
来源：S13 Artifacts提供并排可编辑、返回及分享的产品思路；不意味着序境应自动公开分享或运行任意生成工具。
适配：C4/C5沿现有Artifact/SavedWork保存可编辑源、可交付版、父版本、来源和权限；F保持聊天和工作面关联，局部修改显示diff，再由原Owner产生新revision。失败时保留上个良好版本和可恢复草稿；分享/外发依原权限，打开成果不默认改变共享。
验证：研究报告、BMP提案、播客脚本各做创建→编辑→保存→导出→关闭→冷开→改引用→再导出；来源撤回时显示影响范围。指标为重开成功率、版本冲突丢失=0、导出与编辑源一致率、交接准备分钟。

### OA-ANT-R07：效果评估必须看环境结果和人工代价
问题：模型说完成或mock返回成功就算工作完成。
来源：S14将task、trial、grader、trajectory、outcome分开；最终环境状态与模型叙述不同。S08工程案例强调机械边界和真实结果验证，但其内部低阻塞合并策略并不适用于当前序境安全门。
适配：C5 Shared Evaluation复用现有独立评价Owner，C6核运行、C3核业务成果，F核真实操作；训练集/开发集/保留任务分开。客观计算/权限/引用用确定性裁判；创意质量用盲评和人工校准，可加模型评分但不作为唯一裁决者。差评/超时/未达标保留，不删难例。
验证：SOURCE→RUNTIME→DB→TEST→USER OUTCOME逐层记录同一hash。报告可靠完成率、错误类型、人工返工与成本，重复trial，不只报最优pass。样本太小、合成业务或无对照时标限制，不宣称因果收益。

### OA-ANT-R08：可观测性不能成为隐私外发通道
问题：调试最方便的全量trace把客户原文、密钥、跨项目数据送出。
来源：S15 SDK tracing默认启用且可能包含模型/工具输入输出；S05公开工程将凭据隔离于执行沙箱；S16 MCP规范约束token audience及禁止透传。
适配：C6沿现有日志记录task/run/attempt/step与耗时、错误码、合同hash、权限决策引用，敏感内容不进入遥测；关联事实走权限化引用而非拷贝。外部trace出口默认关闭，启用需另行授权。凭据由现有服务端安全边界管理，模型及生成代码不能读其值。
验证：在伪错误、工具结果、嵌套字段、URL放测试哨兵；日志/导出/恢复包无泄漏；撤权后旧trace链接不可读。指标为故障定位时间与敏感外发=0。不得因需要可观测性就打开外部服务。

### OA-ANT-R09：生态协议是可交换合同，不是自动信任
问题：发现MCP/Skill后就安装运行，或工具schema升级导致已审动作换义。
来源：S16固定2025-11-25版MCP授权规范、S10插件安全指南。它们说明互操作与防御要求，不授予任何具体来源、安装或数据传输权限。
适配：复用mcp_discovery、Skill Registry和Permission，发现→合同审阅→权限→隔离自测→启用→更新差异/回滚。schemaHash与endpoint版本固定；只读也需要正确任务范围。403不能自动申请更广scope或换账号。SSRF、DNS重绑定及外部$ref拒绝应沿现有防线验证。
验证：schema变更、端点换域、错误audience token、注入工具描述、取消后迟到回包、停用后老session调用。用户价值为安全复用生态和少做重复接线；指标为审阅后合同漂移执行=0、连接恢复成功率与人工配置时间。

### OA-ANT-R10：预算应同时包含模型、工具和人的时间
问题：每个子任务没超限，但父任务累计失控；取消只改标签，工具继续运行。
来源：S01/S02强调成本和复杂度取舍；本地loop是明确反例：已有预算，但同步执行器不提供硬中断。
适配：不提高现有默认预算；所有父子attempt共享总量账本，记录实际消耗与预留，重试/恢复不清零。软取消先停止新步骤；能支持硬终止的工具用原执行边界接入，不能支持的标“停止请求已提交/仍在结束中”，完成实际核对后再显示终态。没有可靠费用读数标unknown，不编造0。
验证：并发子任务同时预留、恢复后余额、卡死工具、晚回调、取消和提交竞态。指标为超预算未授权调用=0、取消后新增副作用=0、P50/P95首个有用结果/最终成果时间、人工等待分钟；具体性能目标需基线后制定。

### OA-ANT-R11：团队协作文化落实为少打扰、可交接、敢报失败
问题：用户变成agent的全职项目经理，大量进度与长文挤占真正决策。
来源：S17内部132名工程/研究人员调查与53次访谈，不是随机对照；S18最新2026-10-16研究指出人类注意力与协调压力。公开证据只能描述厂商报告，内部真实全面流程未知。
适配：现有任务工作台按“需要我的决定 / 异常 / 可审成果 / 运行中”呈现；通知只在阻塞、材料变化、完成时触发，相关请求合并但不混淆授权。审阅包包含一句结论、具体变化、证据、风险与最小决策。后台保留完整可读记录；不向用户倾倒模型思维链。成员责任沿现有Owner与权限，AI不能自动派工给未获授权的人。
验证：三项并发工作中量测每次有效决策所需点击/阅读分钟、通知数、重复询问、交接恢复分钟、遗漏重要阻塞数。与原体验做同任务对照；输出更多不是成功。保留人工讨论和专业判断，不用模型经理替代责任人。

### OA-ANT-R12：前端智能呈现服务整个任务
问题：把智能UI收窄成首页聊天、生成装饰或固定几个卡片。
来源：本地V2.1为首要产品要求；外部Projects/Artifacts仅提供可组合工作面启发。
适配：CTH以来源/事件/比较/决策为工作面；BMP以约束/方案/活动/效果为工作面；Shared以材料/编辑器/版本为工作面；SYSTEM以真实运行、权限、故障恢复为工作面。简单事实用短文，比较用同口径表图，调参用确定性计算，媒体用原生时间轴。AI只建议组件组合和内容，原生组件执行；Website解释价值，Workspace/Desktop/iOS按角色操作，不把官网当工作端。
验证：至少在CTH报告、BMP活动比较、Shared播客/研究、SYSTEM故障处置四条跨表面旅程逐项验证三语、键盘/读屏、触控、减少动态、引用定位、dirty保护和恢复。成果指标为任务完成率与人工操作时间；不以“200种特效/页面数量”替代业务结果。

## 5. 实现任务与默认策略

见 ENGINEERING_TASKS.json，12项均为建议；字段是对既有Owner合同的待核映射，不授权新建表/注册表/接口。先核已有字段的语义，优先复用；不得复制canonical数据。

建议验证顺序：
- P0：结果真实性、权限/旧审批、取消/恢复/去重、外发隔离。未通过不能用漂亮UI掩盖。
- P1：成果编辑重开、精确上下文、多任务审阅、前端类型化呈现。
- P2：在独立保留任务和真实预算下比较编排、模型路由与协作收益。不能先接外部模型再补授权。

## 6. 结论限制与下一步

本轮完成官方来源研究、指定源码静态核对和可执行验收建议；未完成运行验证、完整四端体验、真实用户对照、SDK兼容测试或产品实施。任何论文/公司案例/测试定义都不自动改变V2总账的NOT_VERIFIED。

OpenAI/Anthropic内部组织、工具实现细节、未公开安全运维和全面收益均未知；公开案例不能证明本公司所有团队采用。没有为了填表把公司价值观包装成工程事实。

下一步需要在明确具体修改授权后，由原Owner选择一条完整业务旅程：先固定版本与基线，补真实异常/恢复/引用/人工时间证据，再决定最小增量实现。无需先采购、切换模型或拆重架构。研究资料保留原编号并映射V2的2/4/5/6/12/17/18项，V2.1前端要求完整保留；本编号不替代G/R/J/U或canonicalOwner。

## 附：来源直达链接

- S01 [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)；2024-12-19; 页面已提示工具变化；等级B；访问2026-10-18。
- S02 [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)；2025-06-13；等级B；访问2026-10-18。
- S03 [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)；2025-09-29；等级B；访问2026-10-18。
- S04 [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)；2025-11-26；等级B；访问2026-10-18。
- S05 [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)；2026-04-08；等级B；访问2026-10-18。
- S06 [OpenAI Agents SDK Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)；动态文档;未固定SDK发布tag；等级A；访问2026-10-18。
- S07 [OpenAI Agents SDK Sessions](https://openai.github.io/openai-agents-python/sessions/)；动态文档;未固定SDK发布tag；等级A；访问2026-10-18。
- S08 [Harness engineering: leveraging Codex in an agent-first world](https://openai.com/index/harness-engineering/)；2026-02-11；等级B；访问2026-10-18。
- S09 [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)；动态文档;未固定API版本；等级A；访问2026-10-18。
- S10 [Security & Privacy – Plugins](https://developers.openai.com/plugins/guides/security-privacy)；动态文档;旧Apps SDK URL重定向；等级A；访问2026-10-18。
- S11 [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-projects-in-chatgpt)；页面显示更新28天前;不反推精确发布日期；等级A；访问2026-10-18。
- S12 [How can I create and manage projects?](https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects)；动态帮助文档；等级A；访问2026-10-18。
- S13 [What are artifacts and how do I use them?](https://support.claude.com/en/articles/17153992-what-are-artifacts-and-how-do-i-use-them)；页面显示更新一周以上;具体版本未标；等级A；访问2026-10-18。
- S14 [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)；2026-01-09；等级B；访问2026-10-18。
- S15 [OpenAI Agents SDK Tracing](https://openai.github.io/openai-agents-python/tracing/)；动态文档;未固定SDK发布tag；等级A；访问2026-10-18。
- S16 [MCP Authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)；规范版本2025-11-25；等级D；访问2026-10-18。
- S17 [How AI is transforming work at Anthropic](https://www.anthropic.com/research/how-ai-is-transforming-work-at-anthropic)；2025-12-02;2025-08调查；等级C；访问2026-10-18。
- S18 [How employment is changing at Anthropic](https://www.anthropic.com/research/employment-at-anthropic)；2026-10-16；等级C；访问2026-10-18。
