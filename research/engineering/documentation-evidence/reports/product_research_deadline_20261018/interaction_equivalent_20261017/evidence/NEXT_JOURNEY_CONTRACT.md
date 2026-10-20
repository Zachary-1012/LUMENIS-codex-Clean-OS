# 下一条完整行为合同：独立文稿的保存、修订、重开与导出

审计时间：2026-10-17 UTC。只读审计产品与冻结 main；仅本文件为新增独立审核材料。未执行产品、数据库、浏览器、服务、部署或产品测试。候选不是已实现/已验收入口。

## 结论

推荐一个完整入口：**「写成文稿，再放心继续」**。由用户自己的标题/Markdown 起步，编辑预览 → 本地版本保存及精确读回 → 局部修订/差异 → 离开并重开 → 精确版本的人工审阅 → 明确导出所选已保存版本。正式接入仅指向 **独立 Shared SavedWork `kind=report`**。

这是文稿工作旅程，不新增一种动画，也不把已有版本树、导航、冲突分别再计为新种类。43例已有相关原语，但没有一个入口将真实文稿内容、顺序版本、未保存草稿、跨会话恢复、版本审阅和导出对象连成一条可验证路径。最新回归数量见 ENTRY_AND_TEST_INDEX.json，浏览器视觉仍待验；本审计本身没有新增通过数。

**范围边界：**此候选不是完整专业比稿/J4验收。章节结构、事实墙、10段比稿、预算策略、Office编辑器、来源采用及正式 Evaluation 仍由原Owner推进；本demo不能同时自称 BMP internal_pitch 已验收。最小实现可让 Markdown 标题代表章节，但不能说已实现结构化提案编辑器。

## 一、明确规划依据

以下相对路径以 `lumenis_working_20261017/source/` 为根。

- `AGENTS.md` 开头 2026-10-11 correction：用户稿可独立制作，不强制 CTH/BMP/SourceBrief；用户创作不是 Canonical 外部事实。§11（1287起）真实 Permission/effect，拒绝不产生效果。§13（1364起）原型/路由不是产品完成。§14要求区分独立回归与真实E2E。
- `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md` §1：人工编辑/保存导出重开不依赖模型；§3第60行「独立提案/文稿」、第65行「成果与版本」：人工输入→编辑预览→保存→修订→版本比较→关闭重开→已接格式导出。§6第129行：完整旅程与适用Evaluation。G33/G38/G80/G104保留完整创作、独立scope、质检、专业提案要求，不能用此最小切片关闭。
- `00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md` §38，第1331–1378行：同一任务/来源/结果版本，变化产生显式delta，保存/重开/回滚；第1384–1401行：保人工编辑、拒绝迟到结果、草稿/保存/执行分开，撤权行为与真实等待测量。
- `00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md` J4/U13（161/183行）、Shared Content（320行）、跨成果路径（450行）、C4提案/文稿（682–688行）：C4内容，C5 SavedWork/Artifact，C6 Core/API/Permission，F呈现。完整提案与此 report slice 不等同。
- `contracts/experience/screen-specifications/SH-04.md` §§1–2、4–8：现行独立Shared文稿合同，状态 `IMPLEMENTED_SCOPE_GUARDED_EFFECT_UNVERIFIED`，`design_decision: BLOCKED`，`binding_ids: []`。规格明确缺 content diff / return-to-parent-Task；不要将已有实现描述退回“只读列表”，也不要把source存在升级为真实验收。

## 二、现43例缺什么，能复用什么

核对 `evidence/ENTRY_AND_TEST_INDEX.json`、`src/app.mjs` 及其study声明、`README.md`。

- `src/version-tree.mjs` 是**本地分支树**，含 branch/adopt-old；生产SavedWork为同Work的当前父版本顺序子版。不得直接接该reducer到生产保存，更不得伪造生产分支支持。
- `src/navigation.mjs` 只保护research/brief样例任务文本、selection、scroll；不提供SavedWork版本、导出或实际文稿重开。
- `src/local-persistence.mjs` 的 `writeLocal(storage,key,value)` 可复用：精确序列化写入后立即读取比较，失败明确报告。它不是产品持久化回执，也不自动验证内容schema。
- `src/review-session.mjs` 是内存路由snapshot，可复用离开/回来；不能用其Map冒充关闭浏览器后恢复。
- 现冲突/恢复/权限/建议/研究学习入口提供边界参考；71学习验证不是SavedWork文稿Evaluation，不能挪用其“通过”计数。
- 真实新覆盖应是**同一份文稿贯穿工作状态**，尤其保存时仍继续编辑、迟到回执、按旧版查看而不覆盖草稿、重载后恢复同一基线、导出所选已保存版本且不含未保存编辑。实现后只计一个新完整入口。

