# 序境 / LUMENIS｜匿名公开采集能力矩阵与多后端研究

- 编号：ZERO-AUTH-MATRIX-20261008
- 生成时间：2026-10-08 03:25 +08
- 基线：main 288f222decb48e2c8e9217c712e7af6f6c1aa9ce；local HEAD、cached origin/main、live GitHub main 一致，divergence 0/0。
- 工作树 DIRTY，其他窗口候选保留。本任务未改产品源码；Instagram/WeChat system adapter 是 dirty 文件，不是线上 main 证明。
- 机器矩阵：[ZERO-AUTH-MATRIX-20261008.json](./ZERO-AUTH-MATRIX-20261008.json)。

## 结论

覆盖 6 平台 × 12 能力，共 72 项。全部匿名 GET 样本 HTTP 200，只证明单一网页当时可达。响应只检查了字段名/key marker，没有提取和保存实际字段值；没有任何一项因此通过完整产品能力验收。

官方材料证实抖音有需授权的关键词搜索、评论、授权账号媒体/指标 API；Instagram 有专业账号媒体、评论、hashtag 与部分 Business/Creator 能力，仍受账号和 token 权限限制；X 官方 Search 区分近 7 天 Recent Search 与付费/Enterprise Full Archive，需开发者 App/token。Facebook Page 搜索依据是 Meta 2018 公告，当前权限需复核。微信官方开发文档本轮读取失败。

首次系统 DNS 预检对六个平台域名只返回 RFC1918 私网地址，安全预检在 HTTP 前拒绝。随后仅在当前 Python 进程启用仓库已有的 TLS 验证 DoH 回退，并仍通过 public_source 的公开 IP、host pin、redirect 检查。本机 DNS fake-IP 不等于平台拒绝匿名访问。

没有使用授权 session/API，没有把网页响应写为正式 Source/Evidence/Canonical；没有正式原始材料或用途/rights/actor/scope receipt。Production DB 未读写。

## 范围和访问分类

- 仅通过现有 public_source.fetch_public_url 做匿名 GET；trust_env=false、deny-all CookiePolicy、无 Authorization/Cookie/API token、TLS 校验开启、不重试。
- 排除 SESSION、COOKIE、INTERCEPT、UI、OpenCLI commands 和已有浏览器 profile；没有登录态访问。
- 六平台共 7 个 GET（XHS 首页与详情各一次，其余各一次），均 HTTP 200。逐请求时间未埋点，按约 2026-10-08 03:15–03:18 +08 记录。

| 标签 | 含义 |
|---|---|
| Z0 | 匿名公开入口。HTTP 200 只证明可达；字段值须实际提取。 |
| Z1 | 授权 Session/browser 只读路由；本批不执行，源码存在不证明授权/运行。 |
| Z2 | 官方 API；本批只有文档证据，没有真实 API 调用。 |
| BLOCKED | 某具体路径实际遇到拒绝/挑战/权属阻碍；不由未测试推导。 |
| UNKNOWN | 能力级证据不足。 |

## 六平台 × 十二能力矩阵

