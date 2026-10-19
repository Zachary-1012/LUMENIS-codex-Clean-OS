# G108/G109：检索、长期记忆与原件引用深研

2026-10-18。Owner：阿康1，C2 Agent/Memory/Gateway，C1原始来源/准入，C5 Evidence/Library/评价，C6权限/Task checkpoint，F引用和状态。关联G108/G109/G135/G153/G189及U18；不新增记忆数据库或平行权限服务。

## 与已有报告的增量

已读owned_ai的REPORT相关检索/语言/学习章节与APPENDIX_PRODUCT_UNDERSTANDING全文，及creative_quality的范围、事实/文化、Owner和评价协议。原建议已有能力知识投影、同Owner双入口、六轮截断风险与12语任务矩阵。本报告补：固定main源码具体检索边界、真实FTS5失效反例、可执行记忆失效传播逻辑、引用selector与歧义处理。15个自写隔离断言全部真实通过；不导入产品模块、不接生产数据库、不调用模型。

## 固定源码发现及不能外推的部分

main4dab98ed6357133da9307de846180ed4f7bba5f5：
- agent_memory/semantic.py::search_assets先取FACT/VERIFIED且ADMITTED、updated_at最新500，再按词项/标签计分。它有准入过滤，但不是完整Hybrid，也不能证明全资料召回。早于500的精确ID会不可见。长度<2词项被丢弃，单汉字查询可进入无tokens分支并返回近期候选；不能说这等于匹配该字。
- agent_memory/base.py::_query只在过滤键存在于metadata时比较，否则不拒绝缺字段。这个低层函数本身不能充当actor/workspace严格隔离证明。调用者、DB隔离和权限链可能另有保护，本次未证明端到端跨用户泄露。
- BaseMemory.query先调用有limit的_query，再排过期项，可能返回空但更后面存在有效记录。取候选数、过滤顺序和覆盖状态需明确，不能只增大limit掩盖。
- BaseMemory默认_store/_retrieve/_forget为内存字典；WorkingMemory另有Task步骤持久化。不能因默认内存实现就概括所有记忆都不持久，也不能以WorkingMemory持久化推断语义索引/情节摘要自动完整同步。
- semantic.get_knowledge_context只取title/摘要前200字符/tags；缺否定条件、来源ID/精确版本等可能影响解释。实际业务caller是否另补需后续验。

以上为静态观察，结构镜像反例并非产品函数运行验收。源码hash/函数行段在本批总manifest登记。

## 原始资料与采用裁决

1. Anthropic Contextual Retrieval官方工程文章实际说明精确词项与语义候选组合、去重及块语境补充。其报告检索收益只属于原实验；不复制为序境收益承诺。采用“原chunk与派生语境分列”，源/时期/实体不得由生成语境补成新事实。https://www.anthropic.com/engineering/contextual-retrieval
2. SQLite FTS5官方external-content合同要求索引与原内容自行保持一致，新增trigger不自动回填历史。本文在内存SQLite真实重现：源表有记录但MATCH为0；更新源文本未更索引时旧词能命中新文本；rebuild后旧词消失。采用版本/失效与一致性验收；不建议本轮直接重建产品库。https://www.sqlite.org/fts5.html#external_content_tables
3. W3C固定2017 Web Annotation Recommendation的TextQuote支持exact及上下文，TextPosition依赖具体文本位置且易被编辑破坏，State可标识表示。采用位置+精确片段/邻近语境+原件hash/版本的组合；它不证明原文真实、引用有权或主张成立。https://www.w3.org/TR/2017/REC-annotation-model-20170223/#selectors

本轮读上述相关正文，不声称阅读全文所有章节。标准模型是设计参考，不自动要求序境改成JSON-LD或新增服务。

## 可采用的完整检索顺序

A. 由真实Owner先限定actor/workspace/项目/用途、来源准入、失效/撤回与时间范围；未填scope不是通配符。需要检索的“无AI普通关键词/精确ID”持续可用。
B. 在合格集合中分别取词项/向量候选，记录候选上限、索引版本和遗漏；再去重/重排。无向量能力时明确关键词路径，不能改名Hybrid。精确ID应有不依赖近期500预截断的定位路径。
C. 当前证据重读：entity/时期/单位/版本/原件可定位/用途仍有效。命中摘要不能替代原件，命中产品说明不能替代实时capability descriptor。
D. 组装上下文保留最新用户限制、任务/Artifact版本、未完项、已提交效果回执；可选检索片段受预算裁剪。禁止固定字符截断后仍宣称完整上下文；必须给截断账与需重读项。
E. 证据不足时有界重写/检索，保存次数/结束原因。交付支持部分和缺口；不以模型自信填事实、不为了找答案放宽scope或复活旧Provider。

此顺序为产品适配提案；不增加权限，也不承诺RAG自动完成推理或事实核验。

## 长期学习与更正/忘记传播

现有三层记忆、Shared Learning和Task checkpoint继续复用。建议把同一事实的原件→chunk→摘要→embedding→已生成答案建立版本依赖，而非只删原key。自写图实验中source失效递归到四类派生物，未关联资料保留。实际采用应区分：
- 撤权：立即禁止新的检索/使用；派生缓存失效，未获准不能重读原件。
- 更正：保留旧审计事实并建立superseded关系，新回答读取当前版本；历史已发布成果显示影响，不静默改历史。
- 用户忘记：针对被授权可忘记的偏好/任务记忆停止再检索与再派生，依据既有保留策略处理审计；不承诺删除模型权重中的信息。
- 能力升级：缓存descriptor hash变更后重读Owner，旧模型记忆不得授权旧接口。
- 训练：记忆保存、检索、用户纠错、已可用反馈都不自动授予MODEL_TRAIN。语料谱系/用途/保留集/晋升/回滚仍沿原学习闭环。

删除主记录但保留摘要/embedding、后台旧任务在失效后重新写回、复制到答案后不追踪依赖，是需逐一验的失败模式。逻辑实验说明必要性，不证明当前全产品已出现这些失效。

## 引用与定位判定

确定定位需同一Source表示版本和明确单位；字符、UTF16、UTF8字节、规范化视图、OCR页/框与ASR毫秒不互换。重复quote多处命中时不得自动取第一处；位置不符或hash变了，先在正确版本查回，不能悄悄指向新页面类似句。

允许状态：EXACT_VERSION_MATCH、REANCHORED_WITH_REVIEW、AMBIGUOUS、SOURCE_CHANGED、SOURCE_UNAVAILABLE、RIGHTS_BLOCKED。它们是本报告建议的语义状态，不冒充已实现枚举。原文真实、事实支持和许可各自另验。需要受限全文时不把整篇复制进quote字段，引用长度/展示用途沿原SourceUse。

## 真实隔离实验与后续验收

memory_reference_lab/run.py及results.json包含15断言：最新500截断、单字符变空、缺scope宽松过滤、过期后过滤饥饿、FTS5空/旧索引与修复、传递失效、记忆不扩权限/训练、旧descriptor拒绝、重复quote、编辑后旧offset、截断丢禁令、语言集合不等与高词汇重合否定反转。SQLite数据库仅:memory:，脚本不接外网；后四项同时支持22多语研究。

真正待运行：产品真实caller/权限全链与多租户；重启读回；源撤权→索引/摘要/缓存/在途任务；索引更新原子性/并发；真实query集Recall@k/MRR/NDCG与引用准确率；长上下文token计量；四端定位；审批/审计/忘记策略。不能把15实验PASS写成上述产品PASS。
