# 序境-Core · OWASP Agentic Top 10 安全对照审计（IC-035）

> 日期：2026-09-04
> 状态：AUDIT-DONE（对照盘点，不改生产；GAP 待 Contract 后再实施）
> 依据：CONTRACT_IC035_044_048_20260904.md §一（Cycle Y）
> 方法：基于真实源码逐项对照，标注现有覆盖 / GAP / 建议；不新建重复能力。

---

## 一、分层安全架构对照

| 安全层 | 现有实现（真实源码） | 覆盖 |
|---|---|---|
| 输入护栏 | `agent_security.sanitize_input` + `is_instruction_attempt`（Prompt Injection 分层防御、ToolLeak、蜜罐动作） | ✅ 已覆盖 |
| 身份权限 | `kos_execution.py` HCG 状态机（AI_GENERATED→HUMAN_REVIEW→APPROVED→EXECUTING）+ `compliance_gate.py`（BLOCK/REVIEW/PASS） | ✅ 已覆盖 |
| 执行沙箱 | `system_guardian.py`（异常捕获/健康检查/自动恢复）+ `security_scanner.py`（文件完整性/恶意代码/敏感信息） | ✅ 已覆盖 |
| 输出护栏 | `agent_security.filter_output` + `data_quality_gate.py`（write-time 校验，422 拒绝坏记录） | ✅ 已覆盖 |
| 可观测审计 | `ai_channel.py`（重试/熔断/心跳/健康快照）+ `security_scanner`（篡改检测） | ✅ 已覆盖 |

**结论：现有安全层已覆盖 OWASP Agentic 分层架构全部五层，无需新建重复能力。**

---

## 二、OWASP Agentic Top 10 对照

> 注：以下为公开安全领域常见 Agentic 风险类别（OWASP Agentic Top 10 体系），对照现有实现逐项盘点。GAP 均为"建议级"，不阻塞生产。

| # | 风险类别 | 现有覆盖 | 判定 |
|---|---|---|---|
| 1 | 提示注入（Prompt Injection） | `agent_security`（is_instruction_attempt/sanitize_input） | ✅ 已覆盖 |
| 2 | 不受信数据导致代理滥用 | `agent_security.validate_tool_call`（工具调用校验） | ✅ 已覆盖 |
| 3 | 权限提升/越权 | HCG 状态机 + `compliance_gate` | ✅ 已覆盖 |
| 4 | 上下文中毒/历史污染 | 外部内容不可信原则（红线）+ 输入消毒 | ✅ 已覆盖（原则级） |
| 5 | 工具选择失配/工具幻觉 | `validate_tool_call` + capability registry | ✅ 已覆盖 |
| 6 | 过度授权 Agent 动作 | HCG GATED_ACTIONS（对外动作必须人工） | ✅ 已覆盖 |
| 7 | 记忆中毒/长期记忆污染 | 个人业务资料只存本地不上线（红线） | ✅ 已覆盖（原则级） |
| 8 | 逻辑漏洞（Agent 目标欺骗） | 外部内容不可信 + 多法域裁决（compliance_gate） | ⚠️ 建议加强（见 GAP-1） |
| 9 | 供应链漏洞（依赖/第三方） | 第三方代码 License/安全审查（红线） | ⚠️ 建议加强（见 GAP-2） |
| 10 | 数据泄露/敏感信息外泄 | `security_scanner`（敏感信息检测）+ Basic Auth | ✅ 已覆盖 |

---

## 三、GAP 清单（建议级，待 Contract）

| GAP ID | 描述 | 建议 | 优先级 |
|---|---|---|---|
| GAP-1 | Agent 目标欺骗/逻辑漏洞的**结构化推理审计**未独立化 | 将 `security_audit` 的审计结论结构化输出（覆盖/缺口/建议）并纳入 audit 记录 | P2 |
| GAP-2 | 第三方依赖的**清单化 License/版本审计**未沉淀为可执行清单 | 建立 `DEPENDENCY_AUDIT.md`（记录生产依赖 License/版本/来源） | P2 |

**本轮不实施 GAP**（不破坏生产、不建重复能力）；仅登记审计结论。

---

## 四、审计结论

- 序境-Core 现有安全层已覆盖 OWASP Agentic 分层架构**五层全部** + Top 10 **风险类别 8 项**（2 项为原则级，2 项 GAP 建议级）。
- **无需新建重复安全能力**；HCG 人工门控与 ai_channel 权限边界符合设计。
- 后续 GAP-1/GAP-2 若实施，须先 Contract→Test→Evidence→Audit。

| 真实状态声明 | 本审计基于真实源码对照；GAP 未实施，不标记为已完成安全增强 |
