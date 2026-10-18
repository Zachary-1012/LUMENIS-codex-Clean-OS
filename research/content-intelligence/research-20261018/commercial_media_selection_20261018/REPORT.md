# 序境免费商用媒体选型：许可已明确项、替代项与真实接入缺口

研究日期：2026-10-18 UTC。仅研究及交接；未改产品代码、数据库或运行环境，未安装、注册、购买、读取密钥、上传本人声音或执行第三方代码。免费指没有模型/素材许可费及第三方推理 API 订阅要求，不代表算力、存储、电力免费。本文为基于公开许可的工程选型，不提供无侵权担保。

## 一、直接答案与对旧报告的修正

已经找到了免费可商用路线。不能把“尚未接入或未实测”“尚未拿到本人声音样本”“第三方私有格式不通用”混写成“商业许可都还缺”。建议确定以下主线：

1. 音乐短句与音效：Kenney 两个已下载、逐包有 CC0 文件的包；可作为产品内置素材候选。
2. 乐器：Meta-open-sound 三种 CC0 乐器采样；适合作曲素材，不冒充完整歌曲或已经有采样宿主。
3. 长配乐：新增 Kevin MacLeod《Carefree》官方曲目页 CC BY 4.0 候选，接受自动署名和改编标记即可免费商用；音频尚未下载核 hash/听测，不冒充交付完毕。
4. 转场：优先复用已存在 FFmpeg 滤镜；GLSL 候选限定已逐文件核过的 fade、InvertedPageCurl、StereoViewer，分别保留 MIT/BSD 条件。
5. 播客：本人授权音轨＋上述音乐＋现有混音/ducking/响度链，不绑定第三方 API；第一阶段不要求通用原生插件宿主。
6. 本人声音：手机原始录音和准确文本，在产品外使用 Qwen3-TTS Base 制作可复用条件包，再接入产品。明确免费商业基础许可；实际格式合同、环境锁、声样和端到端验收尚未完成。没有证实“现成 iPhone App 直接导出通用包”这件事，不能偷换成已经满足。

这些明确许可证不需要用户重新逐项批准才算允许商用。许可证条件应由研发在发行物中履行。真正需要用户决定的是未明确授权的本人默认声线分发范围、外传、费用、账号权限，以及具体产品修改。用户同意研究也不意味着允许修改产品。

## 二、重要新增证据：Qwen 权重许可并非未知

原模型报告发现 HF 模型仓库独立 LICENSE 路径404，这是文件存在性的事实，但不足以得出商业授权不明。

