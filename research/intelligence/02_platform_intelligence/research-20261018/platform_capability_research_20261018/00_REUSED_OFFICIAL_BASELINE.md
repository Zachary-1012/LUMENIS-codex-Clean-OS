# LUMENIS 全平台官方采集条件矩阵

核验日期：2026-10-17（UTC）。方法：读取平台官方公开文档、官方维护的接口集合和标准正文；只读检查产品静态配置。未登录平台、申请权限、创建凭证、接受协议、调用带凭证的数据接口或进行内容实采；未修改产品代码、数据库或运行环境。

## 1. 结论及口径

1. 当前静态目录是 **16 个社媒品牌**，即此前 15 个主流品牌加贴吧；Google、GitHub 是 2 个辅助源，public_http、web_rss、web_atom、sitemap 是 4 个通用 Web 源，合计 22 个源身份。不能把 Web 通道数量算成社媒品牌数。
2. “已有 adapter”“search=True”“只读会话”“无 cookie”“公开可见”均不构成平台 API、商业使用、跨账号获取、正文持久保存或导出许可。**本次没有任何平台被验收为实际已可采。**
3. 多数已核官方接口适用于自有或用户明确授权账号，不适用于任意品牌全平台历史舆情。X、YouTube 的公开数据查询范围较宽，但有分页、时间、项目额度、使用/保存规则；也不保证完整历史语料。
4. TikTok Research API 明确排除商业用户；Reddit 商业用途需另行协议；LinkedIn 通用 API 条款的存储、跨源混合限制须单独审查。YouTube 已有经申请和审计的分析用途例外，不能笼统写成“不能做情绪分析”，也不能默认 LUMENIS 已获此许可。
5. 匿名既有采集 的已知平台个案仅为小红书。“前期多、后期少”的原因尚未核实，不能用其他平台的 100/500/1000 等数值解释小红书，也不能据此认定平台硬上限。

### 证据来源与状态定义

静态配置来源：`lumenis_working_20261017/source/lumenis/system/collector/adapters/config.py`，本次仅文本读取，未 import 或执行。其文件说明已明确：注册 adapter 不代表凭证、平台权限或 live provider 配置完成。小红书的 ACTIVE、其他平台的 PARTIAL/PLANNED 均为目录/实现状态，不能提升为授权或实采状态。

- **条件适用**：官方已存在与某个限定目标相符的读取路线；只有满足列出的账号、产品、权限、用途条件才可进一步验证。
- **不适用**：该条具体路线不满足目标，例如身份登录 API 获取笔记、研究专用权限用于商业产品。不是断言该平台永远无任何其他合作接口。
- **待核**：官方正文、当前版本、具体产品合同、实际账号权限、额度或验证结果缺一项。未知不记为“支持”，也不记为“没有”。
- **运行状态**：以下所有路线均为“未验证”。技术参数是文档参数，不是 LUMENIS 账户的实际额度。

## 2. 总览矩阵

| 社媒 | 已核官方路线/授权对象 | 任意第三方品牌发现与历史 | 评论与回复 | 本次判定及验收入口 |
|---|---|---|---|---|
| 小红书 | 小红书账号授权；商业平台另有特定能力 | basic_info 不含笔记搜索；全量内容接口待核 | 通用正文/楼中楼合同待核 | 登录路线不适用内容采集；内容来源需提供产品、合同、scope、接口证据 |
| 抖音 | 开放平台小程序，授权用户公开作品 | 授权作品、热点能力各有范围；不能推全站 | 已核 ma.item.comment 根评论及回复接口 | 自有/授权作品条件适用；商业分析用途另审 |
| 快手 | user_video_info 授权用户作品列表/详情 | 任意关键词搜索待核 | 已核仅评论计数，评论正文待核 | 授权作品信息条件适用；评论能力不应置为已验收 |
| 微博 | 官方 CLI/开放 API，按命令、套餐、权限 | limited 搜索等存在，窗口和历史覆盖待核 | comments/show/all 等存在，层级合同待核 | 条件适用；须冻结当前命令目录和账号套餐 |
| B站 | 创作者授权的开放平台账号/稿件数据 | 通用全站搜索接口授权待核 | 稿件评论计数不等于评论正文接口 | 自有创作者数据条件适用；广泛内容与评论待核 |
| 知乎 | 机构号/广告产品存在；通用内容合同未核实 | 待核 | 待核 | 不以网页可访问或内部接口作为官方开放证明 |
| 贴吧 | 历史官方内容合作页 | 特定吧/精品内容合作；当前是否可申请待核 | 历史页列回复数，未证明全文/楼中楼 | 当前商业读取路线待核；历史页不是当前凭证 |
| Instagram | 专业账号；Instagram Login 或 Facebook Login | 消费者账号不支持；部分 hashtag/business discovery 有限 | 专业账号自有 media 的评论管理 | 授权专业账号条件适用；全站任意用户不适用 |
| Facebook | Pages API 候选；研究专用 Content Library | Page 非本账号读取需具体 feature/权限；研究路线非通用商业入口 | 本次未取得当前完整官方参数正文 | Pages 路线待核；需账号、Graph 版本与 entitlement |
| X | v2 recent / full-archive search | recent 7 天；全档案需对应付费/企业访问 | 回复也是 Post，通过会话/引用关系组装 | 公开搜索条件适用；导出有明显限制 |
| 微信公众号 | 自有/授权号发布记录、留言管理候选 | 未核到官方全号关键词历史搜索合同 | 旧/新文档本次不可读，具体层级待核 | 自有账号路线待核；原文链接不等于全号检索权 |
| 视频号 | 未核到任意视频/关键词/评论的官方读取合同 | 待核 | 待核 | 店铺、电商、直播营销接口不能替代社媒内容接口 |
| YouTube | Data API 公共读取，私有/管理项另需 OAuth | 关键词搜索、日期过滤；结果仍可能不完整 | 顶层线程与独立 replies 分页 | 技术条件适用；情绪/评分与保存需用途批准和规则 |
| TikTok | Display API、Research API、Portability 分开 | Research 商业不适用；Display 仅授权用户作品 | Research 提供评论树入口但商业不适用 | 自有展示条件适用；商业广泛舆情路线待核 |
| Reddit | 经批准 OAuth Data API；商业另签协议 | search/listing 范围与索引不保证全历史 | 评论树与 morechildren，必须展开 | 商业合同未核前待核；不能按免费额度默认商用 |
| LinkedIn | 获准 Community Management，账号角色与 endpoint scope | 非通用全网关键词/任意成员资料路线 | 授权 posts/comments/replies，scope 需逐接口区分 | 自有/授权组织条件适用；保存、混合、导出另审 |

