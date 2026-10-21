# 寰意 / OEVIRA 线上主线清障测试证据附录

候选提交：`5e975f9aa4c43f6cb84de82b3e24b0c68b5e6d98`

当前正式收集：12771 个唯一 node ID。状态：PASS 12761, SKIP 10。

此表是源码及隔离合成验证，不是整产品、真实平台、用户设备或生产数据库验收。重复运行不相加，pytest 子测试统计不当成新增任务。

## 证据边界

- 仅源码与隔离合成测试证据，不代表已部署 Runtime 或生产数据库验收。
- 原被拒的真实平台／遥测路径未重复执行；后续新进程采用已修复合成传输及阻断所有非回环 DNS／socket 的守卫。
- 后续真实本地文档解析，在 ONNX Runtime 1.31.0 初始化前预置官方 ORT_DISABLE_TELEMETRY=1；保留网络守卫。
- eSpeak 1.52.0 从官方包解至隔离目录，未做系统安装。
- 不宣称真实模型服务、账号、平台或用户电脑验收。

## 未执行项

- `tests/test_ai.py::TestARKLLM::test_ark_llm_import`：SKIP；RETIRED_PROVIDER_NOT_REACTIVATED。
- `tests/test_ai.py::TestARKLLM::test_get_api_status`：SKIP；RETIRED_PROVIDER_NOT_REACTIVATED。
- `tests/test_browser_extract.py::test_real_chromium_visible_capture_without_network`：SKIP；REAL_BROWSER_OPT_IN_NOT_EXECUTED。
- `tests/test_cross_surface_consistency.py::test_canonical_api_sentiment_matches_db_same_window`：SKIP；LIVE_RUNTIME_ACCOUNT_DB_OUTSIDE_CLEARANCE。
- `tests/test_cross_surface_consistency.py::test_risk_index_present_in_canonical_api`：SKIP；LIVE_RUNTIME_ACCOUNT_DB_OUTSIDE_CLEARANCE。
- `tests/test_cross_surface_consistency.py::test_empty_window_returns_zero_not_error`：SKIP；LIVE_RUNTIME_ACCOUNT_DB_OUTSIDE_CLEARANCE。
- `tests/test_csv_dialect_real_inputs.py::test_official_facebook_original_when_provided`：SKIP；USER_SOURCE_NOT_SUPPLIED。
- `tests/test_intelligence_boundary_audit.py::test_10_network_recovery_retry_mechanism`：SKIP；EXTERNAL_COMPONENT_RESPONSIBILITY。
- `tests/test_refscan_consistency.py::test_brand_industry_stats_matches_canonical`：SKIP；LIVE_RUNTIME_ACCOUNT_DB_OUTSIDE_CLEARANCE。
- `tests/test_refscan_consistency.py::test_brand_industry_stats_consistent_across_views`：SKIP；LIVE_RUNTIME_ACCOUNT_DB_OUTSIDE_CLEARANCE。

## 全目录覆盖

另有 27 个现有脚本入口，按仓库既有规则不进入 hermetic pytest，单列为未执行，不算通过。完整路径和理由在 JSON。

## 恢复及复验

- 原依赖/seed缺失、全片环境中断、裸导入收集失败和旧profile native导入拒绝均保留历史，未作为通过。
- 正式四片覆盖全部收集模块；统计CPU合成测试独立54项；晚期修改由最终候选受影响基线复验。
- 合法私有文档格式实际解析29项、public macro20项、OTIO实际解析22项、eSpeak实际音频及取消27项完成。各组存在重叠，不可加成总体通过数。
- 所有每node原始状态、最后状态、证据文件SHA及测试开始时间见机器可读JSON。未知精确提交明确为null，不猜测。

## 版本与复验说明

完整四片分阶段取得终态，并非在最终提交上把所有测试再跑一遍。最后冻结候选的 57 个变更测试模块实际复验：949 个唯一 testcase，947 通过、2 个退休 Provider 跳过。其余继承完整片证据，具体来源及版本不确定性逐条保留。此附录不代替必需 CI、实质审阅、合并和 main 读回。

## 交付版本映射

- Python 最后受影响基线：5e975f9aa4c43f6cb84de82b3e24b0c68b5e6d98；tree 0fd7682bc71579e63c942b9d43c4bc96e9f06efe。
- 后续本地版本：3eb941d7d5e6d76e4a1821185d2aa4f23907004c；tree 10302cd57e635827d2d2fea495f86ff4ee8867bb。
- 正式 PR 当前 HEAD：5e8aff6411b71438dc1a626800975d561d2540e9。
- 两个本地版本之间仅修改 SH01 浏览器测试夹具与 CURRENT，没有 Python 源码或测试增量。因此保留 Python 基线证据，不伪称在后续 HEAD 重新运行全仓。
- 最终 CI、审阅、合并与 main 读回仍由主回执独立记录，本附录不预告通过。

## 完整复验入口与隐私说明

OEVIRA_TEST_REPRODUCTION.json 提供四片及最终 57 模块的完整路径列表、命令模板、依赖版本和环境变量。oevira_test_offline_guard.py 是本次进程级隔离守卫，复现时放入专用目录并命名为 sitecustomize.py。环境目录及合成 seed 需由执行者显式设置，不得指向生产数据库。

OEVIRA_TEST_NODE_LEDGER.json 保留全部唯一 node ID、历史失败、最后状态、证据 SHA256、UTC 与北京时间。原始 JSON 按字节复制，没有修改历史。未包含内部工作目录、真实临时 DB 身份、秘密或内部笔记；少量 /tmp/schema、user:password 等是源码负例的合成参数，为完整保留 node ID 而保留，不是真实凭据。

### Chrome 编译后续修正

5e8aff6 的真实 Chrome CI 发现 external JS interop 的 remove 方法不能直接 tear-off，改为 teardown closure，保留原全部断言。新本地提交 6e86658ed8eb1f8449eeaabb60ac4dd979d638ee、官方 PR 提交 c7f0cb4e8fd86d967d7f9db37e370cd9f88c8c50 共享 tree c6b8e78574e5e9fba2b3a25f6d2dafa1a0337b05；仍只有 SH01 测试与 CURRENT 增量，无 Python 变化。失败运行39571636062保留，最终结果以主回执为准。
