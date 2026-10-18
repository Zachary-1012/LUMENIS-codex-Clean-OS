# P7/P10/P11：播客剪辑映射、章节/字幕与发布包一致性

2026-10-18。Owner C4 podcast/Timeline，C5 Artifact/Evidence，C6导出/发布Permission，F播客编辑/预览。关联E2/E4/E8、P6/P7/P10/P11与G128。无账号、付费、远端发布或产品改动。

## 已有实现先核，避免重复造轮子

main4dab的podcast/intelligence/episode_runtime.py实际读取1–115、390–560行：_output_segments按保留segment顺序累积输出时间；chapter_document与VTT都复用它，已有章节合并、原文/校对稿分列、空毫秒cue拒绝、标记转义、多音频流显式选择和七件套。metadata明确改稿不等音频变更、未证明对齐/听审/持久化。因此不把“缺重排”或“改稿即改音频”错报为当前缺陷。

新研究重点是跨剪点引用/已有外部词时间码的处理、媒体版本绑定及平台接受边界；当前源码并不自动证明外部逐词ASR、重新剪辑后的全部Sidecar、RSS与平台消费都已闭环。

## 官方固定合同

Podcast Namespace固定commit d4036dcb1047ad654682e1142734e3acf2c13f37，实际读完整chapters标签、transcript标签、JSON chapters规范：
https://github.com/Podcastindex-org/podcast-namespace/blob/d4036dcb1047ad654682e1142734e3acf2c13f37/docs/tags/chapters.md
https://github.com/Podcastindex-org/podcast-namespace/blob/d4036dcb1047ad654682e1142734e3acf2c13f37/docs/tags/transcript.md
https://github.com/Podcastindex-org/podcast-namespace/blob/d4036dcb1047ad654682e1142734e3acf2c13f37/docs/examples/chapters/jsonChapters.md

采用事实：章节是外部文件，可独立更新/被客户端缓存；startTime为秒、按升序；1.2示例version为1.2.0，endTime可选；toc=false为不显示的元数据标记，不应被当用户章节。transcript可多个格式且可声明language/rel；XML按namespace URI识别，不依赖固定前缀字符串。远程章节图片/链接存在隐私跟踪风险，预览不得自动无界抓取。规范格式有效不代表语义或平台采用合格。

Apple公开转录文档本轮实际读取正文：https://podcasters.apple.com/support/5316-transcripts-on-apple-podcasts 。当前列英语、丹麦、荷兰、芬兰、法、德、意大利、挪威、葡萄牙、西班牙、瑞典语；未列zh/ko/ja。页面明确动态插入改变的音频部分可能不显示原转录。因此本地中韩VTT可用/可导出与Apple展示状态分开，不删除原多语目标、不自动切外部服务。Apple语言支持有时效，真正发布前仍需复核。

## 实际隔离反例与采用规则

自写保留区间[0,10)、[20,30)、[40,60)按原顺序拼接成40秒：
- 原15秒章节落在删除区间，必须删除/人工重选或标失效，不能静默夹到输出10秒。
- 原20秒映为输出10秒，而原10秒位于被删区间。半开区间边界必须一致，不能两边同时归属。
- 原8–22秒引语跨过删除区间，变成两个片段[8,10)和[20,22)的输出。拼接后的“连续一句”可能变意；需保存断点、上下文和人工引用确认，不把时间映射当语义批准。
- 25秒与45秒需要不同偏移，一条全局offset不足。重复使用同源片段还会出现一对多；未来倒放/速度曲线/交叉淡化不能沿该简单函数假装处理。
- 原句改成新的意图文本而未换音频，对齐仍NOT_VERIFIED。真实当前源码已明确该点，实验只是独立说明其必要性。
- JSON NaN、超出媒体长度时间拒绝；namespace别名p可识别chapters；当地文件有效与平台语言接受不是同一测试。

上述9项连同01的5项共14断言已执行通过；未生成个人声音/真播客、未跑产品函数或外部宿主。

## 可采用的发布包一致性流程

A. 绑定最终媒体hash、音频流、时长、采样率、plan revision/content digest与编辑映射版本；Source时间码保留原件，output时间码仅用于该渲染版本。
B. 在既有_output_segments基础上，对外来ASR词/外部章节/引语切片做明确映射，区分保留、拆分、删除、歧义、需重对齐。原文文本不因修订消失，原文VTT名称不能暗示源音频坐标或经验证ASR。
C. 用同一冻结revision生成七件套；manifest逐文件hash、MIME与语言。原子保存/回读后才称包完成；仅builder返回字典不算持久保存。动态换音频后sidecar必须重算/重新确认，不能沿用旧链接缓存并假称同步。
D. 本地导出与外部发布分成真实动作：本地包无需账号可用；RSS链接必须最终可达且服务器MIME正确、时间码对应最终媒体。网络检查、托管、上传或发布需适用具体授权；本研究不执行。
E. 章节图/外链来源与用途另核，配置/包字段不自动触发访问；保留用户不加载外部资源的预览。已发布修订需要版本/缓存刷新状态，不能将feed写入成功等同所有客户端已刷新。

## 尚未闭合

研究机制与反例可审；真实长节目/词内剪切/说话人/字幕听读、对齐误差和跨端播放器实测、正常媒体七件套保存重开、RSS服务器返回/客户端接受、动态广告版本、发布撤回与版权仍待实施或用户材料/许可。不会用固定公式测试替代母语听审、源媒体身份或商业发布批准。
