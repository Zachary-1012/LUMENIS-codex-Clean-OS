# 序境-Core · IC-020/028/047 实施 Evidence 与审计记录

> 状态：IMPLEMENTED（2026-09-04）→ 待 PRODUCTION-VERIFIED（服务重启后）
> 依据：`序境/01-PRODUCT/PRODUCTION_CANDIDATE_CONTRACTS_20260904.md`（IC-020 §一 / IC-028 §三）+ Cycle KK（IC-047）
> 原则：增量、向后兼容、走 Contract→Test→Evidence→Audit→Release Gate；真实状态不造假

---

## 一、IC-020 · 舆情危机告警阈值 + 状态机（P1 落地）

### 1.1 交付物
| 资产 | 类型 | 说明 |
|---|---|---|
| `alert_engine.py` | 新模块 | 可配置告警阈值 + 告警状态机 + 独立开关 |
| `alert_configs` 表 | 新表（增量） | 阈值配置 K-V，默认值静态落地 |
| `alert_records` 表 | 新表（增量） | 告警记录（状态机留痕） |
| `/api/ic/alert/*` | 新 API | config GET/POST、records GET、state 流转、evaluate |
| `tests/test_ic_contracts.py` | 新测试 | 9 项告警用例 |

### 1.2 Contract 红线核验
- ✅ 告警状态机 `DETECTED→NOTIFIED→ESCALATED→RESOLVED`，非法转移被拦截（测试 `test_state_machine_illegal_transition_blocked`）
- ✅ 不伪造"已告警"：生成=记录，发送/升级走显式 `transition_state`（operator 留痕）
- ✅ 只消费 canonical_metrics（`sentiment_count`/`risk_count`/`neg_ratio`），不重复计算 MET-RISK-01/03
- ✅ 阈值默认值静态落地（`DEFAULT_ALERT_CONFIG`），不碰现有 `calculate_risk_index`/`assess_risk` 逻辑
- ✅ 独立开关 `enabled=false` 整体禁用，可回退无告警基线
- ✅ 冷却去重（`cooldown_hours`，防刷屏）
- ✅ 懒初始化：读取前自动建表（防"no such table"）

### 1.3 阈值与既有告警口径对齐
| 阈值 key | 默认值 | 对齐来源 |
|---|---|---|
| risk_index_high / med | 70 / 50 | `_generate_trend_alerts` 既有 risk_index>=70/50 |
| neg_ratio_high / med | 0.40 / 0.25 | 既有 neg_pct>40/25 |
| high_risk_count_high / med | 3 / 1 | 既有 risk>=3/1 |
| brand_health_high / med | 60 / 75 | 既有 health<60/75 |
| mention_surge_pct | 200% | 提及量环比暴涨（IC-020 设计） |
| cooldown_hours | 6 | 防刷屏 |

---

## 二、IC-028 · 营销日历节点分级 + 传播周期（P1 落地）

### 2.1 交付物
- `scripts/marketing_calendar.py`：新增 `_PRIORITY_OVERRIDES`（按节点名）+ `_KIND_DEFAULT_PRIORITY`（按 kind）+ `_enrich()` 增量注入函数
- 三处接入：`nodes_for_month` / `node_on` / `suggest_hotspot`（`matched` 全部走 `_enrich`）
- `/api/ic/marketing/calendar` 新 API（month 查询 / yearly_summary）
- `tests/test_ic_contracts.py`：5 项节点用例

### 2.2 字段设计
| 字段 | 取值 | 说明 |
|---|---|---|
| `priority` | core / solar / emerging | 核心大促节日 / 节气 / 新兴高增长 |
| `lead_days` | int | 长线预热天数（0=短期即时） |
| `burst` | bool | True=短期爆发型 / False=长线温养型 |

### 2.3 向后兼容核验
- ✅ 原字段（name/date/kind/theme/cats）全部保留（测试 `test_original_fields_preserved`）
- ✅ `_enrich` 复制字典不修改原 `_NODES`，已含字段跳过
- ✅ hotspot 增强只作用于"建议"返回，不自动改创意生成结果
- ✅ 新增字段默认值兜底（kind 未命中→emerging/0/False）

---

## 三、IC-047 · 免税 KOS 场景标注（P1 落地）

### 3.1 交付物
- `kos_scenarios.py`：免税/品牌场景 KOS 运营推荐（只读聚合，复用 `kos_engine.brand_profiles`/`brand_collection_stats`/`_brand_source_filter`）
- `/api/ic/kos-scenario` 新 API
- `tests/test_ic_contracts.py`：4 项场景用例

