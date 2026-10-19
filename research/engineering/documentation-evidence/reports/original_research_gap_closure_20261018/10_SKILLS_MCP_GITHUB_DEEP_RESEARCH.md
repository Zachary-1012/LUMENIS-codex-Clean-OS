# 原规划补研：Skills／MCP／GitHub完整生命周期

日期：2026-10-18北京时间；研究基线：官方main 4dab98ed6357133da9307de846180ed4f7bba5f5静态副本。本文是研究结论及升级方案，不是补丁、安装、运行或安全验收证明。

## 1. 研究问题和结论

原G185/G186/G187、G83/G109/G115，R04/R07/R14，J7/J8，U19/U22/U25要求的不是“能看见工具清单”，而是来源、许可、审批、隔离、自测、真实任务、升级回滚、停用卸载与效果对账。新前端和新增视频不替代这些原要求。

本次实际推进了原官方协议阅读与当前源码逐机制对照，形成十二项可审核结论、二十个反例/正常任务验收条件。核心决定：复用既有SkillRegistry、ExecutionChain、Permission、Effect Fence及Evidence；补齐其入口和真实安全边界，不引入第二MCP注册表、通用Shell或新代理运行时。能力发现、包身份、运行权限、外部授权、业务成果应保持五种独立事实。

当前代码有MCP真实调用路径，不能沿用旧架构说明“只有发现、没有调用”的绝对描述；同时，存在调用函数不证明当前环境已装好包或正在运行。当前底层的readOnlyHint、shell=False和目录约束均不能单独证明子进程隔离只读。本文不声称已发生泄露或线上攻击。

## 2. 实际研究范围与证据

完整阅读：main的mcp_discovery.py（发现和调用）、mcp_skill_runtime.py、GitHub连接器、GitHub/Skill/MCP架构合同；局部精读account/api.py的发现/调用/激活入口、account/skills.py激活与身份入口、Shared Skill execution.py执行/预留/写回链。下文结论以具体文件边界为准，不把未读全仓推断为全仓缺失。

官方2025-11-25 MCP Lifecycle、Tools、Pagination、Cancellation，Authorization中的resource/audience与逐HTTP请求校验段，安全文档的本地进程、SSRF、代理/凭据边界；Agent Skills格式原文；GitHub App用户授权和REST最佳实践。分页初次误用basic路径返回不可取，沿Tools官方链接改读server/utilities/pagination成功；旧GitHub授权页面未取到，改读官方Generating a user access token成功。没有绕访问限制，没有授权/生成任何凭据。

源码身份、函数范围和hash另见11_CODE_EVIDENCE.json。独立研究目录中的结构脚本只解析文本，不import产品、不启动MCP、不触数据库、不跑攻击或访问私网。

## 3. 十二项发现、采用及反例

### D01 协议协商不能只记录服务器版本

依据：MCP Lifecycle明确初始化需要双方版本/能力相容，并仅使用已协商能力；不支持返回版本时应断开。[S1]

main事实：discover_mcp_stdio和call_mcp_stdio请求2025-11-25，接到initialize后立即发送initialized并继续tools/list，返回的protocolVersion只被写入结果。此函数内未见支持集检查；发现路径还无条件请求resources/prompts，然后把失败转警告。

反例：服务器返回未支持的2099-01-01，仍可能走到DISCOVERED；服务器没声明tools，却被请求tools/list。这里只做静态控制流推导，未运行服务器。

ADAPT：C2在原握手处核支持版本、必要能力、服务身份；不相容返回明确状态并保留既有成果。C6/F显示协议不相容，不能变为“已连接可用”。可选能力未声明跳过，不把缺可选资源当工具任务失败。目标仍是完整互操作，不以拒绝全部服务器冒充完成。

### D02 列表首批和截断不是完整发现

依据：MCP Pagination使用不透明cursor；不能假定页大小，缺nextCursor才表示结束，cursor不得跨会话持久复用。[S2]

main事实：tools/list仅一次；_items截128对象，_bounded还截深度和数组，未在返回结果中表示被截断条数/continuation；第二页工具将不可见。当前“安全上限”有价值，但不等发现覆盖。

反例：获批工具位于第二页，call返回TOOL_NOT_FOUND，不能据此断言服务器无该能力；schema第129个枚举值被截断，不能拿截断schema作为完整审批内容。

