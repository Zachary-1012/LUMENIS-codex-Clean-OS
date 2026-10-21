# 聚合页加载适配合同（新底层实现）

`src/feed-pages.mjs` 是独立前端控制器，不是新的业务服务或产品API。已接入demo72人工异步分页界面，未连接真实Collector/Canonical接口。不能把此模块测试说成平台分页已实现。

输入：注入readPage(query,{signal})、authorize(query)、validateRecord(record,query)。authorize默认拒绝，validateRecord默认拒绝。scope只说明请求上下文，本身不授予权限；真实应用必须由既有Owner提供当前有效的身份/范围授权和字段验证。测试内的true函数仅明确人工fixture。

query包含scope、platform、opaque cursor与limit。响应包含items、nextCursor、hasMore、total；未知总数保持null。此为前端适配器内部协议，实际服务端字段由原Owner转换，未创造生产endpoint。单页1–100条、默认最多载入10000条是机制边界，不是全部产品容量。

状态：UNBOUND→IDLE→LOADING→READY/EMPTY/ERROR/NO_PERMISSION；用户cancel进入CANCELLED，可明确重试。读取前后均重新核Owner授权；撤权会清已载入材料。换scope/platform、取消、撤权与dispose撤销AbortSignal并递增generation，晚到回复不得写回。失败保留此前有效材料与cursor，重试同cursor，不悄悄跳页。重复ID、越界页、游标不推进、坏total或未验证记录整页拒绝，不部分混入。外部异常细节不直接显示，只回稳定安全代码。

九个实际Node测试覆盖：UNBOUND/权限缺失不调用reader、异步失败重试、范围更换迟到回复、取消/释放/撤权、坏页/重复/不推进、并发与容量、默认验证拒绝、异常详情不泄漏、验证回调中撤权也不能迟到提交。

72已接入同一材料阅读与恢复路径，8条挂载测试及7条原断言的异步迁移实际通过。后续仍须与当前产品工作树的实际Owner协议核对，做真实API/权限/重开/浏览器验收。当前模块不增加新入口数或“已完成交互”数量。
