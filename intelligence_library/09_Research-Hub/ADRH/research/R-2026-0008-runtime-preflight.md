# R-2026-0008｜Hub Runtime Preflight（适配 DDC 已落地版）

## 研究问题
按 AI-D 工单 P0「Runtime Preflight 启动预检」，将 DDC 已落地的 `server/startup-preflight.js`（Node.js，13 项安全检查）适配到 Hub 的 Python 工具/研究运行时，建立 Hub 侧的启动完整性门禁。

## 事实审计
- DDC HEAD: `dd6a51f`（V0.5 Effective Rules + Supplement Protocol + Capabilities API，125 tests pass）
- DDC 实现: `server/startup-preflight.js`（112 行）+ `tests/startup-preflight.test.js`（3 测试）
- DDC 检查项: loopbackOnly / originPolicy / sourcePolicy / deniedCapabilitiesLocked / requiredModulesPresent / dangerousServerPatternsAbsent / githubAuditHttpsOnly / sensitiveFilteringPresent / runtimeIdentity / maxBodySize / rateLimit / protocolRegistry / effectiveRules
- Hub 无 HTTP server，是纯 Python 工具/研究仓库；DDC 的 server 级检查（host/CORS/rate limit/child_process/github-audit）不直接适用，需映射到 Hub 实际面

## 设计：映射安全意图，不复制实现

| DDC 检查（Node server） | Hub 对应（Python tool） | 映射理由 |
|---|---|---|
| effective-rules baseline 非空 | permanent_baseline_intact | Hub 的"生效规则"=永久基线文件 |
| required modules present | required_files_present + required_dirs_present | Hub 的"模块"=协议文档/契约/工具/目录 |
| effective-rules resolvable | research_records_valid | Hub 的"可解析规则集"=研究台账 JSONL |
| protocol registry valid JSON | json_registries_valid | capability_registry / repository_matrix / cases INDEX |
| dangerous patterns absent | data_secret_scan_clean | 复用 R-0007 `secret_scan._scan_file`，不重复实现 |
| sensitive filtering present | source_no_hardcoded_credentials | 扫描 src/tools/tests 中的硬编码凭证正则 |
| runtime identity complete | workflow file present | Hub 的"运行时身份"=CI workflow 存在 |

## 实现
- `tools/runtime_preflight.py`：`run_preflight(root)` 返回 `{ok, status, service, checks, warnings}`（PASS）或 `{ok:false, code, message, details, checks}`（FAIL）
- 7 项检查，失败汇总不提前退出（一次报全）
- data 凭证扫描复用 `tools.secret_scan._scan_file`（同仓库内部复用，非跨仓复制核心实现）
- secret_scan 不可用时降级为 warning（`NOT_AVAILABLE`），不硬失败
- CLI: `python tools/runtime_preflight.py`，exit 0=PASS / 1=FAIL
- 源码凭证正则: ghp_ / sk- / xox[baprs]- / AKIA（四类常见硬编码形态）

## 测试
- `tests/test_runtime_preflight.py`：7 测试
  1. PASS 路径（minimal valid hub fixture）
  2. 缺必需文件 → FAIL
  3. 基线被篡改 → FAIL
  4. 无效记录行 → FAIL
  5. 无效注册表 JSON → FAIL
  6. 源码硬编码凭证 → FAIL
  7. 真实仓库 smoke（本地副本不完整时 skip，CI 完整 checkout 运行）
- 全套回归：108 → **115 pass / 0 fail / 1 skip**（Python 3.13 Windows）

## 边界
- 仅 Hub；Z-Brand / SICI / DDC 零改动
- 不复制 DDC Node 实现；是安全意图到 Hub 实际面的 Python 映射
- 不把 Hub 变成 server/runtime；preflight 是工具级完整性检查
- 不注册 Capability（停在 evidence，待 ChatGPT/Human review）
- 永久基线只增不减；records.jsonl append-only（7→8 行）

## NOT VERIFIED
- Hub GitHub Actions 真实 Run（仓库 Actions 疑似未启用，PR #1 创建后 5+ 分钟 0 check run，待用户在 Settings > Actions 启用）
- preflight 在 CI 完整 checkout 上的真实运行（本地 smoke 因副本缺协议文档 skip）
- DDC 是否需要对应 Python 版 preflight 或跨仓 preflight Contract（Owner=DDC，待裁决）

## NEXT FOR CHATGPT
1. 审查 7 项检查映射是否覆盖 Hub 实际风险面，是否有遗漏
2. 是否需要增加检查项（records.jsonl append-only 行数单调性、workflow YAML 语法校验、Capability Registry 生命周期合法性）
3. source_credential 四类正则是否有漏报/误报
4. R-2026-0008 review 结论: approved / changes_requested / rejected
