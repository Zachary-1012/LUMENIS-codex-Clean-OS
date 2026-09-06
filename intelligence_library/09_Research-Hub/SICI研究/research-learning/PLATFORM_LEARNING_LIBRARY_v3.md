# 三仓库平台学习资料库 v3.0（深化版）

> 覆盖 Z-Brand-Core + DDC + SICI-Core 全平台
> 按 SICI Research Learning Schema + CONTINUOUS-RESEARCH-POLICY 整理
> 外部研究标记 Research Material，不直接成为生产事实
> 生成时间：2026-09-01 | v2.0见 PLATFORM_LEARNING_LIBRARY_v2.md | v1.0 CTH-POMS专项见 CTH-POMS_LEARNING_LIBRARY.md

---

## 一、可观测性 / 监控（新增模块）

### PL-020 Grafana（行业标杆）
- **仓库**：grafana/grafana
- **链接**：https://github.com/grafana/grafana
- **星数**：76,535 | 语言：TypeScript/Go
- **核心能力**：开放可组合可观测性平台，可视化Prometheus/Loki/Elasticsearch/InfluxDB/Postgres等多源指标/日志/追踪
- **可借鉴点**：
  - **多数据源统一面板**：现有system_guardian/HealthMonitor可参考其数据源抽象
  - **告警引擎**：指标阈值告警+通知渠道，可用于采集异常/风控触发告警
  - **Dashboard JSON模型**：面板可导出为JSON版本化管理
- **与现有系统关系**：现有console/控制台有基础健康检查，长期可评估接入Prometheus+Grafana
- **状态**：researched
- **owner**：DDC
- **Research Material**：是

### PL-021 Flask可观测性完整方案（深度研究）
- **仓库**：kunal-1207/monitoring-logging-system
- **链接**：https://github.com/kunal-1207/monitoring-logging-system
- **星数**：0（新项目，架构完整）| 语言：Python
- **核心能力**：Flask应用完整可观测性，Prometheus采集（15秒间隔）+Grafana可视化+FluentBit日志收集+ELK Stack（Elasticsearch+Logstash+Kibana）日志聚合，Docker Compose和K8s双部署
- **可借鉴点**：
  - **指标+日志关联排查**：Grafana看延迟/错误率→Kibana查对应堆栈，现有故障排查可参考此关联模式
  - **自定义应用指标**：请求数/延迟直方图，现有collector_service可暴露采集成功率/延迟指标
  - **Docker Compose一键起监控栈**：现有start_v4.bat可评估增加监控栈启动选项
- **与现有系统关系**：现有HealthMonitor+audit日志是雏形，此方案是生产级可观测性参考
- **状态**：researched（已深读README）
- **owner**：DDC
- **Research Material**：是
- **evidence_ref**：README已读，架构含Prometheus+Grafana+FluentBit+ELK五组件

### PL-022 GitHub仓库监控
- **仓库**：vegasbrianc/github-monitoring
- **链接**：https://github.com/vegasbrianc/github-monitoring
- **星数**：277 | 语言：Docker
- **核心能力**：Docker+Prometheus监控GitHub仓库，提交/Issue/PR指标
- **可借鉴点**：三仓库体系可监控各自的提交频率/Issue状态，作为工程健康度指标
- **状态**：observed
- **owner**：DDC

---

## 二、日志系统（新增模块，深度研究）

