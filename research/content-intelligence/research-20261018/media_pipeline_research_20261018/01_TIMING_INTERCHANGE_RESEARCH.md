# G183/J5/E8：工程交换时基与不可静默的损失

2026-10-18。Owner C4 Shared Content/Timeline/rendering，C5 Artifact/Source，C6导出与运行身份，F剪辑/预检。研究独立目录；未修改产品、未安装/执行OTIO适配器、未打开Adobe/Apple宿主。

## 先读：第三方参考候选仍为DEFER，未证明现产品故障

本报告120秒漂移数字来自第三方旧FCPX适配器公式的自写镜像，不是序境当前实现。原VWI对该适配器明确DEFER直接接入。对固定main4dab所有*.py、*requirements*.txt、pyproject.toml、package.json只读检索otio_fcpx_xml_adapter、to_rational_time、opentimelineio import、fcpx_xml，结果0命中；本批没有当前调用证据。该检索不覆盖动态插件/外部环境，亦不证明其他工作根状态。不得依据本报告直接派现产品修复。采用落点仅为原G183/J5/E8交换profile/时基验收设计。

## 研究新增什么

原VIDEO-WORKFLOW-INTERCHANGE-RESEARCH已充分区分FCP7 XML/FCPXML/OTIO/AE及许可，也指出旧FCPX适配器int处理风险。本批不重新写选型清单，直接核其固定源码并用自写Fraction模型量化风险；同时把199材料中三项Adobe教程文字/转录实际读回，填入真实阅读范围，不称视频观看。

原文件与规划条目仍保留，旧“当前renderer拒绝”只属当时基线，本批没有用旧缺陷向正在修复的产品重复派工。

## 固定源码与真实反例

官方固定来源：https://github.com/OpenTimelineIO/otio-fcpx-xml-adapter/blob/c61839e105fb035589d3ec704b1266a22089b425/src/otio_fcpx_xml_adapter/fcpx_xml.py 。静态保存sources/fcpx_xml.py，SPDX Apache-2.0；本轮精读16–26、79–113、675–693行，未宣称该仓全部审计。

- to_rational_time把计算帧数与fps都转int；自写等价算术输入3600秒、30000/1001 fps，得到107892帧按29fps解释，时长3720.413793秒，比原多120.413793秒。不是仅小数显示误差。此为公式镜像实验，不是已安装适配器或宿主实跑。
- 帧长lookup同时有29.97键，但精确30000/1001转float不等于29.97，int29也无键，示例查表返回空。调用者是否先规整到近似值仍需全链验；不能承诺所有输入均失败。
- 1个48kHz音频采样小于1视频帧，直接量化到视频帧会得到0。音频亚帧剪辑不能以视频整数帧代替。
- 一帧30000/1001素材若逐clip四舍五入到6位再累计，10万片段构造例误差约0.033333秒。此为极端反例，不代表通常项目必然漂移；应保留有理时基或明确统一量化边界。
- VFR实例最后PTS与固定帧数/30推算不同，单凭fps均值或帧数不能恢复真实剪点。需要源PTS/时基或明确转CFR衍生物映射。

14项实验中前5项支撑本报告，其余支撑02播客报告。完整输入、结果和脚本在experiments，全部标准库、无外联。

## 原三项材料的实际采用

MAT-b0dfba64e1a67a6dd287，Adobe导入整理教程：正文/转录说明素材分组、统一命名及select sequence。序境采用素材浏览/选段与成片草稿分开，保存素材身份与选择，不能把bin名字当媒体身份。https://www.adobe.com/learn/premiere-pro/web/import-and-organize-travel-footage

MAT-66d403833c9322e1a8c9，剪辑教程：正文/转录给个人快捷键、ripple、markers、select与rough-cut sequence。个人重绑定快捷键不是软件全局默认；借鉴可配置动作与“选段→草剪”连续性，不能硬抄J/W或把同一ripple说成完整磁性时间线。https://www.adobe.com/learn/premiere-pro/web/combine-and-trim-travel-clips

MAT-48e9cb4c820a6613d8a4，导出教程：正文/转录涉及In/Out范围、Match Source、字幕与已登录目的地上传。采用导出范围和预设可见性；“Match Source”不证明对源VFR/色彩/音频/字幕全部无损，平台发布需独立已授权动作。教程说H.264适用网络是教程建议，不是序境所有平台万能配置。https://www.adobe.com/learn/premiere-pro/web/export-share-travel-video

三项仅网页文字/公开转录已读；视频、素材附件、真实Premiere操作均未完成，不把该三项材料整体标READ_COMPLETE或IMPLEMENTED。

## 可采用逻辑

1. 以既有MediaAsset/Timeline记录源时基与项目时基的含义；有理秒、源PTS、音频采样、字幕毫秒、呈现帧分别标单位。具体字段变更需原Owner另行批准，本文不新建Timeline。
2. 预检按目标profile/version/adapter commit列EXACT、QUANTIZED、BAKED、UNSUPPORTED、UNKNOWN及受影响对象；没有可核时基不能PASS。量化说明误差方向/范围，不能偷偷截断。
3. 源素材身份以hash/流选择和时间域为准；代理/转码另有派生身份和映射。同名文件、容器第一个流或近似fps不替代。
4. 交换预检应对比剪切点/全长/间隙/轨顺序/连接/音频参数/字幕/变速/效果与可编辑性。只比clip数与XML合法无法证明语义保真。
5. 用户选择有损转换后产生新Artifact版本，保留原项目和损失表。取消不改原件。烘焙后“看起来一样”也要显示失去参数编辑能力；不重复施加母带增益。

## 真正待验与失败边界

研究已量化固定旧适配器的算术边界；未关闭G183整体。下一获准验收：固定OTIO和适配器实装/隔离fixture、23.976/29.97/59.94/精确分数输入、48k亚帧/VFR、长时间累计；目标FCP/Premiere实际导入/重链/再次导出；音量/字幕/转场/速度逐项损失；真实UI预检取消与新Artifact保存重开。Apple开发者Timing Attributes本轮正文JS页未取得，Markdown点击失败，仅作旧VWI引用继承，不冒新全文核验。
