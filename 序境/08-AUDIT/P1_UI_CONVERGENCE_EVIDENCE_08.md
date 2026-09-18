# 序境 · 创意引擎「约束即创意」落地验证（Evidence #08）

- 日期：2026-09-04 · 状态：VERIFIED-PASS
- 研究来源：RESEARCH_2026-09-B（戛纳 233 项目方法论「创意生于限制」→ 广告门/抖音 2026-04 公开拆解）

## 一、变更（最小 diff，未动核心框架）
`scripts/idea_generator.py`：
- MECHANISMS 新增 `constraint`（约束即创意：短板/预算/场景限制是创意原点）
- MECH_TO_L1 新增「约束即创意公式（限制→原点：少即是多，克制即高级，诚实即张力）」
- `_HOOK` 新增 constraint 组（6 句：少即是多/预算不多照样做/不追热点/诚实即张力/没有花哨/只肯做一件事）
- `_HOOK_LUX` 新增 constraint 组（3 句：专注即奢侈/不铺张/留白即分量）
- MECH_TO_HOOK 新增 `constraint: [constraint, reversal, assert]`
- hook_names 新增「约束即创意」
- mech_order 四分支（luxury/negative/positive/neutral）均接入 constraint 轮转

## 二、测试
`tests/test_idea_generator.py` 新增 `test_constraint_mechanism_present_and_clean`：
- 全部约束句式（_HOOK+_HOOK_LUX）可渲染、无 {}/# 占位符残留、长度>8
- premium 调性 4×12 轮转命中「约束即创意」机制且 slogan 无占位符
- luxury 调性 3×12 轮转也命中（克制即约束）
- 全文件 18 项测试通过

## 三、真实产出（seed=20260904，premium/low）
- 「做不到的，广州太古汇不假装」——15周年，诚实就是一年一次的事
- 机制=约束即创意，句式=约束即创意，来源=戛纳范式方法论 × ZBC 真实信号（15周年/方所，300 笔记样本）

## 四、结论
创意引擎新增第 8 种机制（约束即创意），反模板化面扩大；最小 diff + 测试 + 真实产出验证；未动既有 7 机制与 18 种情感手法。
