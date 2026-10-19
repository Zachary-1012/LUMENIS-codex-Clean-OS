# LUMENIS API Owner Map

> Status: CURRENT IMPLEMENTATION MAP  
> Scope: 序境 / LUMENIS only. This map describes route families and their business owners; it is not a replacement for route-level authorization or runtime acceptance.

## Product domains

| Domain | Product meaning | Route family | Data and behavior owner |
| --- | --- | --- | --- |
| CTH | 序境·商业运营; selected Subject context | `/api/cth/` | CTH capability through canonical database, evidence, evaluation, learning and reporting owners |
| BMP (`ZBMP` stable API identifier) | 序境·品牌市场; selected Brand focus | `/api/zbmp/` | BMP capability through canonical database, evidence, evaluation, learning and reporting owners |
| Shared | Cross-domain reusable services; not a third product | `/api/skills/`, `/api/content/`, `/api/v2/report-center/` and shared service routes | `lumenis/shared/` owners; each request still enforces actor and domain scope |
| SYSTEM | Accounts, permissions, runtime, collection, AI gateway and operations | `/api/system/` and SYSTEM service routes | `lumenis/system/` owners |

CTH is Subject-first. BMP is Brand/Market-first. A selected context may scope a request, but cannot rewrite canonical ownership or move business facts between domains. Shared services do not make CTH and BMP interchangeable.

## Deprecated compatibility routes

Existing route names may remain as compatibility façades while callers migrate. Compatibility does not grant a retired route independent data, permission or execution ownership. The response deprecation header policy is maintained in `app.py` and must be tested alongside the canonical route. Remove a compatibility route only after caller inventory, equivalent behavior, authorization and regression acceptance are recorded.

## Authorization and acceptance

- Every business read and write must be authorized for the authenticated actor, product domain, module and requested action.
- SYSTEM authorization, approvals, Evidence and side-effect controls remain separate canonical owners.
- A route being registered or returning a ViewModel does not prove field-level owner, scope, permission or lineage acceptance.
- Route changes require contract tests for success, denied scope, missing data, failure, and the documented side-effect boundary.
- The Experience binding registry and per-screen specifications record callable, owner, actor, scope, permissions, Evidence and acceptance evidence for the future desktop/mobile App.

## 2026-10-18 完整研究能力源级采用接续（IN_PROGRESS）

完整逐项映射归[LUMENIS-SOURCE-ADOPTION-V1.json](LUMENIS-SOURCE-ADOPTION-V1.json)，既有Owner不变。

| 责任 | 唯一实际接线路径 | 交付边界 |
|---|---|---|
| C5/C6 research/task/scope | `lumenis/shared/reporting/source_brief_job.py`, `source_brief_tasks.py`, `saved_work.py`, `lumenis/importer/documents.py`, `ai_task_engine.py`, `experience_runtime.py`, `lumenis_app_api.py` | 授权Shared workspace、来源、taxonomy、保存/重开/修订/取消恢复；公共route/schema单writer |
| C2 research | `agent_research/`、既有SYSTEM AI Gateway | 有来源的finding/hypothesis；AI可选，不造证据ID或事实 |
| C3 domain | `api_dual_domain.py::BusinessDecisionWorkflow`, `cth_cases.py`, `lumenis/shared/database/cth_cases.py` | 合法域内方案/内部选择/行动owner读回/未知结果/评价，CAS与原scope不变 |
| C2/C5 learning | `lumenis/shared/learning/{loop,memory,persistence,feedback,operations}.py` | 候选及最小化本地outbox；运输与admission分开，ACK非晋升，无自动外发 |
| F four surfaces | 原SH-01/02/04/05/06、AI-01/02/03、CTH-10、BMP-03/04合同 | 本地Codex/GrokBot真实接线；旧HTML仅研究输入，不复制坏路由、脚本、注入或虚假状态 |

API意图不要求照搬原路由；51项来源API全部映射，研究入口由`experience_runtime.py`原SourceBrief owner注册，业务决策仍归`lumenis_app_api.py`。裸user_id/approved_by不是主体，子对象必须验证task/source/version/actor/workspace/project及当前Permission。研究资料不覆盖Collector能力状态。已交付callable按真实源码和限定HTTP证据记录；未实际接线的UI保持OPEN，不能把文稿写成四表面实现成功。


### 已交付Shared研究接口接续（2026-10-18，有界HTTP证据已交付，最终合并门禁待核）

