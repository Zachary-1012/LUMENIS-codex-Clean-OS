# Z-Brand-Core 当前协作基线

> 生效日期：2026-08-30
> 当前版本：以最新源码与运行时为准（当前 GitHub 主线已进入 v5.8.6 同步链）
> 主开发基线：`docs/MASTER_DEVELOPMENT_BASELINE.md`
> 原则：以仓库实际代码、数据库、运行日志和测试结果为准；聊天记录只能作为需求来源，不能替代源码事实。

## 1. 当前最高优先级

### P0：CTH-POMS 尽快稳定落地上线

当前主力生产/客户交付系统是 CTH-POMS（广州太古汇舆情监测系统）。本阶段优先完成：

- 启动与依赖环境统一
- 小红书采集稳定性、Auth Recovery、风控熔断/冷却
- 主体/时间/风险/事件/报告口径回归
- 数据安全、备份与恢复
- HTTPS / 反向代理或 Cloudflare Tunnel 公网边界
- 关键 API、页面与 E2E 验收
- 生产部署与上线验收

任何 ZBMP、Adapter、AI 或研发平台能力，只要可能影响 CTH-POMS P0 稳定性，必须旁路、关闭或延后。

### P1：ZBMP 持续优化完善

ZBMP **不是第二套独立长期维护的产品/源码项目**。它是 Z-Brand-Core 内部的母平台增强能力层，在 CTH-POMS 中通过合法密钥/License/Feature Gate 等受控方式启用。

持续建设：

- 客户 / 品牌 / 竞品 / 项目 / Campaign
- Brand Profile 与监测配置
- 传播主体六维画像
- 内容库与内容类型
- 营销 / 传播 / 舆情三类事件
- `event_relation` 与事件生命周期
- 消费者需求洞察
- 品牌对标
- 多平台 Adapter
- Ollama / AI Shadow / 样本与评测
- 新客户 Release 构建能力

禁止把 ZBMP 拆成第二套 Core 长期维护，也禁止让 CTH-POMS 运行时依赖外部 ZBMP 服务。

### P1/P2：Development-Command-Console 同步建设

`Zachary-1012/Development-Command-Console` 是独立仓库，定位为 Z-Brand 内部 AI 研发中枢，不是 CTH-POMS 生产运行时依赖。

当前 v0.3 已具备 GitHub 只读审计、Local AI Bridge、Evidence、权限矩阵和安全边界；后续继续向“需求 → 分析 → 受控补丁 → 隔离分支 → 测试 → Diff 审计 → 人工批准 → PR/Release 验收”演进。

当前安全边界保持：READ / TASK / AUDIT = ALLOW；TEST = CONTROLLED；WRITE / DEPLOY = DENY。不得为了自动化直接开放生产写入、自动 Merge 或自动部署。

## 2. 正确总体架构

```text
Development-Command-Console
        │
        │ 内部研发审计 / 规划 / 测试 / 受控升级
        ▼
Z-Brand-Core
        │
        ▼
CTH-POMS（当前生产 / 客户交付入口）
        │
        │ 合法 Key / License / Feature Gate
        ▼
ZBMP（Core 内隐藏增强能力层）
```

这是一个 Core、一个生产产品入口、一个受控隐藏能力层；不是两个并列产品。

## 3. 生产原则

- 当前生产系统继续使用已验证的现有采集主链。
- 新 Adapter 只做边界封装，不重复业务逻辑；未通过完整回归前不得接管生产任务。
- 小红书为当前 PRIMARY 平台。
- 抖音为 SECONDARY 规划平台；当前 Adapter 保留但未验证前不得启用。
- 快手、B站、微博、贴吧、知乎仅保留扩展槽位，不进行本阶段深度开发。
- 不推翻现有系统；采用“审计 → 兼容 → 旁路 → 验证 → 切换”。

## 4. 核心业务红线

