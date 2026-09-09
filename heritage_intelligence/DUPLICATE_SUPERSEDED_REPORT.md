# D. Duplicate & Superseded Report

## 重复事实

- 精确重复：4,530 组、5,760 个附加路径版本；按 Git Blob 判定。
- 规范化文本重复：9 组、9 个附加 Blob；只消除格式差异后内容相同。
- 语义近似：376 个机器候选；尚未等同为重复，不删除、不覆盖。
- Korean 分支：40 个名称只对应 3 个尖端提交，不能以 `finalN` 名称计作独立成果。

## 已确认的替代/保留关系

| Historical Asset | Decision | Reason |
|---|---|---|
| `xujing-i18n.js` | SUPERSEDED / REFERENCE_ONLY | 当前 i18n 与正式命名已变化；仍需检查独有 key |
| Fansub fork Blob `e8bd07...` | MERGE KNOWLEDGE | 与当前版本近似，保留其独有平台范围差异，不覆盖当前文件 |
| Command ADR-002 old three-repo allowlist | SUPERSEDED | 当前审计范围和四仓边界已演进 |
| Command ADR-004 cloud-first/Ollama-deferred direction | SUPERSEDED | 当前为 Provider-Agnostic + Local Fallback，红线保持 AI 不拥有真相 |
| 旧 CTH=广州太古汇产品定义 | SUPERSEDED | 当前 CTH 为 Subject-first 商业运营，广州太古汇只是 Subject Profile |
| 旧 ZBMP hidden-layer 定义 | SUPERSEDED | 当前 BMP 是正式 Brand-first 产品线 |

禁止删除任何对应历史文件或分支。替代关系只影响当前决策优先级。
