# PLAT-GAP-20261018：全平台官方证据缺口增补，Bluesky 专项

## 01. 结论、边界与采用决定

研究日期 2026-10-18 UTC。仅公开文档与官方固定源码静态阅读，未进行平台内容实采、登录、权限申请、凭据读取、源码执行或产品修改。本报告补原研究第 7 组明确未读的 Bluesky 合同，不关闭全平台任务。

**采用建议：ADAPT 文档合同与验收设计；DEFER 实际 provider 接入/商业用途批准/运行验收。** Bluesky 从“官方开发页跳转后零正文”提升为“已读官方词典、实现与协议，部分技术条件明确”。不提升为“序境已支持”“匿名全历史可采”或“商用/导出已获准”。

三项关键新证据：
- 固定官方源码已有 searchPostsV2，但有功能门控，且匿名请求带 cursor 会被 Forbidden；首屏公开不等于可完整翻页。
- v1 搜索词典明确 cursor 不保证遍历全部结果，hitsTotal 可舍入/截断。v1 日期预期使用 sortAt，v2 描述 indexed 时间，均不能替换为帖子客户端 createdAt。
- AT Protocol seq 可合法跳号且作用域是 host + endpoint；不能套用本地成果流“整数缺一即丢包”的判据。需以每 DID 的 rev / since / prevData 与提交验证判定同步完整性。

## 02. 原任务保全与去重阅读

复用而不重做：platform_capability_research_20261018 的 REPORT、官方基线、22×14 矩阵、G2 附录及 source_register；original_research_gap_closure_20261018 的 REPORT 与第 7 组缺口；continuation_register_20261018 的 KNOWN_OPEN_ITEMS、研究项目登记；最新 incremental_result_research_20261018 的 01_RESEARCH 及品牌可比研究相关来源/时点段落。

原 G2 17 类来源 × 19 项 live 维度共 323 格完整保留；22 个静态源身份不是产品范围上限。本增补候选 Bluesky 独立 14 合同格，不插入原矩阵伪造既有 adapter，不改变原 live 验收分母。其他平台未闭合同继续沿原报告，包括小红书内容/评论、快手/B站评论正文、知乎/贴吧/视频号通用读取、微信公众号发布/留言正文、Facebook 当前 Pages 合同及实际账号权限、所有平台用途和运行证据。本轮不把它们记为新重验或失败。

## 03. 来源版本和实际阅读范围

- ATProto 官方仓库固定提交 9f66a7e54b030700c03eda0bdbf35ffe756f4cd8，提交时间 2026-10-17T12:15:04Z。完整读取 searchPosts、searchPostsV2、getAuthorFeed、getPostThread、post、images、video、gallery、facet、listRecords 词典；feed/defs 只读 postView、viewerState、feedViewPost、replyRef、threadViewPost、notFound/blocked；subscribeRepos 仅作结构对照。完整读取三个搜索/线程实现文件及 api/util.ts。未读全仓或服务部署配置。
- bsky-docs 固定提交 fd3d7f8bae5b5fb407afd715bc3cc06e1fafc1ee；完整读取 rate-limits.md、api-directory.mdx、firehose.mdx，未运行示例。
- atproto.com/specs/event-stream 与 /specs/sync：保存本次 HTML 与可读文本，完整读取上述两篇协议正文（不包含其外链全部标准）。没有页面明确版本号，不把抓取日称为协议修订日。
- 官方 ToS 2025-08-14：读取正文，采用 §3、§8–10 对内容权利、第三方和无保证的边界；Community Guidelines 2025-09-19：读取正文，采用 §1.6、§4；Privacy 2025-08-14：采用 §5、§8、§11、§13–14；Network Services Privacy 2024-05-22：采用适用范围、共享与第三方处理/个人权利部分。页面通过网页工具读取成功；本地独立下载 403，未绕过或继续重试，不声称拥有这些法律网页的原始字节存档。
- Jetstream 官方仓库固定 f1b41ba424db21e9fb08e32a7e2a2d951946c0ad：完整读取 README，发现当前仓库自称 archive/replay/stream 并将旧版移至 jetstream-legacy。仅确认版本分流；其当前生产协议、保留窗口和服务保障未核，不套用旧 Jetstream 微秒游标说明。

本轮 dev 文档 URL 仍跳转到零可读正文；已通过官方公开仓库的同名文档与固定 lexicon 补技术证据。旧猜测根路径 lexicons/app/bsky 的 404 是路径变化，实际路径为 packages/api/lexicons/app/bsky。下载副本不等逐份已读，逐文件状态见 03_SOURCE_READING_LEDGER.json。

## 04. 搜索、历史和分页合同

