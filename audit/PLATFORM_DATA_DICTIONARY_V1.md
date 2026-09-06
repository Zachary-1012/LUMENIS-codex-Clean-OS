# ZBC全平台采集数据标准字典 V1.0

> 版本：V1.0
> 生效日期：2026-09-07
> 适用范围：Z-Brand Core / CorTech-TaikooHui 全平台采集体系
> 核心原则：三层数据模型（Platform Raw → Platform Normalized → ZBC Canonical Truth）

---

## 0. 命名规则（定死，不可违反）

### 优先级
1. **第一优先级**：平台原生标准名（Raw层），如xhs `liked_count`, douyin `digg_count`, bilibili `view`
2. **第二优先级**：ZBC Canonical标准名（Normalized层），如`like_count`/`view_count`
3. **第三优先级**：业务统一指标，如`engagement`/`engagement_rate`

### 禁止命名
- 禁止 `likes`/`like`/`liked`/`likes_num`/`thumbs` 等随意命名
- 平台原生指标永远保留不能删除（Raw中`liked_count`/`digg_count`全部保留，Normalized映射到`like_count`）

### 缺失值规则
- 缺失值显式标记：`NULL` / `unknown` / `missing` / `unavailable`
- 禁止用0或空字符串静默填充
- 视频号等不存在公开字段的平台，字段值标`unavailable`

### 时间口径
- `publish_datetime` / `published_at`：内容真实发布时间
- `captured_at` / `collected_at`：系统采集时间
- 所有表必须分离这两个时间字段

---

## 1. 三层数据模型

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: ZBC Canonical Truth (业务真值层)               │
│  brands / events / content_analysis / creators /         │
│  metric_snapshots / event_mentions / risk                │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Platform Normalized (跨平台统一层)              │
│  platform_accounts / platform_contents / platform_comments│
├─────────────────────────────────────────────────────────┤
│  Layer 1: Platform Raw (平台原生层)                       │
│  xhs_notes / douyin_videos / bilibili_videos / ...      │
│  (12平台 × 内容/评论/用户表，保留平台原生字段名)           │
└─────────────────────────────────────────────────────────┘
         ↑ 采集入库          ↑ Normalizer映射        ↑ 业务分析
    平台API/浏览器        字段映射+去重+主体过滤    事件/风险/统计/报告
