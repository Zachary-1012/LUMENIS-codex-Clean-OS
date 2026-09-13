# 序境 / LUMENIS 产品市场价值对照评估研究｜V1 阶段基线

> **仓库归档状态：`BASELINE_ONLY` · `REFERENCE_ONLY` · `NON_AUTHORITATIVE` · `NOT_PRODUCTION_TRUTH`**
>
> 本 Markdown 为 2026-09-11 Word 评估报告的仓库原生文本归档版本，用于后续产品完成后的前后对照。它不构成任何正式决策、估值、融资、交易、财务、定价、采购、法律合规、Production Acceptance、Release Approval 或客户承诺依据。若与当前可验证 Source / Runtime / Data / Permission / Evidence / Test / Release 事实冲突，以当前生产可验证证据为准。

**审计基线仓库：** `Zachary-1012/LUMENIS-codex-Clean-OS`  
**审计基线提交：** `b910117567a81b98746468e98dee3a4105d275cc`  
**基线日期：** `2026-09-11`

---

序境 / LUMENIS

最新生产仓产品成熟度、市场价值与研发经济性审计

Source-of-Truth Audit · Market Benchmark · Valuation · AI-native Economics


| 项目 | 冻结口径 |
| --- | --- |
| 审计对象 | Zachary-1012/LUMENIS-codex-Clean-OS（仅此仓库） |
| 冻结分支 / HEAD | main / b910117567a81b98746468e98dee3a4105d275cc |
| HEAD 时间 | 2026-09-11 01:40（UTC+8；Git commit 2026-09-10 17:40:35Z） |
| 报告日期 | 2026-09-11 |
| 市场基准 | 同类型产品能力；不比较 Salesforce / Adobe 等整家公司市值 |
| 估值口径 | 软件/IP 资产、Replacement Cost、Production Ready 资产、客户/收入情景 |
| 排除范围 | 不把其他私有仓、OSAI、GGI、Command 等资产计入序境产品价值 |


| 方法｜审计原则<br>文档存在 ≠ 已实现；代码存在 ≠ 已验证；测试文件存在 ≠ 测试已执行；CI 绿色 ≠ Production Gate 通过。所有结论优先使用当前 HEAD 源码、HEAD CI 运行事实、当前仓内可追溯审计证据，再用外部市场和标准校准。 |
| --- |



# 执行摘要

| 结论｜最终市场位置<br>当前综合 68/100，评级 C：能力资产接近 B，但 Production Gate 失败对市场等级形成硬封顶。完成 Production Closure 后，条件性预测为 84/100，评级 A。S 档仍需要规模化数据覆盖、独立认证/审计、可重复发布、企业 SLO、多租户/全球生态和真实客户长期运行证明。 |
| --- |


| 结论项 | 判断 | 解释 |
| --- | --- | --- |
| 当前综合等级 | 68 / C | 高能力密度的生产候选；不应声明 Production Ready |
| 当前技术资产底座 | 约 B | Evidence / Runtime / Agent / Data / Report 等资产广且有结构 |
| 当前可投入市场 | 受控 PoC / 内部 / 团队 | 可演示、可试点；商业 Production 当前不放行 |
| Production Closure 后 | 84 / A（条件性） | 成熟优秀的私有化/企业产品；仍非全球 S 档 |
| 核心差异化 | A | Evidence → Truth → Decision → Action → Evaluation → Learning |
| 最大短板 | Production Verification | CI、Security、DB/Truth、Runtime、Release lineage |



图 1｜当前与 Production Closure 后的主要能力评分（本报告模型）

## 必须先看到的 8 个事实

HEAD 最新提交仍为 b9101175；最新一批提交主要是 Experience / Governance 文档融合，不能把设计权威当成已上线 UI。

HEAD GitHub Actions 显示 success，但 compile 实际因 tests/test_evidence_store.py 语法错误失败；pytest 因依赖中没有 pytest 而未运行；Boundary Check 报 20 violations，其中 1 HIGH。

CI 对 compile、pytest、boundary、asset scan 均设置 continue-on-error:true，并排除多组浏览器/E2E/双域测试，因此当前绿色 CI 不是阻断式 Release Gate。

资产扫描仍证明产品并非小型原型：约 921 个 Python 文件、10,753 个函数、1,403 个类、609 条 API route（570 唯一路径）、269 个测试文件/3,841 个测试函数。

Evidence 不可变、hash/provenance、Truth Table、freshness/confidence、NO_DATA/ERROR 等生产数据设计已真实落在源码，而不是 PPT。

Runtime Guardian 已有 Worker→Lease→Heartbeat→Checkpoint→Reaper→Retry→DLQ→Resume 生命周期与熔断/冷却构件；但“构件存在”仍需真实运行证据才能晋级 Operating。

Agent Boundary 明确禁止普通 Agent 拥有 COMMIT/PUSH/DELETE，并含 tool allow/deny、审批、幂等与高风险拦截；但 app.py 的全局 PermissionGate 启动授权和历史认证旁路仍构成 P0 审计问题。

当前最大价值不是“AI 聊天”，而是把 Monitoring、Evidence、Canonical、Metric、Action、Content、Evaluation、Learning 组织为同一个 Production Truth 框架。

## 审计结论：为什么不是 B / A，也不是 D

不是 D：因为核心数据、Evidence、Runtime、权限、Agent、报告与工作流已经有大规模真实代码资产和系统化方法论。不是 B/A：因为产品是否能商业生产使用最终取决于可重复、可验证、可恢复、可审计的运行事实；当前 HEAD 的 CI、Security、Production Truth、Runtime 和 Release lineage 仍有阻断证据。于是“技术资产级别”和“市场可交付等级”必须分开：前者接近 B，后者当前只能 C。

# 目录

目录将在 Word 打开时自动更新；下页同时提供静态目录。

静态目录（便于任何 Office/预览器直接查看）

01  一、评估方法与统一评级基准

02  二、最新仓库事实基线与证据等级

03  三、产品与工程评估（1–8）

04  四、市场与商业评估（9–15）

05  五、国际 / 中国 / 韩国标准（16–18）

06  六、估值与重建成本（19–24）

07  七、维护、技术债、Scale、风险与 ROI（25–32）

08  八、32 维总对照矩阵

09  九、Production Closure 市场晋级条件

10  附录 A：估值模型与成本假设

11  附录 B：外部市场/标准/薪资参考

12  附录 C：仓库证据索引


# 一、评估方法与统一评级基准

## 1.1 五档评级

| 等级 | 定义 | 本报告判定标准 |
| --- | --- | --- |
| S | 行业顶级 / Leading Product | 全球或细分赛道领先；不仅功能强，还要规模、稳定、安全、治理、生态和客户证明同时成立。 |
| A | 成熟优秀产品 | Production Ready、企业级可交付，核心链路成熟，风险可控，体验/工程/治理均较强。 |
| B | 中等成熟商业产品 | 可商业使用，但在规模、治理、体验、自动化或生态有明显缺口。 |
| C | 普通商业产品 | 能解决明确问题并可受控交付，但生产工程、治理或扩展性仍不足。 |
| D | 常见 AI / 内部工具型产品 | 以功能/演示/内部效率为主，缺少稳定 Production Evidence 或企业级工程。 |


