# CTH-POMS 学习资料库 v1.0

> 按 SICI Research Learning Schema 整理，每条记录含 source/repository/status/summary。
> 状态流转：observed → researched → shadowed → verified → reviewed → reusable
> 生成时间：2026-08-31 | 学习范围：GitHub 公开仓库 | 不含任何凭证

---

## 一、情感分析 / NLP

### RL-001 vaderSentiment（规则级情感分析）
- **仓库**：cjhutto/vaderSentiment
- **链接**：https://github.com/cjhutto/vaderSentiment
- **星数**：5,056 | 语言：Python
- **核心能力**：词典+规则级情感分析，专为社交媒体优化，无需训练，零依赖
- **可借鉴点**：轻量、快速、适合实时旁路告警；可作为AI不可用时的规则兜底
- **与现有系统关系**：现有 ai_analyzer.py 已有规则情感，可参考VADER的词典构建方式优化中文情感词典
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-002 finBERT（金融领域BERT）
- **仓库**：ProsusAI/finBERT
- **链接**：https://github.com/ProsusAI/finBERT
- **星数**：2,219 | 语言：Jupyter Notebook
- **核心能力**：金融领域微调BERT，金融文本情感三分类（positive/negative/neutral）
- **可借鉴点**：领域微调思路——太古汇商业舆情可基于通用BERT做商业领域微调
- **与现有系统关系**：现有 ark_llm.py 用通用大模型，可参考领域微调提升商业舆情准确率
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-003 中文情感极性分析（词典+机器学习）
- **仓库**：chaoming0625/SentimentPolarityAnalysis
- **链接**：https://github.com/chaoming0625/SentimentPolarityAnalysis
- **星数**：1,267 | 语言：Python
- **核心能力**：基于情感词典、k-NN、Bayes、最大熵、SVM的中文情感极性分析，含中文词典
- **可借鉴点**：中文情感词典可直接复用；多种算法对比可作为系统选型参考
- **与现有系统关系**：现有情感分析偏规则+AI，可补充中文词典提升召回
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-004 PyTorch情感分析教程
- **仓库**：bentrevett/pytorch-sentiment-analysis
- **链接**：https://github.com/bentrevett/pytorch-sentiment-analysis
- **星数**：4,614 | 语言：Jupyter Notebook
- **核心能力**：从RNN/LSTM到CNN/BERT/Transformer的完整情感分析教学，含代码
- **可借鉴点**：模型选型路径清晰，可作为AI学习引擎的训练参考
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 二、社交媒体采集 / 爬虫

### RL-005 Apify MCP Server（数千个现成爬虫）
- **仓库**：apify/apify-mcp-server
- **链接**：https://github.com/apify/apify-mcp-server
- **星数**：5,486 | 语言：TypeScript
- **核心能力**：MCP协议接入Apify Store，数千个现成爬虫（社交媒体/搜索引擎/地图/电商），AI Agent可直接调用
- **可借鉴点**：MCP架构思路——采集能力标准化为可调用工具；Apify的Instagram/TikTok/YouTube爬虫可参考
- **与现有系统关系**：现有 adapters/ 框架类似，可参考Apify的Actor抽象和标准化接口
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-006 多平台社交媒体采集（FastAPI+Vue+AI分析）
- **仓库**：PLA-yi/social-media-scraper
- **链接**：https://github.com/PLA-yi/social-media-scraper
- **星数**：19 | 语言：Python + Vue 3
- **核心能力**：统一Web面板采集抖音/TikTok/Reddit/X/YouTube，FastAPI后端，SSE实时日志，AI聊天分析
- **可借鉴点**：多平台统一采集面板的UI架构；SSE实时日志推送模式；AI分析与采集联动
- **与现有系统关系**：现有 collect/ 采集中心可参考其SSE实时日志和AI联动设计
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-007 社交媒体Profile采集（12平台）
- **仓库**：shaikhsajid1111/social-media-profile-scrapers
- **链接**：https://github.com/shaikhsajid1111/social-media-profile-scrapers
- **星数**：571 | 语言：Python
- **核心能力**：Facebook/Instagram/Medium/Pinterest/Quora/Reddit/TikTok/Twitter等12平台用户数据采集，Selenium+requests
- **可借鉴点**：多平台Profile采集的统一抽象；各平台反爬处理方式
- **与现有系统关系**：现有 cookie_vault.py + human_browser.py 类似，可参考其平台适配层
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-008 微博+中文NLP采集
- **仓库**：julian-chan/social-media-scraper
- **链接**：https://github.com/julian-chan/social-media-scraper
- **星数**：58 | 语言：Python
- **核心能力**：Facebook/Instagram/Weibo/Twitter/LinkedIn采集 + 中文NLP（情感分析、关键词提取）
- **可借鉴点**：微博采集的具体实现；采集后直接接中文NLP的流水线设计
- **与现有系统关系**：现有 weibo_login_manager.py 只有扫码登录，可参考其微博数据采集逻辑
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-009 小红书采集工具横评
- **仓库**：lijiajie-git/xiaohongshu-scraper-bakeoff
- **链接**：https://github.com/lijiajie-git/xiaohongshu-scraper-bakeoff
- **星数**：0 | 语言：Python
- **核心能力**：同账号同格式横评三个小红书采集工具：xiaohongshu-mcp / Spider_XHS / MediaCrawler，含分析结论
- **可借鉴点**：三个工具的优劣势对比；小红书采集的选型决策框架
- **与现有系统关系**：现有 rednote_collector.cjs + xhs_cdp_collector.py，可参考横评结论优化采集策略
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-010 MediaCrawler（全网爬虫，行业标杆）
- **仓库**：NanmiCoder/MediaCrawler（已知行业项目，GitHub搜索未直接返回，记录待确认）
- **链接**：https://github.com/NanmiCoder/MediaCrawler
- **星数**：~10k+ | 语言：Python
- **核心能力**：小红书/抖音/微博/快手/B站/知乎/公众号/贴吧全网爬虫，支持关键词/评论/创作者搜索，IP代理池/Cookie池/手机号登录
- **可借鉴点**：Cookie池+IP代理池的双池架构；多平台统一数据模型；风控降级策略
- **与现有系统关系**：现有 risk_controller.py + cookie_vault.py 可参考其双池架构和风控降级
- **状态**：observed（待确认仓库地址和最新状态）
- **owner**：Z-Brand-Core

