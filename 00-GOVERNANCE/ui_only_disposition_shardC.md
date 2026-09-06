# UI_ONLY 页面处置清单 — Shard C

> 验证时间: 2026-09-06
> 验证方法: curl -u auth 实际访问每个页面调用的 API 端点
> 结论: **0 个纯 UI_ONLY 页面**。所有 19 个 LUMENIS 页面均已绑定真实 API。

## 验证结果汇总

| 页面 | 调用API | HTTP状态 | 分类 | 处置 |
|------|---------|----------|------|------|
| /lumenis/ (command_home) | /api/system/health/summary | 200 | REAL_FUNCTIONAL | 已重构:4/4指标卡绑定真实API |
| /lumenis/ (command_home) | /lumenis/api/intelligence/evidence | 200 | REAL_FUNCTIONAL | 已重构 |
| /lumenis/ (command_home) | /api/negative/stats | 200 | REAL_FUNCTIONAL | 已重构(新增) |
| /lumenis/ (command_home) | /api/collect/tasks | 200 | REAL_FUNCTIONAL | 已重构(新增) |
| /lumenis/ (command_home) | /api/ai-governance/status | 200 | REAL_FUNCTIONAL | 已重构(Provider真实检测) |
| /lumenis/intelligence | /api/ai/status | 200 | REAL_FUNCTIONAL | 已增强:Viewport+EvidenceChain |
| /lumenis/intelligence | /api/ai/chat (POST) | 200 | REAL_FUNCTIONAL | 已增强 |
| /lumenis/production | /api/system/health/summary | 200 | REAL_FUNCTIONAL | 已增强:Viewport+TimeDimension |
| /lumenis/production | /api/collect/schedule-status | 200 | REAL_FUNCTIONAL | 已增强 |
| /lumenis/production | /api/kos/professional/status | 200 | REAL_FUNCTIONAL | 已增强 |
| /lumenis/production/public-opinion | /api/stats | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/public-opinion | /api/risk-alerts | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/risk | /api/risk-alerts | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/risk | /api/system/health/summary | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations | /api/system/health/summary | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations | /api/collect/schedule-status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations | /api/ai/status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations | /api/ai/channel-health | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/skills | /lumenis/api/skills/status | 200 | REAL_FUNCTIONAL | KEEP(唯一全功能页面) |
| /lumenis/intelligence/skills | /lumenis/api/skills/invoke (POST) | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/skills | /lumenis/api/skills/invocations | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/skills | /lumenis/api/skills/sync (POST) | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/agents | /api/agents/status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/evaluation | /api/evaluation/status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/research | /api/research/status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/research | /api/research/pipeline | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/research | /api/research/start (POST) | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/models | /api/intelligence/models | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/intelligence/evidence | /lumenis/api/intelligence/evidence | 200 | REAL_PARTIAL | ENHANCE:补全Loading/Empty/Error状态 |
| /lumenis/production/monitoring | /api/system/health/summary | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/monitoring | /api/collector-guard/status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/monitoring | /api/collect/schedule-status | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/cases | /api/case-analysis/stats | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/cases | /api/event-graph/stats | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/cases | /api/brand-knowledge/stats | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/production/reports | /api/report/* (dynamic) | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/research/findings | /api/case-analysis/system-insights | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/research/findings | /api/brand-knowledge/stats | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations/runtime | /api/system/runtime | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations/permissions | /api/operations/permissions | 200 | REAL_FUNCTIONAL | KEEP |
| /lumenis/operations/repository | /api/system/repository | 200 | REAL_FUNCTIONAL | KEEP |

## 处置统计

- **总页面数**: 19 (LUMENIS) + 1 (healthz) = 20
- **REAL_FUNCTIONAL**: 18
- **REAL_PARTIAL**: 1 (intelligence/evidence — 有API但Loading/Empty/Error状态不全)
- **UI_ONLY**: 0
- **需要删除**: 0
- **需要合并**: 0
- **需要标记 Legacy**: 0
- **需要接 API**: 0 (全部已有真实API)
- **需要增强**: 1 (intelligence/evidence — 补全状态处理)

## 关键发现

1. **所有 LUMENIS 页面均已绑定真实 API**，不存在纯 UI_ONLY 页面。之前审计中标记为 UI_ONLY_PENDING 的页面，经实际 curl 验证全部返回 200。
2. **前置页 command_home 重构前**只有 2/4 指标卡绑定真实 API，重构后 4/4 全部绑定（新增 negative/stats 和 collect/tasks）。
3. **skill_hub 是唯一全功能页面**，拥有 4 个 API 端点（status/invoke/invocations/sync），完整证据链（invocation_id + trace_id + evidence_id + evaluation_id）。
4. **intelligence/evidence 是唯一 REAL_PARTIAL 页面**，API 存在但前端 Loading/Empty/Error 状态处理不全，建议后续增强。
