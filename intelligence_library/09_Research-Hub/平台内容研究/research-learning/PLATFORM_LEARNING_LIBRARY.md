# 三仓库平台学习资料库 v2.0

> 覆盖 Z-Brand-Core（业务真相）+ DDC（工程控制）+ SICI-Core（移动交互）整个平台
> 按 SICI Research Learning Schema 整理，状态流转：observed → researched → shadowed → verified → reviewed → reusable
> 生成时间：2026-08-31 | 学习范围：GitHub 公开仓库 | v1.0 CTH-POMS专项见 CTH-POMS_LEARNING_LIBRARY.md

---

## 一、三仓库架构 / 工程控制面（DDC 域）

### PL-001 Harness Engineering 23阶段指南（核心参考）
- **仓库**：T-Moody/tm-agent-harness
- **链接**：https://github.com/T-Moody/tm-agent-harness
- **星数**：0（新项目，内容质量极高）| 语言：HTML（单文件完整指南）
- **核心能力**：把仓库变成AI友好的可执行规范，23个阶段从仓库盘点→架构模型→可执行规则→知识库→Agent Skills→调查工作流→执行计划→反馈循环→Repo Doctor→质量评分→文档验证→自动垃圾回收→运行时可观测→可测试运行时→CI免疫系统→人机边界→渐进自治→自维护仓库
- **可借鉴点**：
  - **AGENTS.md作为入口**：不读全仓库，从AGENTS.md→架构文档→生成地图→代码测试，逐层定位
  - **人机写知识分离**：docs/decisions（人写为什么）vs docs/generated（机器生成当前状态）
  - **架构规则可执行化**：禁止依赖、命名空间边界、领域隔离变成CI检查，不只是文档
  - **Repo Doctor单一诊断命令**：Build/Tests/Architecture/Formatting/Dep规则/文档链接 一键健康检查
  - **CI作为免疫系统**：Build+Tests+架构+质量+文档+安全六道门
  - **渐进自治6级**：1 Claude读人写→2 Claude写人审→3 CI验证Claude修→4 Claude自审→5人给目标Claude出验证PR→6人给方向Claude全循环
- **与现有系统关系**：DDC工程控制面可直接参考此框架搭建；Z-Brand-Core的v4_upgrade已有部分雏形（审计日志/版本中心/健康检查），SICI-Core已有研究学习schema
- **状态**：researched
- **owner**：DDC

### PL-002 系统架构逆向工程（第二大脑）
- **仓库**：SpillwaveSolutions/system-architecture-capture
- **链接**：https://github.com/SpillwaveSolutions/system-architecture-capture
- **星数**：0 | 语言：Python
- **核心能力**：逆向工程monorepo/multi-repo为标准OKF schema（PKC+SAC），插件支持Claude Code/Grok/Codex/OpenCode
- **可借鉴点**：多仓库架构自动捕获和标准化，可用于三仓库体系的架构地图自动生成
- **状态**：observed
- **owner**：DDC

---

## 二、AI Agent 框架 / 学习闭环（三仓库共用）

### PL-003 Awesome AI SDKs（Agent生态大全）
- **仓库**：e2b-dev/awesome-ai-sdks
- **链接**：https://github.com/e2b-dev/awesome-ai-sdks
- **星数**：1,217 | 语言：Markdown
- **核心能力**：AI Agent的SDK/框架/库/工具数据库，覆盖创建/监控/调试/部署自主Agent，含LangChain/LlamaIndex/LLM Ops/AgentOps等分类
- **可借鉴点**：Agent技术选型全景图；监控/调试/部署工具链参考
- **与现有系统关系**：现有ai_hub/AI中心可参考其工具链分类完善AI能力矩阵
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-004 Swarmclaw（自托管多Agent运行时）
- **仓库**：swarmclawai/swarmclaw
- **链接**：https://github.com/swarmclawai/swarmclaw
- **星数**：656 | 语言：TypeScript
- **核心能力**：开源自托管AI Agent运行时，多Agent框架，Agent记忆/MCP工具/调度/委托，23+ LLM提供商（Claude/GPT/Gemini/OpenRouter/Ollama），Claude Code和LangChain替代方案
- **可借鉴点**：
  - **多Agent协作模式**：Agent记忆+委托+调度，可用于采集Agent/分析Agent/报告Agent分工
  - **MCP工具标准化**：23+ LLM提供商统一接入，可参考其Provider抽象
  - **自托管架构**：数据不出本地，符合舆情系统数据安全要求
