# ZBC 0点收口目标 + 自动运行验收 + 变更冻结 V1.0（2026-09-06 21:30）

## 一、时间目标
- 现在 21:30，目标**今晚 00:00（约2.5h）**前达到"系统可自动运行"并完成本轮精细化收口。
- 优先级：先保双域主链**无人值守自动运行**（约22:45–23:00），再补 P2/审计矩阵/commit/PR（力争0点前）。
- 时间不够时：保主链与已派 P0/P1，次要项如实标 PARTIAL/BLOCKED，**绝不造假写 VERIFIED、不降低验收**。

## 二、"系统可自动运行"验收（无人值守、可恢复，必须真跑）
1. 一条幂等启动命令（scripts\start_production.ps1）拉起全链：配置加载→DB迁移/初始化→系统自检→调度器/Runtime Guardian 自启→采集 worker→AI failover→API→前端，无需手动逐步触发。
2. /healthz 与各组件(DB/Scheduler/Collector/AI/Guardian)健康状态真实可信，不写死。
3. 调度器按计划自动运行；采集按 product/domain 自动执行，状态机 STARTING/RUNNING/DEGRADED/FAILED/STOPPING/STOPPED/RECOVERING 真实。
4. 异常自恢复：采集/worker 崩溃→Guardian 检测→有限重试(上限+退避+熔断)→DLQ→checkpoint 续跑；防重复任务/僵尸worker/假运行/无限重启/死循环。
5. 进程崩溃可被自动重新拉起；服务或机器重启后一键自启、从 checkpoint 恢复且不重复采集。
6. AI 自动 failover：智谱(glm-5.3/4.5-air)→豆包ARK(最小兜底)→Ollama(qwen2.5-coder:7b-agent)→local_rule，缺凭证显式降级不崩。
7. 双域主链都自动通：ZBMP(Data→Canonical→Domain→AI→Risk→Evidence→Report→UI)、CTH(Xiaohongshu→subject红线→Domain→…→UI)。
8. 异常显式化+日志可定位(哪个任务/worker/函数/输入/阶段/错误)，禁止吞异常、假成功；缺失显式 null/unknown/missing。
9. 关机重启恢复演练：stop→start→recovery 真实通过。

## 三、0点达标后变更冻结（用户明确）
达标即进入**维护模式**，后续只做两类：①bug 修复 ②数值/文案/样式/阈值等微调。
**冻结（除非修 bug 必需且经用户同意）**：架构变更、新增大模块/大功能、大规模重构、换技术栈、改 DB 表结构(必须护历史数据)、恢复旧 UI、推翻双域/账户/设置已定方案。任何超出"修bug+微调"的改动必须先报用户同意，不得自行扩张。

## 四、收尾交付
- 全量 pytest 真实结果(X passed/failed/skipped)、路由注册数、commit SHA、分支、PR。
- ZBMP/CTH/System × 各能力验收矩阵，逐项 PASS/PARTIAL/BLOCKED+证据；外部缺凭证列 Known External Blocks。
- 变更文件清单与"复用来源/如何适配"说明；无个人绝对路径、无假数据、无关键断链。