### PL-023 yyds-logger（深度研究，高价值）
- **仓库**：yyds-fast/yyds-logger
- **链接**：https://github.com/yyds-fast/yyds-logger
- **星数**：3（新项目，质量极高）| 语言：Python
- **核心能力**：基于Loguru的增强版Python日志，纯零核心依赖
- **深度研究要点**：
  1. **多实例物理隔离**：每个YydsLogger实例拥有独立Core，打破loguru全局单例限制——现有app.py全局logging可参考此模式实现采集/分析/审计日志物理隔离
  2. **JSON结构化输出（serialize）**：文件输出每行JSON，直接对接ELK/Loki/Datadog/CloudWatch——现有日志是纯文本，结构化后可被日志平台采集
  3. **接管标准库logging**：uvicorn/sqlalchemy/requests等三方库日志统一汇入，通过sys._getframe C级帧跳过优化性能——现有waitress/sqlalchemy日志分散，可统一管道
  4. **环境感知（env='prod'/'dev'）**：prod默认关闭diagnose/backtrace（避免日志泄漏变量值+降低开销），使用异步文件写入——现有生产/开发日志无区分
  5. **有界本地队列**：queue_size+block/drop溢出策略+queue_timeout，writer侧延迟格式化（defer_format）降低业务线程日志延迟
  6. **request_id上下文注入（ContextVar）**：同一条业务链路日志自动带ReqID，多线程/asyncio安全传递——现有多任务采集无链路追踪ID
  7. **行级性能分析（@time_it line_by_line=True）**：未装line_profiler时回退sys.settrace，输出每行命中次数/总耗时/占比/瓶颈标记——现有性能排查靠print，可参考此装饰器
  8. **健康检查**：磁盘/内存/日志文件数量大小，get_health()返回logger生命周期/handler数/队列丢弃数
  9. **多进程隔离**：process_isolation=True，不同进程写独立PID文件，Gunicorn/uWSGI pre-fork自动重建
  10. **优雅退出**：SIGTERM/SIGINT信号处理，后台清理线程有界超时排空队列，避免信号上下文做文件I/O
  11. **按sink独立级别**：控制台WARNING+文件DEBUG，生产排障友好
- **与现有系统关系**：现有app.py logging配置基础，可评估替换为yyds-logger或借鉴其多实例隔离+结构化JSON+request_id模式
- **状态**：researched（已深读完整README）
- **owner**：Z-Brand-Core
- **Research Material**：是
- **evidence_ref**：README完整阅读，11个核心特性已提取

### PL-024 structguru（Rust渲染结构化日志）
- **仓库**：kidoz/structguru
- **链接**：https://github.com/kidoz/structguru
- **星数**：1 | 语言：Python/Rust(PyO3)
- **核心能力**：loguru风格API的原生结构化日志，Rust渲染零运行时依赖，支持OpenTelemetry/脱敏
- **可借鉴点**：Rust渲染性能+脱敏（redaction）能力，日志中自动屏蔽Cookie/Token等敏感字段——现有日志可能包含敏感Cookie
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 三、生产部署 / 容器化（新增模块）

### PL-025 生产级Flask部署模板
- **仓库**：yadhnyarpatil5/production-ready-python-deployment
- **链接**：https://github.com/yadhnyarpatil5/production-ready-python-deployment
- **星数**：0 | 语言：Python
- **核心能力**：生产级Flask+Docker+Docker Compose+GitHub Actions CI/CD+环境配置+监控+日志+部署架构
- **可借鉴点**：
  - **Dockerfile最佳实践**：多阶段构建/非root用户/健康检查
  - **docker-compose编排**：app+db+redis+监控服务编排
  - **GitHub Actions CI/CD**：测试→构建→部署流水线
  - **环境配置分离**：dev/staging/prod配置管理
- **与现有系统关系**：现有start_stable.bat走全局python缺包，长期可评估Docker化部署解决依赖问题
- **状态**：researched
- **owner**：DDC

### PL-026 Nginx+Flask+Postgres生产部署
- **仓库**：KjSharma23/docker-nginx-flask-postgres
- **链接**：https://github.com/KjSharma23/docker-nginx-flask-postgres
- **星数**：0 | 语言：Python
- **核心能力**：Nginx反向代理+Flask后端+PostgreSQL，Docker Compose部署AWS EC2
- **可借鉴点**：Nginx反向代理配置（静态资源缓存/Gzip/SSL），现有waitress直接暴露端口，生产环境应加Nginx
- **状态**：observed
- **owner**：DDC

---

## 四、安全扫描 / 密钥检测（新增模块）

### PL-027 Guardian pre-commit安全扫描
- **仓库**：bobbydeveaux/guardian
- **链接**：https://github.com/bobbydeveaux/guardian
- **星数**：1 | 语言：Go
- **核心能力**：快速本地pre-commit安全扫描，OSV CVE漏洞+密钥检测+AI SAST
- **可借鉴点**：
  - **pre-commit钩子**：提交前自动扫描，防止API Key/Cookie/Token泄漏到Git——现有cookie_vault.py含敏感Cookie，需防止误提交
  - **OSV CVE扫描**：依赖漏洞检测，现有requirements.txt可评估定期扫描
  - **AI SAST**：静态应用安全测试，检测SQL注入/XSS等
