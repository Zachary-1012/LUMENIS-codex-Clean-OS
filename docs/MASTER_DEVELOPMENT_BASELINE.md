# Z-Brand-Core 主开发基线（Master Development Baseline）

> 生效日期：2026-08-30
> 目的：统一 ChatGPT、豆包、本地 Ollama、Development-Command-Console 与本地开发环境对 Z-Brand-Core 的架构、优先级、边界和验收理解。
> 权威性：本文件是开发协作层的补充基线；源码、数据库、运行时和真实测试结果优先于文档快照。

## 1. 总体架构：一个 Core，CTH-POMS 为当前生产产品，ZBMP 为受控隐藏能力层

Z-Brand-Core 不是两个并列、长期独立维护的产品。

当前正确关系：

```text
                 Development-Command-Console
                     内部 AI 研发中枢
                              │
                              │ 审计 / 规划 / 测试 / 受控升级
                              ▼
                       Z-Brand-Core
                        核心技术底座
                              │
                              ▼
                         CTH-POMS
                    当前生产 / 客户交付入口
                              │
                              │ License / Key / Feature Gate
                              ▼
                    ZBMP 隐藏增强能力层
             多品牌 / 竞品 / Campaign / Brand Intelligence
```

- **CTH-POMS**：当前必须优先尽快稳定落地上线的生产系统，服务广州太古汇当前业务场景。
- **ZBMP**：不拆成第二套源码、不独立复制部署、不形成第二套 Core；它是 CTH-POMS 所在 Core 内受控的母平台能力层，需要合法授权密钥/功能授权后才可启用。
- **Development-Command-Console**：独立仓库，作为内部研发中枢服务 Z-Brand 整体持续升级；它不是 CTH-POMS 的运行时依赖，也不是生产业务系统。

## 2. 当前开发优先级（必须保持）

### P0：CTH-POMS 尽快稳定上线

目标：不推翻、不大重构当前可运行系统，优先完成生产可用闭环。

顺序：
1. 启动/依赖环境统一
2. 采集稳定性与 Auth Recovery
3. 主体口径、时间口径、风险/事件/报告回归
4. 数据安全与备份
5. HTTPS / 反向代理或 Cloudflare Tunnel 公网边界
6. 关键页面/API/E2E
7. 生产部署与上线验收

任何新平台能力若可能影响上述 P0，必须旁路、关闭或延后。

### P1：ZBMP 持续优化完善

ZBMP 继续在 Core 内建设，不阻塞 CTH-POMS 上线。

重点：
- Brand / Competitor / Campaign
- Brand Profile 与监测配置
- 传播主体六维画像
- 内容类型
- 营销 / 传播 / 舆情三类事件
- event_relation 与生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter 契约
- Ollama / AI Shadow / 样本与评测
- 新客户 Release 构建能力

ZBMP 能力必须通过配置、Feature Gate、授权和发布边界控制，不得要求 CTH-POMS 运行时依赖一个外部 ZBMP 服务。

### P1/P2：Development-Command-Console 同步建设

继续独立演进为 Z-Brand 内部 AI 研发中枢：
- GitHub 只读审计
- 任务结构化
- Local AI Bridge
- Evidence
- 测试结果读取
- 受控补丁生成
- 隔离分支
- 自动测试
- Diff 审计
- 人工批准
- PR / Release 验收

当前 v0.3 权限边界保持：READ / TASK / AUDIT = ALLOW；TEST = CONTROLLED；WRITE / DEPLOY = DENY。不得因为追求自动化而直接获得生产写权限。

## 3. 代码与数据边界

### CTH-POMS
- 当前真实生产链路为事实来源。
- 新 Adapter、AI 能力、ZBMP 能力均先旁路验证。
- 不得为了架构理想化而重写生产主链。
- 客户数据必须与实验/其他品牌数据隔离。

### ZBMP
- 与 CTH-POMS 共享 Core，不复制 Core 源码。
- 不单独建立第二套长期维护数据库/代码副本。
- 默认关闭；授权后按 Feature Gate/Runtime Mode 启用。
- 其能力不得改变 CTH-POMS 的核心业务口径。

### Development-Command-Console
- 独立仓库、独立部署、独立版本。
- 不连接生产数据库。
- 不成为 CTH-POMS 的运行时依赖。
- 负责研发审计与受控升级，不直接接管生产部署。

## 4. P0 业务红线

以下任何升级都不得弱化、删除、绕过：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `app.py` / `risk_engine.py` 的 `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- 所有下游 SQL、Dashboard、报告、专题统计的主体边界
- `publish_datetime` 与 `captured_at` 时间语义
- 历史生产数据库与业务数据
- 现有风险、事件、报告核心判断

采集异常、验证码、IP 风险、Session 失效等不得伪装为“0 条”。

## 5. AI 原则

- 正式生产 AI Runtime：Ollama-first / 本地化。
- 没有 AI 时，采集、主体过滤、去重、事件、风险、统计、报告仍必须运行。
- AI 是增强层，不是事实生命线。
- AI 输出必须可记录、可追溯、可人工修正。
- 新模型/新能力优先 Shadow Mode，不直接替换生产结论。
- 外部云端 AI 保持 Optional/Legacy，未经调用链确认不得贸然删除。

## 6. 数据与商业化边界

当前研发阶段可以利用真实业务场景进行系统设计和验证，但商业化时必须明确：
- 公司/客户数据的授权边界
- 个人方法论与公司资产的边界
- 原始数据、脱敏数据、统计特征和模型资产的边界
- 数据留存、导出、删除和客户隔离规则

不得把真实客户/公司敏感数据直接提交 GitHub。商业化发布前必须完成依赖许可证、SBOM、数据授权和隐私/安全审计。

## 7. 开发门禁

任何代码变更进入主分支前至少：
1. 读取最新源码和当前基线
2. 影响范围/冲突分析
3. 最小补丁
4. 语法/导入检查
5. 相关单测
6. 数据库迁移检查
7. 启动检查
8. API/蓝图检查
9. 关键页面 E2E
10. 控制台 JS 错误扫描
11. 主体/时间/风险/事件/报告口径回归
12. 安全敏感数据扫描
13. 记录变更、测试、未完成项和回滚方式

未完成真实验证不得标记为“已完成”。

## 8. 冲突处理规则

若不同文档、聊天窗口、AI 输出或历史版本发生冲突：

`当前源码/数据库/运行时实测 > 当前主基线 > 最新开发记录 > 历史文档 > 聊天中的旧结论`

特别是：历史文档中将 ZBMP 描述为独立“产品线/Release”的表述，在当前架构决策下仅表示能力域，不表示第二套长期独立产品。

## 9. 成功定义

当前阶段不是“把所有规划功能一次做完”。

成功定义为：

**CTH-POMS 先稳定上线；ZBMP 在不影响 CTH-POMS 的前提下持续增强；Development-Command-Console 同步成为安全、可审计、可回滚的内部研发中枢。**
