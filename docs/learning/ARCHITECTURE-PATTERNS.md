# ARCHITECTURE-PATTERNS · 可吸收的架构模式（映射到 ZBP）

> 只沉淀模式，不在本轮改生产代码。每条标注：来源 / 模式 / 落到本仓哪里 / 是否动生产。

## P1. Catalog 实体模型（来源 Backstage，LR-001）
- 模式：Component / System / API / Resource / Owner，关系 dependsOn / providesApi / consumesApi / partOf。
- 落到：FEATURE-REGISTRY（Feature）↔ ASSET-REGISTRY（Asset/模块）↔ CAPABILITY-OWNERSHIP（Owner）↔ 路由（API）↔ 51 表（Resource）。建议把四张 Markdown 总账的 ID 互相外键化（文档层即可，先不建库）。
- 动生产：否。

## P2. Adapter / Port（来源 Crawlee、本仓 platform_adapters）
- 模式：Core 只认统一 `CollectionResult`；平台差异封到 XHS/Douyin/… Adapter，独立 Session/状态机/冷却。
- 现状：platform_adapters 已有 base/registry/config/xhs/douyin 骨架；collector_v2 旁路。坚持"新 Adapter 先旁路、回归+灰度后才接管"。
- 动生产：否（继续旁路原则）。

## P3. Provider 端口（AI 可替换）
- 模式：业务层只调 analyze/summarize/classify，背后 Ollama（正式）/云端（Legacy 默认关）/本地规则兜底可换。
- 现状：intelligence.py 编排 + ai_analyzer 执行 + 规则兜底（无 AI 全链可跑）。坚持 AI 仅增强、不决定平台风控/主体/统计/最终风险。
- 动生产：否。

## P4. 显式状态机（采集韧性）
- 模式：SUCCESS/NO_NEW_DATA/RISK_WARNING/NEED_VERIFY/BLOCKED/AUTH_FAILED/NETWORK_ERROR/COOLING_DOWN + 熔断 CLOSED/OPEN/HALF-OPEN（学 circuitbreaker 命名，不引库）。
- 关键：状态驱动 next_run_at；风险信号→停→记→熔断→冷却→健康检查→合法人工验证→小流量恢复；平台之间相互隔离。
- 落库：collection_logs + schedule_decisions 记录 scheduler_decision（"为什么没采"可回答）。
- 动生产：否（SCHED-01 影子转门控需用户签字）。

## P5. 统一 Contract（API / 响应 / 错误）
- 模式：统一 `/api/v1/...` 版本前缀、统一响应包 `{ok,data,error,status}`、统一分页、错误码与采集状态对齐（异常不伪装 0 条）。
- 现状：/api、/api/v2、/v4 多代并存。策略：新接口走 v1 契约，旧接口 LEGACY 保留到前端切换，不一次性重写。
- 动生产：否（登记 OPT-API-CONTRACT）。

## P6. Evidence / Provenance 链（来源 in-toto/SLSA，LR-003/004，详见 EVIDENCE-PATTERNS）

## P7. 变更单 + 版本绑定（来源 Changesets，LR-011）
- 模式：一次改动 = 一个 Change Map（影响模块/仓库/依赖/风险/测试/回滚）→ commit → changelog，可回滚。
- 落到：consolidation CHANGE-MAP + 版本中心；高危运行代码入口收敛（/api/developer/run 等三套只留一个受控）单列安全工单。
- 动生产：否。

## P8. ADR 决策固化（LR-002）
- 重大决策写 `docs/adr/NNNN-title.md`（Context/Decision/Status/Consequences），Superseded 不删除、只链到新决策，解决"多份 BASELINE 各说各话"。
- 动生产：否。

## P9. 分层但不搬目录
- 目标分层 core/domain/collectors/services/web/jobs/tests/docs 只做**映射**（ARCHITECTURE-MAP 已做）；物理搬迁必须 import/route/template/static/test/deploy 全绿才允许，当前不搬。

## P10. 幂等 / 去重 / 增量 / 连接复用（效率）
- 采集：URL+平台 ID 幂等去重（已有）、增量翻页、会话/浏览器 context 复用、按需启动浏览器、批处理入库，减少重复浏览器启动与重复 AI 调用（AI 结果缓存 key=内容hash+模型+prompt版本）。
- 动生产：否（登记 OPT-EFF-*，择期旁路验证）。

## P11. 三仓职责与依赖方向（不可变）
- ZBP=生产 SoT；DCC=治理 SoT（Audit/Contract/Gate/Evidence/Release）；SICI=研究/执行表面。依赖方向只允许 SICI/DCC → 产出规范/证据 → 供 ZBP 参考；**DCC/SICI 永不成 CTH-POMS 运行时依赖**。
