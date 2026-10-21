# 寰意 OEVIRA 主线清障收尾回执

最新结论导航（下面各旧阶段按时间保留，不改写原始结果）：
- 本轮 tests/ 规范节点按精确执行与明确继承重建：12,816 个唯一 PASS，0 个未闭 SKIP/FAIL；不等于整产品验收。
- 候选 head `20ad82d432f8b8953f3f600be6d1f0341862e57d` 的真实 Product/App CI 已通过，含真实隔离 Chromium。
- PR #118 最终 head `60f9f8da05a30c595d3b8fcbb9d1c183d4da2e68` 的必需 CI 已通过；2026-10-21 12:36:05 UTC / 北京时间 20:36:05 正常合并为 `f7c864cbb007eb79eea116aa3d84da93333fba5a`，独立 main 读回及合并后 Product/App 检查均通过。下文旧阶段的“待执行”保留其历史语义，不是当前待办。

本回执处理 2026 年 10 月 21 日复核报告提出的 V01、V02，以及用户随后授权的原 10 项 SKIP 与关联既有缺陷收尾，不推翻 PR #116、#117 已完成的修复，也不提前开始产品闭环开发。最终结论须结合本 PR 的最终检查、正常合并和独立 main 读回；源码、隔离测试、生产 Runtime/DB 与用户成果各自分层。

## PR #118 最终发布与合并原件

本节补齐已经发生的发布证据，不改产品功能、测试定义、完成口径或历史原件。唯一报告仍为本文件，不另建报告副本。

- [合并及独立 main 读回回执](final-publication-receipts/PR118_MERGE_READBACK.json)：记录最终审阅 head、merge SHA、4,622 个 blob 身份、PR 与合并后 main 的必需检查。回执中的 174 成员 manifest 是 PR #118 当时的冻结值，不替代本次扩充后的 manifest。
- [最终 PR CI 原始 offline XML](final-publication-receipts/oevira-offline.xml)：1,189 个规范节点及单列 318 subtests；XML 的 tests=1,507 不能作为新增唯一节点数。
- [最终 PR CI 原始 HTTP XML](final-publication-receipts/oevira-http.xml)：5 PASS；[真实 Chromium XML](final-publication-receipts/oevira-browser.xml)：1 PASS；[offline 原始日志](final-publication-receipts/oevira-offline.log)。三份 XML 均无 FAIL/ERROR/SKIP，原字节保留。

以上 XML 来源是最终 PR Product run [39600006718](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/39600006718) 的官方 artifact `12346385886`，不是合并后 main 再跑所得 XML。实际 synthetic checkout 为 `6cae4f4b9b9c88cbf850d0c216b9a647262911d8`，tree 与最终 PR、合并 main 同为 `4aee4c8d418036c1635e2a3e379b51590e8cef34`。官方下载 ZIP 的 SHA256 为 `b29bf44d79817f1be45b09f8d020a686d496ecb8815fc8855f87966f7178db36`，精确四成员及 CRC 已核；ZIP 不重复入仓。

最终 PR App run [39600006710](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/39600006710) 成功。合并后 main 的 Product [39600906245](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/39600906245) 与 App [39600906369](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/actions/runs/39600906369) 也实际成功；最终读回时间为 2026-10-21 12:41:52.208 UTC / 北京时间 20:41:52.208，main 未改变。

本次仅把这五个缺失原件纳入现有有限 manifest，并更新当前入口；新归档 PR 的自身 CI/merge 以其官方记录与交付回执为准，不循环新增“归档的归档”。原 12,816 唯一适用节点账本及继承边界不变；不宣称单次全仓重跑、生产/设备/训练或整产品验收，不进入下一开发阶段。Issue #17 保持 OPEN。

## 修复范围与冻结版本

开工实际 fetch 的 main 为 `7c261229731c9b2e22f267b6455f024ab8861f83`，tree 为 `30c18dba83af68bc35151cf87fe2fbf284e356af`；当时没有其他开放 PR。原工作保留，未 reset、clean、force-push 或直接推 main。