## 三、真实Owner/API合同（本demo仍 UNBOUND）

### Shared唯一边界

每次调用带 `X-Lumenis-Workspace-Scope: {"scope_kind":"shared_workspace","version":1}`，不带CTH/BMP domain/Subject/BrandFocus、GLOBAL或客户端actor。

真实入口：`experience_runtime.py:2733–2814`；scope解析 `_shared_work_actor_scope`。Flutter：`app/lib/core/lumenis_core_client.dart:1003–1170`，`app/lib/features/shared/sh04/sh04_repository.dart`、`sh04_view_model.dart:93–179`。

1. 新建：`POST /api/experience/saved-work`
   - body：`title`, `markdown`, `kind:"report"`, `payload:{}`, `citations:[]`, `request_id`。
   - title非空且≤300，正文非空；request_id `[A-Za-z0-9_-]{8,128}`。
   - 空citations表示用户稿，绝不表示系统已验证其事实。
2. 列表：`GET /api/experience/saved-work?kind=report&limit=100`；有服务端cursor才续页。不能用旧 `GET /api/experience/screen/SH-04` 的报告类型目录冒充存档。
3. 精确重开：`GET /api/experience/saved-work/{artifact_id}`。返回Artifact ID、SHA-256、version必须与选中的版本匹配。
4. 修订：`POST /api/experience/saved-work/{artifact_id}/revise`
   - body：`request_id`, `expected_sha256`, `reason`, `edits`。
   - `edits` 现Flutter发送 `[ {pointer:"/title",expected:原标题,value:新标题}, {pointer:"/markdown",expected:原正文,value:新正文} ]`。
   - `expected_sha256` 是父**Artifact bytes hash**，不是草稿字符串的hash，更不是payload digest。
   - reason非空、≤4000；省略citations/source_adoptions沿原Owner保留并重新授权引用。
   - 响应须同 `work_id`，`parent_artifact_id`等于所选父，`version=父+1`。父版不覆盖。
5. 导出：`GET /api/experience/saved-work/{artifact_id}/export?format=md|txt|docx|pdf|xlsx`。
   - 显式选择格式；服务端重新读取Artifact、检查DATA_EXPORT与原来源scope，转换后再检查。
   - 响应 `X-Source-Artifact-ID`、`X-Content-SHA256`，非空字节及匹配MIME；下载/复制是后续独立动作。源代码不能证明真实文件交付。
   - 后端支持内部json，现SH-04前端不提供json；不要给此demo增设生产json导出承诺。

### 保存语义与权限细节

`lumenis/shared/reporting/saved_work.py:676–832`：

- `request_id`重复且相同输入hash返回原成果（replayed）；同ID不同输入拒绝 `WORK_REQUEST_REUSE_CONFLICT`。
- `previous_artifact_id`必须当前head，否则 `WORK_REVISION_CONFLICT`。无客户端分支API。
- `document.draft_digest = _digest(payload)`，不是整稿内容digest；Artifact SHA才保护完整保存文档。不要将两者合并为一个字段。
- 保存自身当前也执行 **DATA_EXPORT effect + Shared write authorization**，不是只有点击导出才检查DATA_EXPORT；提交前多次重查，commit后独立连接重开实际不可变字节才返回回执。
- `_prepare_work_revision:1004–1051`只准generic `lumenis.saved-work` v1且无task_id/assertion_id的research/report；Creation/Task-owned稿不得偷走通用revise。
- 既有历史只能读取；采用旧内容必须在当前head重新形成草稿，再保存为新的顺序子版。不得删旧版或改历史以“撤销”。

### 文稿生产Owner与Evaluation不混用

`lumenis/shared/content_creation/internal_pitch.py` 是另一条C4 Task/Word路径：v1包含ShotPlan；v2 `manuscript-only/v2`包含NOT_INGESTED input_manifest；v3 `source-bound/v3`含真实upstream_binding。`lumenis_app_api.py:146–199`为其prepare/read/action/export routes。它不是Shared SH-04的 `kind=report` 新建接口，不可把空白Shared report伪装成这些profile。

`lumenis/shared/evaluation/recorder.py:178–264`有统一record_evaluation，None→unknown、稳定ID冲突拒绝；`:316–354`的get_artifact_evaluations要求精确job_id/artifact_hash/scope/actor/evidence_refs且上游先授权。该函数不是任意空白文稿的一键人评API。`dimensions.py:469–580`是daily_reports/目录总体指标，不是当前文稿真实性或专业质量分数。

