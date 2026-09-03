# 序境-Core · Xujing Core

> **序境（Xujing）** — 生产核心系统  
> **品牌哲学：芥子纳须弥**

## 1. 产品定位

序境-Core 是序境双子库中的生产核心，负责承载可验证的业务事实、生产数据、采集、分析、风险、任务、报告与运行时能力。

它不是通用舆情 SaaS 模板，也不是 AI 实验场。生产规则、数据真相、安全约束和发布质量必须在本库内可验证。

## 2. 双子库边界

```text
序境
├── 序境-Core
│   └── Production Truth
└── 序境-Intelligence
    └── Research & Intelligence
```

### 序境-Core

负责：
- 生产代码与生产数据库
- 数据采集与来源适配
- 主体过滤与数据质量
- 舆情、事件、风险与分析
- KOS / Campaign 等生产能力
- 报告与数据导出
- API、Runtime、Health、Recovery
- 测试、证据与发布

### 序境-Intelligence

负责研究、AI、知识、Benchmark、技术验证与研发建议。研究结果不得绕过 Contract → Implementation → Test → Evidence 直接改变生产真相。

## 3. Canonical 层级

所有生产资产必须能够映射到：

```text
Product
  ↓
Subsystem
  ↓
Module
  ↓
Page
  ↓
Function
  ↓
Data
  ↓
API
  ↓
Runtime
  ↓
File
  ↓
Class / Function
```

治理横向贯穿全部层级：Policy / Permission / Safety / Evidence / Audit。

## 4. 核心功能域

| 域 | Canonical | 职责 |
|---|---|---|
| 观测 | Observation | 采集、来源、舆情、事件、热点 |
| 洞察 | Insight | 分析、趋势、品牌、竞品、风险 |
| 行动 | Action | KOS、Campaign、任务、执行 |
| 报告 | Reporting | 日报、周报、月报、专报、导出 |
| 系统 | System | 数据源、账号、AI、权限、安全、设置 |

## 5. 采集安全规则

自动采集默认受控，仅保留合规来源与合法账号/API 接口。

- 自动窗口：每日 00:00、12:00
- 自动采集：可开启 / 关闭，默认隐藏入口
- 其他采集：默认手动，每次最长 30 分钟
- 合法专业号、授权账号、官方 API 可作为合规来源
- 所有任务必须经过 Preflight / Policy / Identity / Session / Risk 检查
- 风险触发 STOP → COOLDOWN → HUMAN REVIEW
- 不通过换账号、换 Cookie、换 IP 或提高频率规避平台安全限制
- 数据进入生产前必须经过 Validate / Normalize / Filter / Evidence

## 6. AI 边界

AI 是生产能力的增强层，不得绕过核心规则成为生产真相的最终裁决者。

生产 AI 结果必须记录必要的模型、提示词、输入、输出、置信度、最终结果及人工修正信息；重要结论必须可追溯至证据。

## 7. UI / UX 原则

序境采用克制、高密度、操作优先的信息设计：

- 细线 Icon 与小型功能图标
- 清晰的导航层级
- 数据优先，视觉服务于判断
- 图表可下钻至数据与证据
- 禁止巨型 Logo、巨型 Icon、大字报式布局
- 禁止为了装饰牺牲操作效率
- 中 / 英 / 韩共用稳定 Canonical ID，语言仅改变展示层
- 响应式布局必须保持信息层级，不允许多语言导致组件失控

## 8. 数据与报告

标准数据链路：

```text
Source → Collection → Raw → Normalize → Analyze → Evidence → Insight → Report
```

标准报告骨架：

```text
Executive Summary
→ Key Findings
→ Event / Issue
→ Impact
→ Risk
→ Evidence
→ Trend
→ Recommendation
→ Appendix / Data
```

内容创作不是固定报告模板，而是根据需求、受众、场景和目标动态选择结构。

## 9. 文件治理

正式文件必须归属于明确模块，不允许长期堆积在根目录。

推荐治理结构：

```text
00-GOVERNANCE/
01-PRODUCT/
02-ARCHITECTURE/
03-DESIGN/
04-DATA/
05-RUNTIME/
06-REPORT/
07-RESEARCH/
08-AUDIT/
99-ARCHIVE/
```

资产状态统一使用：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE`。

删除前必须完成引用、依赖和运行验证。历史资产如仍具证据价值，应进入 `99-ARCHIVE`，而不是污染生产目录。

## 10. Canonical 命名

正式产品名：**序境 / Xujing / 서경**  
品牌哲学：**芥子纳须弥**

`Zachary` 仅作为历史仓库、研发身份或必要技术标识，不再作为对外产品品牌。

功能名称应体现职责，不以品牌词重复污染文件、类和函数命名。

## 11. 质量 Gate

任何新增或修改必须经过：

```text
Plan
→ Contract
→ Implementation
→ Test
→ Evidence
→ Audit
→ Release
```

涉及破坏性 Rename / Migration / Delete 时，必须先完成依赖扫描和回归验证。

## 12. 当前原则

- 不重新建立第三核心库
- 不重复建设已经存在的 Core 能力
- 不绕过生产规则
- 不以 AI 替代确定性安全规则
- 不以 UI 重构解决本应由信息架构解决的问题
- 不删除未经审计的历史资产
- 不让新模块脱离 Canonical Registry 独立生长

## 13. 研发入口

本 README 是当前生产核心的产品与工程入口说明。详细架构、策略、审计和运行文档应以仓库内当前有效文件及最新基线为准；历史方案不作为新开发依据。

**Status: Active · Production Core · Governed by Zero Sequence**
