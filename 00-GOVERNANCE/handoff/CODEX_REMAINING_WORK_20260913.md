# CODEX REMAINING WORK — 分类交接单（2026-09-13）

> 本文件为**追加式交接**，只记录"豆包 Experience→Production 接线完成后仍未完成、必须由 Codex 收口"的工作。
> 不替代任何既有治理文件；与 `FINAL_CODEX_EXECUTION_REPORT.md`（HEAD `0efd15e`）配套。
>
> - 生成时间：2026-09-13（UTC+8）
> - 分支：`codex/production-experience-wiring`
> - 本单基线 HEAD：`0efd15ea9115336bfdebb0982a0c092790030f7e`
> - 相对 `origin/main@49c325f`：0 behind / ahead（本地提交未 push，见 GIT-12）
> - 机器可读版：同目录 `CODEX_RESUME_PACK_20260913.json`
> - 接手协议：先 `git status / branch --show-current / rev-parse HEAD` 与本单基线比对；
>   若 HEAD 一致，**禁止重新全仓发现**，直接按下方 DAG 从第一张票开工。

---

## 0. 当前已完成（不要重做）

- Experience V2 蓝图 → 可运行 Flask 接线：`experience_runtime.py`（蓝图 7 路由）+ `experience_screens.py`（36 builder）+ app.py 最小注册 + 前端 `runtime.js` 水合。
- **38/44 屏真实后端只读绑定**（36 builder + CTH-01/AI-01 样板）；`unknown-bindings.json` = 42 BOUND / 3 N/A / 9 blocked-rows；`ACTION_REGISTRY.json` 66/66 结论化（无 UNBOUND/UNKNOWN）。
- 本切片测试 `tests/test_experience_runtime.py` 28 函数 exit 0；两次远端整合（`f1eb53b`、`edf6d2b`）后回归全绿。
- 隔离全量 app 真实 HTTP 集成打通（identity/subjects/8 探针屏/composer POST 走真实 `skill_execution_chain`）。
- 稳健 CDP 遍历：深色 1440 + 浅色 1440 各 38 屏全部 `data-source=runtime`、零溢出/零 undefined/零原型横幅；真 390 移动抽测零溢出。
- 4 屏诚实 BLOCKED、2 屏 N/A，未造假；设计 DNA（黑银/白银、原生 Orb、去卡墙）保持。

**结论：豆包侧前端接线闭环；`PRODUCTION_READY = NO`，剩余全部在本单。**

---

## 1. P0-BLOCKING（不完成不得宣布 Production）

### P0-DBISO-01 ｜统一 DB 隔离环境变量契约（本轮新发现，最优先）
- **问题**：仓内存在三个 DB 覆盖变量，测试/Staging 只设 `ZBC_DB_PATH` 时仍会漏写到默认库。
- **证据 / 位置**：
  - `ZBC_DB_PATH`（25 处，canonical）
  - `ZBC_EVIDENCE_DB_PATH`：仅 `evidence_chain.py:38`（`zbc_evidence` 真正写入方，`_get_conn` line356、INSERT line513）
  - `ZBC_RUNTIME_GUARDIAN_DB`：仅 `runtime_guardian.py:41`
  - 完全无 env、硬编码 `data/monitor.db`：`ai_task_engine.py`、`app_evidence.py`、`ark_llm.py`（另有 `intelligence_library_api.py`，见 P1-06）
- **本轮实证**：首版隔离服务因此向本地 gitignored `data/monitor.db` 追加 1 行 `zbc_evidence` + 1 行 `runtime_guardian_workers`；已用带行数断言的事务精确删除（恢复 0 / 8），夹具补齐三变量后复证真实库 mtime 冻结、写入只落 TEMP 库。
- **意图修复**：让 `ZBC_DB_PATH` 成为唯一 canonical override，覆盖全部 writer（或显式 fan-out 并文档化）；硬编码模块改走统一 resolver。
- **禁止**：不改任何业务语义、不删真实数据、不在本轮静默改默认库路径。
- **验收**：新增隔离回归测试——隔离模式下断言**没有任何连接**解析到默认 `data/monitor.db`；composer/guardian 全流程后真实库 mtime/行数不变。
- **依赖**：无（它是 P0-02 / P0-03 的安全前提）。