真实注册者为`experience_runtime.py`原SourceBrief owner。沿`/api/experience/reports/source-brief`使用：GET `/tasks?dimension&state&limit&cursor`、PATCH `/tasks/<id>`提交`{expected_revision,changes}`、POST `/tasks/<id>/cancel|restore`提交`{expected_revision}`、GET `/taxonomy?language=zh|en|ko`、GET `/references?kind&query&region&page&limit`、GET `/jobs?cursor&limit`、POST `/jobs/<id>/save`提交`{request_id,title}`。原start/generate/jobs详情/reviews/tasks详情/resume扩展合法Shared scope，不新挂GGI API命名空间。

Shared请求头`X-Lumenis-Workspace-Scope`为精确JSON `{"scope_kind":"shared_workspace","version":1}`，仍由服务器主体及当前workspace授权，不能传actor自授权。私有文档来源为`private_document`的ART-* ID；start接受`research:{dimension,regions,languages}`及`defer`以保可编辑pending草稿。返回`expected_revision`为opaque64 CAS，不将其当数字增量。Shared review是SavedWork ART-*，修订绑定`{parent_job_id,review_id}`；前端不可用别人的同ID或旧revision覆盖。

九维来自`agent_research/taxonomy.py`，36条历史参考来自`agent_research/reference_assets.json`；界面只展示其来源/日期/权利/未知，不把分类或种子计数当事实覆盖。当前源码已交付，A最终327、参考HTTP/service98、B跨域299及C真实session/localACK测试各按对应固定版本留证，不相加作为全合并结果；旧禁用控件仍需精确scope/route前端接线验收，真实四表面NOT_VERIFIED。

### 已交付学习与本地运输服务合同（2026-10-18，真实session HTTP已验证，最终合并与前端待验）

服务唯一路径`lumenis/shared/learning/contribution.py`：`create_candidate(job_id,review_id,actor,actor_id,expected_scope,submission_id,authorize)`；业务来源使用`create_business_candidate`并增加`work_id/expected_business_revision`；`get_candidate`、`transition_candidate`、`enqueue_candidate`、`get_outbox/list_outbox`、`transition_outbox`及`receive_local_contribution`均沿现有Shared Learning和签名Evidence持久化，非第二学习库。公共route已由experience_runtime.research_learning注册，准确HTTP合同见本节续接；前端仍需本地实际接线验证。

候选`RAW→REVIEWED→VALIDATED→ADOPTED`仅`local_reference_only`，不是规则激活、模型训练或Production Truth；`withdraw`进入WITHDRAWN，`restore`回REVIEWED须重新批准，`reject`独立终态。变更带整数`expected_revision`、`submission_id`和明确notes；不能与SourceBrief opaque64 CAS混用。审批绑定`approval_resource(object_id,action,revision)`及当前scope，不复用别的对象/动作/版本审批。

运输`PENDING→EXPORTED`只表示最小envelope在真实signed Evidence内持久化并读回；显示artifact hash/版本，不能提示已发送。三次失败DEAD_LETTER；requeue须精确批准并清旧staging/receipt。外部`receipt`返回`LEARNING_RECEIVER_NOT_BOUND`，不得在UI伪造外部ACK。仅接收方为本仓且精确DATA_IMPORT获准时，`receive_local_contribution`核staged/hash/1.1.0/current rights后生成真实本地receipt及ACK；`remote_delivery_proven=false`明确保留。本地接收不等于跨仓互通。

Shared候选只允许本仓receiver；领域候选默认Intelligence身份仍不等于实际外发。license UNKNOWN、commercial/training/external_delivery_authorized=false保留，未知资料权利不会因review/adopt/ACK变成授权。界面把候选审阅、运输状态、接收方与是否真实外发分别呈现；离线/撤权不破坏原报告，错误不泄漏prompt/原文/凭据。Shared精确审批及公共HTTP已有真实session全生命周期、跨用户/撤权/CAS/源删除反例证据，已到本仓local ACK；最终合并门禁及本地四表面完整用户旅程仍待验。

### 研究参考的实际版本化接口（2026-10-18最终Owner交接）

统一前缀`/api/experience/reports/source-brief`，均为序境Shared研究能力。POST `/references/match-rules`由`experience_runtime.research_match_rules`→`agent_research.reference_assets.match_rule_references`，严格body为`content`及可选`regions/industry/business/platform/as_of`；返回历史参考、日期/匹配依据与未知适用性，不提供合法/安全裁决。

GET/POST `/reference-work`由`research_reference_work`→`reference_work.list_reference_work/adopt_reference_asset`；采用body为`asset_id/request_id`及可选`edits`。GET/POST `/reference-work/<artifact_id>`由`research_reference_version`→`read_reference_work/revise_reference_work`；更新body为`request_id/expected_sha256/operation`及可选`edits`，operation为update/withdraw/restore。场景edits是用户声明的inputs/work/goal；新研究的`reference`绑定`artifact_id/sha256/work_id/version`，旧版本或撤回引用拒绝，不静默覆盖历史。场景→Task→Report→SavedWork、102版本/CAS/撤回下游拒与事务回滚已有隔离HTTP/service证据。

