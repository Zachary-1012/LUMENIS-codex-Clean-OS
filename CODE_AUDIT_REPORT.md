# LUMENIS 完整源码审计汇总报告

状态：十二大类审计 Canonical Summary

## 1. 总结

当前仓库具备大量真实业务和工程资产，但还不是可发布的纯净生产版本。核心问题不是代码风格，而是多个候选实现、运行/数据库基线分裂、状态契约冲突、跨仓边界未收敛和发布证据缺失。

总判定：`SUBSTANTIAL ASSETS / MULTIPLE TRUTH OWNERS / CLEAN RUNTIME NOT VERIFIED / RELEASE NO-GO`

## 2. Backend

已确认：

- Flask 主应用与大量 Blueprint、API、Collector、Event、Risk、Report、AI、Agent、Runtime 模块存在；
- 旧扫描发现 504 Python 模块、4106 函数、375 类、589 路由候选；
- `app.py` 是高耦合主入口，历史扫描为 5886 行、262 函数、188 路由；
- 路由、初始化、数据库、后台任务和兼容注册存在导入期副作用；
- API response 使用 `ok/success/status/state/error` 多种模型；
- 22+ Blueprint 与 legacy/v2/v4/domain/viz 路径并存；
- 部分 Blueprint 有重复注册或未注册候选；
- `/api/status` 一次实测约 4.7 秒。

风险：单体入口使最小变更难验证；重复 API 和初始化副作用会产生顺序依赖、隐式写库和不同运行结果。

## 3. Frontend

已确认：

- 旧盘点含 60 路由、55 模板、28 JS、10 CSS 候选；
- CTH、Shared、SYSTEM 页面可访问；
- canonical BMP 路径 404；
- CTH 总览与 Runtime/API 对同一状态表达冲突；
- 页面存在旧 ZBMP、旧客户系统和英文后台语义；
- 页面未全部经统一 Truth Table/View Model；
- 旧页面只能做资产来源，不能作为新设计模板。

风险：当前最严重问题是假健康和上下文错配，不是视觉精度。

## 4. Database

已确认：

- 运行库、工作区库、清洁仓库库和便携包库并存；
- 运行库与清洁仓库不一致；
- 原工作区候选库有 43 条外键违规；
- Evidence/Canonical/Event/Metric/Report 存在多表或多模型候选；
- clean bootstrap 的 Migration 顺序曾失败；
- 测试会写入被 Git 忽略的清洁仓数据库；
- `.db` 不受 Git Diff 保护，clean status 不能证明数据未变。

风险：数据真相、测试隔离、迁移和发布血缘均不满足生产要求。

## 5. Collector / Browser / Runtime

已确认：

- Collector、Collector V2、Automation、Platform Adapter、CDP、Browser Surface 等并存；
- 当前 8202 使用 `--no-scheduler`；
- XHS 为 `SESSION_EXPIRED`，需要人工处理；
- 0 Worker、Guardian UNKNOWN；
- 当前页面仍显示采集运行中和正常；
- `D:\Taikoo-monitor-new` 通过 8201 与 9222 实际运行，但其 Health Summary、Collection Log、Guardian 和数据新鲜度互相冲突；
- 社交账号只读红线已定义，未发现本轮执行写操作。

风险：运行状态缺少唯一 owner，健康接口和业务页面可得出相反结论。

## 6. Evidence / Canonical / Metric / Report

已确认：

- Evidence Chain、Evidence Store、App Evidence 并存；
- Canonical Data 至少两套承载；
- Metric 可直接从 notes、canonical 或 snapshots 计算；
- Event 与 Event Graph 双体系；
- Report/Daily/Export/Brand/V4 多入口；
- 无数据时仍返回 50 分品牌健康度；
- AI 参与分析与报告，但全量字段隔离和回溯尚未证明。

风险：重复计算、时间口径不一致、AI 派生内容混入事实、报告无法逐数字回溯。

## 7. AI / Agent

已确认：

- AI Gateway、Provider Registry、fallback、breaker、AI log 存在；
- Permission、Security Boundary、Agent Boundary、Firewall、Fence、Evidence、Evaluation、Trace 构件存在；
- 不能证明所有用户任务经过唯一 Orchestrator；
- 不能证明所有生产写入口强制经过审批和幂等；
- 8202 AI 未启用；
- Ollama 审计调用成功，智谱/OpenCode 最近认证失败；
- Provider 配置存在不能作为 ACTIVE 证据。