| 平台 | 能力 | 分类 | 证据状态 | 当前结论／限制 |
|---|---|---|---|---|
| 小红书／RedNote | 搜索 | UNKNOWN | NOT_VERIFIED | 未对匿名关键词搜索页/接口发请求。官方当前 API 目录列 OAuth 与授权用户基本信息；未在所查目录看到公开搜索，目录未覆盖处不推断不存在。 |
| 小红书／RedNote | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 单条公开笔记匿名 GET HTTP 200；只观察到 og:image 字段名及 timestamp marker，正文/作者/值未提取。 |
| 小红书／RedNote | 创作者／主页 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方 min_user_info 需 access_token，只返回当前授权用户基本资料；不能推导任意创作者查询。 |
| 小红书／RedNote | 创作者作品列表 | UNKNOWN | NOT_VERIFIED | 没有作者作品列表实测或当前官方 API 证据。 |
| 小红书／RedNote | 评论 | UNKNOWN | NOT_VERIFIED | 没有评论字段实测或官方目录证据。 |
| 小红书／RedNote | 评论回复 | UNKNOWN | NOT_VERIFIED | 没有回复列表实测。 |
| 小红书／RedNote | 互动指标 | UNKNOWN | NOT_VERIFIED | 没有互动指标数值提取。 |
| 小红书／RedNote | 发布时间 | UNKNOWN | NOT_VERIFIED | 仅观察到 timestamp marker，未提取值或时区。 |
| 小红书／RedNote | 媒体 URL | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 发现 og:image 字段名；URL 值未保存，媒体有效性/权利未查。 |
| 小红书／RedNote | 标签／话题 | UNKNOWN | NOT_VERIFIED | 没有提取标签/话题；搜索词不能证明平台标签。 |
| 小红书／RedNote | 分享／转发指标 | UNKNOWN | NOT_VERIFIED | 没有分享/转发计数值证据。 |
| 小红书／RedNote | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | 只访问发现首页，不解析榜单/趋势；首页 HTTP 200 不等于热点采集。 |
| 抖音 | 搜索 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方关键词视频搜索要求 video.search 权限和用户授权；文档称只返回最近 1 天。本轮未调用 API。 |
| 抖音 | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 指定公开视频页匿名 GET HTTP 200，但扫描未识别可用 OG/JSON-LD/详情字段。 |
| 抖音 | 创作者／主页 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方 user_info 需授权 token；证明的是授权账号资料，不是任意创作者搜索。 |
| 抖音 | 创作者作品列表 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方 video.list 需用户授权，只列该账号自己的作品；最多 4 页且无时间筛选。 |
| 抖音 | 评论 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方关键词视频评论接口需 client_token/应用权限（无需用户授权）；不是零凭证 Z0。 |
| 抖音 | 评论回复 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方关键词评论回复列表文档存在，需应用 token/权限；未调用。 |
| 抖音 | 互动指标 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | video.data 需用户授权，只支持该 token 对应用户的视频指标。 |
| 抖音 | 发布时间 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 授权视频列表样例含 create_time；未验证真实 API 返回。 |
| 抖音 | 媒体 URL | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 授权视频列表样例含 cover URL；链接有效性未验证。 |
| 抖音 | 标签／话题 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 关键词搜索/作品标题可能含话题字样；未确认结构化标签字段。 |
| 抖音 | 分享／转发指标 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 授权作品 statistics 样例含 share_count/forward_count；没有真实返回。 |
| 抖音 | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | 内容关键词搜索不等于趋势排序；未找到趋势端点证据。 |
| Instagram | 搜索 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | Meta 官方 API 文档列 hashtag media / Business Discovery 等授权能力；没有匿名搜索 smoke。 |
| Instagram | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 公开帖子 GET HTTP 200；观察到 OG/Twitter 字段名与 like/comment/timestamp key markers，值未提取。 |
| Instagram | 创作者／主页 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | Meta API 面向 Business/Creator 专业账号，受 token/权限限制。 |
| Instagram | 创作者作品列表 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 专业账号媒体 API 有文档说明；本轮未请求。 |
| Instagram | 评论 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方文档支持专业账号自身媒体评论管理；没有证明任意第三方帖子评论可读。 |
| Instagram | 评论回复 | UNKNOWN | NOT_VERIFIED | 文档提及评论管理/回复，但未确认读取已有回复 endpoint；发回复属于外部写操作。 |
| Instagram | 互动指标 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 文档提及专业账号和部分 Business/Creator 的基本 metadata/metrics；字段范围未核。 |
| Instagram | 发布时间 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 匿名页面观察到 timestamp key marker；值、时区、语义未解析。 |
| Instagram | 媒体 URL | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 匿名页面有 og:image/twitter:image 字段名；URL 未读取/检查。 |
| Instagram | 标签／话题 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方 API 有 hashtagged-media 能力；需 API 授权，不等于趋势榜。 |
| Instagram | 分享／转发指标 | UNKNOWN | NOT_VERIFIED | 没有确证通用 share/repost count 字段；匿名页数值未提取。 |
| Instagram | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | Hashtag 搜索不等于趋势榜；本轮没有趋势 endpoint/result。 |
| Facebook | 搜索 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | Meta 2018 官方公告称 Page search 需 Page Public Content Access 和 app review；当前权限须复核。 |
| Facebook | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 公开 Page post GET HTTP 200；OG/Twitter 和 comment/share/publish key markers 出现，值未提取。 |
| Facebook | 创作者／主页 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | Page API 历史官方材料涉及公开 Page；当前 app permission/版本未验证。 |
| Facebook | 创作者作品列表 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | Page posts 是历史官方 API 范围；当前 permission 未重新读取或调用。 |
| Facebook | 评论 | UNKNOWN | NOT_VERIFIED | HTML 有 comment_count key marker，正文/分页未提取；当前官方 comments edge 文档未取得。 |
| Facebook | 评论回复 | UNKNOWN | NOT_VERIFIED | 没有回复列表实测或当前官方字段文档。 |
| Facebook | 互动指标 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | HTML 有 comment/share 计数字段名，数值和口径未提取。 |
| Facebook | 发布时间 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | HTML 有 publish_time/timestamp key marker；未取得具体值。 |
| Facebook | 媒体 URL | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | HTML 有 og:image 字段名，URL 未保存或核权。 |
| Facebook | 标签／话题 | UNKNOWN | NOT_VERIFIED | 未获取标签/topic 字段；不以历史功能代替当前证据。 |
| Facebook | 分享／转发指标 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | HTML 有 share_count key marker，但没有值。 |
| Facebook | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | 没有实际趋势 endpoint/结果；Page search 不等于趋势。 |
| 微信公众号 | 搜索 | UNKNOWN | NOT_VERIFIED | 未发关键词搜索请求。本地 dirty 候选含 Sogou URL discovery，但不是 live 或官方内容证据。 |
| 微信公众号 | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 一篇文章匿名 GET HTTP 200；通用字段扫描未识别文章字段，parser 未运行。 |
| 微信公众号 | 创作者／主页 | UNKNOWN | NOT_VERIFIED | 没有作者/公众号主页匿名样本。 |
| 微信公众号 | 创作者作品列表 | UNKNOWN | NOT_VERIFIED | 没有作者作品列表实测。 |
| 微信公众号 | 评论 | UNKNOWN | NOT_VERIFIED | 当前配置 comments=false；本轮未实测。 |
| 微信公众号 | 评论回复 | UNKNOWN | NOT_VERIFIED | 没有评论回复证据。 |
| 微信公众号 | 互动指标 | UNKNOWN | NOT_VERIFIED | 文章响应未解析，不能推断阅读/点赞/在看数。 |
| 微信公众号 | 发布时间 | UNKNOWN | NOT_VERIFIED | dirty parser 有时间提取逻辑，但本次响应未解析；代码存在不证明现场返回。 |
| 微信公众号 | 媒体 URL | UNKNOWN | NOT_VERIFIED | 没有解析图片 URL/媒体。 |
| 微信公众号 | 标签／话题 | UNKNOWN | NOT_VERIFIED | 没有获取文章话题标签字段。 |
| 微信公众号 | 分享／转发指标 | UNKNOWN | NOT_VERIFIED | 没有分享计数观察。 |
| 微信公众号 | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | 没有读取官方热点/趋势结果；搜索发现不等于趋势。 |
| X | 搜索 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方文档给出 recent search（7天）与 full archive（pay-per-use/Enterprise）；需核准开发者账号、Project/App、keys/tokens。 |
| X | 帖子／笔记／文章详情 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | Status 匿名 GET HTTP 200；观察到 OG/Twitter/article/key markers，字段值未提取。 |
| X | 创作者／主页 | Z1 | SOURCE_ROUTE_ONLY_NOT_RUN | 当前 LUMENIS adapter 源码使用 CDP + cookie_vault；本轮未用 session 路径。 |
| X | 创作者作品列表 | Z1 | SOURCE_ROUTE_ONLY_NOT_RUN | 现有 browser adapter 有作者内容读取路径，但依赖 session owner；本轮未启用。 |
| X | 评论 | Z1 | SOURCE_ROUTE_ONLY_NOT_RUN | 现有 adapter 有评论读取路径，需要 authorized browser/session；本轮未启用。 |
| X | 评论回复 | UNKNOWN | NOT_VERIFIED | 没有精确 replies 读取端点证据；to: operator 不证明完整回复线程。 |
| X | 互动指标 | UNKNOWN | NOT_VERIFIED | 没有读取有效互动数值；未核实 API public_metrics 字段和请求参数。 |
| X | 发布时间 | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 匿名 HTML 有 article:published_time key marker；值未抽取。 |
| X | 媒体 URL | Z0 | LIVE_ANONYMOUS_HTTP_REACHABILITY_ONLY | 匿名 HTML 有 og:image/twitter:image key；URL 未读取/校验。 |
| X | 标签／话题 | Z2 | OFFICIAL_API_DOCUMENTATION_ONLY_NOT_CALLED | 官方 Search Posts 文档支持 hashtag query operator，API 仍需 developer app/token。 |
| X | 分享／转发指标 | UNKNOWN | NOT_VERIFIED | 没有验证 repost/share count 字段和值。 |
| X | 发现／趋势／热点 | UNKNOWN | NOT_VERIFIED | 官方导航可见 Trends 章节，但未读取具体 endpoint/permission，也未请求。 |