worker 源码与测试先冻结为本地提交 `1e549e016666a9b3de078f7020038d8a7df353be`，tree `f9ceb7b9973187255711cb0459504aa1522e3eae`。发布的 PR #118 首个 head 为 `bfce94d7c259d94713e70eaaf7682ed0010e5a6d`，其 tree 完全相同。GitHub 的实际 PR synthetic checkout 为 `0334450f9b18080b05e66b040ee6328d7391b3d5`，也核对为同一 tree；它不是已经合并的 main。

## V01 虚拟环境入口修复

`TrainingProcessFence.start_managed_training()` 原来将调用者的 Python 路径 resolve 后直接用于 argv。现在分别处理两件事：对真实解释器实体进行 strict resolve 和 regular-file 核验，但实际启动保留调用者选择的绝对入口。这样 symlinks venv 与 copies venv 都保留自身 pyvenv.cfg、sys.prefix 和 site-packages 语义。

local worker 在已有私有管道握手中返回实际 executable、prefix、base_prefix、Python 版本与 psutil 来源。父进程核入口、源文件 pin、PID/create_time、启动前后目标身份；异常、入口失踪或目标变化仍拒绝并回收进程。remote 握手协议、权限、来源验证和环境白名单未扩大，未透传 PYTHONPATH 或秘密环境变量。

复现没有夸大：本机隔离云环境的 base Python 已安装 psutil，因此原源码复现的是 symlink worker 的 argv/prefix/依赖作用域被替换，不冒称本轮也出现 ModuleNotFoundError。修后测试在两种真正的私有 venv 中复制同版本已安装依赖，断言子进程 psutil 来源位于该 venv，经历启动、停止、替换和未绑定调用拒绝后，进程均回收。

新增 11 个回归节点包含两种 venv 生命周期、五种非法入口、四种身份或目标变化拒绝与回收。目标变化采用真实子进程配合受控故障注入，不是修改系统解释器。Python 3.12.14 的 recovery 模块 28 项、六个相关调用者/remote/AI_OFF 模块 268 项在实现阶段通过；这两批与后续完整冻结验证有重叠，不能相加。

当前非测试调用者 `experience_runtime.py` 的两个调用点使用 AuthenticatedSSHTrainingTransport。此修复验证现存 local managed 入口及其恢复边界，不宣称已运行真实远端训练链。未加载模型、未训练、未部署。

官方机制依据：
- https://peps.python.org/pep-0405/
- https://docs.python.org/3.12/library/venv.html

## V02 重新建立可独立核验的测试版本证据

53 份历史 XML 原件全部找回，合计 15,109,269 字节，逐份 SHA256 与原账本一致。全部内容和敏感字样上下文均已审阅；真实秘密、用户个人数据和内部对话未被识别。测试凭据负例与临时路径不当作真实泄露。原始失败、准备错误、跳过与后续成功均原字节保留，不用成功记录覆盖历史。

进一步核查发现：部分旧 `recorded_base_head` 来自按回执名称映射，并无当时完整 dirty/source-hash 捕获。除了明确缺 SHA 的 3,046 节点，不能仅靠旧字段证明其余旧结果的精确执行字节。因此本轮没有倒填历史 SHA，也没有继续继承旧 PASS，而是对冻结版本重新收集并分片覆盖本轮 `tests/` 规范收集到的全部 pytest 节点。分片在独立临时验证副本执行，不是另建产品实现。

每片保存实际 HEAD/tree、全部 tracked 文件前后 SHA256/Git blob、解释器入口/prefix/base_prefix、依赖 freeze 前后、明确的环境白名单、合成 seed 身份、实际 argv、UTC/北京时间起止、真实退出码与原始 XML。若源码或依赖发生变化，该片不能作为 PASS。所有数据均为隔离合成输入；受控网络规则和官方原生依赖遥测退出配置保留。

最终源码冻结为 `57d79f88c6418eef68d40241b22f9bb8d059ff35`，tree `896d64594742e48b44f6361facd7ab333a8f95a5`；对应远端 Git 提交对象为 `7de5327a399e1982275fa88e7c76cb0194e70c89`，同一 tree。最终归档之后只增加文稿、回执及固定 manifest pin，不再改产品或测试逻辑；最终 head 的必需 CI 另外执行。

