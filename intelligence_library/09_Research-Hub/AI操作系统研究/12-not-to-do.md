# L｜明确的"不做清单"

> 交付物 L · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

| 不做什么 | 为什么 | 谁做得更好 | 是否直接调用 |
|---------|--------|-----------|-------------|
| **不自建 Coding Agent** | SWE-bench 已被刷穿（19.78% 假阳性），自建无差异化优势；Claude Code/Trae 已达生产级 | Claude Code（88.6%）、Trae（国内免费+SOLO）、Codex（Terminal-Bench 第一） | ✅ 是，通过 Execution Contract 调用 |
| **不自建 Browser Runtime** | BrowserGym/Browser Run 已提供成熟框架和运行时，自建重复造轮子 | BrowserGym（可扩展框架）、Browser Run（MCP 原生+Container）、OpenAI Operator（封闭但强） | ✅ 是，集成 BrowserGym+Browser Run |
| **不做通用 Chatbot** | 与 OSAI 定位（Personal AI R&D OS）冲突，市场已饱和 | ChatGPT、Claude、Gemini | ❌ 否，完全不做 |
| **不做 RAG Knowledge Base** | 普通 RAG 无法实现"强改变"，且与 Experience Engine 定位重叠 | Notion AI、Obsidian、各种 RAG 框架 | ❌ 否，Experience Engine 替代 |
| **不直接修改 ZBC 生产代码** | 违反两库架构边界，OSAI 职责是 Research/Plan/Contract，不是 Implement | Z Brand Core 自身 | ❌ 否，通过 Contract 交付 |
| **不给 Agent 永久权限** | 安全风险极高，Prompt Injection/Memory Poisoning 可导致权限滥用 | — | ❌ 否，Task-bound Permission |
| **不做 Multi-Agent Chatbot** | 与 OSAI 定位冲突，多 Agent 辩论仅用于 Skeptic 高风险决策 | ChatGPT Team、Claude Projects | ❌ 否，仅 Skeptic 用多 Agent |
| **不自建向量数据库** | Qdrant/Milvus 已成熟，自建无优势 | Qdrant、Milvus、Weaviate | ✅ 是，集成 Qdrant/Milvus |
| **不自建沙箱运行时** | E2B Firecracker 已商业化（80ms 冷启动，1B+ 运行量） | E2B、Modal、Docker | ✅ 是，集成 E2B |
| **不追求 Benchmark 刷分** | SWE-bench 假阳性率 19.78%，刷分无实际价值；OSAI 关注实际任务表现和 Learning Lift | — | ❌ 否，用 12 维评估替代 |

## Build vs Integrate vs Adapt 决策原则

1. **核心差异化能力 → Build**：Experience Engine、Permission OS、Research-to-Code Pipeline、Evaluation Matrix
2. **成熟基础设施 → Integrate**：Coding Agent、Browser Runtime、沙箱、向量数据库、Benchmark
3. **有价值但需定制 → Adapt**：Reflexion 机制、Constitutional AI、Self-Refine、MemGPT 分层策略、BrowserGym 框架
