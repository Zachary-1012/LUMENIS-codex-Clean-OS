# ZBC 统一 Intelligence 资料库架构 + 研究资产全量盘点 V1.0

> 落盘时间：2026-09-06
> 来源：用户指令（OSAI 研究资产全部嵌入 ZBC，不得丢失/搞混）
> 核心原则：**一个统一资料库，下面按类别细分子库**；研究资产归 Intelligence 层，生产业务真相归 Core，跨库走 Contract/Adapter，研究结论不得自动变成生产规则（须经 E0-E4 证据门 + Release Gate）

## 一、统一资料库层级架构（答案：一个资料库，下分 7 子库）

```
ZBC Intelligence Library（统一资料库 / intelligence_library）
│
├── 1. 案例库 case_library
│   ├── 外部标杆案例 external_cases（公关话术模版 C-01~C-15，15个舆情公关案例）
│   ├── 内部事件案例 internal_cases（太古汇自身舆情事件，public_opinion_cases.py）
│   └── 工程案例 engineering_cases（ADRH cases/，研发工程能力案例）
│
├── 2. 舆情事件库 opinion_event_library
│   ├── 实时事件（events 表，Core 生产数据，只读引用）
│   └── 历史事件归档（复盘后的事件沉淀为案例 → 回流案例库）
│
├── 3. 语言/语料库 linguistics_library
│   ├── 语言品牌生命 LANGUAGE-BRAND-LIFE（哲学/生命系统/AI Agent/生命科学/语言学叙事/命名研究/MiniMax）
│   ├── CTH 短语库 cth_phrases.py（太古汇专项）
│   ├── ZBMP 短语库 zbmp_phrases.py（品牌智能）
│   └── 叙事智能单元（微小事件→情绪→关系→冲突→场景→记忆→价值→传播→反馈）
│
├── 4. 品牌营销知识库 brand_knowledge_library
│   ├── brand-marketing-knowledge-01~25（全球4A/高奢/重奢/创意引擎/全球趋势/播客）
│   ├── KOS 知识库（research-inbox KOS 系列：baseline/benchmark/collection/rules）
│   └── 行业研究（CDF/海澜之家/全球销售节/品类情绪叙事）
│
├── 5. AI/技术研究库 ai_tech_research_library
│   ├── ai-os-research（白皮书/能力雷达/竞品矩阵/架构2030/体验引擎/AI浏览器/主动智能/安全沙箱/评估框架/路线图 15个）
│   ├── ADRH research R-2026 系列（8个工程研究）
│   └── 模式库 pattern（ai-channel稳定/canonical-wrap SOP/contract-first/data-driven-motion）
│
├── 6. 方法论/话术库 methodology_library
│   ├── 公关回复公式（6场景：服务态度/活动安全/食品安全/内容物料/价格规则/不实信息）
│   ├── ACT 法则（Acknowledge承认→Communicate沟通→Transform转化）
│   ├── 专报触发条件（5个升级条件）
│   └── 创意方法 CREATIVE_METHODS（反模板化创意/圈层符号/文学句库/情感共鸣）
│
└── 7. 证据/评估库 evidence_library
    ├── E0-E4 证据等级（E0未验证线索/E1单源可复核/E2多源一致/E3权威原始研究/E4测试审计验证）
    ├── 知识状态（FACT/VERIFIED/PENDING/CONCEPT/RECOMMENDATION/LEGAL REVIEW/LEGACY/REJECT）
    ├── learning_assets / evidence 表（GGI 研究数据库骨架）
    └── 每条知识字段：source/source_type/evidence_level/status/language/culture/time/version/claim/interpretation/application/risk
```

## 二、研究资产物理位置全量盘点（共 ~259 文件 / ~1.4MB，太古汇运营资料已按用户要求排除）

### 2.1 D:\AI-Development-Research-Hub（99 files / 524 KB）
| 子目录 | 内容 | 归入子库 |
|---|---|---|
| cases/ | 5 工程案例 + content-intelligence + INDEX.json | 1案例库(工程) |
| research/ | R-2026-0002~0008 共8个研究 + content-intelligence | 5 AI/技术研究库 |
| data/evidence | 证据 | 7 证据库 |
| data/experiments | 实验 | 5 技术研究 |
| data/learning/capability_registry.json | 能力注册表 | 5/7 |
| data/research/records.jsonl | 研究记录 | 5 |
| data/shadow | 影子学习 | 5 AI学习单元D |
| CASE-LIBRARY.md / RESEARCH-LEARNING-SCHEMA.md / SHADOW-LEARNING-PROTOCOL.md | 案例库/学习模式/影子学习协议 | 6 方法论 |
| CAPABILITY-REGISTRY.md / PLATFORM_BASELINE.md / THREE-REPOSITORY-VALIDATION.md / GLOBAL-CROSS-REPOSITORY-BASELINE.md | 能力注册/基线/三仓验证 | 5/7 |