不得修改、弱化、绕过：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `app.py` / `risk_engine.py` 的 `_subject_sql_and_values()`
- `aggregate_events()` 主体过滤
- `build_daily_report()` 主体过滤
- `publish_datetime` 与 `captured_at` 时间语义
- 历史数据库及生产数据
- 现有风险 / 事件 / 报告核心判断

系统不能因为 AI、Adapter、网络异常、验证码、300012、IP 风险或 Session 失效而伪装成“0条”。

## 5. AI

- 正式生产 AI Runtime：本地 Ollama。
- 生产系统不得依赖豆包/OpenAI/其他云端大模型 API 才能运行。
- 历史外部 AI 代码先标记 Legacy/Optional、确认调用链，再决定清理。
- AI 不能单独决定主体最终归属、真实发布时间、统计数量、报告周期、原始数据真实性和核心风险口径。
- 新 AI 能力优先 Shadow Mode，并保留模型版本、Prompt 版本、输入摘要、结果、置信度、是否采纳、人工修正等审计信息。

## 6. 数据与安全

- `.db/.sqlite/.sqlite3`、迁移、seed、备份、导入导出、ORM Model 均属于数据资产。
- 未经明确授权不得删除、清空、重建或覆盖生产数据库。
- 新表/字段优先向后兼容迁移。
- 客户 Release 不得携带其他品牌/客户实验数据。
- Cookie、Token、API Key、Secret 不得进入 GitHub、前端、日志、测试样例或数据库初始化脚本。
- 商业化阶段必须明确原始数据、脱敏数据、统计特征、模型资产及公司/客户授权边界。

## 7. 采集调度与 Auth

采集频次不以历史固定“30/20分钟、自动9次+手动3次”等数字作为永久硬编码规则。生产调度根据健康度、数据量、连续成功、风险状态和冷却状态动态决定。

风控链路：

`识别 → 停止危险请求 → 记录 → 熔断 → 冷却 → 健康检查 → 合法人工验证 → 逐步恢复`

不得破解验证码、绕过安全验证或对抗平台风控。

Cookie/session 失效时进入全局 Auth Recovery 流程，不简单跳转登录页，不把失败显示成 0 条。

## 8. 时间与数据质量

- `publish_datetime` = 内容实际发布时间。
- `captured_at` = 系统采集时间。
- 报告、日历和周期统计默认按 `publish_datetime`。
- 相对时间必须在采集解析层可靠归一化；无法可靠归一化时标记不确定状态。

## 9. GitHub → 豆包 / 内部研发中枢升级流程

`最新源码检查 → 读取主基线 → 影响范围/冲突分析 → 最小补丁 → 测试/回归 → 安全检查 → 提交 → 再读取 HEAD 二次核验`

GitHub 不是生产覆盖源。任何远端更新不得自动覆盖正在运行的生产代码。

Development-Command-Console 的升级权限必须继续受控；它负责研发过程，不直接成为生产部署器。

## 10. 完成定义

一次升级只有在以下全部满足时才算完成：

- 代码可导入/启动
- 关键单测通过
- 数据库迁移检查通过
- 生产数据未删除/覆盖
- 主体口径回归通过
- 时间口径回归通过
- 采集异常状态可解释
- 新平台未误接管生产
- 没有新增敏感凭据进入 Git
- 变更、测试、未完成项和回滚方式有记录
- 若涉及 CTH-POMS，不能因为 ZBMP/AI/研发平台而降低上线优先级

## 11. 权威性与冲突处理

发生文档、聊天记录、AI 输出或历史版本冲突时：

`当前源码/数据库/运行时实测 > MASTER_DEVELOPMENT_BASELINE.md > CURRENT_BASELINE.md > 最新开发记录 > 历史文档 > 旧聊天结论`

历史文档中把 ZBMP 写成“产品 B / 两条产品线 / 两种 Release”的表述，在当前架构下只表示能力域/Release 能力，不表示第二套独立长期维护产品。