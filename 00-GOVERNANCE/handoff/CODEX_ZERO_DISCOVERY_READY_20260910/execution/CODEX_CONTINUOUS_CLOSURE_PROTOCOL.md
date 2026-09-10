# CODEX_CONTINUOUS_CLOSURE_PROTOCOL
generated 2026-09-10 21:04:29

Codex 默认自动连续执行,无真实BLOCKER不得逐票等待用户确认:
TICKET → IMPLEMENT → SCOPED TEST(Level A/B) → NEIGHBOUR REGRESSION(Level C) → REQUIRED RUNTIME/E2E → EVIDENCE → SCOPE/PROTECTED-ASSET CHECK → ONE-PURPOSE COMMIT(handoff分支) → UPDATE RESUME_STATE/LEDGER → NEXT EXECUTABLE TICKET(按DAG/PARALLEL_MAP)。

仅以下情况停止并输出 BLOCKED(exact blocker / affected ticket / minimum action),不补假设:
1. 需要用户业务决策  2. 需要真实凭据  3. 需要不可逆生产操作  4. 需要生产数据库写入授权
5. 发现事实冲突无法安全判定  6. rollback 不可保证  7. protected asset 可能受损

每票输出遵守 CODEX_REPORTING_PROTOCOL(极简);新失败按 CODEX_FAILURE_FINGERPRINT 标 NEW_REGRESSION 并最小增量分析。
