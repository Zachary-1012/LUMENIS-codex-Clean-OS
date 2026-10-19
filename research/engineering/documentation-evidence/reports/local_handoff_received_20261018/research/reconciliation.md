# 本地交接吸收与现 main / 云候选 / v010 对照

核对日期：2026-10-18 UTC。仅云端读取及独立研究文稿；未访问用户电脑、未唤醒本地窗口、未改产品源码/数据库/运行环境、未改冻结 v010。本文是证据吸收记录，不是第二套治理规则，也不派工或授权操作。

## 1. 实际收到与验证层级

- 已完整读取 LOCAL_HANDOFF_TO_ZACK.md，418 行、50,950 字节。
- 报告实际 SHA-256：`f74e72cca65a218b55b53b0b7aec9958c8317923b94e92388298648600c43b40`。
- FILES_MANIFEST.json 实际 SHA-256：`f39dc36f834b552d03917a0cdfdf2c157e3f434e9f702c2fc0c0aa511aac9582`。
- Manifest 共 21 个成员，其中 1 个就是已收到报告；其余 **20 个文件字节未随附**。manifest 自身不在自身成员表，故现收两个文件不等于收到其全部证据。
- `candidate-and-receipt-map.json` 保存全部 21 成员逐项收到/缺失状态与 68 候选比较。不能以报告里的文件名、路径或 hash 冒称实际已读 JSON、截图、模型权重或原件。
- VERIFIED_CLOUD 指本次在云读取并计算的字节；REPORTED_LOCAL 指报告转述的本机观察；NOT_RECEIVED 指未收到所引文件。报告使用 OBSERVED 是当地取证者的观察，不能自动变成云端亲测。

## 2. 版本、Core 与规划原件

| 对象 | 可下结论 | 不可下结论 |
|---|---|---|
| 历史工作区报告 | 报告HEAD 7792040e；报告并非实时远端读取 | 工作区差异计数不能换算为未完功能数 |
| 本地缓存 main | 报告：4dab98ed6357133da9307de846180ed4f7bba5f5；与父任务已核当前 main 锚点一致 | 本报告无新联网证明；后续发布仍由父任务 fresh remote readback |
| 本地 Core | 报告：PID1320、8201、主根 app.py、主根 monitor.db 句柄、health200；静态文件等于主根构建而不等候选构建 | 单入口 hash/health 不绑定所有内存模块、依赖、构建与 DB 组合；不证明业务闭环 |
| 云2248 | 实际读取 `[LOCAL_WORKSPACE]/lumenis_bmp09_parser_20261017T2248Z/source` | 不是本地主根正在运行版本 |
| 云0605整合 | 实际读取 `[LOCAL_WORKSPACE]/lumenis_integrated_backend_20261018T0605Z/source`；整合员给定 manifest 2f57b6040192177f319b7a59c015541603ea72179b4c0d23688c4e6e0f98b59e | 本记录不把其他任务仍运行的回归宣称完成；没有改该 source |
| main 唯一完整规划 | 云实测250700字节/SHA 8ab5a992502df46bf1c32cbffa3b167d8ee3bffa1a0f54edd76f024ea72bc954，与本地报告一致 | 不是前端实现通过 |
| main 唯一总草图 | 云实测126724字节/SHA b3c6b6b67b4d2e6a6f731f323cb1e909eb2f76acbac0c03ec618aece72bef07d，与本地报告一致 | 不需为核底稿再取得本地副本；不把文件存在当视觉验收 |

云 main 读取根：`[LOCAL_WORKSPACE]/third_party_inventory_recovered_20261018/main4dab`。上述两份规划是**字节级完全对应报告 hash**，比报告“忽略换行相同”更窄且直接可核。

## 3. 68 候选与受保护差异

对报告列出的全部 68 路径，云2248、云0605、main4dab 分别均为：**0 个报告哈希匹配、67 个存在但哈希不同、1 个不存在**。不存在项为 `lumenis/shared/agents/conversations.py`。另将云文件统一 LF 后转换 CRLF 再算 hash，仍 0 个匹配。

这证明没有从这三个云树中找出报告所述完整候选文件的同字节副本；不证明所有 hunks 独有、不证明全部功能未合入，也不证明68项应该整文件覆盖。没有本地候选实际字节，无法做三方语义比较。每项云 SHA 及 LF→CRLF 变换 hash 保存在机器映射。

