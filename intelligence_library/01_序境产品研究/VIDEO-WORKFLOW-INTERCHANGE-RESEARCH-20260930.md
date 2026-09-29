# 视频工作流与工程交换研究 — 2026-09-30

状态：`RESEARCH_REVIEWED / IMPLEMENTATION_REORDERED`。序境12已核对现有 owner 与本研究的格式、时间、连接关系和适配器限制；这是研究输入，不是实现、宿主往返验收或内容板块闭环声明。

主控采用决定：保留第 6 节交换损失预检为后续工程交换子批的必要内容，暂不单独优先开发。当前 J5 冻结范围内，TimedOverlay 已可存储但 renderer 全部拒绝，字幕无法进入成片；下一实施先沿现有 FFmpeg renderer 验证并补齐安全的字幕/文本成片路径。此排序推进实际可交付能力，工程格式、磁性连接、代理预览和插件/宿主的要求均保留在现有总方案第 10 节；没有撤销或缩减。

研究入口：`bdd524509418229ecdd49ae08e420d2b06ece776`；研究期间协调方继续发布，复核 HEAD 为 `cfbc70ceec21eb381610ec278eb0be931e531906`。只新增本文，不改 App、Timeline、renderer、Core、配置或生产 DB，不暂存、提交或推送。所有外部来源访问日期均为 **2026-09-30**。

## 1. 结论与范围

最值得借鉴的是：素材浏览与成片编辑分开、快速预览不破坏当前编辑位置、联动关系明确、工程交换显式说明损失。不能把 FCP/Premiere 的完整界面或专有实现搬成序境的新产品架构。

研究交回时唯一建议的下一实现 Batch 是 **现有 Timeline 内的工程交换损失预检**，核心新增代码不超过 150 行，详见第 6 节；主控现已按页首决定调整顺序。现在不安装 OTIO、不制作原生 `.prproj` / `.aep`、不同时接入多个交换框架。

视频制作、音频优先的播客制作、通用内容创作仍是三个独立工作流；只在已有 Shared Content & Creation、Artifact、Permission 等 owner 内复用能力。完整 NLE、外部宿主与工程交换不得反过来阻塞当前手动编辑、导出、回读的验收。原有 12 个视频仍是 12 个独立学习/验证案例；本文不宣称已经重新剪辑或证明创作质量提高。

## 2. 先纠正文件格式与宿主边界

| 名称 | 实际意义 | 对序境的含义 |
| --- | --- | --- |
| Premiere `.prproj` | Premiere 原生项目；官方明确 Windows/macOS 间可用，媒体仍需可定位。[D1] | 不是 `.aep`；跨平台文件不等于第三方插件、字体和效果在另一机器也可用。 |
| After Effects `.aep` / `.aepx` | `.aep` 是二进制工程，`.aepx` 是 XML 工程；后者仍有二进制编码内容，不是通用剪辑交换标准。[D2] | 不把生成任意 XML 称为生成 AE 工程；不承诺无 Adobe 宿主即可完整渲染。 |
| Premiere 的 Final Cut Pro XML | 当前官方导出说明针对 FCP7 或更早版本；效果和音频参数可能损失，需检查转换日志。[D3] | 与现代 FCPXML 分开命名、版本化、验证。OTIO 的 `fcp_xml` 不是 `fcpx_xml`。 |
| 现代 FCPXML | 描述媒体、编辑决策与元数据；不是原生 FCP library 的完整替代。[A3][A4] | `.fcpxml` 与 `.fcpxmld` bundle 都要区别处理。Apple 用户指南说明 1.10 及以上导出为 bundle。 |
| `.otio` | 编辑结构、时间范围和媒体引用的交换表示；不是音视频内容本身，也不代替现有 renderer。[O1] | 可作为将来边界适配层，不能成为第二个 Timeline、媒体库或 Artifact owner。 |

Adobe 当前 FCPX 迁移文档仍要求先转换 `.fcpxml` 再导入；其中的转换器属于独立产品，本轮没有购买、安装或验证。[D4] Adobe 对转换结果的说明列出音量/声像与淡化的部分映射，也列出转场参数丢失、变速曲线被平均等限制；**这不能反推 OTIO 社区适配器同样实现了这些能力**。[D5]

文档版本注意：本次 Apple 用户指南版本选择器包含 FCP for Mac 12.3；开发者 DTD 页面正文仍描述 **1.10**，不能把该旧正文误报为当前软件的最高格式版本。具体宿主、DTD、导入/导出 profile 必须成对锁定，DTD 校验成功仍不保证宿主成功导入。[A4][A6]

## 3. 操作原则：可适配，不复制产品