Qwen 团队论文固定版本 [arXiv:2601.15621v1](https://arxiv.org/abs/2601.15621v1) 的摘要明确说明 tokenizer 和模型均按 Apache 2.0 发布。与官方固定模型卡的 license: apache-2.0、固定官方代码 LICENSE 一起形成独立交叉证据。论文自身版权许可与其中陈述的模型许可是两个对象，不能混淆。

固定身份沿用原研究，不改选最新版：
- 代码：[022e286b98fbec7e1e916cb940cdf532cd9f488e](https://github.com/QwenLM/Qwen3-TTS/tree/022e286b98fbec7e1e916cb940cdf532cd9f488e)。
- Base：[Qwen3-TTS-12Hz-0.6B-Base@5d83992436eae1d760afd27aff78a71d676296fc](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/blob/5d83992436eae1d760afd27aff78a71d676296fc/README.md)。
- Tokenizer：[Qwen3-TTS-Tokenizer-12Hz@7dd38ad4e9bad454aae9cd937d0cd577604fe229](https://huggingface.co/Qwen/Qwen3-TTS-Tokenizer-12Hz/blob/7dd38ad4e9bad454aae9cd937d0cd577604fe229/README.md)。

决定：基础代码/模型许可选型通过，列入免费本地优先路线；不再要求用户为“找不到同名 LICENSE 文件”重复许可审批。按 [Apache 2.0 §4](https://www.apache.org/licenses/LICENSE-2.0) 分发时附许可、保留适用通知、标记修改并保留存在的 NOTICE；不得声称官方背书。

尚未由此证明：上游五百万小时语料逐项可再分发、所有第三方依赖许可闭包、所有生成音频保证无第三方权利、手机运行速度、实际声音相似度、产品已支持。训练数据未公开的权利链审计与现有模型明确的使用许可应分列，不能反向否定已公开许可，也不能把模型许可借给训练数据。

## 三、逐对象选型矩阵

| 对象/固定版本 | 代码/权重/数据层 | 输出与商用 | 随产品再分发/署名 | 决定与未测边界 |
|---|---|---|---|---|
| Kenney Music Jingles v1.0，85短句 | 音频素材 CC0，不涉及模型 | 可商业剪辑、播客片头片尾 | 可分发素材；不强制署名；保留来源利于追溯 | ADAPT。不是长曲库。已下载旧包，不声称本轮重新听审 |
| Kenney Impact Sounds v1.0，130音效 | 音频素材 CC0 | 可商业拟音与编辑 | 同上，不使用 Kenney logo 暗示背书 | ADAPT。真实节目听感未测 |
| Meta-open-sound@e2ff154845994fe4135becc4d5b857c19f172784 | 采样/元数据 CC0 | 可编曲/混音 | 可分发采样；无署名义务 | ADAPT 素材。钢琴352/尼龙348/钢弦375，不是现成配乐、宿主未验 |
| Carefree，ISRC USUAN1400037 | 作者官方页声明 CC BY 4.0 | 可商业同步、剪辑、混音 | 可再分发，但保留作者、来源、许可、改编提示，不额外限制该素材许可权利 | SELECT_PENDING_ASSET。曲目许可候选明确，文件下载/身份/听测未完成 |
| GL fade@c06c4905958446b7da2d121b12942495e18c99c0 | 单 shader MIT | 渲染视频可商业使用，视频素材另核 | 软件副本保留版权及许可 | ADAPT_CODE，产品适配未测 |
| GL InvertedPageCurl，同提交 | 单 shader BSD-3-Clause | 同上 | 保留规定通知，不用作者名背书 | ADAPT_CODE，不能与根MIT混写 |
| GL StereoViewer，同提交 | 单 shader BSD-2-Clause | 同上 | 保留规定通知 | ADAPT_CODE，未验四端GLSL兼容 |
| Airwindows DeBess@5043ff620c2418cba9137196990753fc89d0f829 | DSP源码 MIT；读取的WinVST外壳依赖audioeffectx.h | 可以研究/按MIT适配算法 | DSP需通知；不能据此批准VST2 SDK及完整二进制 | SELECT_DSP_ONLY，暂不分发该WinVST成品 |
| CLAP@a47f6badb49d948fd009998f28309cdab78979c9（1.2.10） | 接口代码MIT；每插件独立许可 | 接口可商业集成 | 保留MIT；插件/宿主依赖另核 | DEFER_HOST，不作为第一期前置 |
| 现存 FFmpeg 7.1.5 构建 | 自报 enable-gpl 与libx264，非LGPL-only | 商业运行并非一律禁止；媒体输入权利另核 | 实际发行按GPL及依赖义务，不能静默包装成闭源LGPL-only | REUSE_RUNTIME_DESIGN，发行构建待专门核验 |
| Qwen Base＋tokenizer，以上固定身份 | 代码Apache2；模型与tokenizer官方Apache2；训练原始数据不同对象 | 可选商业合成；内容/本人声音授权独立 | 模型分发履行Apache2；本人音色包分发还需明确声音授权 | ADAPT_DESIGN，未下载大权重/执行 |
| VoiceNPC .voicenpc | App私有格式；官网仅证明同App导入 | 不因Qwen开源推定App文件跨引擎/OEM许可 | 未取得明确第三方引擎及产品默认包授权 | 不设为产品主线；用户可保留原始录音，私有包只作待验输入 |
| Apple Personal Voice | Apple功能限定本人个人非商业 | 不满足商业默认声线 | 不可作为免费商业产品声音包 | REPLACE，以本人录音＋Qwen替代 |
| ElevenLabs免费路线 | 服务条款＋账户voice_id | 原研究已确认免费非商业，且clone不可导出独立模型 | 无法形成无API绑定的免费包 | EXCLUDE_FROM_PRIMARY，不购买不注册 |
| Pixabay普通Content License素材 | 网站素材许可，不是CC0的通用替身 | 可用于符合条件的新创意成片 | 禁止standalone素材分发，不能整包做内置素材库 | USER_IMPORT_ONLY_POLICY。不是法规说只能用户导入，而是产品保守选型；逐件保留来源与许可 |

证据：Kenney [官方问答](https://kenney.nl/support)、[Music Jingles](https://kenney.nl/assets/music-jingles)、[Impact Sounds](https://kenney.nl/assets/impact-sounds)及两包实际 License.txt；[Meta固定仓库](https://github.com/facebookincubator/Meta-open-sound/tree/e2ff154845994fe4135becc4d5b857c19f172784)；[GL固定仓库](https://github.com/gl-transitions/gl-transitions/tree/c06c4905958446b7da2d121b12942495e18c99c0)；[Airwindows固定仓库](https://github.com/airwindows/airwindows/tree/5043ff620c2418cba9137196990753fc89d0f829)；[CLAP固定仓库](https://github.com/free-audio/clap/tree/a47f6badb49d948fd009998f28309cdab78979c9)；[FFmpeg官方法律说明](https://ffmpeg.org/legal.html)；[Pixabay完整条款§5](https://pixabay.com/service/terms/)。旧报告内包hash与逐文件hash原样保留，不重新制造实测。

《Carefree》：官方作者站点搜索可读结果完整返回曲名、作者、ISRC、3:25、96 BPM与CC BY 4.0。链接：[官方曲目](https://incompetech.com/music/royalty-free/index.html?isrc=USUAN1400037&lt=)。普通直接打开为动态空壳，remote子域直接打开超时；不把搜索读取当音频已下载。需交付前固定实际音频hash和曲目许可快照。CC BY 4.0的商业再分发、改编和署名要求来自[许可全文§2–3](https://creativecommons.org/licenses/by/4.0/legalcode.en)。建议字幕/节目说明及随包credits记录作者、曲名、源URL、许可链接，并据实际记录裁剪/淡化/混音。不得预先谎称进行了尚未发生的编辑。

## 四、外部手机到本人声音包的实际路线

选定架构是“手机外部采集 → 受控外部转换 → 产品导入”，不是在序境新建录音App。

- 输入A：本人用已有手机录音功能自行生成原始录音＋准确逐字文本。研究不读取设备或代录，也不外传；去掉第三方背景音乐和其他人讲话。
- 处理B：外部Qwen固定Base runtime生成ref_code、ref_spk_embedding及模式/参考文本等条件。已有官方create_voice_clone_prompt支持复用，避免把条件提取误称完整模型训练。
- 输出C：未来实现可用受限JSON＋安全张量格式；绑定schema版本、基础模型commit及权重hash、tokenizer实际hash、采样率、形状、参考数据保留策略。格式是待实现交接设计，不是现有通用标准。
- 接入D：序境只验证和导入匹配包，经现有Gateway/媒体Owner输出。版本不匹配拒绝，不因tensor同shape就默认可替换。
- 使用E：离线播客与实时交互分别验收。普通导出WAV只能播放已经生成的台词，不能承担任意新文字合成；voice_id也不是本地模型。

严格区分两种“手机生成”：手机录音后在外部电脑提取，是当前可控设计；只靠现成iPhone App生成通用可移植包，尚无经核验成品。用户若坚持完全手机完成，保留具体缺口而不假装Qwen Python参考实现已经能在iPhone直接执行。VoiceNPC官网验证到其自身App共享，未证实产品加载，因此不建议以购买Pro解锁一个未证明存在的兼容路径。

个人声线可作为自己私用、商业播客成片、服务端全体用户默认声线、客户端可复用包四种范围，不能自动互相包含。仅本人自愿授权；公开分发可复用包后难以撤回所有副本。具体默认声音授权仍需以用户已给范围为准，不能靠素材开源替代本人决定。

Qwen依赖与现有20B配方的transformers版本存在固定等式冲突。选独立runtime/进程设计；不升级原20B环境。本轮没有实施这一拆分。

## 五、平台使用条款与软件许可单列

MIT/Apache2采集器只授权该软件代码，不授予网站账号、平台API、他人帖子、图片、视频、评论的全部使用权。免费API也可能要求应用注册、账户、限流、删除刷新；本人账号授权不能替第三方作者授予素材再分发权。用户不需要替平台批准者签一张“万能商业许可”，也不能由反复问用户消除平台限制。

- Bluesky：沿旧固定词典和实现证据可研究公开有界查询。其[ToS §3](https://bsky.social/about/support/tos)保留用户内容所有权；授给Bluesky的服务许可不等于授给序境无限素材/训练/客户导出许可。不能写“全面禁商业”，也不能写“免费公开即全用途”。软件、查询资格、用途/保留/再利用分别验收。
- YouTube：官方[Developer Policies §III.G](https://developers.google.com/youtube/terms/developer-policies)允许符合条款的商业API客户端，因而“商业平台用法一律未获准”也过宽。但§III.E.6禁止API客户端抓取YouTube/Google应用或获取抓取数据；音视频拆分、数据保留刷新和用途限制各自有效。不开API路线不能用开源爬虫绕开。当前严格“无第三方API绑定”主线应将此列为受限独立适配，不作为离线媒体能力依赖。
- 其他平台：沿原平台矩阵的未闭合同，不将本次两例扩写成22平台全条款已核。对小红书/知乎/贴吧/视频号等尚未证实官方通用读取用途者，推荐保留用户合法持有材料的导入能力，关闭未核自动采集承诺，而不是为了“全平台”退回不明爬虫。

替代思路是从官方CC0/CC BY素材及用户自有来源构建媒体功能，使音乐、播客、声音和转场不等待社交平台采集许可。平台分析可独立逐平台推进。平台条款与用户对产品修改的授权也是两个不同层次。

## 六、最小交付验收清单（全部技术新增项未执行）

1. 发行清单：每文件有来源、固定版本/内容hash、许可范围和通知；验证CC0音频、CC BY曲目、MIT/BSD源码、Apache权重分别归档。缺失单项不阻塞已明确的其他项。
2. CC BY导出：项目保存→冷开→播客/视频导出仍能生成作者/来源/许可/实际改编说明。无法保证署名链时先不内置该曲，使用CC0短句，不偷偷忽略条件。
3. 素材安全：大小、magic、解码、路径和hash核验；zip不执行。素材包不夹原生插件、脚本或模型。现有rights_state=unknown不能由外置清单偷偷改成已授权，相关合同变更需明确实施授权。
4. 后期：三种固定FFmpeg转场的旧合成探针仅证明滤镜可执行；实际时间线帧数、音轨、字幕、取消、重开、失败不覆盖旧输出仍需产品验收。
5. 播客：本人明确授权真实讲话样本、片头片尾、音乐ducking、爆音与齿音、长节目、编码后响度/true peak、主观可懂度。目标值按交付渠道确定；不拿正弦代替人声测试。
6. 声音包：离线转换往返、模型/tokenizer错误拒绝、安全张量而非pickle、跨设备重开、中英韩专名数字、长文本、同意撤回、删除/替换、失败不冒用别的声音。
7. 实时：端到端首包、停顿、打断、取消、恢复、并发和显存实测；论文97ms不作产品SLA。
8. 发行构建：FFmpeg实际flags和来源/对应源码、各依赖许可和通知；原生插件不得因MIT标题就自动执行。第一期仅固定可信滤镜，无需等待CLAP通用宿主。
9. 平台：每平台固定用途、字段、保留、导出、删除同步和错误合同；403/429不切身份规避；无资格时明确不支持。
10. 授权边界：本报告选型不是执行授权；只有用户明确要求具体修改时才进入对应代码/数据库/环境修改。

## 七、证据与复用记录

复用并实读三组原报告：voice_postproduction_research_20261018/mobile_voice/report.md；postproduction/REVIEW_PLAN_ZH.md及许可/少量源码；model_dependency_gap_research_20261018/REPORT.md；platform_evidence_gap_research_20261018/01_REPORT.md。它们的测试时间、固定hash、未测项保留，不宣称本轮重跑。

新增网页阅读：Qwen论文v1、官方模型卡、Apache2全文、Kenney支持页、VoiceNPC首页、CC0说明、CC BY4全文、Carefree官方搜索可读结果、Pixabay完整条款、Bluesky ToS、YouTube开发政策。NEW_SOURCES.json保存本轮独立下载成功/失败及hash；网页工具成功不代表独立下载成功。VoiceNPC猜测terms路径无法访问；FreePD超时；不采用未读许可。没有读取第三方博客作为许可依据。

停止点：免费商用主路线与取舍已明确；保留具体技术与交付验收，不再用笼统“待许可”挡住所有研究成果。
