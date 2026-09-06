# 双库最终核对报告 + 全面开发冲刺计划（2026-09-02）

> 依据：《AI 编程基线 v1.0》双库真实 HEAD/源码/运行为唯一事实来源
> ZBC HEAD `20eb035 v5.9.9 自动保存版本（21:30 巡检）` / OSAI HEAD `b117cbd docs(reconciliation): P0/P1 队列对账 — P0 3/3 达成、P1 关键项落地（286回归通过）`

---

## 一、最终核对结论

### 1.1 测试基线（Release Gate 核心）
| 项 | 结果 |
|---|---|
| ZBC 全量回归 | **286 passed**（含 browser_runtime 48 项 + safe_collection 10 项 + Failure Recovery 17 项） |
| OSAI 最小基线 | **8 passed**（契约/报告/learning-feed 完整性） |
| 关键测试集 | schema_registry + safe_collection + event_aggregation + agent_security = 38 项全过 |
| 真实 E2E | 生产系统 8200/8201 在线；CDP 9222 在线（XHS_CN_PRIMARY，小红书 explore） |

### 1.2 安全与红线
| 项 | 结果 |
|---|---|
| 硬编码 ARK key 移除 | ✅ 已从代码 + HEAD 清除（仅 .env 环境变量，gitignore 保护） |
| 全仓密钥扫描 | ✅ 无真实硬编码密钥（仅空默认值 os.getenv 模式） |
| .env 入库 | ✅ 未跟踪，历史无提交 |
| subject_rules 权威 | ✅ 17 正向/18 排除词，语义正确（排除一票否决/正向命中/无关过滤），未破坏 |
| 云智(ARK) key 有效性 | ⚠️ **已失效**（401 AuthenticationError: key doesn't exist）——需用户提供新 key |

### 1.3 双库状态
| 仓库 | HEAD | 同步 | 待提交 |
|---|---|---|---|
| ZBC | 含安全修复 3521383 + 自动进程提交 | ✅ 与 origin 同步 | static/zbmp-workbench.html（业务，不动）+ submodule（在途，不动） |
| OSAI | b117cbd | ✅ 与 origin 同步 | components 三仓 untracked（保持现状） |

---

## 二、待办队列对账（冲刺起点）

### 已达成（不需做）
- P0：3/3（aggregate_events / subject_hit 收敛 / archive 密钥风险消除）
- P1 关键项：safe_collection 契约 / 单一权威 DB Schema / 权限审计 / risk_engine / guardian / 证据流转 / app.py 拆分规划（app_refactor_blueprint 已存在）

### 剩余可冲刺（真实存在）
| 优先级 | 项 | 说明 |
|---|---|---|
| P1-A | **OpenAI 智能功能补强** | 用户点名方向；需云智新 key 后端到端验证舆情分析/摘要/聊天/报告生成 |
| P1-B | OpenAPI 文档 | ZBC 200+ API 无 OpenAPI 文档，冲刺补齐（swagger 生成） |
| P1-C | 头条采集适配器 | P1 队列缺失项，按 safe_collection 契约实现 |
| P2-A | UI 主题统一（ZBIP tokens 去重） | 双库设计令牌收敛 |
| P2-B | 临时脚本/backups 清理 | backups 目录 + 临时脚本治理 |
| P2-C | zbrand 目录 | 待确认用途后处置 |
| UNKNOWN | 13 项待运行时审计 | 启动系统后逐项消除 |

### 冲刺阻塞项
- **云智(ARK) API key 已失效**：OpenAI 智能功能补强需新 key。系统已安全降级（无 key 明确报错，不崩溃）。

---

## 三、全面开发冲刺计划

### 冲刺目标：完成 Release Gate（整体 NOT COMPLETE → 推进达标）

**Sprint 1（基础加固）**：
1. 云智 key 到位后：OpenAI 智能功能端到端验证（ark_llm 全链路）+ 能力扩展
2. OpenAPI 文档生成（swagger-ui + 200+ API 标注）
3. 头条采集适配器（对齐 safe_collection 契约）

**Sprint 2（一致与清理）**：
4. UI 主题统一（ZBIP 设计令牌收敛）
5. backups/临时脚本清理
6. 13 项 UNKNOWN 运行时审计消除

**Sprint 3（验证与交付）**：
7. 全量回归 + E2E 全链路
8. 更新施工报告 V1 → V2（Release Gate 逐项 PASS）
9. 双库推送

### 冲刺守则（延续基线）
- 每项：先审计 → 再编码 → 再测试 → 再验证 → 再交付
- 本地 E2E 验证后再推送
- 不破坏现有稳定功能；不重复造已有能力
- 红线：不碰 SUBJECT_WORDS/排除词/产品 Truth；Cookie/Token/密钥永不入库
