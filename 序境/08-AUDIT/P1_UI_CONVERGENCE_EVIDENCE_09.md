# 序境 · 研发闭环 Evidence 09 — 升级 / 恢复回路 / 案例入库

- 日期：2026-09-04
- 基线：GitHub 双库 origin/main（ZBC `e318fb8`）
- 类型：P0 升级验证 + P2 恢复回路 + 案例库数据落地

---

## 1. GLM-5.3 升级（智谱强模型）

| 项 | 值 |
|---|---|
| 配置 | `.env` `ZHIPU_STRONG_MODEL`：`glm-4.7` → `glm-5.3` |
| 依据 | 智谱 API `/models` 实测可用模型 10 个，含 `glm-5.3` / `glm-5.3-flash` |
| 读取方 | `intelligence.py::_strong_model()` 动态读 env（HIGH/CRITICAL 级用） |
| 真实调用验证 | `glm-5.3` chat/completions HTTP 200，`usage` 正常（prompt 30 / completion 80，其中 reasoning 77——推理模型先思考后输出，max_tokens 偏小时 content 为空属正常；生产端 `_level_params` 分级 max_tokens） |
| 现网生效 | 需重启 8201 进程树后 AI Router 新模型生效（部署动作，避免瞬断，登记待执行） |
| 状态 | **DONE（条件式 ADOPT 落地：模型名可用性已确认）** |

> 升级遵守 ADOPTION_EVAL_2026-09 流程：先确认模型名可用 → 改配置 → 真实调用抽样验证。

## 2. internal_browser 执行恢复回路（P2 → 已施工）

对照 Page Agent / browser-use「失败→重新定位→重试→降级」，最小 diff 注入：

| 新增能力 | 说明 |
|---|---|
| `find_element(account, selector)` | JS `querySelector` 定位 + 可视坐标返回；**防注入**（selector 白名单字符校验，非法字符拒绝且不发 JS） |
| `click_selector(account, selector, retry=2)` | 定位→点击，失败重试（重新定位→重试→报告），trace 记录每次尝试 |
| `type_into(account, selector, text, retry=2)` | 定位→聚焦→输入，失败重试 |
| `browser_task(account, steps, max_steps, total_timeout)` | 步骤序列执行：trace 全量 + 预算（步骤上限/总超时）→ 超限 skipped 停止；失败步骤继续不中断 |
| API 端点 ×4 | `/find` `/click-selector` `/type-into` `/task`（steps ≤20，预算默认远小于采集安全 Gate 上限） |

**测试**：`tests/test_internal_browser_recovery.py` 10 项通过（mock CDP，不依赖驻场浏览器），覆盖：非法 selector 拒绝、元素未找到、定位成功、重试后失败、输入成功、任务 trace/预算截断、全部成功、未知 action、导航失败继续。
**相关回归**：internal_browser + idea_generator 共 28 项通过。
**提交**：ZBC `9b2435b..e318fb8`（恢复回路 + 测试）。

> 边界：恢复回路只增强执行可靠性，不改变采集频率/不绕过安全 Gate（手动 ≤30min 约束由调用方控制）。

## 3. 营销案例库入库（case_study 主体 + 9 事件）

**表结构确认**（`data/monitor.db`，`swire_group.py` 品牌营销案例库）：
- `swire_projects(project_key, name, city, line, opened, intro, sort, kind, keywords, is_active, collect_status, created_at, updated_at)`
- `swire_events(id, project_key, brand, event_type, title, summary, source, url, event_date, sentiment, tags, created_at, UNIQUE(project_key,title,event_date))`
- `swire_notes(project_key, brand, note_id, title, author, likes, comments, collects, publish_date, ...)`

**入库**（幂等，`INSERT OR IGNORE` 靠 UNIQUE 去重）：
- 新增主体 `case_study`（name=营销案例研究，kind=case_study，sort=100，is_active=1）
- 9 个公开可查证案例 → `swire_events`，`source` 均为公开资料（B&T / PRDaily / 数英 / MRS / Selfstorm / 4A / 公开分享），`sentiment=neutral`，tags 带机制标签（约束即创意/预算受限/用户共创/文化转译/行为设计/洞察驱动/游戏化/跨媒介）

| # | 品牌 | 案例 | 机制标签 |
|---|---|---|---|
| 1 | McDonald's | Cannes 2026 金狮·Camera Rolls 用户相册 | 用户共创/真实证据 |
| 2 | McDonald's | 《过三关》皮影戏·春节文化转译 | 文化转译/传统焕新 |
| 3 | Selleys | 广告牌预算限制成 Bless | 预算受限 |
| 4 | Therabody | Add Some Magic·4小时 in-house 拍摄 | 预算受限/小成本 |
| 5 | Whiskas | 丢猫营销·危机为创意原点 | 危机转机 |
| 6 | Gatorade | 造球场·设计用户新行为 | 行为设计/品牌即基础设施 |
| 7 | Ajinomoto | 重构食谱·把产品变行为 | 行为设计/仪式感 |
| 8 | McDonald's | Raise Your Arches·未言说的手势洞察 | 洞察驱动/符号资产 |
| 9 | McDonald's | Minecraft Movie Meal·菜单变可玩宇宙 | 跨媒介/游戏化 |

**验证**：入库后 `SELECT COUNT(*)` = 9；`swire_group` 读取正常；不改变表结构、不影响原有 8 个地产主体及 10 条既有事件。

> 说明：案例数据为 DB 数据（`data/monitor.db` gitignored），交付 = DB 变更 + 本 Evidence。新增主体会在品牌营销案例库前端可见（is_active=1），供创意引擎/报告引用。

---

## 验收结论

- [x] 升级：glm-5.3 模型名可用性确认 + 配置升级 + 真实调用验证
- [x] 恢复回路：4 函数 + 4 API + 10 测试 + 28 相关回归全过
- [x] 案例入库：case_study 主体 + 9 案例幂等入库，来源公开可查证
- [ ] 现网 8201 重启（加载 glm-5.3 + 新端点）——部署动作，登记待执行