BS-01 / v1：q 必需，语法未标准化，推荐 Lucene 不等保证所有 Lucene 操作符。sort 为 latest/top；limit 1–100、默认 25。author/mentions 可 handle→DID；mentions 只匹配富文本 facet。since 包含、until 不包含，预期 sortAt 可能与 createdAt 不同。cursor/hitsTotal 明确不保证可遍历全集。[固定词典](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/feed/searchPosts.json)

BS-02 / v2：query 或至少一个 filter，sort recent/top，limit 默认 25 最大 100；新增数组过滤、replyParentUri/threadRootUri、语言分析提示和 allTime。allTime 是全索引而非全世界全部历史；索引时间边界与 estimated hitsTotal 必须带原语义。实现默认 top，门控未开时报错；匿名带 cursor 拒绝，首请求内部最多一次填页。源码中的临时说明不能证明线上所有 host 都已同版，不能推断 v1 所有部署均相同拒绝。[词典](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/feed/searchPostsV2.json)；[实现](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/bsky/src/api/app/bsky/feed/searchPostsV2.ts)

BS-03 / 完备性：源码在 hydrate 后按 block/标签/排序过滤；fillPage 有有界补页逻辑，并不保证每页返回 limit 条。短页不能自动判采完。必须记录 endpoint/version、sort、查询、时间字段、输入/输出 cursor、可见数量、过滤未知、停止理由。不可改日期、切身份或换 provider 绕过 Forbidden/限流。getAuthorFeed 含帖子与转帖，默认 limit 50、最大 100；固定 repo+collection 的 listRecords 是另一对象范围，不自动覆盖所有回复者、转帖者或已删除历史。[v1 实现](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/bsky/src/api/app/bsky/feed/searchPosts.ts)；[listRecords](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/lexicons/com/atproto/repo/listRecords.json)

## 05. 正文、评论、身份与媒体

BS-04：帖子 text 可为空而含 embed；createdAt 是客户端声明时间。post URI + CID、观察时间、indexedAt 分开保存；DID 与 handle 解析身份不能与跨平台真实主体直接等同。reply 保存 root/parent 强引用。facet 是 UTF-8 字节半开区间，不能当 Dart/JS UTF-16 或 Python codepoint 偏移。[post](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/feed/post.json)；[facet](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/richtext/facet.json)

BS-05：getPostThread 无需 auth，但认证改变过滤/元数据；depth 默认 6、parentHeight 默认 80、词典最大 1000，不代表能取 1000 层或全部宽度。实现还受服务器 maxThreadDepth/bigThreadDepth 配置约束。没有通用 cursor 参数；blocked/notFound 是结构或业务错误，不是空评论。replyCount 不可当已发现回复全集的真分母。[线程词典](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/feed/getPostThread.json)；[线程实现](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/bsky/src/api/app/bsky/feed/getPostThread.ts)

BS-06：images 类型最多 4 张，每个 blob 上限 2 MB；gallery 是不同 union 类型，schema 上限 20，当前作者 UI 建议软上限 10，不能将“Bluesky 最多四图”写死。fullsize 未保证原始 blob；video view 为 cid/playlist、可选 thumbnail/alt，并非返回原始 mp4；record 视频 schema 上限 300 MB 不能等同某 host 实际上传/下载限额。媒体字段可读不证明 OCR/ASR、编辑、训练或再分发许可。[images](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/embed/images.json)；[gallery](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/embed/gallery.json)；[video](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/embed/video.json)

