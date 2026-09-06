# R-2026-0006｜AI-D 工单：Credential Sanitization 敏感字段增强（P1 待修复 → 修复）

- Research ID: R-2026-0006
- AI Agent: 豆包（Engineering Execution）
- Repository: Zachary-1012/AI-Development-Research-Hub（AI-D）
- Branch: main
- BASE_COMMIT_SHA（修改前 HEAD）: `0330d1cf96a330d287cd42d928a3635a9e750de1`
- Implementation SHA: `e09e01f3bbdb678b3d79fb30fe5bdcf60e9f2cf0`
- 来源工单: 《ZBIP_四产品_统一安全架构运行预检工单_v1-0901.xlsx》AI-D sheet 第 2 条「Credential Sanitization 敏感字段增强（P1，待修复：覆盖组合凭证字段，先测试再修改实现）」
- 规则依据: 《AI-D｜统一工单执行协议》第五节（敏感信息）、《ZBIP｜四产品总执行规则》、`docs/ZBIP_EXECUTION_LOG_2026-08-31.md`（九类凭证族 + 组合凭证字段）
- 状态: evidence（有真实测试证据；豆包 self-review approved，ChatGPT/Human 独立复核 pending，不自动晋级 reusable）

## 1. 工单—源码映射（先审计，不凭记忆）

| 项 | 事实 |
|---|---|
| 目标源码 | `src/contracts/research_record.py`（远程基线 blob `6283bf06`） |
| 目标测试 | `tests/test_research_record.py`（远程基线 blob `aac3723a`，原 31 用例） |
| 修改前实现 | `FORBIDDEN_KEYS={token,access_token,password,cookie,secret,api_key,apikey}`；`sanitize` 用 `k.lower() in FORBIDDEN_KEYS` 精确等值匹配后递归 |
| 缺口 | ① 缺 `authorization/private_key/session/credential` 四类；② 驼峰组合字段 `accessToken/sessionToken/privateToken/authorizationHeader` 经 `.lower()` 变为 `accesstoken/sessiontoken/...`，与集合里的下划线形态 `access_token` 不相等，全部漏脱敏 |
| 既有脱敏（不改） | `src/contracts/safe_collection.py` 有独立脱敏器，属 R-2026-0003/0004 采集线，本轮不动，留作后续「是否复用同一判定」的研究项 |
| DDC 关系 | 文件头声明兼容 DDC `zachary.platform.research-learning.v1`；DDC 侧 `tools/research_learning.py` 为 Owner，本轮不越权改 DDC |

## 2. 假设与方案（最小修改）

对字段名做命名风格归一后按「词法」匹配，而不是整串等值或子串包含：

1. 驼峰边界 `(?<=[a-z0-9])(?=[A-Z])` 拆词，再按非字母数字 `[-_ ]` 切分；任一独立词命中 `_SENSITIVE_WORD_TOKENS` 即脱敏（含常见复数）。
2. 整串归一（小写、去非字母数字）命中 `_SENSITIVE_PHRASES` 即脱敏，覆盖 `apiKey/privateKey/API_KEY/client_secret` 等。
3. 因要求「词边界」，`tokenizer/cookbook/secretive/sessionable/passwordless` 等近似词不会被误伤（有反向测试锁定）。
4. 保留 `FORBIDDEN_KEYS` 名字向后兼容；`sanitize` 输出标记 `[REDACTED]` 与 dict/list 递归结构不变，新规则是旧集合的**严格超集**（旧 7 键仍全部命中），DDC adapter 不受影响。

## 3. TDD 证据（先红后绿，禁止反过来）

- RED（只加测试、未改实现，真实运行）：`Ran 36 tests ... FAILED (failures=4)`，失败恰为
  `test_camel_case_compound_tokens` / `test_authorization_family` / `test_new_base_families` /
  `test_nested_and_listed_compound`；而 `test_legacy_forbidden_keys_still_redacted`（旧 7 键锁定）
  与 `test_no_substring_false_positive`（反误伤）在旧实现下即通过——证明缺口真实、测试有效、基线不回归。
