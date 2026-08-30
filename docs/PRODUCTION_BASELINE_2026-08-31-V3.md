# Z-Brand-Core 生产基线 V3

> Baseline ID: `ZB-PROD-2026-08-31-03`
> 生效日期：2026-08-31
> 状态：ACTIVE / HARD PRODUCTION GATE
> 上一基线：`ZB-PROD-2026-08-31-02`
> 事实优先级：当前源码/数据库/运行时实测 > 本基线 > 其他文档 > 聊天记录

## 0. 基线目的

本基线用于统一 Z-Brand-Core、Development-Command-Console（DCC）及辅助研发窗口对生产系统的理解和执行边界。

核心原则：**先保护已经跑通的生产链，再做能力扩展；先审计真实代码，再修改；任何新增能力默认旁路/Shadow，验证通过后才允许进入生产。**

## 1. 双仓库职责

### Z-Brand-Core

Business Source of Truth，负责生产业务、数据、采集、分析、事件、报告及增强能力。

### Development-Command-Console

Development Source of Truth，负责研发任务合同、审计、测试、证据、门禁和受控升级。

DCC 不属于 CTH-POMS 运行时依赖，不得因 DCC 故障导致 CTH-POMS 停止。

Core 中的 `tools/development-command-console` 为 Git submodule，只作为 DCC 接入点，不形成第二份独立 DCC 源码。

## 2. 生产优先级

### P0 — CTH-POMS

必须保持当前生产采集和业务链稳定。

### P1 — ZBMP

作为 Core 内受控增强能力层，不复制第二套长期维护业务核心。

### P1/P2 — DCC

完善研发审计、任务、测试、证据、回滚和受控升级能力。

## 3. 不可破坏生产红线

不得弱化、删除、绕过：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 时间语义
- 历史生产数据库及备份
- 已验证 XHS 主采集主链

任何采集异常、IP 风险、300012、验证码、Session 失效、权限问题不得伪装成“0 条”。

## 4. 当前采集架构基线

生产采集统一遵循：

`Platform Adapter → Discovery/Detail/Comments → Normalize → Subject Filter → Quality/Dedup → DB → Rule Analysis → AI Enhancement → Event/Trend/Report`

现有 XHS Adapter 必须保持薄边界层，复用已验证生产 collector，不复制主体过滤和业务逻辑。

### 动态调度

生产调度不得新增固定时间点硬编码作为长期基线。

允许保留历史固定时间配置用于兼容、研究或回归，但生产决策必须逐步由：

- 健康度
- 连续成功
- 数据量
- 风险状态
- 冷却状态
- Session 状态

共同决定。

任何新 Scheduler 必须先 Shadow，不能直接接管生产任务。

## 5. XHS App 能力：永久安全边界

### 5.1 当前定位

在没有小红书官方明确授权的 App API/SDK 能力前，**XHS App 不是生产自动采集源**。

第一阶段只允许：`App Evidence Adapter`。

流程：

`用户主动打开官方 App → 用户主动提供截图/分享/页面证据 → Core 接收 → OCR/结构化 → 标准化 → 双源融合 → Shadow`

### 5.2 永久 BLOCK

以下行为不得进入生产代码、任务合同、自动执行链或“研究模式”实现：

1. 抓包还原或逆向私有 API 签名。
2. 逆向/复制私有加密或签名算法。
3. 伪造设备身份、请求签名、Token、安全参数。
4. 自动绕过验证码、IP 风险、设备校验或 Session 限制。
5. 代理池、频繁换 IP、设备指纹等用于规避平台限制。
6. 多账号轮换、批量注册等用于规避账号/设备限制。
7. 未经官方授权调用私有接口作为生产数据源。
8. App 注入、读取 App 私有数据库、拦截 App 网络流量。
9. 自动登录、自动批量点击/滑动/浏览 App。
10. 将 App 自动化能力直接接入生产高频调度。

### 5.3 App Evidence 数据规则