### P0-WRITEPERM-02 ｜写动作 → permission_gate → approval → runtime POST 链
- **问题**：读侧链与 composer 已验证，但 66 个 action 的**写链**未系统覆盖。
- **位置**：`permission_gate.py`、`experience_runtime.ai_intent`、各 action handler、`ACTION_REGISTRY.json`。
- **意图**：按 CTH/BMP/SH 域抽代表写动作，验证 `permission_required → approval token → runtime execute → result/evidence`，含"无权限 / 待审批 / 成功 / permanent_deny"分支。
- **验收**：四态都有真实测试；拒绝路径不产生任何写入与证据；不暴露 cookie/CDP/token/系统提示。
- **依赖**：P0-DBISO-01（否则写链测试会污染真实库）。

### P0-E2E-03 ｜只读生产副本 Critical E2E
- **问题**：目前仅在 TEMP 隔离库验证，未对 production-candidate 副本做端到端。
- **意图**：拷一份 production-candidate（**只读、绝不连真库**），跑 AI-01 + CTH-01 + 每域代表屏的全链 E2E。
- **验收**：副本前后 hash 不变；全链 200；无 undefined/NaN/`[object Object]`；无 fake 200；缺源显 notcollected。
- **依赖**：P0-DBISO-01、P0-WRITEPERM-02。

### P0-BLOCKEDSCREEN-04 ｜4 个 BLOCKED 屏只在真实来源就位时关闭
- `BMP-05` 创作者 KOS：`kos_engine.get_kol_tier_summary(authors, config)` 需 `authors` 入参，无零参只读源。
- `BMP-11` 对标竞品：生产源无任何 getter。
- `SH-01` Content Studio：写作为主，写链未实现（与 P2-SH01-10 关联）。
- `SYS-06` 内部浏览器：安全敏感，刻意不暴露 CDP/session。
- **规则**：只有真实零参源 / 写路径 / 安全决策存在才转 BOUND；在此之前**保留 BLOCKED_BY_EXTERNAL_DEPENDENCY 横幅，禁止造假接口、假数据、假状态**。
- **依赖**：BMP-05 依赖真实 authors 来源；SH-01 依赖 P0-WRITEPERM-02；SYS-06 依赖安全决策（可能长期 N/A）。

---

## 2. P1（RC 前必须）

### P1-LEGACYTEST-05 ｜全量遗留 pytest 分类
- 本切片 28 测试绿；全仓约 269 测试文件 / 3841 测试函数未在本轮跑。
- 全量跑并分类：REAL_DEFECT / DB_ISOLATION / OLD_CONTRACT / MISSING_MODULE / AUTH / ENV / LEGACY / FIXTURE / UNKNOWN。
- `tests/test_evidence_store.py` 在 CI 曾报语法错，本地当前 HEAD `py_compile` 不复现——需在标准环境复核。
- **禁止删测试换绿灯。**

### P1-TECHDEBT-06 ｜三个既有技术债定 Owner 收口
1. `evidence_api` 蓝图重复注册告警（import 进程 exit 1，自带 try 不阻断运行）。
2. 两套同名 `app_evidence_records` schema（`app_evidence.py` vs `evidence_store.py`/tests）owner 冲突；隔离播种刻意用 evidence_store DDL。
3. `intelligence_library_api.DB_PATH` 硬编码绕过 `ZBC_DB_PATH`；BMP-03 已改走 canonical `database.get_db()` + sqlite_master 守卫（缺表显 None/notcollected）。

### P1-SECRETREC-07 ｜全仓密钥扫描 + Recovery drill
- 本轮仅扫切片文件（CLEAN，真智谱 key 不命中、无 tracked `*.db`）；需全仓 git-diff 扫描。
- 做 runtime crash / scheduler / collector 故障注入与恢复、熔断、DLQ、reaper 演练（`runtime_guardian`）。

