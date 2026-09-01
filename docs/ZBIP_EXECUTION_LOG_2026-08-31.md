# ZBIP 四产品执行日志｜2026-08-31

## 产品身份
- DCC｜Development Command Console｜开发控制/治理中枢
- SICI｜手机端智能开发平台
- CTH-POMS｜广州太古汇舆情监测产品
- ZBMP｜Z-Brand Intelligence Platform｜品牌智能平台
- AI-D｜AI Development Research Hub｜AI 开发研究平台

> 本仓库承载 CTH-POMS 与 ZBMP；两者业务身份独立，禁止窜台。

## GitHub 自动识别与绑定
执行端必须自行识别 Git repository root、remote、owner/repository、branch、HEAD SHA，并与当前产品身份交叉核对。禁止仅依据目录名、旧聊天记录或猜测判断仓库。

若产品身份、Git remote、GitHub repository、branch 或 HEAD 无法一致确认：STOP；禁止写代码、commit、push 或跨仓修改。执行前记录 BASE_COMMIT_SHA；远端 HEAD/branch 发生变化必须重新读取与审计；禁止覆盖新变更、禁止 force push。

## 统一闭环
GitHub 当前状态 → 有效规则 → Excel 工单 → 源码映射 → 最小修改 → 测试 → Evidence → Push 1 Implementation → 重新读取 GitHub → 源码级 Audit → 规则/数据/Evidence 审计 → Push 2 Audit → 更新工单。

COMPLETED 必须同时满足实施、测试、Evidence、Push 1、重新读取 GitHub、Audit、Audit Evidence、Push 2；否则只能 PARTIAL / BLOCKED / FAILED / RESEARCH_PENDING / INSUFFICIENT_EVIDENCE。

## CTH-POMS
保持广州太古汇生产业务口径与既有生产红线；UI/交互可按 ZBIP 母规范重新建设，但不得借 UI 重构改变采集、主体过滤、风险口径等既有业务逻辑。

## ZBMP
保持品牌智能平台独立定位；UI/交互采用 ZBIP 母视觉语言，但信息架构按品牌监测业务组织。共享能力必须通过 Capability Registry 引用，不复制其他产品研究源码。

## 采集能力边界
香港 RedNote/Note 当前作为主要采集研究/运行来源；国内账号阶段性暂缓，恢复后再做双账号交叉采集。禁止绕过访问控制、验证码或封禁机制；授权信息不得进入 Git、README、日志、Evidence 或前端 Bundle。

## UI 母规范
黑/白/灰、状态色小圆点、线性 Icon、Light/Dark、Mobile-first、精细状态反馈、统一交互语言；产品布局因功能与层级不同而不同，视觉统一不等于业务结构统一。

## 跨产品反哺
Research → Evidence → Review → Capability Registry → Promotion → Production Reuse。禁止未经验证的能力直接生产化；引用必须带来源 ID 与版本。

## 安全运行底座
统一接入 Runtime Integrity Preflight：启动前检查产品身份、GitHub 来源、权限、依赖、配置、危险执行模式、数据保护、敏感信息过滤与能力状态；失败即阻断正常运行。

## 本阶段 GitHub 事实
最新已知提交：d06c4c2bd93f975f37f5ddfae75b976da342c104，记录产品独立化、GitHub 长期运行规则、产品 AI 分工、松耦合通信与共享退出判据。
此前已记录 ZBIP unified convergence、mobile design token、弹窗精简与 UI 母规范等变更。

> 本日志只记录已确认事实与执行纪律；后续变化追加新记录，不回写历史事实，避免时间线污染。