**本最小demo只提供「本地人工审阅记录」**：绑定所选local版本hash、人工意见和未核项，不写产品Evaluation、不声称事实认证、发布批准或J4完成。正式Evaluation接入为 `UNBOUND`。人工审阅不新增保存前硬门槛；未审仍可保存用户稿。界面可诚实提示质检未完成。

## 四、最小可复用demo合同

一个纯状态模块 + 一个入口适配器，复用本地persist和session。命名/内部函数由实现者决定，不另造产品owner。demo身份必须 `LOCAL_REVIEW_ONLY`；生产adapter与local storage adapter不可静默互相fallback。

### 状态

- `workspaceKey`（纯样例范围）、schemaVersion；所有fixture权限明确 `FIXTURE_ONLY`。
- `draft:{title,markdown,baseVersionId,editRevision,selection,scroll,dirty}`。
- `versions:[{localId,workId,version,parentId,contentSha256,title,markdown,reason}]`，单链不可变；不用 `ART-` / `WORK-` 仿真服务端回执。
- `viewingVersionId`独立于draft/base；只读看旧版不会覆盖当前稿。
- `pending:{requestId,inputFingerprint,baseVersionId,editRevision,operationGeneration}`；无pending时不接受异步回执。
- `localReview:{versionId,contentSha256,verdict,notes,unknowns}`；新版本不继承旧版已审状态。
- `persistence`区分 unsaved/writing/local-readback-confirmed/failed；`productBinding:"UNBOUND"`恒明确。
- export选择绑定exact version/hash/format；预览当前草稿不能替换导出对象。

### 成功路径

1. 空白标题正文直接写作，无model、业务scope或来源前置。正文惰性纯文本预览，不运行HTML/JS。
2. 保存快照，在保存期间继续输入也保留。写入已生成的版本与journal，精确读回并schema/hash验证后才显示「已保存到本机审核副本」。响应只确认当时快照；若输入已更新，当前编辑仍未保存，不准清dirty。
3. 新修改提供与已保存父版的可读差异，修改原因必填；从当前head生成唯一子版。不允许branch。重复同请求不新增版本。
4. 旧版可选并只读查看；显式「把此内容用于新修订」才进入以当前head为基线的新草稿。撤销尚未保存的编辑只影响draft。
5. 换入口/返回保焦点和选区；关闭重开从有界、schema验证过的本地journal恢复draft与其真实base。显示恢复的是本机草稿而非服务端已保存。
6. 对一个已保存版本人工审阅；保存新版本后旧审阅留历史，新版显示未审。
7. 最小导出只做可真实产生/核对的UTF-8 md或txt，明确为本地审核文件；docx/pdf/xlsx列产品已存在接口但本demo未接，不造空文件/改后缀。可生成并核对字节/hash，然后明确「已准备」或真实handoff状态；普通浏览器下载触发不能证明磁盘落盘。

### 失败、取消、撤权

- 写失败/配额/读回不符/损坏journal：保内存稿、不推进confirmed head、不亮已保存；提供重试，损坏数据不能静默重置后报成功。
- 保存结果不确定：先核同request/本地journal；同ID重试不能重复创建。用户改内容必须新请求ID。
- 并发head改变：保原草稿，提示对比；重新读取head后由用户明确采用差异，不能自动覆盖或另存分支冒充顺序修订。
- 取消预览/关闭对话框无写入。取消尚未完成操作只使该generation不再更新当前UI；若写入已经发生，不能说“已撤回保存”。核读后给真实结果。未接服务端停止接口不显示“后端已停止”。
- fixture read撤销/切workspace：隐藏历史正文与审阅、清可访问动作，迟到回执失效；write撤销保用户当前未保存输入但禁保存；export单独撤销不妨碍合法阅读。是否可保缓存/明文恢复由实际host权限合同决定，demo不能把本地开关当服务端Permission。
- 导出期间版本/选择改变、权限撤回：按generation和精确版本绑定拒绝旧响应作为新版本成功；不得混出未保存编辑。
- 中英韩、emoji/组合字、RTL文本按原文保留。复用语言诊断但不要把diagnostic当翻译或语言理解。diff不要用UTF-16索引冒充生产Unicode codepoint edits；最小路径用完整title/markdown expected-value替换即可。

## 五、验证方案与完成界线

不以测试数量为目标。先一条正常旅程，再围绕它注入风险：

