# ZBIP Feature Ownership

> Z-Brand Intelligence Platform 共享能力唯一 Owner 注册表。所有跨仓库共享的能力、协议、数据结构必须在此注册，明确唯一 Owner 和使用方式。
>
> 版本：v1.0 · 维护者：AI-D Hub · 最后更新：2026-08-31

---

## 1. 核心规则

1. **每个共享能力只有一个 Owner** — 避免多仓库维护导致版本冲突
2. **其他仓库通过 Contract / Adapter / API / Evidence 使用** — 禁止复制核心实现
3. **Owner 变更必须经过 Cross-Repository Validation** — 不能静默转移
4. **能力废弃必须标注 Deprecated + 迁移路径** — 不能直接删除
5. **版本号遵循 SemVer** — MAJOR.MINOR.PATCH

---

## 2. 设计系统能力

| 能力 ID | 能力名称 | Owner | 版本 | 消费方式 | 状态 |
|---|---|---|---|---|---|
| DS-001 | Design Tokens | AI-D | v1.0 | CSS 变量 / JSON | ✅ Active |
| DS-002 | Icon System | AI-D | v1.0 | SVG 组件 | ✅ Active |
| DS-003 | Motion Tokens | AI-D | v1.0 | CSS transition / animation | ✅ Active |
| DS-004 | Color Palette | AI-D | v1.0 | 包含在 DS-001 | ✅ Active |
| DS-005 | Typography Scale | AI-D | v1.0 | 包含在 DS-001 | ✅ Active |
| DS-006 | Frosted Glass Style | AI-D | v1.0 | CSS backdrop-filter | ✅ Active |
| DS-007 | Status Dot System | AI-D | v1.0 | CSS 圆点组件 | ✅ Active |

---

## 3. 工程治理能力

| 能力 ID | 能力名称 | Owner | 版本 | 消费方式 | 状态 |
|---|---|---|---|---|---|
| EG-001 | Evidence Schema | DCC | v0.4 | JSON Schema / 数据结构 | ✅ Active |
| EG-002 | Task Contract (7字段) | DCC | v0.1 | JSON / 文本模板 | ✅ Active |
| EG-003 | Acceptance Levels L0-L5 | DCC | v0.1 | 枚举 / 状态机 | ✅ Active |
| EG-004 | GitHub Read-only Audit | DCC | v0.2 | JS 模块 / API | ✅ Active |
| EG-005 | Local AI Bridge (127.0.0.1:8787) | DCC | v0.3 | HTTP API | ✅ Active |
| EG-006 | Permission Matrix | DCC | v0.3 | 配置 / 闸门函数 | ✅ Active |
| EG-007 | Snapshot + Change Plan | DCC | v0.4 | JS 模块 | ✅ Active |
| EG-008 | Capability Delta (7-Gate) | DCC | v0.4 | Python 模块 | ✅ Active |
| EG-009 | Learning Promote (5-Gate) | DCC | v0.5 | Python 模块 | ✅ Active |
| EG-010 | Cross-Repository Validation | DCC | v0.4 | 编排流程 | ✅ Active |
| EG-011 | Security Gate (敏感数据过滤) | DCC | v0.2 | JS/Python 函数 | ✅ Active |

---

## 4. 研究学习能力

| 能力 ID | 能力名称 | Owner | 版本 | 消费方式 | 状态 |
|---|---|---|---|---|---|
| RL-001 | Research Registry | AI-D | v0.1 | JSON / Python 模块 | ✅ Active |
| RL-002 | Research Learning Store | DCC | v0.4 | JS 模块 / API | ✅ Active |
| RL-003 | Shadow Learning Protocol | AI-D | v0.1 | 协议文档 / 流程 | ✅ Active |
| RL-004 | Learning Cycle | DCC | v0.4 | Python 模块 | ✅ Active |
| RL-005 | Capability Registry | AI-D | v0.1 | 注册表 / 文档 | ✅ Active |
| RL-006 | Case Library | AI-D | v0.1 | Markdown / JSON | ✅ Active |
| RL-007 | Benchmark Registry | AI-D | v0.1 | JSON | ✅ Active |
| RL-008 | AI Collaboration Protocol | AI-D | v0.1 | 协议文档 | ✅ Active |
| RL-009 | Platform Inspection | DCC | v0.4 | Python 模块 | ✅ Active |
| RL-010 | Failure Learning Record | DCC | v0.4 (规划) | 数据结构 | ⚠️ Planned |