| 研究对象与官方事实 | 已有序境基础 / 缺口 | 决策与验收要求 |
| --- | --- | --- |
| FCP 磁性时间线：主故事线插入/修剪/移动时联动；连接片段跟随父片段；Position 操作可保留空隙或覆盖。[A1] | `Timeline._reflow/reorder/delete` 已有本视频轨的连续重排；没有连接片段锚点图，独立音轨不会因此自动跟随。 | **ADAPT 原则，连接语义 DEFER 至现有 J5**。必须先确定移动/删除/修剪时 BGM、旁白、字幕是跟随还是固定；不能把一次 ripple 改名为完整磁性时间线。 |
| FCP browser 与 timeline 都能预览；playhead 保持当前位置，skimmer 随指针临时预览；FCP 还定义二者同时存在时的编辑优先位置。[A2] | 复用已有素材/预览/Timeline 入口；本批不触碰并行开发中的 App，不声称这些交互已实现。 | **ADAPT 原则**：素材范围选择与成片时间位置是两个坐标域；临时预览与正式播放头分离，悬停不改 Timeline/undo/版本。触屏、键盘要有等价操作；明确哪一位置将被用于切割，不能隐式猜测。 |
| Premiere 桌面工程支持 Windows/macOS；插件入口包含 UXP、C++ SDK、CEP；UXP 入门要求 Premiere 25.6+、UDT 2.2+。[D1][D6][D7] | 序境现有跨端 App/Core 继续为主；没有证据证明任意 Adobe 插件能在序境运行。 | **ADAPT 宿主适配思想，DEFER SDK 接入**。插件能力、平台二进制、许可和版本分别探测；不建立平行插件平台，不承诺 Linux/Web 原生 Adobe 插件兼容。 |
| Dynamic Link 在 Adobe 宿主间共享内容且无需中间渲染；主版本不一致时不能工作。[D8] | Artifact 可以将来记录经授权的外部工程关联/替代渲染；现有 renderer 不执行 AE 合成。 | **DEFER 真实宿主集成；REJECT 专有实现照搬**。离线、版本不符、缺插件必须显式失败或使用用户确认的烘焙替代；不能把 OTIO/XML 描述称为 Dynamic Link。 |

以上仅是当前 Experience Constitution 下的抽象行为输入。页面布局、操作语义与跨端设计仍需现有 Screen Specification 的 DESIGN_READY 审批；本文不是新的设计权威。

## 4. OSS 源码、维护与商用边界

| 对象 | 本次核读 commit / 最近观察 | 源码结果与决定 |
| --- | --- | --- |
| ASWF OpenTimelineIO | `dc8366533acd6730228a9802b7cc7a8b6439d2ef`；GitHub `pushed_at=2026-09-26T16:17:39Z`；未归档；Apache-2.0。[O1][O2] | **ADAPT 候选**。原生模型提供 clips/tracks/gaps/transitions、value/rate 时间；不保证效果解释一致。v0.16 后的核心包不自动包含全部外部适配器；只选实际需要的适配器。 |
| OTIO FCP7 adapter | `63824d5ca04dbda81bcced89c9fde6ab0b7e6e36`；`pushed_at=2026-04-08T17:58:41Z`；未归档；Apache-2.0。[F1][F2] | **DEFER**。源码 `write_to_string` 输出 `xmeml version="4"`，不是 FCPXML。效果读取进入 `schema.Effect` 和格式专用 metadata，不足以证明序境 AudioMix 有可逆映射；生成器也依赖格式 metadata。 |
| OTIO FCPX adapter | `c61839e105fb035589d3ec704b1266a22089b425`；`pushed_at=2024-06-25T19:39:48Z`；未归档；Apache-2.0。[X1][X2][X3] | **DEFER 直接接入**。源码输出 FCPXML **1.8**；README 不支持转场、音视频效果、线性/复杂变速、CDL、图像序列引用。维护时间明显较旧，未归档不能充当维护充分或现代宿主兼容的证据。 |

FCPX 源码还暴露两项需验证的风险：`to_rational_time` 对帧数及 fps 使用 `int`；`_framerate_to_frame_duration` 先查询 `int(framerate)`。因此 30000/1001、24000/1001 与亚帧音频必须做针对性往返测试，不能把浮点秒直接套进适配器。缺失媒体还会生成 `/tmp/<clip.name>` 占位引用，序境不能把它作为已可重链媒体。[X2] 这些是**源码风险判断**，本轮没有安装运行适配器，未宣称已复现所有宿主故障。

