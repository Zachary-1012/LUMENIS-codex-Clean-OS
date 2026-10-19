# Shared Intelligence Consumer Boundary V1

> Status: Active local consumer boundary · reconciled 2026-10-18
> Exchange identity: lumenis-ggi-cross-product 1.1.0, fingerprint 68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f

## Purpose

序境 remains an independently runnable production product. Shared intelligence contribution to 序蕴 / LUMENIS Intelligence is optional and must never affect normal production operation.

## Independence guarantee

序境 must continue to collect, normalize, analyze, apply subject/business rules, calculate risk, generate reports and operate when LUMENIS Intelligence is unavailable, degraded, upgrading, rejecting contributions, or offline.

LUMENIS Intelligence must never become a synchronous dependency of the production critical path.

## Contribution flow

```text
Existing LUMENIS lifecycle
 → existing evidence / evaluation / human feedback
 → contribution candidate
 → local outbox
 → asynchronous contract export
 → LUMENIS Intelligence validation
```

The existing production data pipeline and business rules remain authoritative.

## Hard boundaries

- Do not replace or bypass existing subject/business rules.
- Do not move production truth into LUMENIS Intelligence.
- Do not share the production database.
- Do not add a required runtime dependency on LUMENIS Intelligence.
- Do not place credentials, cookies, sessions or unrestricted sensitive records in contribution payloads.
- Do not let LUMENIS Intelligence write LUMENIS production truth directly.
- Do not allow contribution retries to block collection, analysis, reporting or other primary operations.

## Failure isolation

```text
Contribution export
 ├── local staging success → EXPORTED + artifact hash/lineage (not ACK)
 ├── authenticated, artifact-bound receiver receipt → ACKNOWLEDGED (not adoption)
 ├── timeout → bounded retry
 ├── unavailable → local queue / later retry
 └── rejected → local rejection record

Primary product operation → continues in every branch
```

## Returned intelligence

LUMENIS Intelligence may return evaluation, skill, memory or learning candidates. LUMENIS treats them as advisory artifacts until they pass the existing LUMENIS contract, permission, regression and release gates.

## Adoption gate

Exchange gate: `RECEIVE → VERIFY → EVALUATE → ADAPT → TEST → LOCAL_RELEASE`.
Local release additionally requires the existing Evidence/Audit/release proof; these local checks do not replace or rename exchange states.

No returned asset may silently change production rules or production truth.

## P0 implementation constraint

Implement the adapter/outbox boundary within existing Shared Learning lifecycle owners. Do not rewrite the existing collection, subject filter, event aggregation, risk or reporting pipeline to introduce shared intelligence.

## Acceptance criteria

1. LUMENIS passes its existing regression tests with LUMENIS Intelligence disabled.
2. Contribution export failure cannot fail the primary request/task.
3. Production database remains local to LUMENIS.
4. Sensitive payload minimization is enforced before export.
5. Contribution lineage is traceable.
6. Returned intelligence cannot bypass LUMENIS release gates.

## Current source adoption and delivery status

[Current registry](../../00-GOVERNANCE/CROSS-REPO-CANONICAL-REGISTRY-V1.md) and its single machine contract own cross-runtime exchange. [Local source adoption](../../00-GOVERNANCE/LUMENIS-SOURCE-ADOPTION-V1.json) records the PO-authorized source-level absorption into existing LUMENIS owners, not another runtime contract or permission to share production data. External repositories remain observed 1.1.0 and were not modified by this batch. Historical OSAI/ZBC/GGI identifiers remain only for provenance or actual compatibility.

Transport requires current actor/workspace/project/source rights, minimized data, exact contract version/fingerprint, idempotency and authenticated artifact-bound receipts. Up to three retries then DEAD_LETTER; an explicit reviewed requeue does not admit knowledge. Source/rights revocation blocks reuse and export. Receipts do not grant actor identity, approval, production acceptance or learning promotion. Current integration is IN_PROGRESS; local staging is not external delivery, and no external delivery is authorized by this document.