## 1.2 评分与 Gate 封顶规则

内部评分仅用于把 32 个维度放到同一尺度：S=90–100、A=80–89、B=70–79、C=60–69、D<60。综合评分采用生产关键项加权，并设置 Gate 封顶：只要 P0 Blocking、Production Truth、Runtime+Critical E2E、Security+Recovery、Release Lineage 中存在明确 FAIL，综合市场等级最高只能 C。这样可避免“功能多 = 产品成熟”的失真。

## 1.3 状态证据阶梯

| 状态 | 含义 | 能否算商业完成 |
| --- | --- | --- |
| PLANNED | 设计/治理/需求存在 | 否 |
| IMPLEMENTED | 源码存在且可定位 | 否 |
| TESTED | 有可重复测试通过证据 | 部分 |
| VERIFIED | 在指定环境与数据基线验证 | 接近 |
| RELEASED | 有不可变发布血缘与回滚 | 是 |
| OPERATING | 真实生产持续运行且可观测 | 最高 |


## 1.4 市场对照方式

市场比较只比较同类型“产品能力”，不用序境去对比 Brandwatch、Sprinklr、Salesforce、Adobe 等企业整体市值。S 档参照 Brandwatch/Sprinklr 等成熟 Consumer Intelligence / Social Listening / Unified Insight 产品在数据覆盖、AI、工作流、企业可扩展与安全治理上的产品级能力；序境的独特部分单独比较 Evidence / Production Truth / Action / Evaluation / Learning。

# 二、最新仓库事实基线与证据等级

## 2.1 最新 HEAD 冻结

| 项目 | 事实 |
| --- | --- |
| Repository | Zachary-1012/LUMENIS-codex-Clean-OS（private；仅审计此仓） |
| Branch | main |
| HEAD | b910117567a81b98746468e98dee3a4105d275cc |
| Commit | docs: fuse latest experience and Codex handoff into README |
| Commit time | 2026-09-10 17:40:35Z / 2026-09-11 01:40 UTC+8 |
| Commit signature | GitHub commit verification: unsigned |
| Current phase | PRODUCTION CONVERGENCE → Production Acceptance → Release Candidate → Production / Operating |


## 2.2 HEAD CI：绿色但不等于通过

| 检查 | HEAD 实际结果 | CI 表面 | 影响 |
| --- | --- | --- | --- |
| Compile | FAIL：tests/test_evidence_store.py f-string SyntaxError | workflow success | Repository Integrity 未证明 |
| pytest | 未执行：No module named pytest | workflow success | 不能把 3,841 个 test functions 当作 HEAD 已通过 |
| Boundary Check | FAIL：20 violations（INFO 11 / MEDIUM 8 / HIGH 1） | workflow success | 跨边界/Permission 治理仍有缺口 |
| E2E / Browser | 多组测试被 workflow ignore | 未覆盖 | 关键用户链路不能由此 CI 证明 |
| Asset Scan | PASS 并生成 inventory | success | 只能证明资产存在，不证明 Production |


| 结论｜Gate 判定<br>当前 GitHub Actions 采用 continue-on-error，属于“治理信号流水线”，不是可以阻止错误进入 main 的 Release Gate。它是本报告把当前市场等级封顶为 C 的最强 HEAD 级证据之一。 |
| --- |


## 2.3 能力密度与架构资产

| 资产指标 | HEAD 扫描事实 | 解释 |
| --- | --- | --- |
| Python | 921 files / 10,753 functions / 1,403 classes | 规模已超过普通内部脚本 |
| API | 609 routes / 570 unique paths | 能力广，但 API 生命周期/契约治理负担高 |
| Frontend | 55 HTML templates / 28 JS files | 真实前端资产存在；不是现代 SPA 技术栈本身 |
| Tests | 269 files / 3,841 test functions | 测试资产丰富；HEAD 执行证据不足 |
| Contracts | 9 | 已有契约意识，但 Canonical API Contract 未完全收敛 |
| CI workflow | 1 | 自动化入口存在，但当前不是阻断式 Gate |


## 2.4 关键正向源码证据

`evidence_chain.py` 明确规定 Evidence raw_content/hash/source 写入后不可 UPDATE，AI 输出与 human_correction 分离，历史 rule_version 不静默改写，并携带 provenance。

`ui_view_model.py` 定义 DataStatus、Confidence、TruthTable/ViewModel，并显式区分 NO_DATA/ERROR/STALE/UNAVAILABLE，禁止静默成 0。

`runtime_guardian.py` 实现 Worker→Lease→Heartbeat→Checkpoint→Reaper→Retry→DLQ→Resume、RetryLimit、Cooldown、CircuitBreaker。

`agent_boundary.py` 对非人工 Agent 默认移除 COMMIT/PUSH/DELETE，定义高风险动作拦截、tool allow/deny、Human Approval 与幂等。

`ai_channel.py` 将 AI 明确定位为 transport layer，具有限重试、熔断、健康状态，OPEN 时由上层回退本地规则；这是 AI-enhanced 而非 AI-dependent 的有效实现方向。

`.opencode/opencode.json` 对 `.env` 读取禁止、编辑/通用 bash 需询问，说明 AI coding 工具本身已有最小权限意识。

## 2.5 关键生产阻断

CI 不能阻止 compile/test/boundary 失败进入主线。

仓内工程审计仍标记 Security scan FAIL，并指出 `/api/auth/config` 凭据返回、PermissionGate 自动授权、高影响 dev endpoint 旁路等 P0 风险需要关闭。

数据审计仍指出 Evidence/Canonical/Metric/Report 存在多入口或重复真相候选，且历史生产候选 DB 有 foreign key 违规；必须以当前 clean runtime 重新验证。

Clean bootstrap / migration / rollback / single schema owner 未同时证明。

Release lineage 缺 immutable release manifest、artifact digest/SBOM/signature、tag/release 和运行时 release identity；HEAD commit 亦 unsigned。

前端 Experience V2 是当前权威方向，但不能据此宣称新体验已在生产页面全部完成。

# 三、产品与工程评估（维度 1–8）

## 1. 当前产品成熟度

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 62/C | 85/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜前端、后端、数据、Runtime、Evidence、权限、安全、测试、E2E、上线 Gate

当前能力资产广，但“能证明已上线”的证据链不足。HEAD CI 绿色并不等于 Gate 通过：compile 实际失败、pytest 未安装而未运行、Boundary Check 20 项违规仍因 continue-on-error 被吞掉。

Production Closure 判断｜Production Closure 后，若六大 Gate 以阻断式 CI + 同一运行基线 + 关键 E2E + Security/Recovery + Release Lineage 全通过，可进入成熟优秀产品 A 档。

| 行动｜市场/收敛动作<br>把“存在/设计/测试”与“Verified/Operating”分开；建立 HEAD→artifact→runtime→DB→E2E→rollback 的唯一证据链。 |
| --- |


## 2. 前端 / Experience

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 64/C | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜UI/UX、响应式、动效、设计系统、AI Workspace、品牌语言、Logo、交互、信息架构