## 3. 分平台可实现与可验收条件

### 3.1 小红书（xhs / xiaohongshu）

- **官方边界**：账号授权快速入门当前只列 `basic_info`。API Reference 是授权、token/refresh、基础信息、撤销等身份功能，不是笔记搜索、详情或评论库。商业开放平台另有达人报价/合作内容能力，必须逐产品、scope、合作对象确认，不能把某个商业接口扩大为所有用户的全部笔记。来源：[账号快速入门](https://openaccount.xiaohongshu.com/docs/quick-start)、[账号 API Reference](https://openaccount.xiaohongshu.com/docs/api-reference)、[商业平台能力文档](https://ad-market.xiaohongshu.com/docs-center?articleId=3196&bizType=944)。
- **窗口/游标/层级**：未取得可覆盖 匿名既有采集 个案的官方笔记内容 API 契约。因此历史窗口、排序、分页 cursor、根评论/楼中楼、推荐截断、删除可见性全部待核；不能写“最多 N 条”“只能采近 N 天”。
- **认证/限流**：账号平台按接口和 app_id 限流，但内容 API 的规则不能从身份 API 外推；token 有过期、scope 和应用匹配要求。应保留平台业务码、request/log ID、刷新失败和授权撤销状态。[账号 FAQ](https://openaccount.xiaohongshu.com/docs/faq)
- **导出/验收**：要求提供实际内容提供方、官方合作产品/合同、获批用途、字段、保存期、导出受众及删除规则。只读验收应核到同一笔记的详情、顶层分页、至少一个多回复线程及终止理由。若来源是网页会话，必须独立审查其许可和实际接口行为，不标成官方 API 已接通。

### 3.2 抖音（douyin）

- **授权对象**：小程序申请 `ma.item.comment` 能力并取得用户授权，可读授权用户公开视频的评论；不能由该能力推导出任意账号搜索/评论。`tt.showDouyinOpenAuth`、scope 获批、用户同意是不同门槛。[能力说明](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/introduction/capabilities)、[授权说明](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/api/open-interface/authorization/tt-show-douyin-open-auth/)
- **分页/层级**：`GET /api/apps/v1/item/list_comment/` 根评论，`count=1..50`，首个 cursor=0，继续使用返回 cursor/has_more；有 `comment_id`、`create_time`、`reply_comment_total`。`GET /api/apps/v1/item/list_comment_reply/` 对 item_id+comment_id 另分页；支持推荐、时间倒序/正序相关排序。回复数不替代回复内容队列。[根评论](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/video-review-data/comment-list)、[回复](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/video-review-data/comment-reply-list)
- **窗口/限流**：另一项 `ma.item.data_bc` 视频统计有“近30天创建作品”条件，不能把它套到评论正文接口。每条 capability 的限额与 err_no/extra.error_code、log_id 要分别处理；数值额度本次未核。[授权统计接口](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/video-id-convert/user-recent-video-data/get-comment-bc)
- **用途/验收**：某些用户互动统计能力明确限制对外销售数据服务和平台统计分析，此限制至少适用于该能力；LUMENIS 使用时需核目标能力的独立条款。验收：一个获授权账号、一个有多页根评论和回复的公开视频；证明用户撤权与能力未开通分别返回权限失败，不吞成“0条”。[互动统计能力限制](https://developer.open-douyin.com/capacity-center-page/capacity-detail/7180284622729658424)

### 3.3 快手（kuaishou）

- **官方路线**：`user_video_info` + 用户 access_token/app_id；`GET /openapi/photo/list` 读取授权用户作品，`/openapi/photo/info` 读取作品信息。列表默认20、最大200；首轮不传 cursor，后续按文档使用上轮最小 create_time 对应的 photo_id。详情的 comment_count 是计数，不能证明有评论正文/回复接口。[官方查询视频文档](https://open.kuaishou.com/platformDocs/openAbility/contentManagement/searchForVideos.html)
- **范围/窗口**：通用关键词搜索、跨账号全历史、明确起止时间过滤、正文评论与楼中楼，均待取得当前官方接口证据。作品 count 接口出现 public/private/friend/all 分类，不表示调用者能读其他账号私密内容。
- **限流/认证**：本次未核 read 端点日限额。发布/上传文档出现的用户/应用写入限额不得套到读取。分别记录 token/scope 失败、120001 不存在等业务错误、频控和空列表。
- **导出/验收**：先核应用审核、scope、用户授权、用途与存储合同；用超过一页的获授权作品验证顺序、cursor 与重叠去重。评论正文未证实前在结果中明确“仅计数”，不造空评论集。

### 3.4 微博（weibo）

- **官方路线**：当前官方 CLI quickstart 提供命令目录/单命令参数与套餐查询；须固定 `catalog_version` 和命令的当前权限。官方示例包含 `search/statuses/limited`、`statuses/user_timeline/biz`、`comments/to_me/biz`、`comments/show/all`。名称的 limited/all/biz 不是完整性保证。[Quickstart](https://open.weibo.com/cli/quickstart)、[搜索示例](https://open.weibo.com/cli/skills/conversion-desk)、[评论示例](https://open.weibo.com/cli/skills/community-desk)
- **分页/窗口/全文**：官方提醒列表不是冻结快照、total_number 不等于最终可见唯一条数；按 idstr 去重，不混用 page/cursor/max_time。长文参数要看命令支持，is_long_text 本身不保证已返回全文。搜索日期范围、最大历史深度、子评论是否独立接口仍需冻结后的具体命令文档。
- **认证/额度**：开发者验证、试用/付费权限与白名单分层；试用通常7天且每个读接口有低次数限制，不能当作生产额度。实际 endpoint 套餐/扣费/限流优先。旧 wiki 页面本次不可读，不沿用旧博客中的“每小时 N 次”。
- **导出/验收**：核商业内容展示、持久保存与导出协议；测试超过两页、长文、根/子评论、套餐耗尽、token 失败，并核读接口和写接口配额分离。当前文档有搜索能力，不表示 LUMENIS 已购买或获准该命令。[统计示例](https://open.weibo.com/cli/skills/usage-insights)

### 3.5 B站（bilibili）

- **授权对象**：官方开放平台提供账号授权和创作者稿件等能力。基础账号信息要求 `USER_INFO` 与用户授权；签名/Access-Token 等需按当前规范。开发者协议要求相关 UP 授权和数据退出/解绑处理。[开放文档](https://open.bilibili.com/doc)、[账号信息接口](https://open.bilibili.com/doc/4/feb66f99-7d87-c206-00e7-d84164cd701c)、[开发者协议](https://open.bilibili.com/agreement/developer-service)
- **范围/评论**：授权稿件数据可含评论数、弹幕数等，不等于评论或弹幕逐条正文。公开可用的站内 Web API、社区逆向接口说明不自动成为官方对商业应用开放的合同。[开放平台隐私政策](https://open.bilibili.com/agreement/privacy-policy)
- **分页/窗口/认证**：通用搜索、稿件历史窗口、评论层级分页待核具体获批接口。官方错误中，127007 为应用无接口权限、127011 为用户未授权、127009 可能限额/忙、127305 涉白名单；不能全部转成“采完”。[签名及状态码文档](https://open.bilibili.com/doc/4/8673959e-f7bb-56e6-6e68-d225f971b81b)
- **导出/验收**：需接口清单+scope+UP 授权+用途/保存/转授条款。各 endpoint 独立验收多页稿件、缺失/下架稿件、撤权；评论正文未经获批接口证实则保持待核。

### 3.6 知乎（zhihu）

- **已核边界**：官方机构号协议描述账号运营、发布、互动等，不构成全站问题/回答/文章/评论的读取接口授权。此次未核得当前通用内容查询的官方公开开发者合同。[机构号服务协议](https://www.zhihu.com/org_service_agreement)、[官方隐私保护政策](https://www.zhihu.com/term/privacy)
- **窗口/分页/评论/限流**：搜索起止时间、offset/游标、回答详情、根评论/子评论、限流码和账号要求全部待核。配置里的 engine_verified_no_cookie_required 只能说明实现边界，不能代替平台许可。
- **导出/验收**：先取得服务方授权证据/正式产品接口清单，核正文、作者、互动数据、再展示/导出和删除义务。再按一个问题下多个回答、一个多页评论线程、文章详情、已删除内容做只读测试。若只具备公开页面许可，则按该受限覆盖标注，不承诺全站历史。

### 3.7 贴吧（tieba）

- **历史官方路线**：百度贴吧官方旧“贴吧开放平台”页描述申请指定吧或精品内容的合作，列标题、摘要、缩略图、发布时间、昵称、最后回复时间、回复数等字段。这是历史合作入口，不能证明2026年仍可自助开通，也不能把回复数当作完整楼层正文。[官方历史开放平台页](https://tieba.baidu.com/tb/zt/tiebaapi/index.html)
- **窗口/游标/层级/额度**：当前合作准入、关键词搜索、楼层和楼中楼、删除/折叠楼层、历史时间范围、游标和频控数值均待核。本次不引用民间移动端接口作为官方合同。
- **导出/验收**：先核现行合作方、允许吧范围、字段和用途/存储/导出协议，再设计跨页主题和楼中楼树验收。当前静态目录无 adapter binding，属于计划项，不能列已通平台。

### 3.8 Instagram（instagram）

- **官方路线与账号**：Meta 官方维护的 Postman 集合确认：Instagram API 面向 Business/Creator 专业账号。Facebook Login 路线需关联 Facebook Page；Instagram Login 不要求关联 Page。普通消费者账号不是这套专业账号 API 的目标。[Meta 官方 Instagram 工作区](https://www.postman.com/meta/instagram/overview)、[Facebook Login 集合](https://www.postman.com/meta/instagram/folder/9cgqucg/instagram-api-with-facebook-login)、[Instagram Login 集合](https://www.postman.com/meta/instagram/folder/1z5vxzu/instagram-api-with-instagram-login)
- **scope**：两条路线不要混配：Facebook Login 有 instagram_basic、instagram_manage_comments、pages_show_list/pages_read_engagement 等；Instagram Login 使用 instagram_business_basic、instagram_business_manage_comments。生产第三方账号还需对应 app review/access level，账号授权不等于应用已获全部能力。
- **范围/分页**：自有 media 评论管理、mentions、有限 hashtag/business 信息路线不等于任意个人全部历史内容。集合说明通常 cursor 分页；只有部分 insights 支持时间分页，不能泛化所有对象都支持 since/until。评论根节点与 replies 要分别核 endpoint、paging.next 和可见权限。
- **限流/导出/验收**：Graph 当前版本、业务用例限额、响应 usage headers、错误码/subcode、app review、保存/删除政策待项目核验。本次 developers.facebook.com 多页读取返回429，是文档访问失败，不能当作 API 实际配额。验收专业账号、两页媒体、两页评论/回复与撤权；普通账号/非自有媒体应明确不支持或权限缺失。

### 3.9 Facebook（facebook）

- **路线分开**：Pages API 是需核当前 Graph 版本和账号角色的候选；Page 管理权限、非自有 Page 内容访问功能、普通个人内容是不同授权范围。不能从“我能看见公开 Page”推成应用有 API 权限。[Pages 官方入口](https://developers.facebook.com/docs/pages-api/posts/)、[官方 Page access 说明](https://www.facebook.com/help/289207354498410/r.php/)
- **官方研究路线**：Meta Content Library/API 面向合格学术/非营利公共利益研究；数据范围、申请和运行环境有专门要求。它不是普通商业产品的无条件广泛读取入口，也不是现存 CrowdTangle 凭证替代品。[Meta 官方研究工具介绍](https://about.fb.com/news/2023/11/new-tools-to-support-independent-research/)、[Content Library 官方入口](https://transparency.meta.com/researchtools/meta-content-library)
- **分页/评论/限流**：本次 Pages/Graph 关键正文获取被429阻挡，未验证当前 posts/comments/replies 字段、cursor、since/until、分页上限、PPCA 等 feature 的具体适用规则；保持待核，不能用旧版本文章填空。实际接口应解析 Graph error code/subcode，不将权限错误当空页。
- **导出/验收**：需 app ID/Graph version、授权 Page、角色、获批权限/feature 和平台条款，再核多页 posts、评论和回复及撤权/下架。Meta 官方也明确区分授权与未授权自动抓取；个人下载自身信息能力不授予第三方内容批量导出权。[官方 scraping 说明](https://www.facebook.com/help/463983701520800)

### 3.10 X（x）

- **窗口/授权**：v2 recent search `/2/tweets/search/recent` 是近7天，单页最多100；full-archive `/2/tweets/search/all` 从2006年历史开始，需相应 pay-per-use/Enterprise 访问，单页最多500。是否获批、付费余额和应用权限本次未验证。[搜索介绍](https://docs.x.com/x-api/posts/search/introduction)
- **分页/评论**：传递返回 next_token，固定 query/start_time/end_time、排序和字段；不得把下一页 token 换到不同查询。回复本质是 Post，需按会话与 replied_to 关系构建，而非认为一个详情对象包含所有评论；旧回复可能落在当前搜索窗外，删除/保护账号影响可见性。[分页规范](https://docs.x.com/x-api/posts/search/integrate/paginate)、[数据字典](https://docs.x.com/x-api/fundamentals/data-dictionary)
- **429**：按 endpoint、app/user 计限；429 后遵守 x-rate-limit-reset，记录 x-rate-limit-limit/remaining。当前文档 recent 的应用级示例为450次/15分钟，full-archive 还受每秒限制；实际套餐和控制台仍需核验，不能只按一个全局 QPS。[官方限流](https://docs.x.com/x-api/fundamentals/rate-limits)
- **导出**：通用政策对第三方再分发主要限 IDs；有有限非自动对象下载例外，不可据此默认提供全量正文 CSV/API。展示需更新，内容不可用/收到删除请求需按政策处理。[开发者政策](https://docs.x.com/developer-terms/policy)
- **验收**：同一查询跨页、7天边界、全档案 entitlement、conversation 子树、重复 ID、429 后断点、删除同步与导出受限字段。仅配置 cookie/browser engine 不能证明官方 API 可用。

### 3.11 微信公众号（wechat）

- **候选路线**：自有或正式授权公众号的已发布消息/留言管理，和任意公众号全网搜索是两种范围。官方旧发布记录、留言管理文档及新 subscription/service 发布记录链接本次均未取得可读正文，故不将第三方 SDK 的参数宣称为已核官方当前合同。[旧发布记录入口](https://developers.weixin.qq.com/doc/offiaccount/Publish/Get_publication_records.html)、[新发布记录入口](https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_batchget.html)、[留言管理入口](https://developers.weixin.qq.com/doc/offiaccount/Comments_management/Image_Comments_Management_Interface.html)
- **必须核验**：账号类型/认证、app 凭证或第三方授权 token、发布记录与群发记录的集合差异、文章复合 ID/index、正文与摘要差异、留言是否仅精选/可见、作者回复与用户楼中楼区别。
- **分页/时间/限流**：候选 `freepublish/batchget` 的 offset/count/no_content 与 `comment/list` 的 begin/count/type，应以当前官方正文确认；本报告不填未经一手核定的页大小、历史天数或频控。空发表列表不能证明账号无历史文章，可能是记录集合/权限不同。
- **导出/验收**：先取得当前正式文档与权限页，核一个自有账号文章跨页、同一图文多篇、含留言文章、token 失效、IP/权限约束和正文保存/外发条款。只有公开原文许可时，标明链接级覆盖，不冒充全号历史采集。

### 3.12 视频号（channels）

- **官方证据状态**：本次未核得允许任意视频号关键词搜索、视频详情、评论正文与楼中楼批量读取的当前官方合同。微信视频号店铺/电商/带货、广告或直播工具的 API 不能因品牌同属视频号而替代此能力；第三方“视频号API”也不自动是腾讯授权。
- **待核项**：具体官方产品名称、接口目录、申请主体、账号所有权/授权关系、scope、时间范围、分页 token、根/子评论层级、频控和可导出字段。官方 channels 入口本次无法取得可读正文：[官方文档入口](https://developers.weixin.qq.com/doc/channels/API/basics/getaccesstoken.html)。
- **验收门槛**：先有可验证许可和合同，再选择获授权账号与多评论视频，验证分页/楼中楼/删除和错误状态；此时仍不得承诺全站搜索。当前产品目录为 PLANNED，必须保持未实现/未配置的区别。

### 3.13 YouTube（youtube）

- **官方读取**：Data API 可用 API key 获取允许公开读取的数据；账户管理、非公开数据或审核状态需恰当 OAuth。搜索支持 publishedAfter/publishedBefore（含边界，RFC3339）、pageToken、maxResults≤50；短页也可能有 nextPageToken。特定 channelId+type=video 且无 owner/developer/mine filter 时有500视频限制；日期排序/过滤仍可能索引不全。频道最新上传宜走 uploads playlist，不以搜索代替全历史。[search.list 当前正文](https://developers.google.com/youtube/data/reference/rest/v3/search/list)
- **评论树**：commentThreads.list 顶层线程、comments.list(parentId) 补全部可见回复，各自 maxResults≤100/pageToken；嵌入 replies 可能只是子集。顶层列表没有可泛用的视频 publishedAfter 式评论时间过滤；需按评论时间处理，不以视频发布时间代替。commentsDisabled/forbidden/404 是不同停止状态。[线程列表](https://developers.google.com/youtube/data/reference/rest/v3/commentThreads/list)、[回复列表](https://developers.google.com/youtube/data/reference/rest/v3/comments/list)、[线程资源的子集警告](https://developers.google.com/youtube/data/reference/rest/v3/commentThreads)
- **额度新旧口径**：官方修订历史 **2026-06-01** 开始 granular quota 转换，search.list/videos.insert 分独立桶；当前文档最近更新 **2026-10-15**。当前默认：每日100次 search.list、100次 videos.insert、其余端点合计10,000 units；search.list 每次消耗 Search Queries 桶1 unit。不要继续硬编码旧“search.list 每次100 units”，也不能把10月15日当上线日。**实际 project console、获批调整和迁移状态优先**；本次未查项目控制台。[修订历史](https://developers.google.com/youtube/data/revision_history)、[Quota/Audit 正文](https://developers.google.com/youtube/data/guides/quota_and_compliance_audits)
- **存储/衍生用途**：通用政策有30天刷新/删除、用户删除请求等规则及衍生数据限制。自2026-06-01起，经过审计并申请接受 Analytics & Reporting 附录的项目，可在规定条件下做评论 NLP 情绪、频道评分/标签等；已获准的统计与衍生指标可保存至36个月，评论正文/标题/描述仍30天刷新或删除。未获批不能自动用例外；不可推断用户敏感受保护属性。[通用政策](https://developers.google.com/youtube/terms/developer-policies)、[衍生指标与存储附录，2026-09-14更新](https://developers.google.com/youtube/terms/derived-metrics-policy)
- **验收**：项目额度桶与API enablement、两页搜索及日期边界、一个 replies 多页线程、禁评/私密/删除视频、quota耗尽分类、30天刷新与删除、分析用例获批证据。对外呈现只能是“指定查询和时段内可见样本”，不能叫全平台完整语料。

### 3.14 TikTok（tiktok）

- **三种路线独立**：Display API `video.list` 读取授权用户公开作品（默认10、最大20；按 create_time 倒序，cursor 为毫秒时间戳，可指定更早位置）；不能替代任意用户搜索或评论读取。[Display video.list](https://developers.tiktok.com/docs/en/tiktok-api-v2-video-list)
- **Research API**：须合格研究机构/项目审核，开发者账号本身不够；官方FAQ明确商业用户、广告主/创作者不适用。video query 单次 start_date/end_date 的跨度≤30天，最大100，使用 cursor+search_id+has_more；30天是单查询窗口，不等于全部历史只保留30天。评论接口 video_id 与 comment_id 二选一，根评论与回复分开请求，最大100。短页可能来自删除/私密内容。[Research FAQ](https://developers.tiktok.com/docs/en/research-api-faq)、[视频查询](https://developers.tiktok.com/docs/en/research-api-specs-query-videos)、[评论查询](https://developers.tiktok.com/docs/en/research-api-specs-query-video-comments)
- **研究专属额度/时效**：通常1000请求/日、至多100,000记录/日，UTC零点重置；token约2小时；新视频入索引可延迟48小时，统计最多延迟10天。这些条件仅说明研究API，不能作为LUMENIS已可用的商业计划。
- **Portability**：数据可携带产品可由符合条件的全球申请者申请，但导出的用户数据地区目前限定EEA/UK；还需Login Kit与Portability双重批准，授权范围、single/ongoing独立。它是用户自身导出，不是第三方内容宇宙。[产品说明](https://developers.tiktok.com/products/data-portability-api/)、[申请说明](https://developers.tiktok.com/docs/en/data-portability-api-application-guidelines?enter_method=left_navigation)
- **导出/验收**：商业广泛读取需另核正式 Business/合作产品及用途；不得拿Research凭证做商业采集。自有账号先验 display 跨页；若用户导出，验地区/范围/撤回/删除；评论树只在真实获准的相应产品内验。

### 3.15 Reddit（reddit）

- **许可优先**：Data API 商业使用需与 Reddit 另行协议；OAuth或低请求量不免除这一条件。保留/使用不能超获批用途；AI模型训练还需相应权利人许可，不能把普通分析与训练混为一谈。[Data API Terms，2026-07-20版本](https://redditinc.com/policies/data-api-terms)
- **认证/限流**：注册OAuth客户端和真实独特User-Agent；符合免费使用条件的客户端通常100 QPM，以10分钟窗口平均，读 X-Ratelimit-Used/Remaining/Reset。无身份或错误身份可能阻断，实际商业合同另定。[官方 Data API Wiki，2026-05-11更新](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki)
- **分页/层级**：listing 用 after/before fullname、count、limit（最大100）；帖子评论是树，包含 more 占位。`/api/morechildren` 一次最多100 child IDs，官方要求该接口同一时刻只发一个请求；不展开就不完整。search时间档位和索引不保证任意历史日期段穷尽。旧API参考自身不等于2026许可。[官方 API Reference](https://www.reddit.com/dev/api/)
- **删除/导出**：已删除内容应移除，账户删除需去除相关作者标识。Wiki提到48小时例行清理是建议，不能误写成所有数据统一强制48小时TTL；实际要满足删除同步与批准用途。对外正文导出、再分发、持久分析需商业协议明确。
- **验收**：先看商业协议与审批范围，再验两页listing、跨层 morechildren、removed/deleted、private/quarantined限制、429/reset；记录未展开 child IDs 和不可见原因，不用 post.num_comments 当采全判据。

### 3.16 LinkedIn（linkedin）

- **准入/角色**：Community Management 需产品审批，开发测试层与生产 Standard 层分开；请求固定 LinkedIn-Version（YYYYMM）和Rest.li协议版本。Posts API 的 r_organization_social/r_member_social 与新版 Comments 的 r_organization_social_feed/r_member_social_feed 不应合并成一个“读社媒”scope；成员读取受额外限制，组织读取还核授权人的组织角色。[准入](https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access?view=li-lms-2026-09)、[Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-09)、[Comments API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/comments-api?view=li-lms-2026-09)
- **范围/分页/树**：author finder 针对获授权作者/组织，不是全网关键词搜索；按相应 endpoint 的 start/count/返回paging链接读完，不由短页判尾页。评论通过 socialActions/{share/ugcPost/comment URN}/comments，commentURN可进一步定位回复；保留父URN和复合ID。时间窗口、层级最大深度与页大小仍需锁定API版本后核。
- **429**：应用与成员级每日限额，UTC午夜重置，具体数值不公开统一表，应查应用Analytics；429也可能基础设施保护，不能只按固定QPS重试。[Rate Limits](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts/rate-limits)
- **存储/导出高风险**：通用API条款默认不允许任意持久存储（含转换/哈希表达），特定条款例外另论；允许的存储须可隔离删除，不得成为无关第三方可访问数据仓；跨源混合与来源不可辨聚合亦受限。不能把获得API数据等价成可建跨平台原始正文仓或导出客户名单。[API Terms](https://www.linkedin.com/legal/l/api-terms-of-use)
- **验收**：先审实际Additional Terms与存储/分析用途，再验组织角色、scope、author多页、评论回复、版本失效、429与撤权；本次未确认任何LUMENIS应用权限。普通任意成员抓取路线不视为本产品官方许可。

## 4. 辅助源（不计入16个社媒品牌）

| 源 | 官方范围、分页/额度 | 授权/导出条件与验收 |
|---|---|---|
| Google 搜索 | Custom Search JSON API 当前已不接收新客户，存量客户需在2027-01-01前迁移。存量默认100查询/日，单页num≤10，每查询最多100结果，start+num不得超100；dateRestrict不是网页实际完整发布时间索引。[产品现况](https://developers.google.com/custom-search/v1/overview)、[cse.list](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list) | 不能把它设计为新客户稳定基础能力；先核实际产品/存量资格/项目key与cx。搜索结果是发现线索，不授予目标站全文采集/导出权。验查询翻页到上限、日期/站点过滤、额度失败，明确“搜索索引覆盖”与“源站内容覆盖”不同。 |
| GitHub | REST公开未认证通常60请求/小时/IP；常见认证5,000/小时，搜索另计。search最多1,000结果，常见认证搜索30/分钟、代码搜索10/分钟；可能incomplete_results=true，不能当全库。按page/per_page与Link翻页。[限流](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)、[搜索](https://docs.github.com/en/rest/search/search) | 辅助开发者源，仓库/issue/PR/release各有对象与评论。认证、私有仓权限、仓库许可证、正文再分发独立审查；公开不等于放弃版权。403/429按retry-after/reset与二级限流处理。验多页、incomplete_results、issue与PR评论类型、最小仓库权限；不把GitHub开发讨论计作新增社媒平台。 |

Google和GitHub实际读取方式尚未核实；上述是官方API候选的条件，不证明当前浏览器worker或connector使用了这些API。

## 5. 通用 Web 源（单列，不借道绕开平台限制）

| 通道 | 标准能证明什么 | 不能证明什么；实现/验收要求 |
|---|---|---|
| public_http | 普通HTTP资源读取，按站点授权范围使用条件请求/缓存；公开URL属于具体资源 | robots.txt是抓取规则，不是访问授权；没有登录不代表可无限抓取或商用。不得用它替代某社媒被拒绝的API范围。验HTTP状态、编码、canonical、ETag/Last-Modified、重定向与内容许可；401/403暂停权限路径，429遵守Retry-After。[RFC9309](https://www.rfc-editor.org/rfc/rfc9309.html) |
| web_rss | RSS条目可有guid/pubDate/link；ttl是刷新提示；comments通常是评论页链接 | 没有统一强制全历史/分页保证，publisher可仅保留近期条目；guid可缺失且不一定URL，pubDate也可缺。评论链接不等于评论数据。验重复guid、缺日期、feed裁剪、内容是摘要还是全文、站点许可。[RSS2规范](https://www.rssboard.org/rss-specification) |
| web_atom | Atom提供entry/id、updated与链接语义；另有RFC5005分页/归档扩展 | 不是所有feed都实现归档扩展，updated不能自动作初次发布时间。验next/prev/归档链、循环与重叠，区分feed当前窗口/可用archive。许可仍由发布方决定。[RFC4287](https://www.rfc-editor.org/info/rfc4287/)、[RFC5005](https://www.rfc-editor.org/info/rfc5005/) |
| sitemap | Sitemap提供URL发现、可选lastmod；单文件最多50,000URL/50MB未压缩，可索引多文件 | 不是正文、评论或搜索API，不保证全站所有URL、真实更新时间或授权。验index递归、同源规则、压缩/大小、去重、删除链接与lastmod缺失；URL数量不可直接当内容量。[官方协议](https://www.sitemaps.org/protocol.html) |

## 6. 跨平台实现与验收合同（建议，尚未改产品）

以下是研发交接建议，需用户另行明确授权后才能实施。

### 6.1 三个相互独立的门

1. **技术门**：官方endpoint/版本/参数已核；具体provider真实实现，能返回结构化结果。
2. **权限门**：组织、应用、账号、token scope/角色、区域、套餐、额度与获批用途都匹配。
3. **数据使用门**：允许采哪些字段、保存多久、是否可交给模型处理、模型处理是否涉及第三方传输、能否生成衍生指标、能否向客户导出、如何执行撤权与删除。

缺任一门均不应标“已可采”。模型推理、模型训练、统计分析、正文转售是不同用途，不能一概通过或一概拒绝。

### 6.2 每次采集运行的最小证据包

- 来源平台、官方产品/提供方、API版本、许可凭据引用（不记录token/secret明文）、授权账号及scope摘要、用途版本。
- 查询指纹：关键词、作者/账号、地区/语言、排序、开始/结束时间、时区、过滤器；采集时间与内容创建/更新时间分开。
- 每页请求序号、输入/输出cursor或page、官方has_more/next标志、响应码与业务码、耗时、重试次数、限流剩余/重置、返回条数/新增唯一数/重复数。
- 对象的稳定ID、来源链接、父ID/根ID、内容层级；根评论队列与回复队列独立。只得到统计数时标“计数”，不可伪装成空正文。
- 停止理由显式枚举：官方可见结果耗尽、已达指定时间窗、用户预算停止、日额度耗尽、短时限流待续、权限失效、游标失效、源站错误、显式索引/结果截断、部分回复不可见。失败不得折叠为success+0。
- 完整性声明必须限定“指定授权对象+查询+时间窗+可见状态”；禁止仅因某页为空/小于page_size或去重后新增为0就声称“采全”。

### 6.3 时间与游标测试

- 时间戳单位逐接口确认，特别是秒/毫秒、UTC/本地时区、published/updated/created区别；无服务端时间过滤的接口，不能声称请求已按时间窗精准截取。
- 先确认API允许该筛选，再采用有重叠边界的时间切片，并按稳定ID幂等去重。不能为绕过许可/配额而拆查询，也不能假设切片能突破索引保留或套餐上限。
- 不透明cursor只在原查询和权限上下文复用；排序/账号/过滤器变化创建新checkpoint。记录重复cursor、循环、游标过期并人工可审计恢复。
- 评论树必须包含“根列表未完”“某根回复未完”“more占位待展开”等状态；可见回复总数和平台显示总数差异不自动归因丢数，也不能自动忽略。
- 429/配额、401/403、404/删除、验证码/安全验证、网络失败分开。遵守官方backoff/Retry-After；不能通过换身份、代理或隐瞒User-Agent规避控制。

### 6.4 导出验收

默认不把原始正文批量导出作为“采集成功”的附赠功能。每个平台单独列：允许字段/对象、受众、用途、格式、保存期、来源归因、删除同步、是否需合同例外。若仅许可ID和链接，则导出只含获准内容。任何删除回收机制需覆盖正文、缓存、索引、衍生记录及已授权的下游处理范围；是否可保留匿名统计仍按平台合同，不自行假定。

## 7. 匿名既有采集 小红书个案的待证伪原因表

目前没有足够证据把“后期少”归因平台上限。应先取得原运行的脱敏配置和逐页日志；这项研究本身不授权重新采集或修改。

| 假设 | 必须看到的证据 | 能排除的错误解释 |
|---|---|---|
| 后期内容本来更少 | 同窗口、同排序、同账号可见性下，原始返回也下降，且有正常分页终止 | 只看清洗后新增行数不能证明源端量少 |
| 去重/增量导致新增少 | 原始返回数稳定，已有ID比例升高，checkpoint正常 | 这是新增率变化，不等于获取失败或平台上限 |
| 时间窗/关键词/排序改变 | query fingerprint、时区、边界、过滤器或排序发生变化 | 不可比较不同查询批次并得出“越采越少” |
| cursor/页码丢失或循环 | 连续页的cursor相同/跳页/被重置、has_more未消费、错误当空页 | 这是实现问题候选，不是官方限制证明 |
| 只取推荐顶层/未展开回复 | 根评论列表与reply_count、子任务队列不匹配 | “评论少”可能是层级覆盖不足 |
| token/权限/风控/额度 | 对应原始业务码、401/403/429、重置时间、请求ID、provider计费记录 | 没有错误原文不得臆测被风控或日上限 |
| provider预算/本地过滤 | max_pages/max_items/time_budget、短文本/日期/语言过滤、停止理由 | 本地上限不得宣传为平台上限 |
| 索引延迟/删除/私密变化 | 有时间戳的同ID可见性差异、官方说明、合规复核结果 | 不得把所有缺失都归“源站删帖” |

建议下一步顺序：先审已有日志和合法来源合同，再确定最小验证方案，最后才请求具体执行授权。当前可先做的产物是权限/来源证据清单及日志审查表，不是开通或实采。

## 8. 本次仍未解决的证据缺口

- 所有16个社媒的 LUMENIS 实际应用、账号、scope、商业合同、额度、授权有效期与现场读取均未核验。
- 小红书实际 匿名既有采集 provider 的官方身份与全文/评论许可；快手/B站通用评论正文能力；知乎/贴吧/视频号当前通用内容合作合同，均待核。
- 微信公众号新旧官方文档本次无法读取；Facebook关键Graph文档本次429；Instagram优先使用Meta官方Postman集合补充，未伪造缺失的版本/限额。
- 微博命令的当前实际套餐和搜索/回复合同；X账号套餐及导出例外；YouTube项目granular quota迁移/获批分析附录；TikTok商业路径；Reddit商业协议；LinkedIn适用Additional Terms均待核。
- 文档中的页大小、时间窗、日请求限额、搜索结果上限、索引保留、客户端预算、用户授权范围是不同类型的约束，不应合并成一个“平台采集上限”。