| 证据层 | 实际结果与边界 |
|---|---|
| 1e549 完整冻结执行 | 12,785 唯一节点：12,774 PASS、10 SKIP、1 FAIL，原件永久保留 |
| 中间 5494819 组合验证 | 626 PASS、1 FAIL、247 subtests；新失败揭示真实连接生命周期问题，不覆盖成通过 |
| 最终 57d79f8 受影响验证 | 39 模块、932 节点：931 PASS、1 SKIP；247 subtests 单列 |
| 最终完整适用账本 | 12,808 唯一节点：12,798 PASS、10 SKIP，0 FAIL/ERROR/未运行节点 |
| 最终证据来源 | 932 节点在 57d79f8 实跑；11,876 节点继承本轮 1e549 的精确执行，不使用早期缺 SHA 的结果 |

本次继承桥逐文件比较源码与依赖；对 app 与 event_graph 的五个受影响函数另列 AST/文本差异及实际调用者复测。其余 312 个 app 函数、38 个 event_graph 函数的文本与 AST 不变；这不是静态分析能证明任意运行状态的承诺。两个新版本明确保留对旧同 node 失败的关闭关系，不叠加重复执行为测试总数。

最终 XML SHA256：`99909775f128927fac1fe7dd86f81718526ae5f448e08c05476f640e6b8c611d`。

入口：
- [最终节点账本](followup-receipts/FINAL_BOUND_NODE_LEDGER.json)
- [源码与依赖继承桥](followup-receipts/FINAL_SOURCE_INHERITANCE_BRIDGE.json)
- [函数级差异桥](followup-receipts/FINAL_FUNCTION_INHERITANCE_BRIDGE.json)
- [最终原始 XML](followup-receipts/final-owner-impact/results.xml)
- [最终执行回执](followup-receipts/final-owner-impact/receipt.json)
- [原始完整冻结账本](followup-receipts/FROZEN_1E549_NODE_LEDGER.json)
- [27 个脚本逐项适用性](followup-receipts/manual_script_applicability.json)
- [10 个跳过项及原始原因](followup-receipts/skip_provenance.json)

原取证说明中 `CURRENT_BOUND_NODE_LEDGER.json` 对应此处同字节的 `FROZEN_1E549_NODE_LEDGER.json`，改归档名称是为了明确历史冻结身份，未改其内容。部分手工回执沿用“4脚本”模板，但 fixed/final 目录实际只有2条 rows；本报告按真实 rows/argv统计，不把模板措辞当执行数。

## 追加复测揭示的真实连接生命周期缺陷

第一次全量红项只涉及 SHM 协调缓存重建；增强测试仍严格比较主 DB/WAL，随后组合复测确实捕获了持久文件变化。进一步取证证明 `event_graph.init_db()` 的裸 SQLite Connection 上下文在退出时没有关闭连接，延迟 GC 会触发自动 checkpoint。调用实际旧 Owner 返回后连接仍可 SELECT，显式关闭即改变主 DB/WAL；该证据不是单纯的测试预期问题。

修复沿原 DatabaseRepository：event_graph 的 init_db、load_from_db、import_from_existing_events、infer_and_link_relations 中四处裸上下文，以及 app 的事件 DELETE 一处，改用既有 transaction 上下文确保关闭。SQL、权限及原 executescript 语义不变，不宣称 DDL 因此全部原子化。init/load 有当前真实消费者；import/infer 为保留 callable，没有借此擅自删除或重做。

同一 DELETE 路径还确认 commit 失败时内存已提前删除。现在只在事务成功退出后更新内存，第二条 DELETE 异常及 commit 异常均保留数据库事件/关系和内存，成功路径仍仅删除目标。15 个新增正常/异常关闭与失败恢复节点通过；不是只给 fixture 强行收尾，也没有放宽主 DB/WAL 不变断言。

SQLite 只读观察与真实连接生命周期缺陷分开记录：
- https://sqlite.org/walformat.html#the_wal_index_or_shm_file
- https://docs.python.org/3.12/library/sqlite3.html#how-to-use-the-connection-context-manager

