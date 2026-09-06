# ZBIP 四产品执行日志｜2026-08-31

## 产品身份
- DCC｜Development Command Console｜开发控制/治理中枢
- SICI｜手机端智能开发平台
- CTH-POMS｜广州太古汇舆情监测产品（与 ZBMP 位于 Z-Brand 仓库）
- ZBMP｜Z-Brand Intelligence Platform｜品牌智能平台
- AI-D｜AI Development Research Hub｜AI 开发研究平台

## GitHub 自动识别规则
所有执行端必须自行识别 Git repository root、remote、owner/repository、branch、HEAD SHA，并与当前产品身份交叉核对。禁止仅依据目录名、旧聊天记录或人工猜测判断仓库。

身份不一致或无法确认：STOP；禁止写代码、commit、push、跨仓修改。执行前记录 BASE_COMMIT_SHA；远端 HEAD/branch 变化后必须重新读取并重新审计；禁止覆盖新变更、禁止 force push。

## 统一执行闭环
GitHub 当前状态 → 有效规则 → Excel 工单 → 源码映射 → 最小修改 → 测试 → Evidence → Push 1 Implementation → 重新读取 GitHub → 源码级 Audit → 规则/数据/Evidence 审计 → Push 2 Audit → 更新工单。

COMPLETED 必须同时满足实施、测试、Evidence、Push 1、重新读取 GitHub、Audit、Audit Evidence、Push 2；否则只能 PARTIAL / BLOCKED / FAILED / RESEARCH_PENDING / INSUFFICIENT_EVIDENCE。

## AI-D 核心治理
AI-D 是研究与能力发现平台。必须保持 Research → Evidence → Review → Capability Registry → Promotion → Production Reuse。没有独立 Evidence/Review 的研究结果不得自动生产化。

研究记录必须 append-only；不得覆盖或删除历史 Research/Evidence。敏感字段必须持续脱敏，包括 token、secret、password、cookie、authorization、api_key、private_key、session、credential 及组合凭证字段。

## 跨产品能力反哺
一个产品验证通过的采集、审计、UI、测试等能力，可以注册为 Shared Capability；其他产品只能引用 Capability ID、版本与来源，不直接复制研究源码。

## UI 母规范
四产品共享 ZBIP 母视觉语言：黑/白/灰、状态色小圆点、线性 Icon、Light/Dark、Mobile-first、精细状态反馈与统一交互语言。布局按产品功能和层级差异化，不为统一视觉而抹平业务结构。

## 安全运行底座
统一建设 Runtime Integrity Preflight：启动前检查产品身份、GitHub 来源、权限、依赖、配置、危险执行模式、数据保护、敏感信息过滤与能力状态；失败不得进入正常运行态。

## 本阶段 GitHub 事实
最新已知提交：f87f805f8d46d3aa16a04bfe27f1cf81f0379c12，R-2026-0005 收敛审计记录：records.jsonl append-only、历史记录保持、credential scan 0 hit、offline suite 101 pass/0 fail；研究状态仍需独立审计后再考虑 Promotion。
此前已记录 R-2026-0005 Phase1 四仓收敛审计、UI token、motion token、icon system、feature ownership 等研究资料。

> 本日志只记录已确认事实与执行纪律；后续变化追加新记录，不回写历史事实，避免时间线污染。
