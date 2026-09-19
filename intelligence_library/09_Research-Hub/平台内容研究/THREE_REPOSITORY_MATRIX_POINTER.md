# 三仓库统一系统矩阵

SICI-Core 的跨仓库 Contract / Version Truth / Runtime / Evidence / Dependency 统一协调矩阵由 Development-Command-Console 维护：

`Development-Command-Console/docs/THREE_REPOSITORY_SYSTEM_MATRIX.md`

本文件仅作为 SICI-Core 的入口指针，不复制矩阵内容，避免三份文档漂移。

## SICI-Core 责任边界

- 手机/云端开发控制台与移动交互真相由本仓库负责。
- 浏览器运行时能力必须按真实能力声明；当前浏览器 E2E 模拟不得表述为真实服务器 E2E。
- GitHub/API 访问保持最小权限，不把浏览器能力升级为机器级 Runtime 权限。
- DCC 负责工程控制、权限、验证与 Evidence，不复制 SICI UI 逻辑。
- Z-Brand-Core 负责业务/生产真相，SICI 不直接拥有其内部业务逻辑。

任何跨仓库修改先读取统一矩阵，再按本仓库现行基线执行最小增量变更。
