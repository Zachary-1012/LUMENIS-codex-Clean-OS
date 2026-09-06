# G｜AI Browser 技术方案

> 交付物 G · 所属：OSAI P0 三位一体研究体系 · ① AI Frontier Research

## 七层架构

```
Vision + DOM + Browser State + Memory + Policy + Tool + Evidence
```

## 核心决策

- **技术路线**：Hybrid（Vision+DOM+Browser State 融合），非纯 Vision 或纯 DOM
- **框架**：基于 BrowserGym 可扩展框架（Adapt）
- **运行时**：集成 Browser Run（Integrate，原生 MCP/WebMCP + Container）
- **OSAI 定位**：构建 AI Browser Research Framework，聚焦研究方法论，不自研浏览器 Agent
- **Persistent Browser 四大挑战**：状态管理、可审计性、安全沙箱、并发冲突（尚未完全解决，P1 研究）
