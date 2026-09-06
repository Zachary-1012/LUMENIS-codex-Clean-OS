# XHS Topic Monitor Global Adaptation Research V2

## 研究结论

当前 Core 已具备 Adapter Registry、统一 CollectionResult/Status、动态调度目录和 XHS App Topic Adapter 框架，因此不应新建平行采集系统。

GitHub 同类案例进一步验证了几个可复用方向：

- RedNote MCP：持久 Cookie/Profile、首次人工登录、后续复用 Session。
- rednote-rag：内容缓存、OCR、语义索引、来源回溯、增量同步。
- dots.ocr：网页画面/复杂图文 OCR 与结构化解析能力，可作为后续 Evidence/OCR 研究对象。
- 公开 XHS/RedNote scraper：Adapter/provider 抽象和浏览器生命周期值得研究，但反检测/规避实现不进入生产。

## 适配判断

### 保留

- BasePlatformAdapter
- Registry
- CollectionStatus
- Subject Filter
- Dedup
- Risk/Event/Knowledge
- 现有前端导航与视觉升级

### 改造

- Topic Monitor 调度入口
- Source Contract
- Temporary 10×10 policy
- Session health / browser lifecycle
- Provenance metadata

### 暂不改

- 现有 UI 视觉体系
- 主要导航层级
- Risk/Event/Knowledge 核心逻辑
- 数据库整体结构

## 全局原则

业务层稳定，数据源可替换；前端消费统一业务状态，不感知具体采集技术。

当前临时浏览器只是 fallback，不是最终架构。