### P1-STATE-08 ｜13 态诚实降级全屏回归
- 0 / NULL / UNKNOWN / NOT_AVAILABLE / STALE / ERROR 等已在 builder 层体现；做全屏系统回归，确保缺源一律 notcollected、绝不把 NULL 强转 0。

---

## 3. P2 / POST-CLOSURE（不阻断当前前端闭环）

- **P2-MCP-09**：ChatGPT/MCP allowlisted adapter，按 `AGENTS.md §11` 与 `00-GOVERNANCE/LUMENIS-DOUBAO-CODEX-COMPLIANCE-HANDOFF-20260911.md` G0–G10：allowlisted schema + auth + subject/domain + permission + provenance/policy + versioned contract；**禁直达 Collector / Cookie / Browser Session / CDP / raw DB**。本轮刻意未做、不造假。
- **P2-SH01-10**：Content Studio 写侧链 Brief→Research→Draft→…→Learning Asset。
- **P2-SUBJECT-11**：Unified Subject Context / CTH·BMP selector（已明确 P0 收口后单独执行，不在本轮）。

---

## 4. GIT / 远端动作

### GIT-12 ｜本地提交 push 与分支策略（需网络/授权）
- 现状：分支 `codex/production-experience-wiring`，本地 11 提交未 push，0 behind `origin/main@49c325f`；备份分支 `backup/pre-remote-merge-20260913`、`backup/pre-remote2-merge-20260913`。
- **2026-09-13 当下网络事实**：本机外网正常（baidu/gitee 可达、DNS 正常），但 `github.com:443` TCP 不通（链路被重置），且本地代理客户端未开、127.0.0.1:7890 无监听 → **push 暂时不可达，非仓库问题**。
- 代理开启后执行（不 force、不直接推 main）：
  ```powershell
  # 若用本地 clash/v2ray：先启动代理监听 7890
  git -c http.proxy=http://127.0.0.1:7890 -c https.proxy=http://127.0.0.1:7890 `
      push -u origin codex/production-experience-wiring
  ```
- push 后用 GitHub 递归树核对 path/size/git-blob SHA；再决定开 PR 合 main（main 只能经 PR，不直推、不 force）。

---

## 5. 依赖 DAG / Codex 第一动作

```
P0-DBISO-01 ──► P0-WRITEPERM-02 ──► P0-E2E-03 ──► P1-05/06/07/08 ──► 六道 Gate ──► P2 ──► RC
      └──────────► P0-BLOCKEDSCREEN-04（BMP-05/SH-01 分别依赖来源与写链；SYS-06 待安全决策）
GIT-12 与开发并行（网络恢复即可推）
```

**FIRST TICKET = P0-DBISO-01**（它是写链与生产副本 E2E 不污染真实库的前提）。
**FIRST 5**：P0-DBISO-01 → P0-WRITEPERM-02 → P0-E2E-03 → P0-BLOCKEDSCREEN-04（先 BMP-05）→ P1-LEGACYTEST-05。

可并行（SAFE PARALLEL）：P1-SECRETREC-07 的静态密钥扫描、GIT-12、P2-MCP-09 的方案设计（不落地）。
串行阻塞（SERIAL）：任何会写库 / 跑写链 / 连生产副本的工作，必须在 P0-DBISO-01 之后。

---

## 6. 所有权红线

- **Codex = Production Code Owner**（后端 / DB / Runtime / Permission / Migration / 真实生产库 / push main）。
- **Doubao = Experience Layer Owner**（前端 / 设计系统 / 只读接线 / 交接资产）；其他模型仅 Advisory。
- 豆包本轮未改任何后端业务语义、未跑 migration、未写真实生产库（唯一一次隔离夹具漏配已精确回滚并复证）。
- UNKNOWN 保留 UNKNOWN，不猜、不造假、不把文档/文件存在/route 存在/部分测试通过当成 VERIFIED。