- **与现有系统关系**：现有git仓库含Cookie文件风险，可评估接入pre-commit密钥扫描
- **状态**：researched
- **owner**：DDC

### PL-028 OWASP SecGuard（注入检测+密钥扫描）
- **仓库**：Tajaddin/owasp-secguard
- **链接**：https://github.com/Tajaddin/owasp-secguard
- **星数**：0 | 语言：Python
- **核心能力**：OWASP注入检测中间件（FastAPI）+密钥扫描，pre-commit钩子阻止提交凭证，宣称100%召回0误报
- **可借鉴点**：OWASP注入检测中间件模式，可适配Flask；pre-commit密钥扫描
- **状态**：observed
- **owner**：DDC

---

## 五、测试框架（新增模块）

### PL-029 Flask API测试框架（65个用例）
- **仓库**：gdw1986/api-test-framework
- **链接**：https://github.com/gdw1986/api-test-framework
- **星数**：0 | 语言：Python
- **核心能力**：Flask API demo+结构化pytest测试框架，65个测试用例
- **可借鉴点**：
  - **pytest fixture组织**：app/client/db fixture分层
  - **测试用例结构**：正向/反向/边界/权限用例分类
  - **现有tests目录19个正式测试**，可参考其用例组织方式扩充到v4模块
- **与现有系统关系**：现有tests/有19个正式测试+18个_开头临时诊断脚本，可参考此框架规范化
- **状态**：researched
- **owner**：DDC

### PL-030 AI Chatbot测试框架（Playwright+Pytest+Flask）
- **仓库**：mahi1512-beep/AI-Chatbot-Testing-Framework
- **链接**：https://github.com/mahi1512-beep/AI-Chatbot-Testing-Framework
- **星数**：0 | 语言：Python
- **核心能力**：Playwright E2E+Pytest API测试+Flask+日志+HTML报告
- **可借鉴点**：Playwright E2E测试前端交互，HTML测试报告——现有前端JS模块对接缺乏E2E测试
- **状态**：observed
- **owner**：DDC

---

## 六、v2.0已有模块深化更新

### PL-001 Harness Engineering（状态升级）
- **状态**：researched → 待输出DDC落地方案
- **深化点**：23阶段中，Phase 0-3（盘点/地图/架构模型/可执行规则）是DDC当前最需落地的P0

### PL-004 Swarmclaw（深度研究，已读完整README 103KB）
- **仓库**：swarmclawai/swarmclaw
- **链接**：https://github.com/swarmclawai/swarmclaw
- **星数**：656 | 语言：TypeScript（Next.js + Electron）
- **核心能力**：开源自托管AI Agent运行时和多Agent框架（运行时平台，非代码库）
- **15个深度研究要点**：
  1. **24+ LLM Provider统一抽象**：Claude Code/Codex/OpenCode/Gemini/Copilot/Cursor/Qwen/Goose CLI + API Provider，ai_hub多Provider抽象参考
  2. **多Agent组织架构**：CEO/CTO/CFO/CMO/COO角色分工，每Agent独立provider/model/tools，heartbeat自主报到——采集/分析/报告Agent分工参考
  3. **持久Agent记忆**：hybrid recall+graph traversal+reflection memory+dream cycles后台consolidate——ai_learning_log参考
  4. **Conversation-to-Skill学习闭环**：对话→Draft Skill→评审→批准入库，不自动提升，用户/Agent作用域隔离——与SICI Shadow Learning Protocol完全契合
  5. **MCP工具标准化**：stdio/SSE/streamable HTTP，per-agent配置，alwaysExpose策略（全量/懒加载/白名单），长连接池复用
  6. **Quality Center质量中心**：Eval Lab（评估+基线+回归门）+Approval Desk+Release Readiness评分+Architecture Health——DDC质量模型直接参考
  7. **任务执行策略**：ordered review/approval/verification stages，409阻止未完成策略——v4权限体系可增加任务审批流
  8. **Handoff Packets交接包**：run/task/chat context-pack，JSON+Markdown双格式，含evidence/timeline/resume commands——三仓库协作参考
  9. **Gateway生命周期**：activate/drain/cordon/restart，路由自动跳过drain网关——collector_service参考
  10. **OpenTelemetry OTLP导出**：chat/model/tool/session全链路追踪——可观测性接入参考
  11. **CREDENTIAL_SECRET加密**：凭证加密存储，多源解析（env→DATA_DIR→legacy→fallback），验证后持久化——cookie_vault加密参考
  12. **并发控制**：maxConcurrency(默认4硬上限16)/joinPolicy(all/quorum/first)/cycle detection——多任务采集并发控制参考
  13. **上下文管理**：实时token meter(70%黄/90%红)+LLM compaction+clear 30秒undo
  14. **调度可靠性**：cron drift repair+tick-time advancement+stable stagger防惊群——apscheduler可靠性参考
  15. **文件队列连接器**：inbox/outbox/archive/error文件夹JSON命令入口，无需消息总线——轻量队列替代Redis参考
