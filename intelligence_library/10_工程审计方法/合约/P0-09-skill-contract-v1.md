# LUMENIS Skill Contract — 序境能力契约（P0-09）

> 版本：V1.0 ｜ 生效：2026-09-05 ｜ 归属：LUMENIS Skill Hub
> 依据源码事实：`osai_engine/skill_registry.py`

## 1. 定位
Skill 是横向能力（Capability Layer），不属于某个业务/仓库：
`ZBC Skill / OSAI Skill` 的割裂正式废弃 → 统一 LUMENIS Skill Hub。

## 2. 八类与 72 Skills
Source / Data / AI / Research / Engineering / Governance / Business / Operations（S01-S72，
目录见 `skill_registry.py` SKILL_CATALOG）。

## 3. Skill 元数据（每个 Skill 统一）
`id / name / category / version / status / permissions / dependencies /
 success_rate / usage_count / evidence / lifecycle`

## 4. 权限边界（红线⑤）
- Skill 注册时声明所需权限级；默认上限 = VERIFY（permission_gate）。
- 业务保护类（S61/S63/S64 Subject/Brand/PublicOpinion）默认仅 READ/AUDIT/ANALYZE，
  禁止写；**不得私自绕过 subject_hit() / Subject Authority**（红线③）。
- Skill 不拥有无限权限，权限由 Permission Gate 统一判定。

## 5. 调用方式
Skill 通过 Contract 调用 ZBC / OSAI 能力；结果必须写 Evidence，状态进入 Lifecycle。
COMMIT/PUSH 级动作：任何 Skill 都不得自主执行，必须走人工批准。