许可证原文均已读取。Apache-2.0 提供商业使用/修改/分发路径，但应随分发保留许可证、适用版权/归属及 NOTICE，标记修改；不授予商标使用权，不覆盖音乐、视频、字体、插件和宿主授权。[O2][F2][X3] 这是工程许可初筛，不是整个产品的法律保证。Apple/Adobe 文档和 SDK 可访问不等于其产品源码开源，也不授权复制专有实现；未审查具体 SDK 分发条款前不引入。

核心仓库 latest-release API 本轮返回 404，未据此认定无发布或编造版本；使用上述明确 commit 固定研究对象。Adobe UXP changelog 本次实际页面首项为 **26.5.0**，同时列出 API 修复与废弃事项；25.6 是入门最低条件，不是“当前唯一版本”。[D9]

## 5. 映射回现有 owner：不能静默丢失的语义

当前核读源文件：`lumenis/shared/content_creation/video_editing.py`、`lumenis/shared/content_creation/rendering.py`、根目录 `shared_artifacts.py`。入口定位已运行 `locate_capability_context.py --path lumenis/shared/content_creation/video_editing.py --query interchange`，归属 Shared Content & Creation；已有研究 `FULL-PRODUCT-UPGRADE-CLOSURE-RESEARCH-20260929.md` 对 OTIO 的 ADAPT 判断作为历史输入，未替代当前源码。

| 语义 | 当前源码事实 | 交换损失 / 必要处理 |
| --- | --- | --- |
| 时间与帧率 | `MediaAsset` 没有源 fps、帧时基、起始 timecode 或 CFR/VFR 描述；clip 使用浮点秒并取 6 位；当前视频 renderer 固定 30fps。 | 渲染 30fps 不能冒充源素材时基。FCPXML 用有理秒；非帧边界可能触发补 gap。[A5] 未获可信源时基和目标策略时应报 UNKNOWN，不静默四舍五入。 |
| 剪切、间隙、轨道 | clip 有 source in/out、timeline start、track；reorder/ripple delete 只重排本视频轨；音轨保留手动 timeline_start，TimedOverlay 只有绝对 start/end，没有父 clip/anchor offset。 | OTIO Track 顺序与 Gap 可以表达放置，但不能凭空重建磁性连接、复合故事线和随动关系。必须比较剪切点、全长、空隙、轨序，不能只比较片段数量。 |
| 音频来源与选择 | `audio_stream_index` 是音频流序号，`audio_role` 含 original/muted/voiceover/bgm/sfx；并非容器全部流索引，也不等于声道号。 | 不能统一取第一个容器流或第一音轨。多音频流、静音、分离声道和 stem 的映射要独立证明；AI 四分轨不由 OTIO 自动提供。 |
| 混音与最终峰值 | `AudioMix` 有 volume、淡入/淡出、ducking；renderer 还会测量最终编码 true peak 并在必要时作一次固定衰减，结果在 render 元数据。 | 原始 Timeline 参数不能完整代表最终母带处理；通用 metadata 也不等于外部宿主执行。非默认混音应显式列损失。必要时经用户选择烘焙混音/分轨，标记可编辑性减少；不自动双重施加音量。 |
| 转场、字幕与图文 | Timeline 有 Transition/TimedOverlay；当前 renderer 拒绝非 cut 转场和 overlays。 | 区分“模型能存”与“renderer 能出”。不能把字幕位置、字体、逐词时间、字幕样式写进 metadata 就声称宿主可编辑；复杂效果需有目标映射或明确无法交换。 |
| 速度、色彩与 AE 效果 | 当前 Timeline 没有完整 retime、色彩管理或 AE 合成模型。 | 不接受未知语义后直接丢弃；将来导入必须报告不支持，或由已授权宿主生成可追溯烘焙素材。OTIO 效果行为本就由应用决定。[O3] |
| 媒体与重链 | MediaAsset 有 SHA-256/文件名/时长；公开序列化不含本机绝对路径。Artifact 保存 source_refs、父版本、Timeline 和 render 结果，按现有权限与完整性检查回读。 | 同名文件不能替代哈希身份。导出 URI 必须来自授权的可移植重链映射；不泄露私有路径/令牌，不把 missing reference 变假路径。工程文件不是媒体搬运许可。 |
| 版权、Evidence、Permission | 当前本地导入要求 rights_status 为 unknown，Timeline 不接受伪造 canonical evidence_refs；导出走既有 DATA_EXPORT gate。 | 将来导出仍保留 UNKNOWN/提醒，不替用户宣告版权清白；OTIO metadata 是衍生描述，不产生 Evidence/授权。不得自动购买、上传外部宿主或扩大导出范围。 |
| 手动/AI、版本与恢复 | 现有编辑操作、历史与 Artifact 父版本可复用。 | AI 建议与手动确认走同一 Timeline；预检不能修改源项目、重排或升版本。确认有损/烘焙后才产生新衍生 Artifact，旧结果保留并可回读。 |