---

## 5. 生产业务能力（Z-Brand-Core 独有）

| 能力 ID | 能力名称 | Owner | 版本 | 消费方式 | 状态 |
|---|---|---|---|---|---|
| PB-001 | Subject Filter (SUBJECT_WORDS) | Z-Brand | 生产 | Python 函数 | 🔴 生产红线 |
| PB-002 | subject_hit() | Z-Brand | 生产 | Python 函数 | 🔴 生产红线 |
| PB-003 | _subject_sql_and_values() | Z-Brand | 生产 | Python 函数 | 🔴 生产红线 |
| PB-004 | aggregate_events() | Z-Brand | 生产 | Python 函数 | 🔴 生产红线 |
| PB-005 | build_daily_report() | Z-Brand | 生产 | Python 函数 | 🔴 生产红线 |
| PB-006 | Collection Adapter (RedNote/XHS) | Z-Brand | v2.0 | Python 模块 | ✅ Active |
| PB-007 | Dashboard / 统计 / 事件 / 报告 | Z-Brand | 生产 | Web 界面 | ✅ Active |

**🔴 生产红线规则**：以上能力绝对禁止其他仓库修改、复制或绕过。任何变更必须先在影子环境验证，经过人工批准后才能进入生产。

---

## 6. 移动端能力（SICI 独有）

| 能力 ID | 能力名称 | Owner | 版本 | 消费方式 | 状态 |
|---|---|---|---|---|---|
| MB-001 | PWA (manifest + service worker) | SICI | v1.0 | Web 标准 | ✅ Active |
| MB-002 | Browser Surface | SICI | v0.1 | 浏览器控制 | ⚠️ 开发中 |
| MB-003 | Code / Run / Preview | SICI | v0.1 | 前端功能 | ⚠️ 开发中 |
| MB-004 | Upgrade Modules (统一日志/双池/适配器) | SICI | v1.0 | Python 模块 | ✅ Active |
| MB-005 | Shadow Run | SICI | v0.1 | 影子运行环境 | ✅ Active |

---

## 7. 能力依赖关系

```
AI-D (设计系统 + 研究)
    ↓ 提供 Design Tokens / Icon / Motion / Research Protocol
DCC (工程治理 + 学习)
    ↓ 提供 Evidence Schema / Task Contract / GitHub Audit / Bridge
SICI (移动端执行)
    ↓ 提供 Browser Surface / PWA 体验
Z-Brand-Core (生产业务)
    ↓ 提供 Collection Adapter / 生产数据 / 业务验证
```

**依赖方向**：AI-D → DCC → SICI → Z-Brand（研究到生产）
**反馈方向**：Z-Brand → SICI → DCC → AI-D（生产经验反哺研究）

---

## 8. 变更流程

### 新增共享能力

1. 在 AI-D 提出 Proposal
2. 明确 Owner / 版本 / 消费方式 / 依赖
3. Shadow 验证
4. Cross-Repository Validation
5. 注册到此文件
6. 通知所有相关仓库

### 修改共享能力

1. Owner 提出变更
2. 评估影响范围（哪些仓库消费此能力）
3. Shadow 验证 + 兼容性测试
4. Cross-Repository Validation
5. 更新版本号
6. 通知消费仓库升级

### 废弃共享能力

1. 标注 Deprecated
2. 提供迁移路径和替代方案
3. 至少保留 2 个版本周期
4. 确认所有消费仓库已迁移
5. 正式移除

---

## 9. NOT_VERIFIED / 待确认

1. SICI 双主题/设计系统现状 — 未读取 index.html 确认
2. AI-D src/ 和 tools/ 实际代码 — 未读取子目录
3. Z-Brand-Core 完整能力清单 — 目录被截断
4. Failure Learning Record 实现状态 — 标记为 Planned，需确认
5. Browser Surface 实现细节 — SICI 独有，需进一步读取

---

*本文件由 AI-D Hub 维护，是四库共享能力的唯一权威注册表。任何冲突以此文件为准。*
