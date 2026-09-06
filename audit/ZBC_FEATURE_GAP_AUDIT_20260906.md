# ZBC 核心功能缺口全量清单（2026-09-06 审计）

> 审计范围：仅 ZBC（Z-Brand-Core / 序境）核心功能，排除 OSAI/components/GGI/LUMENIS Command 等外部项目。
> 审计方法：功能注册表扫描 + IC队列盘点 + 前后端API对比 + 文档交叉验证 + 代码存在性检查。
> 状态定义：MISSING=完全不存在 | PARTIAL=有代码但未完成 | UNWIRED=完成了但没接入前端/后端 | PENDING=已定计划未开始 | BLOCKED=外部条件阻塞。

---

## 一、完成了但没接入前端/后端（UNWIRED）

### 1.1 函数驱动动态可视化 xujing-viz.js
- **状态**：UNWIRED（文件存在，44个函数，16KB，但零页面引用）
- **位置**：`static/js/xujing-viz.js`
- **问题**：白皮书标记"已实现"，Hard Reset 后没有任何模板页面引用此文件
- **需做**：在 LUMENIS 前端页面中接入 xujing-viz.js，绑定真实数据（指标时间序列 API `database.py:546` / `data_query_api.py:95`），验证渲染/联动/下钻/实时更新/移动端
- **线索文档**：`序境/01-PRODUCT/VISUALIZATION_REGISTRY_V1.md`、`02-ARCHITECTURE/UNIFIED-DATA-INTELLIGENCE-PIPELINE-V1.0.md`

### 1.2 广告智能 ad_intelligence
- **状态**：PARTIAL（框架完整，4个平台API全部待实现，返回空数据）
- **位置**：`ad_intelligence/platforms/`
- **待实现平台**：
  - `jiguang.py` — 极光，API调用待实现
  - `meta_ads.py` — Meta Ads，需access_token+代理
  - `ocean_engine.py` — 巨量引擎，需access_token签名
  - `x_ads.py` — X(Twitter) Ads，需OAuth 1.0a签名+代理
- **已有**：base.py / permission_gate.py / platform_registry.py / analytics / models / strategy 框架
- **需做**：各平台真实API对接，或明确标记 BLOCKED 并给出接入条件

### 1.3 Podcast 模块
- **状态**：PARTIAL（9个intelligence文件已实现，后端路由已注册，需确认前端页面）
- **位置**：`podcast/intelligence/`（breakout/content_yield/episode_runtime/learning/research_levels/research_pipeline/story_nodes/topic_score/topic_scoring）
- **后端**：`app.py:258-259` 已注册 `podcast_routes.register_podcast_api(app)`
- **需做**：确认前端是否有播客页面/导航入口，数据是否真实展示

---

## 二、已定契约但未实施（IC队列 P1）

| IC | 主题 | 契约状态 | 落点 | 优先级 |
|---|---|---|---|---|
| IC-021 | EMV 指标 | ✅ PCCC §二 已定 | 报告系统 / FUNC-CONTENT-04 | P1 |
| IC-039 | 跨文化本地化框架 | ✅ PCCC §四 已定 | scripts/localization_guard.py | P1 |
| IC-040 | KOS 兴趣图谱信号 | ✅ PCCC §五 已定 | kos_engine 策略适配 | P1 |

---

## 三、待 Contract 后实施（IC队列，与ZBC核心直接相关）

| IC | 主题 | 优先级 | 反哺对象 |
|---|---|---|---|
| IC-035 | OWASP Agentic Top10 安全清单 | **高** | AI 治理/审计红线 |
| IC-044 | 耸动/合成内容风险信号 | 中 | 舆情告警（与IC-020联动） |
| IC-048 | 可视化质量门清单 | 中 | 可视化/UI |
| IC-029 | NPS/DRI 评价维度 | 中 | KOS/报告 |
| IC-033 | 情绪唤醒度维度 | 中 | KOS/舆情 |
| IC-041 | 达人分层运营策略 | 中 | KOS 分层 |
| IC-031 | AI Semantic Layer 运行时拦截 | 中 | AI/Canonical |
| IC-030 | 播客八步 SOP 资产化 | 中 | Podcast |
| IC-032 | 模型压缩候选评估 | 中 | ai_channel |
| IC-036 | 品牌命名评估管线 | 中 | 英文 Brand 研究 |
| IC-042 | 定制说服故事线 | 中 | 创意引擎 |
| IC-043 | 长任务可靠性方法论 | 中 | 自研 AI |
| IC-045 | 品牌叙事世界建设 | 中 | 品牌/播客 |

---

## 四、未收尾的并行轨道（PENDING-PARALLEL-TRACKS）

### Track A · ai_api 拆分收尾
- **状态**：PARTIAL（ai_api.py 已拆分，app.py 残留 1 个路由待迁）
- **残留**：`app.py` 中 `@app.route('/api/ai-learning/optimization/<operation_type>')`（约 L1775）
- **待办**：迁移残留路由 → 全量回归 → OpenAPI更新 → 删除临时文件

### Track B · 智谱 24h 保活 / 多层通道 / 编码转换
- **状态**：PENDING
- **待办**：API连接保活/心跳/断线重连（指数退避+上限）、主通道+备用+降级（豆包最小兜底）、编码转换（UTF-8/流式/特殊字符）、额度分配、可观测（连接状态/最后成功/失败计数/熔断）

### Track C · 39 个测试失败收敛
- **状态**：KNOWN（全量 pytest FAILED=10 / ERROR=29）
- **失败分布**：test_kos_ops ×9 ERROR、test_kos_paid ×11 ERROR、test_dev_exec_guard ×9 ERROR、test_idea_sit_backing ×7 FAILED、test_database ×1、test_evidence_export ×1、test_lean_footprint ×1
- **根因**：sqlite3 共享临时库污染、环境/权限、案例库数据、表结构