ADAPT：在原发现会话内有界翻页，记录partial、停止原因和原schema摘要；budget耗尽可交付部分发现并明确未完整。原始审查schema与展示截断副本分开。注册/批准绑定完整schema digest，名称不单独标识可信能力。

### D03 注解是提示，真正隔离发生在进程和网络边界

依据：MCP Tools明确不可信服务器的annotations不可视为可信事实；安全文档把本地服务器视为本地代码执行风险。[S3][S4]

main事实：call要求人工true、allowlist、mcp:tools/call及readOnlyHint；函数文档称read_only grant必需，实际该函数仅检查mcp:tools/call字符串。注册包正常路线还会从registry提供授予集合，不能把底层单缺检查说成全链任意用户可执行。Popen使用shell=False、过滤环境，但此处未建立OS文件/网络沙箱；子进程可执行能力由宿主决定。account/api.py另有owner限定的直接发现/调用入口，传入的是请求body的command和批准布尔值，需跟正式注册链统一验证，owner鉴权不等包审查。

反例：一个声明readOnlyHint=true的程序在initialize前就可能产生效果；没有Shell字符串并不限制Node/Python程序自身读写。只发tools/list也已启动程序，不能把这一阶段称为无执行风险。

ADAPT：C2+C6复用原隔离运行设施（先核实际可用），审批绑定包内容、launcher、依赖、允许文件/域及权限；不可验证隔离时只保留静态预检，不启动。默认无数据库、个人Profile、凭据和任意外网访问；业务能力通过原类型化API。对已信任且确需运行的包保留获准完整路径，不能永久禁用所有Skill替代目标。

### D04 健康、自测和已核包身份需要证据

main事实：validate_installation核manifest名称/版本及package.json、launcher、dist、node_modules存在。account/skills.py activate_installed_mcp_skill只在调用者提供revision/digest时比较字符串；随后根据上述文件存在检查写trust_level=verified、health_state=healthy、授予固定权限。该函数内没有重新计算整个包/依赖摘要，也没有查独立自测回执。其文档假设此前build/smoke已经完成，需让假设成为可读回证据，不能只以函数docstring确认。

反例：名称/版本相同，launcher内容更新，文件仍存在；此前自测指向旧包，而激活可能继续标healthy。registry_sha256对注册行的保护已存在，但注册行hash不等安装字节hash。

ADAPT：C2在原registry保留source revision、manifest摘要、代码/依赖锁摘要与自测回执的关联；执行前复核被批准的包身份，内容变更回到待审。C6负责隔离/原生宿主证据；F分别显示“文件齐备”“自测通过”“已启用”“任务成功”。不另造信任数据库。

### D05 生命周期兼容不能把SKILL.md变为自动权限

Agent Skills标准要求SKILL.md元数据与正文；license/compatibility及实验性allowed-tools可选。标准版本不要求每个包内置统一发布版本。[S5]

ADAPT：继续支持原skill.json与SKILL.md，缺版本用精确来源revision/digest；“未声明license”必须保持许可未知，“allowed-tools”只能作为待审请求，不能覆盖LUMENIS Permission或恢复通用Shell。使用逐层按需加载元数据、正文、引用；引用的脚本/资产也纳入实际包身份和许可。静态预览、安装、启用、运行、升级和卸载分别产生回执。

拒绝：把标准页面的Bash示例复制成产品授予；把Markdown纯文本视为永远无风险（正文和引用都可携带越权指令）。合法材料仍可只读研究，不因不能运行而删除知识用途。

### D06 输入与输出格式合格不等业务可用

main事实：底层要求arguments是dict，并扫敏感形状字段；未在call_mcp_stdio内按工具inputSchema验证。返回结果依据isError判定，然后键名脱敏和截断。Shared execution已有更严格的_product_result_is_success，拒绝错误/空transport元数据，并支持明确no_records结果，不能重复写成“全链只看ok”。[S3]

反例：工具要求正整数而传负数；返回单位错误却格式正确；秘密放在普通text中不会仅凭键名识别。字段敏感检查可能误拒合法主题“tokenization”，也可能漏普通字符串内敏感数据。

ADAPT：C2在原调用前做完整schema、范围和用途校验，C3/C5分别核领域语义与来源；高风险值由原权限链确认。结果raw/staging/validated分存，用户可查看未准入的有用部分及缺口；限制流量但不截断schema后假作完整。内容脱敏不能宣传为绝对防泄露。

### D07 超时与取消不证明外部效果停止