- **与现有系统关系**：现有ai_hub/ark_llm.py单Provider，可参考其多Provider抽象和Agent记忆
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-005 Autono（ReAct自主Agent框架）
- **仓库**：vortezwohl/Autono
- **链接**：https://github.com/vortezwohl/Autono
- **星数**：212 | 语言：Python
- **核心能力**：ReAct模式高鲁棒性自主Agent框架，支持MCP Agent/多Agent/工具学习，Python原生
- **可借鉴点**：ReAct推理-行动循环的Python实现；工具学习机制
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-006 CrewAI多Agent系统
- **仓库**：akj2018/Multi-AI-Agent-Systems-with-crewAI
- **链接**：https://github.com/akj2018/Multi-AI-Agent-Systems-with-crewAI
- **星数**：166 | 语言：Jupyter Notebook
- **核心能力**：CrewAI多Agent角色协作，自动化复杂业务工作流，含简历定制/网站设计/研究/客服等场景
- **可借鉴点**：角色特定Agent协作模式，可用于舆情系统的采集员/分析师/报告员角色分工
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 三、凭证 / 密钥 / Cookie 管理（Z-Brand-Core 安全域）

### PL-007 Credential Bridge（Python统一密钥库）
- **仓库**：ihassan8/credential-bridge
- **链接**：https://github.com/ihassan8/credential-bridge
- **星数**：0 | 语言：Python
- **核心能力**：统一Python密钥管理库，跨HashiCorp Vault/OS系统keyring/.env文件三种后端
- **可借鉴点**：
  - **多后端统一抽象**：Vault/keyring/.env统一接口，可用于Cookie保险库的多存储后端
  - **Python原生**：与现有系统技术栈一致
- **与现有系统关系**：现有cookie_vault.py支持多平台Cookie，可参考其后端抽象扩展到系统keyring存储
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-008 Vault DB Injector（动态数据库凭证）
- **仓库**：numberly/vault-db-injector
- **链接**：https://github.com/numberly/vault-db-injector
- **星数**：50 | 语言：Go
- **核心能力**：K8s中用HashiCorp Vault自动化数据库凭证管理，凭证注入/续期/吊销
- **可借鉴点**：动态凭证+自动续期+吊销的零长期访问模式，长期可用于数据库凭证管理
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-009 零长期访问数据库凭证
- **仓库**：cyberKyrian/HashiCorp-Vault-Dynamic-DB-Secrets
- **链接**：https://github.com/cyberKyrian/HashiCorp-Vault-Dynamic-DB-Secrets
- **星数**：0 | 语言：HCL
- **核心能力**：Zero Standing Access方案，Vault+PostgreSQL生成即时动态凭证，TTL过期自动吊销，完全消除静态密码
- **可借鉴点**：零长期访问安全模型，长期安全升级方向
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 四、数据管道 / ETL / 编排（Z-Brand-Core 采集域）

### PL-010 生产级金融数据ETL
- **仓库**：SoheilGtex/finance-data-pipelines
- **链接**：https://github.com/SoheilGtex/finance-data-pipelines
- **星数**：11 | 语言：Python
- **核心能力**：生产级Python ETL，CoinGecko采集（无API Key），CLI/config驱动，测试+CI，Docker，输出Parquet+SQLite
- **可借鉴点**：
  - **CLI/config驱动的ETL架构**：可参考其配置化采集任务设计
  - **测试+CI+Docker的生产规范**：现有采集模块缺测试和CI
  - **Parquet列式存储**：大批量历史数据存储优化方向
- **与现有系统关系**：现有collect/采集中心可参考其CLI/config驱动和测试规范
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-011 数据管道全工具链示例
- **仓库**：beyondequations/data-pipeline-examples
- **链接**：https://github.com/beyondequations/data-pipeline-examples
- **星数**：1 | 语言：Python
- **核心能力**：真实可用的ETL/ELT管道，覆盖Airflow/Prefect/NiFi/dbt/Spark/Kafka/Meltano/Airbyte/Beam
- **可借鉴点**：9种编排工具的横向对比和选型参考
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-012 Airflow/Prefect/Dagster三工具横评
- **仓库**：Siri-durga/gpp-data-orchestration
- **链接**：https://github.com/Siri-durga/gpp-data-orchestration
- **星数**：1 | 语言：Python
- **核心能力**：Airflow/Prefect/Dagster三种ETL编排工具的对比分析
- **可借鉴点**：编排工具选型决策矩阵，现有apscheduler可评估是否升级
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 五、PWA / 移动交互（SICI-Core 域）

### PL-013 离线优先数字学习平台
- **仓库**：Kavi-priyan/Offline-first-Digital-learning-Platform-for-organizations
- **链接**：https://github.com/Kavi-priyan/Offline-first-Digital-learning-Platform-for-organizations
- **星数**：2 | 语言：TypeScript
- **核心能力**：React Native+Expo跨平台，SQLite本地存储，离线优先架构，联网自动同步；Web端PWA+IndexedDB(Dexie)离线存储
- **可借鉴点**：
  - **离线优先+自动同步**：SICI移动端可参考其离线缓存和同步机制
  - **IndexedDB via Dexie**：浏览器端结构化离线存储方案
