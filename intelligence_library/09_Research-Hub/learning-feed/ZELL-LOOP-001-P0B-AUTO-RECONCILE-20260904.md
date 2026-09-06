# ZELL-LOOP-001 · P0-B Capability↔源码自动对账

- **task_trace_id**: `ZELL-001-20260904-p0b-auto-reconcile`
- **任务**: 补 MASTER-ENGINEERING-MATRIX P0-B 缺口「Capability/Contract/Ownership 文档矩阵缺与代码自动对账」
- **状态**: ✅ 已完成（可复跑：`python scripts/reconcile_capabilities.py`）

---

## 1. Issue
- 来源：MASTER-ENGINEERING-MATRIX-20260903.md P0-B 行 🟡「文档矩阵已建，缺与代码自动对账」。
- 目标：把 skills-registry.json（22 条能力 + 3 契约）与双子库真实源码做可复跑的自动对账，消除"文档声称 vs 源码实际"不确定性。
- 完成判据：脚本可复跑；production 9 / research 10 / contracts 3 逐条核验；MISSING=0 或给出人工判断依据。

## 2. Research（复用不重造）
- 复用：`config/skills-registry.json`（能力注册表 schema 1.0.0）、`reconciliation/03_capability / 06_contract / 07_ownership`、`baseline/MASTER-ENGINEERING-MATRIX`。
- 范式：对齐 GitHub 标杆 AAS Core「本地 catalog + 可检索 + agent 自主选择 + 只读验证」——只读核验，不自动改 registry。

## 3. Architecture
- 产物：`scripts/reconcile_capabilities.py`（OSAI 研究侧，只读扫描 ZBC/OSAI 源码）。
- 关键设计：
  - `parse_locations()`：解析 location 字段的目录前缀省略写法（`dir/a.md, b.md` → 同一目录）与 `+` 独立路径（`ZBC/a/ + b.py`）。
  - 符号抽样：对声称的 .py 抽顶层 `def/class` 名，验证文件真实含代码符号（非空壳）。
  - 边界：只读核验；MISSING 仅报告 + 人工判断，不自动改 registry、不改生产代码。

## 4. Patch
- 新增 `scripts/reconcile_capabilities.py`（+154 行）。
- 报告输出 `research-inbox/AUTO-RECONCILE-P0B-20260903.md`。
- commit：OSAI `5e02db4`（合并后 `b42a975`）。

## 5. Test（数字证据）
- 首次运行：production 9/9 PASS，research 10 条中 3 条 MISSING（因脚本解析缺陷，非 registry 缺陷）。
- 修复 1（research 默认归属 OSAI）、修复 2（location 目录前缀省略继承）后重跑：
  - **production_capabilities 9/9 PASS**（含符号抽样：app.py `_load_dotenv`/intelligence `_env`/agent_security `validate_tool_call` 等真实符号）
  - **research_capabilities 10/10 PASS**
  - **contracts 3/3 PASS**
- 结论：22 条能力 + 3 契约与双子库源码**完全一致**，MISSING=0。

## 6. Runtime
- 运行环境：Windows + 本机 python；运行时间 2026-09-04 04:41。
- 只读核验 ZBC `D:\Taikoo-monitor-new` 与 OSAI 源码；未启动/修改任何生产进程。

## 7. Evidence
- `research-inbox/AUTO-RECONCILE-P0B-20260903.md`（全量对账表）。
- commit：OSAI `5e02db4` / 合并 `b42a975`。

## 8. Evaluation
- 目标达成度：**100%**（P0-B 🟡→✅，矩阵已更新）。
- 发现的问题：对账脚本自身 2 处解析缺陷（证明"对账工具也必须可验证"）。
- 耗时：约 25 分钟。
- 收益：registry 与源码一致性首次被机器验证；后续能力变更可一键复跑。

## 9. Learning（可复用知识）
1. **skills-registry location 目录省略写法**：`dir/a.md, b.md` 表示同一目录——任何解析器需支持目录前缀继承。
2. **研究能力默认归属 OSAI 根**，生产能力默认 ZBC 根——解析器需按域区分默认源。
3. **符号抽样比文件存在性更强**：验证 .py 真实含 def/class，能抓出"空壳/占位"文件。
4. **对账是只读信任层**：发现不一致先修解析器，不自动改 registry；MISSING 需人工判断（描述过时 vs 拼写）。
5. **ZBC 只读核验姿势**：Python 直接扫 `D:\Taikoo-monitor-new` 无副作用，可用于后续所有跨库对账。
