# XHS 账号安全事件：三方研发协作状态

> Incident ID: `XHS-SAFETY-2026-08-31-01`
> 状态：`ACTIVE / HARD FREEZE`

SICI-Core 作为研发协作/验证入口，不执行小红书采集，也不得通过研发任务间接重新启用被冻结的 XHS 自动化能力。

## 协作规则

1. 收到 XHS 账号安全警告后，所有相关自动化任务视为暂停。
2. SICI 只记录、汇总、验证证据，不执行规避平台检测的操作。
3. 不把“随机间隔、模拟真人、代理/IP切换、设备切换、多账号”等作为解决方案。
4. 研究只允许围绕官方授权 API/SDK、OAuth、公开允许的数据来源和用户主动提供的证据。
5. 任何恢复请求必须引用 Incident ID，并经过 Core + DCC 审计及人工批准。
6. 三方研发窗口必须共享同一冻结状态，避免一个窗口暂停、另一个窗口重新启用。

## 当前状态

`XHS collection = FROZEN`

`XHS App automation = BLOCKED`

`XHS Evidence = OFF until incident review`

## 解除条件

事件复盘完成、授权/规则核验完成、代码状态核对完成、测试证据齐全、DCC 审计通过、人工批准后才允许提出恢复方案。