报告的10项主区 dirty 重叠：Experience Constitution、app.py、lumenis_core_client.dart、CTH-10/SH-01/SH-02屏规、experience_runtime.py、experience_screens.py、auth_recovery.py、test_ai_intent_permission.py。这是潜在写入碰撞，不是已经证实的三方冲突。当前不合并、不覆盖。

报告另列7项 generated plugin 文件 dirty 未在68冻结包中；必须保留，不能从68包验收推出整 worktree 已收齐。28受保护记录与77同步记录是历史集合：28项包含4字节相同/1双方删除/9仅换行/14内容不同；77项含69字节同/5历史删除/3内容异。它们本轮仅由报告转述，缺 candidates.json/closing-preservation.json 原字节支持。

## 4. 13项材料与模型缺口

13项是2 DOCX、1 BUSINESS-DRAFTS.md及10份指定UUID粘贴文本转录的位置/哈希记录；报告明确未语义研究、未复制。当前没有由这次交接收到这些原字节，不能称“13原件已完整采用”。十份转录不等于其引用的底层附件。

能力.docx：报告实测45,117字节，hash b5706a06aec535a5de25fcbf10033f3152a7ea2514df7cdfdab897d9523c4e45，与历史hash一致；历史46,222字节矛盾保留，不能选一个改写旧记录。内容身份目前是报告的hash声明；待原字节/原始记录到齐后核清大小来源。补充需求.docx：报告39,389字节及3a5b6689…一致。BUSINESS-DRAFTS.md报告10,832字节/5026cea7…；均不据此宣称完整语义读取。

模型报告的新信息是历史依赖版本已找到，而不是转换链已闭合：

- 批准base revision 6cee5e81ee83917806bbde320786a8fb61efebee；NF4 revision 093fba6992ef5a7152481afec0bdfca1ac486998 的父revision仍UPSTREAM_UNSPECIFIED。
- 未找到base→NF4转换脚本/命令/输入checkpoint回执；manifest shard hash不是本地转换证明，单独tokenizer revision未明。
- 目标framework lock SHA 220e8e688ce0fb05779c5f7f640476bf928c11e185e00c0552cb3cf8b3a6ea21 未找到；resolved文件不同hash不能替代。
- T4 adapter保存/重载技术回执不等业务/进程重启验收；当前adapter hash与另一proof不同，版本关系待核。
- 5090安装/探针model_loaded=false、optimizer_steps=0；Kaggle/SSH阻塞不等训练；Gibbs为另一个实验，不补gpt-oss证据。
- 可继续云端做已有公开revision/配置/脚本静态谱系核对及缺口表；不得自行下载/加载权重、转换或开训。

## 5. 前端语言与普通研究规则：精确对照

v010来源为冻结 source/UNIFIED_FRONTEND_WORKING_v010.md，PDF页码为1起物理页码。main规则直接沿原Experience与既有plan，不另立新规范。

| 核对项 | main位置 | v010位置 | 裁决 |
|---|---|---|---|
| 任务/内容/成果/行动优先；内部实现不得变页面说明 | Experience 676–686行，plan101行 | §3第1节342行/PDF23；354–355行/PDF24；J12 1071行/PDF73 | 分散落实，未发现明确要求把内部说明原样上屏；但未把原全局语言约束完整就地重述，建议在现工作结构段最小补足 |
| 普通研究不设来源使用/本次用途门槛 | Experience690行；plan59、63、338/G189、908行 | J18 1300行/PDF82；G189 6665行/PDF258 | 明确符合；不能误删真正额外用途/第三方处理/训练/发布的授权检查 |
| 实际入库时间、逐材料/分析卡、原文与分析、保存重开恢复 | Experience692行；plan63、338 | J18 1300–1306行/PDF82；G189/PDF258 | 保留；J18主文可显式补“每份材料及每项分析各一张关联卡”，不能以目录/Reader替代既有卡片要求 |
| 方法/版本按需；影响决定的限制须可见 | Experience680–684行 | 1071/PDF73、1145/PDF75、1302–1306/PDF82 | 符合；不能以简洁为名隐藏错误/风险/权限/UNKNOWN |
| source-use具体行动检查 | 同上及普通研究例外 | J06 898/PDF65；J18 1326–1328/PDF83 | 后台检查/额外用途的设计约束，不能据此推断普通上传需再填表；建议明确“后台复核，只有实际额外用途才显式确认” |
| 权限长条/内部术语常驻风险 | Experience678–684行 | J06 880/PDF64：“上方固定来源身份/权限边界” | 来源身份可以固定；“权限边界”易被误做常驻长说明条。建议只显示当前必要权限状态/风险，完整细节按需；不是取消权限门 |
| 技术依据被误投为页面文案风险 | Experience684行 | J22 1553/PDF93的schema/rights_state；J27 1801/PDF107的Owner接入状态 | 是设计/证据文字，不是已经证明的UI缺陷。实现时不逐字上屏；用户只见影响当前工作的可用/受限及可行动原因，技术字段置按需检查 |
| 鼠标如手/四端/约90ms/无障碍 | Experience694–696行 | v010工作结构、空间/交互合同及G189 | 保留原全范围；本次静态检查不证明参数实际绑定、性能或四端验收 |