1. 空白稿→编辑→保存精确读回v1→修订v2→查看v1→关闭重开v2→人工审阅v2→导出v2字节。验证所有content/hash/parent，旧版不变。
2. 写入延迟时继续编辑：v1为旧快照，新草稿仍dirty；晚回执不能把新稿标saved。
3. 相同请求双击/重试、同ID不同body、head并发、旧版采用为新子版；版本数及父链断言。
4. storage set/get抛错、读回被篡改、坏schema/duplicate版本/断链/过长状态、未知引用。恢复须失败且保原输入。
5. 预览取消、保存前取消、写入后回执前取消；区分未执行/已持久化/未知，不假撤销。
6. read/write/export分别拒绝；scope切换和迟到响应隔离；撤权后不靠旧下载内容或cached UI继续展示受限正文。
7. 旧审阅不跟随新稿；未知事实保持未核，不以非空正文或人工点按钮产生质量PASS。
8. 内容含HTML/script、混合语言/emoji、长文；纯文本安全、精确原文往返、导出版本正确。
9. 最小DOM验证按钮/只读与编辑区域/保存状态/审阅/错误的实际接线，不能只测reducer。
10. 离线打包后独立浏览器验完整真实旅程，宽/窄布局、键盘Tab/Escape、焦点/选区、触屏、读屏、200%字号和减少动态。无此证据仍 `BROWSER_PENDING`。

验收只有本地review行为：`LOCAL_STATE_VERIFIED` / `LOCAL_STORAGE_READBACK_VERIFIED` / `BROWSER_PENDING|VERIFIED`分记；产品始终 `UNBOUND`，Flutter/原生/真实Permission/实际产品Evaluation保持未验。不得由本文件、43入口或测试PASS扩大成产品关闭声明。

## 六、working与冻结main差异（已逐文件字节比较）

冻结对照根：`recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/`（父任务标识 main4dab；本审计没有网络确认HEAD）。当前产品取 `lumenis_working_20261017/source/`。

- 字节相同：AGENTS、完整product-plan-full、Experience Constitution、SH-04 ScreenSpec、internal_pitch.py、evaluation/recorder.py、SH-04 screen.dart。因此独立Shared入口与现行规划不是此次working新增。
- `saved_work.py`不同：working扩原始附件custody格式、强化Importer producer验证、保private source原件附件、拆出 `_prepare_work_revision`、新增download_attachment。不得用冻结旧行号/旧附件支持描述working。
- `work_dependencies.py`：working存在，冻结缺失。当前 `experience_runtime.py:2748–2764`在revise发现该payload KEY时分派原dependency Owner，不能退到generic revise。无依赖payload的新建Shared report仍走generic合同。
- `experience_runtime.py`不同；本文采用working对应实际route读取，不把冻结主分支说成拥有新增dependency能力。
- 完整依赖成果传播不是此最小文稿demo范围；不要为了“跨流程”随便植入依赖metadata，泛用接口不会授予签名dependency语义。

本文件是独立审核建议及接入规格，不是产品规则、派工、修改或运行授权。

### 补核：完整替换、Unicode与导出校验的实际边界

- `saved_work.py:961–1001` `_apply_work_edits`只接受两种精确字段集合：`{pointer,expected,value}`（完整标量替换）或`{pointer,start,end,expected,replacement}`（原父字符串范围替换）。1–100 edits，同pointer的全替换不能重复或混合range；range同起点/交叠拒绝。`/title`、`/markdown`均允许完整替换；服务端先比较完整expected值，不匹配即 `WORK_EDIT_VALUE_CHANGED`。
- 当前 `lumenis_core_client.dart:1090–1110`实际使用title/markdown完整替换；最小demo应沿此合同，**不需要实现range协议才能支持局部可见diff**。可见diff与正式提交payload分层。
- 如果以后接范围编辑：`selectionStart/selectionEnd`是JS UTF-16 code units，Python Owner range是Unicode code points，必须从精确父字符串计算转换；不能在代理对中间截断，也不能把grapheme索引直接当codepoint。用户可见操作按字素保护组合字、ZWJ family emoji、旗帜/肤色符；提交前仍比对原父substring。保原文不做NFC/NFKC自动归一化，不能合并视觉相同但字节不同的文本。
- 导出服务端确实发出 `X-Source-Artifact-ID`、`X-Content-SHA256`；当前Flutter `lumenis_core_client.dart:1148–1180`检查HTTP状态、MIME和nonempty bytes，没有在此函数核对上述响应头/hash。因此“exact header/hash validation”是建议的demo/后续adapter验收项，不能描述为当前Flutter已完成。当前函数返回filename由请求artifactId和format构成，文件名本身不证实返回字节对应精确版本。