---

## 五、PROJECT_STATUS 中 P0/P1 未完成项

### P0
1. 双击/自启动生产入口统一 Python 与依赖环境（消除全局 Python 与 .venv 不一致）
2. 历史空正文在稳定网络下合法分批补抓
3. 小红书相对发布时间在采集解析层规范化（严禁用采集时间冒充发布时间）—— **用户增补需求已覆盖**
4. `300012`/验证/IP风控进入状态机、熔断、冷却、告警体系
5. Cookie/session 失效进入 Auth Recovery Modal（不简单跳登录页，显示平台/账号/状态/原因/二维码）
6. 公网模式通过 HTTPS/反向代理或 Cloudflare Tunnel（8200 不裸暴露）
7. Ollama 为正式本地 AI Runtime（云端大模型不作为生产依赖）

### P1
1. 登录双方式、三级权限、安全问答和设置页体验
2. `swire_notes`、`topic_campaign_notes` 真实采集跑数
3. 评估并逐个启用 guardian/recovery/data feedback
4. 微博/B站 Cookie 免登链路实测
5. 微信通知凭证配置后实测
6. 品牌传播平台 Phase 1：主体类型、内容类型、事件关系、三类事件看板与筛选
7. Ollama Shadow Mode、AI运行记录与人工修正样本

### P2
1. 手机端完整苹果设置风
2. `collector_v2` 与现网采集器并行验证后再切换
3. CI/CD、监控大盘、app.py 中期蓝图化
4. 品牌传播平台 Phase 2/3：六维主体画像、事件图谱/生命周期、消费者需求、品牌对标、因果溯源、综合报告

---

## 六、函数注册表缺口（FUNCTION_REGISTRY）

| 项 | 状态 | 说明 |
|---|---|---|
| FUNC-CONTENT-02 情感分析 | CANDIDATE | ai_analyzer.py 与 topic_campaign.py 存在两处口径，双真相待统一 |
| 话题热度/浏览-讨论-笔记-快照 | 待注册 | topic_campaign_snapshots 派生率 |
| 事件传播链 | 待注册 | event_graph |
| Campaign 效果 | 待注册 | topic_campaign_notes 聚合 |
| 报告聚合 | 待注册 | daily/weekly/monthly/annual 全消费 FUNC |

---

## 七、疑似前端死按钮 / API 断链（需验证）

前端调用 36 个 API，后端注册 504 个路由，以下 5 个未匹配：

| 前端调用 API | 疑似状态 | 需验证 |
|---|---|---|
| `/api/risks/active` | 可能断链 | 确认后端是否有此路由（可能是 /api/risk/active 拼写差异） |
| `/lumenis/api/intelligence/evidence` | 可能误报 | lumenis blueprint url_prefix，需确认实际路由 |
| `/lumenis/api/skills/invocations` | 可能误报 | 同上 |
| `/lumenis/api/skills/invoke` | 可能误报 | 同上 |
| `/lumenis/api/skills/sync` | 可能误报 | 同上 |

---

## 八、用户增补数据精准性红线（10项，P0）

1. KOS 计算不得依赖固定公式，按平台规则可延展配置
2. 全平台（小红书/抖音/微博/B站/知乎）数据 100% 精准，禁止估算/近似/假数据/默认值填充
3. 缺失值显式标记 null/unknown/missing，禁止用 0 或 "未知" 静默填充
4. 时间口径分离：publish_datetime vs captured_at，相对时间可靠归一化
5. 采集链路五步质量门禁：Source→Raw→Dedup→Subject Filter→Canonical，每步校验+失败记录
6. 全链路可追溯：原始URL/采集时间/账号/平台/原始字段
7. 去重精准：content_hash+platform_id，不因标题相似误删
8. 评论/详情失败不静默丢弃，必须记录失败状态
9. AI与原始数据分离存储，人工修正可追溯
10. 函数驱动动态可视化接入前端（见 1.1）

---

## 九、统计汇总

| 类别 | 数量 |
|---|---|
| UNWIRED（完成但未接入） | 3 项 |
| 已定契约未实施 | 3 项 |
| 待 Contract | 12 项（与ZBC核心相关） |
| 未收尾并行轨道 | 3 条 |
| P0 未完成 | 7 项 |
| P1 未完成 | 7 项 |
| P2 未完成 | 4 项 |
| 函数注册缺口 | 5 项 |
| 疑似API断链 | 5 项（待验证） |
| 数据精准性红线 | 10 项 |
| **合计** | **59 项** |

---

## 十、执行优先级建议

### 第一批（P0，立即执行）
- 数据精准性红线 10 项（用户明确要求）
- xujing-viz.js 接入前端（UNWIRED）
- /api/risks/active 断链确认修复
- Track C 39个测试失败收敛

### 第二批（P1，紧随其后）
- IC-021/039/040 已定契约实施
- IC-035 OWASP 安全清单（高优先级）
- Track A ai_api 拆分收尾
- Track B 智谱24h保活
- P0 项目状态项（300012状态机/Auth Recovery Modal等）
- ad_intelligence 平台接入或明确 BLOCKED

### 第三批（P2，逐步推进）
- P1 项目状态项
- 待 Contract 的 IC 项（IC-044/048/029/033/041等）
- Podcast 前端接入确认
- 函数注册表缺口补齐
- P2 项目状态项

---

> 本清单为 ZBC 核心功能缺口的完整审计结果，所有项均有代码/文档/扫描证据支撑。执行时逐项核查、完成一项标记一项，不得遗漏。