必要文稿修订建议（仅建议，未改任何冻结稿）：

1. v010 §3第1节末增加一句沿用main原文意旨：“操作界面只呈现当前任务、内容、成果、可用行动及必要状态、错误、风险与权限确认；内部Owner/API/算法与本方案中的实现解释不是页面文案，方法细节按需展开并返回原对象。” 不新增介绍页/教学段。
2. J06 880行改为：“中景保持真实来源页面，上方保来源身份；仅当当前操作受影响时显示必要权限状态、风险和恢复动作，详细边界按需展开。”
3. J18 1326前补明确短语：“以下是后台按具体行动进行的预检；普通获准研究资料仍直接上传导入，不新增通用用途表单。” 其余各类权限语义保留。
4. J18主文补清现G189已有的逐材料/分析卡与保存/修订/重开/恢复语义。仅重申已有要求，不改变Reader主导与原件类型差异。
5. 1553/1801不删技术证据，也不直接用作页面提示；在既有“界面表达”处分清用户短状态与按需技术证据。没有证据据此宣布现UI已修好。

v010规划审批与产品验收分别记录；历史文稿的未审批状态不覆盖后续版本状态。整体产品前端 NOT_ACCEPTED 仍保留。

## 6. full-resume 16条逐项承接

| # | 保留内容与本次处置 |
|---|---|
| 1 | 既有成果收敛、跨模块接口、保存/修订/重开/恢复仍未闭；历史检查记录不证明当前运行状态 |
| 2 | 免费训练纠偏、Kaggle/adapter/评估与真实资源仍缺运行闭环；本次只吸收历史版本证据 |
| 3 | OLD01-18历史移除及材料采用继续需核；原窗口暂停/Goal不由交接恢复或改写 |
| 4 | author fixes、工具/Experience/静态核对及替代候选精确hash；旧4606补丁不发布，最新main路线由父任务主导 |
| 5 | 全产品遗漏/视觉/工作流、REA与原件、未读未采用和用户成果全保留 |
| 6 | 10/12 CTH-10历史失败与内部编号重开问题保历史，不宣称当前main或Core同样失败/已修 |
| 7 | 数学/Hybrid研究采用、一般算法/模型增益及四产品操作证据分开，文档不即实现 |
| 8 | 历史Owner/CURRENT/Goal写回不冒当前真实窗口状态；本次不操作这些窗口 |
| 9 | 全局2D水彩限制移除历史要求不恢复；实际视觉参数/四端效果仍须本地验证 |
| 10 | 依据当前直接PO、实际源码/Owner/runtime更新连续性；完整产品开发/候选整合/成果闭环不缩范围 |
| 11 | Groq旧779缺源码与较新main有源码差异保留；不得把云源码当本地已加载 |
| 12 | CTH/BMP→Shared确认、多worker、媒体UI、崩溃/撤权、线程032/048、Pattern045、FactWall046、54bindings/11章/四端全保留；“130behind/main9556”仅历史 |
| 13 | 诊断源集成不等Core真实入口验收；safe profile不放宽、不借新main回执给旧主区 |
| 14 | 唯一完整规划/草图、像素/代码研究、四端与REA验证保留；05:34批准更新方案状态但不自动启动本地前端 |
| 15 | 五份太古汇材料原件完整读取、可靠补充、Importer/分析实际采用、主体/自主采集/Source-Evidence-Canonical/刷新恢复/成果全保留；手动导入不冒自主采集 |
| 16 | 全前端NOT_ACCEPTED、普通导入免用途表单、真实timeline/逐材料卡、原文/分析/修订/重开/恢复、未知rights及额外门、鼠标如手与无障碍及五材料校准分析全保留 |

