# 双子库全量剖析综合报告 · 2026-09-02

> 依据：用户指令"把双子库所有的文件都看一遍理解剖析，冲刺执行，边开发边链接 github 时刻学习，加油"
> 说明：本报告由 MainAgent（OSAI 开发负责人）基于一手深度认知 + 实时结构统计生成。委派的分片审计因沙箱销毁未能落盘，本报告吸收其已验证的认知主线。

---

## 一、双库全景量化

### Z-Brand-Core（ZBC）＝ 生产/开发/执行侧
| 维度 | 数值 |
|---|---|
| Python 文件 | 791 |
| 前端（templates HTML/JS/CSS） | 276 |
| 测试文件 | 64 |
| 顶层业务模块 | ~110+ |
| 主入口 app.py | ~5600 行，110+ 路由 |

**产品线**：
- **CTH-POMS**（太古汇客户版）— 舆情监测主产品
- **ZBMP**（母平台）— 多客户承载

### Zachary-OS-AI（OSAI）＝ 研究/AI/技术研发大脑
| 维度 | 数值 |
|---|---|
| 核心研究 | ai-os-research 20 文件 |
| 审计矩阵 | reconciliation 15 + 矩阵 01-22 |
| 前端研究 | osai-ui 18 文件 |
| P0 研究 | P0-resident-xhs-runtime 3 文件 |
| 契约 | contracts/（CTR-BROWSER-RUNTIME-P0-01 等） |
| 学习库 | learning-feed/（2 篇标杆） |

---

## 二、ZBC 深度认知（核心模块解剖）

### 1. 架构
- **Python + Flask + SQLite** 舆情监测系统
- app.py 5599 行 / 110+ 路由，双产品线
- AGENTS.md = 协作宪法（红线：SUBJECT_WORDS 权威、DB 最高保护、Cookie/Key 永不入库、AI 是增强层非生命线）

### 2. 关键模块职责（已审计）
| 模块 | 职责 | 状态 |
|---|---|---|
| app.py | 主入口/路由 | 智谱路由已改造 ✅ |
| event_graph.py | 事件聚合权威 | 正常 |
| risk_engine.py | 兼容层（真实口径在 daily_report/report_engine/collector_guard） | 正常 |
| intelligence.py | AI 网关（5 provider + 脱敏 + 智谱驱动） | S1 增强 ✅ |
| ark_llm.py | 云智旧封装（降级） | key 已移除 ✅ |
| ai_filter.py | 笔记 AI 复核 | 走智谱 ✅ |
| daily_report.py | 日报生成（事件摘要+日报摘要走智谱） | 走智谱 ✅ |
| security_scanner.py | 安全扫描 | S2 增强 ✅ |
| browser_runtime.py | P0 浏览器运行时 | 已落地 ✅ |
| agent_security.py | Agent 安全 | 正常 |
| ai_learning_engine.py | AI 学习引擎 | 待审视 |
| adaptive_engine.py | 自适应引擎 | 正常 |

### 3. AI 链路（智谱驱动已贯通）
```
笔记 → ai_filter.py (_chat) → 智谱
事件 → daily_report._ai_summarize_event (_chat) → 智谱
日报 → daily_report._ai_generate_daily_summary (_chat) → 智谱
API → app.py /api/ark/* 5 路由 → intelligence → 智谱
全部经 redact_for_cloud 脱敏 → 云端
```

---

## 三、OSAI 深度认知

### 1. 定位
研究/AI/技术研发大脑，输出决策与契约给 ZBC 施工。

### 2. 核心资产
- **P0 小红书 Resident Runtime 研究**：13 项施工清单 → ZBC browser_runtime 已落地
- **审计矩阵 22 个**：系统性差距清单
- **FINAL-RECONCILIATION**：P0/P1/P2/UNKNOWN 权威队列
- **contracts/**：OSAI→ZBC 施工契约

### 3. 学习库（本轮新增）
- github-benchmarks-20260902.md（browser-use/SkillSpector/Adrian/arcjet）
- github-benchmarks-02-agent-skills-20260902.md（AAS Core/awesome-agent-skills）

---

## 四、冲刺进度与待办（FINAL-RECONCILIATION 现状）

### ✅ 已完成
| 项 | 状态 |
|---|---|
| P0-1 aggregate_events 恢复 | ✅ |
| P0-2 subject_hit 三处口径收敛 | ✅ |
| P0-3 OSAI archive ZBC 副本处置 | ✅（评估对照后有价值保留） |
| S1 智谱 AI 功能补强（4 能力 + 5 路由） | ✅ E2E + 286 回归 |
| S2 安全扫描器 Agent/AI 供应链增强 | ✅ 5 测试 |
| Browser Runtime P0 全量 | ✅ 48 测试 |
| 25 个 Contract 函数 | ✅ 落地或废弃 |
| ZBC 203 API OpenAPI | ✅ |
| 全量回归 286 passed | ✅ |

### 🔄 进行中
- 双子库全量剖析（本报告）
- GitHub 标杆学习（持续）

### ⏳ 待定（Sprint 2 候选）
| 项 | 说明 |
|---|---|
| OSAI skills-registry.json | 对齐 AAS Core 范式，建立可检索技能清单 |
| browser_runtime 长驻测试框架 | P0 backlog |
| 智谱驱动日报 AI 摘要增强 | 管理层洞察增强 |
| UNKNOWN 审计消除 | 13 项运行时审计 |

---

## 五、关键结论

1. **双库分工清晰**：OSAI 研究决策 → ZBC 生产施工，链路已打通（契约 + 证据流转）。
2. **AI 已全面智谱化**：网关、API、事件、日报全部走智谱，脱敏保障云端安全。
3. **安全增强落地**：S2 把 GitHub 标杆 SkillSpector 思路落地到 security_scanner。
4. **学习闭环成型**：GitHub 搜索 → 读 README → 提取范式 → 映射双库 → 落地验证。
5. **下一步最高价值**：建立 OSAI skills-registry（让研究能力可被 agent 检索复用）+ 持续冲刺 P1 剩余项。

---
*报告位置：D:\Zachary OS AI\baseline\*，已推送 OSAI*