现有 55 HTML 模板、28 JS 文件和大量领域页面说明前端不是空壳，但仍是 Flask 模板/静态资产主导；最新 Experience V2 主要是设计权威与研究资产，尚不能按文档宣称已实现。旧 ZBMP/功能目录语义仍有迁移债。

Production Closure 判断｜按新的 Context→Signal→Evidence→Decision→Action 任务链重构，并完成响应式、无障碍、三语、动效状态语义和逐页 Page→API→Truth→Permission→Browser Test，可达 A。

| 行动｜市场/收敛动作<br>不要只换皮；体验升级必须同时验证信息架构、数据状态、Evidence 下钻、Action 回写和移动端。 |
| --- |


## 3. 后端 / Production Core

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 68/C | 86/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜数据链、Evidence、Canonical、Function、Metric、API、DB、Runtime、权限、恢复、测试

Flask 后端能力非常厚：当前资产扫描约 921 个 Python 文件、10,753 个函数、1,403 个类、570 个唯一 API path。Runtime Guardian、Evidence、权限、安全等生产构件真实存在；但 app.py 约 344KB、API 面积大、迁移/契约/发布尚未收敛。

Production Closure 判断｜收敛 schema owner、Canonical API、Worker/Scheduler、错误模型、阻断 CI、SLO 和故障恢复后，后端可从“复杂且能跑的生产候选”进入 A 档。

| 行动｜市场/收敛动作<br>减少并行实现和 fail-open；建立唯一写入口、唯一 schema owner、API 生命周期和可观测 SLO。 |
| --- |


## 4. 产品架构

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 76/B | 88/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜CTH、BMP、Content & Creation、Subject Context、Agent、Shared Capability

当前正式架构方向清晰：CTH/BMP 共用 Subject Context，Content & Creation 是 Shared Capability，Agent Groups 是执行层而非第四产品。架构思想高于普通监测工具，但实际代码仍保留历史命名、重复路由/权限/Canonical 路径。

Production Closure 判断｜完成能力注册、领域边界、Contract 化和 legacy 退役后，可形成高度可复用的 A 档产品架构。

| 行动｜市场/收敛动作<br>控制复杂度：每个 Capability 必须有 owner、唯一 contract、生命周期和退役规则。 |
| --- |


## 5. 数据与 Production Truth

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 67/C | 88/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Evidence、血缘、Canonical Metric、一致性、UNKNOWN/ERROR、审计能力

这是序境最有价值、也最未收口的层。Evidence 不可变、hash/provenance、Truth Table、freshness/confidence、NO_DATA/ERROR 等模型真实存在；但仓库审计明确指出双 Canonical 候选、notes 直算/快照/canonical 多统计入口以及历史 DB 基线分裂风险。

Production Closure 判断｜若统一 Evidence facade、Canonical ID、Metric provider、Truth Table 与 Report 编排，并通过生产样本回放，数据产品能力可进入 A，且差异化接近 S。

| 行动｜市场/收敛动作<br>以单一数据真相入口为 P0：先统一 ID/读写者/迁移，再扩 UI。 |
| --- |


## 6. AI 能力

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 75/B | 87/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜AI Gateway、Agent、Shadow/Learning、模型替换、AI 不可用时的降级

AI 不是套壳：ai_channel 有有限重试、熔断、fallback；Agent Boundary/Firewall/Evidence/Evaluation 控制构件真实存在；核心原则明确 AI 不拥有 Production Truth。缺口在于“所有生产 AI/Agent 调用都强制经过统一入口”尚未证明。

Production Closure 判断｜统一 Orchestrator、Provider Registry、Tool Contract、Evaluation/Human Approval/Trace 后，可进入 A。即使模型不可用，确定性主链仍应继续工作。

| 行动｜市场/收敛动作<br>把 AI 价值衡量从“能聊天”改为准确率、可解释性、采纳率、返工率、fallback 成功率和单位结果成本。 |
| --- |


## 7. AI 自研开发模式

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 82/A | 88/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Codex、豆包、智谱、OpenCode、Ollama、本地模型参与研发

开发治理本身已接近 A：AGENTS.md 强制 READ→AUDIT→IMPLEMENT→TEST→VERIFY→EVIDENCE；OpenCode 配置限制 .env、命令执行需 ask；豆包升级协议要求审计/最小补丁/测试/回滚。但工具治理强、实际 Gate 仍会被 continue-on-error 绕过，说明“流程文档先进”尚未完全变成机器强制。

Production Closure 判断｜将研发规则转为不可绕过的 CI/Policy-as-Code、可复用 eval 和变更证据后，可成为成熟 AI-native 研发范式。

| 行动｜市场/收敛动作<br>下一步不是再加更多 AI，而是缩短 Evidence-backed feedback loop。 |
| --- |


## 8. AI 自研 vs 人工研发

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 78/B | 86/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜速度、代码质量、测试、架构一致性、维护、人力、成本

序境证明多 AI 能快速累积大体量能力资产，但 HEAD 同时证明 AI 速度会放大验证薄弱点：代码增长快于生产收敛。当前更像“高产能 B 档生命周期效率”，而不是已证明的无人化研发。

Production Closure 判断｜Production Gate 真正机器化后，AI-native 模式可把全生命周期人力压低约 45%–70%，而不是简单把编码成本降 90%。

| 行动｜市场/收敛动作<br>以 releases/defects/rework/lead time/MTTR 而非 commit 数量衡量效率。 |
| --- |


# 四、市场与商业评估（维度 9–15）

## 9. 市场产品横向对标

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 70/B | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜与同类型产品能力比较，不比较公司规模

对 Brandwatch/Sprinklr 等顶级产品，序境在数据覆盖、商业数据授权、规模、集成、SLA、认证上明显落后；但 Evidence→Decision→Action→Evaluation→Learning 的“Production Truth”方法更接近专用决策操作层，而非普通 Dashboard。

Production Closure 判断｜Production Closure 后可进入优秀垂直/私有化产品层，仍不会因为功能多就自动等于全球 S 档。

| 行动｜市场/收敛动作<br>把对标拆成“数据网络效应”和“决策闭环”两条赛道，避免用全球数据体量否定本地高价值闭环。 |
| --- |


## 10. 市场分层位置

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 66/C | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Top-tier / 优秀 / 中等 / 普通 / 大多数

当前综合为 C：能力资产接近 B，但商业上线 Gate 失败形成硬上限。可以做受控内部/试点，不应包装为规模化 Production。

Production Closure 判断｜Closure 后预期 A：成熟优秀产品，但距离 S 仍有数据覆盖、全球生态、独立认证、SLO/多租户/大规模并发等差距。

| 行动｜市场/收敛动作<br>用 Gate 作为市场等级封顶规则：Release Gate FAIL 时最高只能 C。 |
| --- |


## 11. 实际可投入市场程度

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 60/C | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Demo、内部、团队、交付、商业生产、规模化

Demo/内部/团队使用：可；受控客户 PoC：可；商业 Production：当前不应放行；规模化：未证明。主要阻断来自 Security、DB/Truth、Runtime、CI、Release lineage。

Production Closure 判断｜完成 Gate 后适合私有部署、项目制、企业团队生产使用；规模化 SaaS/多租户仍需第二阶段架构。

| 行动｜市场/收敛动作<br>把首个商业形态设为私有部署/受控企业交付，而非立即追求大规模 SaaS。 |
| --- |