## 7. 完整Markdown与入仓文稿清单（准备，不写source）

已存在可用的**完整排版源Markdown**，不需要从PDF抽取碎行重建。实核源SHA `9d9db9c1f205fc7d206ded88784d9fd6b2aff053b3222ca61bad4fa096f4d63a`，UTF-8无BOM、LF、末尾换行、7,983行。按有序段落清单本次重新算hash：2,884个exact段全部匹配；3个显式resolved替换全文全部存在。原保全回执记311步骤/195G/25媒体/213UX/29旅程，本次对该回执源hash与段落字节复核；不把计数当产品完成。

六张图全部存在、1600×900；与304页PDF第37/39/41/43/45/47页内嵌图片逐RGB像素相同。源中6个相对图链接均可解；无其他非图片本地相对链接。完整机器证明见 surface-markdown-validation.json。

建议下一文稿阶段沿main原位置更新，不把UNIFIED_FRONTEND_WORKING作为另一个current/router：

| repo相对路径 | 拟操作与约束 |
|---|---|
| `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md` | 在现唯一全文规划原位吸收已批准v010完整正文与随后状态，保原plan全部源路由、需求编号与未闭项；不能直接覆盖丢掉现main序言/规则链 |
| `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md` | 沿原唯一草图更新v010相关空间/工作流；保该文件原全部屏/四端/状态/交互；不另建第二总草图 |
| `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/figures/{cth,bmp,research,media,ai,system}.png` | 保存六图原字节；plan中链接改为`sketches/figures/name.png`，总草图中为`figures/name.png`；图片是资产，不是新治理文件 |
| 同主任务既有证据归档位置 | 保存批准前冻结v010/PDF/段落及图hash证明，标明历史编制状态；不添加新根入口或把旧方案当活规则 |

main .gitattributes未对通用Markdown另订专门编码或全局EOL；本次建议UTF-8无BOM/LF匹配现云main原件与完整v010，不声称仓库已有不存在的统一强制设置，也不修改.gitattributes。后续将相对路径、大小写、UTF-8/LF、图hash与断链重新验证。第三方Word是否有完整MD本任务未核，不作承诺。

注意：v010完整字节可作为交付全文，但把它作为main唯一plan的未来版本之前仍需保全main原文段落及原草图对应矩阵；目前的2,887段证明针对v010既有基线，不是对main1,075行全文的新增逐段合并证明。禁止拿此证明声称原main已完整合并。

## 8. 下一本地交接与云可继续项

现在云端可继续：当前main规则/Owner/接口静态核对；0605候选同版回归由原整合任务进行；前端完整MD沿唯一plan/sketch做文稿级映射和最小语言澄清；模型缺口/原件取得矩阵/精准三方比较准备。均不要求再开本地窗口。

后续源码与证据整合所需材料：

1. 先提供现manifest缺20成员的原字节并核hash，尤其candidates/originals/model-provenance/frontend-local-evidence/closing-preservation；不要求秘密、数据库或权重payload。
2. 提供68冻结包或精确68文件原字节、原manifest及基线身份；同时保10主区dirty碰撞和7生成文件额外dirty，不整文件盲覆、不应用stash。
3. 13指定材料若需全文吸收，定点复制授权文件；十份转录与其引用底层附件分别记，追查能力.docx历史size出处。
4. 本地前端构建由Codex/GrokBot沿用户明确调度执行；先建立精确main+批准候选+本地dirty处置后的组合身份与构建manifest，再验实际装载及正常产品旅程。构建通过不替Web/Win/macOS/iOS、保存/修订/重开/崩溃恢复验收。
5. 当前保持原Core/主区/stash/各worktree不动。模型转换、训练、服务切换、数据库操作、旧任务恢复需各自明确授权，报告本身不授权。

交付给父任务/备份员：本目录两份原接收文件保持原字节，research/为旁挂派生核对。随主任务同版整包备份，不单独上传增量，也不将本记录变成产品执行路由。
