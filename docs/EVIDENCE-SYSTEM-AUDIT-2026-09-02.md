# Evidence 系统审计报告 · 2026-09-02

> 审计范围：Z-Brand-Core 仓库全部 docs/ 资料库、案例库、Evidence 相关文档 + 代码中 Evidence 实际使用情况。
> 审计目标：回答"当前 Evidence 体系有什么、缺什么、下一步怎么建"。
> 审计人：Zachary OS AI（ZBC 生产执行侧）

---

## 一、现有 Evidence 资产清单（已存在，可复用）

### 1.1 数据库层
| 资产 | 位置 | 状态 |
|---|---|---|
| `app_evidence_records` 表 | data/monitor.db | 表结构已存在，字段已定义（见 EVIDENCE-PATTERNS.md 第1节） |
| Evidence 记录结构 | docs/learning/EVIDENCE-PATTERNS.md | 26 字段：id/project/product/feature_id/asset_id/commit/version/env/level(L0-L10)/test_name/result/started_at/finished_at/inputs/outputs/expected/actual/log_path/screenshot/trace/api_request/api_response/db_before/db_after/root_cause/resolution/created_at |

### 1.2 文档层（Evidence 规范与流程）
| 文档 | 大小 | 核心内容 |
|---|---|---|
| `docs/learning/EVIDENCE-PATTERNS.md` | 2.7KB | 统一 Evidence 结构 + L0-L10 每级最小证据 + 失败必留证据链 + 事实vs声明分离 + Release Gate 证据清单 |
| `docs/governance/PHASE2-STAGING-EVIDENCE.md` | 4.4KB | Staging 环境 L0-L10 实测证据 + 隔离铁证（8301 副本库写入不影响 8201 生产） |
| `docs/UI/UI-EVIDENCE-PROCESS.md` | 3.4KB | UI 七步门禁（设计评审→组件确认→页面确认→开发→视觉测试→性能测试→上线）+ UI Evidence 记录结构 + 防覆盖机制 |

### 1.3 案例库层（研究资产，非生产事实）
| 文档 | 大小 | 核心内容 |
|---|---|---|
| `docs/learning/CASE-STUDIES.md` | 10.5KB | 32 个 GitHub 成熟案例（LR-001~LR-032），含 in-toto/SLSA（LR-003/004 Evidence 链路）、Playwright（LR-014 trace 证据）、OpenTelemetry/Prometheus（LR-005/006 可观测） |
| `docs/BRAND_INTELLIGENCE_CASE_LIBRARY_V1.md` | 10.6KB | 21 个跨行业品牌案例（Jacquemus/Patagonia/Nike/Lululemon/Glossier 等）+ 15 维 Benchmark + Case→Evidence→Pattern→Hypothesis→Cross-brand Validation→Metric→Shadow→Regression→Production Insight 链路 |
| `docs/ZBMP-GLOBAL-BIL-RESEARCH-MASTER-LOG-2026-09-01.md` | 24.2KB | 全球品牌情报研究主日志 |
| `docs/learning/LEARNING-REGISTRY.md` | 8.9KB | 学习注册表 |
| `docs/GLOBAL_BIL_*.md`（12 份） | 合计 ~55KB | 全球品牌情报能力矩阵、数据库 SQL、研究协议、执行计划、ZBMP 映射等 |

### 1.4 安全事件与架构文档
| 文档 | 核心内容 |
|---|---|
| `docs/XHS-ACCOUNT-SAFETY-INCIDENT-2026-08-31.md` | 小红书账号安全事件记录 |
| `docs/XHS-REDNOTE-SAFE-ARCHITECTURE-V2-2026-08-31.md` | 小红书/RedNote 安全架构 V2 |
| `docs/learning/BROWSER-RESEARCH.md` | 浏览器研究（含 Resident AI Browser 方向） |

---

## 二、核心缺口（审计发现，按优先级排序）

### P0 缺口：采集证据未系统化留存（用户明确指出）
**现状**：
- `resident_health.py` 三层健康检查结果只写入 `data/resident_health.json`（运行时状态文件，被 .gitignore 覆盖），**不写入 `app_evidence_records` 表**。
- `collector_automation.py` 采集任务执行后，**没有把采集结果写入 Evidence 表**。采集了多少笔记、什么账号、什么时间、耗时多久、是否异常——这些信息只在日志里，没有结构化 Evidence。
- 采集异常（验证码/300012/IP风险/登录失效）**没有落真实状态证据**。EVIDENCE-PATTERNS.md 第4节明确要求"采集异常必须落真实状态证据，禁止以 0 条充当结果"，但代码中未实现。

**影响**：
- 无法回溯"某天某账号采集了什么、为什么异常"。
- 无法做采集质量趋势分析（成功率、异常率、笔记数趋势）。
- Release Gate 无法验证采集链路的 Evidence 完整性。

### P1 缺口：Evidence API 缺失
**现状**：没有 API 来查询/检索 `app_evidence_records` 表。前端无法展示 Evidence，外部工具无法消费 Evidence。

### P1 缺口：Evidence 前端展示缺失
**现状**：Dashboard 没有 Evidence 相关的展示区域。用户看不到最近的采集证据、健康检查证据、异常证据。