## 12. 商业使用价值

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 80/A | 88/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜监测、研究、内容、报告、决策效率与人力节省

商业价值逻辑强：把监测、证据、研究、报告、行动、内容与评估串成一条链，能减少多工具切换和手工证据整理。价值强于单纯“AI 总结”。

Production Closure 判断｜Production 后可将价值从个人效率工具提升为团队决策基础设施。

| 行动｜市场/收敛动作<br>销售时优先量化：分析工时、报告周期、漏报率、复核时间、行动闭环率。 |
| --- |


## 13. 产品差异化

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 84/A | 90/S | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Monitoring→Evidence→Insight→Action→Content→Evaluation→Learning

差异化已达到 A：不是纯舆情、不是纯 BI、不是内容 AI，也不是社媒排程工具。核心差异是 Evidence/Production Truth 与行动-评估-学习闭环。

Production Closure 判断｜若真实生产链全部统一，这一维度有机会达到 S（方法论级领先），但仍需真实客户证明。

| 行动｜市场/收敛动作<br>持续强化 Evidence-backed Action 和 Learning Asset，而不是横向堆功能。 |
| --- |


## 14. 商业模式适配

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 78/B | 87/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜本地、私有、内部、项目、License、订阅、定制

当前技术形态天然适配本地/私有部署和项目制，甚至比纯 SaaS 更符合敏感企业情报场景；但可升级、授权、配置隔离、License、租户治理仍需产品化。

Production Closure 判断｜Production 后可采用“私有部署 License + 年维保 + 专项实施 + 可选订阅能力”混合模式。

| 行动｜市场/收敛动作<br>不强行 SaaS；按数据敏感度和客户 IT 约束设计部署矩阵。 |
| --- |


## 15. 市场竞争壁垒

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 74/B | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜数据结构、方法论、Evidence、领域知识、学习资产、设计、工作流、AI协作

代码与 UI 易复制；真正较难复制的是 Production Truth 方法、领域词/规则、Evidence 链、案例/学习资产、长期反馈数据和研发治理。当前客户数据/网络效应尚未形成，因此壁垒仍是 B。

Production Closure 判断｜有客户和长期 Learning Asset 后，壁垒可进入 A。

| 行动｜市场/收敛动作<br>把“可复用方法论 + 专有学习资产 + 客户工作流嵌入”做成复利，而非保密代码。 |
| --- |


# 五、国际 / 中国 / 韩国标准（维度 16–18）

## 16. 国际标准评估

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 57/D | 78/B | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Security、Privacy、Reliability、Observability、Accessibility、AI/Data Governance

控制构件多，但无证据证明已达到 ISO/IEC 27001、SOC 2、WCAG 2.2、SLSA 等可审计成熟度；当前 Security Gate 还有 P0 设计风险、release provenance 不完整，因此按国际企业采购标准仅 D。

Production Closure 判断｜Closure 后在没有第三方认证的情况下可达 B；要进入 A/S，需外部审计/渗透、SLO、SBOM/签名、隐私治理、WCAG 等。

| 行动｜市场/收敛动作<br>把合规分为“设计对齐”和“可出具证明”两层；后者决定国际采购。 |
| --- |


## 17. 中国市场标准

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 69/C | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜企业采购、数据合规、社媒数据、私有化、微信/企微生态

本地部署、国内平台、主体规则和消息生态方向有优势；但社媒采集合法性/平台授权、个人信息处理、网络安全责任、企业安全验收仍是商业上线约束。

Production Closure 判断｜完成安全/数据治理并以合法授权/最小化采集为前提，适配度可达 A。

| 行动｜市场/收敛动作<br>优先私有化、最小数据字段、权限审计、删除/保留策略、平台授权与合规说明。 |
| --- |


## 18. 韩国市场标准

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 55/D | 79/B | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜韩语、本地平台、PIPA/ISMS-P、企业习惯、设计体验

目前三语方向可作为基础，但缺少韩国本地数据连接、PIPA/ISMS-P 级证据、Naver/Kakao 等生态验证以及韩国企业部署/支持体系，因此当前 D。

Production Closure 判断｜完成韩语 UX、本地连接器、PIPA 隐私流程与 ISMS-P 对齐后可到 B，进一步有本地客户与认证才可能 A。

| 行动｜市场/收敛动作<br>韩国不是“翻译成韩文”即可：需本地数据源、隐私与采购证据、支持/部署流程。 |
| --- |


# 六、估值与重建成本（维度 19–24）

## 19. 国际市场估值

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 68/C | 82/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜当前资产、Replacement、Production Ready、客户收入后的价值

当前价值主要来自代码/方法论/IP，而非已验证收入；因 Release Gate 未过需较大风险折价。

Production Closure 判断｜Production Ready 后可显著提高资产可转让性和买方信心；客户收入再使用收入倍数。

| 行动｜市场/收敛动作<br>使用分层估值，不用一个数字冒充所有价值。 |
| --- |


## 20. 中国市场估值

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 72/B | 85/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜国内开发成本、替代成本、采购价值、软件资产价值

中国开发替代成本较国际低，但序境的领域方法、本地平台适配与私有部署价值更直接，当前资产价值 B。

Production Closure 判断｜Production 后可进入 A 档企业软件资产，真实客户会进一步放大。

| 行动｜市场/收敛动作<br>估值同时看替代成本、可交付性、客户节省和 recurring revenue。 |
| --- |


## 21. 韩国市场估值

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 62/C | 80/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜韩国研发成本、本地 B2B 价格、替代成本

韩国人力成本较高，但当前本地化不足，买方会对本地合规/连接器/支持打折，当前 C。

Production Closure 判断｜完成韩国本地化和 Production 后可进入 A 边缘/高 B。

| 行动｜市场/收敛动作<br>先投资本地化与合规证明，再谈估值溢价。 |
| --- |


## 22. 重建成本 / Replacement Cost

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 78/B | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜专业团队从零重建的人月、团队与成本

从功能宽度、路由/API、Evidence/Runtime/Agent/报告/前端资产看，重建不是“做一个仪表盘”，传统团队需跨产品、数据、AI、SRE、安全等角色。

Production Closure 判断｜Production-ready 版本的 Replacement Cost 还要增加硬化、迁移、E2E、可观测与发布工程。

| 行动｜市场/收敛动作<br>重建成本是资产价值上限参考，不等于可成交价格。 |
| --- |


## 23. AI-native 重建成本

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 86/A | 89/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜成熟 AI-native 团队重做成本

AI-native 能显著降低代码生产与文档/测试生成的人力，但验证、领域口径、架构审查、合规与运行仍需人。

Production Closure 判断｜序境若把自身 Audit/Gate 机器化，可接近 AI-native 高效率上沿。

| 行动｜市场/收敛动作<br>按全生命周期而不是 token 单价计算。 |
| --- |


## 24. 传统人工研发重建成本

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 76/B | 84/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜PM、设计、前后端、数据、QA、DevOps、AI 工程师 FTE

传统团队的优势是职责清晰、评审成熟；劣势是同等广度的人力和时间高。序境当前资产宽度对应约 14–18 FTE 峰值团队。