- GREEN（最小实现后）：全套离线 `Ran 107 tests in 0.108s ... OK`，exit code 0（原 101 + 新增 6 = 107），Python 3.13 / Windows PowerShell / `PYTHONUTF8=1`。
- 行为样例（真实运行输出）：
  `accessToken/sessionToken/authorizationHeader/private_key/session → [REDACTED]`；
  `tokenizer=keep1, cookbook=keep2, passwordless=keep3, name=keep4`（近似/正常字段保留）。
- 历史数据回归：现有 5 条 `data/research/records.jsonl` 用新规则逐条 `validate` 全 `[]`，递归扫描敏感键泄漏 = 0；追加 R-2026-0006 后共 6 行，全部 `validate` 通过。

## 4. 修改文件清单（Push 1 Implementation）

- `src/contracts/research_record.py`：保留 `FORBIDDEN_KEYS`；新增 `_SENSITIVE_WORD_TOKENS`、`_SENSITIVE_PHRASES`、`_normalize_key`、`_key_tokens`、`is_sensitive_key`；`sanitize` 改调 `is_sensitive_key`。仅凭证判定逻辑变化，其余契约（枚举、validate、review、to_ddc_record、make_*）一行未动。commit `e09e01f`，+58/-2。
- `tests/test_research_record.py`：新增 `TestCredentialCombinationSanitization`（6 用例：驼峰组合 / authorization 族 / 新增基础族 / 嵌套 list / 旧 7 键不回归 / 反误伤），+53/-0。
- `data/research/records.jsonl`：append-only 追加 R-2026-0006（5 → 6 行，前 5 行字节保留）。

## 5. 边界与影响（责任分明）

- 未修改 Z-Brand-Core / SICI-Core / Development-Command-Console 任何文件。
- 未把 Hub 变成生产 Runtime；本次是 Hub 自身研究契约的安全缺陷修复。
- 未复制 DDC 源码，未改 safe_collection，未删任何既有协议/能力/历史 Evidence。
- 对 Z-Brand：无影响（not_applicable）。对 SICI：无影响（not_applicable）。
- 对 DDC：保持兼容（严格超集、输出契约不变）；是否在 DDC `research_learning.sanitize` 做镜像增强，属 DDC Owner 决策，本轮只提建议不越权。

## 6. NOT VERIFIED（不把推断写成通过）

- Hub GitHub Actions 的真实 Run 结果：当前工具无 `list_workflow_runs`，未取得真实 Run ID，标 NOT VERIFIED，本地离线测试不等同 CI。
- DDC 侧是否需要镜像同一脱敏增强：未改、未测，待 ChatGPT/Human 裁决后另立 DDC 工单。
- `safe_collection.py` 是否改为复用 `is_sensitive_key`：本轮刻意不改，留作后续复用研究（避免一次提交扩大范围）。
- 是否存在其它组合命名形态绕过匹配：已覆盖 snake/camel/Pascal/kebab/SCREAMING_SNAKE 与常见复合词，待 ChatGPT 独立做绕过性复核。

## 7. NEXT FOR CHATGPT（独立复核请求）

1. 以推送后最新 HEAD 为准（勿用本文件里的 BASE SHA），独立复核 `is_sensitive_key` 是否存在可绕过的组合形态、是否会误伤合法字段。
2. 复核「严格超集 + DDC 兼容」结论是否成立。
3. 裁决：是否给 DDC 开镜像工单；safe_collection 是否复用本判定（Capability 化前仍需 Evidence + Review）。
4. R-2026-0006 维持 evidence，未获 ≥1 approved 独立 Review 前不注册 reusable、不 Promotion。

> 永久基线只增不减：三方反哺、互相验证、边界不破、能力共享、责任分明。
