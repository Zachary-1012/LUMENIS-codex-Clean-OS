# DCC 生产门禁：XHS App 端能力

> Baseline ID: `ZB-PROD-2026-08-31-04`
> 状态：ACTIVE / HARD GATE
> 上一基线：`ZB-PROD-2026-08-31-02`
> 适用：Development-Command-Console 对 Z-Brand-Core 的所有研发任务

## 1. 门禁目的

XHS App 端存在平台、授权、隐私和风控不确定性。DCC 的职责是阻止越界实现，而不是寻找绕过限制的方法。

## 2. 当前生产定位

在没有小红书官方明确提供并授权相应 App API/SDK 能力前，XHS App 不得作为生产自动采集源。

允许的第一阶段能力只有 `App Evidence Adapter`：

`用户主动打开官方 App → 用户主动提供截图/分享/页面证据 → Core 接收 → OCR/结构化 → 标准化 → 双源融合 → Shadow`

## 3. 强制 BLOCK

任务合同、AI 指令、补丁候选、测试计划或运行操作中出现以下行为，DCC 必须 `BLOCKED`：

- 抓包还原/逆向私有 API 签名
- 逆向/复制私有加密或签名算法
- 伪造设备身份、请求签名、Token 或安全参数
- 自动绕过验证码、IP 风险、设备校验或 Session 限制
- 使用代理池、频繁换 IP、设备指纹等规避平台限制
- 多账号轮换、批量注册等规避账号/设备限制
- 未经官方授权调用私有接口作为生产数据源
- 注入 App
- 读取 App 私有数据库
- 拦截 App 网络流量
- 自动登录 App
- 自动批量点击、滑动或浏览 App
- 将 App 自动化直接接入生产高频调度

DCC 不生成上述绕过实现的代码、步骤或操作指令。

## 4. App Evidence 最小数据边界

只处理用户可见、业务所需的公开话题页面数据。

不得读取：

- 私信
- 通讯录
- 收藏
- 草稿
- 账号隐私数据
- 与业务无关的 App 数据

Evidence 最小字段：

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

OCR 失败、页面缺字段、页面异常不得写为 `0`。

Web 与 App Evidence 数值不一致时必须保留双源、原始值、来源和时间，不得静默覆盖。

## 5. 自动化与调度门禁

没有官方授权时：

- App Adapter 默认 `OFF`
- 不自动登录
- 不自动批量浏览
- 不自动高频调度
- 不接管现有 XHS 生产 collector
- 不绕过任何风控/验证码/Session 限制

Shadow 只用于验证数据结构和融合效果，不是绕过本门禁的模式名称。

## 6. 官方 API 未来路径

只有官方开放平台明确提供相应能力并完成应用审核/授权后，才允许建立 `OFFICIAL_APP_API` Adapter。

必须依次完成：

1. Scope/授权确认
2. API/SDK 文档核对
3. 限流与错误码测试
4. 数据使用范围确认
5. Token 生命周期与撤销授权测试
6. Shadow
7. Core 生产回归
8. DCC 审计
9. 人工批准

## 7. 与 Core 生产链的隔离

XHS App Evidence 不得绕过现有 Core Pipeline：

`Evidence → Normalize → Subject Filter → Quality/Dedup → Storage → Analysis`

不得复制第二套主体过滤、风险判断、事件聚合或报告口径。

不得影响 CTH-POMS 已验证 XHS 主采集链。

## 8. DCC 权限

保持：

`READ / TASK / AUDIT = ALLOW`

`TEST = CONTROLLED`

`WRITE / DEPLOY / PRODUCTION_WRITE / UNKNOWN_CODE_EXECUTION = DENY`

任何新 App Adapter 默认 OFF；未经充分证据、回归和人工批准不得进入生产。

## 9. 上线验收

必须同时证明：

- 未绕过平台授权
- 未新增敏感凭据
- 未影响 CTH-POMS 主采集
- 未改变主体/时间/风险/事件/报告口径
- 失败状态可解释
- 可独立关闭 App 能力
- 有测试、证据和回滚方案
- Core 与 DCC HEAD 二次核验完成

## 10. 冲突处理

如果任务要求与 `ZB-PROD-2026-08-31-04` 冲突：

`BLOCKED → 记录原因 → 提出合规替代方案 → 等待人工判断`

任何人不得通过“研究模式”“实验模式”“Shadow 模式”“临时补丁”“调试模式”等名称绕过本门禁。
