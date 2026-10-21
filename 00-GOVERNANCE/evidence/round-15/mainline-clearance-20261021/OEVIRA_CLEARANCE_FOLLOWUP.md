# 寰意 OEVIRA 主线清障收尾回执

本回执仅处理 2026 年 10 月 21 日复核报告提出的 V01 与 V02，不推翻 PR #116、#117 已完成的修复，也不提前开始产品闭环开发。最终结论须结合本 PR 的最终检查、正常合并和独立 main 读回；源码、隔离测试、生产 Runtime/DB 与用户成果各自分层。

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