```

**关键规则**：不能因为统一字段而丢掉平台特有字段。Raw层完整保留平台原生字段，Normalized层做映射，Canonical层做业务聚合。

---

## 2. Platform Raw层（12平台原生表）

### 2.1 小红书 XHS

#### xhs_notes（小红书笔记）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| note_id | TEXT PK | 笔记ID | note_id |
| title | TEXT | 标题 | title |
| desc | TEXT | 正文描述 | desc |
| type | TEXT | 类型(normal/video) | type |
| user_id | TEXT | 作者用户ID | user_id |
| nickname | TEXT | 作者昵称 | nickname |
| avatar | TEXT | 作者头像URL | avatar |
| liked_count | INTEGER | 点赞数 | liked_count |
| collected_count | INTEGER | 收藏数 | collected_count |
| comment_count | INTEGER | 评论数 | comment_count |
| share_count | INTEGER | 分享数 | share_count |
| time | INTEGER | 发布时间戳 | time |
| url | TEXT | 笔记URL | url |
| tag_list | TEXT(JSON) | 标签列表 | tag_list |
| image_list | TEXT(JSON) | 图片列表 | image_list |
| video | TEXT(JSON) | 视频信息 | video |
| source_keyword | TEXT | 来源搜索关键词 | source_keyword |
| xsec_token | TEXT | 详情签名令牌 | xsec_token |
| collected_at | TEXT | 采集时间 | collected_at |

#### xhs_note_comments（小红书笔记评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| note_id | TEXT | 所属笔记ID |
| user_id | TEXT | 评论者用户ID |
| nickname | TEXT | 评论者昵称 |
| content | TEXT | 评论内容 |
| like_count | INTEGER | 点赞数 |
| sub_comment_count | INTEGER | 子评论数 |
| time | INTEGER | 发布时间戳 |
| collected_at | TEXT | 采集时间 |

#### xhs_users（小红书用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT PK | 用户ID |
| nickname | TEXT | 昵称 |
| avatar | TEXT | 头像URL |
| desc | TEXT | 个人简介 |
| fans | INTEGER | 粉丝数 |
| following | INTEGER | 关注数 |
| interaction | TEXT(JSON) | 互动数据 |
| gender | INTEGER | 性别(0未知/1男/2女) |
| collected_at | TEXT | 采集时间 |

---

### 2.2 抖音 Douyin

#### douyin_videos（抖音视频）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| aweme_id | TEXT PK | 视频ID(19位BigInt，字符串保精度) | aweme_id |
| desc | TEXT | 视频描述 | desc |
| author_id | TEXT | 作者sec_uid | author_id/sec_uid |
| author_uid | TEXT | 作者数字uid | uid |
| create_time | INTEGER | 发布时间戳 | create_time |
| digg_count | INTEGER | 点赞数 | digg_count |
| comment_count | INTEGER | 评论数 | comment_count |
| share_count | INTEGER | 分享数 | share_count |
| collect_count | INTEGER | 收藏数 | collect_count |
| play_count | INTEGER | 播放数 | play_count |
| download_count | INTEGER | 下载数 | download_count |
| music_id | TEXT | 音乐ID | music_id |
| hashtag_list | TEXT(JSON) | 话题标签列表 | hashtag_list |
| location | TEXT | 地理位置 | location |
| duration | INTEGER | 视频时长(秒) | duration |
| url | TEXT | 视频URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### douyin_comments（抖音评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| aweme_id | TEXT | 所属视频ID |
| user_id | TEXT | 评论者sec_uid |
| nickname | TEXT | 评论者昵称 |
| content | TEXT | 评论内容 |
| digg_count | INTEGER | 点赞数 |
| reply_count | INTEGER | 回复数 |
| create_time | INTEGER | 发布时间戳 |
| collected_at | TEXT | 采集时间 |

#### douyin_users（抖音用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| sec_uid | TEXT PK | 加密用户ID |
| uid | TEXT | 数字用户ID |
| nickname | TEXT | 昵称 |
| avatar | TEXT | 头像URL |
| signature | TEXT | 个性签名 |
| follower_count | INTEGER | 粉丝数 |
| following_count | INTEGER | 关注数 |
| total_favorited | INTEGER | 获赞数 |
| collected_at | TEXT | 采集时间 |

---

### 2.3 B站 Bilibili

#### bilibili_videos（B站视频）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| bvid | TEXT PK | BV号(Base58) | bvid |
| aid | INTEGER | 数字AV号 | aid |
| title | TEXT | 标题 | title |
| owner_mid | TEXT | UP主mid | owner/mid |
| owner_name | TEXT | UP主名称 | owner/name |
| pubdate | INTEGER | 发布时间戳 | pubdate |
| duration | INTEGER | 时长(秒) | duration |
| view | INTEGER | 播放数 | view/stat.view |
| like | INTEGER | 点赞数 | like/stat.like |
| coin | INTEGER | 投币数 | coin/stat.coin |
| favorite | INTEGER | 收藏数 | favorite/stat.favorite |
| share | INTEGER | 分享数 | share/stat.share |
| reply | INTEGER | 评论数 | reply/stat.reply |
| danmaku | INTEGER | 弹幕数 | danmaku/stat.danmaku |
| tid | INTEGER | 分区ID | tid |
| tname | TEXT | 分区名称 | tname |
| url | TEXT | 视频URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### bilibili_comments（B站评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| rpid | TEXT PK | 评论ID |
| oid | TEXT | 所属视频aid |
| mid | TEXT | 评论者mid |
| username | TEXT | 评论者名称 |
| content | TEXT | 评论内容 |
| like | INTEGER | 点赞数 |
| rcount | INTEGER | 回复数 |
| ctime | INTEGER | 发布时间戳 |
| collected_at | TEXT | 采集时间 |

#### bilibili_users（B站用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| mid | TEXT PK | 用户mid |
| name | TEXT | 昵称 |
| avatar | TEXT | 头像URL |
| sign | TEXT | 签名 |
| level | INTEGER | 等级 |
| follower | INTEGER | 粉丝数 |
| following | INTEGER | 关注数 |
| collected_at | TEXT | 采集时间 |

---

### 2.4 视频号 Channels

> 注意：视频号无公开API，可采集字段有限。不存在的公开字段标`unavailable`。

#### channels_videos（视频号视频）
| 字段 | 类型 | 说明 | 可采集性 |
|------|------|------|---------|
| object_id | TEXT PK | 视频对象ID | 可采集 |
| desc | TEXT | 视频描述 | 可采集 |
| author_id | TEXT | 作者ID | 可采集 |
| author_name | TEXT | 作者名称 | 可采集 |
| create_time | INTEGER | 发布时间 | 可采集 |
| like_count | INTEGER | 点赞数 | 可采集(部分) |
| comment_count | INTEGER | 评论数 | unavailable |
| share_count | INTEGER | 分享数 | unavailable |
| collect_count | INTEGER | 收藏数 | unavailable |
| view_count | INTEGER | 播放数 | unavailable |
| duration | INTEGER | 时长 | 可采集(部分) |
| url | TEXT | 视频URL | 可采集(部分) |
| location | TEXT | 地理位置 | unavailable |
| collected_at | TEXT | 采集时间 | 系统字段 |

#### channels_comments（视频号评论）
| 字段 | 类型 | 说明 | 可采集性 |
|------|------|------|---------|
| comment_id | TEXT PK | 评论ID | 可采集 |
| object_id | TEXT | 所属视频ID | 可采集 |
| author_id | TEXT | 评论者ID | 可采集 |
| author_name | TEXT | 评论者名称 | 可采集 |
| content | TEXT | 评论内容 | 可采集 |
| like_count | INTEGER | 点赞数 | 可采集(部分) |
| create_time | INTEGER | 发布时间 | 可采集 |
| collected_at | TEXT | 采集时间 | 系统字段 |

---

### 2.5 YouTube

#### youtube_videos（YouTube视频）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| video_id | TEXT PK | 视频ID | video_id/id |
| channel_id | TEXT | 频道ID | channel_id/snippet.channelId |
| title | TEXT | 标题 | snippet.title |
| description | TEXT | 描述 | snippet.description |
| view_count | INTEGER | 观看数 | statistics.viewCount |
| like_count | INTEGER | 点赞数 | statistics.likeCount |
| favorite_count | INTEGER | 收藏数 | statistics.favoriteCount |
| comment_count | INTEGER | 评论数 | statistics.commentCount |
| duration | TEXT | 时长(ISO 8601) | contentDetails.duration |
| category_id | TEXT | 分类ID | snippet.categoryId |
| tags | TEXT(JSON) | 标签列表 | snippet.tags |
| live_broadcast_content | TEXT | 直播类型 | snippet.liveBroadcastContent |
| default_language | TEXT | 默认语言 | snippet.defaultLanguage |
| published_at | TEXT | 发布时间(RFC3339) | snippet.publishedAt |
| url | TEXT | 视频URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### youtube_comments（YouTube评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| video_id | TEXT | 所属视频ID |
| author_channel_id | TEXT | 作者频道ID |
| author_display_name | TEXT | 作者名称 |
| text_display | TEXT | 评论内容(HTML) |
| text_original | TEXT | 评论内容(原文) |
| like_count | INTEGER | 点赞数 |
| reply_count | INTEGER | 回复数 |
| published_at | TEXT | 发布时间 |
| updated_at | TEXT | 更新时间 |
| collected_at | TEXT | 采集时间 |

#### youtube_channels（YouTube频道）
| 字段 | 类型 | 说明 |
|------|------|------|
| channel_id | TEXT PK | 频道ID |
| title | TEXT | 频道名称 |
| description | TEXT | 频道描述 |
| custom_url | TEXT | 自定义URL |
| subscriber_count | INTEGER | 订阅数 |
| video_count | INTEGER | 视频数 |
| view_count | INTEGER | 总观看数 |
| country | TEXT | 国家 |
| published_at | TEXT | 创建时间 |
| collected_at | TEXT | 采集时间 |

---

### 2.6 TikTok

#### tiktok_videos（TikTok视频）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| video_id | TEXT PK | 视频ID | id/video.id |
| author_username | TEXT | 作者用户名 | author.unique_id |
| author_id | TEXT | 作者ID | author.id |
| desc | TEXT | 视频描述 | desc |
| create_time | INTEGER | 发布时间戳 | create_time |
| digg_count | INTEGER | 点赞数 | statistics.digg_count |
| comment_count | INTEGER | 评论数 | statistics.comment_count |
| share_count | INTEGER | 分享数 | statistics.share_count |
| play_count | INTEGER | 播放数 | statistics.play_count |
| collect_count | INTEGER | 收藏数 | statistics.collect_count |
| music_id | TEXT | 音乐ID | music.id |
| hashtag_list | TEXT(JSON) | 话题标签列表 | challenges/text_extra |
| duration | INTEGER | 时长(秒) | video.duration |
| url | TEXT | 视频URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### tiktok_comments（TikTok评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| video_id | TEXT | 所属视频ID |
| user_id | TEXT | 评论者ID |
| username | TEXT | 评论者用户名 |
| text | TEXT | 评论内容 |
| like_count | INTEGER | 点赞数 |
| reply_count | INTEGER | 回复数 |
| create_time | INTEGER | 发布时间戳 |
| collected_at | TEXT | 采集时间 |

#### tiktok_users（TikTok用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT PK | 用户ID |
| username | TEXT | 用户名(unique_id) |
| nickname | TEXT | 昵称 |
| avatar | TEXT | 头像URL |
| signature | TEXT | 签名 |
| follower_count | INTEGER | 粉丝数 |
| following_count | INTEGER | 关注数 |
| total_favorited | INTEGER | 获赞数 |
| collected_at | TEXT | 采集时间 |

---

### 2.7 Instagram

#### instagram_media（Instagram媒体）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| media_id | TEXT PK | 媒体ID(BigInt，字符串保精度) | id |
| media_type | TEXT | 类型(IMAGE/VIDEO/CAROUSEL_ALBUM) | media_type |
| shortcode | TEXT | 短码 | shortcode |
| permalink | TEXT | 永久链接 | permalink |
| caption | TEXT | 标题/描述 | caption |
| author_username | TEXT | 作者用户名 | owner.username |
| author_id | TEXT | 作者ID | owner.id |
| children | TEXT(JSON) | 子媒体(轮播图) | children |
| location | TEXT(JSON) | 位置信息 | location |
| hashtags | TEXT(JSON) | 话题标签 | hashtags |
| mentions | TEXT(JSON) | @提及 | mentions |
| collaboration | TEXT(JSON) | 合作创作者 | collaboration |
| like_count | INTEGER | 点赞数 | like_count |
| comment_count | INTEGER | 评论数 | comments_count |
| taken_at | INTEGER | 发布时间戳 | taken_at_timestamp |
| url | TEXT | 媒体URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### instagram_comments（Instagram评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| media_id | TEXT | 所属媒体ID |
| user_id | TEXT | 评论者ID |
| username | TEXT | 评论者用户名 |
| text | TEXT | 评论内容 |
| like_count | INTEGER | 点赞数 |
| parent_comment_id | TEXT | 父评论ID |
| created_at | INTEGER | 发布时间戳 |
| collected_at | TEXT | 采集时间 |

#### instagram_users（Instagram用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT PK | 用户ID |
| username | TEXT | 用户名 |
| full_name | TEXT | 全名 |
| avatar | TEXT | 头像URL |
| biography | TEXT | 简介 |
| is_business_account | BOOLEAN | 是否商业账号 |
| category | TEXT | 账号类别 |
| follower_count | INTEGER | 粉丝数 |
| following_count | INTEGER | 关注数 |
| media_count | INTEGER | 帖子数 |
| collected_at | TEXT | 采集时间 |

---

### 2.8 X/Twitter

#### x_posts（X/Twitter帖子）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| tweet_id | TEXT PK | 推文ID(BigInt，字符串保精度) | id |
| conversation_id | TEXT | 会话ID | conversation_id |
| author_id | TEXT | 作者ID | author_id |
| author_username | TEXT | 作者用户名 | author/username |
| text | TEXT | 推文内容 | text |
| in_reply_to_user_id | TEXT | 回复的用户ID | in_reply_to_user_id |
| retweet_count | INTEGER | 转推数 | public_metrics.retweet_count |
| reply_count | INTEGER | 回复数 | public_metrics.reply_count |
| like_count | INTEGER | 点赞数 | public_metrics.like_count |
| quote_count | INTEGER | 引用数 | public_metrics.quote_count |
| bookmark_count | INTEGER | 书签数 | public_metrics.bookmark_count |
| impression_count | INTEGER | 展示数 | public_metrics.impression_count |
| context_annotations | TEXT(JSON) | 上下文注解 | context_annotations |
| referenced_tweets | TEXT(JSON) | 引用推文 | referenced_tweets |
| hashtag_list | TEXT(JSON) | 话题标签 | entities.hashtags |
| mention_list | TEXT(JSON) | @提及 | entities.mentions |
| created_at | TEXT | 发布时间(RFC3339) | created_at |
| url | TEXT | 推文URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### x_users（X/Twitter用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| user_id | TEXT PK | 用户ID |
| username | TEXT | 用户名(@handle) |
| name | TEXT | 显示名称 |
| description | TEXT | 简介 |
| avatar | TEXT | 头像URL |
| verified | BOOLEAN | 是否认证 |
| verified_type | TEXT | 认证类型(blue/business/government) |
| follower_count | INTEGER | 粉丝数 |
| following_count | INTEGER | 关注数 |
| tweet_count | INTEGER | 推文数 |
| listed_count | INTEGER | 被列入列表数 |
| location | TEXT | 位置 |
| created_at | TEXT | 账号创建时间 |
| collected_at | TEXT | 采集时间 |

---

### 2.9 Reddit

#### reddit_posts（Reddit帖子）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| post_id | TEXT PK | 帖子ID | id |
| subreddit | TEXT | 子版块 | subreddit |
| subreddit_id | TEXT | 子版块ID | subreddit_id |
| author | TEXT | 作者 | author |
| author_fullname | TEXT | 作者全名ID | author_fullname |
| title | TEXT | 标题 | title |
| selftext | TEXT | 正文内容 | selftext |
| url | TEXT | 链接URL | url |
| permalink | TEXT | 永久链接 | permalink |
| score | INTEGER | 得分(upvotes-downvotes) | score |
| upvote_ratio | REAL | 点赞比例 | upvote_ratio |
| num_comments | INTEGER | 评论数 | num_comments |
| num_crossposts | INTEGER | 交叉发布数 | num_crossposts |
| link_flair_text | TEXT | 链接标签 | link_flair_text |
| over_18 | BOOLEAN | NSFW标记 | over_18 |
| spoiler | BOOLEAN | 剧透标记 | spoiler |
| stickied | BOOLEAN | 置顶标记 | stickied |
| created_utc | REAL | 发布时间(Unix时间戳) | created_utc |
| collected_at | TEXT | 采集时间 | collected_at |

#### reddit_comments（Reddit评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| post_id | TEXT | 所属帖子ID |
| subreddit | TEXT | 子版块 |
| author | TEXT | 作者 |
| body | TEXT | 评论内容 |
| score | INTEGER | 得分 |
| depth | INTEGER | 评论层级深度 |
| parent_comment_id | TEXT | 父评论ID |
| created_utc | REAL | 发布时间 |
| collected_at | TEXT | 采集时间 |

#### reddit_subreddits（Reddit子版块）
| 字段 | 类型 | 说明 |
|------|------|------|
| subreddit_id | TEXT PK | 子版块ID |
| name | TEXT | 子版块名称 |
| display_name | TEXT | 显示名称 |
| description | TEXT | 描述 |
| subscriber_count | INTEGER | 订阅数 |
| active_user_count | INTEGER | 活跃用户数 |
| created_utc | REAL | 创建时间 |
| collected_at | TEXT | 采集时间 |

---

### 2.10 LinkedIn

#### linkedin_posts（LinkedIn帖子）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| post_id | TEXT PK | 帖子ID(URN) | id |
| author_id | TEXT | 作者ID(URN) | author |
| author_name | TEXT | 作者名称 | author_name |
| commentary | TEXT | 帖子正文 | commentary |
| article_url | TEXT | 文章链接 | content.article.source |
| image_url | TEXT | 图片URL | content.images |
| like_count | INTEGER | 点赞数 | likes.summary.total_count |
| comment_count | INTEGER | 评论数 | comments.summary.total_count |
| share_count | INTEGER | 分享数 | reshareSummary.primaryCount |
| impression_count | INTEGER | 展示数 | totalShareStatistics.impressionCount |
| created_at | TEXT | 发布时间 | createdAt |
| url | TEXT | 帖子URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### linkedin_users（LinkedIn用户）
| 字段 | 类型 | 说明 |
|------|------|------|
| profile_id | TEXT PK | 个人资料ID(URN) |
| vanity_name | TEXT | 自定义URL名称 |
| first_name | TEXT | 名 |
| last_name | TEXT | 姓 |
| headline | TEXT | 标题 |
| summary | TEXT | 简介 |
| avatar | TEXT | 头像URL |
| industry | TEXT | 行业 |
| company | TEXT | 当前公司 |
| job_title | TEXT | 职位 |
| follower_count | INTEGER | 关注者数 |
| connection_count | INTEGER | 人脉数 |
| location | TEXT | 位置 |
| collected_at | TEXT | 采集时间 |

---

### 2.11 GitHub

> GitHub按原生对象模型设计：Repositories / Issues / Pull Requests / Releases

#### github_repositories（GitHub仓库）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| repo_id | INTEGER PK | 仓库ID | id |
| name | TEXT | 仓库名 | name |
| full_name | TEXT | 完整名(owner/repo) | full_name |
| owner | TEXT | 所有者 | owner.login |
| owner_id | INTEGER | 所有者ID | owner.id |
| description | TEXT | 描述 | description |
| language | TEXT | 主要语言 | language |
| stargazers_count | INTEGER | Star数 | stargazers_count |
| forks_count | INTEGER | Fork数 | forks_count |
| watchers_count | INTEGER | Watch数 | watchers_count |
| open_issues_count | INTEGER | 开放Issue数 | open_issues_count |
| subscribers_count | INTEGER | 订阅数 | subscribers_count |
| topics | TEXT(JSON) | 主题标签 | topics |
| license | TEXT | 许可证 | license.spdx_id |
| default_branch | TEXT | 默认分支 | default_branch |
| homepage | TEXT | 主页 | homepage |
| is_fork | BOOLEAN | 是否Fork | fork |
| is_archived | BOOLEAN | 是否归档 | archived |
| created_at | TEXT | 创建时间 | created_at |
| updated_at | TEXT | 更新时间 | updated_at |
| pushed_at | TEXT | 最后推送时间 | pushed_at |
| collected_at | TEXT | 采集时间 | collected_at |

#### github_issues（GitHub Issues）
| 字段 | 类型 | 说明 |
|------|------|------|
| issue_id | INTEGER PK | Issue ID |
| issue_number | INTEGER | Issue编号 |
| repo_full_name | TEXT | 所属仓库 |
| title | TEXT | 标题 |
| body | TEXT | 正文 |
| state | TEXT | 状态(open/closed) |
| author | TEXT | 作者 |
| labels | TEXT(JSON) | 标签 |
| assignees | TEXT(JSON) | 经办人 |
| comments_count | INTEGER | 评论数 |
| is_pull_request | BOOLEAN | 是否PR |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| closed_at | TEXT | 关闭时间 |
| collected_at | TEXT | 采集时间 |

#### github_pull_requests（GitHub Pull Requests）
| 字段 | 类型 | 说明 |
|------|------|------|
| pr_id | INTEGER PK | PR ID |
| pr_number | INTEGER | PR编号 |
| repo_full_name | TEXT | 所属仓库 |
| title | TEXT | 标题 |
| body | TEXT | 正文 |
| state | TEXT | 状态(open/closed/merged) |
| author | TEXT | 作者 |
| head_branch | TEXT | 源分支 |
| base_branch | TEXT | 目标分支 |
| commits_count | INTEGER | 提交数 |
| additions | INTEGER | 新增行数 |
| deletions | INTEGER | 删除行数 |
| changed_files | INTEGER | 变更文件数 |
| comments_count | INTEGER | 评论数 |
| review_comments_count | INTEGER | 审查评论数 |
| labels | TEXT(JSON) | 标签 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |
| closed_at | TEXT | 关闭时间 |
| merged_at | TEXT | 合并时间 |
| collected_at | TEXT | 采集时间 |

#### github_releases（GitHub Releases）
| 字段 | 类型 | 说明 |
|------|------|------|
| release_id | INTEGER PK | Release ID |
| tag_name | TEXT | 标签名 |
| name | TEXT | 名称 |
| body | TEXT | 发布说明 |
| repo_full_name | TEXT | 所属仓库 |
| author | TEXT | 作者 |
| is_draft | BOOLEAN | 是否草稿 |
| is_prerelease | BOOLEAN | 是否预发布 |
| assets_count | INTEGER | 附件数 |
| download_count | INTEGER | 下载总数 |
| created_at | TEXT | 创建时间 |
| published_at | TEXT | 发布时间 |
| collected_at | TEXT | 采集时间 |

---

### 2.12 知乎 Zhihu

#### zhihu_answers（知乎回答）
| 字段 | 类型 | 说明 | 平台原生名 |
|------|------|------|-----------|
| answer_id | TEXT PK | 回答ID(BigInt，字符串保精度) | id |
| question_id | TEXT | 所属问题ID | question.id |
| question_title | TEXT | 问题标题 | question.title |
| author_id | TEXT | 作者ID(url_token) | author.url_token |
| author_name | TEXT | 作者名称 | author.name |
| content | TEXT | 回答内容(HTML) | content |
| excerpt | TEXT | 摘要 | excerpt |
| voteup_count | INTEGER | 赞同数 | voteup_count |
| thanks_count | INTEGER | 感谢数 | thanks_count |
| favlists_count | INTEGER | 收藏数 | favlists_count |
| comment_count | INTEGER | 评论数 | comment_count |
| is_collapsed | BOOLEAN | 是否折叠 | is_collapsed |
| created_time | INTEGER | 创建时间戳 | created_time |
| updated_time | INTEGER | 更新时间戳 | updated_time |
| url | TEXT | 回答URL | url |
| collected_at | TEXT | 采集时间 | collected_at |

#### zhihu_questions（知乎问题）
| 字段 | 类型 | 说明 |
|------|------|------|
| question_id | TEXT PK | 问题ID |
| title | TEXT | 问题标题 |
| detail | TEXT | 问题描述 |
| author_id | TEXT | 提问者ID |
| answer_count | INTEGER | 回答数 |
| follower_count | INTEGER | 关注数 |
| comment_count | INTEGER | 评论数 |
| topics | TEXT(JSON) | 话题标签 |
| created_time | INTEGER | 创建时间 |
| updated_time | INTEGER | 更新时间 |
| collected_at | TEXT | 采集时间 |

#### zhihu_articles（知乎文章）
| 字段 | 类型 | 说明 |
|------|------|------|
| article_id | TEXT PK | 文章ID |
| title | TEXT | 标题 |
| content | TEXT | 正文(HTML) |
| excerpt | TEXT | 摘要 |
| author_id | TEXT | 作者ID |
| author_name | TEXT | 作者名称 |
| voteup_count | INTEGER | 赞同数 |
| comment_count | INTEGER | 评论数 |
| created_time | INTEGER | 创建时间 |
| updated_time | INTEGER | 更新时间 |
| url | TEXT | 文章URL |
| collected_at | TEXT | 采集时间 |

#### zhihu_comments（知乎评论）
| 字段 | 类型 | 说明 |
|------|------|------|
| comment_id | TEXT PK | 评论ID |
| resource_id | TEXT | 所属资源ID(回答/文章/问题) |
| resource_type | TEXT | 资源类型(answer/article/question) |
| author_id | TEXT | 评论者ID |
| author_name | TEXT | 评论者名称 |
| content | TEXT | 评论内容 |
| vote_count | INTEGER | 点赞数 |
| reply_count | INTEGER | 回复数 |
| parent_comment_id | TEXT | 父评论ID |
| created_time | INTEGER | 创建时间 |
| collected_at | TEXT | 采集时间 |

---

## 3. Platform Normalized层（跨平台统一表）

### 3.1 platform_accounts（统一账号表）

| 字段 | 类型 | 说明 | 映射来源 |
|------|------|------|---------|
| id | INTEGER PK | 自增ID | 系统 |
| platform | TEXT | 平台canonical名 | normalize_platform() |
| platform_account_id | TEXT | 平台原生账号ID | xhs user_id / douyin sec_uid / bilibili mid / ... |
| username | TEXT | 用户名/handle | xhs nickname / douyin nickname / bilibili name / x username |
| display_name | TEXT | 显示名称 | 平台昵称 |
| avatar_url | TEXT | 头像URL | 平台avatar |
| bio | TEXT | 个人简介 | xhs desc / douyin signature / bilibili sign / x description |
| verified | BOOLEAN | 是否认证 | x verified / instagram is_business_account |
| verification_type | TEXT | 认证类型 | x verified_type / instagram category |
| account_type | TEXT | 账号类型(KOL/KOS/KOC/UGC/MEDIA/BRAND/OFFICIAL) | 业务层判定 |
| follower_count | INTEGER | 粉丝数 | 平台follower/fans |
| following_count | INTEGER | 关注数 | 平台following |
| content_count | INTEGER | 内容数 | 平台media_count/tweet_count/video_count |
| location | TEXT | 位置 | 平台location |
| country | TEXT | 国家 | youtube country |
| language | TEXT | 语言 | youtube default_language |
| website | TEXT | 个人网站 | 平台website |
| profile_url | TEXT | 主页URL | 平台profile URL |
| first_seen_at | TEXT | 首次采集时间 | 系统 |
| last_seen_at | TEXT | 最后采集时间 | 系统 |
| raw_data | TEXT(JSON) | 平台原生完整数据 | 保留可追溯 |

**唯一索引**：(platform, platform_account_id)

### 3.2 platform_contents（统一内容表）

| 字段 | 类型 | 说明 | 映射来源 |
|------|------|------|---------|
| id | INTEGER PK | 自增ID | 系统 |
| platform | TEXT | 平台canonical名 | normalize_platform() |
| platform_content_id | TEXT | 平台原生内容ID | xhs note_id / douyin aweme_id / bilibili bvid / x tweet_id / ... |
| content_type | TEXT | 内容类型(note/video/post/answer/article/media) | 平台type |
| author_id | TEXT | 作者平台账号ID | 映射platform_accounts.platform_account_id |
| author_name | TEXT | 作者名称 | 平台昵称 |
| title | TEXT | 标题 | 平台title |
| content | TEXT | 正文内容 | xhs desc / douyin desc / x text / reddit selftext |
| published_at | TEXT | 真实发布时间 | xhs time / douyin create_time / bilibili pubdate / x created_at |
| url | TEXT | 内容URL | build_content_url() |
| like_count | INTEGER | 点赞数(统一) | xhs liked_count / douyin digg_count / bilibili like / x like_count |
| comment_count | INTEGER | 评论数(统一) | 平台comment_count |
| share_count | INTEGER | 分享数(统一) | xhs share_count / douyin share_count / x retweet_count |
| collect_count | INTEGER | 收藏数(统一) | xhs collected_count / douyin collect_count / bilibili favorite |
| view_count | INTEGER | 播放/观看数(统一) | douyin play_count / bilibili view / youtube view_count |
| topic_list | TEXT(JSON) | 话题列表 | 平台tag_list/hashtag_list |
| hashtag_list | TEXT(JSON) | Hashtag列表 | 平台hashtags |
| mention_list | TEXT(JSON) | @提及列表 | 平台mentions |
| media_list | TEXT(JSON) | 媒体资源列表 | xhs image_list/video / instagram children |
| language | TEXT | 语言 | 平台language |
| location | TEXT | 地理位置 | 平台location |
| raw_data | TEXT(JSON) | 平台原生完整数据 | 保留可追溯 |
| first_collected_at | TEXT | 首次采集时间 | 系统 |
| last_collected_at | TEXT | 最后采集时间 | 系统 |
| collected_at | TEXT | 采集时间(兼容字段) | 系统 |

**唯一索引**：(platform, platform_content_id)

### 3.3 platform_comments（统一评论表）

| 字段 | 类型 | 说明 | 映射来源 |
|------|------|------|---------|
| id | INTEGER PK | 自增ID | 系统 |
| platform | TEXT | 平台canonical名 | normalize_platform() |
| comment_id | TEXT | 平台原生评论ID | xhs comment_id / douyin comment_id / bilibili rpid / ... |
| content_id | TEXT | 所属内容平台ID | 映射platform_contents.platform_content_id |
| parent_comment_id | TEXT | 父评论ID | 平台parent_comment_id |
| author_id | TEXT | 评论者平台账号ID | 平台user_id/mid |
| author_name | TEXT | 评论者名称 | 平台昵称 |
| content | TEXT | 评论内容 | 平台content/text/body |
| like_count | INTEGER | 点赞数(统一) | 平台like_count/digg_count |
| reply_count | INTEGER | 回复数 | 平台reply_count/rcount |
| created_at | TEXT | 评论发布时间 | 平台time/create_time/ctime |
| updated_at | TEXT | 评论更新时间 | 平台updated_at |
| location | TEXT | 位置 | 平台location |
| raw_data | TEXT(JSON) | 平台原生完整数据 | 保留可追溯 |
| collected_at | TEXT | 采集时间 | 系统 |

**唯一索引**：(platform, comment_id)

---

## 4. 采集与Evidence层

### 4.1 collection_runs（采集运行记录）

> 对应现有collection_logs，兼容映射。现有collection_logs保留，新数据写入collection_runs。

| 字段 | 类型 | 说明 |
|------|------|------|
| collection_run_id | TEXT PK | 采集运行ID(UUID) |
| platform | TEXT | 平台 |
| collector | TEXT | 采集器名称 |
| collector_version | TEXT | 采集器版本 |
| task_id | TEXT | 任务ID |
| keyword | TEXT | 搜索关键词 |
| started_at | TEXT | 开始时间 |
| finished_at | TEXT | 结束时间 |
| status | TEXT | 状态(SUCCESS/NO_NEW_DATA/RISK_WARNING/NEED_VERIFY/BLOCKED/SESSION_EXPIRED/COLLECT_ERROR/COOLING_DOWN) |
| requested_count | INTEGER | 请求数量 |
| collected_count | INTEGER | 采集数量 |
| new_count | INTEGER | 新增数量 |
| duplicate_count | INTEGER | 重复数量 |
| filtered_count | INTEGER | 过滤数量 |
| error_count | INTEGER | 错误数量 |
| error_code | TEXT | 错误码 |
| error_message | TEXT | 错误信息 |
| duration_ms | INTEGER | 耗时(毫秒) |

### 4.2 platform_evidence（平台证据链）

| 字段 | 类型 | 说明 |
|------|------|------|
| evidence_id | TEXT PK | 证据ID(UUID) |
| platform | TEXT | 平台 |
| content_id | TEXT | 内容ID |
| source_url | TEXT | 来源URL |
| source_type | TEXT | 来源类型(search/detail/comment/api/browser) |
| captured_at | TEXT | 捕获时间 |
| capture_method | TEXT | 捕获方法(playwright/cdp/api/rss) |
| raw_payload | TEXT(JSON) | 原始响应载荷 |
| screenshot | TEXT | 截图路径/URL |
| content_hash | TEXT | 内容哈希(SHA256) |
| collector_version | TEXT | 采集器版本 |
| confidence | REAL | 置信度(0-1) |

---

## 5. 业务层（ZBC Canonical Truth）

### 5.1 brands（品牌表，扩展现有）

| 字段 | 类型 | 说明 |
|------|------|------|
| brand_id | TEXT PK | 品牌ID |
| brand_name | TEXT | 品牌名称 |
| brand_alias | TEXT(JSON) | 品牌别名列表 |
| category | TEXT | 品类 |
| industry | TEXT | 行业 |
| parent_brand_id | TEXT | 父品牌ID |
| status | TEXT | 状态(active/inactive) |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 5.2 events（事件表，现有体系保留扩展）

| 字段 | 类型 | 说明 |
|------|------|------|
| event_id | TEXT PK | 事件ID |
| event_name | TEXT | 事件名称 |
| event_type | TEXT | 事件类型(marketing/propagation/opinion) |
| start_time | TEXT | 开始时间 |
| end_time | TEXT | 结束时间 |
| status | TEXT | 生命周期状态 |
| severity | TEXT | 严重程度 |
| source_count | INTEGER | 来源平台数 |
| content_count | INTEGER | 内容数 |
| growth_rate | REAL | 增长率 |
| confidence | REAL | 置信度 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 5.3 event_mentions（事件提及关联）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 自增ID |
| event_id | TEXT | 事件ID |
| platform | TEXT | 平台 |
| content_id | TEXT | 内容ID |
| relation_type | TEXT | 关系类型(trigger/derived/secondary/parallel) |
| confidence | REAL | 置信度 |
| matched_at | TEXT | 匹配时间 |

### 5.4 content_analysis（内容分析）

| 字段 | 类型 | 说明 |
|------|------|------|
| analysis_id | TEXT PK | 分析ID |
| platform | TEXT | 平台 |
| content_id | TEXT | 内容ID |
| sentiment | TEXT | 情绪(positive/neutral/negative) |
| sentiment_score | REAL | 情绪分值(-1到1) |
| emotion | TEXT | 情感标签 |
| risk_level | TEXT | 风险等级(low/medium/high/critical) |
| risk_score | REAL | 风险分值 |
| topic | TEXT | 主题分类 |
| intent | TEXT | 用户意图 |
| brand_relevance | REAL | 品牌相关度 |
| event_relevance | REAL | 事件相关度 |
| ai_model | TEXT | 使用的AI模型 |
| prompt_version | TEXT | Prompt版本 |
| confidence | REAL | 置信度 |
| analyzed_at | TEXT | 分析时间 |

### 5.5 note_review_history（人工复核历史，现有保留）

> 现有表结构保留，不做修改。

### 5.6 creators（创作者/传播主体表）

| 字段 | 类型 | 说明 |
|------|------|------|
| creator_id | TEXT PK | 创作者ID |
| platform | TEXT | 平台 |
| platform_account_id | TEXT | 平台账号ID(映射platform_accounts) |
| creator_type | TEXT | 主体类型(KOL/KOS/KOC/UGC/MEDIA/BRAND/OFFICIAL) |
| display_name | TEXT | 显示名称 |
| followers | INTEGER | 粉丝数 |
| engagement_rate | REAL | 互动率 |
| content_count | INTEGER | 内容数 |
| average_interaction | REAL | 平均互动量 |
| influence_score | REAL | 影响力分值 |
| brand_relevance | REAL | 品牌相关度 |
| category | TEXT | 内容类别 |
| location | TEXT | 位置 |
| verified | BOOLEAN | 是否认证 |
| first_seen_at | TEXT | 首次出现时间 |
| last_seen_at | TEXT | 最后出现时间 |

### 5.7 metric_snapshots（指标快照，现有表保留统一）

| 字段 | 类型 | 说明 |
|------|------|------|
| metric_id | TEXT PK | 指标ID |
| platform | TEXT | 平台 |
| object_type | TEXT | 对象类型(content/account/event/brand) |
| object_id | TEXT | 对象ID |
| metric_name | TEXT | 指标名称 |
| metric_value | REAL | 指标值 |
| metric_unit | TEXT | 指标单位 |
| period_start | TEXT | 周期开始 |
| period_end | TEXT | 周期结束 |
| snapshot_at | TEXT | 快照时间 |
| source | TEXT | 数据来源 |
| confidence | REAL | 置信度 |

---

## 6. 互动量统一计算公式

```
engagement = like_count + collect_count + comment_count + share_count
engagement_rate = engagement / follower_count (当follower_count > 0时)
```

- 与现有笔记报告计算逻辑一致
- view_count/play_count不计入互动量（属于曝光指标）
- 各平台原生指标名保留在Raw层，Normalized层统一映射后计算

---

## 7. 平台字段映射速查表

### 点赞数映射（Raw → Normalized like_count）
| 平台 | Raw字段名 |
|------|----------|
| 小红书 | liked_count |
| 抖音 | digg_count |
| B站 | like |
| YouTube | like_count |
| TikTok | digg_count |
| Instagram | like_count |
| X/Twitter | like_count |
| Reddit | score(upvotes-downvotes) |
| 知乎 | voteup_count |

### 收藏数映射（Raw → Normalized collect_count）
| 平台 | Raw字段名 |
|------|----------|
| 小红书 | collected_count |
| 抖音 | collect_count |
| B站 | favorite |
| YouTube | favorite_count |
| TikTok | collect_count |
| Instagram | (无原生收藏，saved_count可选) |

### 播放/观看数映射（Raw → Normalized view_count）
| 平台 | Raw字段名 |
|------|----------|
| 抖音 | play_count |
| B站 | view |
| YouTube | view_count |
| TikTok | play_count |

### 内容ID映射（Raw → Normalized platform_content_id）
| 平台 | Raw字段名 | 精度要求 |
|------|----------|---------|
| 小红书 | note_id | 字符串 |
| 抖音 | aweme_id | 19位BigInt→字符串 |
| B站 | bvid | 字符串(Base58) |
| YouTube | video_id | 字符串 |
| TikTok | video_id | 字符串 |
| Instagram | media_id | BigInt→字符串 |
| X/Twitter | tweet_id | BigInt→字符串 |
| Reddit | post_id | 字符串 |
| 知乎 | answer_id | BigInt→字符串 |

---

## 8. 数据质量红线

1. **100%精准**：禁止估算/近似/假数据/默认值填充
2. **缺失显式**：NULL/unknown/missing/unavailable，禁止静默0
3. **时间分离**：published_at与captured_at必须分离
4. **原生保留**：Raw层平台原生字段名永远保留，不删除不改名
5. **可追溯**：所有Normalized/Canonical数据必须能回溯到Raw记录(raw_data字段)
6. **主体过滤**：SUBJECT_WORDS/SUBJECT_EXCLUDE_WORDS/subject_hit()不得修改
7. **AI增强**：AI只做增强，不做业务最终真值
8. **不伪造**：视频号等不存在公开字段标unavailable，不编造