GET/POST `/reference-library`及GET `/reference-library/<int:evidence_id>`由`research_reference_library`→`intelligence_library_api.adopt_reference_library_asset/discover_reference_library_sources/read_reference_library_source`。POST同`asset_id/request_id/edits?`，签名binding与SavedWork同事务提交；RAW/REFERENCE、license UNKNOWN及原来源日期保留。更新/撤回使依赖旧task/report/saved result/library引用失效，新版须显式选用。前端显示版本与受影响状态、保留旧稿，禁止将102测试版本或36资料数当覆盖率或产品限制。

前端仍由本地Codex/GrokBot按原四表面职责实现并实测，以上证据未证明浏览器、桌面或iOS页面已构建。所有界面使用序境的研究/参考资料/版本/采用语义，GGI只在按需来源追溯显示。

### 已验证公共学习HTTP与本仓回执

`experience_runtime.research_learning`已注册统一SourceBrief前缀下GET/POST `/learning/<kind>`、GET `/learning/<kind>/<object_id>`、POST `/learning/<kind>/<object_id>/<operation>`，kind严格为candidates/outbox。候选创建严格为`job_id/review_id/submission_id`或业务`work_id/expected_business_revision/job_id/submission_id`；review/validate/adopt/withdraw/restore/reject为`expected_revision/submission_id/notes`；enqueue为`expected_revision/submission_id/receiver`；outbox stage/fail/requeue/receive_local为`expected_revision/submission_id`。不接收任意外部receipt body。

CONFIG_MODIFY候选变更/stage/requeue和DATA_IMPORT本仓receive_local使用原Permission精确单次token与commit lease；approval issuer必须是当前actor，前后重查来源/对象/版本并跨SQLite commit持有租约。真实session的Shared上传→研究→独立反馈/评价→候选→adopt/withdraw/restore→stage→local ACK→重开已验证，另一用户和会话删除拒绝。业务`read_learning_material`核当前精确revision、已记录评价及原始SourceUse后进入同一候选链。

本仓ACK由实际owner验证saved envelope/contract/hash/lineage并原子持久receipt，仅证明本地接收；`remote_delivery_proven=false`。外部receiver/delivery adapter仍未绑定，`LEARNING_RECEIVER_NOT_BOUND`保留，无外发/训练/部署/商业使用许可。已ADOPTED内容仅进入`build_reviewed_research_context`的untrusted reference context，不额外调用模型、不成为指令或Production Truth。最终全合并门禁与本地四表面验收另计。

### 维度汇总与真实假设复核（Owner与独立反例验证状态）

GET `/api/experience/reports/source-brief/tasks`的`result.summary`已由原`list_report_tasks`同一读快照返回九维/六task状态全范围聚合、多语标签和零填充；`result.total`仍是所选筛选总量，两者不混。跨actor/scope、WAL并发变化、撤权及未知持久维度/状态的有界HTTP测试已报告；succeeded只指任务成果，`business_outcome=NOT_ESTABLISHED`。

原`experience_runtime.research_hypothesis_review`已注册GET `/api/experience/reports/source-brief/jobs/<job_id>/hypotheses`及POST同前缀`/jobs/<job_id>/hypotheses/review`，POST严格为`hypothesis_id/disposition/rationale/evidence_refs/request_id/expected_revision`。`source_brief_job.get_hypothesis_review/write_hypothesis_review`保存真实同范围来源绑定的人审；disposition仅challenge/reject/reinstate。原摘录保留，challenge/reject从effective_findings/effective_hypotheses移除有效支持；reinstate只恢复未核验候选，不成为verified事实。debate_transcript只记录实际人工声明与source版本，不伪称独立专家或模型深研。

纯函数/service/真实session HTTP及独立反例已验证：A保存结果、派生报告、Shared源采用绑定最新`hypothesis_review={artifact_id,sha256,version,work_id}`；B签名prepare/adopt和C候选/evaluation/staged envelope均复核该引用，旧无review来源保持兼容。challenge/reject拒绝有效采用，reinstate产生新引用，不能复活旧批准。B返回`BUSINESS_WORK_RESEARCH_REVIEW_CHANGED`后须显式新adopt（`adoption.research_review_changed=true`）；C须真实新增操作者评价，再新建候选及审批，单换submission_id无效。页面显示原文、理由、来源范围/版本、历史、冲突后重新确认和未核状态，不把reinstate展示为事实认证。R04汇总basis为`persisted_task_state_same_sqlite_snapshot`，列表`snapshot_state`与实时worker校正`state`分开展示。完整PR门禁、前端构建及四表面仍待最终/本地验收，外部receiver未绑定。
