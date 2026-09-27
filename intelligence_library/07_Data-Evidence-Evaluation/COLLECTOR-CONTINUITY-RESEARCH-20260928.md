# 采集维度与持续更新研究

2026-09-28。状态：研究与采用记录，能力验收以对应源码、运行和用户结果为准。

## 用户要求与执行边界

用户要求没有 Cookie 时仍努力达到既定采集维度，避免用户账户承担采集风险。
因此验收必须逐平台、逐字段比较有会话与无会话的真实结果，不能把“抓到网页”
当作内容、作者、评论回复、互动、媒体、时间、关系和历史指标全部等价。
无法公开获得的字段保留缺口与替代来源；不声称登录专属数据可无损匿名获取，
不通过验证码绕过、违规切换个人账户或规避封禁来补数字。

现有国家目录继续作为实体身份和经营关系基线。官网陈述不能替代消费者、
媒体社交或创作者情报。CTH 场内品牌关系仍是 TENANT_OF，不能把品牌全球内容
自动归为广州太古汇场内反馈。BMP BrandFocus 保留独立业务语义。

端用户 MANUAL 默认，AUTO 显式开启。用户已授权的 prelaunch/global 公开基线
单独配置可停用、可恢复的到期维护，沿既有 Scheduler/Collector/Evidence/DB，
不能隐式激活私人会话或全部平台自动采集。

## 当前执行及原规划入口

- 原规划：`00-GOVERNANCE/SHARED-CAPABILITY-COLLECTOR-CLOSED-LOOP-V1.md`。
- 领域研究：`intelligence_library/02_BMP研究/BMP-DATA-INTELLIGENCE-ADOPTION-2026-09-27.md`。
- 历史字段规划：`intelligence_library/02_BMP研究/DATA_AND_CONTENT/FINAL_DATA_PIPELINE_KOS_KOC_UGC_IMPLEMENTATION_DIRECTIVE.md`。
- 导航仍用 `locate_capability_context.py`；本记录不替代上述原文和当前 owner。

| 当前可执行切片 | 现有 owner | 执行动作与验收 |
|---|---|---|
| 短正文、原文语言、页面身份 | SYSTEM Collector/PublicHttpAdapter | 已发布 86382707，42 项回归；真实韩国网页提取核验，未冒充入库/E2E |
| HK 专用本地采集入口 | SYSTEM Collector/Browser 与既有 account allowlist | 修复旧 loopback 全拒绝；连接前限定专用端口/profile，工作前核验批准身份；候选待真实运行 |
| 原生字段与历史指标 | Shared platform_content + Collector | 普通平台路径接入现有 owner；缺失不写零、保留源 ID、签名 Evidence、精确 scope 与更新历史 |
| 每日到期维护 | 既有 scheduling/decision store + Collector | versioned source/scope/cadence，durable claim、失败退避、重开一致，配置后真实两次运行与未来周期 |
| Instagram 缺失互动 | 既有 Instagram adapter | 保留显式 0，未提供/无效值 UNKNOWN，不能初始化成 0；隔离候选执行中 |
| 前端与内容能力 | 既有 Experience / Shared Content & Creation | 当前任务继续；前端 AIGC/3D 是视觉素材与效果，不据此新增内容生成功能 |

## GitHub 与官方资料核验

访问日期均为 2026-09-28。下面是适配候选，未安装新依赖、未宣称最佳工具或上线能力。
开源代码许可不等于平台数据许可；工具列出支持平台也不证明每字段匿名可得。

| 来源及版本 | 维护/许可 | 采用判断 |
|---|---|---|
| [F2](https://github.com/Johnserf-Seed/f2)，`c2c52a4da0cfe0ce646cc836738d7f1aca1308f8`，开发分支 `v0.0.1.8-pw3` | 非归档；最近 push 2026-09-26；Apache-2.0 | DEFER 接依赖。研究现有平台字段与版本变化；README 的 Cookie 配置和开发分支提示不支持“全平台免 Cookie 等价”结论。先修当前 adapter，不替换整个运行时 |
| [Instaloader](https://github.com/instaloader/instaloader)，`7efc78de12e02feb1794b71125a48e66250f0db0` | 非归档；最近 push 2026-09-06；MIT | ADAPT 增量截止点、可恢复采集与频率状态的思路到现有 Scheduler。公开/私密内容访问不同，session 不是全有或全无开关 |
| [Instaloader 故障文档](https://instaloader.github.io/troubleshooting.html) | 官方维护者文档，滚动版本 | ADAPT 跨运行保留请求频率状态，避免反复重启反而触发 429；不以代理池或频繁重登承诺安全 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp)，`caf63903a1f59e1765bfb390df2d89f47ae7a310` | 非归档；最近 push 2026-09-27；仓库标识 Unlicense，分发依赖需单独核验 | DEFER 接入。评论/metadata 与媒体下载、Cookie 选项分开评估，不能凭支持列表扩展当前 YouTube 产品入口或绕过来源策略 |
| [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)，`380b426000aac3d612837ed72c99808347dc94c9` | 非归档；最近 push 2026-09-19；GitHub license=NOASSERTION；README 明示研究学习用途及禁止商业用途 | REJECT 直接并入产品依赖/复制源码。仅研究字段与失败模式，其保存登录态浏览器方案并不是匿名等价证明 |
| [TikTok Research Tools](https://developers.tiktok.com/docs/en/about-research-api) | 官方 API；有研究资格要求 | DEFER：不能把非营利研究申请入口当序境商业产品可直接使用的无认证接口 |
| [YouTube comments.list](https://developers.google.com/youtube/v3/docs/comments/list) | 官方 API 文档，2026-09-14 更新；文档 CC BY 4.0，示例 Apache-2.0 | 保留公开评论/回复可用入口的研究，资格/配置未完成时不声明运行；403 是权限不可用，不是评论数 0 |

Meta Instagram 官方文档本次返回 429；没有将抓取失败当作接口能力不存在。

## 维度等价与持续运行验收

每个平台记录：源原生 ID、内容/正文、作者、发布时间、采集时间、评论/回复、
平台实际提供的互动、话题/标签/Mention、媒体、地区/语言，以及来源缺口。
同一公开记录分别检验已授权会话与匿名/官方公开入口，记录字段级 SAME、
PARTIAL、UNAVAILABLE，不把不同帖子或统计时间混作等价对照。

落库沿 Raw → Evidence → Canonical → exact CTH/BMP scope；变更才增加观察，
首次采集时间与发布时间不被刷新覆盖。重复、到期、失败、重启、恢复都使用
当前真实输入验证。真正未来周期尚未执行前 OPERATING 保持 NO。

## 已接收的能力原文与适配

用户指定的 `能力.docx` 已于 2026-09-28 通过共享只读文件流成功读取，
46,222 bytes，SHA-256 `b5706a06aec535a5de25fcbf10033f3152a7ea2514df7cdfdab897d9523c4e45`。
最初的云占位/文件占用错误已经解决，不再作为阻塞。
34 个章节、910 个非空段落全部保存在
`intelligence_library/01_序境产品研究/CAPABILITY-AUDIT-SOURCE-20260928.md`，
原段落序号保留；旧描述与当前执行的逐节映射位于同目录
`CAPABILITY-ADOPTION-20260928.md`。原文是研究输入，不覆盖当前源码和最新产品决策。

香港 RedNote 实际会话已通过既有“我”入口核对；缺少旧身份 Cookie 并不等于会话失效。
身份校验候选保留准确账号、官方域名和已有会话要求，实际采集与入库验收仍独立进行。
本资料记录能力范围和采用判断，不证明所有能力已完成。
