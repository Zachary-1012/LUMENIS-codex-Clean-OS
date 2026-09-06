# LUMENIS Identity / Delegation Production Boundary V1.0

**Status:** ACTIVE / PRODUCTION GOVERNANCE BASELINE  
**Positioning:** ZBC Production Core 的 Agent Delegation / Identity 执行边界  
**Authority:** ZBC 保持 Production Truth 最终所有权

## 1. Purpose

本文件将 OSAI 的 Identity / Delegation 能力正式接入 ZBC 的生产治理边界。

核心原则：

> Agent 可以被用户授权执行，但 Agent 永远不能因为“代表用户”而自动获得用户在生产系统中的全部权限。

## 2. Canonical Execution Chain

```text
User
→ Delegation
→ Agent Identity
→ Skill Identity
→ Tool / API Identity
→ Production Permission Gate
→ Execution
→ Audit / Evidence
```

ZBC 是最终生产执行方。任何来自 OSAI 的身份、权限、Scope、Intent 或 Token 都必须经过 ZBC 本地 Production Policy 再决定是否执行。

## 3. Effective Permission

生产侧有效权限必须收敛：

```text
Effective Production Permission
= Delegated Permission
∩ Agent Permission
∩ Skill Permission
∩ Tool Permission
∩ ZBC Production Policy
∩ Resource Scope
∩ Runtime State
```

**禁止权限扩大。**

特别禁止：

```text
Agent Token = User Full Access
Agent Identity = User Identity
AI Result = Production Authorization
```

## 4. Production Truth Boundary

ZBC 继续拥有：

- Production Data；
- Collector / Source Adapter；
- SUBJECT_WORDS；
- SUBJECT_EXCLUDE_WORDS；
- `subject_hit()`；
- Risk / Domain Rules；
- Production API；
- Runtime / Health / Recovery；
- Report / Export Truth。

Identity / Delegation 层不得改变这些 Production Truth 的权威归属。

## 5. OSAI → ZBC Contract Direction

OSAI 提供：

```text
identity
agent_identity
skill_identity
tool_identity
delegation_id
workflow_id
intent
scope
permissions
issued_at / expires_at
trace / audit references
```

ZBC 必须自行验证：

```text
identity validity
permission
scope
resource ownership
expiry
revocation
runtime policy
production risk policy
```

OSAI 的“允许”不是 ZBC 的最终“允许”。

## 6. Token / OBO Evolution

后续 Token / OBO 层只能作为安全的授权上下文传递机制：

```text
Identity Chain
      ↓
Delegation Contract
      ↓
Signed Token / Context
      ↓
ZBC Verification
      ↓
Production Permission Gate
      ↓
Execution
```

不得通过 JWT / OBO 字段的存在本身宣称“已完成生产级 OBO”。真正上线前必须完成签名验证、Audience 校验、Expiry、Revocation、Replay Protection、Key Rotation、失败闭环与安全测试。

## 7. Audit Requirement

生产执行必须可以追溯：

```text
User
→ Delegation ID
→ Agent
→ Skill
→ Tool/API
→ Production Action
→ Resource
→ Permission Decision
→ Result
→ Timestamp
→ Evidence
```

高风险或被拒绝的请求同样必须留痕。

## 8. Security Boundary

当发生以下任一情况时，ZBC 必须拒绝执行：

- Delegation 不存在或已过期；
- Delegation 已撤销；
- Permission 不足；
- Scope 越界；
- Resource 不属于授权范围；
- Token / Context 无法验证；
- Replay / Nonce 风险；
- Production Risk Policy 拒绝；
- Collector / Platform 安全限制要求停止；
- Runtime 状态不允许执行。

拒绝必须形成 Audit / Evidence，而不是静默失败。

## 9. Compatibility / Independence

ZBC 不绑定 Microsoft Entra、某一云厂商或某一 Token 服务商。

可以兼容标准协议，但生产侧必须保留自己的 Permission Gate、Policy、Audit 与 Runtime Boundary。

## 10. Acceptance Criteria

Identity / Delegation 与生产融合完成的必要条件：

1. Delegation 与 Impersonation 明确分离；
2. 权限只能收敛；
3. Scope / Intent / Expiry / Revocation 可验证；
4. Production Permission Gate 为最终裁决点；
5. 所有生产执行可完整归因；
6. Token/OBO 通过独立安全测试后才能进入生产状态；
7. 不影响现有 Production Truth 与确定性业务规则；
8. 不引入对单一云身份系统的硬依赖；
9. 所有上线结论必须由源码 + 测试 + Evidence + Audit 共同证明。

## 11. Status

**ACTIVE — PRODUCTION BOUNDARY DEFINED**

当前状态：OSAI 已具备 Identity + Delegation 架构与基础集成；ZBC 已建立对应的生产边界规范。

**Token-level OBO Exchange 仍属于下一阶段实现，不得标记为已完成。**
