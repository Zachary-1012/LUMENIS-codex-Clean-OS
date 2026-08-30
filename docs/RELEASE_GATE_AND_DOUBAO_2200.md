# Release Gate & 豆包 22:00 施工门禁

## 目标
以当前稳定版本为唯一生产基线，在不破坏既有业务闭环的前提下完成公网化、统一运行环境、Ollama-only、Auth Recovery、采集风控状态机及双产品适配。

## P0：上线前必须通过
- 启动入口统一，不允许依赖机器全局 Python 的偶然环境；启动前执行依赖/运行时自检。
- Flask + Waitress 生产启动可重复执行；健康检查失败则禁止进入生产态。
- Playwright 与浏览器内核完整性检查。
- SQLite/数据库迁移前自动备份；迁移失败可回滚；禁止破坏既有数据。
- 6 个蓝图注册检查；核心 API Smoke Test。
- 现有 15 个 SPA + 话题监测独立页回归。
- 小红书 SUCCESS/EMPTY/BLOCKED/AUTH_FAILED/CAPTCHA/NETWORK_ERROR 六态保持；风控不得伪装为 0 条。
- Cookie/Session 在任何页面失效时进入系统内统一 Auth Recovery 弹窗；弹窗展示合法二维码/登录恢复入口（若当前平台只能人工完成验证，则明确提示人工验证），禁止无意义反复跳转。
- 300012/IP 风险触发降频、熔断、冷却、告警；不得绕过验证码或平台安全机制。
- Ollama 关闭/不可用时，核心采集、数据库、规则、事件、报告仍能运行；AI 只作为增强层。
- 原广州太古汇 SUBJECT_WORDS / SUBJECT_EXCLUDE_WORDS / subject_hit 及既有主体 SQL 过滤口径不得弱化。

## P1：功能闭环
- 双产品共用 Core，产品层隔离；客户→品牌→竞品→项目→事件数据边界明确。
- WHO/WHAT/WHAT HAPPENED/SO WHAT 四层模型保持：传播主体、内容、事件、品牌影响。
- subject_type 与 content_type 严格分离，禁止把 UGC 当账号身份。
- 营销事件/传播事件/舆情事件统一进入事件中心；event_relation 支持触发、衍生、继发、并行关系。
- 事件生命周期、主体画像、内容、消费者需求、品牌对标、报告链路可逐步旁路接入。
- AI Shadow Mode 只新增结果，不直接覆盖系统主判断；人工修正可沉淀为样本。

## P2：优化
- 手机端完整设置风格。
- 全站版本号、命名、注释统一。
- collector_v2 与现网采集器并行验证后再切换。
- 清理 tests 中临时诊断脚本。
- system_guardian / auto_recovery / data_feedback_loop 逐项验证后再启用。
- 微博/B站仅作为辅助源，先验证 Cookie 免登，不影响小红书主线。

## 豆包执行规则
1. 先读取 README、PROJECT_STATUS、CHANGELOG、本文件及最新 main；先审计后施工。
2. 不允许推倒重构，不允许删除现有稳定功能，不允许擅自改变数据库口径。
3. 每个补丁必须有测试；先单测，再 Smoke/E2E；失败自动停止，不得宣称完成。
4. 任何数据库结构修改先备份并提供迁移/回滚路径。
5. 任何采集器修改必须验证正常、无新数据、登录失效、验证码、300012、网络异常五类以上场景。
6. 完成后更新 CHANGELOG、PROJECT_STATUS 和开发日志，并提交清晰 commit。
7. 上线结论只能使用“测试通过/未通过”事实，不得使用无法验证的 100% 无错误承诺。