## 匿名公开 GET 样本

| ID | URL | HTTP/大小 | 观察到的字段名或 key marker |
|---|---|---:|---|
| R_XHS_HOME | [https://www.xiaohongshu.com/explore](https://www.xiaohongshu.com/explore) | 200 / 36679 B | og:image, timestamp (embedded marker) |
| R_XHS_DETAIL | [https://www.rednote.com/discovery/item/69a7bc76000000002203aa75](https://www.rednote.com/discovery/item/69a7bc76000000002203aa75) | 200 / 279263 B | og:image, timestamp (embedded marker) |
| R_DOUYIN_DETAIL | [https://www.douyin.com/video/7117200114686414094](https://www.douyin.com/video/7117200114686414094) | 200 / 72914 B | 无通用字段识别 |
| R_IG_POST | [https://www.instagram.com/p/CmUv48DLvxd/](https://www.instagram.com/p/CmUv48DLvxd/) | 200 / 1038476 B | og:description, og:image, og:title, og:type, og:url, twitter:card, twitter:image, twitter:title, like_count (key marker), comment_count (key marker), timestamp (key marker), screen_name (key marker), user_id (key marker) |
| R_FB_POST | [https://www.facebook.com/PhilipsHomeLivingMY/posts/register-your-product-now-with-our-online-registration-portal-to-get-2-to-5-year/2530989226953745/](https://www.facebook.com/PhilipsHomeLivingMY/posts/register-your-product-now-with-our-online-registration-portal-to-get-2-to-5-year/2530989226953745/) | 200 / 811756 B | og:description, og:image, og:title, og:type, og:url, twitter:title, twitter:description, twitter:image, twitter:card, comment_count (key marker), share_count (key marker), publish_time (key marker), timestamp (key marker), comment_list (key marker) |
| R_WECHAT_ARTICLE | [https://mp.weixin.qq.com/s/ClOUA5AHJqmAFYSUONk8Ww](https://mp.weixin.qq.com/s/ClOUA5AHJqmAFYSUONk8Ww) | 200 / 18165 B | 无通用字段识别 |
| R_X_POST | [https://x.com/HurriyatEN/status/2041724546366202299](https://x.com/HurriyatEN/status/2041724546366202299) | 200 / 99198 B | og:description, og:image, og:title, og:type, og:url, twitter:card, twitter:description, twitter:image, twitter:title, article:author, article:published_time, timestamp (key marker), media_url (key marker), screen_name (key marker) |

请求无 Cookie、授权头或 API token；redirect 经过同一 public_source guard。没有观察到 challenge marker，但短时单样本不能证明稳定性。字段值未提取。

## 官方来源

| ID | 来源 | 类型 | 支持的判断 |
|---|---|---|---|
| S_XHS_API | [小红书开放平台 API 参考](https://openaccount.xiaohongshu.com/docs/api-reference) | Official | 目录列 OAuth/device authorization/current authorized-user basic info；basic_info 要 access_token，返回 open_id/nickname/avatar/gender/region。所查目录未见公开内容搜索，不据此断言整个服务没有其它 API。 |
| S_DY_SEARCH | [抖音关键词视频搜索](https://open.douyin.com/platform/resource/docs/openapi/search-management/keywords-video-list/keywords-video/) | Official | video.search 需应用权限和用户授权；文档称只返回最近 1 天。 |
| S_DY_LIST | [抖音授权账号视频列表](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/search-video/account-video-list) | Official | video.list 需用户授权，仅列授权用户作品；最多四页、不支持时间过滤；样例含 title/create_time/cover/statistics。 |
| S_DY_PROFILE | [抖音获取用户基本信息](https://open.douyin.com/platform/resource/docs/openapi/account-management/get-account-open-info/) | Official | user_info 要求用户 access token；不等同任意创作者公开查询。 |
| S_DY_COMMENT | [抖音关键词视频评论列表](https://open.douyin.com/platform/resource/docs/openapi/search-management/keywords-video-comment-management/comment-list/) | Official | client_token 不需用户授权，但仍需 app token/scope；样例有 content/create_time/digg_count/reply_comment_total。 |
| S_DY_REPLY | [抖音关键词评论回复列表](https://open.douyin.com/platform/resource/docs/openapi/search-management/keywords-video-comment-management/comment-reply-list/) | Official | 文档列出 video.search.comment 下的回复列表；本轮未调用。 |
| S_DY_VIDEO_DATA | [抖音单视频数据](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/search-video/video-data) | Official | video.data 需用户授权，只能查 token 对应账号上传的视频；文档涉及点赞/播放指标。 |
| S_IG_META | [Meta Instagram API 官方 Postman collection](https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api) | Official Meta workspace | 官方材料介绍专业账号媒体、评论管理、hashtags、部分 Business/Creator 元数据和指标；须 app/token/permission，未调用。 |
| S_FB_PAGE_SEARCH | [Meta Pages API 平台公告](https://about.fb.com/news/2018/07/a-platform-update/) | Official historical | 2018 公告称 Page search 需要 Page Public Content Access 和 app review；当前 access policy 需复核。 |
| S_X_SEARCH | [X API Search Posts](https://docs.x.com/x-api/posts/search/introduction) | Official current docs | Recent Search 7 天、Full Archive 付费/Enterprise；需 approved developer account、Project/App、keys/tokens；query operator 支持 hashtags。 |
| S_WECHAT_OFFICIAL_UNAVAILABLE | [微信公众号开发者文档访问尝试](https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Overview.html) | Official retrieval attempt | 本轮浏览工具返回内部错误/空内容；没有使用第三方镜像代替官方事实。 |
| S_LUMENIS_X | LUMENIS X adapter source | Current source | System/V4 X routes use CDP/browser + cookie_vault；本批未使用，不代表 session 已授权/可用。 |
| S_CONFIG | LUMENIS platform adapter config | Current source | Douyin disabled pending worker/session; Instagram/Facebook proxy+Cookie; WeChat original public article+Permission; X Cookie+browser gate。 |
| S_PUBLIC_SOURCE | LUMENIS public_source | Current source | 拒绝 Authorization/Cookie；TLS verify、DNS address validation、host pin 与 redirect validation；有 process-local DoH fallback。 |
| S_DIRTY_WECHAT | WeChat adapter working-tree candidate | Unpublished dirty source | 含文章 parser/Sogou URL discovery，但未运行且不属于 published main truth。 |
| S_DIRTY_INSTAGRAM | Instagram adapter working-tree candidate | Unpublished dirty source | 含 public HTML parser/detail candidate；文件 dirty，未运行或发布。 |

微信官方文档 retrieval 失败，不使用第三方镜像代替。Facebook Page 权限材料来自 2018 官方公告，时效有限。Instagram 使用 Meta 官方 Postman 集合，未调用 API。

## 序境 Owner 和源码证据

唯一采集 Owner 是 SYSTEM Collector。AGENTS.md 的 C1/W1、Collector P0/FND 和 Source Owner Index/Shared Collector contract 要求 Source → Evidence → Canonical 单链；不新增第二 Collector、Truth 或结果库。

- config.py：Douyin disabled + worker/session gate；Instagram/Facebook proxy+Cookie gate；WeChat public original article + Permission；X cookie+browser gate。配置不证明运行。
- public_source.py：91–139 安全 DoH；234–300 host/redirect 检查；369–370 拒绝 Authorization/Cookie；383–481 TLS 验证的公开 GET。
- XHS adapter 36–203 走授权 worker；detail/health 不证明匿名解析。
- Douyin system adapter 20–21 disabled；v4 caller 使用 Cookie/session browser。
- Instagram system adapter 20–88 public parser candidate、99–109 默认 disabled + proxy/Cookie；该文件 dirty，不是线上 main 证据。
- Facebook system/v4 source 有 Cookie/browser 路径；health metadata 不证明内容读取。
- X system/v4 adapter 走 CDP/browser + cookie_vault；本批未用。
- WeChat dirty adapter 行 30–86 parser 与 90–177 discovery/detail 只证明本地候选代码存在，未运行/未发布。

### 源文件 SHA-256

| 路径 | 状态 | SHA-256 |
|---|---|---|
| lumenis/system/collector/adapters/config.py | clean at 288f222 | 8349c2ec04bcdf475baf334de0a9a75624a779883593036fc1d0c3b367c71bd6 |
| lumenis/system/collector/adapters/public_source.py | clean at 288f222 | b338080b2fa5a7fc8346a11104eba85a71cfaf4aa1fb851233d659773822c712 |
| lumenis/system/collector/adapters/xhs.py | clean at 288f222 | 8789b112db0dce3dbedb9971f6e38cc1e9e1beeee3b2f46796a53cc3ecce6bac |
| lumenis/system/collector/adapters/douyin.py | clean at 288f222 | 19049a44afacb263da8e064795e22786bbbe8c874520ad19b24f422fd47eaf05 |
| lumenis/system/collector/adapters/facebook.py | clean at 288f222 | 427df5a92d26afe6a1ec33a1726db398e4f128d0ba6201e8f1c3fa11235c9912 |
| lumenis/system/collector/adapters/x_platform.py | clean at 288f222 | 9808a186548283958d3b8f4a7050b3ef1295937616cb9f4272e5c8dd3d08e650 |
| lumenis/system/collector/adapters/instagram.py | dirty local candidate | 4795d2dbbc6e613efba7ac271fb72f6526e28902db91a56300814e4867efa9d5 |
| lumenis/system/collector/adapters/wechat.py | dirty local candidate | d1c4fe723ad304b0ea30cf5888b2e99dbfb5cea4f8b5bc4bf133af04cbf3dc21 |
| lumenis/adapters/douyin.py | clean at 288f222 | f25ae30baa690b6c8e03a00bc14d39272ec2e1eea1ac2e0eec73b4231ce43d92 |
| lumenis/adapters/instagram.py | clean at 288f222 | c9feb90285a8f118271a561aad18dc9e6d32346b59a85b969fdc8d7c7ee8779 |
| lumenis/adapters/facebook.py | clean at 288f222 | 1c23619d8bff4a3061741d267a310c4886ae6f0469ac16da591e47d3246845a0 |
| lumenis/adapters/x_platform.py | clean at 288f222 | 8c40983a8436a6c6b0c7ef075ff93b944740d62c6f0a5022f1caba929cbd837f |

Dirty candidate 以工作树 hash 为准，不能用 main permalink 假称已发布。

## 上游研究结论

| 项目快照 | SHA | License | 决定 | 实际机制与适配 |
|---|---|---|---|---|
| [Agent-Reach](https://github.com/Panniantong/Agent-Reach/tree/94f06c1969dfc1834001269d79d3ad0972d9dee6) | 94f06c1969dfc1834001269d79d3ad0972d9dee6 | MIT | ADAPT PRINCIPLES ONLY | ordered backend routing/per-backend checks useful; some social routes use OpenCLI with existing Chrome session or Cookie, therefore Z1; no parallel Collector/store. |
| [OpenCLI](https://github.com/jackwener/OpenCLI/tree/24136945847afbfad266c6c46a8cd335377f9112) | 24136945847afbfad266c6c46a8cd335377f9112 | Apache-2.0 | NO INTEGRATION THIS BATCH; ADAPT ERROR/ACCESS SEMANTICS | README explicitly uses logged-in Chrome, Browser Bridge extension and daemon; session/UI/intercept paths excluded. No install/command run. |
| [NVIDIA OpenShell](https://github.com/NVIDIA/OpenShell/tree/e406c2befbe65501409026d49259602669f7246a) | e406c2befbe65501409026d49259602669f7246a | Apache-2.0 | RESEARCH ONLY | policy sandbox for files/process/network; Windows WSL2 is experimental and requires Docker/Podman or virtualization; no install. |

Agent-Reach 可借鉴 capability-level backend routing 和 per-route readiness；fallback 必须服从 Permission，并记录 requested/actual access class、backend、原因。OpenCLI 的登录浏览器、扩展、daemon、操作式 Browser 与本批 session/UI/intercept 排除范围冲突，不集成。OpenShell Windows/WSL2 为实验路线且部署依赖较重，当前只研究。

## 对现有 Collector 的最小适配建议

1. 在现有 PlatformManifest/Adapter 内按 capability 记录 route、access class、auth requirement、backend、字段证据、健康状态和 unavailable reason；不建新 owner。
2. 区分匿名页面可达和业务字段抽取；只有实际值解析、来源/时间/版本与质量检查完成才标 ready。
3. Z0→Z1/Z2 不能静默改变授权、session 或 API scope；失败返回真实 AUTH_REQUIRED/UNKNOWN/UNAVAILABLE。
4. 热点/趋势和普通搜索分开；平台原生热度与序境样本统计分开记录。
5. Evidence 入库需原始来源、捕获时间、rights/use class、actor/scope receipt；训练用途另行授权。

## 分层状态

| 层 | 状态 |
|---|---|
| SOURCE | OBSERVED：main 288f222，源 hash/dirty 状态如上。 |
| 匿名 HTTP | PARTIAL LIVE：7 GET，均 200；只有 reachability/key markers。 |
| Parser | NOT VERIFIED：未运行 Instagram/WeChat parser，字段值未保存。 |
| API / Session runtime | NOT RUN：未使用官方 API 或授权 session。 |
| Evidence / Canonical | NOT ADMITTED：无 rights/scope receipt，未访问 Production DB。 |
| TEST / CI | NOT RUN。 |
| USER OUTCOME | NOT VERIFIED：未形成正式产品可追溯结果。 |

## 未覆盖部分

- 每个平台仅一或两个页面样本；不能代表该平台范围、长期稳定性、许可、商业使用或训练权。
- WeChat 官方文档读取失败；Instagram 精确 schema 需按 Meta 当前官方文档核；Facebook 2018 Page 权限需复核。
- 无匿名 browser DOM/hydration 测试；没有 Source → Evidence → Canonical 正式准入，C1 采集验收仍 OPEN。
- 72 行中多数为 UNKNOWN 或 Z1/Z2 文档状态；这不等于平台不支持。

报告和 JSON 是研究记录，不是 Permission receipt、采集准入或验收 PASS。