这里的“应/必须处理”是待协调方批准的采用条件，不是新建数据/Permission owner 的授权。

## 6. 唯一下一 Batch 建议：Timeline 工程交换损失预检

**建议名：`J5-INTERCHANGE-LOSS-PREFLIGHT`，待序境12批准；核心新增代码 <=150 行，测试另计。** 选择这一项而不立即接 OTIO：当前缺源时基、可移植媒体重链与 AudioMix 映射；先输出真实损失比生成一个能打开但语义错误的工程文件更有直接价值。

- 范围：只在现有 `video_editing.py` 增加一个确定性、只读检查入口，并在现有 `tests/test_video_editing_core.py` 加针对性测试；复用 Timeline.validate/to_dict，不新增 service/registry/DB/依赖，不改 renderer、Artifact、权限、App。
- 一个固定研究 profile：`editorial-cut-v1`，只分析源模型到基础编辑交换表示的缺口；不是 FCPXML/PRPROJ exporter，也不承诺对接成功。
- 输出最小字段建议：`profile`、源 `timeline_version`、按稳定顺序排列的 issues；每项含明确 code、严重度、受影响 clip/track ID、源字段、可执行的处理建议。没有检查结果不能变成 PASS；不返回笼统的 `export_ready=true`。
- 已知损失：非默认 volume/fades/ducking、静音/音频流选择、非 cut 转场、overlays、多轨放置/间隙需要映射。缺失输入：源/项目帧时基和可移植媒体定位；均明确标为 UNKNOWN/待解析，不读取文件、启动转码或联网填空。
- 对有 Timeline 无法表达的连接、速度、插件语义，只声明 profile 不覆盖；不靠不存在的字段猜测“没有这些效果”。检查母带处理需要既有 render 元数据，未提供时说明不能比较最终声音，不伪造校验。
- 回滚：纯新增只读入口，可直接撤销该批代码；不迁移历史项目、不覆盖源媒体、不改变既有导出行为。

建议验收：默认 cuts-only 项目仍报告缺失时基/重链，不能误判为可交付；分别测试 volume=0/非1、淡入/淡出、ducking、muted、多音频流选择、overlay、dissolve、间隙与多轨；非法 Timeline 沿用原验证错误；重复调用结果相同；原 Timeline、历史、版本、序列化与所有本地文件不变；输出无绝对路径或凭据；未知 profile 明确拒绝。当前相关 core 回归必须 exit 0 且记录依赖哈希，不能使用修改前结果。

**真实用户工作闭环验收边界：**此 Batch 最多形成经测试的内核预检，不能单独获得 J5/工程交换 PASS。后续由序境12批准入口绑定后，必须让用户从真实项目进入、看到具体损失、取消时项目不变、选择处理后获得新结果并能回读。可商用工程交换还需在实际授权的 FCP/Premiere/AE 目标版本中导入、重链、复检剪切/声音/字幕、再次导出比对，并验证缺媒体/缺插件的恢复。测试样例、DTD、HTTP 200 或文件存在均不能代替这一验收。

## 7. 本批验证状态与交接

- 已执行：公开官方文档检索、三个 OSS 固定 commit 的源码/许可证核读、GitHub 仓库维护状态读取、现有 owner/source/依赖声明定向检查。未安装库、未执行第三方代码、未操作 XHS 账号。
- 辅助算力：OpenCode `zhipu/glm-4.7` 在无私有输入、只读清单任务上超时 55 秒；Ollama `qwen3:1.7b` 同类有限任务超时 40 秒。两者均无结果采用；超时不能按外层处理脚本 exit 0 算作模型成功。最终判断来自官方材料和直接源码核读。
- 本批没有产品代码修改，因此不把其他并行批次的自动测试挪作本文的验收。交接前只做本文结构/引用/路径存在性/单一建议/空白错误检查并记录文件哈希；那只证明文档一致性。
- `LIVE_NOT_VERIFIED`：未进行 OTIO 适配器运行或 Apple/Adobe 宿主往返；本机宿主授权与可用性未探测。`COMMERCIAL_READY=NO`：素材权利、目标版本、插件授权、真实用户 E2E 均未由本批证明。
- `REAL DELIVERY CARD` / `COMMERCIAL OVERLAY IMPACT`：这是当前 J5 的研究输入，优化将来跨工具交接的准确性；不修改现有工作台、产品定价/宿主授权或发布承诺。
- `GLOBAL UNIVERSE / DATA MATURITY IMPACT`：不涉及采集、实体或市场覆盖；本批不产生覆盖声明，不修改三项全域覆盖状态。
- 源码核读指纹：video_editing.py `bd6ef17f50bc252b82252a023908a01078a6ecaf0bf0a9517c6f7a9bbdc5bf91`；rendering.py `d20ef078f472c122007cc20ac541f10b55c66d036aeb94bebe09c7b3efc8fbe3`；shared_artifacts.py `80ecc240e74004514c4e8d5e925295eb73cf44ac7b033b972de59c0d9820e697`。并行修改后由协调方重新核对，本文不冻结其他 owner。