### 2.2 D:\Zachary OS AI\03-RESEARCH（39 files / 289 KB）
| 内容 | 归入子库 |
|---|---|
| LANGUAGE-BRAND-LIFE/ 8文件（00哲学/01生命系统/02AI Agent/03生命科学/04语言学叙事/05命名研究/06MiniMax/README） | **3 语言库核心** |
| language-brand-life-intelligence-research.md + LANGUAGE-BRAND-LIFE-INTELLIGENCE-RESEARCH | 3 语言库 |
| BRAND-LIFE-PHILOSOPHY-RESEARCH-BASELINE.md | 3/6 |
| LEARNING-UNITS-REGISTRY.md（A语言/B叙事/C舆情/D AI学习 四单元+E0-E4） | **6/7 总纲** |
| UNIFIED-DATA-INTELLIGENCE-PIPELINE-V1.0.md | 5 |
| P0-AGENT-ORG/ | 5 |

### 2.3 D:\Zachary OS AI\learning-feed（46 files / 243 KB）
| 内容 | 归入子库 |
|---|---|
| brand-marketing-knowledge-01~25（25个品牌营销知识） | **4 品牌营销知识库核心** |
| KOS/行业：CDF-HAILAN、KOS-BASELINE/BENCHMARK/COLLECTION/RULES、global-sales-festivals、category-emotion-narratives | 4 |
| pattern-*（5个工程模式） | 5/6 |
| github-benchmarks-*（4个基准） | 5 |
| COALA-MEMORY-INDEX.md / ZELL-INDEX.md / ZELL-LOOP 系列 | 5/7 |
| seed-sumeru-taiji-mapping（芥子纳须弥太极映射） | 3/6 |
| INDUSTRY-CASE-STUDY-MULTIAGENT / report-convergence-gap | 1/5 |

### 2.4 D:\Zachary OS AI\ai-os-research（20 files / 57 KB）
15个核心研究：00README/01白皮书/02能力雷达/03竞品矩阵/04架构2030/05体验引擎/06研究到代码/07AI浏览器/08主动智能/09安全权限沙箱/10评估框架/11路线图/12不可做清单/13实施契约/14市场情报雷达 → **全部归入 5 AI/技术研究库**

### 2.5 D:\Zachary OS AI\research-inbox（25 files / 128 KB）
KOS 系列 + 审计源 + 自动对账 + 研究收件箱 → 按主题分流到 4 品牌知识库 / 7 证据库

### 2.6 D:\Zachary OS AI\序境（27 files / 149 KB）
- 00-GOVERNANCE 治理 → 7 证据/治理
- 01-PRODUCT（INTELLIGENCE_REGISTRY/CREATIVE_METHODS/RESEARCH/UDIP/CONTRACT 12个）→ 4/5/6
- 08-AUDIT 审计 → 7

### 2.7 D:\Zachary OS AI\research（3 files / 7 KB）
podcast-module → 4 品牌知识库（播客方法论）

### 2.8 ZBC 项目内已有（不重复迁移，做索引映射）
| 现有模块 | 归入子库 |
|---|---|
| public_opinion_cases.py（25KB 太古汇自身案例） | 1 案例库(内部) |
| v4_upgrade/report_center/cth_phrases.py（9KB） | 3 语言库(CTH) |
| v4_upgrade/report_center/zbmp_phrases.py（6.6KB） | 3 语言库(ZBMP) |
| brand_knowledge_base.py + brand_knowledge 表 | 4 品牌知识库 |
| audit/公关话术模版-舆情信息.docx（15案例+6话术+ACT） | 1/6 |
| ai_learning_engine.py / learning_collector.py / learning_persistence.py | 7 学习闭环 |

## 三、整合方式（不搞乱、不复制核心实现）

1. **物理迁移**：把外部研究资产复制到 ZBC `intelligence_library/` 目录（保留原文件，ZBC 内是受治理的副本），原仓库不删不动
2. **元数据索引**：每个文件登记 library_id / sub_library / evidence_level(E0-E4) / status / source_origin / tags，建立 intelligence_library_index
3. **数据库**：新建 intelligence_assets 表（资产登记）+ 复用现有 brand_knowledge / learning_assets，不破坏 62 张现有表
4. **检索 API**：/api/intelligence/library?sub=case|linguistics|brand|ai_tech|methodology|evidence
5. **证据门**：研究资产默认 E0-E3，只有 E4（经测试审计验证）才能进入生产规则；AI 引用研究结论时标注 evidence_level，不直接覆盖规则判断（对齐"AI不能替代核心规则"红线）
6. **双域归属**：语言库分 CTH/ZBMP（phrases 已有），品牌营销知识库主要供 ZBMP，公关案例/话术主要供 CTH，AI/方法论/证据为 Shared

## 四、待执行（P1，UI 改版收口后）
- [ ] 创建 intelligence_library/ 7 子库目录结构
- [ ] 复制 259 文件并生成元数据索引
- [ ] intelligence_assets 表 + 迁移脚本（不破坏现有表）
- [ ] 检索 API + 前端资料库页面（SYSTEM 或独立 Intelligence 入口）
- [ ] 15 个外部公关案例录入 public_opinion_cases（对齐公关话术需求）
- [ ] 证据门 E0-E4 接入 AI 引用链路
- [ ] 与案例对标字段联动（专报自动匹配同类案例）
