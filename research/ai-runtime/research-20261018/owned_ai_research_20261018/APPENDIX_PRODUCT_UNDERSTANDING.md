# 补篇：AI懂整个产品与用户/AI双入口

冻结：2026-10-17 20:00 UTC。文档研究，不是实施指令。原REPORT.md等四个冻结文件不修改。此补篇延续完整自研AI目标，小专家只是实施组成，不替代整体理解、推理、创作、多模态、受控工具、连续工作和学习能力。

## 1. 原目标的可验证含义

“懂整个产品”意味着面对实际任务，AI能准确解释可做与不可做、选择当前存在的能力、保持业务语义和来源、把结果交回可编辑工作，并在权限/资源不足时提供真实继续路径。它不意味着把所有源码塞进权重，也不意味着拥有全部数据或权限。

产品能力知识、当前运行可用性、来源事实、用户意图、执行授权、模型质量是六类不同对象。检索到文档不是功能已经部署；模型记住旧接口不是新版本可执行；数据被检索到不是Canonical事实或可训练许可；模型生成的命令/计划不能成为Permission授予者。

用户直接从页面执行与AI从对话发起，必须进入同一原Owner业务合同、同一权限/SourceUse、同一保存版本与取消恢复链。AI入口不得获得更大权限；手动入口也不能为了共享而强制先跑模型。聊天可以独立完成问答，也可启动获准的独立研究/提案/视频/播客，或接续CTH/BMP成果；不强制全任务经过五轮或固定五角色。

## 2. 实际读取源码与局限

源码根与REPORT.md相同，恢复候选名称为LUMENIS_20261017T1620Z_dot-zack_NOT_FINAL。另有源hash见APPENDIX_SOURCE_MANIFEST.json。本次只静态读源码，没有导入产品模块、调用HTTP/API、执行工具、读生产数据库、跑测试或改产品。16:25之后未恢复的Conversation候选不在本次证据范围；不能声称那批70项测试在本候选通过，也不把源码定义当运行验收。

| 读取点 | 实际可证明内容 | 不可据此声称 |
|---|---|---|
| `lumenis/ai_hub/service.py:26–47,144–205` | SYSTEM_ROLE、静态MODULE_HINTS；chat仅取FUNCTION_MAP路由元数据，明确没有会话逐来源SourceUse；沿Gateway选路 | 已理解全产品、已读取业务来源、当前通用owned聊天可用 |
| `function_registry.py:1–约100` | legacy兼容FUNCTION_MAP以id/page/label/targets/keywords定位功能，search_function_metadata不读业务记录 | 权威能力执行清单、实时可用性或新创作功能已全覆盖 |
| `lumenis/ai_hub/conversations.py:13–46,321–349,385–486` | actor/workspace/scope、revision、幂等键；用户/模型/任务投影分开；最近6轮各800字符；token预算未验；reserved完成CAS；未知结果不自动重试 | 完整长上下文、无损记忆、调用已停止、所有任务链可加入模型上下文 |
| `lumenis/ai_hub/routes.py:149–167` | respond/interrupt路由分支与允许body字段，Owner解析实际身份 | 请求已授权或生产可用 |
| `lumenis/shared/agents/skills/registry.py:61–85,268–326` | SkillMetadata定义owner/version/input/output schema/permission/risk/policy/evidence/evaluation；Shared catalog复用到原registry | 元数据EVALUATED等于本环境测试已通过 |
| `lumenis_shared_skills.py:36–254,264–380` | 六个Shared研究/创作工具的目的、schema、策略与绑定；有PARTIAL标记 | 工具名字所暗示的全部平台访问或端到端生成能力 |
| `agent_capability/router.py:89–121,449–494,627起` | ToolDefinition与FormedCall绑定descriptor/implementation/runtime/content/request/context身份；形成后变更拒绝；执行进入安全链 | 模型自带工具名/参数能授权执行；仅dict非空就成功 |
| `agent_runtime/task_binding.py:78–107,175–220` | 先限已授权registered tools；rule_based无模型计划；Gateway请求沿任务输入版本 | 任意新工具已自动可用、模型必须执行所有轻任务 |
| `agent_runtime/durable_adapter.py:392–546` | 复用TaskEngine终态/checkpoint/cancel，并核持久取消读回 | 会话interrupt即取消所有底层效果或外部调用 |
| `lumenis/shared/agents/skills/execution.py:2–4,14–70` | Permission→Firewall→Effect Fence/幂等→Execute→Evidence→Evaluation→Trace；ctx分离可信server对象与payload | AI可以直接改生产事实或以payload覆盖可信actor |
| `owned_service.py:56–124,323–348`和`core.py:710–724` | typed准入/SourceUse与runtime绑定；源资料不能通过泛型聊天自动外传；无hidden fallback | 全部Shared文本能力已接好或外部API配置即许可 |