- **与现有系统关系**：SICI-Core现有localStorage（上限500条），可评估升级到IndexedDB支持更大学习资料库
- **状态**：researched
- **owner**：SICI-Core

### PL-014 可安装PWA启动模板
- **仓库**：redfernhqah26515-afk/installable-pwa
- **链接**：https://github.com/redfernhqah26515-afk/installable-pwa
- **星数**：0 | 语言：HTML
- **核心能力**：精致PWA启动模板，离线支持，安装提示就绪，移动优先界面
- **可借鉴点**：PWA manifest和Service Worker的标准配置
- **状态**：observed
- **owner**：SICI-Core

---

## 六、CTH-POMS 专项（v1.0 已覆盖，此处补充深化）

> 完整19条记录见 CTH-POMS_LEARNING_LIBRARY.md，以下为新增/深化项

### PL-015 小红书采集三工具横评（深化）
- **仓库**：lijiajie-git/xiaohongshu-scraper-bakeoff
- **状态升级**：researched → 待shadow run
- **深化点**：横评结论需实际跑一次三个工具对比采集成功率/风控触发率/数据完整度，输出verified级选型建议
- **P0优先级**：直接指导现有rednote_collector.cjs优化

### PL-016 MediaCrawler全网爬虫（待确认）
- **仓库**：NanmiCoder/MediaCrawler（待确认最新地址和状态）
- **状态**：observed（pending-confirmation）
- **深化点**：确认仓库后深入读Cookie池+IP代理池双池架构源码，提取可复用模式

### PL-017 pyresilience弹性工程（深化）
- **仓库**：AhsanSheraz/pyresilience
- **状态升级**：researched → 待shadow run
- **深化点**：实际集成到adapters/base.py，对比现有CircuitBreaker，验证bulkhead/rate limiter模式效果

---

## 七、平台学习汇总统计

| 模块域 | 记录数 | observed | researched | verified | reusable | 归属仓库 |
|--------|--------|----------|------------|----------|----------|----------|
| 三仓库架构/工程控制 | 2 | 1 | 1 | 0 | 0 | DDC |
| AI Agent框架/学习闭环 | 4 | 2 | 2 | 0 | 0 | 共用 |
| 凭证/密钥/Cookie管理 | 3 | 2 | 1 | 0 | 0 | Z-Brand-Core |
| 数据管道/ETL/编排 | 3 | 2 | 1 | 0 | 0 | Z-Brand-Core |
| PWA/移动交互 | 2 | 1 | 1 | 0 | 0 | SICI-Core |
| CTH-POMS专项深化 | 3 | 1 | 0 | 0 | 0 | Z-Brand-Core |
| **平台合计（新增）** | **17** | **9** | **5** | **0** | **0** | — |
| CTH-POMS v1.0（已有） | 19 | 10 | 8 | 1 | 0 | Z-Brand-Core |
| **全平台总计** | **36** | **19** | **13** | **1** | **0** | — |

---

## 八、三仓库学习任务分配

| 仓库 | 学习重点 | P0项 | P1项 |
|------|----------|------|------|
| **Z-Brand-Core** | 采集/AI/安全/数据管道 | PL-015小红书横评shadow run、PL-016 MediaCrawler确认 | PL-004 Swarmclaw多Agent、PL-007 Credential Bridge、PL-010生产级ETL |
| **DDC** | 工程控制/验证/CI | PL-001 Harness Engineering 23阶段落地 | PL-002架构逆向工程 |
| **SICI-Core** | 移动交互/PWA/学习系统 | PL-013离线优先+IndexedDB升级 | PL-014 PWA模板 |

---

## 九、下一步深化计划

- [ ] **P0**：PL-001 Harness Engineering → 输出DDC工程控制面落地方案（AGENTS.md+Repo Doctor+CI六门）
- [ ] **P0**：PL-015 小红书横评 → 实际跑三工具对比，输出verified级选型建议
- [ ] **P1**：PL-004 Swarmclaw → 提取多Agent+MCP+多Provider架构，评估ai_hub升级路径
- [ ] **P1**：PL-007 Credential Bridge → 评估cookie_vault扩展到系统keyring
- [ ] **P1**：PL-013 离线优先 → 评估SICI localStorage升级IndexedDB
- [ ] **P2**：PL-010 生产级ETL → 参考其CLI/config+测试+CI规范完善采集中心
- [ ] 每条记录完成shadow run后升级为verified，积累evidence_ref