Production Closure 判断｜Production 完整版需 20–28 个月左右的传统建设周期（模型估算）。

| 行动｜市场/收敛动作<br>成本估算不含商业数据授权、客户实施和销售成本。 |
| --- |


# 七、维护、技术债、Scale、风险与 ROI（维度 25–32）

## 25. 当前维护成本

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 64/C | 82/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Bug、Runtime、DB、采集、AI、测试、前端、合规、依赖升级

当前并行实现、monolith、SQLite、多 API/旧命名、非阻断 CI 会让维护成本高于“代码看起来能跑”的直觉；维护风险主要是返工与诊断时间。

Production Closure 判断｜Closure 后通过唯一 contract、阻断 Gate、可观测/恢复可显著降低波动性。

| 行动｜市场/收敛动作<br>当前最值得投入的是降低不确定性，而不是继续扩功能面。 |
| --- |


## 26. AI-native 维护成本

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 79/B | 87/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜AI + 少量人工监督、模型、服务器与工具

AI 可以承担回归生成、审计、依赖升级、故障归因和文档同步，但不能独立承担生产审批。可持续模式仍建议 2.5–4.5 FTE 等价专业监督。

Production Closure 判断｜Gate 机器化后，年度全生命周期成本预计较传统团队低 45%–65%。

| 行动｜市场/收敛动作<br>将 token 预算、模型路由、缓存、失败熔断纳入成本治理。 |
| --- |


## 27. 传统团队维护成本

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 70/B | 80/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜正常企业人员配置

同等体量若按传统模式持续维护，通常需要 7–10 FTE 才能覆盖产品/前后端/数据/QA/SRE/安全/AI。

Production Closure 判断｜Production 后虽然故障更少，但客户 SLA 和合规会维持一定固定团队成本。

| 行动｜市场/收敛动作<br>传统团队成本高，但在关键岗位不可完全被 AI 替代。 |
| --- |


## 28. 维护效率对比

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 78/B | 87/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜AI-native vs 混合 vs 传统

AI-native 在重复审计、生成测试、跨文件修改、知识检索上占优；当前最大短板是验证没有完全阻断化，导致产能放大缺陷流量。

Production Closure 判断｜成熟后可实现约 1.5–2.2× 全生命周期吞吐，年度成本降低约 45%–65%（情景模型）。

| 行动｜市场/收敛动作<br>以 DORA/发布/缺陷/MTTR 指标长期校准。 |
| --- |


## 29. 技术债与长期风险

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 60/C | 82/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜Python/SQLite/Runtime/采集/测试/契约/AI 依赖

最先卡的不是 Python 本身，而是单体 app.py、SQLite 写并发/迁移、API/Canonical/Permission 多入口、采集平台依赖、CI 非阻断与 Runtime 基线分裂。

Production Closure 判断｜Closure 可解决“可控性”，但真正大规模还需数据库、队列、worker、租户和发布架构升级。

| 行动｜市场/收敛动作<br>建立 debt register：P0 真相/安全/发布，P1 契约/模块化，P2 scale/全球化。 |
| --- |


## 30. Scale 能力

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 57/D | 75/B | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜数据量、用户、多主体、多地区、多语言、多团队、并发

当前更适合单机/私有节点/小团队和受控数据量；SQLite + 单体 Flask + 未验证 worker 吞吐不支持宣称企业大规模并发。

Production Closure 判断｜Production Closure 后可到 B：稳定的单客户/小中型团队生产；要 A/S 需 PostgreSQL/队列/水平扩展/多租户/SLO 压测。

| 行动｜市场/收敛动作<br>不要把“路由多”理解为“规模能力强”。 |
| --- |


## 31. 上线风险

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 48/D | 82/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜功能、数据、法律、采集、安全、AI 幻觉风险

当前 D：存在会真实阻止上线的问题，包括隐藏 CI 失败、安全 P0、Production Truth/DB/Release lineage 未闭环、关键 E2E 未覆盖。AI 幻觉反而不是最大风险，因为架构已设计为 AI 非事实源。

Production Closure 判断｜Closure 后可降到可管理企业风险 A/B 区间，仍需平台采集合规和区域治理。

| 行动｜市场/收敛动作<br>用六大 Gate 清零上线阻断项后再对外承诺 Production。 |
| --- |


## 32. 最终 ROI

| 评估项 | 当前序境 | Production Closure 后 | 市场普通 | 市场中等 | 市场优秀 | 市场顶级 |
| --- | --- | --- | --- | --- | --- | --- |
| 等级 / 分数 | 74/B | 87/A | C / 60–69 | B / 70–79 | A / 80–89 | S / 90–100 |
| 定位 | Current Evidence | 条件性预测 | 可交付但治理一般 | 稳定商业化 | 成熟企业级 | 规模/生态/治理领先 |


核心问题｜开发投入、维护、替代人工、可售价格、商业回报

继续投入是有经济意义的，因为当前已经完成大量高替代成本资产，剩余价值主要在“把已有能力变成可证明、可交付、可维护的产品”。但如果继续横向加功能而不收口，ROI 会快速恶化。

Production Closure 判断｜Production Closure 后 ROI 进入 A：能把技术资产转成 License/私有部署/项目和 recurring maintenance 收入，并降低内部研究与报告成本。

| 行动｜市场/收敛动作<br>未来 8–12 周/一阶段预算应优先给 Production Closure，而非新功能。 |
| --- |


## 6.7 四类估值总表：International / China / Korea

以下均为 2026-09-11 的风险调整情景模型，不是融资报价、交易报价或会计公允价值。当前无真实 ARR/客户留存数据，因此“客户/收入后的商业价值”只能使用公式和情景区间；严禁把该情景写成序境当前市值。成本与资产估值不包含商业数据授权、法律顾问、销售获客和客户专属实施。

| 估值口径 | International | China | Korea | 说明 |
| --- | --- | --- | --- | --- |
| ① 当前代码/软件/IP 资产价值 | US$1.2–2.5M | ¥5–10M | ₩0.8–1.7B | 因 Gate FAIL、安全/Truth/Release 风险折价 |
| ② Replacement Cost（传统专业团队） | US$5.5–8.5M | ¥18–32M | ₩3.0–5.6B | 14–18 FTE 峰值，约 20–28 个月 |
| ③ Production Ready 产品资产价值 | US$3.0–5.5M | ¥12–22M | ₩2.0–3.8B | 完成六大 Gate 后；仍不含客户网络效应 |
| ④ 已有客户/收入后的商业价值 | ARR×2.5–5.0（情景） | Recurring ARR×2.5–5.0 | Recurring ARR×2.5–5.0 | 参考 2026 SaaS 交易/市场倍数；混合项目收入需折价 |


## 6.8 客户/收入情景，不等于当前估值

| 区域 | 示例情景（非当前事实） | 商业价值情景 | 适用条件 |
| --- | --- | --- | --- |
| International | Recurring ARR US$0.8–1.5M | 约 US$2.0–7.5M | 增长、续费、毛利、客户集中度决定倍数 |
| China | Recurring ARR ¥4–8M | 约 ¥10–40M | 私有部署 license/维保的 recurring 部分优先使用倍数 |
| Korea | Recurring ARR ₩0.8–1.5B | 约 ₩2.0–7.5B | 须有韩语、本地生态、隐私/支持和客户证明 |


