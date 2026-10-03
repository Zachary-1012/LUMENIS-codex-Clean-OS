# 参考视频研究移交给 F / C4

## 分工和范围

- 按用户最新收口，接下来全部本地参考视频的 UI/UX、视觉、动效/动线、页面跳转、AIGC 呈现及交互研究由 **前端窗口 F** 接手审计；涉及视频剪辑、播客和视听课程交付的素材研究由 **C4** 共同负责。M 只接收规则与完整性验收，不再占用主控时间人工审读视频。
- 研究范围不缩减。继续当前已提供的素材，并核对更广的“历史视频”来源；来源组必须分开建档：本次五个 Desktop MP4、2026-09-24 的五个微信视频路径、另五个 XHS URL 是不同素材组。原始 Desktop 附件请求入口为 Codex 会话 `01a0cf2d-6ece-7c90-8877-b58fc80a4480` source line 36949（2026-10-02 16:42:08.166 UTC）；用户后续要求研究之前发过的历史视频见 line 41491（2026-10-03 05:21:34.484 UTC）。更广历史语料不能因本批五条完成而宣称穷尽。
- 新 MP4 和历史前 3 条已有完整逐帧视觉覆盖及独立分析文件，证据可直接复用；不得将旧索引中的两秒采样 `COMPLETE` 当作逐帧审阅。#260147 当前只部分读到；#cb55 尚未开始视觉审阅。旧索引、旧采样图页和本次连续图页均保留。
- 所有观察只来自离线用户录屏。可研究并适配通用交互和视觉机制，包括丰富颜色；品牌身份不可冒充，第三方代码/资产按真实来源和许可证核验。视频里的账号、私人内容、帖子和媒体不转录或作为序境事实；不启动/登录/访问视频里出现的应用或账户。AI 入口、翻译、导出等仅记录可见事实，未验证的能力不推断为真。具体采用由 Owner 和 Experience 权威决定。

## 已完成逐帧视觉审阅

| 素材 | 原始视频准确路径 / SHA-256 | 事实元数据与人工视觉覆盖 | 报告 |
|---|---|---|---|
| 新录屏 `20261003-1238-22.9468452.mp4` | `C:\Users\28049\AppData\Local\Packages\Microsoft.ScreenSketch_8wekyb3d8bbwe\TempState\Recordings\20261003-1238-22.9468452.mp4`<br>`433a0be4d757ac903db13b119b03301609f7957f0d1604c90d6f91ada7e82601` | 71.7333 秒；1914×1004；30 fps；2152 源帧、1472 unique、680 精确重复。92/92 张连续页实际 `view_image`；1472/1472 unique 已查看；18 张原分辨率关键帧；未读 0。 | [VIDEO-1238-FRAME-ANALYSIS.md](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-video-1238/VIDEO-1238-FRAME-ANALYSIS.md) |
| 历史 #28346 | `C:\Users\28049\Desktop\28346dd9b6cbda22c59a9f13c6757b1b.mp4`<br>`36cf5faa224c709e0e31694a6288043f46bbc4e4a2d60ece55eaa2b40995b026` | 19.233333 秒；592×1280；30 fps；577 源帧 / 577 unique / 0 重复。37/37 张连续页实际查看；9 张原分辨率关键帧；未读 0。 | [VIDEO-28346-FRAME-ANALYSIS.md](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-videos-history-20261002/28346dd9b6cbda22c59a9f13c6757b1b/VIDEO-28346-FRAME-ANALYSIS.md) |
| 历史 #28d5 | `C:\Users\28049\Desktop\28d5aca3aaba2851b9a0f24f5c49f039.mp4`<br>`53a84b983045101a0d20d6a3315a1a37ce0a472bb11d16257ef247b5cd94504f` | 62.636222 秒；592×1280；约 22 fps（`6201000/281863`）；1378 源帧 / 1368 unique / 10 重复。86/86 页实际查看；10 张原分辨率关键帧；未读 0。 | [VIDEO-28D5-FRAME-ANALYSIS.md](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-videos-history-20261002/28d5aca3aaba2851b9a0f24f5c49f039/VIDEO-28D5-FRAME-ANALYSIS.md) |
| 历史 #a700 | `C:\Users\28049\Desktop\a700b33f084a1601c9c98e5d5dc52264.mp4`<br>`03c9f84814aaf7d21000bbc0b86333e456c2d6a3f4a3f540bee5f3d03d02df74` | 37.200000 秒；592×1280；30 fps；1116 源帧 / 1115 unique / 1 重复。70/70 页实际查看；12 张原分辨率关键帧；未读 0。 | [VIDEO-A700-FRAME-ANALYSIS.md](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-videos-history-20261002/a700b33f084a1601c9c98e5d5dc52264/VIDEO-A700-FRAME-ANALYSIS.md) |