依据：MCP取消允许接收方因已完成或不可取消忽略，且有竞态；task增强请求另用tasks/cancel。[S6]

main事实：底层finally关闭stdin、terminate/kill直接子进程；未见发notifications/cancelled及process tree/外部服务回执对账。返回TIMEOUT不等外部未执行。取消语义也不能用新版任务机制默认替换当前未协商功能。

ADAPT：C2 Task/attempt沿原checkpoint记录cancel_requested、local_process_stopped、external_effect_unknown、reconciled等独立事实（名称为建议语义，不新建运行时）；C6负责子进程树与预算回收；C5保留已提交成果，F不把停止按钮显示为外部撤销成功。有未知效果时先查同一operation回执再重试。

### D08 读取上限应在分配前生效

main事实：_reader使用stdout.readline()后才检查1MiB；Queue未指定maxsize，发现进程stderr=PIPE但未读。没有换行的大输出、通知洪泛或stderr阻塞可以在消息处理前耗资源。这是静态资源边界缺口，不是本次压测成绩。

ADAPT：C6在已有进程通道实施有界按块读取、队列背压、stderr有界消费或丢弃、总字节/总消息/墙钟预算；C2呈现真实部分发现和资源终止原因。性能记录峰值RSS与退出耗时，不只timeout返回值。

### D09 GitHub“有Token”与“用户已验证连接”分开

官方GitHub App用户令牌访问是用户和App可访问资源的交集；用户可撤销授权。[S7]

main事实：GitHubConnectorConfig.snapshot(token_available=True)直接CONNECTED，status没有GET /user。原架构说明也承认还需健康验证。authorization_url只校验state字符串形状，state的产生/保存/单次核验由宿主实现，不能因为生成URL就显示授权完成。

ADAPT：C6账户/凭据Owner保存非秘密连接审查状态及用户/安装/仓库选择证据；C1读取成功后才将健康事实显示给F。令牌存在可用“凭据已提供、连接待验证”语义，不必为此强制新账号墙。用户确认、callback state、PKCE（按当前官方适用流程）、过期/撤销都须真实证据；本文不启动授权。

### D10 GitHub分页和限流不能误报无数据／失效

官方REST建议按Link继续分页，按Retry-After或rate-limit reset暂停，条件请求节省重复获取。[S8]

main事实：repository_collection只请求per_page=50一次；get_json只返回解码body，丢弃Link/ETag/rate headers；401与403合并为认证/权限失败，429归unavailable。403可能限流，也可能权限不足，不能所有403都诱导重新授权；只看50条不能代表仓库全集。

ADAPT：C1复用统一Collector/Session续接、真实coverage和调度，保留页链接与观察时间；C6连接Owner分类认证、权限、限流、网络。对重定向仍重新核精确允许域/仓库，官方建议follow redirect不取消安全边界。没有引入写API或扩大已选仓库范围。

### D11 远程HTTP MCP仍应单独准入

官方HTTP授权要求resource/audience绑定及每次请求鉴权，不能透传任意下游token。[S9] 当前阅读的实际MCP运行模块是stdio；不能用静态来源分类含mcp_http就宣称HTTP传输已完整实现。

ADAPT：新增HTTP支持若属于下一批获准实施，沿原Owner核版本、Origin、目标/重定向/DNS/私网策略、逐请求权限及凭据隔离；不将stdio健康证明外推HTTP。HTTP恢复会话与业务授权分离，session id不成为跨用户权限。

### D12 保存真实成果与全链质量仍是终点

当前Skill execution已有Permission→Firewall→Effect Fence→Execute→Evidence→Evaluation→Trace，registry元数据预约、状态和语义失败检查。优先补真实接缝而非新造框架。J7必须取得一个正常CTH/BMP或独立Shared研究任务：合法输入→获准工具→来源清楚的有用可编辑结果→保存/修订/重开→撤权/取消/升级回滚。MCP CALLED只证明该层收到结果，静态负例只证明应验什么；均不能关闭J7/U19。

## 4. 二十项可执行验收（全部NOT_RUN）