对于“项目制 + License + 年维保”的混合业务，不应把全部项目收入按 SaaS 倍数计算。更保守的方法是：Recurring License/Maintenance × 2–4 + 服务/实施收入 × 0.3–1.0，再根据毛利、增长、续费和客户集中度调整。

## 6.9 重建团队与周期模型

| 模式 | 有效团队规模 | 周期 | International | China | Korea | 核心特征 |
| --- | --- | --- | --- | --- | --- | --- |
| 传统人工 | 14–18 FTE 峰值 | 20–28月 | US$5.5–8.5M | ¥18–32M | ₩3.0–5.6B | 职责完整；成本高；评审链成熟 |
| AI-assisted Team | 8–12 FTE | 14–20月 | US$2.8–5.0M | ¥9–18M | ₩1.6–3.2B | AI 辅助编码/测试/文档，人仍主导架构 |
| 成熟 AI-native | 5–8 FTE | 10–15月 | US$1.6–3.0M | ¥5.5–10M | ₩1.0–1.9B | Agent 执行 + 强 CI/Gate/Eval；人负责目标/审核 |
| 序境式多 AI + PO + Truth/Gate | 4–7 FTE 等价 | 12–18月 | US$1.5–3.0M | ¥5–10M | ₩0.9–1.9B | 理论接近 AI-native；当前需先补机器 Gate 才能达到上沿 |


## 6.10 AI 研发效率：为什么不能简单说“省 80% 人”

2026 年 NBER 对 50 万+ GitHub 开发者的研究显示，AI 代理可显著提高 commits，但增益沿着“代码→项目→实际 releases”逐级衰减：自主 coding agent 对 commits 的累计增益约 240%，到 projects 约 80%，到 actual releases 约 30%。DORA 同样强调 AI 是组织能力的“放大器”；没有测试、版本控制和反馈环，代码速度可能转化为交付不稳定。序境 HEAD 的“绿 CI 吞掉失败”正是这一宏观规律的本项目实例。因此本报告只假设全生命周期 45%–70% 人力节省，而不是把代码生成速度直接等价为企业产品交付速度。

## 7.9 可持续商业维护成本模型

| 维护模式 | 典型有效 FTE | International / 年 | China / 年 | Korea / 年 | 相对传统成本 |
| --- | --- | --- | --- | --- | --- |
| AI-native + 专业监督 | 2.5–4.5 | US$0.45–0.90M | ¥1.8–3.5M | ₩0.35–0.70B | 约 -45% 至 -70% |
| 混合研发 | 4–7 | US$0.8–1.5M | ¥3.0–5.5M | ₩0.6–1.1B | 约 -25% 至 -50% |
| 传统团队 | 7–10 | US$1.4–2.4M | ¥4.5–8.0M | ₩0.9–1.6B | 基准 |


维护成本是“可持续企业维护”模型，不代表你当前真实现金支出。当前真实维护预算未提供，因此不能假装知道。模型已把产品/工程/QA/SRE/安全/数据/AI 的持续责任计入，但不含商业数据源采购、客户现场服务与销售。

# 八、32 维总对照矩阵

表中“市场大多数/普通/中等/优秀/顶级”是统一锚点，不是某一家公司的分数。维度 19–28 的金额见前文，本表评分表达的是相应“经济性/资产强度/可实现程度”，不是把成本高低直接当作产品质量。


| 维度 | 当前序境 | Closure后 | 市场大多数 | 普通商业 | 中等 | 优秀 | 顶级 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1. 当前产品成熟度 | 62/C | 85/A | D | C | B | A | S |
| 2. 前端 / Experience | 64/C | 84/A | D | C | B | A | S |
| 3. 后端 / Production Core | 68/C | 86/A | D | C | B | A | S |
| 4. 产品架构 | 76/B | 88/A | D | C | B | A | S |
| 5. 数据与 Production Truth | 67/C | 88/A | D | C | B | A | S |
| 6. AI 能力 | 75/B | 87/A | D | C | B | A | S |
| 7. AI 自研开发模式 | 82/A | 88/A | D | C | B | A | S |
| 8. AI 自研 vs 人工研发 | 78/B | 86/A | D | C | B | A | S |
| 9. 市场产品横向对标 | 70/B | 84/A | D | C | B | A | S |
| 10. 市场分层位置 | 66/C | 84/A | D | C | B | A | S |
| 11. 实际可投入市场程度 | 60/C | 84/A | D | C | B | A | S |
| 12. 商业使用价值 | 80/A | 88/A | D | C | B | A | S |
| 13. 产品差异化 | 84/A | 90/S | D | C | B | A | S |
| 14. 商业模式适配 | 78/B | 87/A | D | C | B | A | S |
| 15. 市场竞争壁垒 | 74/B | 84/A | D | C | B | A | S |
| 16. 国际标准评估 | 57/D | 78/B | D | C | B | A | S |
| 17. 中国市场标准 | 69/C | 84/A | D | C | B | A | S |
| 18. 韩国市场标准 | 55/D | 79/B | D | C | B | A | S |
| 19. 国际市场估值 | 68/C | 82/A | D | C | B | A | S |
| 20. 中国市场估值 | 72/B | 85/A | D | C | B | A | S |
| 21. 韩国市场估值 | 62/C | 80/A | D | C | B | A | S |
| 22. 重建成本 / Replacement Cost | 78/B | 84/A | D | C | B | A | S |
| 23. AI-native 重建成本 | 86/A | 89/A | D | C | B | A | S |
| 24. 传统人工研发重建成本 | 76/B | 84/A | D | C | B | A | S |
| 25. 当前维护成本 | 64/C | 82/A | D | C | B | A | S |
| 26. AI-native 维护成本 | 79/B | 87/A | D | C | B | A | S |
| 27. 传统团队维护成本 | 70/B | 80/A | D | C | B | A | S |
| 28. 维护效率对比 | 78/B | 87/A | D | C | B | A | S |
| 29. 技术债与长期风险 | 60/C | 82/A | D | C | B | A | S |
| 30. Scale 能力 | 57/D | 75/B | D | C | B | A | S |
| 31. 上线风险 | 48/D | 82/A | D | C | B | A | S |
| 32. 最终 ROI | 74/B | 87/A | D | C | B | A | S |



# 九、Production Closure 市场晋级条件

| 结论｜晋级逻辑<br>当前 C → A 的路径不是再增加 30 个功能，而是把已经存在的能力变成“同一版本、同一数据、同一权限、同一 Runtime、同一 Gate、可回滚”的产品。 |
| --- |


