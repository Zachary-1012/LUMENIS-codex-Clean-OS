> **SUPPORTING RELEASE SAFETY POLICY ? NOT A SECOND PRODUCT/EXECUTION AUTHORITY.**
> Root `AGENTS.md` owns execution, the sole Product Architecture owns scope, C6/W6 owns integration/runtime/release, and M owns final engineering acceptance. This file preserves release safety rules only; it cannot reduce functionality, create another product or redefine current status.
> Machine markers: `NO_SCOPE_REDUCTION_ON_RELEASE` / `SINGLE_PRODUCT_FOUR_SURFACES` / `C6_W6_RELEASE_OWNER`.

# RELEASE_POLICY.md

## 目标

所有升级必须以当前稳定版本为基线，优先增量、旁路和可回滚，不允许为了“架构漂亮”而破坏现有生产链路。

## 发布顺序

审计 → 设计 → 最小修改 → 单测 → 启动 → API → 数据库 → E2E → 真实数据抽查 → 版本记录 → 发布。

## 数据库保护

迁移前备份；新增优先；已有字段不得无理由删除/重命名；历史数据不得批量清空；任何破坏性迁移必须显式说明并提供回滚方案。

## 采集器切换

新采集器必须与现网采集器并行验证。未证明字段、时间口径、主体过滤、去重、错误状态和入库结果等价前，不得直接替换生产入口。

## 风控处理

小红书等平台出现验证、IP 风险、登录态失效时，系统进入明确状态并停止危险重试；不得将异常伪装成空数据，不得以破解验证码或绕过风控为目标。

## Session 失效体验

任何时候检测到 Cookie/session 失效，应在系统内显示可操作弹窗：平台、失效原因、当前任务状态、暂停/冷却、合法重新验证入口以及恢复采集操作。不得要求用户自己寻找登录入口。

## 双产品版本

Core 能力可以共享，但广州太古汇产品与品牌传播市场情报产品的发布、配置、客户数据和业务口径必须可追溯。

## 回滚

每个功能发布必须记录变更文件、数据库迁移、测试结果、已知风险和回滚路径。
