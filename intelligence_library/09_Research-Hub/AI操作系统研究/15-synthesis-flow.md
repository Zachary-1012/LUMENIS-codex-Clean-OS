# Q｜三层情报综合判断流程

> 交付物 Q · 所属：OSAI P0 三位一体研究体系 · 综合判断层

## 七步综合判断流程

```
三层情报（AI Frontier / Product Intel / Market Intel）
        ↓
Step 1 归一化（统一格式、去重、来源分级）
        ↓
Step 2 相关性打分（与 CTH / ZBMP / OSAI 相关性）
        ↓
Step 3 交汇识别（单层 vs 跨层影响）
        ↓
Step 4 冲突检测（三条线结论矛盾时）
        ↓
Step 5 决策分级（P0 / P1 / P2 / 暂缓 / 不做）
        ↓
Step 6 生成机会/Gap 清单（含证据引用）
        ↓
Step 7 产出产品决策 → 架构 → Contract → ZBC
```

## 决策分级标准

| 级别 | 定义 | 动作 |
|------|------|------|
| IGNORE | 与三层均无关 | 忽略 |
| MONITOR | 可能有影响但未明确 | 记录+持续观察 |
| RESEARCH | 需要深入研究 | 派发研究任务 |
| ADAPT | 有价值需改造 | 进入方案设计 |
| ADOPT | 直接采用 | 进入 P0/P1/P2 |
| P0/P1/P2 | 优先级 | 进入 Roadmap |

## 12 个三层交汇场景（示例）

1. Agent 安全事件（Market）→ OSAI 安全研究（AI Frontier）→ ZBMP 隔离标准
2. 舆情量化评估趋势（Market）→ CTH 报告升级（Product）→ OSAI NLP 组件
3. Codex Persistent Mode（Market）→ OSAI Proactive 研究（AI Frontier）→ ZBMP 长任务运行时
4. …（完整 12 场景详见研究轨迹）

## 冲突处理机制

- 三条线结论矛盾 → 以证据强度 + 用户意图 + 商业优先级排序
- AI Frontier 推荐 vs Product 需求冲突 → 以 Product 落地价值优先
- 安全红线不可被商业价值覆盖

## 反馈闭环

ZBC 执行后产生 Evidence → 回流 OSAI → 更新三层情报 → 下一轮判断