| ID | 输入/扰动 | 期望的可核证据 | Owner |
|---|---|---|---|
| S01 | 正常固定版本、单页已核只读工具 | 正确schema/来源及保存重开成果，不只CALLED | C2/C5 |
| S02 | 返回不支持协议版本 | 握手停止、无工具调用、明确原因 | C2 |
| S03 | 缺tools capability | 不调用未协商能力，已有工作可继续 | C2 |
| S04 | 正常工具在第二页 | 同会话cursor继续；预算截止显示partial | C2 |
| S05 | schema超过展示上限 | 展示可缩略，批准仍核完整schema digest | C2/C6 |
| S06 | 仅readOnlyHint但未可信/无沙箱 | 发现进程启动前阻断并说明所缺 | C2/C6 |
| S07 | 仅mcp:tools/call缺read_only或域授权 | 原权限链拒绝，不以布尔true授予 | C2/C6 |
| S08 | 同版本launcher字节变化 | 当前包与批准不匹配，无执行 | C2 |
| S09 | 缺自测回执/回执指向旧包 | 不升级healthy/verified | C2/C6 |
| S10 | 名称不变、schema/工具行为改动 | 旧批准失效，差异可读和回滚 | C2/F |
| S11 | 无换行超大stdout、stderr洪泛 | 预算内终止，峰值内存有界，无宿主卡死 | C6 |
| S12 | 负数/错误类型/额外字段 | schema拒绝；合法正常值成功 | C2 |
| S13 | isError、业务UNKNOWN、明确no_records | 各自保真，正常0与未知不混 | C2/C5 |
| S14 | 用户取消与旧回调竞态 | 新版本不覆盖，实际效果单独对账 | C2/C6 |
| S15 | 禁用/卸载与运行中任务相交 | 不接新工作；已发生效果可读，审计保留 | C2/C6 |
| S16 | GitHub有过期凭据 | 不显示验证CONNECTED、不泄露凭据 | C1/C6 |
| S17 | 已选仓库正常读取跨50条 | Link与断点、真实总取得量/缺失可核 | C1 |
| S18 | 403限流 vs 权限不足，429 | 分类/退避正确，不盲目重登录或高频重试 | C1/C6 |
| S19 | 撤销GitHub授权/扩大仓库选择 | 立即停止后续越范围读取；新增授权独立确认 | C1/C6 |
| S20 | 获准真实Shared任务+升级失败回滚 | 原引用/编辑/保存版本正确，正常用户成果复核 | C2/C5/F |

这些是有具体反例和出口的实验协议，不是20项测试通过。可在授权的隔离环境中实现固定假服务器/fixture，再运行一个获准正常业务任务；任何生产运行、包安装、账号授权、密钥或依赖变更都需对应实际授权。

## 5. 资源、实施与研究缺口分开

已补研究：官方协议关键行为、当前main函数/调用边界、静态反例、采用/拒绝及Owner方案。仍缺研究：全部第三方包的精确revision/传递许可/源码体积及逐包行为审阅，HTTP完整caller和所有跨平台宿主细节；不能由本报告称全商店完成。

实施缺口：上述握手/分页/身份/隔离/回执接线须在原Owner开发验证；本文不改产品。资源缺口：真实目标宿主和包、测试账号、精确许可/用户用途、可复核安装环境。用户验收：母语可读交互、正常CTH/BMP/Shared成果、升级恢复与收益需用户实际任务，不是文献可补的证据。

本研究覆盖公开官方资料与静态源码，不证明历史开发、服务或模型训练正在运行。既有候选回执仅适用于各自冻结版本；缺当前源码和运行证据时，不能宣称开发续跑或产品闭环。

## 6. 原始来源

- S1 [MCP Lifecycle 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)，版本/能力/超时与关闭相关段。
- S2 [MCP Pagination 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination)，完整分页机制正文。
- S3 [MCP Tools 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)，schema、annotations、错误与结果相关段。
- S4 [MCP Security Best Practices 2025-11-25](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)，本地进程、SSRF、token/代理隔离相关段。
- S5 [Agent Skills Specification](https://agentskills.io/specification)，滚动格式文档，本次读取元数据/许可/兼容/allowed-tools及按需加载段，不作某产品实现承诺。
- S6 [MCP Cancellation 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation)，完整行为与竞态正文。
- S7 [GitHub App User Access Token](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app)，访问交集、授权流程、撤销及过期相关段；滚动文档。
- S8 [GitHub REST Best Practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)，分页、限流、条件请求与重定向相关段；滚动文档。
- S9 [MCP Authorization 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)，resource/audience及每次HTTP请求相关段。

所有来源读取于2026-10-17 21:12–21:14 UTC；协议按2025-11-25固定，不声称它是未来所有服务器唯一版本。产品源码固定main SHA；官方网页滚动内容与固定产品代码版本分开。
