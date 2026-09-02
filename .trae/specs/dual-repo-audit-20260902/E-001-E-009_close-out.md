# E-001 ~ E-009 Close-Out Log（README 架构错误修复结案）

> **审计批次**：dual-repo-audit-20260902 / Spec Mode Implement
> **规则版本**：AGENTS.md V2.0 + ZOSAI IMMUTABLE BASE-001~022
> **状态枚举**：DONE ✅ / PARTIAL ⚠️ / OPEN ❌
> **每字段**：错误编号 / 描述 / Task 编号 / 修复前原文片段 / 修复后位置 / 状态

| # | 描述 | Task | 修复前原文（片段）| 修复后位置（绝对路径 + 锚点）| 状态 |
|---|---|---|---|---|---|
| E-001 | 术语：全仓 "三仓" → 升级为 "四库"（补齐 AI-DRH 第四仓），旧称"三仓"属于历史遗留，README 顶层不再出现 | T1 A 侧 + T3 B 侧 + T4 E-008 组件侧 | ZBC README §2 / §4 / §9 多处："三仓体系 = ZBC + SICI + DCC"；ZOSAI README 多处"三仓"；组件矩阵/指针/清单标题"三仓库统一…"；DCC 多处"三仓验证" | ① [ZBC README §2 第 62 行](file:///D:/Taikoo-monitor-new/README.md#L62) 首行："四库定义：ZBC + SICI + DCC + AI-DRH" ② [ZOSAI README 标题 + §1 第 29 行](file:///D:/Zachary%20OS%20AI/README.md#L29) 四库角色总览段 ③ [THREE_REPOSITORY_SYSTEM_MATRIX.md 标题升级（保留文件名不改）](file:///D:/Zachary%20OS%20AI/components/Development-Command-Console/docs/THREE_REPOSITORY_SYSTEM_MATRIX.md#L1) ④ [PRE_CHANGE_THREE_REPO_CHECKLIST.md](file:///D:/Zachary%20OS%20AI/components/Development-Command-Console/docs/PRE_CHANGE_THREE_REPO_CHECKLIST.md#L1) ⑤ [SICI THREE_REPOSITORY_MATRIX_POINTER.md](file:///D:/Zachary%20OS%20AI/components/SICI-Core/docs/THREE_REPOSITORY_MATRIX_POINTER.md#L1) ⑥ [SICI PLATFORM_README §6](file:///D:/Zachary%20OS%20AI/components/SICI-Core/PLATFORM_README.md#L69) ⑦ [AI-DRH CAPABILITY-REGISTRY §1/§2/§4](file:///D:/Zachary%20OS%20AI/components/AI-Development-Research-Hub/CAPABILITY-REGISTRY.md#L12) ⑧ [AI-DRH PLATFORM_BASELINE §1/§3/§4/§5/§6](file:///D:/Zachary%20OS%20AI/components/AI-Development-Research-Hub/PLATFORM_BASELINE.md#L15)。验证：ZBC README grep "三仓" = 0 处（✅）；ZOSAI README grep "三仓" = 0 处（✅）。历史学习库 v2/v3 JSON 归档快照保留原貌不破坏历史 | ✅ DONE |
| E-002 | A 侧补生产边界硬约束："CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件" | T1 + T2 | 原 ZBC README 只有单仓描述，缺双子边界显式声明 | ① [ZBC README 第 8 行 顶部 banner 硬约束（不可编辑）](file:///D:/Taikoo-monitor-new/README.md#L8) ② [§2 双子 10 维对比 生产依赖关系行第 71 行](file:///D:/Taikoo-monitor-new/README.md#L71) 两处引用 AGENTS.md §2 锚点 | ✅ DONE |
| E-003 | A 侧补资产清单 8 大类分类表（含路径/数量/Owner/备份/是否允许进 Git 主分支 6 字段）| T2 | 原 README 仅有零散"21,656 files / 8150 MB"数字，缺资产清单 | [ZBC README §9.5 资产清单 8 大类（源码/DB/数据资产/文档/测试/子模块/凭证配置/静态）](file:///D:/Taikoo-monitor-new/README.md#L810-L860) 6 字段齐全；所有数字 v5.9.7 / 42 项 / 264KB / 667 笔记 / 151 事件 / 13 日报 / 178 采集 / 370 ai_filter / 7135 review / 180 event_mentions 全部映射至对应资产类 | ✅ DONE |
| E-004 | A 侧补 允许/禁止/受控 四层矩阵（产品/仓库/组件/研发），每行附依据标签 | T2 | 原 README §13 AGENTS 引用散列，缺集中禁止允许矩阵 | [ZBC README §9 四层矩阵 产品 9 行 / 仓库 14 行 / 引用 §4 Owner 组件 8 行 / 研发 9 行](file:///D:/Taikoo-monitor-new/README.md#L760-L810) 每行 [AGENTS §x] [BASE-xxx] [DUAL-REPO §x] [RED-LINE §x] 依据标签；与 evidence-traceability.md Part A 一一对齐（42 行） | ✅ DONE |
| E-005 | B 侧（ZOSAI）补本仓四库声明（§1 首节即四库，不依赖旧三仓）| T3 | 原 ZOSAI README（65 行审计表头）仅有 "22 份交付"，无产品定位与四库结构 | [ZOSAI README 标题（第 1 行）"Zachary 独立 AI 平台｜四库治理与收敛总枢纽"](file:///D:/Zachary%20OS%20AI/README.md#L1) + §1 第 29 行 四库角色总览 4 行表（ZBC/SICI/DCC/AI-DRH），明确 AI-DRH 为第四仓 | ✅ DONE |
| E-006 | B 侧补双子交叉引用（顶部对端链接 + §2 双子关系 10 维对比 + §11.3 回链，三元 repo/branch/section 齐全）| T3 + T5.1 | 原 ZOSAI README 缺双子产品关系段 | ① [ZOSAI README 第 6 行 顶部对端 banner](file:///D:/Zachary%20OS%20AI/README.md#L6) 含 last_verified_sha=b497277 ② [§2 双子对比 10 维（第 50 行起）含反哺环 BASE-019](file:///D:/Zachary%20OS%20AI/README.md#L50) ③ [§11.3 跨仓回链 3 条（第 464-469 行）](file:///D:/Zachary%20OS%20AI/README.md#L464) 全部含 last_verified_sha=b497277 + 三元 repo/branch/section | ✅ DONE |
| E-007 | B 仓 .gitignore 同步：docs-wps/ archive/ config/codex/ *.db *.env zip node_modules .venv 等 NFR-009 要求项；解除 README §9.5 "已在 .gitignore 配置"的超前声明 | T4 | ZOSAI 仓无 .gitignore 文件；README §9.5 写 "🚫 永久不 push 主分支（已在本仓 .gitignore 配置）" → 超前声明 ⚠️ HIGH 风险 | 新建 [D:\Zachary OS AI\.gitignore](file:///D:/Zachary%20OS%20AI/.gitignore) 覆盖 6 大类 42 条（归档/DB/凭证/依赖/压缩/OS 编辑器）；§9.5 声明现在与事实一致。验证：glob .gitignore 存在 ✅；docs-wps/** archive/** config/codex/* 三条在文件第 9-11 行 ✅ | ✅ DONE |
| E-008 | B 仓三组件权威基线文档术语 "三仓→四库" 升级（SICI/DCC/AI-DRH 矩阵/指针/清单/注册表/平台基线）| T4（与 T1/T3 配合，T1/T3 做了两仓 README，T4 补组件）| ① THREE_REPOSITORY_SYSTEM_MATRIX.md 标题 "三仓库统一系统矩阵" ② PRE_CHANGE_THREE_REPO_CHECKLIST.md 标题 + Gate0 缺 AI-DRH SHA ③ SICI THREE_REPOSITORY_MATRIX_POINTER.md 标题 + 只给 DCC 链接 ④ SICI PLATFORM_README §6 inspect all three repositories ⑤ AI-DRH CAPABILITY-REGISTRY §1/§2/§4 "三仓库" ⑥ AI-DRH PLATFORM_BASELINE §1/§3/§4/§5/§6 "三仓库" 共 13 处 | ① [DCC THREE_REPOSITORY_SYSTEM_MATRIX.md 标题升级 + Scope 扩展 4 仓 + 三向验证域说明](file:///D:/Zachary%20OS%20AI/components/Development-Command-Console/docs/THREE_REPOSITORY_SYSTEM_MATRIX.md#L1) ② [DCC PRE_CHANGE Gate0 新增 Record AI-DRH SHA](file:///D:/Zachary%20OS%20AI/components/Development-Command-Console/docs/PRE_CHANGE_THREE_REPO_CHECKLIST.md#L13) ③ [SICI 矩阵指针新增 GLOBAL 基线 + Capability Registry 两个入口](file:///D:/Zachary%20OS%20AI/components/SICI-Core/docs/THREE_REPOSITORY_MATRIX_POINTER.md#L6) ④ [SICI §6 Mandatory pre-change 升级 inspect all four repos + 三向与全局基线区分注](file:///D:/Zachary%20OS%20AI/components/SICI-Core/PLATFORM_README.md#L69) ⑤ [AI-DRH CAPABILITY-REGISTRY 注册条件 4/7/状态 verifying+reusable/使用规则](file:///D:/Zachary%20OS%20AI/components/AI-Development-Research-Hub/CAPABILITY-REGISTRY.md#L12) ⑥ [AI-DRH PLATFORM_BASELINE 六处替换（§1/§3/§4/§5 两处/§6）](file:///D:/Zachary%20OS%20AI/components/AI-Development-Research-Hub/PLATFORM_BASELINE.md#L15)。注意：历史学习库（PLATFORM_LEARNING_LIBRARY_v2/v3.md / platform_learning_records.json / research 早期 R 文档）属于存档快照，保留原貌不破坏历史上下文（此为刻意决定，非遗漏） | ✅ DONE |
| E-009 | 两仓 §2 顶部 + §11 全部跳转链接必须含三元（repo + branch + section）+ last_verified_sha，统一指向当前真实 HEAD，而非占位 bd6ed8d | T5.1（配合 T1/T3）| 原 ZBC §2 顶部 last_verified_sha 缺失；ZBC §11 三条 / ZOSAI §11 三条 = bd6ed8d（占位旧基线）；ZOSAI §11 第 2/3 条缺 last_verified_sha | 两仓所有跨仓外链 4+6 条：① A→B 顶部 + §11 三条 last_verified_sha = f0b8bb5（B 仓真 HEAD）② B→A 顶部 + §11 三条 last_verified_sha = b497277（A 仓真 HEAD）③ ZOSAI §11 原缺的第 2/3 条补上 ④ 两条外链底部加说明句，解释"ZOSAI 三组件目标是本地以 components/ 快照同步，所以用 B 仓 SHA 自证" 与 "A 仓三链接目标都是 A 仓自己，所以用 A 仓 SHA 自证"。位置：[ZBC 顶部第 7 行](file:///D:/Taikoo-monitor-new/README.md#L7) / [ZBC §11.2 905-911 行](file:///D:/Taikoo-monitor-new/README.md#L905) / [ZOSAI 顶部第 6 行](file:///D:/Zachary%20OS%20AI/README.md#L6) / [ZOSAI §11.3 464-469 行](file:///D:/Zachary%20OS%20AI/README.md#L464) | ✅ DONE |

---

## 附录：9 项 × 依赖 + 覆盖

```text
E-001（三仓→四库）= T1 + T3 顶层 README  ┐
                                            ├→ E-008（组件侧） 配合 T4 补全
E-007（.gitignore）= T4 独立  ──────────────┘
E-002 / E-003 / E-004 = T1&T2 A 侧
E-005 / E-006        = T3 B 侧
E-009                = T5.1 最后锚定真 HEAD SHA
```

**总验证结论**：9/9 = DONE ✅（E-001/E-008 刻意保留历史学习库原貌不破坏 → 显式说明，非遗漏）