| 优先级 | 必须完成 | 晋级证据 |
| --- | --- | --- |
| P0-1 阻断式 CI | 移除关键步骤 continue-on-error；requirements/CI 安装 pytest；compile/test/security/boundary/E2E 失败必须让 main/release Gate 失败。 | Repository Integrity = PASS |
| P0-2 Security | 关闭凭据返回设计、收紧 PermissionGate 自动授权与 dev endpoint bypass；执行 ASVS/渗透/secret/supply-chain 检查。 | Security + Recovery = PASS |
| P0-3 Production Truth | 统一 Evidence facade、Canonical ID、Metric provider、Truth Table 与 Report；修复 FK/迁移/clean bootstrap。 | Production Truth = PASS |
| P0-4 Runtime | 用 main@明确 SHA 在 clean environment 启动；Worker/Scheduler/Collector/AI fallback/Recovery 做长稳和故障注入。 | Runtime + Critical E2E = PASS |
| P0-5 Release Lineage | immutable manifest、core SHA、schema/profile digest、SBOM、artifact digest、签名/attestation、tag/release、rollback manifest。 | Release Lineage + Rollback = VERIFIED |
| P1-1 API/Frontend Contract | Page→API→Schema→DB→Evidence→Permission→Browser Test；收敛 legacy/v2/v4/重复路由与 ZBMP 旧命名。 | Experience/Engineering → A |
| P1-2 Scale Baseline | p95/p99、并发写、SQLite lock、collector 长稳、内存、队列/worker 容量；决定是否迁 PostgreSQL/queue。 | Scale → B/A |
| P1-3 企业治理 | WCAG 2.2、数据保留/删除/访问权、SLO/incident、AI model/eval registry、地域合规档案。 | International procurement → B/A |


## 九.1 最终 ROI 判断

建议继续投入 Production Closure，原因不是“已经投入很多所以不能停”，而是边际投入结构已经发生变化：当前仓库拥有大量高替代成本的功能/数据/运行/治理资产，下一阶段最有价值的工作不是扩功能，而是提高这些资产的可证明性、可转让性和可维护性。若 Closure 预算控制在 Replacement Cost 的约 10%–25%，并能把当前 C 级受控试点升级为 A 级可收费企业交付，经济上通常是合理的。反之，如果继续新增模块而 Gate 不收口，新增代码会扩大维护面、降低资产折价率，ROI 会恶化。

## 九.2 商业落地建议：先卖什么

第一产品形态：企业私有部署 / 本地部署 License + 年维保，而不是强行 SaaS。

第一价值主张：把监测/研究/报告的人工链缩短，并且每个结论可回 Evidence；不要主打“AI 更聪明”。

第一交付门槛：明确 Subject/Domain、数据授权边界、采集合法性、Retention/Deletion、权限与审计。

第一 ROI 指标：报告产出时长、人工复核工时、异常发现延迟、Evidence 定位时间、行动闭环率、重复劳动减少。

第一扩展路线：先稳单客户/单节点/小团队，再做 PostgreSQL/队列/多租户/全球连接器；不要同时追求所有市场。

# 附录 A：估值模型、成本与假设

## A.1 汇率快照

| 换算 | 2026-09-11 参考快照 | 用途 |
| --- | --- | --- |
| USD → CNY | 1 USD = 6.7065 CNY | 仅用于交叉校验；中国估值主要按本地成本建模 |
| USD → KRW | 1 USD = 1,348.46 KRW | 仅用于交叉校验；韩国估值主要按本地成本建模 |


汇率来自报告生成时的实时 FX 数据源。三地估值不是把一个美元数字机械换算，而是分别考虑本地研发工资、采购与本地化折价。

## A.2 人力成本锚点

| 地区 | 公开 2026/最新工资锚点 | 本报告 Fully-loaded 假设 | 说明 |
| --- | --- | --- | --- |
| United States | BLS May-2025 median：Software Developer US$135,980；QA/Test US$104,300；Software Developer national mean US$148,100 | 资深跨职能 blended US$180k–250k/FTE-year | 含福利、雇主成本、设备、招聘/管理等情景加成 |
| China | Robert Walters China 2026 Salary Survey 作为市场锚点 | 约 ¥0.60–0.85M/FTE-year（资深产品研发 blended） | 非单一岗位工资；用于重建团队模型 |
| Korea | Robert Walters Korea 2026 Salary Survey 作为市场锚点 | 约 ₩90–140M/FTE-year（资深 blended） | 韩国本地工程/产品/QA/SRE 混合团队情景 |


## A.3 估值方法

Current Code/IP Asset：以 Replacement Cost 为上限，按 Production readiness、可转让性、技术债、安全/数据/发布风险折价。

Replacement Cost：角色 × Fully-loaded 人力 × 周期 + 工具/基础设施/管理冗余；不包含商业数据授权和销售费用。

Production Ready Asset：在完成 Gate 后提高风险调整系数，但仍不把未存在的客户/收入/品牌网络效应估入。

Customer/Revenue Commercial Value：有 recurring revenue 后才使用 revenue multiple；2026 公开 SaaS 市场基准显示约 3.1–3.2x 中位附近，报告采用 2.5–5.0x 情景区间以反映增长/续费/毛利差异。

混合项目/私有部署收入：Recurring license/maintenance 与 services 分开估；服务收入倍数远低于 recurring software。

## A.4 价值不包含什么

本报告不估算公司股权融资估值、创始人个人品牌、其他仓库技术、未提供的客户合同、未来收入承诺、商业数据版权/授权资产、专利、商标、现金、销售渠道或并购协同溢价。若未来加入真实客户、ARR、毛利、NRR、销售周期、CAC、客户集中度和续费数据，应重做商业估值。

# 附录 B：外部市场 / 标准 / 研发经济性参考