当前会话源版有具体保守限制：历史task_projection或非source_free模型输出进入后续响应前，会要求typed SourceUse；这能避免未准入来源混入聊天，但尚不能据此宣称研究→提案→视频的完整聊天上下文链已闭合。interrupt_response返回external_call_stopped=False、prior_result_unknown=True；前端必须保持这个区别。

## 3. 复用既有Owner形成版本化产品能力知识

建议由原有SkillRegistry、Shared catalog、ToolDefinition、ScreenSpec/业务Owner API与运行状态生成只读能力投影，附原来源hash。它是检索/模型上下文，不新建第二个权限库、调度器或注册中心。FUNCTION_MAP作为兼容入口提示，不覆盖现有权威Owner。只有确认字段缺失才向原Owner补字段，不能直接新造平行体系。

每个能力投影至少包含：
1. 原skill/tool/capability标识、Owner、来源path/hash、schema与实现版本、有效期/撤回状态。
2. 业务目的与边界：输入从哪里来、什么成果、适用范围、不能做什么、独立使用与可选串联、人工路径。
3. 参数schema、必填/可选、单位/币种/时区/日期含义、合法枚举、敏感字段与来源版本；不要让LLM补造actor、scope、凭据。
4. 结果schema、原文/确定性计算/AI派生/人工决定的类型、Artifact版本、Evidence定位、成功/部分/不可用/待批/失败/取消/未知状态。
5. 所需Permission、SourceUse、执行policy、外部效果、审批资源、幂等与重试条件、取消/恢复能力；这些只是说明，调用时仍由真实Owner重新决策。
6. 当前模型/provider/版本、调用预算和支持任务/语言、运行实测时间、可用/不可用原因；没有实测成本就UNKNOWN，不编造免费或零延迟。
7. 当前Task/原工作版本/关联材料/已确认决定/未完成步骤/已提交效果/合法下一步；用户可见简要计划与结果，不展示私有推理链。

对旧文档与新接口冲突：从Owner取当前descriptor；投影hash不符就重新读取，不让模型以记忆补齐参数。新能力尚未训练进权重时，可用经核实的当前schema做检索增强规划；若不存在、禁用、未绑定或只PLANNED，明确不可用，不能编造函数调用。

## 4. 实际六工具示例及正确理解

以下是静态catalog内容摘要，执行仍须当前registry/handler/Permission验证；它们不构成全产品工具总数。

| ID | 目的与关键输入 | 返回形状 | 原policy与重要边界 |
|---|---|---|---|
| shared.union_search | 本地研究/Evidence检索；query必填，limit可选 | resources[]、research_assets[] | READ_ONLY；不是外网全平台搜索；候选资料不自动成为事实 |
| shared.video_shotcraft | Brief镜头/转场草案；brief必填，evidence_id/note_id/ocr_text/asr_text可选 | shot_plan[]、video_analysis、artifact、render_status | APPROVAL_REQUIRED；允许的Evidence由运行时准入；草案不等已生成/发布视频 |
| shared.cangjie | 本地文本/Brief结构提炼；text/query | structure、research_candidates[] | READ_ONLY；不替代原文与事实链 |
| shared.huashu | Brief映射创作工作流；brief必填，platform/asset_type/audience/goal可选 | workflow、content_types[]、modules[] | APPROVAL_REQUIRED；流程建议不是每个制作步骤已完成 |
| shared.social_card | 本地SVG社交卡草稿；title必填，subtitle/accent/width/height可选 | artifact_type、svg、approval_required | APPROVAL_REQUIRED；SVG草稿不是已发布社交内容，也不是基础图像模型生成 |
| shared.last30days | 本地Canonical近时段素材；days/query | period、stats、notes[] | READ_ONLY；真实范围和缺失须保留，不冒称采集全部平台 |

SkillMetadata已有input_schema和output_schema。ToolDefinition主要有params、permission/risk/approval、version和运行身份，不能用简单参数检查冒充完整结果schema验证；候选升级须逐handler与Skill输出合同核对。路由中_normalize_handler_result会识别ok/success=False，模型回复“成功”不能覆盖真实失败。

## 5. 完整工作上下文与可编辑交付

建议以现有conversation_id/task_id/Artifact版本链接上下文，而不是复制另一份成果。独立创作以工作区/项目及素材权限作为合法起点；CTH/BMP场景沿原domain/Subject/BrandFocus语义，不能为了兼容文本服务伪造业务归属。

示例验收链（拟议，尚未执行）：
- 用户直接上传自己的Brief→手动编辑提案→保存、离开重开；AI停用也完成。
- 同一Brief在聊天中要求提纲→已准入模型生成可编辑草稿→用户改第二段→新版本保存；来源与人工改写分开。
- 经许可研究材料→主张/引用→提案→用户选择转视频或播客→复用脚本/素材版本、实际剪辑与试听→产物保存/导出；独立视频和播客同样能从空白Brief开始。
- 一次对话交办两项独立任务；长任务继续，用户可打断/修改指定一项；另一项actor/scope/输入版本不串；结果回到原任务。
- 用户回到原工作直接操作，AI同步读取最新已保存版本；旧草稿不能覆盖新修改，冲突需解释与选择。