风险：多个控制层并行时，旧调用方可能绕过新边界；AI 结果可能被误认为生产事实。

## 8. Security

P0 问题：

- 客户端可读取 Basic 凭据的历史接口设计；
- Permission 自动授权和高影响旁路；
- 多套权限实现优先级不唯一；
- Secret/Session/Browser/Auth 边界需要完整 E2E；
- CI 安全检查不是统一阻断门禁；
- Command 本地恢复文件被 Git 忽略，审计完整性不足。
- 8201 将 `/api/system/runtime`、`/api/system/health/summary` 和 `/api/auth/config` 列入 Basic Auth 例外；未认证请求可读取内部路径、数据库计数、Cookie/CDP 状态和调度信息。

安全声明必须由具体 ASVS 控制、攻击面测试、拒绝路径和 Runtime Evidence 支撑，不能使用“有 Security 模块”作为结论。

## 9. Dependencies / Supply Chain

已确认存在 requirements、容器、compose、脚本和 CI 资产，但：

- 依赖未形成唯一锁定与哈希；
- 无统一 SBOM、漏洞门禁、许可证门禁；
- compose 使用可变标签；
- 无 Build Provenance、签名 Artifact 和验证命令；
- 远程无可验证 Release/Tag 证据；
- 现有启动脚本含旧绝对路径。

## 10. Tests

已确认大量单元、集成、边界和 E2E 资产存在，部分专项测试通过；但：

- 测试通过不能证明当前 8202 或生产数据链；
- Windows 编码会导致边界测试失败；
- 存在 skip；
- 测试写入非临时 DB；
- GGI 当前提交测试无法收集；
- Command 存在集成、安全、E2E 和独立性失败；
- 缺少从新建空库、历史升级、生产副本迁移、回滚到长稳运行的统一 Gate。
- `Taikoo-monitor-new` 正连接真实业务库；因测试隔离未完成，本轮没有在该目录直接执行 pytest，避免再次污染生产候选数据。

## 11. 分类结论

| 分类 | 当前使用规则 |
|---|---|
| ACTIVE | 仅限七类证据完整且真实运行的唯一实现；当前不能批量继承旧标签 |
| DUPLICATE | 已证明同一输入产生同一业务输出；当前多为候选 |
| LEGACY | 仍有消费者的兼容实现，保留 |
| DEPRECATED | 替代路径、迁移窗口和退出条件已定义 |
| DEAD | 调用、数据、Runtime、测试均证明无消费者后才可标记 |
| UNKNOWN | 当前默认安全状态；继续审计，不删除 |

## 12. P0 问题清单

1. 固定唯一源码、进程、数据库和 Release 身份。
2. 隔离生产、测试、实验数据库并阻止测试污染。
3. 修复 clean bootstrap、历史升级和 rollback Migration。
4. 建立唯一 Evidence/Canonical/Metric/Truth/View Model 链。
5. 修复 UI 假健康与 BMP 路由/上下文。
6. 建立唯一 API State/Error Contract。
7. 收敛 Runtime Guardian、Collector 和 Auth 状态所有权。
8. 收紧认证、权限、Agent 写入和 Effect Fence。
9. 消除对 OSAI 内部模块的跨仓直接调用。
10. 建立不可变 Release Manifest、SBOM、Provenance、签名和回滚证据。
11. 让全部 Gate 在 UTF-8、临时 DB 和隔离 Runtime 下阻断式执行。
12. 在真实浏览器和真实数据副本上完成 CTH/BMP 验收。

## 13. 最终结论

Backend：`PARTIAL / MULTIPLE`

Frontend：`DESIGN BASELINE READY / RUNTIME BLOCKED`

Database：`BASELINE SPLIT / MIGRATION BLOCKED`

AI/Agent：`CONTROL ASSETS EXIST / ADMISSION NOT VERIFIED`

Security：`RELEASE GATE FAIL`

Tests：`SUBSTANTIAL / ISOLATION NOT TRUSTWORTHY`

Production：`NO-GO`
