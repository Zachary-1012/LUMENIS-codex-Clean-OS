# Z-Brand-Core 生产基线 V2

> Baseline ID: ZB-PROD-2026-08-31-02
> 生效日期：2026-08-31
> 状态：ACTIVE / PRODUCTION-FIRST
> 事实优先级：当前源码/数据库/运行时实测 > 本基线 > 其他文档 > 聊天记录

## 1. 当前真实版本与双仓库状态

- Core：`Zachary-1012/Z-Brand-Core`，Private，main。
- Core 当前 `VERSION` 文件：`5.9.0`；最近主线提交已进入 `v5.9.7`，因此版本文件与应用实际版本存在漂移，必须作为 P0 文档/版本一致性问题处理，不得继续凭旧文档判断版本。
- DCC：`Zachary-1012/Development-Command-Console`，Private，main，当前独立研发中枢。
- DCC 是 Development Source of Truth；Core 是 Business Source of Truth。

## 2. 生产优先级

### P0：CTH-POMS 稳定上线

任何新增能力均不得影响现有生产采集、主体口径、数据库、风险/事件/报告链路。

升级必须遵循：

`审计 → 兼容 → Shadow/旁路 → 回归 → 小范围验证 → 才能切换`

### P1：ZBMP

继续作为 Core 内受控增强能力层，不建立第二套长期维护 Core。

### P1/P2：DCC

DCC 负责研发审计、任务合同、测试、证据和受控升级；不得成为 CTH-POMS 运行时依赖。

## 3. 不可破坏红线

不得修改、弱化、绕过：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` / `captured_at` 语义
- 历史生产数据库及备份
- 已验证的 XHS 主采集主链

任何采集失败、IP 风险、300012、验证码、Session 失效、权限问题均不得伪装成“0 条”。

## 4. XHS 生产采集基线

当前 Core 已有：

- `collector.py`
- `xhs_cdp_collector.py`
- `xhs_runtime_state.py`
- `xhs_cookie_bridge.py`
- `auth_recovery_center.py`
- `platform_adapters/xhs.py`
- `topic_campaign.py`
- `web_topic_discovery.py`

`platform_adapters/xhs.py` 必须继续保持薄适配层：复用现有生产 collector，不复制主体过滤和业务逻辑；未经回归验证不得接管生产任务。

采集调度不得永久依赖固定时刻表；由健康度、连续成功、数据量、风险状态、冷却状态共同决定。历史固定时间点仅可作为兼容/研究配置，不得成为新的生产硬编码基线。

## 5. XHS App Topic：安全封锁基线

### 5.1 当前事实

截至 2026-08-31，小红书官方开放平台公开文档显示首期开放范围仅有 `basic_info`；`read_notes` 等能力仍处于规划状态。官方 API 参考当前主要覆盖授权、Token 和用户基本信息接口，并明确开放接口按 `接口 + app_id` 维度限流。

因此：**当前不得把“小红书 App 话题指标 API”当作官方可用生产接口。**

### 5.2 明确禁止

以下方案永久标记 `FORBIDDEN / BLOCKED`，不得进入生产代码、任务合同或自动执行链：

1. 抓包还原/逆向小红书 App 私有 API 签名。
2. 逆向、破解或复制私有加密/签名算法以绕过官方授权。
3. 伪造 App 请求、设备身份、签名、Token 或安全参数。
4. 通过自动化规避验证码、风控、IP 风险、设备校验或 Session 限制。
5. 通过频繁换 IP、代理池、设备指纹等手段规避平台限制。
6. 多账号轮换、批量注册或其他方式规避账号/设备限制。
7. 未经官方授权调用私有接口作为生产数据源。

### 5.3 推荐落地方案：App Evidence Adapter

第一阶段不做“App 自动爬虫”，而做安全的 **App Evidence Adapter**：

`用户在官方小红书 App 打开目标话题 → 用户主动触发分享/截图/页面证据 → Core 接收证据 → OCR/结构化解析 → 标准化 → 与 Web 数据融合 → 进入现有分析链`

允许采集的内容限定为业务所需且用户可见的公开话题页面指标，例如页面明确展示的浏览/讨论/笔记等字段；不主动读取通讯录、私信、收藏、草稿、账号隐私数据等非业务数据。

### 5.4 自动化限制

在没有小红书官方明确授权的 API/SDK/自动化能力前：

- 不自动登录 App。
- 不自动点击/滑动/批量浏览 App。
- 不注入 App。
- 不拦截 App 网络流量。
- 不读取 App 私有数据库。
- 不绕过 App 安全校验。
- 不让 App Adapter 自动调度高频任务。

如未来取得官方授权，必须先单独建立 `OFFICIAL_APP_API` Adapter，并完成权限、接口、限流、数据使用范围、撤销授权和审计测试后才能进入 Shadow。

## 6. App Evidence 数据契约

建议新增独立证据实体，不直接写入主采集结果：

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

App Evidence 与 Web 数据不一致时：

`不覆盖原始值 → 保留双源 → 标记时间差/来源 → 由融合层决定展示口径`

禁止把 OCR 失败或页面缺字段写成 0。

## 7. 风控与恢复硬门禁

状态链固定：

`正常 → 风险预警 → 停止危险请求 → 记录 → 熔断 → 冷却 → 健康检查 → 合法人工验证 → 低频恢复 → 连续成功 → 正常`

`NEED_VERIFY` 不自动绕过；`IP_RISK/300012` 不通过换 IP 强行恢复。

## 8. AI 边界

AI 只能增强：分类、聚类、摘要、洞察、OCR 后结构化、候选事件关系。

AI 不得独立决定：主体归属、真实发布时间、统计数量、原始数据真实性、核心风险口径。

新 App 能力必须先 Shadow，不得直接替换生产链。

## 9. DCC 门禁

DCC 保持：

- READ / TASK / AUDIT = ALLOW
- TEST = CONTROLLED
- WRITE = DENY
- DEPLOY = DENY
- PRODUCTION_WRITE = DENY
- UNKNOWN_CODE_EXECUTION = DENY

任何涉及 XHS App 的任务，DCC 必须先检查本基线；出现 `FORBIDDEN / BLOCKED` 行为时直接阻断任务，而不是生成绕过方案。

## 10. 完成定义

只有同时满足以下条件才可进入生产：

- 现有 CTH-POMS 主链回归通过。
- 主体/时间/风险/事件/报告口径回归通过。
- App 能力未绕过官方授权边界。
- 采集异常状态可解释。
- App 新能力为旁路/Shadow，且可关闭。
- 无敏感凭据进入 GitHub。
- 有测试证据、变更记录、回滚方案。
- DCC 审计通过。

## 11. 基线同步纪律

本文件为当前生产基线 V2。后续任何 Core/DCC/豆包开发任务必须引用 Baseline ID：`ZB-PROD-2026-08-31-02`。

若新方案与本基线冲突，必须先提出“基线变更申请”，不得在代码中悄悄绕过。