## 后两条：已解码图页，审阅状态未完成

### #260147（当前部分读到，按 M 指令停止）

- 源文件：`C:\Users\28049\Desktop\2601473a2d645d6250caede43c3486a6.mp4`
- SHA-256：`54831c2c64e297aa7869625c3ba1250562a33686c095fdf37059156c12f12369`
- 70.05 秒；592×1280；平均帧率元数据 `27160/1401`；1358 源帧，1305 unique，53 精确重复；82 张连续页已经生成。
- 只用 `view_image` 查看了 `contact-sheet-0001.png`–`contact-sheet-0008.png`：unique index 0–127，代表源帧 F0000–F0127，最后已读 PTS 6.350000 秒；128/1305 unique 可见画面已审，后续 unique index 128–1304 未读，未抽取/查看原分辨率关键帧。后续 source occurrence 可依据 JSON 中精确哈希映射核对；没有把部分审阅称为完成。
- 当前覆盖状态已在 [FRAME-COVERAGE.json](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-videos-history-20261002/2601473a2d645d6250caede43c3486a6/FRAME-COVERAGE.json) 标为 `PARTIAL_CHRONOLOGICAL_CONTACT_SHEET_REVIEW`；不删除图页。尚无分析报告。

### #cb55（尚未视觉审阅）

- 源文件：`C:\Users\28049\Desktop\cb55b77feb25668ebdaea62e177adf1b.mp4`
- SHA-256：`ee9a5f01bbf1f70f3f470f4f9cfada01d4b1a9537853dd904718a194eaf79faa`
- 62.206259 秒；592×1280；30 fps；1865 源帧 / 1865 unique / 0 重复；117 张连续页已经生成。
- `contact-sheet-0001.png`–`contact-sheet-0117.png` 全部尚未 `view_image`；视觉已读 0/1865，未读源帧 F0000–F1864；未抽取/查看原分辨率关键帧，尚无分析报告。覆盖状态保留 `PENDING_CONTACT_SHEET_REVIEW`。

## 产物与资源复用

- 五条历史 Desktop MP4 已生成 `37+86+70+82+117 = 392` 张连续 contact sheets；其中前三条 193 张完成视觉审阅，#260147 前 8 张部分审阅，#cb55 的 117 张未审。新 MP4另有 92 张全部已审。因此目前六个本地文件一共生成 484 张连续图页，全部保留、可由 F/C4 复用。
- 历史媒体覆盖根目录：[reference-videos-history-20261002](D:/LUMENIS_REBUILD/序/序境/work/m-controller-20261003/reference-videos-history-20261002)。各子目录的 `FRAME-COVERAGE.json` 保存帧 index、PTS、精确重复映射和各页索引，`source-metadata.json` 保存文件 SHA 与解码元数据。
- 原两秒样本目录 `work/frontend-2026-10-03/reference-videos/` 未改。五条 Desktop 视频与其它历史来源组保持独立。
- 审阅到的前三条历史视频中，#28346 主要为图文动态阅读/主题列表；#28d5 含手机剪辑器、素材选择和社交浏览；#a700 含社交媒体视频流、翻译状态和资料/消息/发现页。后两条还没有完整研究结论。新 MP4、前三条详细观察与适配建议以各自报告为准。

## 操作边界

本次仅离线解码和查看本地用户提供的文件，在 `work/m-controller-20261003/` 创建分析工件；未安装依赖、未调用模型 API、未上传视频，未改产品代码、规则、运行时、数据库、旧样本索引或 Git 状态。不要从图面账号信息延伸到登录或实时账号访问。
