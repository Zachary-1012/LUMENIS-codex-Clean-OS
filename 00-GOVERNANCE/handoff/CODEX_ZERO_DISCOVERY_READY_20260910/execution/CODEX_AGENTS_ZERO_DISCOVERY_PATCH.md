# CODEX_AGENTS_ZERO_DISCOVERY_PATCH.md (提案;不在main直接改,由Codex在handoff分支对应ticket应用)
generated 2026-09-10 21:00:25

安全原则不变,新增最高优先规则:
IF CODEX_HANDOFF_FREEZE matches baseline (FREEZE_MATCH=YES):
1. DO NOT repeat full-repository discovery. 2. DO NOT reread all governance files.
3. Read only: AGENTS.md / CODEX_START_HERE.md / CODEX_RESUME_STATE.json / current ticket pack / 该票引用的精确evidence与source symbol。
4. Expand context only when BLOCKED_BY_MISSING_EVIDENCE=YES. 5. 每次扩展记录 reason/file/symbol/expected_evidence。
旧 "AUDIT CURRENT TRUTH" 在Freeze命中时 = VERIFY CURRENT TICKET TRUTH + DRIFT ONLY,不是FULL REPOSITORY RE-AUDIT。
Freeze不匹配时只算 CODEX_DRIFT_DELTA 漂移范围,不重建全量事实地图。
