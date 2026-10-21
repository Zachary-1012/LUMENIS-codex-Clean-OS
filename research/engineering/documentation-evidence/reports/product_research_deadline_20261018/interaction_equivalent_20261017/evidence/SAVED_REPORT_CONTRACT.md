# 独立 Shared 文稿连续旅程：本地状态与持久化合同

日期：2026-10-17 UTC。范围仅 `review_working/src/saved-report.mjs`、`tests/saved-report.test.mjs` 与本文件。产品源码只读；没有产品、数据库、运行环境、服务、浏览器、部署或上传修改。

## 依据与边界

已完整读取 `evidence/NEXT_JOURNEY_CONTRACT.md`（含最后补核）、只读产品 `AGENTS.md`、`contracts/experience/screen-specifications/SH-04.md`，以及当前 `saved_work.py` 的 save/revision 合同（676–832、961–1051）。这是一个作者原文连续旅程的独立审核实现，不是另一套产品 SavedWork Owner。

- 恒定 `identity=LOCAL_REVIEW_ONLY`、`productBinding=UNBOUND`；所有权限开关有 `provenance=FIXTURE_ONLY`。
- 本地 ID 以 `local-report-` / `local-work-` 开头，不生成 ART-/WORK- 服务端收据。
- 没有 CTH/BMP/Task 前置，也不发送任何真实 API；用户文字不构成 Canonical 外部事实。
- 人工审阅 `LOCAL_HUMAN_REVIEW_ONLY` 绑定精确版本和 Artifact 字节 hash。没有产品 Evaluation、事实认证、发布批准、专业提案质量 PASS 或 J4 关闭。
- 正式 Owner 的保存还要求 DATA_EXPORT effect 与 Shared write authorization。demo 的 `export` 仅指本地准备导出字节的 fixture 权限，不能映射为该真实 effect；本地 export=false 时仍可本地保存，不可由此推断生产权限行为。

## 稳定导出与接线

`createSavedReportController({storage, sha256, workspaceKey, permissions, onChange})`

- `storage` 显式注入 `getItem(key)` / `setItem(key,value)`，可以同步或 Promise；禁止静默 backend fallback。
- `sha256(Uint8Array)` 可注入，返回64位小写hex；默认 `browserReportSha256` 使用 WebCrypto，缺失时明确失败。
- `workspaceKey` 只允许1–80位字母、数字、下划线、短横线，纯样例范围。
- `permissions` 必须完整 `{read:boolean,write:boolean,export:boolean}`，默认全开；只是假数据开关。
- `onChange(state)` 获得隔离的 JSON 副本。`subscribe(listener)`立即发送一次state，返回unsubscribe，适合view mount/unmount保留controller。渲染回调抛错不能改变持久化收据。
- `state()` 返回只读意义的副本：`draft, versions, viewingVersionId, reviews, pending, persistence, error, journalDirty, generation, lastExport, confirmedHeadId`。读取撤权时隐藏正文、版本、审阅和导出。

同步动作：

- `edit({title?,markdown?,selection?,scroll?})` 保原文，不做Unicode规范化。selection是显式 `unit:'utf16'` 的 textarea UI选区，不作为Owner范围编辑；direction为 none/forward/backward。
- `viewVersion(localId)` 只切只读查看，不替换草稿。
- `adoptVersion(localId)` 明确把该旧版内容放进草稿，但父版始终为当前head。
- `discardDraft()` 只把草稿恢复到当前head，不删历史，不写存储。
- `reviewVersion({versionId,verdict:'reviewed'|'needs-work',notes,unknowns:[]})` 添加本地人工意见；返回 `unsaved-local-review`，需随后 `checkpoint()`。
- `cancel()` 使当前generation失效；结果说明持久写入没有被撤销。没有pending时不声称停止后台。
- `setPermissions(fullObject)` / `switchWorkspace(key)` 隔离迟到结果；切scope不自动写入或迁移原内容。
- `storageKey()` 供测试/host诊断，不必显示给用户。

异步动作均返回 `{ok:true,...}` 或 `{ok:false,code,...}`：

- `save({requestId,reason})` 捕获快照，生成唯一顺序子版，验证完整本地journal及其hash，精确写后读回才推进confirmed head。修订理由非空；初版可空。重复同ID同原输入回放原版本；不同输入拒绝。保存期间继续编辑不会清新稿dirty。
- `checkpoint()` 持久化当前草稿、选区、scroll、历史与审阅；不生成新版本，也不等同保存文稿。成功为 `local-journal-readback-confirmed`。调用前需无pending；未完成时继续编辑，则 `journalDirty=true`，需再次checkpoint。
- `restore()` 显式读回并替换本机journal；期间有本地更改则拒绝覆盖。损坏/不存在/拒绝访问不会抹掉当前稿。成功只说明本地恢复。
- `restore({preserveDraft:true})` 是**用户明确协调冲突**的动作：读最新版本/审阅，同时保当前稿并以最新head为新基线。view必须给明确动作，不得收到HEAD_CONFLICT就自动调用。后续改用新的requestId。
- `prepareExport({versionId,format:'md'|'txt'})` 重新读持久版本并验hash，拒绝选择变化/权限撤回的旧响应。返回 `bytes:Uint8Array, bytesSha256, contentSha256, byteLength, mime, filename, status:'bytes-prepared', diskDelivery:'NOT_VERIFIED'`。两种格式均逐字保留Markdown正文（txt不去标记）；title保存在Artifact中，不擅自拼入导出正文。未保存草稿不混入导出。

