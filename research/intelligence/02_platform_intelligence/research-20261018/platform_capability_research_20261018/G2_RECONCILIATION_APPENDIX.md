# G2 原 17×19 要求与本研究的显式对照

核对时间：2026-10-17 19:49–19:52 UTC。只读恢复文档/源码；没有实采、执行产品代码、改库或改运行环境。

## 1. 原要求是什么

当前恢复规划 `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md:143`：G2 要建立 PLATFORM LIVE CAPABILITY MATRIX，17 类来源×19 字段；引用 RD:648–714。

已实际读取该引用，即 `00-GOVERNANCE/LUMENIS-REAL-DELIVERY-OVERLAY-CURRENT.md:648–714`。原文完整摘录及文件指纹保存在 `evidence/G2_REQUIREMENT_EXCERPT.txt`，不是根据 G2 简述猜测。

17 行原文顺序：

1. 小红书
2. 抖音
3. 微博
4. B站
5. 知乎
6. Instagram
7. Facebook
8. X
9. 微信公众号公开文章 / Sogou WeChat
10. 快手
11. TikTok
12. 视频号
13. RSS
14. Public HTTP
15. Atom
16. Sitemap
17. 当前 main 中其他真实 Adapter

原第17行是开放式动态类别，不是一个固定社媒品牌；17也不是最终产品平台数上限。原19列包含采集、身份/会话、运行、持久化、恢复和持续运行，不应缩写为19个正文抽取字段。

分类原样保留：OPERATING、LIVE_VERIFIED、IMPLEMENTED_LIVE_UNVERIFIED、PARTIAL、NOT_CONFIGURED、PLANNED、BLOCKED、ABSENT。本研究没有足够逐格实际回执来替已有工程验收定级，因此 live_classification 保留 null（未评估），另用知识状态解释证据；没有偷偷新增第九个 G2 分类。既有独立回执须由相应 Owner 按版本回填，不能被本轮未知覆盖。

## 2. 两张矩阵不是同一件事

- 22×14：恢复静态目录的来源/对象/权限/商业使用文档研究。22 混合了社媒、辅助源和技术通道；不能称22个社媒，也不能称其覆盖17×19验收。
- 17×19：原产品 live 能力交付与运行要求。本次仅新增323格逐项交叉索引，所有验收仍 OPEN，不将表格填满当成能力完成。
- 176市场审查行：建议审查维度，既不是用户已经确认的市场名单，也不是能力覆盖数量。

## 3. 原19列逐列映射与缺口

| 原G2列 | 文档矩阵可辅助的字段 | 不能由文档替代的证据 |
|---|---|---|
| Adapter | 路线/目录身份 | 当前版本真实绑定与 callable；文件存在不是能工作 |
| Search | post/history/pagination | 实际查询、多页、排序/时间范围、停止理由 |
| Detail | post/media | 原生详情/长文/ID/截断与不可见情况 |
| Comments | comment/pagination | 根评论与回复正文的真实获取和未完任务 |
| Creator | account/identity | 实际作者能力、字段、身份命名空间和归属 |
| Auth | access | 当前账号/应用/角色/权限有效性 |
| Cookie | access只能解释路线前提 | 是否需要、是否有效、是否获准；不得保存秘密证明 |
| Session | access只能解释路线前提 | 会话所有权、隔离、失效与恢复 |
| Proxy | 无对应文档字段 | 实际需要与批准；开关不等于可用或可规避控制 |
| Provider | route/access | 真实供应方/版本/条款及运行绑定 |
| Live Connectivity | 无 | 当前合法路径现场连通回执；health不能替代采集 |
| Real Result | 无 | 真实对象/查询结果与合法零条原因；fixture不能代替 |
| Evidence | 无 | 原始记录、来源、用途、持久化与读回 |
| Canonical Persistence | 无 | 与原始入库分开的准入/数据库读回/事实采用 |
| Scope | account/license/market_rule | 实际actor/workspace/查询/来源/用途边界 |
| Rate Limit | rate | 实际账号额度、业务码、预算区别、断点续行 |
| Risk | license/export/retention | 实际挑战/权益/安全处理及失败隔离 |
| Recovery | access/retention仅提供限制 | 真中断、恢复、幂等、不丢失/不重复 |
| Continuous Operation | rate/retention仅提供约束 | 真实时间持续运行、刷新/删除/限流/中断；一次成功不够 |

特别保留 Cookie、Session、Proxy、Live Connectivity、Real Result、Evidence、Canonical Persistence、Recovery、Continuous Operation：这些不能被新14字段中的许可或历史说明伪填。

## 4. 第17行动态展开与源码发现

`07_G2_DYNAMIC_OTHER_ADAPTERS.json` 为候选逐列展开，共8类候选/兼容项×19列=152行，仍附属原第17行，不把原17改写为其他数字。

- 22目录中未在前16行逐名列出的6项是 YouTube、Reddit、LinkedIn、GitHub、Google、贴吧。其存在目录不等于均注册了真实可用 adapter。Google/贴吧的配置 adapter_module 为 None，尤其不能由目录名断言已有采集实现。
- `adapters/overture_places.py` 在22目录之外：文本显示它读取本地 Overture Places Parquet 为审核候选，保留上游来源/许可信息，声明不持久化或断言 Canonical。此次未发现该文件内 register_adapter 调用，不能自动算新已注册社媒。作为第17行的源码候选单列，官方数据权益和实际接线未核。
- `xhs_app_topic.py` 是现有XHS兼容 provider 入口，不增加一个社媒品牌；单列防漏查，不重复计平台。
- 其他同目录辅助模块不是因为文件名位于 adapters 就全算平台。静态 AST 清单记录所有类、方法与注册语句，未 import/执行产品代码。
- “当前main”是原要求，本次只有固定恢复包，未证明远端main最新状态，不能把恢复包清单当作最终动态范围。
- Bluesky、Mastodon 仍是报告中的扩展研究候选，未自动加入G2主表或现有22源目录。

## 5. 公众号 / Sogou 原路线没有被官方 API 研究替换

原G2第9行明确公开文章/Sogou。`wechat.py` 静态源码包含公开原文解析、Sogou发现解析、原文时间信号、索引时间不是原发布时间、未知互动数保留 None、挑战识别等。官方公众号 batch publish API 文档不可读，并不代表这条已有公开文章路线不存在，也不能据此删除其验收。

反过来，看到 parse_public_article 或 parse_sogou_discovery 方法，也不证明当前公开路径已获准、连通或返回有效数据。该行须分别验发现、原文、身份、时间与证据持久化；“Sogou发现”和“公众号原文”可在同一行下保留不同provider/来源角色。

## 6. 323格的机器结构与验收边界

每格保留原行号、原文标签、原列名、固定cell_id、研究路线、静态源码定位/指纹、官方来源索引、明确缺失证据和未评估 live 分类。共享文件仅标为候选Owner，不冒称对每个平台已接线；直接方法缺失也不擅断不支持，因为可能继承或委托。

原文“至少所有已有真实实现的平台必须尝试授权 live acceptance”保留为待执行验收义务。它不是当前读文档任务的实采授权，更不能覆盖用户对具体产品修改/运行的限制。下一次具体获准执行时，再由实际版本/权限/运行结果逐格定级，并保留旧证据与变更来源。

本次校验：17原行、19原列、323唯一cell_id，原分类枚举未变；零格被本研究宣称 live pass。既有研究文件仍保留，新附录纠正范围关系，不修改产品中的G2或任何其他原要求。