---

## 三、权限体系 / RBAC

### RL-011 Flask-RBAC
- **仓库**：shonenada/flask-rbac
- **链接**：https://github.com/shonenada/flask-rbac
- **星数**：233 | 语言：Python
- **核心能力**：Flask的RBAC扩展，角色-权限-资源模型，装饰器权限控制
- **可借鉴点**：RBAC模型的Flask原生实现方式；权限装饰器模式
- **与现有系统关系**：现有 v4_upgrade/auth/ 已自实现三级权限，可参考其角色继承设计
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-012 Flask访问控制（中文文档）
- **仓库**：gsw945/flask-access-control
- **链接**：https://github.com/gsw945/flask-access-control
- **星数**：29 | 语言：Python
- **核心能力**：封装RBAC模型、蓝图和装饰器的Flask访问控制，中文文档
- **可借鉴点**：蓝图级权限控制；权限与路由绑定的实现
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-013 小程序商城后端（完整RBAC+Swagger）
- **仓库**：Allen7D/mini-shop-server
- **链接**：https://github.com/Allen7D/mini-shop-server
- **星数**：832 | 语言：Python
- **核心能力**：Flask+SQLAlchemy的完整后端，含RBAC权限管理、Swagger API文档、RESTful规范
- **可借鉴点**：完整的RBAC表结构设计（用户-角色-权限-资源）；API文档自动生成
- **与现有系统关系**：现有 v4_users/v4_sessions/v4_audit_logs 可参考其更完整的权限表设计
- **状态**：researched
- **owner**：Z-Brand-Core

---

## 四、PDF / 文档解析

### RL-014 PDF解析库横评（10+库对比）
- **仓库**：genieincodebottle/parsemypdf
- **链接**：https://github.com/genieincodebottle/parsemypdf
- **星数**：196 | 语言：Python
- **核心能力**：对比AI方案（docling/claude/openai/gemini/llama-vision/unstructured-io）和传统方案（pdfminer/pymupdf/pdfplumber/pypdf/camelot），含性能对比
- **可借鉴点**：PDF解析的选型决策矩阵；AI解析vs传统解析的适用场景
- **与现有系统关系**：现有 importer/parser.py 用pdfplumber/PyPDF2回退，可参考横评结论优化解析策略
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-015 pdfsink-rs（Rust版，10-50x加速）
- **仓库**：clark-labs-inc/pdfsink-rs
- **链接**：https://github.com/clark-labs-inc/pdfsink-rs
- **星数**：22 | 语言：Rust
- **核心能力**：纯Rust PDF提取库，比pdfplumber快10-50倍，支持文本/词/表格/布局/图片/元数据
- **可借鉴点**：性能优化方向——大批量PDF导入时可考虑Rust子进程加速
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 五、熔断 / 限流 / 弹性工程