| ID | 来源 | URL | 本报告用途 |
| --- | --- | --- | --- |
| M1 | Brandwatch Consumer Research | https://www.brandwatch.com/products/consumer-research/ | 100M+ online sources；1.4T+ historical posts；496M new posts/day；AI/classifier/image/search。 |
| M2 | Sprinklr Consumer Intelligence | https://www.sprinklr.com/products/consumer-intelligence/ | 30+ channels；400K+ media sources；1B+ sites/review sites；AI、Copilot、case/action。 |
| M3 | Sprinklr Social Listening | https://www.sprinklr.com/products/consumer-intelligence/social-listening/ | enterprise scale；petabytes/billions predictions；firehose/real-time。 |
| S1 | ISO/IEC 25010:2023 | https://www.iso.org/standard/78176.html | 软件/ICT product quality model，9 个质量特征。 |
| S2 | ISO/IEC 27001:2022 | https://webstore.iec.ch/en/publication/79694 | ISMS requirements 与信息安全风险管理。 |
| S3 | ISO/IEC 42001:2023 | https://www.iso.org/standard/42001 | AI Management System，治理、透明、风险、持续改进。 |
| S4 | NIST AI 600-1 GenAI Profile | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence | AI RMF 的 GenAI 风险管理 profile；2026-04 更新页面。 |
| S5 | OWASP ASVS 5.0.0 | https://owasp.org/www-project-application-security-verification-standard/ | Web application security verification standard，5.0.0 为最新稳定版。 |
| S6 | WCAG 2.2 | https://www.w3.org/TR/wcag/ | W3C Recommendation；Web accessibility。 |
| S7 | SLSA v1.2 | https://slsa.dev/spec/v1.2/ | 软件供应链 provenance / build/source tracks / levels。 |
| S8 | AICPA SOC 2 Trust Services Criteria | https://www.aicpa-cima.com/topic/audit-assurance/audit-and-assurance-greater-than-soc-2/ | Security、Availability、Processing Integrity、Confidentiality、Privacy。 |
| C1 | 中华人民共和国个人信息保护法 | https://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html | 个人信息处理、跨境、权利与义务。 |
| C2 | 生成式人工智能服务管理暂行办法 | https://www.cac.gov.cn/2023-07/13/c_1690898326795531.htm | 中国面向公众 GenAI 服务治理背景。 |
| C3 | 网络安全法 2025 修正决定 | https://www.npc.gov.cn/npc/c1773/c1848/c21114/wlaqfxz/wlaqfxz002/202511/t20251103_449242.html | 修正后 2026 年现行网络安全治理背景。 |
| K1 | Korea PIPC | https://pipc.go.kr/eng/ | 韩国 Personal Information Protection Commission；2026 AI/privacy policy updates。 |
| K2 | PIPA Amendment Bill for AI Development | https://pipc.go.kr/eng/user/ltn/new/noticeDetail.do?bbsId=BBSMSTR_000000000001&nttId=3171 | 2026-08 韩国 AI/PIPA 政策最新进展。 |
| K3 | KISA ISMS-P | https://isms.kisa.or.kr/ | 韩国信息保护/个人信息保护管理体系认证。 |
| K4 | Naver DataLab | https://datalab.naver.com/ | 韩国本地搜索/购物/地域等趋势生态示例。 |
| E1 | Google DORA 2025 AI-assisted Software Development | https://dora.dev/research/2025/dora-report/ | AI 是组织能力放大器；强基础实践决定收益与稳定性。 |
| E2 | NBER Working Paper 35275 (May/Sep 2026) | https://www.nber.org/papers/w35275 | 500K+ GitHub developers；AI 增益从 commits 到 releases 显著衰减。 |
| E3 | METR experienced OSS developer RCT | https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ | 早期 2025 工具在特定 experienced OSS setting 曾使任务慢 19%，说明 AI 收益依赖情境。 |
| V1 | Software Equity Group 2Q26 SaaS report | https://softwareequity.com/research/quarterly-saas-report | SEG SaaS Index 2Q26 median EV/TTM Revenue ~3.2x。 |
| V2 | Array Capital B2B SaaS valuation multiples 2026 | https://www.arraycapital.com/insights/saas-valuation-multiples/ | 汇总 public median ~3.4x / private SaaS M&A ~3.1x 的 2026 数据。 |
| W1 | U.S. BLS Software Developers / QA | https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm | May 2025 median wages，页面 2026-08 更新。 |
| W2 | Robert Walters China Salary Survey 2026 | https://www.robertwalters.cn/our-services/salary-survey.html | 2026 中国薪资与招聘市场基准。 |
| W3 | Robert Walters Korea Salary Survey 2026 | https://www.robertwalters.co.kr/en/our-services/salary-survey.html | 2026 韩国薪资与招聘市场基准。 |


# 附录 C：最新生产仓证据索引

| ID | 仓库证据 | 用途 |
| --- | --- | --- |
| R1 | README.md | 当前产品身份、Production Convergence、六大 Gate、Truth/AI/Subject 原则 |
| R2 | AGENTS.md | 研发执行总指令、证据优先级、Production Truth 与跨仓边界 |
| R3 | .github/workflows/platform-verify.yml | HEAD CI 配置：continue-on-error 与 E2E ignore 范围 |
| R4 | HEAD Actions run 34509670873 | 真实日志：compile SyntaxError；pytest missing；Boundary 20 violations；asset scan inventory |
| R5 | app.py | 大单体启动、模块注册、PermissionGate 初始化、Flask 生产入口 |
| R6 | requirements.txt / package.json | Python 依赖未固定、pytest 缺失；前端主要为 Flask/static + Playwright |
| R7 | evidence_chain.py | 不可变 Evidence、hash/provenance、AI/human 分离、lifecycle |
| R8 | ui_view_model.py | TruthTable/ViewModel、freshness/confidence、NO_DATA/ERROR/STALE |
| R9 | runtime_guardian.py | Worker 生命周期、retry/cooldown/circuit breaker/DLQ/resume |
| R10 | agent_boundary.py | Agent 权限、tool allow/deny、审批、幂等、高风险拦截 |
| R11 | ai_channel.py | AI transport、有限重试、熔断、fallback/health |
| R12 | .opencode/opencode.json | AI coding tool 权限约束、.env 禁止、bash/edit 需 ask |
| R13 | DOUBAO_GITHUB_UPGRADE_PROTOCOL.md | 豆包升级审计→最小补丁→测试→回滚流程 |
| R14 | LUMENIS_ENGINEERING_QUALITY_AUDIT_V1.md | 仓内既有工程审计：RELEASE GATE FAIL；Security/API/DB/CI 风险 |
| R15 | LUMENIS_DATA_TRUTH_CHAIN_AUDIT_V1.md | 仓内既有数据审计：双 Canonical/多统计入口/Production Evidence FAIL |
| R16 | LUMENIS_FRONTEND_IA_AUDIT_AND_REDESIGN_V1.md | 前端资产与 Context→Signal→Evidence→Decision→Action 重构方向 |
| R17 | LUMENIS_AI_AGENT_ARCHITECTURE_AUDIT_V1.md | Agent/Evidence/Evaluation 架构与 Production admission 缺口 |
| R18 | LUMENIS_RELEASE_LINEAGE_AND_CANARY_AUDIT_V1.md | Release lineage、canary、immutable manifest/rollback 缺口 |


# 附录 D：最终判断一句话版本

| 结论｜当前<br>序境 / LUMENIS 当前不是“普通 AI 工具”，但也还不是 Production Ready 企业软件：它是一个拥有 A/B 级方法论与能力资产、被 C/D 级生产验证短板卡住的高密度产品候选。 |
| --- |


| 结论｜Production Closure 后<br>如果只做收敛而不继续堆功能，序境有现实机会进入 A 档成熟优秀产品；S 档要靠持续运行、客户、规模、数据生态、认证与全球/本地化复利，而不是再写更多代码。 |
| --- |


| 结论｜资产价值<br>当前代码/IP 的合理风险调整资产价值显著低于从零 Replacement Cost；完成 Production Closure 能提高的不是“文件数量”，而是可交付性、可审计性、可转让性和未来收入倍数。 |
| --- |


免责声明：本报告为产品、工程与市场研究用途，不构成法律意见、会计估值、证券估值、投资建议或交易报价。涉及中国/韩国/国际合规的商业上线，应由具备当地资质的法律/安全/隐私专业人员按实际数据流、部署方式和合同重新审查。

---

## 仓库归档边界与后续复评规则

- 本文件与同目录说明文件仅是**阶段性产品定位评估基线**，不是 Production Truth，也不是 Governance Authority。
- V1 必须冻结保留，不应在后续产品变化后回写旧分数或旧估值；未来评估应新建日期与版本。
- 产品完成 / Production Closure 后，必须以当时最新 HEAD 和真实运行证据重新审计；不得直接继承本次结论。
- 后续报告应尽量沿用本次维度和评分口径，以形成可比较的 `V1 → Final` 差异矩阵；不再适用的维度应明确说明，而不是机械沿用。
- 所有估值、成本、ROI 与商业化区间继续按“情景模型”处理，除非未来获得真实成交、合同、收入、成本、审计或第三方估值证据。
