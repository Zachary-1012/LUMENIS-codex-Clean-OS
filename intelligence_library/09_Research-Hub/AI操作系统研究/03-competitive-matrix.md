# C｜OSAI 竞争/案例矩阵

> 交付物 C · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## Build vs Integrate vs Adapt 决策汇总

| 类别 | Build（自研） | Integrate（集成） | Adapt（适配） |
|------|-------------|-------------------|--------------|
| **占比** | 60% | 25% | 15% |
| **代表** | Experience Engine、Research Engine、Contract Studio、Evidence Auditor、Learning Loop、Security Gateway、Permission OS、Evaluation Matrix | Trae、Claude Code、BrowserGym、Browser Run、E2B Firecracker、SWE-bench、Qdrant/Milvus | Plan Compiler、Perception Engine、AI IDE 集成、Reflexion 机制、Constitutional AI、Self-Refine |

## 关键竞争对手分析

| 产品 | 核心能力 | 优势 | 劣势 | OSAI 策略 |
|------|---------|------|------|-----------|
| **Claude Code** | 端到端编码 | SWE-bench 88.6%，CLI-first，强推理 | 国际访问，成本高 | Integrate（国际首选执行引擎） |
| **Codex CLI** | 终端自主编码 | Terminal-Bench 83.4% 第一，GPT-5.5 | 假阳性率高 | Integrate（备选） |
| **Trae** | AI IDE+SOLO 主-子 Agent | 国内免费，多模型，MCP 原生 | 企业功能待完善 | Integrate（国内首选执行引擎） |
| **Devin** | 全栈自主开发 | 长程任务，自主调试 | 成本极高，黑盒 | Inspire（长程规划+回滚） |
| **Cursor/Windsurf** | AI IDE 插件 | 开发者体验好 | 受限于 IDE，自主性弱 | Adapt（集成研究流程） |
| **OpenAI Operator** | 浏览器自主操作 | Browsing Camp 50%+ | 封闭，不可定制 | Inspire（Hybrid 架构） |
| **BrowserGym** | 浏览器 Agent 评测框架 | 开源，可扩展，Benchmark 完善 | 仅框架，无运行时 | Adapt（Research Framework 基础） |
| **MemGPT/Letta** | 分层记忆管理 | OS 级虚拟上下文，生产就绪 | 仅记忆，无经验学习 | Adapt（热/温/冷存储策略） |
| **E2B** | 代码执行沙箱 | Firecracker 80ms 冷启动，1B+ 运行量 | 仅沙箱，无权限管理 | Integrate（沙箱运行时） |
