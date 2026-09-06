# ZBIP 四产品执行日志｜2026-08-31

## 目的
本文件用于收敛本阶段四产品开发、审计、安全加固、UI/交互、GitHub 长期运行与跨产品能力反哺规则。它是执行记录，不替代产品业务基线。

## 四产品身份
- DCC｜Development Command Console｜开发控制/治理中枢
- SICI｜手机端智能开发平台
- CTH-POMS｜广州太古汇舆情监测产品（与 ZBMP 位于 Z-Brand 仓库）
- ZBMP｜Z-Brand Intelligence Platform｜品牌智能平台
- AI-D｜AI Development Research Hub｜AI 开发研究平台

## GitHub 自动识别规则
执行端必须自行识别当前 Git repository root、remote、owner/repository、branch、HEAD SHA，并与当前产品身份交叉核对。不得仅依据目录名、旧聊天记录或人工猜测判断仓库。

若产品身份、Git remote、GitHub repository、branch 或 HEAD 无法一致确认：STOP；禁止写代码、commit、push 或跨仓修改。

执行前记录 BASE_COMMIT_SHA；若执行过程中远端 HEAD 或 branch 发生变化，必须重新读取并重新审计，禁止覆盖新变更，禁止 force push。

## 统一执行闭环
1. 读取 GitHub 当前仓库实际状态。
2. 读取当前有效规则、Baseline、Supplement、产品规则与 Capability 约束。
3. 形成 Effective Rules。
4. 将 Excel 工单映射到当前源码与现状。
5. 已完成项只验证，不重复开发。
6. 待处理项按 P0→P1 执行。
7. 最小修改面、增项优先、保持向后兼容。
8. 测试与安全验证。
9. 生成 Evidence。
10. Push 1：Implementation。
11. Push 1 后重新读取 GitHub 与最新有效规则。
12. 进行源码级 Audit、规则审计、数据安全审计、Evidence 审计。
13. Push 2：Audit。
14. 更新工单状态。

COMPLETED 必须同时满足：实施、测试、Evidence、Push 1、重新读取 GitHub、Audit、Audit Evidence、Push 2。否则只能标记 PARTIAL / BLOCKED / FAILED / RESEARCH_PENDING / INSUFFICIENT_EVIDENCE。

## 跨产品能力反哺
优秀能力不得复制粘贴跨仓传播。统一走 Research → Evidence → Review → Capability Registry → Promotion → Production Reuse。其他产品引用 Capability ID、版本与来源，不直接复制研究代码。

## 安全运行底座
统一建设 Runtime Integrity Preflight：启动前检查产品身份、GitHub 来源、权限、依赖、配置、危险执行模式、数据保护、敏感信息过滤与能力状态；Preflight 失败不得进入正常运行态。

## 本阶段已确认的真实问题与处理
- DCC：CORS null/unknown source、请求体超限状态收敛、安全响应头、Reusable Workflow 输入边界、GitHub Actions SHA 固定与启动 Preflight 已进入安全加固流程。
- SICI：Service Worker 已收紧为静态资源白名单缓存，避免任意动态 GET/API 响应进入 Cache。
- Z-Brand：已记录产品独立化、GitHub 长期运行、CTH-POMS/ZBMP 身份映射、ZBIP UI/架构收敛与跨产品边界；后续严格按产品身份执行。
- AI-D：R-2026-0005 已记录四仓收敛审计；研究记录保持 append-only；未通过独立 Review 的能力不得自动 Promotion。

## UI/交互统一原则
四产品共享 ZBIP 母视觉语言：黑白灰、状态色小圆点、线性 Icon、Light/Dark、Mobile-first、精细状态反馈与统一交互语言。信息架构与布局根据产品层级/功能不同适配，禁止为了视觉统一而抹平业务差异。

## 执行纪律
禁止猜测、禁止跨仓窜台、禁止删除历史 Evidence/Research 数据、禁止用新任务覆盖旧业务规则、禁止将未验证研究结果标记为生产能力、禁止把 Token/Cookie/Secret 写入 Git、禁止跳过 GitHub 状态核对、禁止跳过 Audit、禁止一次 Push 后直接宣布完成。

## 当前 GitHub 事实记录
- DCC main 最新已知提交：cc9145c165e69ff8985b18be0260204f3b59d926；另有独立 security/runtime-preflight-hardening 安全加固分支与 Draft PR，避免与主线业务变更混淆。
- SICI 最新已知提交：46079f25cd1206f2d34bb53a7be0da35412e6458；该提交记录了跨仓串台事故及防再发硬门禁。
- Z-Brand 最新已知提交：d06c4c2bd93f975f37f5ddfae75b976da342c104；记录产品独立化与 GitHub 长期运行规则。
- AI-D 最新已知提交：f87f805f8d46d3aa16a04bfe27f1cf81f0379c12；记录 R-2026-0005 收敛审计结果。

> 本日志只记录已确认事实与执行纪律；后续变化必须追加新记录，不得回写历史事实造成时间线污染。