BS-07：reply/repost/like/quote/bookmark 等计数是可选字段；缺失保持 UNKNOWN，不补零，不冒充历史时间序列或跨平台同义指标。viewerState 只有认证请求才有有意义的内容。来源身份、可见过滤、当前累计计数与历史发布分别记录。[feed defs](https://github.com/bluesky-social/atproto/blob/9f66a7e54b030700c03eda0bdbf35ffe756f4cd8/packages/api/lexicons/app/bsky/feed/defs.json)

## 06. 准入、速率、用途与删除

BS-08：公开 AppView 推荐 public.api.bsky.app，有缓存；认证 app 请求通常走用户 PDS。并非所有 lexicon 在所有 host 匿名可用。PDS 文档 3000 次/5 分钟按 IP，不得外推到 AppView；AppView 仅描述较宽松限额，未给可采用的固定数字。Relay 的新 PDS 入口限额不是下游采集客户端消费速率。[主机](https://github.com/bluesky-social/bsky-docs/blob/fd3d7f8bae5b5fb407afd715bc3cc06e1fafc1ee/docs/advanced-guides/api-directory.mdx)；[速率](https://github.com/bluesky-social/bsky-docs/blob/fd3d7f8bae5b5fb407afd715bc3cc06e1fafc1ee/docs/advanced-guides/rate-limits.md)

BS-09：ToS 保留用户内容所有权；授给 Bluesky 的有限许可不是授给序境的普遍再许可。条款指出其他 Developer Application 有独立条款，网络删除无法强制所有第三方。准则要求尊重隐私/版权，不规避 API、安全、限流或执法。官方隐私说明公开帖子及分布式共享，不给序境一个通用商用/训练/导出授权。因此商业分析、原文保留、媒体重用、推理、训练、客户导出逐用途仍待资格与权利审查，也不能反向写成官方全面禁止商业使用。[ToS](https://bsky.social/about/support/tos)；[Guidelines](https://bsky.social/about/support/community-guidelines)；[Privacy](https://bsky.social/about/support/privacy-policy)；[Network Privacy](https://bsky.social/about/support/network-services-privacy-policy)

## 07. 增量与恢复：协议结论和产品推论分开

BS-10 协议：event-stream 的 cursor 有回放窗口，不是回到流创世；host+NSID 决定序号作用域。seq 可以跳号；无 cursor 从当前开始，太旧有 info 并从最老保留点继续，未来 cursor 为错误。应使用最后成功处理的状态，不能只取收到的最大值。窗口长度由具体服务决定。错误/非法 framing 有明确断连处理。[Event Stream](https://atproto.com/specs/event-stream)

BS-11 协议：同步需每 DID 的仓库状态、签名验证及 rev/since/prevData 一致性；#sync 不含全部仓库内容，断链需重同步。账号停用/删除要影响下游可用性。完整 repo 是当前记录快照，不恢复已删除历史。旧 bsky.network 示例缺 prevData，官方指南转向 Sync 1.1 端点；不能用同名 firehose 推断协议能力相同。[Sync](https://atproto.com/specs/sync)；[Firehose guide](https://github.com/bluesky-social/bsky-docs/blob/fd3d7f8bae5b5fb407afd715bc3cc06e1fafc1ee/docs/advanced-guides/firehose.mdx)

产品适配推论：沿 C1 Collector 的 provider 与 PlatformManifest、同一 Browser/PlatformSession；Gateway 的用户/AI 调用同一能力合同、Actor/scope 与错误。C6 原 Task 保存 host/endpoint、attempt、checkpoint 身份；C5 Source/Evidence 保存 URI/CID/版本/时间/许可/删除状态，依赖成果标记失效而不是偷偷重写旧结论；C2 仅消费已获准证据；F 同样显示 partial/blocked/unknown。不得另起采集平台、复制事实库、为 AI 放宽匿名翻页规则。

恢复状态须区分 RECEIVED、VALIDATED、APPLIED、DURABLE；本地任务有连续语义时可核连续前缀，但 ATProto 不能按 seq+1 判断缺失。按来源合同保留安全去重键/版本，不重置未来 cursor、吞太旧警告或跨 host 复用 cursor。有限重试与退避、大小/解码预算及未知主机 SSRF 防护走现 Owner。以上均为建议，不声称已经实现或授权修改。

## 08. 代价、收益与采用边界

公开 AppView 查询成本低、适合有界发现，但不能承诺全历史和全集；repo/relay 可提供版本验证与删除同步，代价是状态、带宽、签名/索引验证和重同步运维。Jetstream 当前/legacy 需独立定版后再选，不凭老教程判可替代完整验证。没有本轮请求量、时延或费用实测，不能给虚构 ROI。建议先复用现 provider 接口、静态合同和失败表达，再由具体任务决定是否申请实际验收；不将全网镜像设为独立研究/编辑功能前置。

## 09. 验收与剩余缺口

04_ACCEPTANCE_CASES.json 给出 12 项可执行方案，全部 NOT_RUN。涵盖 v1/v2/host 绑定、分页拒绝、日期语义、非空媒体帖/Unicode、线程深度/屏蔽、计数缺失、速率、恢复跳号/过期/跨主机、删除与双入口同能力。应使用获准固定输入和官方/自有测试夹具；不得为制造 429 压测公共服务，不为匿名限制切身份或切时段规避。

本轮闭合的是具体官方技术章节与固定源码读取，不是“完整所有商业合同”。仍待：实际部署版本/feature、provider 精确速率和回放窗口、合法任务语料和字段覆盖、搜索索引/删失完备性、评论宽度、当前 Jetstream 协议、具体用途/市场/保留/导出资格、四端运行与用户/AI 同能力实测。其他平台及 G2 原未闭项目不变。下一步研究可补当前 Jetstream 官方生产协议；生产采集或产品改动须有对应具体授权。
