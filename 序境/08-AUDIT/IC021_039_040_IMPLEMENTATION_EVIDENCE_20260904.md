# 序境-Core · IC-021/039/040 实施 Evidence（PCCC 20260904 §二/四/五）

> 日期：2026-09-04
> 状态：**IMPLEMENTED + 全量回归通过**（待服务重启后 PRODUCTION-VERIFIED）
> 依据：PCCC `PRODUCTION_CANDIDATE_CONTRACTS_20260904.md`（IC-021 §二 / IC-039 §四 / IC-040 §五）
> 原则：增量、向后兼容、Contract→Test→Evidence→Audit→Release Gate、真实状态不造假（IMPLEMENTED ≠ PRODUCTION-VERIFIED）

---

## 一、IC-021 · EMV（earned media value）→ MET-CONTENT-04

### 1.1 落点
- **新增 `emv.py`**：FUNC-CONTENT-04，纯函数 EMV 估算引擎。
  - `calculate_emv(likes/comments/collects/shares, cpm, exposure_ratio)`：单条 EMV 估算
  - `aggregate_emv(notes, ...)`：周期汇总（日报/周报/月报/年报）+ 覆盖度
- **`report_engine.py` 接入**：`generate_report` 末尾追加 `report['emv']`，独立 try/except（失败不阻塞报告生成）。

### 1.2 口径（契约红线）
- EMV = 加权互动 × 互动-曝光折算(33.3) × CPM(默认 8.0 元/千次)；
- **永远标记 `is_estimate=True` + disclaimer"估算口径，非官方媒体投放成本"**；
- CPM 来源登记（行业公开参考区间 3~15 元/千次中间值，2026 估算，待季度校准）；
- 无互动数据 → `NOT_AVAILABLE`，**禁止估 0**。

### 1.3 测试（tests/test_ic_contracts_p1.py）
- 真实互动返回 OK + 估算标注；无数据 NOT_AVAILABLE；汇总覆盖度；自定义 CPM。全部通过。

---

## 二、IC-039 · 跨文化本地化守卫 → scripts/localization_guard.py

### 2.1 落点
- **新增 `scripts/localization_guard.py`**：静态禁忌/合规库（中英韩）+ 检查层。
  - `TABOO_RULES`：中/英/韩绝对化用语（最/第一/领先/国家级/the best/최고/1위 等，HOLD 级）
  - `SYMBOL_RULES`：宗教/王室符号（清真/Allah/하나님/royal 等，BLOCK/HOLD 级）
  - `PLATFORM_BEHAVIOR`：平台行为建议库
  - `check()` / `check_multi()`：返回 hold/blocked/hits/requires_human + "待母语者确认"标记
- 独立开关：`LOCALIZATION_GUARD_ENABLED`（默认开，可整体关闭回滚）。

### 2.2 Gate
- 命中 HOLD/BLOCK 必须 `requires_human=True`，**禁止自动改写后直接发布**；
- AI 输出一律标记"初译/变体，待母语者确认"；
- 本地化最终决策权在人工/母语者。

### 2.3 测试
- 中文绝对化用语 HOLD；合规内容通过；宗教符号 BLOCK；韩文/英文命中；多语言聚合；开关关闭；AI 待确认标记。全部通过。

---

## 三、IC-040 · KOS 兴趣图谱信号 → kos_engine.py

### 3.1 落点
- **`kos_engine.py` 追加 `interest_signal(author_id, brand, limit)`**：只读聚合，附加评估维度。
  - 信号：watch_depth_proxy（平均互动→完播/停留代理）、dm_share_proxy（平均分享→DM 分享代理）、search_asset_proxy（收藏/点赞比→搜索资产化代理）
  - `SIGNAL_AVAILABILITY`：平台原生信号源标注 available=False + 代理说明（契约：不可得不编造）
  - 返回 `no_blackhat=True`（采集安全红线声明）
- **不改 kos_score 主计算、不改分层**（防数字真相漂移）；独立函数，可整体移除。

### 3.2 测试
- 无数据优雅降级；代理标注；不改变 kos_score（纯只读）。全部通过。

---

## 四、API 接入（ic_routes.py 追加 3 端点）

| 端点 | 方法 | 功能 |
|---|---|---|
| `/api/ic/emv` | GET | EMV 汇总（start/end/cpm/limit），真实 notes 互动 |
| `/api/ic/localization/check` | POST | 本地化禁忌/合规检查（text/lang/platform） |
| `/api/ic/kos/interest-signal` | GET | KOS 兴趣图谱信号（author_id/brand/limit） |

API 冒烟（test_client + Basic Auth）：3 端点全部 200。

---

## 五、验证结果

| 项 | 结果 |
|---|---|
| 新增测试 | 18 passed（IC-021×4 + IC-039×8 + IC-040×3 + API×3） |
| 相关子集回归 | 59 passed + 1 skipped（ic_contracts + ic_contracts_p1 + kos_ops + kos_paid） |
| **全量回归** | **reg69 EXIT=0 通过**（带 -p no:capture -p no:cacheprovider） |
| Metric 登记 | MET-CONTENT-04 已入 METRIC_REGISTRY（CANONICAL 估算口径登记） |
| 契约补充 | IC-047 正式 Contract 已补记（CONTRACT_IC047_20260904.md） |

---

## 六、待完成（不造假、如实标注）

- [ ] **PRODUCTION-VERIFIED**：现有服务进程（PID 1328/36624/22228/23492）运行旧版 app.py，需**重启服务**后 `/api/ic/emv|localization/check|kos/interest-signal` 才生效；重启后需生产冒烟（GET emv / POST localization / GET interest-signal）。
- [ ] IC-021 P2（agentic 监测闭环编排 + KOS 融合）未排期。
- [ ] IC-039 P2（AI 10→3 变体生成 + 母语者确认工作流对接 HCG）未实施。
- [ ] IC-040 P2（内容资产化长尾留存指标）未接入。

| 真实状态声明 | 代码已实现、全量回归通过；**服务未重启，未标记 DONE/PRODUCTION-VERIFIED** |
