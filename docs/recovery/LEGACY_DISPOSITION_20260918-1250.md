# LUMENIS Legacy Asset Disposition

更新时间：2026-09-18 12:50（Asia/Shanghai）  
唯一产品源码路径：`D:\LUMENIS_REBUILD\序\序境`  
远端主线：`Zachary-1012/LUMENIS-codex-Clean-OS`  
本轮基线：`f9bcc3acf7d5528114e06e2145e7a01d7f99ae14`

## 处置原则

1. 序境 Production Truth 只有当前主路径持有。
2. 历史目录只能作为证据来源，不能因为文件名或目录名直接并入生产。
3. 已确认的能力回收到当前实现；重复实现、旧数据库、旧模型绝对路径和旧启动入口不进入生产。
4. 本轮本地清理使用回收站，不做不可逆永久删除；GitHub 远端历史不修改。
5. 固定工程入口保持原名；报告、快照和回收证据使用分钟级时间戳。

## 已回收至序境

| 资产 | 当前落点 | 处理结论 |
|---|---|---|
| 旧 XHS live runner | `collector_v2/run_xhs_live.py` | 仅保留兼容入口，委托当前 `collector_v2.xhs.live_engine`；没有新增第二采集器 |
| 旧 XHS 入口验证 | `tests/test_legacy_xhs_entrypoint.py` | 已验证委托和空关键词过滤，目标测试 `1 passed` |
| 旧 P0-A/P0-B/P0-C/P0-D、Runtime、AI 审计材料 | `docs/recovery/legacy-evidence_20260918-1235/` | 19 个无密钥证据文件已回收；未把旧报告当作当前运行事实 |
| 旧 `local_ai_runtime` | 未复制源码包 | 旧配置引用已失效的 D 盘模型路径和 qwen2.5；当前真实 Ollama 模型是 `qwen3:4b` 与 `bge-m3`，复制会形成第二套 Runtime |
| 旧数据库 | 未合并生产库 | 历史数据库没有经过 schema、主体归属、数据质量和 Evidence 链验证，禁止直接写入生产 |

## 退役目录审计结果

| 目录 | 只读发现 | 结论 |
|---|---|---|
| `_DECOMMISSIONED_20260917` | 10 个子目录；包含历史审计仓、其他产品仓、便携副本及 42 个数据库文件 | 不作为生产输入；已完成可验证 LUMENIS 证据回收，根目录及全部子目录已移入回收站 |
| `_DECOMMISSIONED_WORKTREES_20260913` | 2 个旧 worktree；约 79 个数据库文件；包含 dirty/clean 历史状态 | 不作为生产输入；已完成可验证 LUMENIS 证据回收，根目录及全部子目录已移入回收站 |
| `_ARCHIVE_OLD_frontend_gpt_deliverables_20260911` | 旧前端交付快照，已被新体验基线取代 | 已移入回收站，可恢复 |
| `Z-Brand-Core` | 旧本地生产仓，已完成证据回收并移入回收站；远端仓库未修改 | 不再作为本地工作入口 |
| `edge-cdp-profile` | 旧浏览器 Profile，无当前产品引用 | 已移入回收站，可恢复 |

## 明确不导入的内容

- 旧 `local_ai_runtime` 包：与当前 `local_ai_client`、`intelligence`、`provider_registry` 形成重复实现风险。
- 旧 qwen2.5 / 绝对 D 盘模型配置：与当前 Ollama 实际模型不一致。
- 旧 `monitor.db`、staging DB、migration backup DB：未经数据真相链和迁移验证，不进入生产。
- 其他仓库的 AI、增长、审计和采集实现：保持仓库边界，不复制为第四产品线或平行 Collector。

## 清理验收

- 本地产品源码唯一入口：`D:\LUMENIS_REBUILD\序\序境`
- 当前序境工作树：应保持干净；任何清理操作不得修改生产数据库。
- 回收站清理：两个退役根目录均已逐项移动成功并验证原路径不存在；内容可从 Windows 回收站恢复，未做不可逆永久删除。
- GitHub Actions 账户计费门禁：属于账户外部状态，不由源码解决；本地开发、测试和本地 Runtime 不受此门禁影响。
