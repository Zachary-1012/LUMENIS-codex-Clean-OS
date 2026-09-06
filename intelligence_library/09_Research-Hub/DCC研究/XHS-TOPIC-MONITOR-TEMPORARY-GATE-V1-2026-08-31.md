# XHS Topic Monitor Temporary Gate V1

## 当前状态

国内主账号：`WARNING / NOT_BANNED`。
香港 RedNote 账号：`RESTRICTED`，不得作为自动化测试账号。

## 临时任务预算

```text
TEMPORARY
≤ 10 batches / day
≤ 10 new notes / batch
dedup = required
```

这是业务连续性预算，不是规避平台检测的参数，也不构成“不触发风控”的保证。

## DCC 审计规则

允许：
- 对现有任务做预算、去重、质量、错误处理和可替换数据源设计；
- 研究官方 API、合规 Provider、用户 Evidence；
- 研究浏览器 Profile、Session 持久化和崩溃恢复。

禁止：
- 通过调整频率、随机行为、代理/IP、设备指纹等方式规避平台检测；
- 自动互动或自动恢复被平台限制的账号；
- 把香港受限账号作为实验账号。

## 研发门禁

任何把 `temporary_browser` 替换为 `official_api` / `licensed_provider` / `user_evidence` 的变更，优先级高于继续优化浏览器采集。

Core 上层业务链必须保持 Source Adapter 可替换，不能把临时方案固化成永久架构。