App Evidence 必须与 Web 数据分源保存，不得静默覆盖。

最小数据契约：

- `source = xhs_app_evidence`
- `capture_mode = user_assisted`
- `captured_at`
- `topic`
- `metric_name`
- `metric_value`
- `evidence_uri/hash`
- `parse_confidence`
- `verified_by`
- `status = observed | uncertain | invalid`

OCR 失败、字段缺失、页面异常不得写为 0。

Web 与 App 数值不一致时：保留双源、保留时间、保留原始证据，由融合层决定展示口径。

### 5.4 官方 API 未来路径

只有在官方开放平台明确提供相应能力并完成授权/审核后，才可建立 `OFFICIAL_APP_API` Adapter。

进入 Shadow 前必须完成：

1. Scope/授权核对
2. API/SDK 文档核对
3. 限流与错误码测试
4. 数据使用范围确认
5. Token 生命周期与撤销授权测试
6. Shadow
7. 生产回归
8. 人工批准

## 6. AI 边界

AI 只负责增强：分类、聚类、摘要、洞察、OCR 后结构化、候选事件关系。

AI 不得独立决定：

- 主体归属
- 真实发布时间
- 统计数量
- 原始数据真实性
- 核心风险口径

AI 异常不得阻断核心数据采集。

## 7. 风控与恢复

统一状态链：

`正常 → 风险预警 → 停止危险请求 → 记录 → 熔断 → 冷却 → 健康检查 → 合法人工验证 → 低频恢复 → 连续成功 → 正常`

`NEED_VERIFY` 不自动绕过。

`IP_RISK / 300012` 不通过换 IP、设备或账号强行恢复。

## 8. DCC 强制门禁

DCC：

- `READ / TASK / AUDIT = ALLOW`
- `TEST = CONTROLLED`
- `WRITE = DENY`
- `DEPLOY = DENY`
- `PRODUCTION_WRITE = DENY`
- `UNKNOWN_CODE_EXECUTION = DENY`

任何新 Adapter 默认 OFF。

任何 XHS App 任务必须先通过本基线检查；触发 BLOCK 条款必须停止任务并提出合规替代方案。

## 9. 版本与文档事实纪律

代码版本、README、架构文档、基线必须定期校准。

当前已知存在 `VERSION` 文件与主线应用实际版本漂移的问题。后续必须以实际源码/运行时实测为准，并建立版本一致性校准任务。

不得以旧 README、旧聊天记录或旧版本号证明当前生产状态。

## 10. 上线门禁

任何新能力只有同时满足以下条件才可进入生产：

- CTH-POMS 主链回归通过
- 主体/时间/风险/事件/报告口径回归通过
- 无生产红线修改
- 新能力可独立关闭
- 异常状态可解释
- 无敏感凭据进入仓库
- 有测试证据
- 有回滚方案
- DCC 审计通过
- Core 与 DCC HEAD 二次核验完成

## 11. 变更纪律

任何与本基线冲突的需求必须先提交“基线变更申请”。

不得通过以下名称绕过基线：

- research mode
- experimental mode
- shadow mode
- temporary patch
- debug mode

Shadow 是验证隔离机制，不是绕过安全门禁的名称。

## 12. 当前开发路线

P0：CTH-POMS 生产稳定与版本事实校准。

P1：将 Topic Campaign 与统一 Dynamic Scheduler 收口，消除固定时间生产硬编码冲突。

P1：完善 XHS App Evidence Adapter，仅处理用户主动提供的公开页面证据。

P1/P2：统一 Auth / Session / Circuit / Recovery。

P2：DCC Private GitHub Audit Gateway，在最小权限和审计前提下接入私有 Core。

P2：完善事件关系、品牌洞察和 AI 增强。

## 13. 生效声明

本文件 `ZB-PROD-2026-08-31-03` 为当前生产基线，**覆盖并 supersede `ZB-PROD-2026-08-31-02`**。

后续 Core、DCC、豆包及其他研发窗口必须引用本 Baseline ID。