- **状态**：researched（深读完整README，15要点提取）
- **owner**：Z-Brand-Core + DDC
- **evidence_ref**：_swarmclaw_readme_full.txt (103KB)

### PL-031 WakaQ（极简Celery替代，消息队列新增）
- **仓库**：wakatime/wakaq
- **链接**：https://github.com/wakatime/wakaq
- **星数**：594 | 语言：Python
- **核心能力**：Redis后端的Python后台任务队列，超极简Celery替代，支持async/分布式/任务调度/worker
- **可借鉴点**：极简API+Redis后端，比Celery轻量，现有apscheduler可评估升级为WakaQ支持分布式任务队列
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-032 Flask API加固+性能优化（缓存/限流新增）
- **仓库**：abq2904/flask-api-hardening-performance-optimization
- **链接**：https://github.com/abq2904/flask-api-hardening-performance-optimization
- **星数**：0 | 语言：Python
- **核心能力**：安全高性能Flask API，高级限流+IP白名单+Redis缓存+Cloudflare WAF集成，面向高流量生产后端
- **可借鉴点**：
  - **Redis缓存模式**：查询结果缓存60秒，更新/删除时清缓存保证一致性——现有舆情查询可参考缓存
  - **高级限流**：按IP/用户/端点分级限流，现有登录限流5次锁30分钟可参考扩展
  - **Cloudflare WAF集成**：公网部署安全加固参考
- **与现有系统关系**：现有系统无缓存层，高频查询（笔记列表/报告）可评估Redis缓存
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-033 CacheLine（Nginx+Redis分层架构）
- **仓库**：Ask99Ayush/CacheLine
- **链接**：https://github.com/Ask99Ayush/CacheLine
- **星数**：0 | 语言：HTML
- **核心能力**：生产式分层架构，Nginx反向代理+Redis缓存+HTTPS+MongoDB，监控就绪部署
- **可借鉴点**：Nginx静态资源缓存+Gzip+SSL终止，Redis应用缓存，分层架构设计——现有waitress直接暴露可参考
- **状态**：observed
- **owner**：DDC

---

## 六-A、AI营销 / 品牌 / 舆情监控（新增模块）

### PL-034 Short Video Factory（AI营销短视频，5212星）
- **仓库**：YILS-LIN/short-video-factory
- **链接**：https://github.com/YILS-LIN/short-video-factory
- **星数**：5,212 | 语言：TypeScript
- **核心能力**：一键生成产品营销与泛内容短视频，AI批量自动剪辑，高颜值跨平台桌面端（Win/Mac/Linux）
- **可借鉴点**：
  - **AI批量内容生产**：产品营销素材→短视频自动剪辑，可用于太古汇15周年/活动宣传内容生产
  - **跨平台桌面端**：Electron架构，与SICI移动控制台形成PC+移动双端
  - **模板化营销**：产品营销模板库，可参考品牌宣传内容模板化
- **与现有系统关系**：现有系统偏监控分析，缺内容生产端，此项目可作为ZBMP品牌营销模块参考
- **状态**：researched
- **owner**：Z-Brand-Core（ZBMP预留）

### PL-035 BrandShield 多Agent危机检测
- **仓库**：RahulNaidu-lab/BrandShield-Crisis-Detection
- **链接**：https://github.com/RahulNaidu-lab/BrandShield-Crisis-Detection
- **星数**：0 | 语言：Python
- **核心能力**：多Agent AI系统实时社媒监控+情感分析+品牌危机早期检测，Planner/Worker/Evaluator三Agent分工，负面情感峰值检测+实时告警，可部署Hugging Face或本地
- **可借鉴点**：
  - **三Agent分工**：Planner规划监控目标→Worker采集分析→Evaluator评估危机等级，可参考现有ai_hub多Agent设计
  - **负面情感峰值检测**：时序情感异常检测算法，现有risk告警可参考增加情感峰值触发
  - **危机分级告警**：Evaluator输出危机等级，不同等级不同通知渠道