## 历史脚本与跳过项

27 个不进入 pytest 的旧脚本均按实际内容分类，而不是因“没有 pytest 函数”就认定完成。退休 Provider、真实部署/账户/生产数据库、缺原始资料及显式浏览器 opt-in 保持各自范围，不能为了清零启动未授权效果。

另对四个可隔离执行的纯逻辑工程脚本补做实际检查。proxy 与 risk 原脚本通过；guard wiring 的旧导入和 T2 对尚未到期冷却的错误恢复期待被定位并修复。修复只更新测试到当前 Owner 与安全语义，不改变产品熔断规则。有效冷却内 on_success 必须继续禁止请求；仅在 wall 与 monotonic 两个期限都届满后验证 half-open 恢复。Guard 的指标和 checkpoint 必须处于临时目录，不使用生产数据路径。原失败和修后证据分别保存，脚本断言数不加入 pytest 节点数。

## 原件唯一入口与完整性

归档沿原 `00-GOVERNANCE/evidence/round-15/mainline-clearance-20261021/`，原七个交付文件及固定 hash 不变。新增回执使用固定 hash 的 `OEVIRA_FOLLOWUP_ARTIFACT_MANIFEST.json` 精确列出路径、字节数和 SHA256；不是目录/XML 扩展名白名单。

现有治理检查器验证整个有限集合。缺失、改字节、额外成员、路径逃逸、重复原件、文件或父目录符号链接、非法大小/hash 均阻断；不会执行归档代码。原独立 guard 唯一缓存规则未扩大，缓存不入仓。

## 检查与交付边界

首个代码 head 的 Product Gate 39584710596 与 App Gate 39584710502 均通过；Product 实际使用 CPython 3.11.17，执行新增 venv/拒绝/回收回归。后续有归档治理、旧测试脚本和证据展示改动，必须对最终 head 重新检查，不能沿用这组旧 head CI 作为最终合并凭据。