### P2 缺口：Evidence 表使用不足
**现状**：`app_evidence_records` 表存在，但可能只有测试/Staging 阶段写入，生产采集链和健康监控没有使用。需要审计表中实际有多少条记录、什么类型。

### P2 缺口：AI 产出 Evidence 未分离
**现状**：EVIDENCE-PATTERNS.md 第4节要求"AI 产出单独标 model/prompt_version/confidence/human_override，不与系统事实混存"，但当前 AI 学习引擎的产出没有结构化 Evidence。

---

## 三、Evidence 系统建设路线图（Contract：OSAI 研究 → ZBC 生产）

### Phase 1（P0，本轮可启动）：采集 Evidence 基础留存
1. **`evidence_store.py` 新建**：统一 Evidence 写入接口，封装 `app_evidence_records` 表的 INSERT/QUERY，支持批量写入、按类型/账号/级别查询。
2. **采集链集成**：在 `collector_automation.py` 中，每次采集任务完成后写入一条 Evidence：
   - `project=ZBC, product=CTH, feature_id=XHS_COLLECT, env=prod`
   - `level=L4`（API Smoke）或 `L8`（Browser）
   - `inputs`: account, platform, keywords, session_state
   - `outputs`: notes_collected, notes_filtered, duration_ms
   - `result`: PASS / FAIL / ENV / GAP
   - `actual`: 异常类型（验证码/300012/IP风险/登录失效）+ 异常消息
   - `api_request/api_response`: 采集 API 请求响应摘要
3. **健康检查集成**：在 `resident_health.py` 中，每次健康检查写入一条 Evidence：
   - `level=L3`（Health）或 `L8`（Browser）
   - `inputs`: account, cdp_port
   - `outputs`: port_alive, cdp_ws_ok, login_state, cookie_count
   - `result`: PASS / FAIL
   - `actual`: 健康状态详情
4. **异常证据强制留存**：采集异常时 `result=FAIL`，`actual` 记录异常类型和消息，**禁止以 0 条充当结果**。

### Phase 2（P1）：Evidence API + 前端展示
1. **`GET /api/evidence`**：查询 Evidence 记录，支持 `type/account/level/result/limit/offset` 过滤。
2. **`GET /api/evidence/stats`**：Evidence 统计（按天/账号/类型的成功率、异常率）。
3. **Dashboard "采集证据"区域**：展示最近 N 条采集 Evidence（时间、账号、平台、笔记数、异常、状态），支持按账号/状态过滤。
4. **健康状态卡片关联 Evidence**：点击健康状态卡片的"查看证据"按钮，展示该账号最近的健康检查 Evidence。

### Phase 3（P2）：Evidence 体系完善
1. **AI 产出 Evidence 分离**：AI 学习引擎产出单独标 `model/prompt_version/confidence/human_override`。
2. **Evidence 回放**：失败 Evidence 关联 screenshot/trace/log_path，支持一键回放。
3. **Release Gate Evidence 校验**：上线前自动校验核心业务/DB/API/页面/E2E/Browser/Restart 全部 PASS 且证据可回放。
4. **Evidence 保留策略**：成功 Evidence 保留 90 天，失败 Evidence 永久保留（或至少 1 年）。

---

## 四、与现有文档的对齐确认

| 现有规范 | 本审计是否对齐 | 备注 |
|---|---|---|
| EVIDENCE-PATTERNS.md L0-L10 分层 | ✅ 对齐 | 采集=L4/L8，健康=L3/L8，测试=L0-L7 |
| EVIDENCE-PATTERNS.md 失败必留证据链 | ✅ 对齐 | Phase 1 第4点强制异常留存 |
| EVIDENCE-PATTERNS.md 事实vs声明分离 | ✅ 对齐 | Phase 3 AI 产出分离 |
| EVIDENCE-PATTERNS.md Release Gate 证据清单 | ✅ 对齐 | Phase 3 第3点 |
| UI-EVIDENCE-PROCESS.md 七步门禁 | ✅ 不冲突 | UI Evidence 走独立流程，本审计聚焦采集/健康 Evidence |
| CASE-STUDIES.md in-toto/SLSA 思想 | ✅ 吸收 | Evidence 结构 = step+materials+products+signature，不引工具链 |
| BRAND_INTELLIGENCE_CASE_LIBRARY Case→Evidence→...→Production Insight | ✅ 对齐 | 品牌案例的 Evidence 链路与采集 Evidence 共用表结构 |

---

## 五、审计结论

1. **Evidence 规范层已成熟**：L0-L10 分层、记录结构、失败证据链、事实vs声明分离、Release Gate 清单都有明确文档定义。
2. **案例库层已丰富**：32 个 GitHub 技术案例 + 21 个品牌案例 + 12 份 Global BIL 研究文档，研究资产充足。
3. **生产执行层有缺口**：`app_evidence_records` 表存在但采集链和健康监控未使用，采集证据未系统化留存，这是当前最大的 P0 缺口。
4. **建议立即启动 Phase 1**：新建 `evidence_store.py`，在采集链和健康检查中集成 Evidence 写入，异常强制留存。这是投入产出比最高的一步。

---

*审计完成时间：2026-09-02*
*审计范围：D:\Taikoo-monitor-new\docs\ 全部文档 + 代码中 Evidence 使用情况*
*下一步：按 Phase 1 路线图启动 evidence_store.py 开发*