## 官方与固定源码引用

[A1]: https://support.apple.com/en-eg/guide/final-cut-pro/verb8fcfc133/mac "Apple: Magnetic timeline"
[A2]: https://support.apple.com/en-nz/guide/final-cut-pro/veradb8241c/mac "Apple: Playhead and skimmer"
[A3]: https://developer.apple.com/documentation/professional-video-applications/fcpxml-reference "Apple: FCPXML Reference"
[A4]: https://support.apple.com/en-hk/guide/final-cut-pro/verdbd66ae/mac "Apple: Import/export XML"
[A5]: https://developer.apple.com/documentation/professional-video-applications/timing-attributes "Apple: Rational timing attributes"
[A6]: https://developer.apple.com/documentation/professional-video-applications/document-type-definition "Apple: DTD page (body describes 1.10)"
[D1]: https://helpx.adobe.com/premiere/desktop/collaborate-with-others/collaborate-using-productions/productions-faq.html "Adobe: PRPROJ and Windows/macOS productions"
[D2]: https://helpx.adobe.com/after-effects/desktop/work-with-projects/after-effects-projects/projects.html "Adobe: AEP and AEPX"
[D3]: https://helpx.adobe.com/premiere/desktop/render-and-export/export-files/export-a-project-as-a-final-cut-pro-xml-file.html "Adobe: FCP7 XML export and loss warnings (2026-01-07)"
[D4]: https://helpx.adobe.com/premiere/desktop/organize-media/import-files/migrate-from-final-cut-pro-x.html "Adobe: FCPX XML conversion before import (2026-04-02)"
[D5]: https://helpx.adobe.com/premiere/desktop/organize-media/transfer-files/supported-elements-for-final-cut-pro-x.html "Adobe: Translation support and losses (2026-08-18)"
[D6]: https://developer.adobe.com/premiere-pro/ "Adobe: UXP / C++ SDK / CEP"
[D7]: https://developer.adobe.com/premiere-pro/uxp/plugins/ "Adobe: UXP prerequisites"
[D8]: https://helpx.adobe.com/premiere/desktop/use-premiere-with-other-apps/working-with-other-adobe-applications/share-assets-between-after-effects-and-premiere-using-dynamic-link.html "Adobe: Dynamic Link host-version boundary"
[D9]: https://developer.adobe.com/premiere-pro/uxp/changelog/ "Adobe: UXP changelog (observed 26.5.0)"
[O1]: https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/dc8366533acd6730228a9802b7cc7a8b6439d2ef/README.md "OTIO pinned README and package scope"
[O2]: https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/dc8366533acd6730228a9802b7cc7a8b6439d2ef/LICENSE.txt "OTIO Apache-2.0 license"
[O3]: https://github.com/AcademySoftwareFoundation/OpenTimelineIO/blob/dc8366533acd6730228a9802b7cc7a8b6439d2ef/docs/tutorials/otio-timeline-structure.md "OTIO time, composition and effect semantics"
[F1]: https://github.com/OpenTimelineIO/otio-fcp-adapter/blob/63824d5ca04dbda81bcced89c9fde6ab0b7e6e36/src/otio_fcp_adapter/fcp_xml.py "FCP7 writer / metadata / xmeml v4"
[F2]: https://github.com/OpenTimelineIO/otio-fcp-adapter/blob/63824d5ca04dbda81bcced89c9fde6ab0b7e6e36/LICENSE "FCP7 adapter Apache-2.0 license"
[X1]: https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter/blob/c61839e105fb035589d3ec704b1266a22089b425/README.md "FCPX adapter feature matrix"
[X2]: https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter/blob/c61839e105fb035589d3ec704b1266a22089b425/src/otio_fcpx_xml_adapter/fcpx_xml.py "FCPX 1.8 writer, integer timing and missing-reference fallback"
[X3]: https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter/blob/c61839e105fb035589d3ec704b1266a22089b425/LICENSE "FCPX adapter Apache-2.0 license"
