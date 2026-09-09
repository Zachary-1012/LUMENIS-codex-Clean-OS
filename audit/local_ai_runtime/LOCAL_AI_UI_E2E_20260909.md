# LUMENIS LOCAL_ONLY UI E2E Evidence — 2026-09-09

- 隔离地址：`http://127.0.0.1:8293/lumenis/cth/qa`
- 隔离数据库：`D:\LUMENIS_REBUILD\AI_RUNTIME_UI_20260909\ui-monitor.db`
- 云端开关：`CLOUD_AI_DISABLED=1`、`ZHIPU_DISABLED=1`
- 页面：序境·商业运营 / 智能问答
- 输入：用户投诉停车等待时间过长，尚未获得官方核实，请仅依据这条文本分析。
- 页面实际显示：情绪 `negative`、置信度 `0.9`、Provider `OLLAMA_LOCAL`、Evidence ID `4482a836957ce41ca8c4472ce893f7806d83138868ffa46925ec4e6257c0b999`、标记“仅供辅助分析”。
- 结果：`PASS`

本次真实页面测试发现旧页面先调用 `/api/ai/chat`，其回退又以 `query` 字段调用 `/api/ai/analyze`，与当前 `text + runtime_mode` Contract 不一致。现已收敛为直接调用现有 Canonical `/api/ai/analyze`，并读取嵌套 `analysis` View Model；没有新增第二套业务 API。

测试服务使用临时无认证配置以避开自动化认证对话框；正式认证逻辑、生产配置和生产数据库均未变。测试后隔离服务已停止。