### 已交付学习与本地运输服务合同（2026-10-18，真实session HTTP已验证，最终合并与前端待验）

服务唯一路径`lumenis/shared/learning/contribution.py`：`create_candidate(job_id,review_id,actor,actor_id,expected_scope,submission_id,authorize)`；业务来源使用`create_business_candidate`并增加`work_id/expected_business_revision`；`get_candidate`、`transition_candidate`、`enqueue_candidate`、`get_outbox/list_outbox`、`transition_outbox`及`receive_local_contribution`均沿现有Shared Learning和签名Evidence持久化，非第二学习库。公共route已由experience_runtime.research_learning注册，准确HTTP合同见本节续接；前端仍需本地实际接线验证。

候选`RAW→REVIEWED→VALIDATED→ADOPTED`仅`local_reference_only`，不是规则激活、模型训练或Production Truth；`withdraw`进入WITHDRAWN，`restore`回REVIEWED须重新批准，`reject`独立终态。变更带整数`expected_revision`、`submission_id`和明确notes；不能与SourceBrief opaque64 CAS混用。审批绑定`approval_resource(object_id,action,revision)`及当前scope，不复用别的对象/动作/版本审批。

运输`PENDING→EXPORTED`只表示最小envelope在真实signed Evidence内持久化并读回；显示artifact hash/版本，不能提示已发送。三次失败DEAD_LETTER；requeue须精确批准并清旧staging/receipt。外部`receipt`返回`LEARNING_RECEIVER_NOT_BOUND`，不得在UI伪造外部ACK。仅接收方为本仓且精确DATA_IMPORT获准时，`receive_local_contribution`核staged/hash/1.1.0/current rights后生成真实本地receipt及ACK；`remote_delivery_proven=false`明确保留。本地接收不等于跨仓互通。

Shared候选只允许本仓receiver；领域候选默认Intelligence身份仍不等于实际外发。license UNKNOWN、commercial/training/external_delivery_authorized=false保留，未知资料权利不会因review/adopt/ACK变成授权。界面把候选审阅、运输状态、接收方与是否真实外发分别呈现；离线/撤权不破坏原报告，错误不泄漏prompt/原文/凭据。Shared精确审批及公共HTTP已有真实session全生命周期、跨用户/撤权/CAS/源删除反例证据，已到本仓local ACK；最终合并门禁及本地四表面完整用户旅程仍待验。

### 已验证公共学习HTTP与本仓回执

`experience_runtime.research_learning`已注册统一SourceBrief前缀下GET/POST `/learning/<kind>`、GET `/learning/<kind>/<object_id>`、POST `/learning/<kind>/<object_id>/<operation>`，kind严格为candidates/outbox。候选创建严格为`job_id/review_id/submission_id`或业务`work_id/expected_business_revision/job_id/submission_id`；review/validate/adopt/withdraw/restore/reject为`expected_revision/submission_id/notes`；enqueue为`expected_revision/submission_id/receiver`；outbox stage/fail/requeue/receive_local为`expected_revision/submission_id`。不接收任意外部receipt body。

CONFIG_MODIFY候选变更/stage/requeue和DATA_IMPORT本仓receive_local使用原Permission精确单次token与commit lease；approval issuer必须是当前actor，前后重查来源/对象/版本并跨SQLite commit持有租约。真实session的Shared上传→研究→独立反馈/评价→候选→adopt/withdraw/restore→stage→local ACK→重开已验证，另一用户和会话删除拒绝。业务`read_learning_material`核当前精确revision、已记录评价及原始SourceUse后进入同一候选链。

本仓ACK由实际owner验证saved envelope/contract/hash/lineage并原子持久receipt，仅证明本地接收；`remote_delivery_proven=false`。外部receiver/delivery adapter仍未绑定，`LEARNING_RECEIVER_NOT_BOUND`保留，无外发/训练/部署/商业使用许可。已ADOPTED内容仅进入`build_reviewed_research_context`的untrusted reference context，不额外调用模型、不成为指令或Production Truth。最终全合并门禁与本地四表面验收另计。