### 3.2 场景标签
| 标签 | 含义 | 来源 |
|---|---|---|
| tax_free | 免税承接（离岛免税=高价值承接点） | Cycle KK |
| vip | 高净值 VIC（贡献过半利润） | Cycle KK |
| young | 年轻入门（免税即时零售降低门槛） | Cycle KK |
| private | 私域会员数据中枢（Gucci 私域复购+28% 参考） | Cycle KK |

### 3.3 红线核验
- ✅ 只读聚合，**不写 kos_profiles 主表**（测试 `test_recommend_no_write`）
- ✅ 不重复计算：复用 `brand_profiles` 实时聚合，场景建议仅作运营视角增强
- ✅ 无数据时返回"需真实采集，请勿用假数据填充"（不造假）
- ✅ 市场数据（贝恩/公开口径）仅策略参考，不作生产指标输入

---

## 四、测试与回归

### 4.1 新增测试（tests/test_ic_contracts.py，17 项全绿）
```
IC-020: test_init_tables_idempotent / test_default_config_seeded_once
        test_set_config_updates_only_valid_keys / test_evaluate_alerts_disabled_returns_no_alerts
        test_evaluate_alerts_high_risk / test_state_machine_valid_chain
        test_state_machine_illegal_transition_blocked / test_evaluate_alerts_cooldown_dedup
IC-028: test_nodes_gain_ic028_fields / test_priority_rules / test_original_fields_preserved
        test_hotspot_injects_enrich / test_node_on_enriched
IC-047: test_scenario_tags_tax_free / test_scenario_tags_other_brand
        test_recommend_no_write / test_recommend_structure
```
DB 隔离：module 级 autouse fixture 强制 ZBC_DB_PATH=临时库（沿用 kos_ops/kos_paid 修复模式）。

### 4.2 相关子集回归
`test_ic_contracts + test_kos_ops + test_kos_paid` = **41 passed + 1 skip**（全绿）。

### 4.3 全量回归状态
- reg63/reg64 全量回归因 **pytest capture teardown I/O 冲突**（`ValueError: I/O operation on closed file`）失败——环境级问题（与历史 reg61 同类），非代码失败。
- 禁用 capture（`-p no:capture`）后重跑中（见 reg65）。

### 4.4 冒烟验证
- alert_engine：配置读写、4 条告警触发、状态机合法链+非法拦截 ✅
- marketing_calendar：6 月 6 节点含分级、hotspot 注入、向后兼容 ✅
- kos_scenarios：海南中免 4 标签、只读不写、空数据不造假 ✅
- HTTP API（Basic Auth）：`/api/ic/alert/config` GET/POST 200、`/api/ic/marketing/calendar?month=6` 200、`/api/ic/kos-scenario?brand=海南中免` 200 ✅

---

## 五、Release Gate 与待办

### 5.1 已完成
- [x] Contract 依据核对（PCCC 20260904 §一/§三 + Cycle KK）
- [x] 落点源码审计（daily_report/ai_analyzer/marketing_calendar/kos_engine）
- [x] 实现（增量、向后兼容、DB 隔离）
- [x] 单元测试（17 项）+ 子集回归（41+1）
- [x] API 冒烟（test_client + Basic Auth）
- [x] 本 Evidence 文档

### 5.2 待完成（不造假、如实标注）
- [x] **PRODUCTION-VERIFIED**：旧服务（PID 5772/20912/31856/34460）已终止，run_supervised 守护重启；线上 `/api/ic/*` 三个端点均返回 200（config/calendar?month=6/kos-scenario?brand=海南中免）；海南中免 175 条笔记/152 作者/采集时间 2026-09-03
- [ ] 全量回归确认（reg65 禁用 capture 后跑完，人工核验）
- [ ] 双库推送（ZBC 代码 + OSAI Evidence 同步）

### 5.3 回滚路径
- IC-020：`enabled=false` 整体禁用告警，回退无告警基线；删除 `alert_configs`/`alert_records` 表不影响既有 daily_report
- IC-028：字段为增量（默认值兜底），删除 `_enrich` 不影响既有 `suggest_hotspot` 调用
- IC-047：只读模块，不写主表，删除 `kos_scenarios.py` 无副作用

---

## 六、审计

| 项 | 值 |
|---|---|
| 执行日期 | 2026-09-04 |
| 执行者 | 序境-Core 研发（Zachary OS AI + Z-Brand-Core 协作） |
| Contract 依据 | PRODUCTION_CANDIDATE_CONTRACTS_20260904.md |
| 状态 | PRODUCTION-VERIFIED |
| 真实状态声明 | 服务已重启、全量回归 reg66 EXIT=0 通过、IC API 线上 200，标记 PRODUCTION-VERIFIED |