本文件固定源码与测试事实，不能预先写入尚未发生的合并 SHA。最终发布、精确 head 的两项必需 CI、审阅及 main 读回由 [PR #118](https://github.com/Zachary-1012/LUMENIS-codex-Clean-OS/pull/118) 和交付读回回执定位。未具备全部正常合并条件时不得合并；交付之后停止等待用户复核。

修改源码的 Ruff F821/F822/F823/E9、编译、AI-native constitution 与源码 whitespace 检查已执行。历史 XML/log 中的原始末尾空格不被改写来伪造“原件”；其逐文件哈希和原字节保持，不能将此表述为全仓所有历史日志都无 whitespace。

独立实质审阅覆盖 worker 入口、local/remote 兼容、有限归档准入、两个历史脚本、SHM 测试校准、五处连接上下文与 DELETE 失败恢复。没有 GitHub 新评论不被当作审阅通过，实际测试数不等于产品完成率。

Issue #17 保持 OPEN，只使用 Refs #17。完成本轮后停止等待复核，不自动同步用户电脑、不启动线上线下统一、不进入实际产品闭环开发。测试通过和证据闭合不代表生产 Runtime/DB 已验收，也不是全仓永无未知缺陷的证明。

署名：dot（zack）。

## 后续授权：原 10 个 SKIP 的资源和工程闭合（浏览器 CI 待定）

用户随后要求解决原 10 个跳过项和缺失资源。本节是对前述历史冻结结论的追加，不删除或修改当时的 10 SKIP 原件。新的本地冻结为 `9be5e6d8ff2ce021da07bd954415f71d88abe616`，tree `b2ca1c999a601f5261063706f36f354a65dcaf30`；远端对应提交 `f3b4f92049620218158a77ce3ceb59e4043cf584`。PR #118 此阶段尚未合并。

50 个受影响测试模块实际运行 **1,123 PASS、1 SKIP**；`tests/` 当前规范收集 **12,816** 个唯一节点。紧凑 delta 以原 FINAL_BOUND_NODE_LEDGER 的 SHA256 `4ea148291bf1567776511db8da174e90b607551c48386e66ecd0d52985221108` 为基准：本轮执行 1,124 节点、继承本轮已精确绑定的 11,692 节点，合计 **12,815 PASS、1 SKIP**。唯一仍待关闭的是下面的真实 Chromium 节点。此处不能宣布 0 SKIP 或全部通过，mock 浏览器不替代真实浏览器。

| 原节点 | 原状态及原因 | 本轮处理与实跑 | 验证边界 |
|---|---|---|---|
| `test_ai.py::TestARKLLM::test_ark_llm_import` | SKIP：退休 ark_llm 未安装 | PASS：兼容 intelligence 入口指向唯一 Gateway，ARK/doubao 维持退休禁用 | 没有安装或恢复退休 Provider，不是推理验收 |
| `test_ai.py::TestARKLLM::test_get_api_status` | SKIP：退休模块缺失/异常被跳过 | PASS：UNBOUND 真实返回不可用，旧选择不能触发凭据、外部网络或 fallback | 不把禁用变成模型可用 |
| `test_browser_extract.py::test_real_chromium_visible_capture_without_network` | SKIP：需真实浏览器隔离宿主 | 本地仍 SKIP；已安排真实 Chromium CI，待精确源码和 XML 读回 | 不用模拟结果代替真实渲染，不提前记 PASS |
| `test_cross_surface_consistency.py::test_canonical_api_sentiment_matches_db_same_window` | SKIP：固定 8201 服务不可达 | PASS：隔离合成库与当前 Owner，启动实际 loopback HTTP，核同窗口情绪 | 非生产数据或真实平台采集 |
| `test_cross_surface_consistency.py::test_risk_index_present_in_canonical_api` | SKIP：固定服务不可达 | PASS：实际 HTTP 返回当前风险指标及来源口径 | 未知保持未知，不用零伪造可用 |
| `test_cross_surface_consistency.py::test_empty_window_returns_zero_not_error` | SKIP：固定服务不可达 | PASS：空窗口请求与当前计量合同一致 | 历史节点名称保留，不强迫未知指标变零 |
| `test_csv_dialect_real_inputs.py::test_official_facebook_original_when_provided` | SKIP：未提供官方 CSV | PASS：重新取得 UCI 官方原件；唯一只读 fixture 默认离线运行，缺失/错字节 override 负例仍拒绝 | 不是用户账号导出或在线 Facebook 验收 |
| `test_intelligence_boundary_audit.py::test_10_network_recovery_retry_mechanism` | SKIP：外部 OSAI retry 不属于零网络导出器 | PASS：现行 signed Evidence outbox 失败、dead-letter、未批准重排拒绝、批准重排、重暂存及读回 | 明确语义迁移；外部 Receiver retry/ACK 未被测试，不冒充通过 |
| `test_refscan_consistency.py::test_brand_industry_stats_matches_canonical` | SKIP：固定服务不可达 | PASS：实际 HTTP 的品牌/行业统计与 Canonical 同 scope 比较 | 合成证据；collection_health 的离线桩不是采集健康验收 |
| `test_refscan_consistency.py::test_brand_industry_stats_consistent_across_views` | SKIP：固定服务不可达 | PASS：两视图相同 scope/口径一致，权限仍受约束 | 未运行生产账号，不是全平台验收 |

所有完整 node ID、旧状态、新状态和语义限定见 [紧凑节点 delta](skip-closure-receipts/SKIP_CLOSURE_NODE_DELTA.json)。原 10 SKIP 原因仍在前阶段 skip_provenance 原件，不倒改历史。五个 HTTP 测试使用真实本地 HTTP 服务和当前源码，隔离的合成 Source/Evidence/Canonical/Registry；不连用户电脑或生产数据库。

### 官方资源补齐与长期可复现

UCI 官方 Facebook Metrics 页面 https://archive.ics.uci.edu/dataset/368/facebook+metrics 及 DOI https://doi.org/10.24432/C5QK55 确认作者 Moro、Rita、Vala 和 CC BY 4.0 许可。2026-10-21 11:27 UTC（北京时间 19:27）取得官方 ZIP，CSV 37,891 字节，SHA256 `666ec82952b7ce90b464f5a87ec4f0fe92d9a63208f2fcb2d0443cb5f31c3f4c` 与原固定预期及已有备份一致。没有修改 expected hash 凑通过。

唯一原件进入 `tests/fixtures/uci_facebook_metrics/dataset_Facebook.csv`，相邻 SOURCE.md 保留作者、链接、许可及未改字节说明。测试不联网下载；显式路径覆盖必须仍满足同一 hash。原固定源码加原件 30 PASS，默认 fixture 和两个拒绝负例候选 32 PASS，最后纳入前述冻结 50 模块，重跑不累加计数。该公开数据只是历史匿名品牌 500 篇的公开子集，不补造未公开资料。

### 额外发现并修复：旧只读 exporter 同秒覆盖

追加实际调用复现发现：旧 `evidence_exporter` 同秒两次运行使用相同路径，第二次零增量把先前 367 字节 JSONL 截成空文件，原 manifest hash 失效。该保留旧入口目前没有已确认生产消费者，但不能继续保留破坏历史产物的 callable。

修复为 UUID 唯一后缀、`x` 独占创建、完整产物 fsync、同目录独占临时水位文件后原子 replace。碰撞、manifest 写失败、水位写失败和 replace 失败均抛错且不推进既有水位，旧产物保持。原 DatabaseRepository 只读连接、准入筛选、字段最小化、文本脱敏和 URL 凭据清理没有放宽。相关 72 PASS，以及独立 53 PASS 审阅回归，均与最终冻结执行有重叠，不相加。

仍明确：共享水位调用者必须串行；这不是跨文件事务、并发 exactly-once 或断电/目录 fsync 验收。失败遗留诊断产物不自动删，不能将局部完成当发送成功。

证据入口：
- [最终本地执行 XML](skip-closure-receipts/skip-close-impact/results.xml)
- [精确源码、依赖与前后状态回执](skip-closure-receipts/skip-close-impact/receipt.json)
- [规范收集回执](skip-closure-receipts/skip-close-collection/receipt.json)
- [官方 CSV 来源与 hash](skip-closure-receipts/skip-facebook/SOURCE_RECEIPT.json)
- [旧覆盖缺陷原复现](skip-closure-receipts/exporter-regression/exporter_collision.json)
- [语义迁移与 exporter 修复映射](skip-closure-receipts/exporter-regression/node-semantic-map.json)
- [独立审阅精确文件 hash 与执行回执](skip-closure-receipts/export-independent-review/receipt.json)

下一道必要门槛是精确候选版本的真实 Chromium CI 原始 XML 与环境读回。它尚未在本节写作时确认，不能由此宣布 PR 可以合并。后续只追加其真实结果，不修改本地原始 SKIP。

### CI 隔离 seed 条件校准（保留失败，不推测远端运行原因）

随后本地源码头更新为 `2ecf05001adb37742449a1664ae2025a0cb9dbe5`，tree `5b771c8955d64c3f03243ea7fdfb4182f19db09f`。逐项比对 Git tree：相对 9be5e6d，仅 `.github/workflows/platform-verify.yml` 变化，其余 4,583 个 blob 相同，产品与测试字节未变。工作流为当前 step 创建独有合成 seed、在导入测试前应用已有业务 schema，明确硬超时非零阻断，并保留原 XML/log；没有修改生产数据库。

隔离 CPython 3.12 对照实际执行：原 step 为 1,186 PASS、3 FAIL，318 subtests 单列；只补同 step seed 后为 1,189 PASS、0 FAIL、0 SKIP，318 subtests 单列。失败涉及缺列风险，并非生产数据事故；这份本地对照不等于 GitHub CPython 3.11 验收，更不能解释尚未取得日志的远端长运行原因。

- [失败原日志](skip-closure-receipts/offline-ci-diagnostic/output.log)
- [只补 seed 后原日志](skip-closure-receipts/offline-ci-diagnostic/seeded-output.log)
- [对照方法派生公开回执](skip-closure-receipts/OFFLINE_CI_DIAGNOSTIC_PUBLIC.json)
- [源码等价派生公开回执](skip-closure-receipts/SKIP_CLOSURE_WORKFLOW_EQUIVALENCE_PUBLIC.json)

两份公开 JSON 清楚标注 DERIVED_PUBLIC_RECEIPT、原文件 SHA256 和移除的内部协调/未独立核验远端字段，不能冒称原件。原始日志保持同字节。最终远端 commit/tree、必需 CI 和真实浏览器结果仍须官方读回。

后续本地 `b0d253eb11dd9b0743183173bfaa72e85ddac382`，tree `4f119b6a672f65954629544e879a511fab225849`，仅将 offline pytest 控制台 `-vv` 改为 `-q` 并补注释，选择范围、断言、完整 XML 不变。原因是实际单条参数化 node 名可产生约 200 万/180 万字节输出，减少 CI 传输风险；这不是确认远端长运行的唯一根因，也不是跳过测试。见[追加源码等价回执](skip-closure-receipts/SKIP_CLOSURE_WORKFLOW_EQUIVALENCE_20AD_PUBLIC.json)。此时最终 CI 和真实浏览器仍待读回。

### 真实 Chromium CI 已补齐：原 10 项 SKIP 收尾结果

北京时间 2026-10-21 20:12:56（UTC 12:12:56）官方读回：PR #118 候选 head `20ad82d432f8b8953f3f600be6d1f0341862e57d` 的 Product Gate（39596291255）与 App Gate（39596291275）均成功。实际合并预览 checkout `cb978a27e8f0e17f103cf36a6b340ed9cb4dcfba`，tree `4f119b6a672f65954629544e879a511fab225849`，与上文 b0d253e 本地 tree 一致。此为候选检查，不是随后归档提交的检查，也不是合并回执。

官方 artifact 12343569530 下载后 ZIP SHA256、CRC 和全部四成员均核验；只保存四个可读原成员，不重复嵌套 ZIP。真实 Python 3.11.17、Playwright 1.64.0、Chromium 156.0.8078.4，在网络 namespace 隔离下执行合成可见页面：浏览器 1 PASS、HTTP 5 PASS、offline 1,189 PASS，均 0 FAIL/ERROR/SKIP；318 subtests 单列，不计入规范节点总数。此前本地浏览器 SKIP 与各失败原回执不改写。

本轮 tests/ 规范收集的唯一 12,816 节点，按原 FINAL 账本 → 本轮精确 delta → 单浏览器 CI 覆盖重建，最终 12,816 PASS、0 SKIP、0 FAIL。不是把不同批次相加，也不是同一最终提交无差别全量重跑。继承来源、字节等价、依赖和变化执行边界仍按所链接账本与桥接回执限定。原 10 项依次由 5 项真实隔离 HTTP、1 项官方公开 CSV、2 项现行 Gateway/退休 Provider 语义、1 项本地签名 outbox 恢复、1 项真实隔离 Chromium 验证收尾。退休 ARK 不恢复生产推理，OSAI 不冒称外部投递，浏览器不冒称真实网站或全前端验收。

- [官方 CI 身份、运行与下载核验原件](skip-closure-receipts/ci-20ad/OFFICIAL_CI_READBACK.json)
- [真实浏览器原 XML](skip-closure-receipts/ci-20ad/oevira-browser.xml)
- [HTTP 原 XML](skip-closure-receipts/ci-20ad/oevira-http.xml)
- [offline 原 XML](skip-closure-receipts/ci-20ad/oevira-offline.xml)及[原日志](skip-closure-receipts/ci-20ad/oevira-offline.log)
- [最终单节点覆盖及可重建归并映射](skip-closure-receipts/SKIP_CLOSURE_CI_FINAL_OVERLAY_PUBLIC.json)

最终覆盖文件明确标注派生、原 SHA256、移除字段和公开桥映射；官方身份以原件为据，不以内部协调说明代替。归档更新后的精确最终 HEAD 仍须正常必需 CI、实质审阅、合并及 main 官方读回；本节不预写未来结果。不部署、不训练、不操作用户电脑，不宣告整产品完成。