其他模块导出：`SAVED_REPORT_LIMITS`、`validateSavedReportJournal(raw,workspaceKey,sha256)`、`savedReportArtifactBytes(version)`、`savedReportLocalEdits(parent,draft)`、`browserReportSha256`、`createLockedReportStorage(storage,locks)`。

`savedReportLocalEdits`仅生成本地比较数据：`binding:LOCAL_REVIEW_ONLY`、`localParentId`、`localParentSha256`和两个完整 `/title`、`/markdown` expected→value edits。故意没有 `expected_sha256`，不能直接成为生产revise请求。旧名 `savedReportOwnerEdits` 已移除，避免误把自定义local-review文档hash当生产Artifact SHA；生产形状或仅含hash的父对象被拒绝。正式adapter必须另从已授权读取/核实的生产父Artifact及其原字段构造真实Owner请求，不能转换或复用localParentSha256。payload的 draft_digest 也不是这两个hash。

## 持久化与并发

本地journal单链不可分支。版本/hash/引用/唯一请求ID/父hash/dirty真值/schema字段集合严格校验。标题300 Unicode codepoints、正文262144 UTF-8字节、理由4000 codepoints、64版本、128审阅、总journal 2MiB。无效代理项拒绝，而非静默用U+FFFD损失原文。历史不可变，当前状态副本不能篡改内部版本。

裸storage的串行锁只覆盖同realm内共享**同一storage对象**的合作controller；状态显式标注 `SAME_STORAGE_OBJECT_ONLY`，不能宣称跨标签页原子性。浏览器建议显式用 `createLockedReportStorage(localStorage,navigator.locks)`：缺少host锁时写入 `EXCLUSIVE_LOCK_UNAVAILABLE`，不得静默退化。host锁的正确实现及真实浏览器跨标签竞争仍需浏览器验证。

每次写入比较当前raw与此前已观察的journal；同head的另一个编辑器改了草稿或审阅也拒绝覆盖。并发head变化保原稿与confirmed head；显式恢复/协调后再修订。写入前最后检查generation和fixture权限。异步storage在写入调用发出后才完成的效果无法撤销：此时取消返回失效与真实已写读回/未知状态，后续明确恢复检查结果。

写失败、配额、读失败、坏schema、错hash、精确读回不符均不推进内存confirmed head。写入结果未知时，同ID重试先寻找持久版本，避免重复创建。若该版本之后又有其他人推进head，拒绝自动重定基线。

view应在离开入口但同会话返回时保留controller实例；关闭/重载恢复必须通过checkpoint和restore。保存期间编辑仍需在pending结束后checkpoint新稿。纯内存保留不能称关闭浏览器恢复。已经交给外部调用者的导出bytes不能被JavaScript远程收回；host应在权限变化时清理预览/对象URL，且不得复用旧结果宣布新导出成功。

## 实际验证

命令：`node --check src/saved-report.mjs`；`node --test tests/saved-report.test.mjs`。

首次23测试：22通过、1失败，发现首版同ID回放被“当前有head就必填修订原因”误挡。已修为按原请求父版判定原因要求；保留该回归。随后强化同head草稿/审阅并发与旧请求回放冲突，当前28测试全部通过，无跳过。

覆盖完整作者旅程、混合语言/组合字/ZWJ emoji/RTL/CRLF/script原文、不可变顺序版本、旧版查看/采用、关闭后journal恢复、hash绑定人工审阅、精确字节导出、保存中输入、双击/请求重用、并发head与journal冲突、存储失败/读回被改、损坏schema/hash/引用/超长输入、取消前后效果区别、scope切换、分别撤销read/write/export、迟到export与restore、snapshot不可外改、缺host锁写入失败、立即订阅/退订/渲染错误隔离。

验证层级：`LOCAL_STATE_VERIFIED`；注入测试存储下 `LOCAL_STORAGE_READBACK_VERIFIED`。这里不是实际浏览器LocalStorage可靠性或关闭浏览器E2E证明。DOM接线、浏览器完整旅程、宽窄布局、键盘/触屏/读屏、200%文字、减弱动态、真实Web Locks竞争、设备磁盘交付均未在本子任务运行，保持 `BROWSER_PENDING`。产品权限、API、Flutter/原生、Evaluation、部署均 `UNBOUND/NOT_RUN`。

父任务复审修正：27通过后发现旧helper命名和expected_sha256字段仍可能被误接生产，虽文字注明UNBOUND仍不够。已改为纯local比较输出，移除生产请求字段及旧导出名，并新增生产形状/仅hash父对象拒绝反例；28项全部通过。