### RL-016 pyresilience（Python版Resilience4j）
- **仓库**：AhsanSheraz/pyresilience
- **链接**：https://github.com/AhsanSheraz/pyresilience
- **星数**：73 | 语言：Python
- **核心能力**：统一弹性模式装饰器：retry/circuit breaker/timeout/fallback/bulkhead/rate limiter/cache，零依赖
- **可借鉴点**：装饰器模式的弹性工程实现；bulkhead（舱壁隔离）模式可用于多平台采集隔离
- **与现有系统关系**：现有 adapters/base.py CircuitBreaker 可扩展为完整弹性模式集
- **状态**：researched
- **owner**：Z-Brand-Core

### RL-017 nopanic（零依赖弹性工具包）
- **仓库**：dagdelenemre/nopanic
- **链接**：https://github.com/dagdelenemre/nopanic
- **星数**：3 | 语言：Python
- **核心能力**：retry/circuit breaker/timeout/rate limit/bulkhead/hedging，零依赖，同步+异步
- **可借鉴点**：hedging（对冲请求）模式——超时同时发第二个请求，取先返回的
- **状态**：observed
- **owner**：Z-Brand-Core

### RL-018 tenacity（Python重试标准库）
- **仓库**：jd/tenacity（已知行业项目）
- **链接**：https://github.com/jd/tenacity
- **星数**：~5k+ | 语言：Python
- **核心能力**：Apache Airflow迁出的重试库，支持指数退避、条件重试、异步、装饰器/上下文管理器
- **可借鉴点**：重试策略的标准化实现；指数退避+抖动算法
- **与现有系统关系**：现有 base.py 固定延迟重试，可参考tenacity的指数退避+抖动
- **状态**：observed
- **owner**：Z-Brand-Core

---

## 六、移动UI / PWA

### RL-019 SICI-Core 自身（移动控制台）
- **仓库**：Zachary-1012/SICI-Core
- **链接**：https://github.com/Zachary-1012/SICI-Core
- **星数**：自有 | 语言：HTML/CSS/JS
- **核心能力**：纯前端PWA移动控制台，GPT风格侧边栏，苹果交互（haptic/长按/滑动删除/action sheet），SHA-256认证
- **可借鉴点**：移动端UI组件库；苹果交互模式；PWA离线缓存
- **与现有系统关系**：CTH-POMS手机端可直接参考其UI组件和交互模式
- **状态**：verified（已审计，代码可读）
- **owner**：SICI-Core

---

## 七、学习汇总统计

| 模块 | 记录数 | observed | researched | verified | reusable |
|------|--------|----------|------------|----------|----------|
| 情感分析/NLP | 4 | 3 | 1 | 0 | 0 |
| 社交媒体采集 | 6 | 3 | 3 | 0 | 0 |
| 权限体系/RBAC | 3 | 1 | 2 | 0 | 0 |
| PDF/文档解析 | 2 | 1 | 1 | 0 | 0 |
| 熔断/弹性工程 | 3 | 2 | 1 | 0 | 0 |
| 移动UI/PWA | 1 | 0 | 0 | 1 | 0 |
| **合计** | **19** | **10** | **8** | **1** | **0** |

---

## 八、优先学习建议（按系统需求排序）

1. **P0**：RL-009 小红书采集横评 → 直接指导现有小红书采集策略优化
2. **P0**：RL-010 MediaCrawler → Cookie池+IP代理池双池架构，解决300012风控
3. **P1**：RL-014 PDF解析横评 → 优化外部数据导入模块的解析选型
4. **P1**：RL-016 pyresilience → 扩展采集适配器的弹性工程能力
5. **P1**：RL-003 中文情感词典 → 提升现有情感分析的中文召回
6. **P2**：RL-013 完整RBAC表结构 → 参考优化v4权限体系
7. **P2**：RL-005 Apify MCP → 长期可考虑MCP架构标准化采集能力

---

## 九、下一步学习计划

- [ ] 深入阅读 RL-009 小红书横评结论，输出采集策略优化建议
- [ ] 深入阅读 RL-010 MediaCrawler 源码，提取Cookie池/代理池架构
- [ ] 深入阅读 RL-014 PDF横评，输出导入模块解析选型矩阵
- [ ] 阅读 RL-016 pyresilience 源码，扩展适配器弹性模式
- [ ] 提取 RL-019 SICI移动端UI组件，适配到CTH-POMS手机端
- [ ] 每条学习记录完成shadow run后升级为verified状态
