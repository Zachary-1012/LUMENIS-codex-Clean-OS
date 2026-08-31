# 三仓库统一系统矩阵

Z-Brand-Core 的跨仓库 Contract / Version Truth / Runtime / Evidence / Dependency 统一协调矩阵由 Development-Command-Console 维护：

`Development-Command-Console/docs/THREE_REPOSITORY_SYSTEM_MATRIX.md`

本文件仅作为 Z-Brand-Core 的入口指针，不复制矩阵内容，避免三份文档漂移。

## Z-Brand-Core 责任边界

- 业务/品牌/舆情/生产数据真相由本仓库负责。
- CTH-POMS 是当前生产/客户交付入口。
- ZBMP 是 Core 内受控能力层，不形成第二套 Core。
- 主体、时间、风险、事件、报告等生产口径不得被跨仓库优化弱化。
- DCC 只负责工程协调、验证、Evidence 与 Release Gate，不成为本仓库运行时依赖。
- SICI 只负责移动交互与用户工作流，不成为本仓库生产运行时依赖。

任何跨仓库修改先读取统一矩阵，再按本仓库 Master Development Baseline 执行最小增量变更。
