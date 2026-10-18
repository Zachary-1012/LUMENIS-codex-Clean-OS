# ORG-MECH-06：Read Aloud的离线契约与停止失败

## 结论及边界

固定main静态可证：Dart服务会处理抛异常的stop，但Android、Apple、Windows原生桥没有将部分原生停止返回值向上表达。当前不能因此证明实际音频曾停不下来；本研究无实机/产品运行。停止请求成功、已确认静音、资源已释放必须区分，已有generation防旧回调和单会话串行机制继续复用。

先复用已完整读过的本人声音原方案及voice_postproduction/mobile_voice/report.md完整107行、postproduction/REVIEW_PLAN_ZH.md完整70行。其VoiceNPC schema/商用分发/真实包兼容仍未验证，本项不重做候选搜索或增加采声产品。当前系统本地朗读仅预览已授权文本，不是生成可分发本人音色或播客成品。

指定2248候选与main的7份朗读文件SHA逐一相同，见ACTIVE_2248_COMPARISON.json，因此原生停止返回未传递的静态观察也适用于该候选；仍无实机故障证据。

## 官方依据与实读范围

1. Android TextToSpeech API：stop返回ERROR或SUCCESS，speak异步入队不证明开始，shutdown释放引擎资源。读取对应方法，不冒称整个API读完。[官方](https://developer.android.com/reference/android/speech/tts/TextToSpeech)
2. Android Engine：官方建议通过Voice.isNetworkConnectionRequired选择嵌入式声音；未安装语音标记需处理，加载未完成可失败或换声。本轮读取该条说明与已有准入逻辑，不安装语音。[官方](https://developer.android.com/reference/android/speech/tts/TextToSpeech.Engine)
3. Apple stopSpeaking(at:)官方页面正文工具只得到短页，官方搜索返回布尔结果语义；不能冒称完整SDK源码核验。false不应一概当仍发声，若原本无活动语句需要独立状态确认。[官方](https://developer.apple.com/documentation/avfaudio/avspeechsynthesizer/stopspeaking(at:))
4. Microsoft SAPI5.3 Speak官方方法全文实读：purge可传NULL，返回HRESULT，包括设备忙等错误；方法返回值不能丢弃。[官方](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms719820(v=vs.85))
5. Web Speech API §4.2相关方法/错误/Voice属性：localService区分本地合成服务；cancel清队列/停止当前语句但不改变全局paused；有not-allowed、audio-busy等错误。规范依据不替代具体浏览器实现验收。[官方](https://webaudio.github.io/web-speech-api/)

以上本轮2026-10-17读取；除固定SAPI5.3外网页为动态文档，不声称固定SDK版本。产品源固定commit与整文件SHA在evidence。

## 现有实现与精确缺口

|原Owner入口|已存在且应复用|研究需核的边界|
|---|---|---|
|read_aloud_service.dart完整|generation、backend串行、先stop再start、精确locale、8秒启动期限、250msobserve、异常转failed|stop返回不抛错被视为成功；observe失败停止poll却不等音频一定停止；dispose是异步停止非资源释放确认|
|read_aloud_backend_io.dart完整|同一MethodChannel，PlatformException可向上失败|invokeMethod<void>无法传原生停止状态；MissingPlugin被解释无会话，支持假设需平台验证|
|Android MainActivity.kt:20–48/110–185|本地/已安装voice筛选，准确区域，setVoice和speak检查返回，分块utteranceID|stop分支忽略ERROR后写STOPPED并success；speak前stop同样未核；不能让上层异常保护替代本层返回检查|
|iOS AppDelegate.swift:26–108及macOS:35–90|准确locale、当前utterance身份、回调防陈旧|stopSpeaking结果未使用，先清current再自报STOPPED；com.apple前缀是供应商筛选，不是离线证明|
|Windows read_aloud_platform.cpp:100–132/194–280|SAPI声音Language属性、GetStatus实际观察|Stop忽略purge HRESULT立即STOPPED；Observe在STOPPED时不再查GetStatus。注册token+语言不证明任意第三方引擎离线|
|Web backend完整|localService/locale筛选，utterance身份，onstart/onend，cancel|异步voice列表只等待一次250ms；空列表可能暂不可用；cancel后paused仍可能true，后续start需按原UI合同处理真实状态，不能自动宣称播放|

这是当前固定源码连接路径，不是第三方候选；是否运行中的产品加载此版本仍未知。研究不修改代码。错误展示宜“停止失败/状态未确认”，不能对用户宣称已静音或已释放；也不能因为一次false就误报异常，必须区别原本idle与仍active。

## 采用方案：在原共享服务/平台桥补证

- 复用现single-session/generation，不建第二音频管理器。每次request绑定可复核的utterance/generation、文本版本、scope、locale、voice与engine版本。
- 停止开始先停止接收旧会话事件；平台桥记录停止调用结果与观察态。明确请求停止、已无活动语句、失败/未知；资源shutdown/release独立于停止播放。
- stop失败或超时不能仅因UI切换就启动另一个voice；由原Owner确定有界重试/观察或明确恢复步骤，不偷偷换引擎/云端。已经idle的幂等stop应正常处理。
- 本地资格分“API声明的local/embedded”“已安装”“实际断网成功”“未观察到外联”。最后一项需要获准实机网络证据，不能凭供应商名或一次声音试听推断；也不能靠安装来源推断所有合成离线。
- 声音安装/删除、引擎更换、蓝牙/音频焦点变化后重新发现；缺韩语不翻译、不换英语；仅实际支持pause/resume才呈现。重试必须仍是用户发起且读当前授权文本。
- 本人声音包与系统voice库存分开：格式/checkpoint/runtime/权利匹配才导入使用，禁止把系统Personal Voice或云voice_id等同可分发音色包。

## 实验与真正验收

lab共23断言，其中8项有关TTS：原生-1被void桥吞掉、停止失败仍active、false但已idle、accepted但无idle证据、旧utterance回调、缺精确locale、供应商前缀无离线证明、Web cancel保paused。纯逻辑反例，不调用原生音频。

G13/Experience1264–1278、前端J29.01/02；原Shared/C4、SYSTEM平台桥、F呈现。待运行：各端安装声音/离线/初次延迟/停止错误/超时/切页/源改版/蓝牙设备断开/恢复、真实短长文本与zh/en/ko、实际静音和CPU/资源释放、saved稿重开。旧Windows smoke不能代其他端或后续版本。研究补齐机制，但以上产品验收全部NOT_RUN。
