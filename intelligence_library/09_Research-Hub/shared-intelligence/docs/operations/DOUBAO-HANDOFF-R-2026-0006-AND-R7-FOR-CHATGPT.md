# DOUBAO HANDOFF → ChatGPT 独立复核请求

> 生成时间: 2026-09-01T04:00Z | 生成方: 豆包 (Engineering Execution)
> 请 ChatGPT 以 GitHub 当前事实为准独立复核，勿沿用本文件中的 SHA（动手前先 list_commits 重取）。

---

## 一、R-2026-0006 Credential Sanitization（P1 待修复 → 已实现，待独立复核）

### 事实锚点

| 项 | 值 |
|---|---|
| 仓库 | Zachary-1012/AI-Development-Research-Hub |
| BASE_SHA（动手前 HEAD） | `0330d1cf96a330d287cd42d928a3635a9e750de1` |
| 最终 HEAD（main） | `cbd8966e16ede57e8023eacd9b9d9140c1e94041` |
| 研究状态 | `evidence`（豆包 self-review=approved，ChatGPT review=pending，**未自动晋级**） |

### 提交链（最新在前）

1. `cbd8966` — Push2 四类审计文档（source/contract/evidence/capability）
2. `f9d5841` — 审计锁定测试：安全超集设计取舍（107→108）
3. `bf2b57f` — 恢复 records.jsonl + append R-0006（5→6 行）
4. `969490a` — **误发 placeholder probe**（已披露，见下）
5. `6157a66` — R-0006 研究文档
6. `e09e01f` — TDD 实现：is_sensitive_key + 6 测试
7. `0330d1c` — BASE

### 改动文件

- `src/contracts/research_record.py`（+58/-2）：保留 `FORBIDDEN_KEYS`，新增 `_SENSITIVE_WORD_TOKENS / _SENSITIVE_PHRASES / _normalize_key / _key_tokens / is_sensitive_key`，`sanitize` 改调 `is_sensitive_key`。其余契约（枚举/validate/review/adapter）一行未动。
- `tests/test_research_record.py`（+71/-1）：`TestCredentialCombinationSanitization` 7 用例（驼峰组合 / authorization 族 / 新增基础族 / 嵌套 list / 旧 7 键锁定 / 连写近似词反误伤 / 组合敏感词安全超集）。
- `research/R-2026-0006-credential-sanitization.md`
- `research/R-2026-0006-audit.md`
- `data/research/records.jsonl`（append-only，R-0001~0005 字节保留）

### Evidence（可运行/可回读，非 AI 自述）

- **TDD 红**：只加测试、旧实现下实跑 `Ran 36 tests, FAILED (failures=4)`，4 个失败恰为组合/新增族用例。
- **TDD 绿**：实现后全套 **108 pass / 0 fail / exit 0**（Python 3.13 Windows，`PYTHONUTF8=1`）。
- **历史兼容**：R-0001~0005 用新规则逐条 `validate` 全 `[]`，递归敏感键泄漏 0。
- **边界矩阵**：真实凭证字段（accessToken/sessionToken/authorizationHeader/private_key/session/credential 等 30+ 形态）0 漏；连写近似词（tokenizer/cookbook/secretive/passwordless）0 误伤；含独立敏感词的组合字段（sessionLengthNote/credentialCountLabel）按**安全超集**脱敏——这是设计取舍，见裁决项 2。

### 事故披露（不隐藏）

`969490a "temp probe"`：施工中误发占位探针提交，瞬时把远程 `records.jsonl` 覆盖为 `PLACEHOLDER`。本地经校验的 6 行副本未受影响，`bf2b57f` 立即完整恢复并追加 R-0006，随后远程回读确认 6 行齐全、无占位残留。根因：整文件覆盖型接口无 dry-run，禁止再发探针式提交。影响面：仅 Hub 台账，约 3 分钟修复，未触源码/测试/三产品。

### 请 ChatGPT 裁决（5 项）

1. **绕过性**：`is_sensitive_key`（词法匹配 + 整串归一短语）是否存在可绕过的组合命名形态？
2. **安全超集取舍**：含独立敏感词的组合字段（如 `sessionLengthNote`）一律脱敏，是否接受？还是要求更窄策略（仅尾词核心名词命中）？若更窄，需另开修改+测试。
3. **DDC 镜像**：DDC `tools/research_learning.py` 的 sanitize 是否需要镜像同一增强？（Owner=DDC，豆包本轮未越权改，待裁决后另立 DDC 工单）
4. **safe_collection 复用**：`src/contracts/safe_collection.py` 有自己的脱敏器，是否改为复用 `is_sensitive_key`？（Capability 化前仍需 Evidence+Review）
5. **R-0006 review 结论**：`approved / changes_requested / rejected`。approved 前维持 `evidence`，不进 `reusable`，不注册 Capability。

---

## 二、R-2026-0007 Hub Actions 真实 Run（进行中，受 Actions 启用状态阻塞）

| 项 | 值 |
|---|---|
| PR | [#1](https://github.com/Zachary-1012/AI-Development-Research-Hub/pull/1) |
| 分支 | `ci/r7-secret-scan-fix`，HEAD `f244437891402bab34f048f176dd725c196265de` |
| 修复 | `tools/secret_scan.py` 新增（复用 `is_sensitive_key`，不重复实现）；workflow secret scan 步骤从 grep 改为 `python tools/secret_scan.py data/`；records.jsonl append R-0007（6→7 行） |
| 本地验证 | 108 pass；正向样本 `{api_key, nested.sessionToken}` → exit1 命中；`data/` → exit0 零误报；含 R-0007 的台账仍零命中 |
| 根因 | 旧 grep 扫描原始文本，把研究描述里的凭证字段名和脱敏样本键名误判为凭证 → 5 处误报，CI 永远红 |
| **阻塞** | GitHub Actions 4.5 分钟未调度任何 check run（`get_check_runs` total_count=0，`get_status` state=pending 但 statuses=[]）。疑似仓库 Settings > Actions 未启用。MCP 无启用 Actions 的工具，需用户在仓库 Settings > Actions > General 确认 "Allow all actions and reusable workflows"。启用后 PR 自动触发 `on: pull_request`，豆包回读 check_runs 补 Evidence。 |

---

## 三、通用约束（复核时请确认未被违反）

- 永久基线只增不减：三方反哺、互相验证、边界不破、能力共享、责任分明。
- AI 输出≠Evidence；不伪造测试/E2E；不存 token/password/cookie/secret/api_key/session/private_key/credential/authorization。
- 三产品仓（Z-Brand / SICI / DDC）本轮 0 改动；Hub 未变成第四生产产品。
- R-0006 / R-0007 均停在 `evidence`，无 ≥1 approved 独立 Review 前不进 `reusable`、不注册 Capability、不 Promotion。
- 下一轮 Research ID：R-2026-0008（开工前读 records.jsonl 确认最大号）。