- **与现有系统关系**：现有risk_controller有风险打分，缺多Agent危机检测闭环，可参考升级
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-036 AI社交监听平台（6平台28M帖子/天）
- **仓库**：jhondados/ai-social-listening-platform
- **链接**：https://github.com/jhondados/ai-social-listening-platform
- **星数**：0 | 语言：HTML/Python
- **核心能力**：实时品牌情报，6平台（Twitter/IG/Reddit/YouTube/News）28M帖子/天，<3分钟危机告警，BERTimbau情感分析F1=0.94，趋势检测（病毒式传播前发现新兴话题），竞争对比（品牌vs Top5竞品NPS/情感），网红追踪（关键倡导者和批评者识别）
- **可借鉴点**：
  - **<3分钟危机告警SLA**：现有告警链路可参考设定SLA
  - **趋势检测算法**：新兴话题在病毒式传播前发现，现有话题发现可参考
  - **竞争情报**：品牌vs竞品NPS/情感对比，ZBMP多品牌母平台核心功能
  - **网红追踪**：关键倡导者/批评者识别，现有博主关注页可参考升级
- **与现有系统关系**：现有系统有话题发现+风险告警，缺竞争情报+网红追踪，此项目是完整社交监听参考
- **状态**：researched（已深读README）
- **owner**：Z-Brand-Core

### PL-037 PR MCP服务器（公关标准化）
- **仓库**：zavora-ai/mcp-pr
- **链接**：https://github.com/zavora-ai/mcp-pr
- **星数**：1 | 语言：Rust
- **核心能力**：Public Relations MCP服务器，品牌监控/媒体情感分析/危机检测/社交监听/声量对比(Share of Voice)/新闻稿格式化
- **可借鉴点**：
  - **Share of Voice声量对比**：品牌声量占比计算，ZBMP多品牌核心指标
  - **新闻稿格式化**：AI生成标准化新闻稿，品牌宣传内容生产参考
  - **MCP标准化**：公关能力MCP化，与现有adapters MCP方向一致
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-038 PR情报监控（BERT危机检测）
- **仓库**：dhrutiPatil1534/PR_Intelligence_and_Monitoring
- **链接**：https://github.com/dhrutiPatil1534/PR_Intelligence_and_Monitoring
- **星数**：0 | 语言：Python
- **核心能力**：品牌/网红声誉追踪，实时爬虫+NLP，Reddit/Twitter/Instagram/新闻/Wikipedia，每日自动更新，BERT危机检测，结构化CSV输出
- **可借鉴点**：BERT危机检测模型，每日自动更新机制，多源数据聚合
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-039 n8n AI社交监听分诊（轻量方案）
- **仓库**：Abidasharif/n8n-AI-Social-Listening-Triaged
- **链接**：https://github.com/Abidasharif/n8n-AI-Social-Listening-Triaged
- **星数**：0 | 语言：n8n workflow
- **核心能力**：n8n工作流+Gemini AI实时社媒情感分析+分诊，RSS监控品牌提及，分类（Negative/Crisis/Bug Report等），紧急告警Slack，全量记录Google Sheets
- **可借鉴点**：
  - **轻量分诊方案**：无需自建系统，n8n+AI即可实现基础社交监听，可作为现有系统的补充告警通道
  - **分类标签体系**：Negative/Crisis/Bug Report分类，现有笔记分类可参考
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-040 ProductMind（AI产品管理Copilot）
- **仓库**：pradeeps-lite/ProductMind
- **链接**：https://github.com/pradeeps-lite/ProductMind
- **星数**：0 | 语言：TypeScript
- **核心能力**：AI原生产品管理平台，产品发现/客户反馈分析/PRD生成/冲刺规划/路线图创建/产品分析全生命周期
- **可借鉴点**：
  - **客户反馈分析→PRD生成**：现有舆情笔记可作为客户反馈输入，AI生成产品改进PRD
  - **产品分析仪表盘**：舆情数据驱动产品决策，可参考现有报告中心升级
