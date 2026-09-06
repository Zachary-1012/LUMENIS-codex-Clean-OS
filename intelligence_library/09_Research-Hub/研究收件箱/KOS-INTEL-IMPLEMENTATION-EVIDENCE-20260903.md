# KOS Intel 施工证据（Phase A 适配优化）

> 双子星闭环：OSAI 研究/Contract → ZBC 施工 → 本证据 → OSAI 再学习
> 日期：2026-09-03 ｜ 状态：IMPLEMENTED & VERIFIED（ZBC main a08daf1）

## 1. 施工内容（Z-Brand-Core）

**新增 `kos_intel.py`（a08daf1，346 行）** — Phase A 三能力（不依赖蓝V/聚光）：
1. **意向评论分层**：`classify_intent`（强/弱/无意向 + 负面识别）+ `analyze_comments_intent`（复用 note_comments 表，按 level/category 聚合）
2. **KOS 号识别**：`recognize_kos_identity`（证据加权：命名信号+内容信号+重复品牌内容+官方标记，不虚构雇佣关系）+ `refresh_kos_identity`（幂等 ALTER TABLE 回写 identity_label/is_kos）
3. **竞品对标**：`competitor_benchmark`（复用 hainan_cdf.json subject_terms + entity_disambiguation.do_not_merge_without_evidence，主品牌 vs 海免/海旅免税/深免/中服免税）

**路由协同（用户研发侧 be9be46 已挂载）**：
- `GET /api/kos/intent-analysis` → `analyze_comments_intent`
- `GET|POST /api/kos/kos-identity` → `recognize_kos_identity` / `refresh_kos_identity`
- `GET /api/kos/competitor-benchmark` → `competitor_benchmark`

## 2. 验证结果

| 验证项 | 结果 |
|---|---|
| py_compile（kos_intel / kos_routes / kos_engine） | PASS |
| 意向分层用例（强4/弱2/无意向+负面） | 7/7 PASS |
| 路由→函数签名匹配 | 4/4 匹配，NONE MISSING |
| KOS 身份回写（900 profiles，前10刷新） | OFFICIAL 1 / UGC 9，幂等列新增 OK |
| 竞品对标框架（当前 DB 尚无中免数据） | 主品牌+4竞品结构正常，等待 Phase A 采集 |

## 3. 边界合规
- 未动 SUBJECT_WORDS / subject_hit / 风险口径 / 报告口径等最高保护层
- KOS 识别为候选分类，不宣称雇佣/隶属关系（对齐 hainan_cdf.json kos_candidate_rules.important）
- 系统不宣称已投流/已转化/已产生 ROI
- 无 Cookie/Token/Session 入库；仅公开采集数据

## 4. 待办（采集启动后）
- 中免 subject_terms 采集数据入库 → competitor_benchmark 与 intent-analysis 有真实值
- 意向分层后续可接 AI 校准（现为规则版，confidence 预留）
- 评论→私信→留资闭环（Phase B，需蓝V+聚光认证）

## 5. 学习点（OSAI 再学习）
- 协同模式验证成功：OSAI 契约（CTR-XHS-LEADS-P1-01 Phase A）→ ZBC 路由层先行（研发侧）→ 实现层补齐（OSAI 施工）→ 无缝拼合
- 竞品对标/实体消歧的配置先行（hainan_cdf.json）大幅降低实现成本——配置即契约