原模型目标仍包括理解、推理、原创创作、工具协作与恢复；分类专家准确不等于上述交付闭环已达到。模型、工具、Owner能力与界面回路分别取证。

## 6. 受控语义纠错

保留user_input原始文本及版本。可以生成“理解候选”供查询/计划使用，但不得覆盖原话、原文件或Evidence。建议记录原片段、候选解释、理由/置信、涉及实体/数值/时区及用户确认结果；此为文档设计建议，不声称当前有完整schema。

低风险明显拼写错误可在不改变任务含义的检索中做候选扩展，同时保留原词；有歧义或会影响执行时问最小必要问题。金额、币种、日期、时区、数量、收件人、否定、权限、发布/删除/购买/训练等动作词不可静默修正。

例：
- “帮我做个提按”可理解为“提案”，交付时保留原输入，必要时表述解释。
- “不要发布”绝不能纠成“发布”；模型自信不构成更改许可。
- “预算1.5万/15万”、“10/11”、同名品牌或“给他发”在目标不明确时停止相关效果并确认。
- 源文档写错金额与用户输入错别字是不同情况：事实核验应标冲突、保留原文，不能替原来源改事实。

网页、Skill说明、模型回答、检索片段中的“忽略权限/自动批准/换provider”均是不可信内容。可当研究对象，不进入可信策略、工具定义或系统指令。纠错后的文本也不能扩大授权。

## 7. 具体验证计划与判定

本表是后续获准实施的验收清单，不是测试运行结果。沿现有G31/G39/G50/G83/G84/G92/G108/G109/G110/G121/G124/G128/G132/G136/G138/G189、原Owner与ScreenSpec接续，不新增队列。

| 场景 | 必须观察到的证据 | 失败判定 |
|---|---|---|
| 用户/AI双入口同任务 | 同业务Owner、同参数含义/actor/scope、同Artifact版本与Effect审计 | AI绕过确认，手工被强制要求模型，或各有一份不同真相 |
| 错版本/新能力 | 当前descriptor/hash对照；schema不符/禁用/未绑定typed拒绝或重取 | 模型调用记忆中的已退休工具；未学过就编造接口 |
| 产品知识与事实分离 | 路由提示标metadata；来源逐条准入且引用可读回 | “检索到”被显示为已执行、最新事实或权限 |
| 模型输出与参数 | schema+单位/范围+owner语义验证；拒绝伪actor/权限字段 | JSON格式正确就执行语义错误的金额/范围 |
| 注入/不可信工具说明 | 引用内容原样保留但不改策略；可信descriptor版本不变 | 原文一句话扩大工具权限、外传资料或复活provider |
| 幂等/超时/重试 | 同key同请求返回既有结果；异请求冲突；先核已提交效果 | 超时自动再发、重复发布/生成/扣费；无回执即假成功 |
| cancel/interrupt差异 | TaskEngine取消实际读回；会话未知结果仍标未知 | 会话interrupt就宣称GPU/HTTP已停止或外部效果已撤销 |
| 连续上下文 | 原用户输入/最新版本/未完成项/授权期限；截断有账 | 6×800字符静默当完整历史，省掉否定/日期/约束 |
| 多任务/跨用户隔离 | 任务引用及actor/workspace绑定；错误引用拒绝 | 其他用户资料或任务结果混入，群成员代替授权 |
| 独立/串联创作 | 草稿可编辑、保存/重开、版本冲突、源撤回影响定位 | 只返回聊天文字、不落成果；空白Brief被强制绑CTH/BMP |
| 语义纠错 | 原输入不变；高影响歧义确认后才形成精确动作 | 自动改数量、金额、日期、否定或接收对象 |
| 资源不可用/成本 | 当前模型选择与可用证据、预算上限、真实耗用 | 文档宣称模型可用、暗转Groq/Claude、以临时开发算力承诺上线 |
| 学习/知识更新 | 新descriptor可检索但不自动训练；训练与晋升独立批准 | 会话保存等于训练同意；角色模型自批升级 |

## 8. 建议实施先后与停止点

先审查当前实际能力投影和调用覆盖，补齐原Owner缺少的参数/结果/权限/恢复说明；再在可用模型上验证版本化上下文与建议；再审批有限真实双入口/连续创作闭环；最后用失败案例驱动小专家或20B微调。权重路线和产品理解路线并行，但谁都不能代替对方。

当前停止点为此补篇交付。完整原AI目标保留；产品修改、数据准备/训练、模型切换、第三方访问与任何效果不由本报告授权。