- **状态**：observed
- **owner**：Z-Brand-Core

### PL-041 舆情事件监控AI实操应用框架（综合提炼）
- **来源**：综合PL-035~PL-039 + 现有系统能力
- **AI在舆情事件监控中的实操作用**：
  1. **实时采集层**：AI驱动的话题发现（趋势检测，病毒式传播前预警）+ 多平台统一采集
  2. **情感分析层**：BERT微调领域模型（F1>0.9）+ 规则兜底，负面情感峰值时序检测
  3. **危机检测层**：多Agent分工（Planner规划→Worker采集→Evaluator评级），危机分级（关注/预警/紧急/危机），<3分钟告警SLA
  4. **竞争情报层**：Share of Voice声量对比 + NPS/情感竞品对比 + 网红倡导者/批评者追踪
  5. **内容生产层**：AI新闻稿格式化 + 营销短视频批量生成 + 品牌宣传模板化
  6. **产品反哺层**：舆情客户反馈→AI分析→PRD生成→产品路线图
- **与现有系统对应**：
  - 现有：采集(adapters)→情感(ai_analyzer)→风险(risk_controller)→告警(微信)→报告(报告中心)
  - 缺口：危机分级SLA/竞争情报/网红追踪/内容生产/产品反哺
  - P0补：危机分级+情感峰值检测；P1补：竞争情报+网红追踪；P2补：内容生产+产品反哺
- **状态**：researched
- **owner**：Z-Brand-Core

### PL-015 小红书横评（状态升级）
- **状态**：researched → 待shadow run（P0）
- **深化点**：需实际跑三工具对比采集成功率/风控触发率/数据完整度

---

## 七、全平台学习统计（v3.0）

| 模块域 | 记录数 | observed | researched | verified | 归属 |
|--------|--------|----------|------------|----------|------|
| 三仓库架构/工程控制 | 2 | 1 | 1 | 0 | DDC |
| AI Agent框架 | 4 | 2 | 2 | 0 | 共用 |
| 凭证/密钥/Cookie | 3 | 2 | 1 | 0 | Z-Brand |
| 数据管道/ETL | 3 | 2 | 1 | 0 | Z-Brand |
| PWA/移动交互 | 2 | 1 | 1 | 0 | SICI |
| 可观测性/监控 | 3 | 1 | 2 | 0 | DDC |
| 日志系统 | 2 | 1 | 1 | 0 | Z-Brand |
| 生产部署/容器化 | 2 | 1 | 1 | 0 | DDC |
| 安全扫描/密钥检测 | 2 | 1 | 1 | 0 | DDC |
| 测试框架 | 2 | 1 | 1 | 0 | DDC |
| 消息队列/任务调度 | 1 | 0 | 1 | 0 | Z-Brand |
| 缓存/性能优化 | 2 | 1 | 1 | 0 | Z-Brand+DDC |
| AI营销/品牌/舆情 | 8 | 3 | 5 | 0 | Z-Brand |
| CTH-POMS专项 | 19 | 10 | 8 | 1 | Z-Brand |
| **v3.0合计** | **55** | **27** | **27** | **1** | — |

---

## 八、P0深化任务（按CONTINUOUS-RESEARCH-POLICY）

1. **PL-023 yyds-logger → shadow run**：在隔离环境测试多实例隔离+JSON结构化+request_id，输出是否替换现有logging的评估报告
2. **PL-021 Flask可观测性 → DDC落地方案**：输出Prometheus+Grafana接入现有HealthMonitor的最小方案
3. **PL-027 Guardian → 密钥扫描评估**：评估pre-commit密钥扫描接入，防止Cookie/Token误提交
4. **PL-001 Harness → DDC Phase 0-3落地**：输出三仓库AGENTS.md+架构地图+可执行规则
5. **PL-015 小红书横评 → shadow run**：实际跑三工具对比

---

## 九、Research Material声明

本资料库所有外部项目均为 **Research Material**，用于研究和参考，不直接成为生产事实。任何外部方案接入生产系统前，必须经过：
- shadow run（影子运行，不影响生产）
- Evidence收集（实际测试数据）
- 三方验证（DCC工程治理+Z-Brand业务兼容+SICI移动适配）
- Promotion Candidate评审

NOT_VERIFIED 不得写成 PASS。
