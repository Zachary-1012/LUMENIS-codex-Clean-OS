# 公开研究版本说明

2026-10-18 05:34 用户批准本研究；这不表示产品已验收。个人采声专项已取消；授权声音导入、ASR 与播客方向保留。

下文为历史 v11 研究全文。历史“待用户审核”及研究建议保留原话；涉及个人采声的历史提议不作为当前工作安排。本文是研究材料，不授权产品代码、数据库或运行环境变更。

公开发布前已检查正文、解码后的 HTML 超链接及转换记录。本报告未发现需要遮盖的私有文档链接、个人账户路径、邮箱、客户原材料、内部对话原文或凭证值。本次脱敏清单为零项；完整 Markdown 因新增本说明而不与原转换文件字节一致。

<!-- Full fidelity transcription of the v11 Word source. Research evidence only; this conversion does not amend product rules or authorize implementation. -->

# <span id="p0001">序境第三方依赖补核更新提示</span>

<span id="p0002">审核版本 v11    待用户审核    更新截至 2026年10月18日 00时25分 UTC</span>

<span id="p0003">先读本页，再读原报告。原报告180页完整保留，仍代表此前冻结时点；其“尚未下载固定发行物”“仅有许可元数据”等状态，须按新增附录更新理解。新增证据没有完成部署验收，也不构成法律意见或执行许可。</span>

## <span id="p0004">本次需要优先审核的变化</span>

<span id="p0005">固定 Unsloth 2026.9.12 与 Zoo 2026.9.8 wheel 已下载并核官方 SHA256。实际发行物包含 Apache、LGPL 与 AGPL 文本及文件头，不能以包级声明代替逐文件审阅。AGPL 文件不仅存在于 Studio；训练相关静态导入链可到达 Zoo 的 pad&#95;token.py。静态可达不等于已在产品现场执行，也不直接决定产品或权重的法律义务。</span>

<span id="p0006">Qwen3 TTS 候选固定源码要求 transformers 4.57.3，20B NF4 配方固定4.56.2，不能原样放进同一 Python 环境满足两项等式。它尚非已集成组件，该文本冲突不代表产品发生运行故障。独立运行环境仅是待研究方案，未实施。</span>

<span id="p0007">PEFT、datasets、safetensors 的真实部署精确版本仍未取得。上游范围约束已补核，但不能替代锁文件、framework&#95;versions 原文或部署 wheel 身份。NF4 的原基座 revision 仍为 UPSTREAM&#95;UNSPECIFIED；固定最终权重身份不证明转换来源可重建。</span>

## <span id="p0008">阅读顺序与保留边界</span>

<span id="p0009">下一页起为原报告，保留原页码1至180；附录从标示页码181起。PDF物理页码因本提示页顺延1页。附录先逐项定位旧说法，再给出完整补核研究。凡旧文与补核状态不同，以附录所列证据范围和时间限定理解；旧文未作静默覆盖。</span>

<span id="p0010">原20B基础目标不变。小模型、声音、多模态、多语言及Claude Quickstarts均按研究候选或参考材料界定，不能据本稿视为已集成、已商用可用或已授权修改。报告内未闭合的许可、依赖、权重、GPU、声样和质量验证继续保留。</span>

<span id="p0011">本次只制作审核材料，未安装研究包、运行模型、训练、上传声音、修改产品代码、数据库或环境，也未联系第三方。</span>

<span id="p0012"></span>

# <span id="p0013">序境当前第三方接入研究审核报告</span>

<span id="p0014">主线与恢复候选对照  供用户审核</span>

<span id="p0015">研究撰写 dot（zack）</span>

<span id="p0016">研究日期 2026年10月18日 北京时间<br />状态 源码机制与证据复核完成到本文明确范围  真实运行及许可缺口保持开放</span>

### <span id="p0017">审核结论</span>

<span id="p0018">建议保留成熟的解析、数值、网络、UI和编码基础库，将调整集中在现有产品owner的授权、失败语义、取消、持久化、来源及回执。当前证据不足以宣布全部第三方在真实目标环境完成验收，也不足以作出全面自研替代的决定。本报告交代每层已有机制和明确缺口，供审核研究结果及后续验证优先级；不构成替换、迁移、安装、发送或部署批准。</span>

<span id="p0019">两版必须分别审核。A为官方GitHub主线4dab98ed6357133da9307de846180ed4f7bba5f5；B为恢复的未最终验收候选，来源清单指纹7bcb3b87210b8eabf0b41982bc717419​936c0da01bdae6a4a779528ce7c4c206。A可配置任意HTTPS AI目标，与既定Groq-only规划存在差距；B才固定Groq并逐次核权限。A的邀约邮件路由可直达SMTP发送；B才改为默认未绑定执行器的scoped链。不能把B的收紧写成主线已经修复。</span>

<span id="p0020">采集层还存在来源真实性风险：旧Facebook的URL组装参数合同错误，旧缓存降级未按关键词隔离，部分适配器把未知互动量记为0，默认关闭或仅占位能力可能给出偏乐观health。A/B调度已不同，逐项裁定见采集章节。</span>

<span id="p0021">较高优先级风险包括Windows偏好持久化返回false被上层忽略、Web正文超时和取消不等价、MCP/外仓子进程的声明式只读并非操作系统隔离，以及外部效果完成后回执/本地提交失败造成不确定状态。所有发现都区分静态确定路径、恢复历史实测与当前未验证；没有把静态推演包装成新运行结果。</span>

<span id="p0022">许可需要按实际分发形态处理。MIT/BSD/Apache仍有版权、许可、NOTICE等义务；LGPL/MPL不自动禁止商业使用，应区分构建工具、客户端被打包代码、条件平台包、修改及再分发方式。FFmpeg具体构建、eSpeak声库、模型权重、tokenizer、字体和平台内容权利独立于顶层Python或Dart包许可。当前没有足够依据签发全产品商业许可无风险结论。</span>

### <span id="p0023">完整性依据与边界</span>

<span id="p0024">主线归档3186个安全提取文件逐个匹配官方Git树blob，零不一致；一个环境示例文件未读取。Python扫描A含vendor共1345文件，去除55个vendor后1290；B含vendor1456，去除后1401。两版均无AST解析错误。研究同时收集requirements声明、静态import、动态导入表达式、路由/工厂注册、原生进程调用和资产锁。静态扫描无法证明动态部署注入或当前配置，未读取这些敏感值。</span>

<span id="p0025">100项Python联合账来自96项声明/import身份，加4项在训练函数运行时版本门禁发现的底层包；49项在B存在产品源import，不等49项当前都运行。其中有退休死分支、条件训练、ImportError备用和可选服务器。npm/Dart共362锁实例，含重复嵌套及平台变体；357可定位归档与锁hash一致，5个SDK占位缺真实SDK身份。74项服务账是适配路径/模型/native/退休身份，不等74家供应商。三种数字不能相加为已运行集成数。</span>

<span id="p0026">前端和根JS配置的482文件两版相同。后端不能以这个结果推断相同。Python没有全平台精确传递锁；历史104包共享freeze只证明那时环境存在，另外3包浏览器target与19个数学独立环境安装receipt分别保留，不冒充产品已调用。没有将标准库列为第三方集成；OpenSSL、BLAS、FFmpeg编解码器等原生传递边界仍需现用二进制清单。</span>

<span id="p0027">研究深度分为产品调用机制、所用上游函数、版本/许可证身份、真实运行证据四层。固定公开tag可用于理解实现，但不自动证明与部署wheel相同；下载归档验hash也不证明安全或使用效果。闭源服务仅能核公开合同和获准观测，不声称掌握私有后台。未核实项在各章和总账中明确保留，不用庞大附录替代深入结论。</span>

### <span id="p0028">建议审核的六组后续工作</span>

<span id="p0029">1. AI与对外效果组：由AI Gateway、Permission和KOS owner联合审A/B差距。验证直接adapter调用、重定向、配置变更、撤权、成功发送后记账失败及稳定回执重试。凭据和真实发送只在具体授权后执行，先用受控fixture证明不外发。</span>

<span id="p0030">2. 文档与SavedWork组：由Importer、Reporting与Artifact owner核解析降级和结果完整性。覆盖缺包、损坏文件、公式/缓存、资源关闭、字体缺字、多页表格、导出独立重开、读到一半撤权。许可证需随字体与转换二进制一起记录。</span>

<span id="p0031">3. 数学与数据组：沿Statistics和Canonical owner做输入适用条件、独立小规模oracle、不可行/非最优拒绝、保留集及重开；复用恢复的42项历史证据，但目标平台重新验。不得把安装BERTopic或ORTools等同业务语义/收益成立。</span>

<span id="p0032">4. 前端与桌面组：由Client Settings、HTTP和MediaPreview owner核写失败、重启回读、正文取消、平台插件注册、Windows原生依赖和打包NOTICE。锁中Android/iOS/Linux包不等当前平台承诺。</span>

<span id="p0033">5. Skills与采集组：由SYSTEM、Skill Invocation和SourceUse owner逐项确认真实注册、来源授权、只读边界、超时/进程树清理、撤销及派生数据隔离。旧/v4仍可达项目不得漏测，未绑定广告/通知保持未绑定记录。</span>

<span id="p0034">6. 媒体与模型组：由Shared Rendering、Speech和Owned AI owner固定实际二进制/声库/权重/tokenizer，做输入解码、非静音、时间轴、字幕、人审、checkpoint独立重开及目标设备资源。商业音乐/SFX/转场/插件候选和用户上传插件是新增审核工作，不能自动升级为当前已接入能力。</span>

<span id="p0035">上述队列沿已有owner补闭环，不建议另造一个绕开权限、来源或Artifact的第三方总入口。用户审核研究报告与批准具体实现修改是两个独立动作。</span>

### <span id="p0036">与原有研究及新增媒体要求的关系</span>

<span id="p0037">Claude相关实现参考、Evo、REA、Obelisk、Jev、数学依赖和Handbook等原有研究继续有效，各自保留原研究范围和审核状态。本报告只裁定当前源码接入，未在当前锁/调用链找到的候选不因此作废，也不混入已使用清单。新增加的视频与播客商业音乐、音效、转场、效果器和用户上传插件，应在既有媒体owner下单列候选来源、素材权利、插件权限与实际作品验收；当前FFmpeg、播放器、字体及动画能力不能替代这些新增需求的完成证据。</span>

<span id="p0038"><br /></span>

## <span id="p0039">Python 当前调用与上游机制</span>

### <span id="p0040">1. 本地文档解析链</span>

<span id="p0041">已重新逐函数读候选 lumenis/importer/parser.py 第1–470行，包括 parse&#95;file、parse&#95;markitdown、parse&#95;pdf、parse&#95;word、parse&#95;excel、parse&#95;legacy&#95;word、parse&#95;legacy&#95;excel。入口接收本地文件，拒绝带 :// 的路径，检查文件存在及大小，再按扩展名分派。解析后对原字节计算SHA256、保存来源名；对保留文本另算hash，建立页、段、表格单元格或解析行定位。定位是保留文本的位置，并非所有格式都能还原原文件页面。</span>

#### <span id="p0042">MarkItDown 0.1.8 与转换传递库</span>

<span id="p0043">requirements.txt精确声明 markitdown&#91;pptx&#93;==0.1.8。PPTX/HTML/HTM走 parse&#95;markitdown，惰性导入，MarkItDown(enable&#95;plugins=False)，优先convert&#95;local，不支持该方法才用convert。保留markdown/text&#95;content并要求非空。成功后才记录包版本。关闭插件和只传本地路径是产品调用约束，不能据此证明整个上游转换器绝无网络行为；应审查实际转换器、文件识别模型、PPTX解析及链接处理。其下python-pptx、Magika、ONNX等依赖分别计许可和资源，不把“MIT”扩展到全部二进制、模型或客户文件。保留成熟转换器；自研重点是格式质量、来源定位、可取消资源预算和真实文件回读。现有测试存在不等本轮新执行。</span>

#### <span id="p0044">pdfplumber 与 PyPDF2 备用路径</span>

<span id="p0045">parse&#95;pdf先用pdfplumber.open上下文，逐页extract&#95;text和extract&#95;tables；文本按双换行拼接，记录页起止位置。主try中任何ImportError才触发PyPDF2.PdfReader备用，包括处理过程中迟发的ImportError；普通损坏/密码/其他解析异常不会自动降级。备用只调用文本抽取，且复用原ParseResult，若首选已追加表格才出现ImportError，可能混入部分旧表格，需故障注入核实。PyPDF2精确版本与资源所有权未明，不借pypdf或最新版补身份。PyPDF2不是pypdf名字的同义安装包，实际版本未固定，应单列待核。扫描PDF无文字可能返回空字符串，不能据此宣称OCR。保留解析库，审核空页、加密/损坏文档、合并单元格、页码定位和回读；不建议自行重写PDF解析内核。</span>

#### <span id="p0046">python-docx</span>

<span id="p0047">parse&#95;word通过Document解析DOCX，按doc.element.body顺序区分段落与表格；通过Paragraph/Table包装lxml节点，保留段索引和表格行列定位。该顺序比单独遍历doc.paragraphs更能保持表格穿插关系，但当前正文遍历不等页眉、脚注、文本框或复杂版式完整抽取。ImportError清晰失败，未把库不可用变成空成功。输出生成调用另由reporting owner负责；客户端文件保存成功还应独立打开/渲染验证，不以ZIP存在证明内容可读。</span>

#### <span id="p0048">openpyxl 与 pandas XLSX 备用路径</span>

<span id="p0049">parse&#95;excel首选load&#95;workbook(data&#95;only=False,read&#95;only=True,keep&#95;links=False)，因此保留公式表达式，不把无缓存计算结果当零。逐sheet逐row转字符串、保存非空行与单元格locator。正常结束wb.close，但异常路径没有finally；只读懒加载资源在中途异常时清理值得测试。仅ImportError才进入pandas：ExcelFile(file&#95;path)，再每sheet read&#95;excel(file&#95;path)，并非复用同一reader。备用输出df.to&#95;string和values，定位与公式语义不同，ExcelFile未显式close。当前未指定pandas engine；后文已从pandas v3.0.6默认引擎源码确认此备用仍依赖openpyxl，不能写成独立恢复。建议审核后统一合同，保留成熟XLSX库，不在未获准情况下删除依赖或更改默认路径。</span>

#### <span id="p0050">xlrd 2.0.2</span>

<span id="p0051">parse&#95;legacy&#95;excel专门处理XLS：open&#95;workbook(on&#95;demand=True)，按ctype区分空、布尔、日期、错误、数字，日期使用workbook.datemode。保留行列位置，明确formula&#95;expressions=not&#95;exposed&#95;by&#95;xlrd、计算结果为原文件缓存而非重算；finally release&#95;resources。与XLSX/openpyxl不可互换。测试应含1900/1904日期系统、错误值、空缓存、公式及大表；保留xlrd，不把缓存值当新计算证据。</span>

#### <span id="p0052">LibreOffice 原生DOC转换</span>

<span id="p0053">parse&#95;legacy&#95;word寻找本地soffice，创建临时独立UserInstallation profile，禁宏/活动内容和链接、字段更新；环境只留公共PATH/LANG/TMPDIR等。先5秒version探测，再headless转换DOC→DOCX，30秒wait。POSIX超时killpg，其他平台kill直接子进程并wait；无任务取消回调。转换成功还检查文件存在、0–8MiB并计算中间hash，再交python-docx解析，locator标converted。临时转换不是已提交Artifact；禁宏配置不是完整操作系统沙箱。源码未固定发行二进制、动态库及版本，实际版本和分发许可证仍待核。建议保留Office解码器，补真实DOC、取消、异常清理、进程后代和产物独立验证，不自研完整Office格式。</span>

### <span id="p0054">2. 可选网络 重试的真实可达性</span>

#### <span id="p0055">aiohttp 是保留死分支 不是当前XHS采集实现</span>

<span id="p0056">候选 lumenis/system/collector/runtime/xhs/client.py:64–111 的request在任何&#95;rate&#95;limit或import aiohttp之前，无条件抛出RuntimeError，说明私有接口适配器非生产、禁止真实请求。其后ClientSession和requests备用虽可静态识别，但当前函数永远不执行到那里。requirements关于“异步客户端、同步降级”的注释不能覆盖真实控制流。保留历史登记，不能据此安装或重新启用私有接口。</span>

#### <span id="p0057">tenacity</span>

<span id="p0058">collector.py:&#95;cdp&#95;online先经&#95;resolve&#95;server&#95;cdp&#95;url核SYSTEM注册worker，拒绝非法endpoint后才GET /json/version。可选tenacity装饰器最多3次，wait&#95;exponential(multiplier=.3,min=.2,max=1.2)，只重试URLError/OSError/TimeoutError，最终转False；ImportError时只探测一次。timeout参数是每次网络请求上限，不是总deadline，默认2秒的3次尝试加退避可能明显超过2秒。不能把重试当平台反爬绕过或新增授权。建议保留库，自研统一总预算/取消/故障分类，测试注册撤销、超时及未知结果。</span>

### <span id="p0059">3. 已重新深读的上游实现与产品影响</span>

<span id="p0060">本节上游均取官方GitHub精确tag的静态源码，逐文件与归档SHA256保留。与历史freeze版本相同并不证明其字节与历史wheel相同；本轮未运行这些下载源码。</span>

#### <span id="p0061">解析核心复核</span>

<span id="p0062">pandas v3.0.6 的 io/excel/&#95;base.py:ExcelFile 与 &#95;util.py:get&#95;default&#95;engine 已重读：未指定engine时识别XLSX，再取配置，auto映射openpyxl。产品没有另选引擎，故缺openpyxl后的pandas备用在默认配置下仍依赖openpyxl，不是独立恢复。上游支持配置其他引擎不代表本产品已启用。结论是静态已确认，未移除包做故障实测。</span>

<span id="p0063">MarkItDown v0.1.8 的 HtmlConverter.convert明确strict默认False。BeautifulSoup解析后删除script/style，再markdownify；RecursionError时警告并回退get&#95;text纯文本。产品没传strict，故深层HTML可技术成功但丢失Markdown结构。&#95;markitdown.py初始化Magika并identify&#95;stream猜类型；不能把扩展名判断或关闭插件理解为绕过识别模型。应保存降级标志，并独立检验标题/表格/层级，而不是强行替换解析库。</span>

<span id="p0064">pdfplumber v0.11.10 Page.extract&#95;text→get&#95;textmap→as&#95;string，extract&#95;tables→find&#95;tables→Table.extract，主要是PDF字符坐标、线段与单元格几何抽取。它不是OCR，也不理解业务事实。python-docx v1.2.0 Document→Package.open→main&#95;document&#95;part，核Word主文档content&#95;type；lxml/ZIP/XML组成实际底层，打开DOCX不等Word版式引擎或自动页码重建。xlrd 2.0.2 open&#95;workbook先inspect&#95;format，非XLS明确拒绝，再进入BIFF工作簿解析；不能拿它读取XLSX。</span>

<span id="p0065">Pillow 13.0.0 Image.open只读前缀识别格式并创建插件对象，存在懒加载；文件可识别不证明所有像素都已解码。&#95;decompression&#95;bomb&#95;check对超过MAX&#95;IMAGE&#95;PIXELS发警告、超过两倍抛错；警告不自动等同产品拒绝。产品封面/参考图/字幕字体链应保留像素、尺寸、帧数、ICC/字体、输出独立解码测试。其PIL许可及捆绑编解码库分开核，不把生成图片内容权利包含进库许可。</span>

#### <span id="p0066">Flask Werkzeug 与 Waitress</span>

<span id="p0067">Flask 3.1.3 wsgi&#95;app建立请求上下文，full&#95;dispatch&#95;request先preprocess&#95;request，再dispatch&#95;request按endpoint调用view，异常走handle&#95;user&#95;exception/finalize&#95;request；最后ctx.pop。Werkzeug 3.1.9 Response.get&#95;app&#95;iter对HEAD/1xx/204/304提供空body，对普通迭代器使用ClosingIterator；这些保证HTTP生命周期，不自动替业务做授权、事务、输入隔离或撤销复查。</span>

<span id="p0068">app.py条件ZB&#95;WSGI=waitress才进入serve，缺库回落Flask dev server；未读当前配置，不能写生产已用Waitress。静读Waitress v2.1.0是声明下限研究基线，不是历史部署版本证明。WSGITask.execute检查status/header类型与CR/LF、拒hop-by-hop header，迭代响应并finally close应用迭代器；Content-Length不匹配关闭连接。应保留成熟WSGI/路由框架，二改产品异常语义、响应中途撤权和持久化；用户认可后方可评估生产服务器设置。</span>

#### <span id="p0069">requests urllib3 WebSocket</span>

<span id="p0070">requests v2.34.2 Session.request构造Request、prepare、合并环境设置，Session.send经adapter，处理cookies和redirect；默认allow&#95;redirects=True。HTTPAdapter.send将timeout标量变为connect/read，交urllib3.urlopen时redirect=False，由requests上层自己处理重定向。连接/读取超时不是全链总deadline；自写安全transport必须在每跳重新核目标及授权，不能只看最初URL。产品公共源已有专门pin-IP与限定adapter，旧搜索/登录辅助路径也用requests，不能自动继承新transport策略。代理、凭据、cookie实际配置未读。</span>

<span id="p0071">websocket-client历史freeze为1.9.2，官方tag源码已保全；当前浏览器screencast、resident health、CDP辅助有导入，后续审计需把HTTP发现出的webSocketDebuggerUrl与SYSTEM注册目标绑定，重定向与Origin不能依靠库名保证。该库提供帧/握手/网络通信，不提供业务权限或“只读浏览器”的语义。真实浏览器会话本轮未连接。</span>

#### <span id="p0072">jsonschema referencing</span>

<span id="p0073">MCP &#95;schema&#95;validator只允许object和2020-12方言，深度48，拒绝非#开头的$ref/$dynamicRef；使用Registry(retrieve=deny)阻断外部资源。jsonschema v4.26.0 iter&#95;errors只分派已注册VALIDATORS的关键词，未知关键词不自动报错；validate遇错误抛出。产品未传FormatChecker，故schema format声明不能当已做完整格式验证。referencing v0.37.0 get&#95;or&#95;retrieve先本地资源/爬取，再调用retrieve；产品deny提供了具体网络禁取边界。结构通过仍不是授权、工具安全或内容可信；保留库，强化业务字段与效果合同。</span>

#### <span id="p0074">cryptography 配置与可观测</span>

<span id="p0075">产品 training&#95;receipts.py 使用Ed25519签名验证和序列化，cryptography==50.0.2被固定。其公开许可为Apache-2.0或BSD-3-Clause双选，底层Rust/OpenSSL与打包 notices另核。签名只能证明匹配公钥签过同一规范字节，不能证明训练质量、来源权利或当前授权；应由现有Permission/训练owner管理密钥身份、payload规范和撤销。不要自研签名原语。</span>

<span id="p0076">python-dotenv在config读取配置，PyYAML用于质量规则/提示登记；本轮仅读调用源码，未读配置中的私密值。psutil用于进程发现/资源和回收，PID本身会复用，应核进程身份与所有权，不能将检测到同名进程当当前worker。yyds&#95;logger可选增强：模块顶层import且底部创建四个核心logger，不能将类级探测优化视为整个模块无实例化或文件IO。UnifiedLogger实例构造失败回stdlib logging，prod选择JSON并不自动脱敏；当前历史freeze无该包，实际运行来源/具体版本未核。保留标准logging回退，完善秘密过滤、错误反馈、文件句柄与关闭测试。</span>

#### <span id="p0077">Alembic SQLAlchemy</span>

<span id="p0078">alembic/env.py通过engine&#95;from&#95;config和NullPool打开连接，target&#95;metadata=None，SQLite render&#95;as&#95;batch，离线输出SQL或在线事务执行。官方Alembic rel&#95;1&#95;19&#95;1 command.upgrade选择&#95;upgrade&#95;revs；stamp选择&#95;stamp&#95;revs，只标版本状态而非重演结构迁移。声明“已stamp”不能证明表结构符合目标，也不能自动授予本轮迁移权限。SQLAlchemy是迁移工具传递/显式导入，不等整个产品数据层已切换ORM。应保留工具，先核现有数据库结构、备份恢复、升级降级与跨版本回读；本轮无连接/迁移执行。</span>

### <span id="p0079">4. 数学与统计依赖的实际算法职责</span>

<span id="p0080">候选 statistics&#95;methods.py重新追踪18个方法及其imports，另读statistics&#95;mmm.py采样模型和trend&#95;api.py趋势入口。包负责数值计算，输入来源、方法适用条件、缺失值、权限、结果保存和业务解释由原产品owner承担。</span>

<span id="p0081">NumPy提供有限数数组、矩阵、向量运算和SVD等；SciPy提供MILP、优化、积分、概率分布和距离，而不是产品自研求解器。portfolio调用milp/Bounds/LinearConstraint；Hawkes、Beta排名与合成控制调用minimize；Bass调用least&#95;squares；实验用beta和quad；离散变化用rel&#95;entr；相似性用cdist。每一项都需核success/status、边界、目标函数与残差，失败不应被曲线或有限数掩盖。BLAS/LAPACK/HiGHS等原生实现和链接库没有随顶层包tag自动获得部署闭包证明。</span>

<span id="p0082">statsmodels 0.14.6用于OLS及趋势。STLForecast.fit先STL分解，然后将trend+resid交预测模型；get&#95;prediction把季节预测加回均值，但沿用底层pred.var&#95;pred&#95;mean。该区间没有在该包装层显式加季节估计不确定性。ruptures 1.1.10提供变化点，参数/最短段/惩罚影响切分；变化点不等业务事件因果。networkx 3.5提供图结构/中心性/连通分析，图节点和边来自已接纳数据，不等真实总体影响网络。建议保留成熟库，重点自研可解释输入合同与假设披露。</span>

<span id="p0083">scikit-learn 1.7.2承担等距回归校准、分类评估、TF-IDF/SVD与HDBSCAN。precision/recall/F1需要正确标签、split与未知类别处理；高分不证明外推。候选BERTopic明确字符2–4gram TF-IDF、最多5000特征、TruncatedSVD维数min(32,n-1,p-1)、固定seed再normalize；传入预计算embeddings，embedding&#95;model=None、BaseDimensionalityReduction和sklearn.cluster.HDBSCAN。已读BERTopic v0.17.4 fit&#95;transform：有embeddings时跳过其文本embedding生成；&#95;reduce&#95;dimensionality调用传入对象；&#95;cluster&#95;embeddings调用传入聚类器并读labels&#95;/probabilities&#95;。因此SentenceTransformer/UMAP/external hdbscan虽在安装依赖，不是本产品此路径选用的算法；不得宣传神经语义模型已启用。c-TF-IDF主题词仍需人审。</span>

<span id="p0084">OR-Tools 9.15.6755：产品以整数成本、收益、UTC有限时隙构建布尔选择、可选interval、每资源NoOverlap、预算、覆盖、前置与互斥。10秒、单线程、固定seed；只接受OPTIMAL，不把FEASIBLE当已证最优，并独立复核时间/预算/覆盖/互斥/目标与best bound。上游v9.15 CpSolver.solve把model.proto交原生SolveWrapper，Python不实现完整CP-SAT。官方tag不是精确wheel字节，原生求解器闭包另核。历史独立环境曾验证目标15与穷举相等、互斥后12、不可行与非整数拒绝；该证据不代表真实经营收益正确。</span>

<span id="p0085">PyMC 5.25.1 + PyTensor 2.31.7 + ArviZ 0.22.0：产品模型对adstock、饱和、渠道系数、截距、趋势、季节与噪声设明确先验；只训练段观测进入似然，宏观控制标准化统计取训练段。pm.sample两链、cores1、draws500、tune750、seed固定、target&#95;accept .95；ArviZ summary检查Rhat/ESS并统计divergence。自动NUTS/计算图及编译依赖属于上游，不是自研MCMC；稳定采样不自动消除内生性、混杂或代表性偏差。保留库，先核识别假设、后验预测、保留集、真实来源与业务解释。</span>

### <span id="p0086">5. 真实运行证据与尚未完成的闭包</span>

<span id="p0087">恢复备份可重新打开数学相关依赖历史验证报告、测试XML、安装JSON及freeze。它们记录独立环境42项统计测试通过（含2项主题/排程重点，不相加为44），新进程SavedWork重开，以及原共享protobuf7.36.2与OR-Tools要求&gt;=6.33.1,&lt;6.34冲突。独立副本改为6.33.6并新增18包，不等共享产品已安装此方案。19个官方wheel的来源/摘要及Requires-Dist已从原安装receipt提取，保留原证据hash。没有新执行或隐藏安装。</span>

<span id="p0088">完整Python锁仍有真实缺口：requirements主要为下限/范围，不能唯一解出全传递版本；部分生产声明未发现当前直接调用，浏览器研究清单不进入生产runtime；历史freeze是环境全貌，不能把104包全标产品集成。附录逐项列声明、静态入口、历史版本、官方研究tag和未验证状态。缺原wheel/动态库/目标平台实测的项目不标完成，不用库数量代替真实调用验收。</span>

### <span id="p0089">6. 输出 文本抽取 本地数据与二维码</span>

#### <span id="p0090">ReportLab 与输出字体</span>

<span id="p0091">word&#95;pdf&#95;export.py 的 export&#95;saved&#95;document 将标题、Markdown、来源及完整保存快照写入内存。DOCX逐行建立段落，PDF用Platypus流式排版，XLSX使用openpyxl；请求PDF不会在缺转换器时返回伪装的Word。PDF的pdf&#95;text&#95;context以进程内RLock串行化字体子集处理，载入产品NotoSansSC/NotoSansKR字体，逐字符查charToGlyph，缺字体或字形明确失败；html.escape后生成Paragraph标记，避免把原文直接当排版标签。字体权利与ReportLab代码许可证分别审核。直接export&#95;pdf先生成Word，PDF异常返回空字符串，可能留下Word或失败文件；但完整generate&#95;and&#95;export已清理失败PDF及中间Word、异常时清理本次文件，并在产物hash后再次复核来源和导出权限。删除失败被吞掉，属尽力清理；内存export&#95;saved&#95;document则异常不返回半成品。三层合同须分别验收。应保留排版库，补独立解析、中文/韩文/emoji缺字、多页表格、并发与中断产物清理。历史freeze记录ReportLab5.0.1；已取得官方同步GitHub镜像的5.0.1发布提交并深读Paragraph解析/CJK换行、Frame拆页、字体子集及PDF写出，核许可原文。部署wheel、字体及原生/可选依赖闭包仍未核，不标内核或整栈全审。</span>

#### <span id="p0092">BeautifulSoup 与 lxml</span>

<span id="p0093">public&#95;http.py:&#95;substantive&#95;body使用CSS选择器筛正文，剔除导航和页脚，以html.parser重建候选节点、decompose危险/装饰标签，再get&#95;text；按语义优先级和长度选正文。&#95;publication&#95;signals合并meta、JSON-LD与time等日期信号，而不是把抓取时间冒充发布日期。BeautifulSoup负责树及选择，抓取授权、URL安全和证据归属仍由fetch&#95;public&#95;url及业务边界负责。Sogou、WeChat、Instagram旧适配器也有导入，是否已注册启用须看服务章节，不能统一当当前可用来源。已从作者官方站取得BeautifulSoup4.15.0源码包，摘要与PyPI公开sdist一致，核MIT许可并深读产品指定的html.parser builder、树文本/删除及SoupSieve转派。其他builder及SoupSieve内核不在本轮深读范围。产品16000字符限制未覆盖最终description分支，且候选反复重建可能放大解析成本；坏HTML、编码和降级语义仍待测试。lxml虽无当前产品直接导入，却是python-docx/python-pptx等XML链的重要底层；其BSD风格许可之外，libxml2/libxslt二进制和构建选项需要部署级核验。</span>

#### <span id="p0094">feedparser 与 Atom</span>

<span id="p0095">web&#95;atom.py的AtomAdapter默认enabled=False。明确提供订阅地址后，先由统一fetcher抓取，拒被政策阻断的YouTube feed及重定向目标；再feedparser.parse(response.content)，这里传字节而非URL，不能把库自身可联网能力误记为此调用的网络出口。bozo且无entries报错；有entries的容错解析仍可能继续，之后要求稳定entry身份并生成hash。需测试坏XML、编码、重复ID、缺时间及混杂内容，保留解析器并由原owner承担来源权利。历史freeze6.0.14；现已从正确官方v6.0.14标签取得解析源码及BSD-2-Clause许可正文，尚非部署wheel证明。parse对bytes仍先尝试open，正常XML才回落内容解析；相对URL、编码与无敏感文件名形状夹具列入验收。</span>

#### <span id="p0096">DuckDB 与 Overture</span>

<span id="p0097">overture&#95;places.py的本地Parquet函数拒URL、UNC、通配符、相对路径及非.parquet，resolve(strict=True)后要求文件存在；duckdb.connect(':memory:')、read&#95;parquet、fetchmany按批转字典交规范化，finally close。这条调用没有自动下载Overture数据，也未主动load扩展；不能将DuckDB支持远程S3/HTTP宣传为产品已接入。DuckDB负责原生列式扫描与解码，Overture数据许可、来源release和数据质量另核。未继续下载超限整仓；已按固定commit取得v1.5.5 Python绑定与Parquet扫描、页解压及嵌套列部分源码，Python仓库gitlink与core v1.5.5一致，两个MIT LICENSE已核。当前native动态库、构建/扩展及实际部署仍未核。fetchmany限制单批Python行数，产品去重字典仍累计全部唯一候选，不能标为有总内存上限。建议保留引擎，测试极大/损坏Parquet、列类型、批量上限与取消，不自行重写列式格式。</span>

#### <span id="p0098">qrcode 与 vendored Colorama</span>

<span id="p0099">account/totp.py:generate&#95;qr&#95;code&#95;svg把otpauth URI交QRCode，纠错M、自动fit、SvgPathImage生成SVG再base64封装，未使用Pillow渲染。仓库实际带vendor/qrcode8.2及colorama0.4.6和各自license/RECORD，属于可逐字节定位的嵌入源码，不等运行时必然从vendor优先加载。已读qrcode.make、best&#95;fit和SvgPathImage：选择可容纳数据的版本并生成二维码矩阵，SVG把矩阵模块合并为path；图形生成不提供TOTP认证本身。异常返回错误SVG data URL，调用者若仅检查非空可能误判成功；且异常文本未XML escape，需专门测试。二维码包含绑定秘密，只能在获准的本地绑定页面显示，不应入日志/对外资源URL。qrcode与Colorama根许可为BSD-3-Clause风格；qrcode旧pyqr相关说明和可选成像依赖独立核。Colorama主要用于ANSI终端适配，无产品直接import证据，保留为vendor传递/工具层登记，不提升为独立用户功能。</span>

#### <span id="p0100">openpyxl 上游只读机制追加核验</span>

<span id="p0101">本研究工具环境已有openpyxl3.1.5，与历史产品freeze版本号相同；只读取其文件和MIT许可证并保留hash，未将它视为产品运行字节。ExcelReader.read按manifest、shared strings、workbook、样式、worksheet依次解析，read&#95;only时保留archive；ReadOnlyWorksheet.&#95;cells&#95;by&#95;row通过带上下文的源流逐行解析并填空单元格，Workbook.close才关闭&#95;archive。产品采用只读模式仍需明确关闭工作簿；底层局部with不抵消产品异常路径遗漏wb.close。data&#95;only=False保留公式字符串，库不充当Excel公式计算引擎。</span>

#### <span id="p0102">配置与签名的上游边界补充</span>

<span id="p0103">PyYAML6.0.3的safe&#95;load明确选择SafeLoader，load在finally dispose。产品data&#95;quality&#95;gate的契约加载调用safe&#95;load，解析异常跳过该契约；validate对未知rule type也continue，意味着无报错不能证明全部声明规则实际生效，应核契约缺失、未知规则及lint是否被真正执行。safe&#95;load限制构造类型，不等业务规则正确或输入大小有界。python-dotenv1.2.4的load&#95;dotenv缺路径时find&#95;dotenv，默认override=False，已有环境键不覆盖；产品读配置与对子进程继承配置需分开审。本研究没有执行load&#95;dotenv或读取任何环境文件。</span>

<span id="p0104">cryptography50.0.2的Ed25519Python接口委派Rust OpenSSL绑定；上游verify使用无摘要Verifier并以verify&#95;oneshot核原字节，失败抛InvalidSignature，sign同样为无摘要的一次签名。产品training&#95;receipts的规范JSON排序、无空格、拒NaN、严格base64、精确字段和短TTL是其额外协议，不由签名库自动提供。库不做Permission、重放存储或训练准入；不得把验签成功扩大为业务批准。</span>

### <span id="p0105">7. Whisper 实际声学与解码机制</span>

<span id="p0106">官方v20250625已重读audio.log&#95;mel&#95;spectrogram、model.AudioEncoder.forward/TextDecoder.forward、transcribe的语言/解码回退及decoding选择器。音频经Hann窗STFT、功率谱、固定Mel滤波、log10与截断归一化；编码器两层卷积降采样后加位置编码并经过注意力块，文本解码器以因果mask及音频cross-attention逐token输出。它是预训练神经转录模型，不是产品自行训练的语音识别内核。</span>

<span id="p0107">产品owned&#95;speech.py:436–438固定CPU FP32、task=transcribe、language&#95;hint、condition&#95;on&#95;previous&#95;text=False、temperature=0.0、beam&#95;size=1、word&#95;timestamps=True、无initial&#95;prompt。指定beam&#95;size进入BeamSearchDecoder，即便宽度1也不应误写为调用GreedyDecoder。上游decode&#95;with&#95;fallback把标量温度包装成单元素列表，因此此产品设置没有默认多温度阶梯重试；压缩率/低logprob标记不会凭空新增第二个温度。未指定语言时上游用开头最多30秒检测，语言标签准确度仍需真实多语音频验证。</span>

<span id="p0108">词级时间由timing.find&#95;alignment提取cross-attention，softmax/标准化、median filter、聚合选定heads，再动态时间规整对齐token与帧。时间戳是模型对齐结果，不是原音逐词硬标注；静音、重复词、跨segment尾界必须保留不确定性和人审。产品历史small结果的尾词越界警告不能通过截断文字掩盖。保留固定Whisper实现，优先二改输入质量、取消、边界映射和独立听审；本轮没有运行ASR或声称准确率达标。</span>

### <span id="p0109">8. 训练依赖的实际职责与分栈</span>

<span id="p0110">已逐行读候选owned&#95;training.py:490–670。NF4训练在metadata.version层固定8包：unsloth2026.9.12、unsloth&#95;zoo2026.9.8、transformers4.56.2、trl0.22.2、torch2.11.0+cu128、bitsandbytes0.50.2、tokenizers0.22.2、triton3.6.0；任一不同即T4&#95;TRAINING&#95;STACK&#95;VERSION&#95;MISMATCH。其中unsloth&#95;zoo、bitsandbytes、tokenizers、triton四个身份没有进入原import/requirements联合结果，因此额外纳入完整账。版本字符串相等不证明包完整或CUDA实际可用。普通NF4入口的八包门与checkpoint不同：后者另采集14包精确版本字典并匹配已批准framework&#95;lock&#95;sha256，包含PEFT、datasets和safetensors。</span>

<span id="p0111">NF4由FastLanguageModel.from&#95;pretrained从固定本地目录加载，local&#95;files&#95;only=True、trust&#95;remote&#95;code=False、token=False、load&#95;in&#95;4bit=True，额外复核返回模型路径与nf4配置；get&#95;peft&#95;model设置rank8/alpha16、特定投影层、固定随机种子和Unsloth gradient checkpointing。非NF4使用AutoTokenizer与AutoModelForCausalLM，本地固定revision、eager attention、bfloat16、Mxfp4Config(dequantize=True)、use&#95;safetensors=True，再用PEFT LoraConfig包裹指定线性/专家层。基础权重、量化解释和adapter权重是不同对象。</span>

<span id="p0112">数据由tokenizer.apply&#95;chat&#95;template生成训练文本，逐条在不截断情况下检查长度，再Dataset.from&#95;list；实际训练交TRL SFTTrainer/SFTConfig。回调在step&#95;begin、substep&#95;end、pre&#95;optimizer&#95;step复核权限，在保存点检查已提交checkpoint；输出目录创建前及train前也有检查。report&#95;to=none、push&#95;to&#95;hub=False并不替代整体进程隔离。所有路线检查新增optimizer step；显式有限train&#95;loss检查限low&#95;memory/NF4路线，部分配方还核GPU峰值内存。原版TRL0.22.2对text-only会补EOS、默认tokenize并truncate，预检add&#95;special&#95;tokens=False与最终序列须逐样本比对；默认整段loss，不自动assistant-only。Unsloth补丁后的实际类待冻结。恢复路径交checkpoint adapter并防output重叠，不直接把文件夹存在当恢复成功。</span>

<span id="p0113">这些属于外部训练框架加产品自研准入/回执逻辑。PEFT、datasets、safetensors未在普通NF4八包常量中，本次也未获得真实明文版本；checkpoint却要求它们在14包字典中并匹配策略摘要，摘要无法反推出明文版本。不得据此把所有训练路径说成无锁，也不能用别的环境版本代填。统计CPU链的torch2.14.1+cpu、transformers5.20.1是另一环境，不能直接合并升级GPU训练栈。已读固定bitsandbytes0.50.2量化/反量化、Linear4bit、CUDA分派及8-bit优化器状态，并核原版TRL/Transformers相关函数。Unsloth精确发行源码、其实际Triton补丁kernel及部署二进制仍待核，不宣称整个GPU栈全审。现有训练历史不证明当前基础权重、GPU或业务质量可用。</span>

#### <span id="p0114">固定训练版本许可证追加</span>

<span id="p0115">已从官方固定源码地址取得TRL v0.22.2、Transformers v4.56.2、Tokenizers v0.22.2的Apache-2.0 LICENSE，bitsandbytes0.50.2及Triton v3.6.0的MIT LICENSE，以及PyTorch v2.11.0的PyTorch/Caffe2 BSD风格声明，逐文件保存SHA256。此证据关闭此前TRL网页读取失败的源文本缺口，不代表训练wheel、CUDA及其他捆绑库全部许可已核。Unsloth2026.9.12、unsloth&#95;zoo2026.9.8所试同名官方tag文件返回404，未以main分支冒充精确版本。</span>

<span id="p0116">9份恢复freeze未发现SQLAlchemy与PyPDF2版本；SQLAlchemy仅确认Alembic环境的engine&#95;from&#95;config/NullPool连接调用，target&#95;metadata=None且基线upgrade/downgrade为空。迁移版本戳、注释表数或测试文本不能证明生产schema正确或回滚通过。先冻结分发身份，实际迁移须另获明确授权。</span>

<span id="p0117">官方固定发行元数据补证：Unsloth2026.9.12声明Apache-2.0，unsloth-zoo2026.9.8声明LGPL-3.0-or-later。只关闭发行声明许可缺口，包内LICENSE/NOTICE与部署分发闭包未核，不能把全栈统称Apache或据LGPL推断不能商用、所有模型权重须开源。</span>

<span id="p0118"><br /></span>

## <span id="p0119">文档 HTML 与列式读取的固定上游机制</span>

<span id="p0120">研究日期：2026年10月17日（UTC）。主线产品源码：官方提交 4dab98ed6357133da9307de846180ed4f7bba5f5；候选B仅作差异对照。范围限定为 ReportLab、BeautifulSoup、DuckDB、SQLAlchemy 与 PyPDF2。本轮只读取静态源码、公开许可、历史冻结清单和测试文本；未安装依赖，未运行下载代码或产品测试，未迁移数据库，未修改产品、运行环境及实际部署配置。</span>

### <span id="p0121">一 版本身份与结论等级</span>

<span id="p0122">ReportLab：历史共享环境两份freeze均记录5.0.1，产品requirements仅为&gt;=3.6.0，浏览器研究清单另有4.4.9。官方发布文档说明MrBitBucket/reportlab-mirror由官方Mercurial仓库同步；本轮找到发布提交c4c83349b7272094f7413f726dcf206dbde7836d，其src/reportlab/&#95;&#95;init&#95;&#95;.py明确Version="5.0.1"。已固定读取排版、段落解析、字体子集和PDF写出函数及BSD-3-Clause风格LICENSE。该提交可用于5.0.1源码机制研究，但没有证明历史wheel与该提交逐字节一致，更没有核实当前部署版本。官方源码包下载页401、Mercurial标签页403均停止该路径，未绕过登录。</span>

<span id="p0123">BeautifulSoup：从作者官方站取得4.15.0源码发行包，632571字节，SHA256为288e3ca7d54b06f2ac191970bc275c19​39cb46d450b255bf6718b04aa37ab4f7，与PyPI该版本公开发行页的sdist摘要相同。已核包内版本及MIT许可原文，并深读产品实际用到的html.parser builder、树文本/删除和CSS转派链。这关闭此前仅凭项目元数据的源码与许可缺口；仍非部署wheel核验。产品要求&gt;=4.12.0，历史环境记录4.15.0。</span>

<span id="p0124">DuckDB：产品精确声明1.5.5。官方duckdb-python v1.5.5指向b236c8194ed14c7a7c685e0534dde501cc855b3a；该提交external/duckdb的gitlink指向d8cdaa33fda8df955cc76ef58a280f68f4cd43fa，与core仓库v1.5.5一致。分别固定取得Python绑定、结果取回、Parquet扫描/解压/嵌套列部分源码及两个MIT LICENSE。本轮不再下载超过原大小上限的整仓归档。实际加载的native文件、编译选项、扩展和wheel仍未知。</span>

<span id="p0125">SQLAlchemy：重新检查恢复候选全部9份&#42;freeze.txt，没有该包记录；产品所见入口为alembic/env.py和基线迁移导入。Alembic的要求不等SQLAlchemy精确版本。本轮没有任意选最新版或用研究机版本冒充部署版本，因此SQLAlchemy内核及精确发行许可仍标“身份待冻结”。</span>

<span id="p0126">PyPDF2：产品没有精确声明，9份历史freeze也无记录；只发现PdfReader备用导入。不能把pypdf或PyPDF2最新版本当实际使用版本。本轮只确认产品分支和质量合同，不对未知发行版宣称内核、密码支持、资源所有权或许可已完成核验。</span>

<span id="p0127">官方来源索引：ReportLab官方镜像说明 https://docs.reportlab.com/releases/ ；固定源码 https://github.com/MrBitBucket/reportlab-mirror/tree/c4c83349b7272094f7413f726dcf206dbde7836d ；BeautifulSoup发行来源 https://www.crummy.com/software/BeautifulSoup/bs4/download/4.15/beautifulsoup4-4.15.0.tar.gz ，摘要对照 https://pypi.org/project/beautifulsoup4/4.15.0/ ；DuckDB Python https://github.com/duckdb/duckdb-python/tree/b236c8194ed14c7a7c685e0534dde501cc855b3a ，core https://github.com/duckdb/duckdb/tree/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa 。逐文件URL、SHA256、深读函数行段在来源与阅读范围附录，正文不复制上游代码。</span>

### <span id="p0128">二 ReportLab 排版内核与三层导出合同</span>

#### <span id="p0129">2.1 产品实际传入什么</span>

<span id="p0130">pdf&#95;text&#95;context先持有进程内RLock，再注册或复用产品的NotoSansSC/NotoSansKR TTFont。每个字符按charToGlyph选择可显示字体；无字体或无字形明确失败。连续同字体字符组成font片段，用户文本先html.escape，再进入Paragraph；换行由产品生成br标签。因此这里不是把任意原始HTML直接交给ReportLab。锁覆盖story创建与build，不能把“上游每段单独创建解析器”误认为整个字体子集处理已经无共享状态。</span>

<span id="p0131">export&#95;saved&#95;document把标题、Markdown原文、来源和完整保存快照JSON逐行放入Paragraph，以A4、9pt、13pt行距、CJK换行构建BytesIO。Markdown在此作为文字，不会自动成为完整Markdown版式。字节只有build成功后才返回；缺转换器或缺字形会抛出，未以Word伪装PDF。此函数不创建输出目录或数据库，但调用它的业务owner仍负责权限和来源准入。</span>

#### <span id="p0132">2.2 上游如何把文字变成页</span>

<span id="p0133">Paragraph.&#95;setup为每段创建ParaParser，将XML样式标记解析成带样式的文字片段；解析失败抛ValueError。wrap根据可用宽度、首行/左右缩进分配行宽，wordWrap="CJK"时明确走breakLinesCJK。单片段用wordSplit，多片段用cjkFragSplit；行高来自leading或自动ascent/descent。split按剩余高度和孤行/寡行设置拆成两个Paragraph，不是业务层先行人工分页。</span>

<span id="p0134">SimpleDocTemplate.build建立第一页/后续页模板和正文Frame，再调用BaseDocTemplate.build。后者消费story：Frame.add先wrap，放得下则draw；放不下尝试split，把剩余片段放回队列；不能拆则换Frame/页，重复无法放入才抛LayoutError。Table.split先计算宽高，再按行拆分，只有配置允许才尝试行内拆分。产品简单Table没有自行实现完整跨页表格算法，也没有证明超长单元格必然成功。</span>

<span id="p0135">TTFont.splitString维护按PDF文档区分的字符到子集编码映射；缺字体字形的字符会映射0，冻结后新增字符会抛错。产品前置charToGlyph检查因此有真实作用。addObjects冻结各子集，写出字体宽度、ToUnicode映射和FontDescriptor，最后清掉该文档的字体state。字体嵌入有利于显示和回读，但不能代替字体许可核验，也不保证复杂组合字、emoji序列或阅读顺序正确。</span>

#### <span id="p0136">2.3 失败清理必须分三层写</span>

<span id="p0137">第一层，内存export&#95;saved&#95;document：不返回半成品字节，异常传播；未主动证明字节完整、每页可读或视觉无裁切。</span>

<span id="p0138">第二层，直接export&#95;pdf：先调用export&#95;word，之后才在try中生成PDF；PDF异常打印并返回空字符串，先生成的Word会留下。上游Canvas.save调用PDFDocument.SaveToFile，后者对路径先以wb打开，再GetPDFData并写入；所读版本没有包围整个写出过程的finally或原子改名。因此直接函数的布局/字体/写出失败应与成功产物明确区分，不能仅用路径存在验收。</span>

<span id="p0139">第三层，完整generate&#95;and&#95;export：当前主线425–507行已建立独立UUID目标及本次文件集合，失败PDF被删除，PDF中间Word被清理，整体BaseException时清理本次文件；成功独立Word可保留。产物读取hash后还复核来源使用权和DATA&#95;EXPORT权限。因此“整个导出链没有清理或没有导出后二次权限检查”不成立。其删除函数吞掉OSError，故这是尽力清理而非删除必成；直接调用第二层也不会自动获得第三层保护。后续验收应分别覆盖三层，避免为已有外层能力重复造轮子。</span>

#### <span id="p0140">2.4 真实应用方案与验收</span>

<span id="p0141">建议保留ReportLab排版内核，只在获准后增强产品合同：先冻结部署wheel/RECORD、字体文件摘要及其许可；保留已有锁、转义、字形拒绝、外层权限复核；评估统一异常分类、原子落盘及清理失败显式状态，而非替换整套PDF引擎。验收包括中文/韩文/拉丁混排、组合字符与不支持字形、字面量标签、多页长段/超长表格、三线程不同快照、磁盘写满/写入中断、撤权与清理失败。必须同时做独立文字回读和页面渲染，验证完整快照、来源与旧版本标记，不以PDF头或字体字节存在替代业务正确性。</span>

<span id="p0142">仓库test&#95;saved&#95;work&#95;pdf&#95;exports.py已有上述多语、字面标签、缺字体/字形、并发、外层清理等测试文本。本轮未执行；恢复历史验证材料中的XML按相应classname查找未找到可关联记录，不能把测试存在标成这轮已通过。</span>

### <span id="p0143">三 BeautifulSoup 树构造 选择器与正文合同</span>

#### <span id="p0144">3.1 实际函数链</span>

<span id="p0145">PublicHttpAdapter默认enabled=False；提供本次地址且被启用/调用后，fetcher取得PublicResponse，&#95;item将response.content字节交BeautifulSoup(...,"html.parser")。此处明确指定标准库HTML parser builder，不能把安装了lxml理解为当前链改用lxml。构造器选择builder；prepare&#95;markup用UnicodeDammit把字节转换为Unicode并记录编码/替换字符；&#95;feed把事件转为Tag/NavigableString树，收尾未闭合文本和标签。成功后清除原markup和builder对soup的环引用。它不执行JavaScript、CSS布局或网页权限判断。</span>

<span id="p0146">html.parser builder对重复属性默认保留后一个值，空属性变空字符串，并为标准空元素补结束处理。产品随后读取canonical、meta和date，故坏HTML、重复属性及编码误判可改变所选值。当前产品没有把original&#95;encoding或contains&#95;replacement&#95;characters记入结果，技术解析成功不等证据文字无损。</span>

<span id="p0147">Tag.select经CSS包装转派SoupSieve.select；缺SoupSieve会抛NotImplementedError。历史freeze虽记录soupsieve3.0.3，但本章节没有对该引擎进一步全审，不能将CSS选择算法全部归功于BeautifulSoup自实现。get&#95;text是遍历指定类型子字符串、可strip、以分隔符join；不是“可见正文”渲染。decompose先extract再逐节点清空字典/contents并标记销毁，是真正移除候选子树；不适合继续使用已经decompose的对象。</span>

#### <span id="p0148">3.2 产品业务算法及两个边界</span>

<span id="p0149">&#95;substantive&#95;body先按article/main等选择器收集候选，排除导航祖先和命中导航标记的节点；对每个候选序列化并重新建树，再decompose脚本、样式、导航、表单等。非语义候选少于500字符被拒，全部候选超过100000字符被拒；按语义优先级、再按正文长度升序选最短合格项。故算法不是“取最长正文”；相同优先级嵌套节点、摘要和正文共存时要专门验证。</span>

<span id="p0150">第一，16000字符限制发生在text变量上，最终content表达式在无article&#95;text且存在description时改用description.get("content")，该路径没有经过同一个截断。如果description标签无content属性，str(None)还可能成为非空文字“None”。这是主线静态控制流可确认的合同缺口；不等于网络下载无上限，统一fetch&#95;public&#95;url另有2MiB响应限制。</span>

<span id="p0151">第二，候选正文为空时会退回整个body.get&#95;text；该对象不是已经清理的候选副本，可能含导航等噪声。即使响应有2MiB界限，候选循环反复序列化和重建嵌套大节点仍可能放大CPU和内存。输出16000字符不限制此前的树构造和选择开销。</span>

<span id="p0152">&#95;publication&#95;signals从有限数量meta、JSON-LD、time和可见日期取信号，按日一致才标declared，不一致或不可解析分别保留conflict/unparseable。一个有效信号也可成为declared，不等多源独立验证；datetime.date比较没有先统一时区，只是页面声明的日期。canonical仅接受与已抓取地址同scheme/host/port且无凭据的目标，还拒把内容页塌缩成首页；这些是产品额外规则，不由BeautifulSoup提供。</span>

<span id="p0153">主线search将PublicSourceError/ValueError映射PROVIDER&#95;UNAVAILABLE，其余异常映射COLLECT&#95;ERROR；空正文也明确不可用。候选B新增fetch&#95;document的锁、限速与2MiB文档检查，并未改变本文&#95;html解析核心，不应把B新增方法描述成官方主线现有能力。</span>

#### <span id="p0154">3.3 旧调用与真实应用计划</span>

<span id="p0155">Sogou搜索、Sogou微信及旧微信/Instagram适配器同样用BeautifulSoup做选择、meta或正文抽取；这仅证明静态存在，不证明适配器已注册启用、平台授权可用或可以绕过公共transport。旧HTML选择器应作为独立输入合同，不继承新public&#95;http的所有政策。</span>

<span id="p0156">建议保留BeautifulSoup及明确html.parser选择；获准后先对最终content统一非空/类型/长度校验，显式记录正文/description/body降级来源和编码损失，再评估候选数量及嵌套重建预算。以授权保全HTML构建黄金集：重复meta属性、缺content、超长description、嵌套main/article、纯导航、JSON-LD日期冲突、带不同时区同一时刻、乱码和深层坏标签。验收是正文准确及来源可解释，不是仅assert返回SUCCESS。不得为提高“通过率”自动启用旧采集或扩大抓取范围。</span>

<span id="p0157">MIT许可原文已从4.15.0源码包读取，包含保留版权/许可通知义务及html5lib来源说明；SoupSieve、编码探测器、Python标准库和网页内容权利分别登记。库许可不赋予网页转载、训练或商业采集权。</span>

### <span id="p0158">四 DuckDB 本地Parquet怎样成为地点候选</span>

#### <span id="p0159">4.1 产品输入 绑定和扫描</span>

<span id="p0160">read&#95;overture&#95;places&#95;parquet拒绝URL、UNC、通配符、相对路径和非.parquet后缀，resolve(strict=True)后核实普通文件；batch&#95;size只要求正整数且拒bool，没有上限。连接为:memory:，路径作为read&#95;parquet参数传入，不拼SQL；取relation.columns后fetchmany并zip成字典，交parse&#95;overture&#95;place&#95;rows，finally关闭连接。此函数未持久化业务候选、未下载Overture、未显式INSTALL/LOAD网络扩展。绝对路径限制不是授权根目录白名单；符号链接resolve也不证明文件内容在后续读取前未变化。</span>

<span id="p0161">固定上游Python绑定的read&#95;parquet注册到FromParquet。它通过GetPathLike取得路径列表，构造parquet&#95;scan表函数参数及binary&#95;as&#95;string、file&#95;row&#95;number、filename、hive&#95;partitioning、union&#95;by&#95;name等命名选项，再返回关系对象。产品未额外传这些选项，不应把上游可支持的远程/多文件能力扩大为本调用。</span>

<span id="p0162">FetchMany第一次调用ExecuteOrThrow(true)建立流式查询结果，随后DuckDBPyResult.Fetchmany循环Fetchone，最多生成batch&#95;size条Python tuple；Fetchone按native chunk取值，NULL映射None，其他类型经PythonObject.FromValue转换。因此输入中的names/brand/address等嵌套字段不是产品从Parquet字节自行解码。</span>

<span id="p0163">core ParquetReader先以只读模式打开可seek文件、取footer和schema；ParseParquetFooter检查PAR1/PARE标记、加密配置及footer长度。InitializeScan建立row-group状态、列reader和definition/repetition缓冲区。Scan在行组间切换，必要时预取列或整组，再按STANDARD&#95;VECTOR&#95;SIZE构造DataChunk；列层按page header选择数据页v1/v2或字典页，检查负页长，按codec解压，再按PLAIN、字典、RLE、DELTA或BYTE&#95;STREAM&#95;SPLIT等编码分派解码器。definition/repetition层用于NULL及嵌套值；StructColumnReader核子列行数一致，ListColumnReader对单个超长列表可能跨多个向量循环。这些是数据库/格式内核职责，不能靠几行Python替代。</span>

#### <span id="p0164">4.2 内存与失败不能只看fetchmany</span>

<span id="p0165">产品的selected字典累计每个stable&#95;source&#95;id的最佳候选，最终排序、生成candidates和unlocated&#95;candidates。去重先比字段完整数，再比confidence，完全相同则比规范化原行JSON字典序；它提供顺序无关选择，却不是恒定内存流式归约。batch&#95;size只限制每轮Python列表，不限制全部唯一地点、原生预取/解压缓冲、超长单行列表和最终返回对象。产品未把SG/分类筛选下推给relation，当前由Python逐行执行；不能声称已利用SQL谓词下推获得扫描成本收益。</span>

<span id="p0166">扫描、解压或类型错误会传播，产品finally仍关闭连接；上游Close清理当前result、native connection/database、游标与注册依赖。产品未调用Interrupt，也无取消回调/总deadline和显式memory&#95;limit/线程配置；“finally有close”不等可立即取消任意native工作。所读Brotli解压分支在失败throw前未调用DecoderDestroyInstance，而成功后才销毁；这是需进一步独立验证的异常清理观察，不在未复现、未核wheel与分配器前宣布可利用漏洞或自行修补上游。</span>

#### <span id="p0167">4.3 业务与许可边界 应用计划</span>

<span id="p0168">解析函数只产生评审候选：缺稳定ID或外国家地址被过滤；未知地点单列；confidence必须是非bool、有限且0–1；来源license字段状态与release缺失独立保留。source里的license字符串存在不是已经取得并审阅对应数据协议，release参数也不是自动验证实际Parquet来自该release。MIT引擎许可、捆绑压缩库许可、Overture数据许可及第三方来源条款必须分账。</span>

<span id="p0169">建议保留DuckDB内核，先冻结实际native/wheel、平台和扩展清单，再在获准的隔离副本中做资源与真实性验收。计划包括：批次1/2048与不同输入顺序输出一致；损坏footer、截断页、NULL/空列表/类型漂移、重复id、超长嵌套列表；大量唯一id的峰值内存；解压失败与取消后文件/连接资源释放；同路径内容变更；本地文件必须在授权范围且无额外网络访问。若资源预算不达标，再评估列投影/国家筛选下推、分块落地或外部去重，但先比较当前UNKNOWN/OUT&#95;OF&#95;SCOPE及确定性去重合同，不能随意改语义。</span>

<span id="p0170">仓库test&#95;overture&#95;places&#95;parser.py已有临时生成Parquet、batch&#95;size=1、地址/来源/去重测试代码；本轮未运行，也不能把合成文件测试当真实Overture全量数据验收。</span>

### <span id="p0171">五 SQLAlchemy 先补身份 再评估迁移可靠性</span>

<span id="p0172">alembic/env.py在offline分支只取配置URL，literal&#95;binds=True及named paramstyle生成迁移输出；online分支才读取ZBC&#95;DB&#95;PATH并覆盖sqlalchemy.url。非sqlite:///开头的值被当路径转为绝对SQLite URL；本轮没有读取环境变量值、配置中的真实连接地址或数据库。随后engine&#95;from&#95;config按sqlalchemy.前缀构造engine，显式NullPool，在with connectable.connect()中把connection交Alembic context，再begin&#95;transaction/run&#95;migrations。SQLAlchemy在此承担配置、方言/DBAPI连接和资源上下文，不是产品业务ORM模型层。</span>

<span id="p0173">target&#95;metadata=None，故这份env没有提供业务模型元数据给自动差异生成；render&#95;as&#95;batch=True是SQLite迁移渲染配置，不证明所有DDL都可原子回滚。基线e4278c4d1d79的upgrade/downgrade均pass；stamp基线只建立版本认知，不能把注释“54 tables”当程序已逐表创建/校验54张表。test&#95;alembic&#95;migration.py在复制的迁移目录和临时mini库里测stamp、加列、回退及行数，并恢复cwd/环境，但本轮未执行，不代表实际产品库已迁移或可回滚。</span>

<span id="p0174">实际应用顺序：第一步取得目标环境的SQLAlchemy分发元数据、安装路径、wheel/RECORD摘要，以及Alembic、Python、SQLite精确版本与历史安装receipt，允许只读且不import产品配置；第二步对该固定版本深读engine&#95;from&#95;config→create&#95;engine、NullPool连接/关闭和SQLite事务分支，核MIT发行许可；第三步经用户明确授权后才在隔离数据库副本验证迁移前后schema/data/hash、故障注入和恢复。不得因本研究角色主动运行upgrade、stamp、改URL、安装包或触碰生产数据库。缺身份时保持“未核”，不引用别人的freeze或最新版填表。</span>

### <span id="p0175">六 PyPDF2 备用分支不等独立可靠恢复</span>

<span id="p0176">parse&#95;pdf一次创建ParseResult。主try覆盖pdfplumber导入、open、遍历每页extract&#95;text/extract&#95;tables和locator构建；只有ImportError进入PyPDF2，因此不仅入口导入缺失，主try内部迟发的ImportError也可能触发备用。普通损坏PDF、密码错误或其他解析异常不会自动降级。</span>

<span id="p0177">备用PdfReader(file&#95;path)按pages逐页extract&#95;text，空返回替换为""，以双换行拼接，再按保留字符串长度生成pdf&#95;page定位和非空paragraph。它没有调用表格抽取、OCR或decrypt，也未记录实际备用包版本/解析路径。页偏移指向保留文本，不能解释为原PDF字节偏移或准确视觉阅读序。</span>

<span id="p0178">由于ParseResult在try外只创建一次，若pdfplumber已向tables追加部分表格后才抛ImportError，备用没有清空tables，可能形成PyPDF2文本与前一路部分表格混合结果；这是控制流允许的边缘场景，需故障注入确认，不声称现实数据已发生。备用代码没有显式close reader；未知版本可能自己复制路径数据到内存或持有流，故不能仅据缺close就认定确定的句柄泄漏。parse&#95;file外层才做大小/存在性检查和原文件hash，不能把其保护自动赋予直接parse&#95;pdf调用。</span>

<span id="p0179">建议先确认备用是否实际部署和需要保留。若要保留，应由明确批准的工作冻结一个实际/拟用PyPDF2版本、源码与发行许可，记录解析器和质量降级，并测试首选导入缺失、处理中迟发ImportError、加密/损坏/扫描空页、混排阅读序、分页定位及句柄清理。若拟迁移到pypdf或取消备用，这是新的代码/依赖变更决定，须先比较同一真实文件集的输出和失败合同并获明确授权；不能在研究中替换。无论选择哪条路，备用必须明确“文本级恢复、无表格/OCR保证”，失败不能变为空成功。</span>

### <span id="p0180">七 待审核后的实施清单 尚未执行</span>

<span id="p0181">1. 冻结身份：ReportLab与BS4取当前部署wheel/RECORD；DuckDB补native/扩展/codec；SQLAlchemy和PyPDF2先确定是否存在及精确版本。记录来源、平台、摘要、许可和传递库，不把历史freeze当实时部署证明。</span>

<span id="p0182">2. 固定合同：导出三层失败/清理职责、HTML最终content及降级来源、Parquet内存预算与候选语义、迁移前后可恢复条件、PDF备用文本/表格一致性。</span>

<span id="p0183">3. 先做离线黄金数据验收：授权副本与合成边界数据均保留hash，区分合成回归、真实文件效果和用户验收；所有失败记录不能被“最终通过”抹去。</span>

<span id="p0184">4. 只在用户批准具体变更后修改产品包装层。成熟PDF/HTML/列式内核原则上保留，自研重点是准入、预算、可取消、产物验证和来源链；不会因为发现缺口自动升级依赖或重写内核。</span>

<span id="p0185">5. 验收证据应能重新打开：测试命令/环境身份、输入与产物摘要、独立解析/视觉结果、异常资源记录、业务字段对照。本章节是研究，不宣称已完成上述实施或全栈安全审核。</span>

<span id="p0186"><br /></span>

## <span id="p0187">训练基础库与条件接入的固定上游机制</span>

<span id="p0188">研究日期：2026-10-17 UTC。性质：只读静态研究及拟议验收方案；未安装第三方包、未导入或执行下载源码、未运行序境、未连接GPU或调用产品API。未修改产品代码、数据库、环境及实际部署配置。</span>

### <span id="p0189">一 结论与证据边界</span>

<span id="p0190">1. 训练链不能只锁八个显眼包。 NF4普通训练在 owned&#95;training.py:510–515 校验八包版本字符串，PEFT、datasets、safetensors没有写入这个常量，A/B限定文档和清单检索亦未发现三者具体版本。与此不同，checkpoint路径在 &#95;FRAMEWORK&#95;PACKAGES、CheckpointPolicy.validate&#95;runtime、TrainingCheckpointAdapter.&#95;validate&#95;runtime 纳入14包精确版本字典并匹配策略摘要。准确表述是“普通训练门未显式固定三包；checkpoint要求精确运行时版本集合与已批准摘要匹配；本次仍未取得该集合的真实版本原文”，不能把三者任意选成最新版，也不能把checkpoint说成完全无版本约束。</span>

<span id="p0191">2. NF4不是一个固定kernel名字。 在取得的 bitsandbytes 0.50.2 源码中，4-bit权重、量化状态、计算dtype、梯度路径和CUDA形状/架构启发式共同决定执行路径；部分输入回退到反量化后 torch.nn.functional.linear。Unsloth精确发行物源码尚未取得，因此其是否绕过、替换或融合上述通用调用链仍待身份闭合，不可用Unsloth主分支宣称现场kernel。</span>

<span id="p0192">3. 固定TRL存在需验收的数据语义差异。 序境先按聊天模板生成纯 text，用 add&#95;special&#95;tokens=False 预检长度；原版TRL 0.22.2的 &#95;prepare&#95;dataset 对纯文本可补EOS，再按tokenizer默认方式tokenize、最后truncate。原版TRL对这种text-only输入默认是整段language-model loss，而非仅assistant loss。这是固定源码与产品调用的静态差异，尚非实测缺陷；Unsloth补丁路径可能改变它，必须记录实际类/函数身份再验收。</span>

<span id="p0193">4. safetensors文件不等于全checkpoint无pickle。 产品显式用 safetensors.torch.save&#95;file 保存CUDA RNG观察副本；Transformers仍用自身保存/恢复optimizer、scheduler、RNG和训练参数。恢复可信性来自产品签名准入、库存/状态摘要与恢复后测量组合，不能由文件后缀单独担保。</span>

<span id="p0194">5. feedparser缺口已关闭一层。 正确固定tag为 v6.0.14，取得官方LICENSE与解析源码；原无v路径404不表示版本源码不存在。它仍是历史环境出现、产品默认关闭的Atom条件路径，并非已上线服务。</span>

<span id="p0195">6. yyds-logger保持可选项。 产品有stdlib回退，但未证明其已启用或具体安装版。其缺失与初始化失败可降级，不等于任意日志写入故障都自动回退，也不等于stdlib分支具备相同request&#95;id、JSON、文件sink行为。</span>

<span id="p0196">7. 许可不能把Unsloth全栈统称Apache。 官方固定发行元数据：Unsloth 2026.9.12 为Apache-2.0；unsloth-zoo 2026.9.8 为LGPL-3.0-or-later。后者本次仅达到发行元数据证据，不等于已核完整LICENSE或分发义务闭包。所有部署、商业分发及修改判断需基于实际发行文件另审。</span>

### <span id="p0197">二 基线与可复查材料</span>

<span id="p0198">- A：产品源码commit 4dab98ed6357133da9307de846180ed4f7bba5f5 的研究副本。</span>

<span id="p0199">- B：已恢复的 恢复候选B源码。</span>

<span id="p0200">- 关键产品路径：lumenis/system/ai&#95;gateway/owned&#95;training.py、owned&#95;training&#95;checkpoints.py、owned&#95;inference.py、lumenis/system/collector/adapters/web&#95;atom.py、lumenis/unified&#95;logger.py。逐文件A/B哈希、函数行段及相同性见独立 产品文件身份与行段附录。</span>

<span id="p0201">- 固定上游来源附录：本次固定上游源码的官方URL、tag、全文SHA256、字节数、保存路径。函数阅读范围附录：Python函数/类的精确起止行（由AST静态解析，未import源码），供复核实际讨论函数，不代替阅读上下文。</span>

<span id="p0202">- 发行元数据证据附录：官方固定PyPI页面的发行文件标识、页面公布hash与许可字段；这些hash是页面声明，不是本次本地下载验证。</span>

<span id="p0203">- 版本检索范围记录：限定A/B文档、依赖清单及配置式文本的三包精确版本检索结果。空结果仅代表这个限定范围未发现，不代表所有历史机器均无版本记录。</span>

<span id="p0204">- 复用已有六包固定源码LICENSE索引 训练固定许可来源附录；本章节只追加证据，不重写原索引。源码tag内容的hash可复查，但tag仍非不可变commit签名；部署wheel和本地补丁身份仍应单独锁定。</span>

### <span id="p0205">三 PEFT 训练参数注入 适配器加载与恢复测量</span>

#### <span id="p0206">3.1 产品真实入口</span>

<span id="p0207">普通H100路线：LoraConfig(r=8,lora&#95;alpha=16,target&#95;modules="all-linear",target&#95;parameters=&#91;第7/15/23层mlp.experts的gate&#95;up&#95;proj与down&#95;proj&#93;) 后调用 get&#95;peft&#95;model(model, config)（训练文件551–560）。这同时依赖模块选择及裸参数目标功能，不能仅用“支持LoRA”的旧PEFT版本代替精确兼容性证据。NF4路线则调用 FastLanguageModel.get&#95;peft&#95;model，传七类投影模块、r8/alpha16、dropout0、bias none、Unsloth gradient checkpointing及固定seed。两个接口路径不能混为同一注入实现。</span>

<span id="p0208">推理文件159–179：PeftModel.from&#95;pretrained(model, local&#95;output, is&#95;trainable=False, local&#95;files&#95;only=True, token=False)，之后 model.eval()。这是本地候选适配器加载，未证明合并LoRA或生产发布。checkpoint文件1394–1413则以 get&#95;peft&#95;model&#95;state&#95;dict(trainer.model) 生成适配器/模型状态摘要。</span>

#### <span id="p0209">3.2 已可判断的机制与未闭合点</span>

<span id="p0210">产品的优化目标是增量适配器，而非单凭模型名就可推出全部基础权重可训练。实际可训练参数由上游注入器、target匹配、modules&#95;to&#95;save及模型结构决定；目前缺少实际PEFT版本和已加载模型树，不能声称所有目标均命中，更不能把训练loss下降当作目标命中证明。训练后仅检查 adapter&#95;config.json、adapter&#95;model.safetensors 是非空常规文件并计算hash（训练686附近），这能确认文件产生，不能单独确认适配器参数集合正确。</span>

<span id="p0211">恢复摘要采用PEFT公开状态提取函数，再由产品 training&#95;state&#95;sha256 对类型、形状、精确张量字节等作确定性编码（checkpoint125起），并非直接hash某个pickle容器。这个选择减少容器元数据差异，但仍依赖所用PEFT版本对state&#95;dict键的选择/规范化一致。升级PEFT即使仍可加载适配器，也可能改变状态键或目标处理，从而必须重新冻结框架摘要与验收。</span>

#### <span id="p0212">3.3 失败恢复与数据边界</span>

<span id="p0213">缺库会被训练外层ImportError转换为 LOCAL&#95;TRAINING&#95;DEPENDENCIES&#95;UNAVAILABLE。参数不支持、target未命中、结构变化等非ImportError如发生在输出目录建立前，不会进入内层训练状态落盘异常块；不能承诺每种加载失败都有 training&#95;status.json。输出目录以 exist&#95;ok=False 创建，重试不能简单复用上次目录。恢复必须走已准入checkpoint，而非根据文件存在自动续训。</span>

<span id="p0214">当前处置：不选任意PEFT版本源码作实际版本；待提供/采集历史受控环境版本、wheel/RECORD或构建锁，再逐函数核对 get&#95;peft&#95;model、LoRA target模块/参数匹配、PeftModel.from&#95;pretrained、get&#95;peft&#95;model&#95;state&#95;dict、save&#95;pretrained。此处完成产品调用合同研究，PEFT内部源码闭包仍明确待核。</span>

### <span id="p0215">四 datasets 从受控训练记录到实际消耗行</span>

<span id="p0216">产品仅以已经预检的训练记录渲染出 {"text": text} 列表，调用 Dataset.from&#95;list(rows)（528–541），本调用没有 load&#95;dataset、远端仓库地址或dataset脚本入口。输入消息中的内容仍是训练数据，不构成执行指令；是否进入缓存或多进程及序列化实现须由具体datasets版本查证，不能把“输入本地”扩大为“依赖绝无其他IO”。</span>

<span id="p0217">原版TRL 0.22.2 &#95;prepare&#95;dataset（847–1025）先在Dataset上设置清理None值的transform，再按数据形状决定ChatML/模板/补EOS，经过map tokenization，再packing或truncate。序境传入的是text而非messages/prompts-completions，因此常规路径是补EOS→text tokenizer→截断。assistant&#95;only&#95;loss默认false，completion&#95;only&#95;loss=None将根据列推断，对text-only为false；collator会屏蔽padding，但没有由产品提供的assistant/completion mask。不能把聊天模板中的角色标记理解为自动loss屏蔽。</span>

<span id="p0218">checkpoint包装器在SFTTrainer完成构造之后，取 trainer.train&#95;dataset的实际处理后行 计算row&#95;hashes，构建数据游标，再add&#95;column内部行标识。collator要求单条list，检查标识和行摘要，交给原collator，并把标识交给重载training&#95;step；训练step完成后再提交已消费批次（checkpoint832–865、1208–1243）。这比只存原JSONL位置更接近实际训练消费顺序；但并不自行保证模板语义正确。序列采样器、单worker、无drop&#95;last、无packing和固定seed是恢复合同组成部分。</span>

<span id="p0219">恢复时需要数据顺序摘要、数据位置、梯度累积边界及已完成optimizer步匹配，不能只用 global&#95;step 估计恢复后的下一条样本。实际datasets的from&#95;list/Arrow构造、with&#95;transform/map/select/add&#95;column内部实现及许可仍待精确版本冻结；本次不以latest库研究替代该缺口。</span>

### <span id="p0220">五 safetensors 两类用途与checkpoint可信边界</span>

<span id="p0221">1. 非NF4基础模型加载显式 use&#95;safetensors=True；最终适配器文件要求 adapter&#95;model.safetensors 存在且非空。上游Transformers &#95;save（4285–4333）对PEFT模型委托 save&#95;pretrained(...,safe&#95;serialization=args.save&#95;safetensors)，不应误写成产品直接序列化所有适配器张量。</span>

<span id="p0222">2. 产品checkpoint &#95;write&#95;observations（1415–1430）显式调用 save&#95;file({"cuda:0": cuda&#95;rng}, target)。写前检查目标不存在且不是符号链接。它是CUDA RNG观察副本，不是替代所有框架checkpoint文件。</span>

<span id="p0223">3. 原版Trainer &#95;save&#95;checkpoint（3318–3367）保存模型、optimizer/scheduler/scaler、RNG及trainer&#95;state；&#95;load&#95;rng&#95;state（3237起）仍读取 rng&#95;state.pth 并经 torch.load 恢复Python/NumPy/CPU/CUDA状态；&#95;save还以torch.save保存training&#95;args。不能声称整包无pickle或仅凭safetensors就可接纳不可信checkpoint。</span>

<span id="p0224">4. 产品包装每个恢复组件（model、optimizer&#95;scheduler、scaler、callback、rng），第一次物理读取前验证当前准入，禁止重复组件；RNG恢复后 &#95;finish&#95;load 要求五组件全部齐备、global&#95;step与游标一致、callback状态一致、实测状态摘要完全一致，才向owner提交完成。未知提交结果进入 CHECKPOINT&#95;COMMIT&#95;UNKNOWN，不自动第二次load（832–959、1059–1108）。</span>

<span id="p0225">5. 保存先取得签名reservation，将整个Trainer输出root临时切换到staging，调用TRL/Transformers原保存逻辑，再写观察材料与文件库存，检查期限并commit；finally还原output&#95;dir。部分文件已写并不等于checkpoint已提交。save异常置failed，未确认的commit不能擅自猜测成功或盲目重试（1337–1392）。</span>

<span id="p0226">safetensors具体Rust/Python版本、连续张量/共享storage检查、文件格式验证和底层写入原子性本次未获得实际版本源码，保持待核。产品写前存在性检查与第三方写函数之间是否存在TOCTOU条件，需在受控staging权限与实际版本下验收；不宣称已发现可利用漏洞。</span>

### <span id="p0227">六 Unsloth NF4与固定bitsandbytes调用链</span>

#### <span id="p0228">6.1 产品加载合同</span>

<span id="p0229">NF4八包常量：unsloth2026.9.12、unsloth&#95;zoo2026.9.8、transformers4.56.2、trl0.22.2、torch2.11.0+cu128、bitsandbytes0.50.2、tokenizers0.22.2、triton3.6.0。版本字符串比较不是wheel内容证明，不含PythonABI、驱动、CUDA动态库及本地补丁hash。</span>

<span id="p0230">产品 &#95;offline&#95;hf 临时设离线环境并在finally恢复，Unsloth禁统计，T4强制FLOAT32标志与原生BF16配方不同。FastLanguageModel.from&#95;pretrained 接收本地模型路径、load&#95;in&#95;4bit=True/full&#95;finetuning=False/local&#95;files&#95;only=True/trust&#95;remote&#95;code=False/token=False；返回后核对model.config路径以及 bnb&#95;4bit&#95;quant&#95;type == "nf4"。这是有价值的本地/模型身份约束，但不独立证明所有子模块、编译缓存与外部动态库均相同，也不能把trust&#95;remote&#95;code=False当成禁止已安装Python包执行代码的沙箱。</span>

#### <span id="p0231">6.2 已取得的通用固定链 不是Unsloth实际补丁证明</span>

<span id="p0232">- Transformers4.56.2 integrations/bitsandbytes.py 的 &#95;replace&#95;with&#95;bnb&#95;linear 递归匹配Linear/Conv1D，排除名单后构造 bnb.nn.Linear4bit，传compute&#95;dtype、double&#95;quant、quant&#95;type、quant&#95;storage，并冻结基础模块requires&#95;grad。</span>

<span id="p0233">- bitsandbytes0.50.2 Params4bit 管理压缩权重与QuantState；Linear4bit.forward（609起）取量化状态、选择计算dtype、转换输入和bias，再进入 bnb.matmul&#95;4bit，输出回到输入dtype。存储4-bit并不等于所有运算4-bit。</span>

<span id="p0234">- functional.quantize&#95;4bit（884–975）检查blocksize、NF4/FP4和输入dtype，调用 torch.ops.bitsandbytes.quantize&#95;4bit；QuantState记录原shape/dtype/blocksize/量化类型。compress&#95;statistics时还量化每块absmax并记录offset与第二层state。</span>

<span id="p0235">- CUDA注册层 backends/cuda/ops.py:383–420 按BF16/FP16/FP32及NF4/FP4选择原生符号 cquantize&#95;blockwise&#95;&#42;&#95;nf4；csrc/kernels.cu 的NF4映射函数及blockwise内核按块归一化，以每字节两个4-bit码打包。反量化根据NF4码表与块absmax还原近似值；嵌套量化需先还原absmax。它不是无损压缩。</span>

<span id="p0236">- autograd/&#95;functions.py:300–388,407–490 将权重整理为canonical压缩形状；无梯度和有梯度路径分别调gemm或autograd封装。反向对输入梯度用反量化后的基础权重乘法；该基础4-bit autograd未计算grad&#95;B，LoRA可训练增量由适配器路径承担。不能由这一文件证明Unsloth全部LoRA实现。</span>

<span id="p0237">- CUDA gemm&#95;4bit（934–982）按M、K与blocksize对齐、设备架构和dtype选融合自定义kernel或 &#95;dequant&#95;linear&#95;fallback。CUDA大M超过1536或K不对齐走反量化+F.linear，其他形状再经启发式。fallback不是失败恢复或CPU降级，而是正常数值实现分派，可能提高峰值显存。T4/ADA/H100不同运行轨迹不能靠同一个包版本等同。</span>

<span id="p0238">- C入口 csrc/gemm&#95;4bit.cu:46–135 再按编译宏与架构选SIMT、SM75 FP16 MMA或SM80+ MMA；FP32/极小M先走SIMT，SM75 BF16没有同一tensor-core分支。这个分派实现已读，具体MMA/SIMT头文件内循环未全面审计，不能称GPU内核逐指令全审。C/CUDA阅读行段另见 native-函数阅读范围附录。</span>

<span id="p0239">- cextension.get&#95;native&#95;library（348–375）选择并加载平台动态库；CUDA binary缺失会失败，环境中的BNB&#95;CUDA&#95;VERSION等还可能影响选择。产品的metadata版本门并未等价锁定实际native binary。真实验收需记录库路径/文件hash、驱动/runtime与GPU SM，不应读取/披露无关环境或凭据。</span>

#### <span id="p0240">6.3 优化器 Triton及tokenizers边界</span>

<span id="p0241">产品 optim="adamw&#95;8bit" 经原版Transformers trainer1533–1607实际选 bitsandbytes.optim.AdamW并传optim&#95;bits=8、is&#95;paged=False，不是必然实例化名称为AdamW8bit的类，也不是paged optimizer。其Optimizer2State对小于min&#95;8bit&#95;size（默认4096）的参数保留FP32状态，其余用uint8状态、qmap和按256块absmax；update&#95;step按状态dtype进入32-bit或8-bit blockwise内核。恢复必须完整保留这些状态和step，不能只保存LoRA权重后称“原位续训”。</span>

<span id="p0242">Triton3.6.0、tokenizers0.22.2在产品只表现为版本门/传递使用；本次未取得精确Unsloth发行源码到相应Tritonkernel、tokenizer实现的完整对应。因此不把Triton笼统等同所有NF4算子；已审bitsandbytes CUDA段明确经torch custom ops和C/CUDA库。需要先冻结Unsloth包，再查实际FastLanguageModel模型分派、LoRA补丁、fast&#95;dequantize、loss/RoPE/MLP及gradient-checkpointing调用和缓存；tokenizer还需冻结tokenizer.json、chat&#95;template与special-token配置hash。</span>

#### <span id="p0243">6.4 Unsloth发行身份与许可补证</span>

<span id="p0244">官方同名无v tag LICENSE此前404；官方仓库提交搜索只找到将安装脚本下界提升到这两个版本的提交，不能据此认定该commit就是发行源码。本次不以main或附近日期commit替代。</span>

<span id="p0245">固定发行页提供可供后续校验的身份：</span>

<span id="p0246">- <a href="https://pypi.org/project/unsloth/2026.9.12/">Unsloth2026.9.12</a>：2026-09-28发行、wheel unsloth-2026.9.12-py3-none-any.whl，页面SHA256 0b0a8d5694c693ff7a5183b1df073a2b​045f503193d76a0beec1696d1fef6013，许可表达式Apache-2.0。页面另说明可选Studio组件有不同许可；本产品FastLanguageModel调用不能自动归为Studio。</span>

<span id="p0247">- <a href="https://pypi.org/project/unsloth-zoo/2026.9.8/">unsloth-zoo2026.9.8</a>：2026-09-28发行、sdist SHA256 c9f7eb5919a0fef8a4d423cfac8d2912​5cfef623979f3551189cc94074c3ee91，wheel SHA256 740aacbb70f6f735ef367905cd753d32​1b3088aaff404ebfb4f1cdf9f62e56e8，许可表达式LGPL-3.0-or-later。</span>

<span id="p0248">上述发行页面是元数据证据，未重新尝试已失败的terminal PyPI访问，未下载/安装这些发行物，也未核包内逐文件LICENSE/NOTICE。许可证义务需按实际组合、修改与分发方式审核，不能由metadata一句话完成法律合规结论。</span>

### <span id="p0249">七 默认关闭的feedparser6.0.14</span>

#### <span id="p0250">7.1 固定身份与调用</span>

<span id="p0251">requirements仅下界 &gt;=6.0.11；历史freeze为6.0.14；本次取得 <a href="https://github.com/kurtmckee/feedparser/tree/v6.0.14">官方v6.0.14源码</a>，LICENSE为BSD两条款文本，包含源代码/二进制再分发保留声明等要求，另有文档许可段。它不证明当前安装版本。固定发行的依赖元数据与历史freeze的feedparser-sgmllib亦应纳入最终闭包，不能只记顶层一个库。</span>

<span id="p0252">AtomAdapter.enabled=False。输入必须提供feed&#95;url，初始及最终response.url都拦截指定YouTube feeds路径。产品通过公共源fetcher先取内容，再 feedparser.parse(response.content)；feedparser并非此产品调用中的主HTTP获取器。产品从entries取稳定id/link做hash，选择summary/content、日期与作者，交normalize&#95;item，返回Evidence关联元数据。空输入NOT&#95;CONFIGURED，解析有bozo且零entries则PROVIDER&#95;UNAVAILABLE；有bozo但仍有entries被接纳，说明这是容错解析而非严格验证。</span>

#### <span id="p0253">7.2 解析器机制与不能过度承诺的安全性</span>

<span id="p0254">固定api.py152–284：检测编码，处理doctype，优先SAX严格解析并尝试禁外部通用实体；遇SAX错误标bozo并转宽松SGML解析。mixin对HTML类内容按选项解析相对URL、调用sanitizer。sanitize功能不是全产品HTML/XSS安全证明，下游最终呈现仍须对应验证。</span>

<span id="p0255">重要边界：parse的 &#95;open&#95;resource（76–138）兼容URL、file-like、文件路径及原始内容。传入bytes不会走字符串URL分支，但实现仍先尝试原生open，再把无法打开的内容视作数据。因此“parse(response.content)绝无文件读取”不是源码支持的绝对结论。正常XML字节会被当作数据；未来验收应以专门本地夹具验证路径形状bytes不会意外读取可访问文件，且不得使用真实敏感路径。当前只是静态可达性观察，未执行攻击或认定线上可利用。</span>

<span id="p0256">此外，产品未把response&#95;headers或最终URL作为解析器base传入，解析器的相对URL与编码推断可能缺少HTTP上下文；需测试xml:base、相对entry link、非UTF8 Content-Type与实际内容声明冲突。max&#95;results限制的是返回entries切片，不是解析器处理整个响应的成本；输入体积/超时防线依赖fetcher合同。列表切片前调用 list(parsed.entries) 也不会省去前面的全量解析。源URL原值可进入raw/provenance，包含查询参数的日志/展示需检查按产品数据合同处理，不应把移除query的错误source&#95;url等同所有持久材料均已去query。</span>

### <span id="p0257">八 可选yyds-logger与stdlib回退</span>

<span id="p0258">产品requirements只有 yyds-logger&gt;=0.8.0，本次没有确认该版本发行身份或实际部署。公开旧版页面存在不等于符合此下界的已安装版本，不能拿0.5.1宣传或旧版MIT声明冒充当前固定许可。固定源码/完整许可证仍未闭合。</span>

<span id="p0259">本地 unified&#95;logger.py 的具体行为：</span>

<span id="p0260">- import yyds&#95;logger失败捕获ImportError，后续用logging.getLogger；若第三方import产生非ImportError异常，不在这个回退分支覆盖范围。</span>

<span id="p0261">- 可用时创建YydsLogger，传file&#95;name、log&#95;dir、serialize（APP&#95;ENV==prod）、console&#95;level/file&#95;level、language；构造/初始化块异常时写stdlib warning。模块底部会创建四个核心实例，因此“模块本身不做探测logger”不代表导入整个模块无logger实例/潜在文件IO。</span>

<span id="p0262">- &#95;log用 bind(kwargs).log(level,message)；stdlib用 log(...,extra=kwargs)，request&#95;id字段没有在stdlib分支自动注入。exception的kwargs处理与普通日志也不完全相同。flush/close仅操作第三方对象，stdlib生命周期依靠外部配置。</span>

<span id="p0263">- request&#95;context使用ContextVar token回滚；get&#95;logger按name:request&#95;id缓存。大量唯一request&#95;id可能产生大量缓存实例，需真实负载与资源关闭验收。当前无运行计数不能直接判内存泄漏。</span>

<span id="p0264">- patch&#95;logging只拦截明确白名单name，非“所有logging调用自动第三方化”；本次在A的lumenis Python范围检索，仅见函数定义与文档示例，没有找到外部调用或导入证据。不能由文件存在标为已启用。</span>

<span id="p0265">- 写入时 &#95;log不做异常回退。初始化后半段失败时已赋值的 &#95;yyds是否残留也需夹具核验；“初始化except发生”不能不经检查即等同后续一定走stdlib。</span>

### <span id="p0266">九 身份冻结计划 仅建议 未执行产品修改</span>

<span id="p0267">1. 先获取用户明确许可的实际训练环境只读物料：Python/platform、14包精确版本、发行来源、wheel/sdist/RECORD与自有补丁hash。优先现有构建清单/运行回执，不为研究擅自安装或连接GPU。</span>

<span id="p0268">2. 对PEFT、datasets、safetensors与yyds-logger取得实际版本后，下载或接收对应官方发行文本到隔离研究目录，仅解包和静态分析，核官方hash；不要用当前latest/附近tag猜测。</span>

<span id="p0269">3. Unsloth两包先按上述固定发行文件hash校验，再核包内LICENSE/NOTICE/METADATA及实际FastLanguageModel源码，建立发行物→源码文件hash映射；若缺tag，发行文件本身可成为固定研究基线，但必须与部署身份分开。</span>

<span id="p0270">4. 扩展native身份：torch wheel构建、CUDA runtime/driver、bitsandbytes实际.so、Triton编译配置/缓存标识、GPU型号/SM、模型与tokenizer文件hash。版本号相同但内容不同不得直接复用checkpoint基线。</span>

<span id="p0271">5. 把已核版本字典与checkpoint批准framework&#95;lock摘要互验。只取得摘要无法反推出版本内容；只有版本内容也不能代替owner批准策略。任何修改版本、代码或训练环境需另获具体授权。</span>

### <span id="p0272">十 真实应用验收计划 全部未执行</span>

<!-- table-01 -->
| <span id="p0273"><strong>编号</strong></span> | <span id="p0274"><strong>场景与样本</strong></span> | <span id="p0275"><strong>可观测证据</strong></span> | <span id="p0276"><strong>通过标准</strong></span> |
| --- | --- | --- | --- |
| <span id="p0277">T01</span> | <span id="p0278">相同八包版本、改一项未常量固定三包</span> | <span id="p0279">14包字典、策略摘要、错误阶段</span> | <span id="p0280">checkpoint不匹配拒绝；普通路径清楚记录其身份覆盖范围，不冒称八包门完整</span> |
| <span id="p0281">T02</span> | <span id="p0282">PEFT目标模块/裸expert参数命中与缺失各一组</span> | <span id="p0283">注入前后参数名/shape/requires&#95;grad、adapter&#95;config</span> | <span id="p0284">命中集合与批准配方一致，缺失明确失败；不以loss替代证明</span> |
| <span id="p0285">T03</span> | <span id="p0286">text长度max-1/max/max+1、结尾含/不含EOS、含特殊token</span> | <span id="p0287">渲染text hash、预检token ids、Trainer实际input&#95;ids与labels</span> | <span id="p0288">不出现未说明截断或重复special token；若需改语义另审批</span> |
| <span id="p0289">T04</span> | <span id="p0290">system/user/assistant三角色夹具</span> | <span id="p0291">collator标签掩码、loss参与token集合、实际SFT类源码hash</span> | <span id="p0292">与批准训练目标一致，不能因名字SFT就假设assistant-only</span> |
| <span id="p0293">T05</span> | <span id="p0294">单批、跨梯度累积、跨epoch恢复</span> | <span id="p0295">实际处理后row hash、cursor、global&#95;step、optimizer与RNG摘要</span> | <span id="p0296">下一消费位置正确，无重复/跳过；回执一致</span> |
| <span id="p0297">T06</span> | <span id="p0298">8-bit optimizer大小阈值两侧LoRA张量</span> | <span id="p0299">参数大小、state1/2 dtype、qmap/absmax/step</span> | <span id="p0300">FP32/uint8混合符合固定实现，续训恢复全部状态</span> |
| <span id="p0301">T07</span> | <span id="p0302">NF4不同M/N/K、K对齐/不对齐、允许GPU配方</span> | <span id="p0303">分派路径、实际.so hash、CUDA内存峰值、有限loss</span> | <span id="p0304">真实kernel与配方可解释，正常fallback不误判失败，峰值在许可预算内</span> |
| <span id="p0305">T08</span> | <span id="p0306">离线本地模型缺文件、路径改变、quant&#95;type错误</span> | <span id="p0307">网络隔离记录、加载错误、输出目录/状态</span> | <span id="p0308">拒绝而不静默下载替代；明确输出前失败可能无训练status</span> |
| <span id="p0309">T09</span> | <span id="p0310">保存中断、写满、commit响应丢失</span> | <span id="p0311">staging库存、owner查询结果、状态码</span> | <span id="p0312">未提交不冒称可恢复，不盲目重复commit/load</span> |
| <span id="p0313">T10</span> | <span id="p0314">合法签名但缺optimizer/RNG/callback或篡改文件</span> | <span id="p0315">文件库存、恢复组件集合、恢复后实测摘要</span> | <span id="p0316">fail-closed；safetensors存在不掩盖其余组件缺失</span> |
| <span id="p0317">T11</span> | <span id="p0318">精确Unsloth包是否补丁SFT/LoRA/kernel</span> | <span id="p0319">module/file/hash、函数指纹、编译缓存标识</span> | <span id="p0320">说明实际与本报告原版TRL/BNB链是否相同，不以包版本推定</span> |
| <span id="p0321">C01</span> | <span id="p0322">Atom保持关闭、显式本次输入的正/负夹具</span> | <span id="p0323">enabled/config快照、返回状态、Evidence归属</span> | <span id="p0324">默认无自动采集；来源及授权条件成立才手动验收</span> |
| <span id="p0325">C02</span> | <span id="p0326">畸形XML有entries/无entries、HTML、相对URL、非UTF8、大体积</span> | <span id="p0327">bozo、normalize结果、峰值/超时、最终渲染</span> | <span id="p0328">容错行为及渲染安全符合合同；资源限制有效</span> |
| <span id="p0329">C03</span> | <span id="p0330">原始bytes恰似本地文件名的无敏感夹具</span> | <span id="p0331">文件访问观察、解析结果</span> | <span id="p0332">证实不会产生越界读取；如需封装BytesIO/改实现先审批</span> |
| <span id="p0333">C04</span> | <span id="p0334">yyds缺失、构造失败、写入失败、关闭与并发request&#95;context</span> | <span id="p0335">选中后端、字段、handler数、文件/线程资源</span> | <span id="p0336">回退范围明确、request&#95;id不串扰、不丢关键日志，未启用不误报</span> |

<span id="p0337">所有验收必须在隔离、获得明确执行授权的环境里进行，先冻结输入/依赖/许可与资源上限，再运行最小样本；研究授权本身不包含修改代码、安装依赖、连接GPU或启动训练。</span>

### <span id="p0338">十一 交付覆盖与剩余缺口</span>

<span id="p0339">完成：A/B产品调用链、三包身份限制、checkpoint更强版本约束、固定TRL/Transformers/BNB函数机制、feedparser固定源码与许可、logger条件分支、发行元数据、真实应用验收矩阵。</span>

<span id="p0340">仍缺：PEFT/datasets/safetensors/yyds实际版本及对应源码许可；Unsloth两包固定发行物源码/完整许可；部署wheel/native闭包；真实GPU/运行结果；Unsloth补丁后SFT/tokenizer/kernel行为。不把这些缺口用最新版或主分支填成已核结论。</span>

### <span id="p0341">十二 LGPL发行声明的使用与交付审查范围</span>

<span id="p0342">这是一份工程合规核查清单，不代替对具体分发安排的法律意见。unsloth-zoo的LGPL-3.0-or-later当前只得到固定发行页声明，未核包内许可证、每文件例外、其他捆绑依赖或部署物。</span>

<span id="p0343">- 商业使用：LGPL不是“禁止商用”许可，亦不能仅凭LGPL推定整个序境必须采用同一许可。重点在具体使用、修改、组合和交付方式。<a href="https://www.gnu.org/licenses/why-not-lgpl.html.en">GNU对LGPL与专有程序的说明</a></span>

<span id="p0344">- 链接/组合交付：若向客户交付包含该库的镜像、安装包或环境，需核被覆盖库是否修改、保留声明及许可证文本，是否允许调试库修改所需的逆向，以及符合重新组合/重新链接或合适共享库机制的条件；相应源码与必要安装信息义务须按实际形态核对。Python import本身不能代替对可替换性和分发构成的审查。<a href="https://www.gnu.org/licenses/lgpl-3.0.en.html">LGPLv3第4节</a></span>

<span id="p0345">- 源码义务：修改并分发库，与只调用未修改库，应分别列出材料；“只给上游主页链接”不应未经审查就当作所有对应源码义务已满足。交付清单应保存准确版本、修改差异、LICENSE/NOTICE、对应源码取得方式及可重链接/替换验证记录。</span>

<span id="p0346">- 远程API：调用远端服务、自己运行库后仅提供API、以及把含库镜像交给客户，是不同事实，不应混称代码分发；不要把AGPL的网络条款机械移植到LGPL。具体镜像转交、托管合同及库修改情形仍须审核。<a href="https://www.gnu.org/licenses/gpl-howto.en.html">GNU许可使用说明</a></span>

<span id="p0347">- 模型权重：代码库许可、基础模型/适配器权重许可、训练数据权利、输出使用条件是独立审查对象。使用LGPL训练工具并不足以单独证明模型权重被其覆盖，也不足以证明权重可自由再分发；应核实际权重许可证与内容来源。</span>

<span id="p0348">需要的下一份材料是精确发行包内许可和部署/交付边界清单，而非“全栈开源/不可商用”的笼统标签。</span>

#### <span id="p0349">A B差异补充</span>

<span id="p0350">本次六个产品文件中owned&#95;training、owned&#95;training&#95;checkpoints、web&#95;atom、unified&#95;logger四文件A/B hash一致。owned&#95;inference全文件和requirements有差异；本篇引用的本地模型/PEFT加载行段在两份均相同，不能因此声称整个推理文件一致。B还包含token计数及formatter身份变化，超出本篇训练库范围；完整静态差异保存于A/B产品源码差异记录，不据此修改产品。</span>

#### <span id="p0351">Feedparser打包元数据补充</span>

<span id="p0352">固定v6.0.14的pyproject.toml仅定义setuptools构建后端；版本取自feedparser/&#95;&#95;init&#95;&#95;.py，依赖与Python下界在setup.py（明确feedparser-sgmllib&gt;=2,&lt;3和Python&gt;=3.10）。不可将当前main的pyproject布局或requests依赖投射到这个固定tag。</span>

<span id="p0353"><br /></span>

## <span id="p0354">前端 原生依赖与素材</span>

<span id="p0355">证据日期：2026-10-17 UTC。性质：只读源码与固定版本上游复核；没有安装、执行第三方包，没有构建产品、访问用户电脑或读取环境密钥，没有修改产品代码/数据库/运行环境。</span>

### <span id="p0356">一 结论与证据边界</span>

<span id="p0357">本次从恢复候选重新读取全部 JS/Dart manifests/locks，不沿用旧报告计数。再与恢复的 main commit 4dab98ed6357133da9307de846180ed4f7bba5f5 比较：app/、website/全目录和根 package.json/package-lock.json 共 482 个文件逐字节 SHA-256 相同，没有新增、缺失或修改。因此以下前端发现同时适用于该主线快照；不意味着远端之后的提交或任何部署实例也相同。逐文件证据见 两版前端逐文件核对记录。</span>

<span id="p0358">重新枚举得到 362 个锁记录：根 npm 3、Website npm 287、Dart 72。Dart 包含 67 个 hosted 包及 5 个 SDK 占位项；占位版本 0.0.0 不能识别实际 Flutter/引擎版本。357 个可定位官方归档均重新下载并与锁文件 SHA-512/SHA-256 完全吻合。此结果证明取到的包与锁一致，不证明包安全、已部署、已安装、运行正确或法律义务已经完成。</span>

<span id="p0359">最值得处理的事实：</span>

<span id="p0360">1. Windows 偏好存储确有“磁盘写入失败返回 false，但 Async API 丢弃 bool”的路径。SYS-05 目前依赖异常判失败，可能在重启前表现为已保存，重启后丢失；本次是源码级确定路径，未模拟真实 Windows 磁盘故障。</span>

<span id="p0361">2. Web 普通 HTTP 请求只给获取响应头阶段设 timeout，正文读取没有该 timeout。二进制请求虽有总超时，但 http 1.6.0 的 close 在响应头返回之后不再持有对应 AbortController，不能把 timeout 后 close 作为正文网络中止证明。</span>

<span id="p0362">3. video&#95;player 锁内有 Android/iOS/macOS/Web 平台包，并不等于 LUMENIS 各平台预览均完成；当前原生 MediaPreview 明确仅 Windows 进入播放器，其他原生平台显示提示。</span>

<span id="p0363">4. Astro 的构建/开发遥测属于真实依赖能力。所查项目构建入口没有显式禁用；源码不能证明实际环境发送过遥测，也不能证明已关闭。CI 仅跳过提示，不等于 record 被禁用。</span>

<span id="p0364">5. Transitions.dev 的确采用自定义许可，禁止把实质性集合重打包成竞争性 transitions library/motion pack；当前 generated&#95;result&#95;reveal.dart 有明确适配归属和调用者，并非只存在研究文档。</span>

<span id="p0365">6. Windows video&#95;player&#95;win 构建会触发 NuGet/WIL 下载，边界超出 pubspec.lock。NuGet fallback 有固定 SHA，PATH 中已存在的 nuget 不经过这段 SHA 校验；WIL 固定版本但没有在此 CMake 中固定包 hash。</span>

<span id="p0366">7. 75 个 npm 归档没有独立 LICENSE/NOTICE 文件，尽管官方 package.json 与锁内许可证声明逐项一致。不得把“357 个 hash 通过”写成“357 个许可证文本完整”。</span>

### <span id="p0367">二 全量账与计数口径</span>

<span id="p0368">附录保留完整的逐项紧凑总账，以下说明其字段与计数边界。每行含 ecosystem、name、version、唯一 id、所属锁及锁路径、直接/传递关系、用途分类、锁内 integrity、重新下载的 archive SHA-256、匹配结果、上游 URL、manifest license、许可证文件位置/hash、导入点和依赖边。npm 重复 name/version 若位于不同锁或嵌套位置仍保留独立记录，不混成“唯一项目数”。</span>

<span id="p0369">所有 npm 实例的官方归档 package.json license 与本地锁声明一致。Dart hosted 包按归档 LICENSE 文本识别 MIT/BSD-3-Clause/Apache-2.0，保留原文；这是许可证识别，不是法律意见。282 个 hosted/npm 归档带已保存的许可证/声明文本；75 个只有 manifest 声明（部分 README 提供额外组件条款链接）；5 个 SDK 项缺实际 SDK 身份。研究记录保留许可证、manifest、README及重点机制来源；各平台大型可执行二进制没有解包保存或执行，archive&#95;sha256 是下载时原始归档 hash，不是当前目录拼接 hash。</span>

<span id="p0370">npm 的 111 个 optional 记录包含不同 OS/CPU/ABI 的替代产物；它们不应同时计入某一设备已安装包。Website 177 个非 optional 锁项仍主要是构建链，并不等于 177 个浏览器运行脚本。产品已配置 Astro output: static。npm 的 dependencies 字段不能独自区分构建时与终端运行时，必须看构建和输出。</span>

<span id="p0371">Dart 分类保留 直接生产/直接开发/transitive。shared&#95;preferences&#95;platform&#95;interface 虽在应用 dev&#95;dependencies 中，但 shared&#95;preferences 等生产依赖也依赖它，不能标成纯测试。flutter&#95;test 的完整 SDK 图不可用，因此仅依赖 hosted manifests 推导的 dev-only/共享分类是保守局部结果，未到达的传递包不据此判闲置。Android/Linux 客户端已从当前需求移出，但锁和源码保留它们；不删除、不自动恢复，也不将其算作已验收平台。</span>

### <span id="p0372">三 真实调用与数据流</span>

#### <span id="p0373">3.1 Flutter 产品壳与路由</span>

<span id="p0374">Flutter、flutter&#95;localizations、flutter&#95;web&#95;plugins 属 SDK；入口/本地化/Web 路由策略使用实际 SDK import，锁内 0.0.0 是占位。go&#95;router 18.0.1 承担页面导航，不取得 Permission、Canonical Data 或后端业务身份的所有权。cupertino&#95;icons 1.0.9 是字体资源依赖，无 Dart import 不等于未使用；generated&#95;result&#95;reveal.dart:56–62 明确识别该注册字体。flutter&#95;lints 是 analysis&#95;options 规则，属于开发工具，不能以无 import 判缺失。</span>

<span id="p0375">精确 import 的文件/行号见 调用位置记录；test 与 lib 分开，统计是 import 出现次数而非业务调用次数。video&#95;player&#95;win 没有业务 Dart 显式 import，但其 pubspec 的 Windows 插件注册和 app/windows/flutter/generated&#95;plugins.cmake 把它接入构建，不能据此判为死依赖。</span>

#### <span id="p0376">3.2 Web HTTP 二进制和 SSE</span>

<span id="p0377">所有者：app/lib/core/transport/lumenis&#95;http&#95;transport&#95;web.dart，消费方通过现有 Core client 使用它；http 是传输实现，不是业务事实或权限所有者。</span>

<span id="p0378">普通路径（12–40）：request.validateBody → http.Client → http.Request（method/URI/headers/body）→ client.send.timeout(connectionTimeout) → incoming.stream.toBytes → 返回状态、headers、bytes → finally close。timeout 仅覆盖 send；响应头完成以后正文可以继续等待，且此函数没有 maxBytes 参数。</span>

<span id="p0379">二进制路径（43–111）：maxBytes 必须正数，禁重定向，先检查 Content-Length，再逐 chunk 累计检查；超时包围 &#95;sendBinaryRequest 全体。这防止无限大小的完整正文被正常接收，但不等于 timeout 本身取消底层 Future。</span>

<span id="p0380">固定上游 http 1.6.0 lib/src/browser&#95;client.dart:72–131 创建 AbortController、调用 fetch，在 send 的 finally 移除 controller；close:140–144 只 abort 尚在集合中的 controller。响应正文由 &#95;readStreamBody:168 起独立消费，Stream subscription 的 onCancel 才调用 reader.cancel。产品使用普通 Request，而非 AbortableRequest。于是：响应头之前超时随后 close 可以中止仍在集合中的 fetch；响应头之后的二进制超时仅结束等待，finally close 无法据此保证正文停止，&#95;sendBinaryRequest 仍可能继续读直到结束/出错/超过 maxBytes。普通路径还缺整体正文超时。两种路径必须分开描述。</span>

<span id="p0381">同一上游把 withCredentials 默认 false 转为 fetch credentials: same-origin；并非“完全不带 cookie”。cross-site include 不会自动开启。followRedirects=false 对 fetch 设置 redirect:error；遇重定向可能直接 ClientException，不必先得到 3xx。maxRedirects 和 persistentConnection 在 BrowserClient 中被忽略。</span>

<span id="p0382">SSE（114–155）直接用 package:web EventSource，withCredentials=true；取消订阅主动 close，onerror 结束以避免静默重连。当前 maxEventBytes 比较 text.length，实际是 Dart 字符串长度而非 UTF-8 字节计数，名称不可当字节级网络限额。未做浏览器网络/代理/跨域实测。</span>

<span id="p0383">建议验收（未执行/未修改）：延迟响应头、响应头后永久挂起、慢速 chunk、超限 chunk、主动导航取消分别验证；记录客户端终态与服务端连接真正关闭，不只验证抛了 TimeoutException。</span>

#### <span id="p0384">3.3 本地偏好与外观</span>

<span id="p0385">SYS-05 的 Sys05AppearanceController 用 SharedPreferencesAsync，key 为 lumenis.sys05.appearance.v1 和 wallpaper.v1；外观 JSON 与壁纸 base64 属本机呈现偏好，不是账户密钥、业务数据库或 Evidence。壁纸上限在业务控制器为 3 MiB。更新有 revision 与串行队列，避免快拖动后旧写回覆盖新状态。</span>

<span id="p0386">上游 shared&#95;preferences&#95;windows 2.4.1 lib/shared&#95;preferences&#95;windows.dart:306–318 先修改缓存，再 await &#95;writePreferences；374–399 遇不能定位文件或创建/写入异常时打印并返回 false。Async &#95;setValue 不检查返回值，clear:260–275 也不检查。SYS05:152–168 的 catch 因此对这种失败不生效；reset:190–211 以没有 exception 判断成功，同样存在误判。缓存还可能使同进程读回看到新值，普通 readback 不足以证明落盘。CTH SourceBrief 的 motion 选择（source&#95;brief&#95;panel.dart:42、108）也用 Async 存储。</span>

<span id="p0387">这是偏好持久化可靠性缺口，不应扩大成“业务 Canonical 数据一定丢失”或“已发生用户数据泄露”。需要 Windows 非可写目录/磁盘满/文件锁/重启读回证据，并考虑适配层或上游修复；实施前另需产品修改授权。</span>

#### <span id="p0388">3.4 文件选择与导出</span>

<span id="p0389">file&#95;selector 1.1.0 通过各平台实现呈现选择/保存对话框，cross&#95;file 承载 XFile。AI01 draft&#95;files 读用户选择的文本 bytes 后解码；SH01 media&#95;project&#95;files 选择媒体或将现有 ContentProjectFile bytes 保存；SH04 export&#95;files 保存已有导出 bytes；SYS05 appearance&#95;editor 读选择图像后交给控制器验证。调用点在 调用位置记录，具体 openFile/openFiles/getSaveLocation/saveTo 均保留原源码 hash。</span>

<span id="p0390">文件选择器不是 Source/use 权限授予者，用户选择文件不自动赋予外部传播权。Web 的 XFile.saveTo 与桌面保存对话框实现不同，不可把一个平台测试结果推广全部平台。此次未打开任何真实用户文件。</span>

#### <span id="p0391">3.5 原生窗口材质</span>

<span id="p0392">lumenis&#95;window&#95;material&#95;io.dart:11–14 只支持 Windows/macOS。Windows 调 flutter&#95;acrylic 1.1.4 的 initialize/setEffect；macOS 直接调 macos&#95;window&#95;utils 1.9.1 的 initialize、overrideMacOSBrightness、setMaterial。请求串行；异常返回 false；初始化失败清除缓存允许后续重试。UI 需要处理 false，不应把请求完成当材质已生效。其职责只是原生窗口外观，不是一般 OS 控制授权。</span>

#### <span id="p0393">3.6 视频播放器与 native 资源生命周期</span>

<span id="p0394">上游 video&#95;player 2.14.0 default&#95;package 仅 Android、iOS、macOS、Web；Windows 通过 video&#95;player&#95;win 3.3.0 implements: video&#95;player 注册，底层使用 Windows Media Foundation。当前 app/lib/features/shared/sh01/media&#95;preview&#95;native.dart:28–39 同时检查 Platform.isWindows 与 TargetPlatform.windows，其他原生平台走提示文案。锁内 video&#95;player&#95;avfoundation 存在不等于 macOS/iOS 预览已绑定。</span>

<span id="p0395">现有数据流：Core ContentProjectFile 的已取回 bytes → NativeMediaCache.create 检查类型/大小、受控 lease 目录、普通文件/路径验证、写入 flush → NativeMediaPlayer 接收本地 lease.path → VideoPlayerController.file → 播放/暂停/seek → dispose 完成 → 删除 lease/释放 slot。插件不直接获得业务 URL 或认证头。native&#95;media&#95;player.dart:25 将 allowBackgroundPlayback 设 true 是为关闭包自动恢复，产品控制器自行管理前台/覆盖状态；不能只看参数名断言产品允许后台播。</span>

<span id="p0396">native&#95;media&#95;preview&#95;controller 的 initialize 有 timeout，但注释和释放实现明确不因超时放弃原生所有权；release 不确定时保留 slot，不能提前转交播放器。这是正确方向的源级保护。Windows native create/dispose/codec/文件锁是否按期完成仍须真实原生验证；没有 DLL/PDB/链接映射、运行日志或设备，本报告不判 PASS。</span>

### <span id="p0397">四 构建链 下载与网络边界</span>

#### <span id="p0398">4.0 根 Node Playwright 采集工具</span>

<span id="p0399">根 package.json 声明 playwright ^1.62.1，锁定 playwright 与 playwright-core 1.62.1（Apache-2.0），macOS optional fsevents 2.3.2（MIT）。这不是 Website 浏览器 bundle，而是 Collector/浏览器辅助 Node 进程。rednote&#95;collector.cjs:245–262 在 SYSTEM 登记 endpoint/preflight 后 connectOverCDP，校验 context 身份，返回受控 browser/context；endpoint:225–240 拒绝远端地址、含凭证/query、特定旧端口等。依赖本身不提供 Source 权益或 Canonical 入库判定。</span>

<span id="p0400">同时保留独立 persistent-context 脚本：xhs&#95;search.js 和 inject&#95;cookies.js。后者从环境变量接收 cookie JSON，先调用登记 profile/域校验，再 launchPersistentContext、addCookies 和访问指定 RedNote 页面；该脚本带 --no-sandbox/--disable-setuid-sandbox 启动参数（inject&#95;cookies.js:18–24）。这是有实际外部/凭据副作用的工具能力，不能因为 root npm 名叫 tools 就认成纯离线开发依赖，也不能把审计当执行授权。本次只读脚本文本，没有读环境变量值、cookie、profile 或打开浏览器。Chromium/实际 CDP 浏览器版本、平台二进制及第三方 notices 未由 npm 的 playwright 版本单独确定。</span>

#### <span id="p0401">4.1 Astro 7.3.3 与 telemetry 3.3.3</span>

<span id="p0402">website/package.json dev/build/preview 直接运行 Astro；astro.config.mjs 声明静态输出与 zh-CN/en/ko。上游 astro CLI 调用 events/telemetry；固定 @astrojs/telemetry 3.3.3 dist/index.js:47–49 默认 enabled=true；isDisabled:65–69 检查 ASTRO&#95;TELEMETRY&#95;DISABLED、TELEMETRY&#95;DISABLED 和保存配置；notify:85 在 CI 跳过提示，但 record:104 只查 isDisabled，117–118 只是更换 CI anonymousId。</span>

<span id="p0403">post.js 向 https://telemetry.astro.build/api/v1/record 发 JSON。system-info 包括 Node/Vite/Astro 版本、OS/架构、CPU 型号/数量/频率、内存和 CI/WSL/Docker 信息；project-info 从 Git 初始提交或 cwd 派生 SHA-256 项目标识并记录包管理器；匿名不等于没有可关联元数据。报告只读了上游源码，没有运行其 Git 命令或遥测。</span>

<span id="p0404">在 website、.github、scripts 的所查入口未找到显式禁用变量。没有读取 .env 或用户配置，因此实际是否已全局禁用 UNKNOWN。不能把静态官网说成浏览器端偷偷上报，也不能把“源码有能力”说成已发生上报。若要求无非必要出站，可在经批准的构建环境明确禁用并以网络证据验证，当前没有做修改。</span>

#### <span id="p0405">4.2 NuGet 与 WIL</span>

<span id="p0406">video&#95;player&#95;win 3.3.0/windows/CMakeLists.txt:19–42：NuGet fallback 为 v5.10.0，SHA-256 852b71cc8c8c2d40d09ea49d321ff56f​d2397b9d6ea9f96e532530307bbbafd3；先 find&#95;program(NUGET nuget)，只有找不到时下载并校验。因此 PATH 命中的工具版本/hash 不由这一段锁定。</span>

<span id="p0407">WIL 固定 Microsoft.Windows.ImplementationLibrary 1.0.220914.1，经 NuGet install 写入 build/packages；CMake 未附 WIL 内容 hash。此次独立官方 nupkg 下载 SHA-256 为 b6b1d55bc8df309105cd7733fd200ccc​c678d703b61b31398a63a146a7148b09，内含 MIT LICENSE 与 ThirdPartyNotices（含 libc++ 材料）。此 hash 是审计证据，不是已部署包身份。NuGet.Client 5.10.0 固定源码 LICENSE 为 Apache-2.0；该源码许可不能代替 NuGet exe 所有打包第三方声明。</span>

<span id="p0408">没有下载执行 nuget.exe，没有执行 CMake，没有变更 PATH。构建供应链验收需实际所用 NuGet 路径/版本/hash、NuGet 源配置、解析出的 WIL hash、签名及 NOTICE 打包清单。必须与 pubspec.lock 分账。</span>

#### <span id="p0409">4.3 npm 原生平台包与 copyleft</span>

<span id="p0410">Website 锁含 sharp/libvips、lightningcss、esbuild、Rolldown、Astro compiler 等 OS/ABI 替代包。逐个 exact version/license/hash 见全账，不以其中一个平台代表全部。</span>

<span id="p0411">锁中 10 个 libvips 平台包声明 LGPL-3.0-or-later；3 个 sharp Windows 包声明 Apache-2.0 AND LGPL-3.0-or-later；sharp wasm 另含 MIT；12 个 lightningcss 包声明 MPL-2.0。libvips README 还列出多种编解码依赖许可证，因此主包 SPDX 不是二进制内所有组件的完整法律清单。需要区分只在构建机使用与将含这些库的运行包再次分发。对分发情形分别核实对应源码/修改、通知、重链接等实际义务；本报告不凭 package.json 对整个产品下“必须开源/完全无义务”的结论。</span>

### <span id="p0412">五 字体 图片 适配来源和可选工具</span>

<span id="p0413">三份捆绑字体及 OFL 文本实际存在且重新取 hash：Noto Sans SC、Noto Sans KR 的 name table version 均为 2.004-H2；Noto Color Emoji 为 2.057，内嵌 noto-emoji:20260911:fc4ca365e7c20e78278ae702aa20434bfe704c8f。字体 name table 是文件自述，尚未与官方同版本下载逐字节复比。完整版本/文件大小/hash/license 文本 hash 见 资产身份附录。OFL 通知必须随实际字体分发保留；改字体还需检查 reserved font name 条件。</span>

<span id="p0414">两张 wallpaper README 记录 Product Owner 于 2026-09-27 提供并指定使用，分别 182063 与 159638 bytes；照片不是公开 OSS，README 不等于可对任意第三方无限再许可。它们用于 SYS05 本地壁纸呈现，不是业务 Evidence。website/favicon.svg 为项目素材，未额外发现公开第三方授权证据。</span>

<span id="p0415">Transitions.dev 固定源 9398105c07dafe877e43197b71c15a10a3b0e3f6/skills/transitions-ui-generation/LICENSE.txt 已直接取回，SHA-256 605755af8c1e74a5b145ab0191a6a24b​28a51efc40127a8dce90a75339961e9c。允许个人和商业产品内使用/修改/交付，禁止实质性集合竞争性重包装；付费 Pro/Business 条款不能误套成此免费 skill 必须订阅。链接的完整 terms 页面本次返回 403，完整条款未复核，不能宣称许可审查完全关闭。</span>

<span id="p0416">实际适配位于 app/lib/core/generated&#95;result&#95;reveal.dart:11–18；固定字体白名单、实测 render geometry、结果版本与 arrivalToken、可跳过/用户偏好构成呈现层。CTH source&#95;brief&#95;panel.dart:457 调用它。根 register 的“documentation decision alone is not implemented”是日期化文字，当前实际代码已经存在，必须以此次源码为准；运行体验仍未验证。该效果不创建结果、伪造后台任务或修改 Permission。源树只有归属指向 register，发布包中是否带完整上游自定义许可需另核。</span>

<span id="p0417">flutter&#95;quill 在 register 中是 selected/not yet added；不在此次 pubspec/lock 内，不能算已安装生产编辑器。Android/Linux native targets 属保留非当前客户端范围。Ollama 等历史工具不在此账被恢复成活跃项。</span>

<span id="p0418">FFmpeg/ffprobe 是后端 Shared 媒体 owner 的外部工具，不是 Flutter 播放器自带的库。shared/content&#95;creation/rendering.py 调 &#95;ffmpeg&#95;path/&#95;ffprobe&#95;path，使用文件协议白名单、输出 probe、解码和响度测量等。FFmpeg 官方 legal 页面说明总体 LGPL，启用部分组件时进入 GPL；必须核实际二进制版本、configure flags、codec/library 和 notices。当前恢复产品树没有 FFmpeg exe/DLL 可作为现用实例，不能从 Python subprocess 调用反推已安装 build 或授权完整。相关更全的后端工具清单应与后端分报告合并，避免双重计数。</span>

### <span id="p0419">六 建议的关闭顺序 仅建议 未获执行授权</span>

<span id="p0420">P1：先处理 Windows 偏好“无异常即成功”的误判，以及 Web 正文超时/取消分离。分别验真实失败后重启结果、客户端和服务端网络资源释放。源码可解释风险，但不能代替故障复现与修复回归。</span>

<span id="p0421">P1：建立真实 release 的二进制清单：Flutter SDK/engine commit，Windows 插件与 NuGet/WIL，macOS/iOS 的 Apple native 解析结果，FFmpeg build、npm 实际平台产物。SDK 0.0.0、pubspec.lock、package-lock 都不是机器级 SBOM。</span>

<span id="p0422">P2：按分发形态补齐 license bundle；75 个没有完整 LICENSE 的 npm 包要向相应固定上游取得缺失文本或从父源码明确覆盖关系，不能套 MIT。尤其 libvips 内嵌组件、MPL/多重许可与 Transitions 自定义条款。</span>

<span id="p0423">P2：明确 Astro 构建遥测策略，在授权环境验证关闭或准许的出站；不擅改用户环境。平台验收按 Windows/macOS/iOS/Web 分开，插件存在不替代实际功能绑定和音视频播放验收。</span>

<span id="p0424"><br /></span>

## <span id="p0425">前端分发许可与构建辅助调用补核</span>

### <span id="p0426">结论与边界</span>

<span id="p0427">原始357个已核档案中，282个包含单独许可或NOTICE文件，75个npm锁实例没有此类文件。这个档案事实保持不变。本次对75个实例按共同上游项目分为10组，补得其中6组、合计71个实例所对应的固定版本父项目许可或组件声明；剩余4个实例仍只有发行manifest许可声明。父项目许可证不是对应平台二进制完整材料清单，不能将71个实例宣告为分发合规闭环，也不能将75个实例宣告为无许可证。</span>

<span id="p0428">这些实例主要属于Astro构建、平台可选绑定或终端辅助工具。锁文件存在不等于当前操作系统安装，不等于输出静态网站包含原生代码，更不等于用户已运行该集成。当前产品部署包和网站构建产物未执行或重新打包，因此最终分发边界仍需以发布制品清单核对。</span>

### <span id="p0429">固定版本逐组核验</span>

<span id="p0430">- Astro compiler-binding 0.4.1，共10个平台实例。withastro/compiler-rs固定v0.4.1根LICENSE为MIT，版权Astro contributors。补齐父编译器许可正文；尚未取得每个平台编译链接依赖的完整对应源码/通知清单。建议保留编译器，不以重写编译器作为许可证补档替代。</span>

<span id="p0431">- esbuild 0.28.2，共26个平台实例。evanw/esbuild固定v0.28.2的LICENSE.md为MIT，版权Evan Wallace。包身份依然由各自npm锁integrity与已下载档案hash绑定。源码许可对应已补，构建机器与发布制品是否包含这些可选二进制仍待清单确认。</span>

<span id="p0432">- Rolldown 1.2.9，共15个平台实例。固定v1.2.9根LICENSE为MIT，另明确要求保留外来代码通知；同版本THIRD-PARTY-LICENSE实际含Rollup contributors与Evan Wallace的MIT通知。不能只打包VoidZero一条版权而遗漏这两组通知。此文件不代表全部Cargo依赖或本机共享库已核。</span>

<span id="p0433">- Satteri 0.10.5，共9个平台实例。正确标签为satteri-v0.10.5，解析到commit b3d38e1e341c809b20b76a655e9b1601d11bd1f0，根LICENSE为MIT。随源码保留的MDXJS派生许可同时含Bruits和Titus Wormer，pulldown-cmark派生许可同时含Bruits和Google。third&#95;party目录另含CommonMark规范、测试资料及commonmark.js的各自通知；规范标注CC-BY-SA-4.0，不能因此把整个Satteri绑定改标CC-BY-SA，也不能因根MIT而忽略实际随源码分发的规范。是否进入编译后二进制或产品制品尚未证明，应按实际分发对象判断。</span>

<span id="p0434">- @napi-rs/wasm-runtime 1.2.4，共1个实例。napi-rs固定发行标签@napi-rs/wasm-runtime@1.2.4的根LICENSE含两份MIT版权通知，分别为Long Yinan和GitHub。两者均纳入通知候选清单；仍不能据根文件推定全部WASM传递组件无额外义务。</span>

<span id="p0435">- sharp-libvips 1.3.3，共10个平台实例。固定v1.3.3的README和LICENSE明确打包脚本为Apache-2.0；同版本THIRD-PARTY-NOTICES列出29个原生组件，涉及LGPLv3、MPL2、MIT、BSD及字体/图像专用许可。README区分Linux/macOS共享库、Windows静态构建和WASM静态构建。不能用脚本Apache覆盖这些二进制；也不能把构建工具存在直接推导为产品整体不可商用。需按实际链接、修改与分发方式逐项落实通知、许可证及适用的对应源码/可替换链接材料，发布前由负责许可审阅者确认。当前versions.json已提供组件版本身份，但全部对应源码与完整许可正文仍有缺口。</span>

### <span id="p0436">四个仍未补齐正文的实例</span>

<span id="p0437">am-i-vibing 0.4.0、process-ancestry 0.1.0与piccolore 0.1.3的正确固定标签均已解析并读取完整非截断Git树；各自树中未发现LICENSE、COPYING或NOTICE命名文件。前两者manifest声明MIT，后者声明ISC。此结论限于树文件名检查及已读发行manifest，不等于宣告作者没有授权，也不冒称已逐行排除每个源码头注释。</span>

<span id="p0438">boolbase 1.0.0的官方npm固定发行元数据声明ISC，tarball与已核锁完整性一致；官方仓库tag列表只返回v2.0.0，1.0.0元数据未给gitHead。不能拿v2.0.0或main的许可证冒充1.0.0精确来源。它是极小布尔常量辅助依赖，不构成面向用户的独立接入能力。建议发布前向固定发行来源补归属通知或在受批准的依赖升级工作中解决，当前报告不替换依赖。</span>

### <span id="p0439">验收队列与停止条件</span>

<span id="p0440">先从发布制品列出实际包含的JS、WASM、原生绑定、共享库、字体和NOTICE；把仅开发安装、条件未安装、随服务器部署、随桌面分发和仅静态网站输出分开。对实际包含部分关联锁完整性、父项目固定commit与各组件完整通知。尤其sharp-libvips按目标平台核对versions.json及实际链接方式；Satteri规范/测试资产只有确实再分发才进入对应资产义务判断。验收完成条件是具体制品与材料逐一匹配，而非把锁条目总数归零或统一贴MIT。以上是工程证据与待审措施，不是对所有商业发行形式的法律结论。</span>

### <span id="p0441">构建工具的实际辅助调用 环境识别与进程祖先</span>

<span id="p0442">Astro7.3.3的dist/events/session.js和dist/cli/agent.js确实调用am-i-vibing0.4.0的detectAgenticEnvironment()。本次除固定commit源码外，还重新取得该npm固定档案及process-ancestry0.1.0档案，逐一验证锁integrity后只读dist实现。detectAgenticEnvironment先遍历预设环境变量规则，首个匹配即返回工具id/name/type；无匹配时返回false/null。Astro会把识别结果的isAgentic、agentId、agentName、agentType加入CLI会话遥测payload，随后是否发送仍由前述telemetry开关决定。这条已读路径没有把环境变量原值或整个环境对象塞入该payload，不能从工具识别字段推断泄露了密钥；研究也没有读取本机环境值或实际触发遥测。</span>

<span id="p0443">重要范围区别：固定0.4.0的checkProcesses默认关闭，而上述两个Astro调用都没有传入启用选项。因此process-ancestry虽被import，其读取进程树的分支在这两个调用中不会自动执行。只有显式checkProcesses或提供祖先数组才进入该路径。process-ancestry0.1.0内部按平台调用ps或wmic，单次超时分别5秒/10秒，最多1000层并检测循环；失败返回空/部分结果，不是完整祖先树保证。不能把库的潜在能力写成当前产品已采集命令行，也不能把单次timeout当整次1000层遍历的总预算。</span>

<span id="p0444">建议保留静态构建能力，将构建遥测是否允许及哪些字段可发列入发布配置审核；任何开关修改需单独获用户明确批准。拟议测试只用合成环境字典、模拟祖先及拦截发送器，验证默认不启动子进程、未知环境的false/null语义、开关关闭时不发请求和payload最小字段。没有执行这些测试，当前结论是固定源码及档案静态证据。</span>

<span id="p0445"><br /></span>

## <span id="p0446">服务 MCP 模型与外部进程</span>

<span id="p0447">日期：2026-10-17 UTC。范围：只读源级机制、固定官方协议、恢复证据核验；不运行产品/第三方代码，不访问用户电脑，不读环境配置值、Cookie、凭证、Git 认证或会话，不改产品。</span>

### <span id="p0448">1. 两版身份与必须保留的差异</span>

<span id="p0449">本文 A = 官方树校验的 main commit 4dab98ed6357133da9307de846180ed4f7bba5f5（main4dab）；B = 未最终验收的恢复候选源码。B 不是已合并主线，也不是当前运行实例。前端 482 文件相同的结论不扩展到后端。</span>

<span id="p0450">本章使用 服务与原生接入身份账：74 个具体接入/适配项目记录，包含 15 个旧 /v4 collector、21 个 SYSTEM 适配器文件（其中五项为计划占位、快手仅有backend注入边界、XHS App Topic核心仍固定空返回）、3 个公共源辅助 owner、4 个广告 collector、7 个通知项目（四微信渠道、SMTP 邀约及邮件/SMS验证码占位）、8 个退休 provider 身份，以及模型、MCP、OSAI、GitHub、native 工具等。此数是明确界定的接入账，不是唯一供应商数；两个路径访问同一平台仍分别保留。Python/NPM 第三方库自身全账由相邻报告覆盖。</span>

<span id="p0451">关键版本差异：</span>

<!-- table-02 -->
| <span id="p0452"><strong>项目</strong></span> | <span id="p0453"><strong>A 主线</strong></span> | <span id="p0454"><strong>B 恢复候选</strong></span> | <span id="p0455"><strong>解释</strong></span> |
| --- | --- | --- | --- |
| <span id="p0456">user&#95;api</span> | <span id="p0457">任意符合基本格式的 HTTPS:443 base URL</span> | <span id="p0458">仅 api.groq.com/openai/v1，固定请求 URL，逐请求 Permission</span> | <span id="p0459">B 的收紧不能算主线已修复</span> |
| <span id="p0460">SMTP 邀约发送</span> | <span id="p0461">/api/kos/email/send 直接调用 kos&#95;ops SMTP</span> | <span id="p0462">同路径经 scoped executor，默认 adapter 字典为空而阻断</span> | <span id="p0463">“默认 SMTP 未绑定”仅适用于 B 该执行链</span> |
| <span id="p0464">Whisper</span> | <span id="p0465">只声明固定 base 权重</span> | <span id="p0466">保留 base，增加固定 small 评估模型与请求语言；stdin 改临时可 seek 文件</span> | <span id="p0467">small 历史证据不能给 A 作验收</span> |
| <span id="p0468">eSpeak NG</span> | <span id="p0469">无 offline&#95;formant&#95;speech.py</span> | <span id="p0470">新增外部 formant 合成 owner</span> | <span id="p0471">B-only，不是全产品当前能力</span> |
| <span id="p0472">旧采集编排</span> | <span id="p0473">collector&#95;service直接adapter.collect，默认可选全部registry平台</span> | <span id="p0474">经actor/scope权限与secondary&#95;collection，兼容start&#95;collect限定7个旧社交平台</span> | <span id="p0475">15类本体相同不代表两版入口相同</span> |
| <span id="p0476">SYSTEM计划项</span> | <span id="p0477">五项未默认导入；占位返回COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA</span> | <span id="p0478">目录导入但明确NOT&#95;SUPPORTED/NOT&#95;CONFIGURED，手动入口关闭</span> | <span id="p0479">目录可见不等于实现或启用</span> |

<span id="p0480">A/B源文件身份账 对每个关键文件给出两边 SHA-256。所有“已接入”均指源级调用关系；不证明当前凭证、账户、网络、部署或实际成功。</span>

### <span id="p0481">2. AI Gateway Groq 外部输入和退休 provider</span>

#### <span id="p0482">2.1 A 的具体行为</span>

<span id="p0483">A lumenis/system/ai&#95;gateway/user&#95;api&#95;adapter.py:30–38 接受 https、有 hostname、无 userinfo/query/fragment、端口缺省或443的任意目标；未限制 Groq 主机或固定路径。chat:69–109 重新读配置、redact&#95;for&#95;cloud，构造 base&#95;url + /chat/completions、Bearer 头，NoRedirect 拒重定向，读取最多2,000,001字节并拒超限，区分401/403/429等失败。NoRedirect 能防重定向转发，但不能把起始目标变成 Groq。</span>

<span id="p0484">上游入口不是完全无门禁：core.py:708–722 只在 external&#95;user&#95;input=True 且 is&#95;configured 时调用；lumenis/ai&#95;hub/service.py:191 是实际调用点。这个 bool/入口约定与“每个最终传输重新核验服务端主体/权限”不同；直接调用 adapter.chat 仍主要依赖配置。服务状态 configured 不等于 available，代码明确 CONFIGURED&#95;当前未验。</span>

<span id="p0485">风险定性：A 的通用目标能力与产品 Groq-only 的目标边界不一致（两版治理依据：00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md:34、164、952）；不能把“用户填写 URL”当已获得发送任何业务数据的批准，也不能仅因私有 host 可能可配置就声称已成功 SSRF/泄漏。本次没有调用网络模型或读取 key。所有 source-bearing 业务调用仍应使用现有 typed SourceUse/Permission owner。</span>

#### <span id="p0486">2.2 B 收紧到哪里 仍没有证明什么</span>

<span id="p0487">B user&#95;api&#95;adapter.py 增加 GROQ&#95;BASE&#95;URL/GROQ&#95;CHAT&#95;URL；configuration&#95;error 拒控制字符、替身主机、userinfo、非443、query/fragment及替代路径，允许规范主机及可选尾斜线，真正发送使用常量 URL。chat 要求 external&#95;user&#95;input is True、合法有限温度/timeout及正整数 max&#95;tokens；冻结配置后使用同一份构造请求，发送前重查选择和配置未变。</span>

<span id="p0488">&#95;conversation&#95;permission 需要 Flask request context，从 get&#95;current&#95;user(read&#95;only=True) 或服务端本地 workspace principal 取 actor；以固定 Groq URL 加请求 body 的 SHA-256 形成资源，调用 check&#95;shared&#95;workspace&#95;effect / AI&#95;CALL，非明确 allowed 即阻断。缺服务端 Permission 或上下文不能退化成允许。这比只靠客户端 actor 或 approved 布尔值更强。</span>

<span id="p0489">本次只证明 B 有上述机制；没有证明 Groq 账户、模型有效、额度、输出质量、业务 Source export 许可或接口当前连通。官方兼容文档 https://console.groq.com/docs/openai 本次下载返回403，不能声称完成在线账户/模型验证；固定主机的结论来自本产品代码。</span>

#### <span id="p0490">2.3 退休身份与 owned 模型分开</span>

<span id="p0491">providers.py:19 明确退休 zhipu、ollama、lmstudio、llama&#95;cpp、ark、qwen、openai、deepseek；旧名称和 env&#95;key 不是当前可调服务。channel 的兼容 dispatcher 拒退休/disabled provider，不能恢复为自动 fallback。openai provider 身份被禁用与采用 OpenAI 开源 gpt-oss/Whisper 权重是不同事项，不能把两者合并成“OpenAI 已接通/全被禁用”。</span>

<span id="p0492">owned&#95;service、owned&#95;inference、owned&#95;training 有显式 binding/admission、模型与数据 pin、checkpoint/reload 契约；有实现与当前有获准活跃执行器是两层证据。当前未读取真实服务 slot/数据库或发起推理，实际 bound 状态 UNKNOWN。</span>

### <span id="p0493">3. 采集与外部服务全链</span>

#### <span id="p0494">3.1 旧  v4 15类本体保留 A B编排可调范围不同</span>

<span id="p0495">A app.py:6958–6960 初始化并注册v4 blueprint；lumenis/blueprint.py:177起保留adapter/search/collect等接口，search:204调registry.search&#95;all。A collector&#95;service.py:213–317 在registry为空时默认注册15类；未指定平台可选择全部，&#95;run&#95;one经risk&#95;controller及部分平台锁后adapter.collect，再persist。这里未直接核验SYSTEM capabilities/actor/scope，不等于更外层HTTP没有门禁。</span>

<span id="p0496">15类为Douyin、Instagram、Bilibili、Weibo、Zhihu、Facebook、X、BaiduSearch、BingSearch、SogouSearch、Google、SogouWechat、Dianping、Smzdm、Jiguang。本体、legacy base/registry/human&#95;browser A/B字节相同；但B collector&#95;service.py:214–505要求manual=True、明确有界平台列表、整数actor.id和scope，经&#95;validate&#95;request/&#95;manual&#95;collection&#95;guard精确DATA&#95;IMPORT批准后写TaskQueue，&#95;run&#95;one调secondary&#95;collection.collect&#95;search，并有租约、检查点、截止时间和恢复授权重检。</span>

<span id="p0497">B这一兼容start&#95;collect入口只包含上述7个社交平台（Douyin、Instagram、Bilibili、Weibo、Zhihu、Facebook、X）。Google无SYSTEM adapter&#95;module且entry=False；其余7个旧网页/搜索类也不在该入口能力集合。旧registry仍存在，其他入口不能据此宣布全部不可达；同时不能从15个注册类推断B仍可通过该编排执行全部15项。详见采集适配器逐项机制章节共用合同C3及每项A/B说明。</span>

<span id="p0498">registry.search&#95;all仍是串行for循环；默认collect有重试、熔断与allow&#95;fallback=True，缓存未按keyword隔离，可能失败后返回上次成功的旧关键词结果且success=True。A上述编排沿用默认降级；SYSTEM的部分wrapper明确禁fallback，不能混用口径。legacy Facebook多个urlunsplit调用传6元素而API要求5元素，是静态参数合同问题；搜索逐卡异常可能吞掉问题，detail归一化可能直接异常。本次未执行复现或请求平台。</span>

#### <span id="p0499">3.2 SYSTEM 21个文件不等于21项可用采集能力</span>

<span id="p0500">A包&#95;&#95;init&#95;&#95;.py默认导入15个文件，registry仅给微信提供惰性导入。LinkedIn、Reddit、YouTube、TikTok、Channels五个文件有注册语句/schema，但不在A默认导入列表，采集方法均为占位；A返回COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA且继承capability&#95;map偏乐观。B按config.adapter&#95;module导入目录，五项明确NOT&#95;SUPPORTED/NOT&#95;CONFIGURED、能力不支持、manual&#95;collection&#95;enabled=False。B目录注册不构造provider、不自动授权或启用。</span>

<span id="p0501">另须区分：Kuaishou只有backend注入委托，默认未配置；XHS App Topic发现/指标硬返回&#91;&#93;/None，非空endpoint字符串却可使health SUCCESS；GitHub有只读connector实现但仍optional且B manual&#95;collection&#95;enabled=False；XHS既有主路径默认启用，不能把其他类False一概套到它。其余公开源及社交wrapper存在具体调用实现，但真实会话、worker、平台权限、数据有效性仍未核。secondary&#95;collection.&#95;get&#95;runtime&#95;adapter缓存已注册实例，方法存在与运行可用是两层证据。</span>

<span id="p0502">21项完整清单：Facebook、XHSAppTopic、LinkedIn、Xiaohongshu、Kuaishou、GitHub、Reddit、WebRSS、X、PublicHttp、Weibo、YouTube、TikTok、Atom、Douyin、Bilibili、Channels、WechatPublic、Zhihu、Sitemap、Instagram。逐项输入→endpoint/HTTP/浏览器或委托→normalize→失败/重试/空值→启用/运行缺口→建议，均见采集适配器逐项机制章节及读取范围hash。</span>

<span id="p0503">细节风险包括：Instagram公开HTTP media pk与浏览器shortcode身份/schema不同，异常路径引用未定义logger；X评论后端实际NOT&#95;SUPPORTED；Facebook/知乎评论容器与其他平台不同；多处未知互动数变0或作者统计量混入内容指标。不能用search可调用、health或SUCCESS分支给全部能力背书。所有结论均为静态合同，非当前实跑。</span>

<span id="p0504">附加公共源owner：public&#95;source.fetch&#95;public&#95;url封装公网地址pin、重定向重验、2MiB上限与连接/读超时，但不是总墙钟deadline；WebRSS仍使用另一固定Google News RSS helper，不能误称也继承全部公共transport限制。Overture Places只本地Parquet读取/规范化，不是在线API。secondary&#95;collection保持现有Evidence/Canonical边界。公开读取与转载/训练许可分别判断，不混同来源事实和派生分析。</span>

#### <span id="p0505">3.3 广告四项与通知四项</span>

<span id="p0506">ad&#95;intelligence/platforms/factory.py 可构造 OceanEngineCollector、JiguangCollector、MetaAdsCollector、XAdsCollector，按环境配置 credentials/account IDs；四项各有 endpoint/API/browser-readonly/不可用机制。全产品 Python 非测试静态引用检索只找到 package export 和 factory 内部调用，没有找到外部业务 owner 实际调用 AdCollectorFactory.get&#95;collector/health&#95;check&#95;all。准确状态是“已实现工厂、未找到业务绑定调用”，不是删除候选，也不是当前已认证广告账户。动态导入/外部部署调用未据此排除。</span>

<span id="p0507">wechat&#95;notifier.py 定义 WeComBotChannel、ServerChanChannel、PushPlusChannel、WeChatOfficialAccountChannel；WeChatNotifier 可按环境/配置装配并发送。仓内非测试生产 import 检索没有找到外部业务 importer；system&#95;health&#95;api 仅检查文件存在，不是发送调用；审计工具里文字描述也不是执行证据。四渠道归类“可独立运行的配置驱动实现，未找到外部产品绑定”，不对用户是否配置 token 作推断。没有读取 token 值或发送消息。</span>

### <span id="p0508">4. 邮件 必须区分 A B 与验证码占位</span>

<span id="p0509">A app.py:738–741 注册 kos&#95;routes；kos&#95;routes.py:2216–2226 /api/kos/email/send 接收 execution&#95;id 和 actor 字段，直接 ko.send&#95;invitation&#95;email。kos&#95;ops.py:200–235 在允许的旧状态上连续执行 PENDING&#95;HUMAN&#95;REVIEW→HUMAN&#95;APPROVED→EXECUTING，再使用 SMTP&#95;SSL 或 SMTP+STARTTLS（timeout20），login/send&#95;message，写运营记录并转 SUCCESS。外层鉴权和全局 Permission 门禁仍须联合审查；函数自身的状态迁移和客户端 actor 字段不能当独立的人类批准证明。发送成功后本地记账失败还涉及重复发送/回执不确定性，不能只看 SUCCESS 字符串或重试请求安全。</span>

<span id="p0510">B kos&#95;routes.py:1807 的同名路由改为 &#95;scoped&#95;execution&#95;route，取得服务端 actor/scope并经 execute&#95;scoped&#95;execution。B kos&#95;execution.py:172 的 &#95;SCOPED&#95;EXECUTION&#95;ADAPTERS={}；在非测试生产源未找到写入注册者。311–331 要求 HUMAN&#95;APPROVED/EXECUTING/SUCCESS、取当前 scope record、检查 channel 的 authorize/execute/lookup&#95;receipt/verify&#95;receipt；未注册返回 KOS&#95;CHANNEL&#95;NOT&#95;CONFIGURED、external&#95;effect=not&#95;performed，不宣称发送成功。重试时按稳定执行ID查回执，而非不加区分重发。</span>

<span id="p0511">因此“SMTP 默认未注册”只描述 B 新链；A 的旧 SMTP 路径仍可由已注册路由到达，B 保留的旧 kos&#95;ops 函数也不应因新路由未使用而被误写成不存在。二者差异列为主线风险/候选收紧，绝不把候选能力覆盖 main。</span>

<span id="p0512">account/verification.py:351–362 的邮件验证码始终返回 blocked，即便配置 host/user也仍 TODO；SMS:345–348同样保留占位。它们不等于上面真实 SMTP invitation 实现。</span>

### <span id="p0513">5. OSAI 跨仓适配与 GitHub</span>

<span id="p0514">agent&#95;runtime&#95;adapter.py:83–106 发现外部 OSAI 根目录，用 subprocess.run(current Python, -c script, JSON argv)，cwd 指向外仓、PYTHONPATH 指向外仓，env={os.environ,...}；异常/超时返回 UNAVAILABLE，避免伪造身份。lumenis&#95;skill&#95;adapter.py 同型读取 registry/调用 SkillInvoker。实际调用者包括 lumenis&#95;app&#95;api 的 skill 接口及 skills/execution.py:477–484 的非 MCP fallback。JSON argv 避免拼接 shell 不是隔离沙箱。</span>

<span id="p0515">重要边界：这两桥没有冻结外部仓 commit、完整源 hash或依赖 lock；available 主要是目录找到。继承全部父环境会使外仓代码获得进程环境中的潜在敏感配置，不等于“只传了JSON所以没有秘密暴露”。审计没有访问外仓或环境值，不能据此断言泄露已发生。若继续使用，需由现有 owner约束外仓身份、入口、env allowlist、权限和子进程树清理；本任务不授权修改。</span>

<span id="p0516">GitHubConnector 是单独的 GitHub App/read-only 数据 connector，固定 api.github.com 配置/15秒 request timeout、scope和 token provider；授权 URL、仓库选择与Skill注册分别处理，不自动把任意 GitHub repo 变成已安装 MCP。实际账户授权、token权限、目标仓私有数据范围均未读未验证。上游服务条款/商标和服务可用性不由本产品 Apache-2.0 授权覆盖。</span>

### <span id="p0517">6. MCP 2025-11-25 实际协议 权限检查与非沙箱边界</span>

<span id="p0518">固定官方公开协议已取回并记录 hash：</span>

<span id="p0519">- https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle</span>

<span id="p0520">- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports</span>

<span id="p0521">- https://modelcontextprotocol.io/specification/2025-11-25/server/tools</span>

<span id="p0522">mcp&#95;discovery.py 使用自写 newline JSON-RPC stdio 客户端，不是因为 requirements 有某 SDK 就存在另一实现。argv 必须 list，1–32项且每项长度限制；shell=False；默认环境只取固定 allowlist，extra&#95;env 拒若干精确敏感字段名。精确字段名单不是对所有命名变体的秘密检测，更不是任意 child代码无法读文件/联网。</span>

<span id="p0523">Discover（158–290）：先显式 allow&#95;process、timeout在0–60秒；Popen→initialize(protocolVersion=2025-11-25, capabilities={})→notifications/initialized→tools/list→resources/list→prompts/list；统一 monotonic deadline。resources/prompts异常会降为 warning，最终仍可 DISCOVERED，因此“发现成功”不能代替全部列表完整。没有 tools/call。列表最多128项、字符串4096、深度8、行1MiB；未见 nextCursor分页循环，不能将结果当大server完整能力表。返回协议版本被记录，但没有强制拒绝不支持版本的完整协商校验，不能称全协议一致性已通过。</span>

<span id="p0524">Call（338–512）：要求 allow&#95;process、allow&#95;tool&#95;call、human&#95;approved、mcp:tools/call grant、reviewed allowlist、参数dict且无敏感字段；启动后重新 tools/list，必须 readOnlyHint=true且destructiveHint不为true，再 tools/call，仅一次；返回 redacted staging数据，isError进入 TOOL&#95;ERROR。注释声称 read&#95;only grant，但代码实际检查的 grant名为 mcp:tools/call，勿按注释补出独立 read&#95;only 检查。</span>

<span id="p0525">官方 tools 规范说明 annotations 应视为不可信，除非来源 server 可信。产品 readOnlyHint gate 是准入条件，不是 OS 网络/文件权限约束；恶意进程仍可能在 initialize 或 tools/list 时产生副作用，security.production&#95;truth&#95;write=false 只说明这段客户端不写产品业务真值，不能证明 child没有其他写入或联网。stdout/stderr、返回内容即使脱敏也须保持数据而非指令身份。</span>

<span id="p0526">清理：finally关闭stdin→terminate→wait1秒→kill；只针对直接 Popen，kill后没有额外 wait确认，未见 Windows Job Object/整进程树沙箱。timeout主要限制读取等待，阻塞stdin写、子进程树/解码资源仍需真实压力/故障验证。</span>

<span id="p0527">mcp&#95;skill&#95;runtime.py 限安装根 runtime/skill&#95;packages，要求 manifest/package.json/launcher/dist/index.js/node&#95;modules、skill id/version匹配，Node&gt;=22；关闭 TRENTHUB&#95;AUTOUPDATE。invoke 取注册 tools/permissions并要求payload human&#95;approved，实际调用入口在 skills/execution.py:453–470。安装文件存在检查没有等价于完整包内容hash验证，metadata approval也不等于不可伪造的服务端授权事实；完整安全性要沿现有Skill invocation Permission链验证。</span>

<span id="p0528">A与B恢复树均没有 runtime/skill&#95;packages。准确结论是“MCP生产适配源码/调用入口存在，未恢复任何实际安装server包，不能证明当前server连通”。不是“MCP未实现”，也不是“MCP已安装验收”。没有启动任何server。</span>

### <span id="p0529">7. 原生工具 版本 数据和失败清理</span>

#### <span id="p0530">FFmpeg   ffprobe</span>

<span id="p0531">shared&#95;artifacts.py:187 起从 LUMENIS&#95;FFMPEG&#95;PATH/FFMPEG&#95;PATH、PATH、既有工具归档和tools目录解析文件；video&#95;editing.&#95;ffprobe&#95;path从环境/PATH/FFmpeg邻接路径解析。主线没有由这些路径自动固定实际exe hash。Shared Rendering 的 &#95;run 使用 argv、shell=False、poll+communicate、截止时间和 check&#95;continue；失败/取消先 kill/reap再离开临时目录，避免删除仍被编码器占用的工作区。局部协议白名单、format whitelist、probe/full decode 是输入/输出校验措施，不构成操作系统网络隔离。子进程树和解码器漏洞不由“不用shell”自动解决。</span>

<span id="p0532">实际 build version、configure flags、codec、font和第三方库，必须来自被交付的二进制；恢复产品树没有所用FFmpeg/ffprobe二进制。本次没有运行 --version。FFmpeg许可证依build可能 LGPL/GPL，现有前端报告已保存官方 legal 页面，不重复假定具体build许可。</span>

#### <span id="p0533">eSpeak NG B-only</span>

<span id="p0534">B 中 experience&#95;runtime.py:3397–3399 导入并实际调用 synthesize&#95;formant&#95;speech；lumenis/shared/content&#95;creation/toolchain&#95;capabilities.py:28 亦读取该 runtime 能力。因此它是候选版本存在调用入口的实现，不能只记作孤立工具文件。</span>

<span id="p0535">offline&#95;formant&#95;speech.py 从显式变量/which取绝对binary，读取version/voices，按 zh-CN→cmn、ko、en→en-us的固定voice；文本&lt;=4000、拒控制字符和标记，临时输入/输出、120秒合成上限及30MiB检查，FFmpeg全量PCM decode比较、非静音检测，前后校验engine文件hash。明确 third&#95;party、formant&#95;non&#95;neural、机械音色/自然度未评测，不是自研神经声音或静默fallback。</span>

<span id="p0536">其 environment=dict(os.environ)，可附LD&#95;LIBRARY&#95;PATH；记录 external&#95;network&#95;used=false 不能靠声明证明继承环境的外部二进制完全没有网络能力。实际eSpeak、声库、动态库和GPL-3.0-or-later分发义务尚无现用字节核对，不能用代码记录的license字段完成许可证验收。</span>

#### <span id="p0537">LibreOffice 二进制DOC转换</span>

<span id="p0538">parser.py:315–367 通过which(soffice)，单独临时UserInstallation、禁宏/ActiveContent/链接更新配置、最小环境；先 --version（5秒），后 --headless转换docx（30秒），POSIX新session超时killpg、Windows kill直接子进程，wait后清理。转换结果&lt;=8MiB，计算hash后用原有parse&#95;word，临时中间件不当作已保存Artifact。缺本地工具明确ImportError；没有用DOCX parser假装支持旧DOC。实际LibreOffice分发版本/许可和Windows后代进程释放仍未验证。</span>

#### <span id="p0539">Git   SSH</span>

<span id="p0540">Skill package&#95;runtime.&#95;run&#95;remote&#95;git:563–591 在一次性目录 init/fetch已解析commit/ls-tree/show，不checkout、不装依赖或执行repo内容，timeout+非交互。但复制os.environ、仅GIT&#95;CONFIG&#95;NOSYSTEM=1并未等价禁用户Git配置/credential helper；它与本次审计完全不读Git认证是不同层。版本中心 git&#95;manager 还具commit/push/remote retry等真实副作用能力；不能把所有Git都标read-only。未执行任何Git命令或自动保存发布。</span>

<span id="p0541">owned&#95;training&#95;ssh.SSHTrainingEndpoint:59–82要求正规本地SSH/identity/known&#95;hosts、合法host/user/port和source pins；argv关闭agent/forwarding，BatchMode、StrictHostKeyChecking=yes、限定known&#95;hosts，连接10秒/保活。远端preflight校验源码hash，进程组停止/继续/终止逻辑与receipt/检查点回收明确存在。源码支持不证明已连接GPU或当前资源授权；本次未读取identity文件或连接SSH。调用超时、远端进程退出、检查点落盘、独立回执验证应分别验收。</span>

### <span id="p0542">8. 固定模型文件与真实证据缺口</span>

#### <span id="p0543">gpt-oss   Unsloth</span>

<span id="p0544">config/ai-owned-foundation.json 固定 openai/gpt-oss-20b revision 6cee5e81ee83917806bbde320786a8fb61efebee，11文件（3权重shards、tokenizer、config、template、LICENSE/USAGE&#95;POLICY等）；T4 derivative固定 unsloth/gpt-oss-20b-unsloth-bnb-4bit revision 093fba6992ef5a7152481afec0bdfca1ac486998，11文件。base&#95;revision&#95;state=UPSTREAM&#95;UNSPECIFIED，不能推断衍生权重一定对应前述OpenAI commit。</span>

<span id="p0545">本次对恢复档逐文件名查找并比对匹配候选hash：22项没有一项找到匹配pin字节；另项目的同名 tokenizer&#95;config/chat&#95;template 不匹配，不能冒充已恢复权重。模型文件身份附录 留完整声明文件hash、名字候选和实际比对结果。没有重新下载大模型权重，也没有加载pickle/torch文件。</span>

<span id="p0546">历史治理文档 round-07/ROUND-07-OWNED-AI-MATERIALS-2026-10-01.md:681–715 记载免费Colab T4、4个公共算术QA、LoRA rank8、3步，mean loss4.619938214619954、steps4.9395/4.9875/3.9328、非空adapter保存及PeftConfig重开。记录adapter权重370,291,488 bytes/hash ffbeacc27fa632fa5274b93c1a8a4680​bc3ec4b783cdab7345aa048f7901cabb；ZIP下载恢复超时、工作站存在未确认。恢复档未找到这些checkpoint实际字节，不能独立重开证明该训练，不能把历史文档否定成“从未训练”，也不能拿三步算术证明生产业务模型已达标或上线。</span>

#### <span id="p0547">Whisper base   small</span>

<span id="p0548">A owned&#95;speech 固定 openai/whisper-base revision31243bad24cc746f07d4c8bfdd2d974872cb1803、权重SHA ed3a0b6b1c0edf879ad9b11b1af5a0e6​ab5db9205f891f668f8b0e6c6326e34e；要求openai-whisper20250625、torch2.14.1+cpu、17个源文件/资源hash、runtime manifest及Python/FFmpeg/输入音频hash。离线worker用CPU和固定解码参数，Python audit hook拦部分network/subprocess/SQLite事件；这不是native依赖的完整OS sandbox。</span>

<span id="p0549">17个hash已与官方v20250625静态来源全部一致，包括额外取回gpt2.tiktoken、multilingual.tiktoken和mel&#95;filters.npz；Whisper源码与资源核对附录给出逐项证据。这证明固定实现资源一致，不证明本机Torch、权重、runtime manifest可用。没有恢复base/small权重本体或当前完整运行环境。</span>

<span id="p0550">B新增small评估权重SHA 9ecf779972d90ba49c06d968637d720d​d632c55bbf19d441fb42bf17a411e794；恢复 历史ASR推理结果回执 记载small实际推理elapsed37.292秒、总40.225秒、source/config/adapter/manifest/package hashes及源/映射字幕结果。prior-checks有completed&#95;with&#95;review&#95;warning、末词跨segment尾界保留且UNREVIEWED、worker peak RSS2,684,424,192 bytes。两份receipt-first/second只有冷读回，明确inference=false/network=false，不能冒充本次又跑了两次ASR。</span>

<span id="p0551">历史ASR证据记录只提取模型/时长/hash/状态/资源，不复制用户转录正文。模型字段model&#95;revision在历史small结果中实际填了权重hash，不应把它称HuggingFace commit。回执有证据价值，但没有weight/runtime字节重开，本次不确认结果准确率，更不能将B历史结果上升为A或当前生产已验收。</span>

### <span id="p0552">9. 后续验收优先级与边界</span>

<span id="p0553">高优先：主线A的Groq-only目标约束和SMTP旧路由，须在现有Permission/route owner上审核；B是候选收紧的源证据，未经明确修改授权不直接移植/合并。MCP/OSAI的进程权限、继承环境、真实child副作用与树清理应单独验，不能把security元数据当沙箱证明。</span>

<span id="p0554">发布前：确认实际服务配置/绑定、审核外部发送范围和source rights，锁定native和model实际字节，保留合法license/NOTICE和权重/数据使用条件。广告/通知若无实际业务caller就保持未绑定；旧/v4仍有caller就不能漏账，同时按A/B编排分别限定可调范围；五个SYSTEM占位和XHS App Topic不能算已实现采集。优先离线验证Facebook URL合同、跨关键词缓存、Instagram身份/schema及异常路径，再考虑有明确授权的live验收。模型训练、ASR历史、checkpoint重开、held-out质量、生产推理、发布必须各自有证据。</span>

<span id="p0555">本任务仅给出机制与证据，不安装、执行、发送、训练、部署或修改；所有真实运行层结论保持当前未验，除明确标注的恢复历史回执。</span>

<span id="p0556"><br /></span>

## <span id="p0557">采集适配器逐项机制</span>

<span id="p0558">A为主线commit 4dab98ed6357133da9307de846180ed4f7bba5f5，B为2026-10-17恢复候选NOT&#95;FINAL，未经合并或部署确认。覆盖原74账中的15个legacy adapter和21个SYSTEM adapter文件，逐项保留输入、实际机制、输出、失败/重试/空值、启用与运行证据边界、建议。21个文件不等于21个已实现或已授权采集能力。</span>

### <span id="p0559">逐项核验结论</span>

<span id="p0560">1. 五个SYSTEM计划项（LinkedIn、Reddit、YouTube、TikTok、Channels）没有真实采集实现。A未默认导入且占位方法/health偏乐观；B统一目录导入并明确NOT&#95;SUPPORTED/NOT&#95;CONFIGURED。Kuaishou需要注入backend；XHS App Topic核心发现/指标仍固定空返回。</span>

<span id="p0561">2. 15个legacy适配器本体A/B相同，但B兼容编排改走统一Permission/secondary&#95;collection，仅该入口允许7个旧社交平台；不要把A旧registry调用结论直接套到B。</span>

<span id="p0562">3. 高优先静态合同问题：legacy Facebook urlunsplit六元素参数；legacy默认跨关键词缓存降级；Instagram两路身份/schema与未定义logger异常路径；多处unknown被写0、评论/作者字段量纲混用。这些是静态证据，不称已执行复现。</span>

<span id="p0563">4. 未请求闭源平台、读取cookie或启动产品。本次没有新增live采集成功证据。保留未核实项而不把配置存在、health或SUCCESS分支当实测。</span>

<span id="p0564">配套分类账：服务与原生接入身份账；逐项源文件与读取范围hash见适配器读取范围记录及其三份明细。</span>

<span id="p0565"></span>

<span id="p0566">审查时间：2026-10-17 UTC。范围为15个旧版已注册适配器的静态实现。</span>

<span id="p0567">- A：主线快照，产品相对目录 lumenis/adapters。</span>

<span id="p0568">- B：NOT&#95;FINAL候选的对应产品相对文件，不等同已部署版本。</span>

<span id="p0569">- 15 个 adapter 本体均完成 A 源码审读和 A/B 全文件 SHA-256/字节对比，全部相同。共享调用链有重要差异，见 C3。</span>

<span id="p0570">- 仅做源文件读取、静态解析和差异比较；没有导入/执行产品、启动浏览器、请求任何平台、读取数据库/日志/运行配置值，未读 .env、Cookie 数据、密钥、会话文件或 Git 认证。代码中的凭据接口调用只是依赖说明，不代表读取了凭据。</span>

<span id="p0571">- “已注册”只指源码注册列表；“失败/成功”均为代码合同；本次没有任何平台的运行成功证据。未观察不等于证明从未运行。函数、注释、测试名称、网络地址都不构成实测。</span>

<span id="p0572">- 行号默认指 A，相对路径默认 lumenis/adapters/；B 行号显式标注。实际审读范围及每个文件 SHA-256 见 旧适配器读取范围记录。</span>

### <span id="p0573">关键结论</span>

<span id="p0574">1. Facebook 的 URL 归一化把 6 元素元组传给要求 5 元素的 urllib.parse.urlunsplit（facebook.py:83、104–105、128、225）。这是静态 API 合同错误：命中这些分支时会异常；search 的逐卡异常处理可吞掉错误，detail 的首次归一化在 try 外。未执行验证。</span>

<span id="p0575">2. BaseAdapter 默认缓存降级不按 keyword 隔离，且失败可变成 success=True；A collector&#95;service 直接使用默认降级并把结果交给 persist。新关键词可能收到旧关键词结果。B 已改调单一 secondary&#95;collection owner，不能把 A 路径结论直接套给 B。</span>

<span id="p0576">3. 数据语义不统一：Dianping、Jiguang、搜狗微信、知乎仍把未观测互动量写 0；知乎把回答数写 comments、作者粉丝数写 likes，抖音作者作品数写 shares。Instagram 评论单项装在 raw&#95;data.comments，外层 notes 恒有一条，与其他评论接口不同。</span>

<span id="p0577">4. 严格空值/身份合同主要集中在 Douyin search/detail、X search/detail、Instagram search/detail、Facebook search/detail；同一平台 comments/creator 常未达到相同强度。不能用 search 成功替代其他能力验收。</span>

<span id="p0578">5. B 的兼容编排已不直接分发全部 15 个旧适配器：7 个社交平台（douyin/instagram/bilibili/weibo/zhihu/facebook/x）进入新的能力与授权路径；Google 及另外 7 个旧搜索/网页适配器不在该 B start&#95;collect 允许的平台集合。旧 registry 仍存在，因此这里只限定这条入口，不宣称所有其他入口不可达。</span>

### <span id="p0579">共用合同</span>

#### <span id="p0580">C1 标准输出与重试 降级</span>

<span id="p0581">证据：base.py:24–61、64–136、193–342；lumenis/config.py:61–68。</span>

<span id="p0582">- CollectedNote：title 必填；content/url/author/author&#95;id/publish&#95;date/cover/source&#95;platform 默认空串；likes/comments/collects/shares 默认 None；raw&#95;data 默认空字典。optional&#95;int 使 None、空串和不可转换值保持 None，但对可 int() 的值转换，并不验证非负/精确观测。</span>

<span id="p0583">- AdapterResult：success、notes、error、raw&#95;count、duration&#95;seconds、diagnostics；默认 notes=&#91;&#93;、raw&#95;count=0。各接口的 raw&#95;count 有的为截断前数量，有的为返回量，有的为看到的原生 ID 数，不能跨平台直接比较。</span>

<span id="p0584">- collect：令牌桶默认 30 次/分、burst=5；无令牌等待最多 10s；熔断连续 5 个 collect 失败后开启、300s 后 half&#95;open；最多 3 次 search 尝试，间隔 retry&#95;delay×(attempt+1)，默认 2/4/6s，末次失败也 sleep。重试次数是总尝试数。</span>

<span id="p0585">- 终止重试依赖错误字符串包含 captcha/登录/cookie/risk/blocked/HTTP 403/429 等，而非结构化状态码。Instagram 的 AUTH&#95;REQUIRED/CHALLENGE&#95;REQUIRED/RATE&#95;LIMITED 和 X 的 “verification challenge detected”等文本并不全部匹配该列表，不能把注释“风控不重试”视为统一保证。</span>

<span id="p0586">- 降级默认 allow&#95;fallback=True：先自定义回调，再上一次成功结果，最后失败。缓存没有 keyword、平台之外的请求身份、时间有效期或作用域键；返回 success=True 并把降级原因放 error，raw&#95;count/diagnostics 不保留。allow&#95;fallback=False 才直接失败。safe&#95;collect 额外兜底所有异常；detail/comments/creator 通常不经 collect，无统一重试/熔断/限流保证，Douyin detail 独立取令牌是例外。</span>

<span id="p0587">- 建议：显式区分 FRESH/STALE/FALLBACK/PARTIAL、缓存键包含请求身份和作用域、保留 diagnostics/原始状态、基于结构化错误决定重试。全为待授权建议。</span>

#### <span id="p0588">C2 浏览器共用机制与证据边界</span>

<span id="p0589">证据：human&#95;browser.py:118–204、545–573、769–955、1044–1081；SYSTEM adapters/config.py:23–205。</span>

<span id="p0590">- HumanBrowser 使用 Playwright sync API connect&#95;over&#95;cdp，取首个既有 context；本地连接核验已登记 profile、端口、内核和 BACKGROUND/headless 模式；多个适配器传 auto&#95;ensure=False，不负责自动起 worker。</span>

<span id="p0591">- configured&#95;readonly&#95;worker&#95;url 要求已登记平台、固定 loopback endpoint、对应 opt-in/account 环境值及匹配进程。这里只读取变量名和源码条件，没有读取实际环境值或进程。</span>

<span id="p0592">- new&#95;page 默认 stealth=True，会 add&#95;init&#95;script 改浏览器环境属性；Douyin search/detail、Instagram search、Facebook 全部、X 明确传 False；Google、知乎浏览器支路、Jiguang、Douyin comments/creator、Instagram detail/comments/creator沿用默认。仅记录现状，不建议规避平台限制。</span>

<span id="p0593">- detect&#95;state 先基于正文/URL 的风控、验证、登录、网络标记，再判断 selector；缺 selector 且有正文可判 EMPTY，正文中的普通用户内容也可能碰到关键词。各平台必须加自身真实空结果合同。</span>

<span id="p0594">- 注册/能力声明、Cookie 文件级检查、CDP 进程约束都不是平台真实登录/权限/采集成功证据。需要用户明确授权的逐平台实际结果，本文未做。</span>

#### <span id="p0595">C3 A B 共享调用链差异 每项均适用</span>

<span id="p0596">证据：registry.py:34–83、92–117；A collector&#95;service.py:213–317；B collector&#95;service.py:214–505；B secondary&#95;collection.py:36–46、398–414、1519–1590；A/B SYSTEM adapters/config.py。</span>

<span id="p0597">- 共同 registry：register&#95;default&#95;adapters 列出 15 类；先执行所有 import，再在逐实例 try 内注册。因此任一顶层 import 失败可阻断整次默认注册，而不只是该平台。search&#95;all 名称/注释称并行，实际 for 循环串行；合并接口按 URL 去重并保留 SUCCESS/EMPTY/FAIL。它本身不读 SYSTEM enabled。</span>

<span id="p0598">- A：start&#95;collect 若 registry 为空则默认注册；未指定 platforms 会选全部；后台 &#95;run&#95;one 经 risk&#95;controller 和部分平台锁后调用 adapter.collect，再交 persist.persist&#95;result。这里未直接核验 SYSTEM capabilities/actor/scope；不能由此推断更外层 HTTP 路由无校验。</span>

<span id="p0599">- B：start&#95;collect 要求 manual=True、明确有界平台列表、整数 actor.id、scope；&#95;admit 调 &#95;validate&#95;request + &#95;manual&#95;collection&#95;guard（当前权限与精确 DATA&#95;IMPORT approval），再写 TaskQueue。&#95;run&#95;one 转 secondary&#95;collection.collect&#95;search；有租约/心跳、完成平台检查点、operation&#95;id、截止时间、恢复时重验授权，权限/挑战状态等待明确行动。这里未深审整个 secondary&#95;collection，不声称完整行为验证。</span>

<span id="p0600">- B capabilities 新增 canonical&#95;id/source&#95;kind/adapter&#95;module/collection&#95;entry&#95;enabled 等静态投影。Google 为 discovery、无 SYSTEM adapter&#95;module、entry=False；另 7 个旧网页/搜索类根本不在 capabilities 内。7 个社交类 enabled=False 仍保留 manual&#95;collection&#95;enabled=True、entry=True；表示声明可人工入口，不是已完成配置/授权。</span>

<span id="p0601">- A/B 相同：15 类本体、base、registry、&#95;&#95;init&#95;&#95;、human&#95;browser、lumenis/config.py。不同：collector&#95;service.py 与 SYSTEM adapters/config.py。所有建议须区分快照，不改变 B 的权限设计，也不从旧 registry 注册推断可执行范围。</span>

### <span id="p0602">逐项机制</span>

#### <span id="p0603">1. DouyinAdapter   douyin</span>

<span id="p0604">证据：douyin.py:39–84、114–400、403–697。</span>

<span id="p0605">- 输入→机制：search(keyword,max&#95;results=20)；非空关键词进 www.douyin.com/search/{quoted}?type=general。显式 DOUYIN&#95;CDP&#95;URL；本地只允许 opt-in 的 127.0.0.1:9225 / DOUYIN&#95;READONLY，远程为无用户信息/query/fragment 的 HTTP(S) endpoint。浏览器 requestfinished 捕获 xhr/fetch 的 general/search/single 与 general/search/stream，后者连续 JSON 解码；最多 3 轮滚动，缺接口结果才 DOM 兜底。detail(aweme&#95;id) 打开 /video/{id} 并取 aweme/detail；comments 同页 response 捕获 comment/list；creator(sec&#95;uid) 打开 /user/{sec&#95;uid} 捕获 user/profile。</span>

<span id="p0606">- normalize→输出：search aweme&#95;info 去重 string aweme&#95;id，必须有 desc；title=desc&#91;:80&#93;、content、video URL、nickname、uid/short&#95;id、create&#95;time→本地日期；statistics→likes/comments/collects/shares，play&#95;count 仅非负严格 int 存 raw。DOM 兜底无原生 URL/时间、首段推断点赞。detail 严格匹配 response aweme&#95;id，并加时间/正文/指标 locator、去 query 的 typed media&#95;hints、media&#95;bytes&#95;saved=False。评论逐条 note 含 cid/author/content/date/likes/reply&#95;comment&#95;total；creator total&#95;favorited→likes、aweme&#95;count→shares，followers/following 放 raw。</span>

<span id="p0607">- 失败/重试/空值：search 失败可保留已观察 notes 但 success=False；只有 status&#95;code=0 且明确 data=&#91;&#93;、同时没有候选才算 EMPTY。无可验证结构失败；detail 无匹配响应失败；comments 未观察响应也可成功空、未做同等页面状态/父帖身份校验。未观测统计大多 None，creator comments/collects=0；详情独立限流，其他非 search 接口不继承 C1 重试。</span>

<span id="p0608">- 启用/运行缺口：声明 manual=True、enabled=False；缺真实 worker/profile/登录、响应 shape、detail 身份、评论父子关系实测。接口响应路径字符串匹配未限定 response hostname，需确认关联请求来源。</span>

<span id="p0609">- A/B：本体完全相同；A 直调 collect，B 按 C3 进入受控 secondary&#95;collection，不能用 A 默认缓存逻辑推断 B 最终落库。</span>

<span id="p0610">- 建议：保留 search/detail 的严格证据合同；把评论/作者页提升为相同身份、页面状态、空值合同；作品数不要放 shares；DOM 点赞推断应标估计/不可用；统一 requestfinished 生命周期。</span>

#### <span id="p0611">2. InstagramAdapter   instagram</span>

<span id="p0612">证据：instagram.py:32–350、352–713、715–1231。</span>

<span id="p0613">- 输入→机制：search(keyword,&lt;=20, native&#95;hashtag?,native&#95;topic&#95;reference?) 仅接受原始关键词；registered 9227 worker，经官网主页可见搜索输入/唯一已观察搜索按钮 fill+Enter，比较搜索前后 main 中原生 /p/、/reel/、/reels/ 链接；无帖子可沿完整显示名归一后精确匹配的账号链接，最多 3 个账号。hashtag 必须 literal="#"+native&#95;hashtag，与引用一致才进 /explore/tags/{tag}/；不从关键词自造标签。detail(shortcode,media&#95;type) 进 /p&#124;reel/{shortcode}/；comments 强制 /p/；creator 进 /{username}/。</span>

<span id="p0614">- normalize→输出：预览 note 为 caption/alt 或占位标题、原生 shortcode URL、author、空 publish&#95;date、精确 likes；raw 包 search&#95;ui&#95;scope、query、native hashtag/profile 发现路径、body&#95;kind=SEARCH&#95;PREVIEW、needs&#95;detail=True、cover/media URL hints。detail 核验最终官方域名/shortcode，从 article h1/time/作者链接/metrics 取 caption、日期、点赞/评论、原生 media&#95;id/locator；图片 alt 单独保存；无媒体字节。comments 返回一条包装 note（title=comments），raw.comments 为 author/content/publish&#95;time/likes 数组，raw&#95;count 为评论数；creator 粉丝/关注/帖子数、原始显示、verified/private 在 raw。</span>

<span id="p0615">- 失败/重试/空值：search 只有明确 no-results UI 才成功空；未知、登录、挑战、频控失败。精确计数不接受 1.2K 等缩写，保留 display；评论 JS 却把未观测 likes 初始化0。detail 最终 URL匹配后即使无 article/完整 caption，只要没识别失败状态仍可 success=True+needs&#95;detail；comments 可能 raw&#95;count=0 但 notes=1；creator 可无字段也返回包装成功。C1 字符串终止重试未覆盖全部 INSTAGRAM&#95;&#42; 状态。</span>

<span id="p0616">- 启用/运行缺口：manual=True、enabled=False，缺真实9227 worker/有效会话/搜索结果来源和评论父帖对应证据；search 没有调用 inject&#95;into&#95;context，依赖 worker 既有会话，detail/comments/creator 会注入。</span>

<span id="p0617">- A/B：本体相同；B 人工入口适用 C3。静态缺口：&#95;is&#95;official&#95;search&#95;route 把 &#95;official&#95;instagram&#95;path 返回的 None 折成空串，而空串属于允许集合（490–504），使外站/无效URL初始路由检查不能按预期拒绝；后续 origin 校验只保护媒体行，不能替代初始路由边界。</span>

<span id="p0618">- 建议：首先区分 None 与官网根路径；评论限于确切帖子评论容器及原生 comment ID，统一空值；成功与完整正文分开；统一页面状态与 retry code，补 query 结果归因和 exact identity 离线用例。</span>

#### <span id="p0619">3. BilibiliAdapter   bilibili</span>

<span id="p0620">证据：bilibili.py:50–191、194–391。</span>

<span id="p0621">- 输入→机制：search(keyword,max&#95;results)；有注入 manager 则 check&#95;login&#95;status→search&#95;videos；否则 Cookie ACTIVE 前置后 requests GET api.bilibili.com/x/web-interface/search/type（search&#95;type=video,page=1,page&#95;size=max&#95;results，15s）。detail(bvid)→/x/web-interface/view；comments(bvid,aid?,max&#95;comments) 无 aid 先 detail，再 /x/v2/reply(type=1,oid=aid,pn=1,ps,sort=1)；creator(mid)→/x/space/acc/info。均第一页，不保证全量。</span>

<span id="p0622">- normalize→输出：搜索清理 em 高亮、title/description/url/author、pubdate→UTC ISO、favorites→collects，likes/comments/shares=None；raw aid/bvid/play/video&#95;review/duration/pubdate&#95;ts。detail owner→author/id、stat.like/reply/favorite/share→标准互动、pic→cover，raw 保留 view/danmaku/coin 等原生统计。评论逐条 note 空 title、message、#reply{rpid}、会员/ctime/like，raw type=comment；creator 基础信息+face、等级/sex/vip&#95;type 等 raw，标准互动均 None。</span>

<span id="p0623">- 失败/重试/空值：code!=0 明确失败；-101 登录、-352/-509 风控；detail 额外识别412。code=0 没有结果成功空；detail/creator 即使缺完整 data 仍可能生成空字段 note。search manager 与直连 raw&#95;count 口径不同。没有 raise&#95;for&#95;status，HTTP状态依赖JSON解析/业务code；C1只覆盖collect路径。</span>

<span id="p0624">- 启用/运行缺口：manual=True、enabled=False；缺会话、当前API权限/结构、bvid↔aid一致性和翻页证据。manager 分支依赖的登录经理实现未在本章节深审。</span>

<span id="p0625">- A/B：本体相同；B 经 C3，新入口权限和落库不能据 legacy 本体推定。</span>

<span id="p0626">- 建议：维持未知互动=None；要求原生 bvid/aid/mid 与请求一致、正常空与无 data 分开；保存 HTTP+业务错误分层；范围只承诺首批，补分页合同后再扩充。</span>

#### <span id="p0627">4. WeiboAdapter   weibo</span>

<span id="p0628">证据：weibo.py:54–212、215–347。</span>

<span id="p0629">- 输入→机制：search(keyword,max&#95;results)→requests GET m.weibo.cn/api/container/getIndex，containerid=100103type=1&amp;q={quoted keyword}，Cookie header，15s；注入 manager 可提供登录检查/凭据。detail(mid)→m.weibo.cn/statuses/show?id；comments(mid)→/api/comments/show(id,page=1)；creator(uid)→getIndex(containerid=230283{uid}&#95;-&#95;INFO)。只取一批，不分页。</span>

<span id="p0630">- normalize→输出：cards&#91;&#93;.mblog→清HTML正文、前80字title、/status/{mid}、screen&#95;name/id、created&#95;at→ISO；attitudes/comments/reposts→标准统计，collects=None；raw mid/id/is&#95;long&#95;text/source/region/page&#95;info。detail复用同转换。评论 hot&#95;data+data 截断，逐条正文、#cmt{id}、作者/时间/like&#95;count，type=comment；creator 从card&#95;type10/11取用户，简介/头像，followers/follow&#95;count/verified 仅 raw。</span>

<span id="p0631">- 失败/重试/空值：空关键词或无凭据失败；search ok=-100/登录词→登录失效，验证/风险词→风控；其他ok!=1失败；ok=1却无mblog或解析项全丢成功空。detail和comments校验Cookie ACTIVE，creator只查非空Cookie；无统一HTTP状态判定，字段转换失败可逐项静默丢弃。统计缺失None，created&#95;at相对时间留空；comments热点+普通未去重。</span>

<span id="p0632">- 启用/运行缺口：manual=True、enabled=False；需真实会话/API响应、原生mid/uid身份和评论去重证据，不能凭ACTIVE文件态认定已登录。</span>

<span id="p0633">- A/B：本体相同；C3的调用/权限/持久化变化适用。</span>

<span id="p0634">- 建议：保留None；鉴别无结果与结构变化，验证详情id和评论父帖；校正热评重复、HTTP异常和业务状态；明示首屏覆盖度。</span>

#### <span id="p0635">5. ZhihuAdapter   zhihu</span>

<span id="p0636">证据：zhihu.py:51–230、232–465。</span>

<span id="p0637">- 输入→机制：search(keyword,max&#95;results)优先查看是否存在readonly&#95;worker声明；存在才走注册CDP的 /search?type=content&amp;q=，该支路失败不得转API；无声明则 requests GET www.zhihu.com/api/v4/search&#95;v3(t=general,q,limit&lt;=20,correction=1，15s)。本次A/B config均未给知乎readonly&#95;worker，因此源码默认走API。detail(content&#95;id,type=answer&#124;article&#124;question)→/api/v4/{answers&#124;articles&#124;questions}/{id}；comments→同资源/root&#95;comments(limit&lt;=20)；creator(user&#95;id)→/api/v4/members/{id}。</span>

<span id="p0638">- normalize→输出：browser卡片title/content/url/author，前30字标题+作者及URL去重；API answer取question标题、answer URL，article取自身标题URL，question取问题URL；excerpt清HTML、作者/id、UTC ISO日期。缺统计置0，question.answer&#95;count→comments；creator follower&#95;count→likes、answer&#95;count→comments、articles&#95;count→collects。评论单项 vote&#95;count/child&#95;comment&#95;count 映射。raw object&#95;type/id/updated&#95;time或cid/creator标记。</span>

<span id="p0639">- 失败/重试/空值：API error字段失败；无data、非dict响应、未知类型或解析全丢可能成功空；DOM没有卡片也成功空。detail请求include=content却复用只读excerpt的转换，完整正文可能未输出。浏览器点赞取所有数字拼接，会把缩写/杂文误成精确数；collects/shares=0等不符合C1未知合同。</span>

<span id="p0640">- 启用/运行缺口：manual=True、enabled=False、enable&#95;gate声明engine&#95;verified&#95;no&#95;cookie&#95;required，不是本次API免登录成功证明。缺当前API权限/签名/响应shape、详情全文和量纲证据。</span>

<span id="p0641">- A/B：本体相同；B C3适用；无readonly&#95;worker这一静态分支条件相同。</span>

<span id="p0642">- 建议：修正指标量纲、None及精确数字；detail分别输出content和excerpt；正常空需明确业务证据；API/浏览器各自建立fixture，不以注释“主路径API”替代实际分支。</span>

#### <span id="p0643">6. FacebookAdapter   facebook</span>

<span id="p0644">证据：facebook.py:59–156、159–293、295–651。</span>

<span id="p0645">- 输入→机制：search(keyword,max&#95;results)限0–20，configured readonly worker（声明9228）→www.facebook.com/search/top?q=，解析div&#91;role=article&#93;及备用卡片；detail(post&#95;id)实际要求完整、已观察到的官方 /posts/{native&#95;id} 或 permalink.php/story.php?story&#95;fbid= URL，不接受任意裸ID。最终URL和article原生ID必须一致。comments(post&#95;id)及creator(username)则允许原始 http&#42; URL或拼接facebook路径，未用同等官方域/帖子身份门禁。</span>

<span id="p0646">- normalize→输出：卡片content/title/author、原生post&#95;id+permalink、time&#91;datetime&#93;/data-utime、精确likes/comments/shares（缩写仅保留display，collects=None）；raw SEARCH&#95;PREVIEW、正文hash/locator、native&#95;time、audience observation、限定站点的media hints、无媒体字节。detail复用预览转换并加exact matched详情定位，仍不保证完整正文。评论逐条note无URL/原生评论ID/时间，source&#95;platform=facebook&#95;comment；creator name/URL/username，source&#95;platform=facebook&#95;creator，标准互动None。</span>

<span id="p0647">- 失败/重试/空值：search显式no-results才空成功，未见卡片/不可解析均失败；登录/挑战/外域/不可用分状态。comments没有相同页面风险/身份检查，可能成功空；creator没有字段也以username兜底成功。非search不经C1。最大风险为上述6元组urlunsplit：帖子/公共/媒体URL归一化分支静态必异常；detail首次调用在try外，search逐卡异常吞掉。不能称运行复现。</span>

<span id="p0648">- 启用/运行缺口：manual=True、enabled=False；缺已授权会话、9228身份、页面和精确原生ID证据；源码错误尚未修复/验证。</span>

<span id="p0649">- A/B：本体相同，故该静态错误两份都有；B新的C3入口不自动修复本体。</span>

<span id="p0650">- 建议：先经授权修正urlunsplit参数并以离线URL样例回归；comments/creator统一官方URL和父对象身份、风险与真实空结果合同；确认“detail”为完整正文还是可见预览。</span>

#### <span id="p0651">7. XAdapter   x</span>

<span id="p0652">证据：x&#95;platform.py:36–83、109–295、297–706。</span>

<span id="p0653">- 输入→机制：search(keyword,max&#95;results&lt;=20,skip&#95;tweet&#95;ids?)；checkpoint须≤5000个numeric-string ID。仅允许显式opt-in且绑定profile的127.0.0.1:9226/X&#95;READONLY；进 https://x.com/search?q=&amp;src=typed&#95;query，article DOM，最多8轮滚动/连续2轮无新增停止。detail接受numeric id或官方x.com status URL→/i/web/status/{id}；creator要求1–15字符handle；comments明确不支持，不触网。</span>

<span id="p0654">- normalize→输出：以主帖且不在quote容器的time permalink取得原生ID、URL、datetime；主帖tweetText/作者handle、精确互动及原显示；views保持None、未分类计数仅raw；twimg媒体去query hints，无字节。结果动态加 metadata.continuation（未在AdapterResult dataclass声明）：观察ID/已跳过ID、无native&#95;cursor、coverage&#95;complete=False。detail要求最终URL+唯一article的ID匹配；creator精确followers/原显示存raw，标准互动None。</span>

<span id="p0655">- 失败/重试/空值：无可验证帖子失败，只有checkpoint下全部已观察ID均已跳过才成功空。途中风控可failure+partial notes，C1最终失败包装会丢该partial/metadata。login/challenge/blocked靠路由/title，避免任意帖文关键词误判；challenge文本不一定触发C1的terminal marker。detail非唯一失败；creator缺名称且缺粉丝元素失败。</span>

<span id="p0656">- 启用/运行缺口：manual=True、enabled=False；config虽comments=True，本体明确NOT&#95;SUPPORTED，声明与能力不一致。缺实际worker身份/会话、quote排除和continuation序列化/传播证据。</span>

<span id="p0657">- A/B：本体相同；B C3的权限/持久化/续采owner需要另外证据，不能以动态metadata存在认定已持久化。</span>

<span id="p0658">- 建议：保持禁止伪造回复关系；comments能力声明对齐实际；Continuation进入显式schema，保留partial及观察ID；按code停止挑战重试，明确有限窗口不等于全量。</span>

#### <span id="p0659">8. GoogleAdapter   google</span>

<span id="p0660">证据：google.py:35–201；config.py:129–149（此处为SYSTEM adapters/config.py）。</span>

<span id="p0661">- 输入→机制：非空keyword，max&#95;results默认10；注册GOOGLE&#95;READONLY、9230/profile/headless核验后CDP，先google.com主页处理同意页，再/search?q=&amp;hl=zh-CN&amp;num=max(n,10)，等h3最多15s、滚动；无requests搜索API。/goto缺直链时page.request.get跟重定向（最多20，3.5s）。</span>

<span id="p0662">- normalize→输出：h3对应标题、近邻snippet、同结果块外链优先；去重URL，author=Google，摘要显式日期→YYYY-MM-DD，raw engine/link&#95;redirect。无互动字段保持None。</span>

<span id="p0663">- 失败/重试/空值：未见h3失败；挑战/验证/登录/网络失败；有h3但解析不到note返回成功空，不能证明真无搜索结果。中转还原失败保留goto并标记。外链筛选字符串过滤、日期仅月1–12/日1–31，无完整日历合法性验证。C1适用collect。</span>

<span id="p0664">- 启用/运行缺口：manual=True、enabled=False；缺实际9230 worker/浏览器访问与snippet字段匹配证据。动态Google DOM和外链跳转可变化。</span>

<span id="p0665">- A/B：本体相同；A可被旧registry默认选择；B config将其定义discovery、adapter&#95;module=None、collection&#95;entry&#95;enabled=False，B start&#95;collect不接受google，即使manual flag仍True。</span>

<span id="p0666">- 建议：区分解析器失配与EMPTY；域名用结构化host校验、保留直接/中转来源；Google搜索发现应独立明确入口/权限及结果质量验收。</span>

#### <span id="p0667">9. BaiduSearchAdapter   baidu&#95;search</span>

<span id="p0668">证据：baidu&#95;search.py:11–51。</span>

<span id="p0669">- 输入→机制：keyword/max&#95;results→requests GET www.baidu.com/s?wd={quote}&amp;rn={n}，UA+中文语言、共用30s timeout，UTF-8；正则匹配result/h3/link/content-right，失败改h3链接兜底（最多20条且排除含baidu.com的URL）。</span>

<span id="p0670">- normalize→输出：去HTMLtitle/content、原href、author=百度搜索、source&#95;platform=baidu&#95;search，其余C1默认；只截notes&#91;:n&#93;，raw&#95;count为解析总数。</span>

<span id="p0671">- 失败/重试/空值：只捕获异常，无HTTP status/验证码/登录/响应shape检查；任何未抛异常的403/验证HTML或结构失配均可能success=True+&#91;&#93;。没有分页/详情/评论/作者实现；search自身不校验空keyword/负n。</span>

<span id="p0672">- 启用/运行缺口：旧registry有注册；SYSTEM capability无该key，无法推断生产启用；缺HTTP/DOM实证与合法正常空结果样本。</span>

<span id="p0673">- A/B：本体相同；B C3 start&#95;collect平台集合不含该key，旧registry直接方法仍在。</span>

<span id="p0674">- 建议：优先补HTTP、challenge和明确空结果识别，替换易碎正则；区分搜索引擎中转URL与原文，限定输入/截断合同。</span>

#### <span id="p0675">10. BingSearchAdapter   bing&#95;search</span>

<span id="p0676">证据：bing&#95;search.py:11–40。</span>

<span id="p0677">- 输入→机制：keyword/max&#95;results→requests GET www.bing.com/search?q={quote}&amp;count={n}，UA/Accept-Language、C1 timeout；单一正则匹配li.b&#95;algo→h2 a→p。</span>

<span id="p0678">- normalize→输出：清HTMLtitle/content、原href、author=必应搜索；其余C1默认；notes&#91;:n&#93;，raw&#95;count解析数。</span>

<span id="p0679">- 失败/重试/空值：仅异常失败，无status/challenge/shape验证；解析不到即成功空，C1不会重试此类假空。无分页、detail/comments/creator；无关键词/上限有效性校验。</span>

<span id="p0680">- 启用/运行缺口：仅旧registry注册，SYSTEM无key；缺实际Bing响应及正常空/限制页证据。</span>

<span id="p0681">- A/B：本体相同；B start&#95;collect不含key，其他直接registry入口未判定。</span>

<span id="p0682">- 建议：与百度分别建立站点fixture/状态判定，显式区分DOM变化与EMPTY；归一URL、质量门槛和raw&#95;count口径。</span>

#### <span id="p0683">11. SogouSearchAdapter   sogou&#95;search</span>

<span id="p0684">证据：sogou&#95;search.py:60–139、157–228、249–394。</span>

<span id="p0685">- 输入→机制：非空keyword、max&#95;results；构造requests.Session，可选凭据失败回匿名。依次news.sogou.com/news?mode=1&amp;query=与www.sogou.com/web?query=，间隔1.6–3s；每频道命中验证页退避4–6s后再1次，网络异常立即失败；再最多6线程Session GET /link中转（8s），读HTTP最终URL或前4000字JS/meta跳转。</span>

<span id="p0686">- normalize→输出：BeautifulSoup div.vrwrap的标题、snippet、href、来源、publish&#95;date；新闻来源行/网页cite-date分开解析，绝对/相对日期+date&#95;source/date&#95;conflict；raw channel/link&#95;redirect/content&#95;hash/platform&#95;id/product&#95;id/domain&#95;id/cookie&#95;used；按还原后URL去重，新闻优先。缺互动保持None。hash以还原前title&#124;href计算，URL还原后不重算。</span>

<span id="p0687">- 失败/重试/空值：少于800字或反爬关键词视blocked；无任何collected且任一频道blocked即失败（并非必须两频道都blocked）；部分结果+另一频道失败仍success=True且不保留该频道错误。缺bs4返回&#91;&#93;，无blocked则成功空。无HTTP status检查；反爬错误文案“反爬验证页”未包含C1完整terminal marker，可被外层重复整个采集。</span>

<span id="p0688">- 启用/运行缺口：旧registry注册，SYSTEM无key；缺双频道实测/bs4安装、跳转还原安全和跨线程Session适用性证据。</span>

<span id="p0689">- A/B：本体相同；B start&#95;collect平台集合不含key。</span>

<span id="p0690">- 建议：返回每频道状态/PARTIAL，缺解析依赖应失败；以归一URL稳定标识且保留原链接；结构化停止验证重试；严格跳转host/scheme与日期语义。</span>

#### <span id="p0691">12. SogouWechatAdapter   sogou&#95;wechat</span>

<span id="p0692">证据：sogou&#95;wechat.py:54–146、149–272。</span>

<span id="p0693">- 输入→机制：keyword/max&#95;results和构造时product&#95;id/domain&#95;id；可选凭据、失败匿名；requests GET weixin.sogou.com/weixin?type=2&amp;query=&amp;num=，最多2尝试：验证页等待4–6s，网络异常2–3s。BeautifulSoup txt-box/sogou&#95;vr，失败/缺包正则兜底。</span>

<span id="p0694">- normalize→输出：公众号文章title/snippet/URL/account/date；相对路径补weixin.sogou.com；MD5(title&#124;URL)、platform&#95;id、product/domain/engine/cookie&#95;used；author&#95;id/cover空；publish&#95;date绝对/相对日期，无证据空。likes/comments/collects/shares显式0，和自身“缺失不用0”注释不一致。</span>

<span id="p0695">- 失败/重试/空值：短于800字/反爬关键词失败；没有status判定；非blocked但无解析结果成功空，不能区分结构失配。HTML两层选择器可能重复同条，未见本地去重。内层2次与C1外层重试可叠加，错误“反爬验证页”不保证终止。</span>

<span id="p0696">- 启用/运行缺口：只有旧registry注册，非SYSTEM wechat能力本体；缺文章原文、跳转、真实公众号身份/日期和反爬合同证据。</span>

<span id="p0697">- A/B：本体相同；B start&#95;collect不支持sogou&#95;wechat；B的wechat是另一能力，不应混为同一个adapter。</span>

<span id="p0698">- 建议：互动未知改None，补解析失败/空结果区分和去重；原文链接与搜索中转分层；结构化错误防止验证页重复请求。</span>

#### <span id="p0699">13. DianpingAdapter   dianping</span>

<span id="p0700">证据：dianping.py:11–44。</span>

<span id="p0701">- 输入→机制：keyword/max&#95;results→requests GET www.dianping.com/search/keyword/1/0&#95;{quote}，固定路径城市标识1，UA/Referer、C1 timeout；正则跨shop-list/tit/star/score，最多20个匹配。注释建议CDP但实现没有浏览器支路。</span>

<span id="p0702">- normalize→输出：title="商户名 - 评分{score}"；content为“商户评价，关键词…”模板，非真实评论正文；商户URL、author=大众点评、likes=0，其余默认。</span>

<span id="p0703">- 失败/重试/空值：只异常失败，无status/登录/验证码检测；0个匹配即success空；score只拼进标题，非typed评分；无真实评价详情/分页。</span>

<span id="p0704">- 启用/运行缺口：仅旧registry注册，SYSTEM无key；缺城市范围、商户列表结构和真实评价获取证据，不能宣称商户评价采集已通。</span>

<span id="p0705">- A/B：本体相同；B start&#95;collect不含key。</span>

<span id="p0706">- 建议：能力名改为商户发现并显式城市输入；评价正文、评分、互动量分别建合同，未观测量None；受限页面需失败状态，不能依赖注释。</span>

#### <span id="p0707">14. SmzdmAdapter   smzdm</span>

<span id="p0708">证据：smzdm.py:11–34。</span>

<span id="p0709">- 输入→机制：keyword/max&#95;results→requests GET search.smzdm.com/?c=home&amp;s={quote}&amp;v=b，UA、C1 timeout；正则h5.feed-block&#95;&#95;title内链接，内部固定最多20条，max&#95;results仅最终截断。</span>

<span id="p0710">- normalize→输出：去HTMLtitle、原href、author=什么值得买；content/作者ID/时间为空、互动None；raw&#95;count解析总数。</span>

<span id="p0711">- 失败/重试/空值：只捕异常；未检查HTTP/challenge，正则0匹配即success空；无详情、价格、评论、作者、分页实现。</span>

<span id="p0712">- 启用/运行缺口：只有旧registry注册，SYSTEM无key；缺当前DOM、反爬/正常空样例，不能当价格或购买数据接口。</span>

<span id="p0713">- A/B：本体相同；B start&#95;collect不含key。</span>

<span id="p0714">- 建议：明确只是标题/链接发现；状态/结构验证先于EMPTY，保证URL规范及输入限制；不推定价格或活动字段已支持。</span>

#### <span id="p0715">15. JiguangAdapter   jiguang</span>

<span id="p0716">证据：jiguang.py:40–130；human&#95;browser.py:835–900。</span>

<span id="p0717">- 输入→机制：非空keyword/max&#95;results，Cookie ACTIVE前置；HumanBrowser(port=9224,auto&#95;ensure默认True)，连接后注入授权上下文，goto www.jiguang.cn/；不把keyword放URL、表单或任何检索，抓通用div.card/item/li文本，最多20。非JPush推送API、非广告统计API。</span>

<span id="p0718">- normalize→输出：每个长度10–500文本→title&#91;:80&#93;/content&#91;:500&#93;、所有note URL同为主页、author=jiguang、日期空；4个互动量0，raw engine=jiguang&#95;cdp/index。keyword完全未进入结果筛选。</span>

<span id="p0719">- 失败/重试/空值：没有有效Cookie失败；只看最终URL含login/signin判断失效，未统一challenge/频控/域名/业务身份检测；解析异常吞掉，页面可达无结构即success=True+&#91;&#93;并附error。全量同URL在registry合并时会只保留第一条，不能作为独立内容ID。</span>

<span id="p0720">- 启用/运行缺口：仅旧registry注册，SYSTEM无jiguang readonly&#95;worker；固定9224依赖HumanBrowser额外找到合法registered profile，实际是否存在未知。缺登录后的营销页面、查询、内容实体和统计接口证据。</span>

<span id="p0721">- A/B：本体相同；B start&#95;collect不含key；不能将其与别处JiguangCollector/极光API服务归并为同一完成能力。</span>

<span id="p0722">- 建议：暂标“主页结构探测/未实现关键词采集”，不要宣传搜索成功；若确需接入，先确定授权产品页面/endpoint与实体schema，独立内容ID、未知量None、严格状态合同，再请求具体修改授权。</span>

### <span id="p0723">建议验收次序 本次未实施</span>

<span id="p0724">1. 离线合同：Facebook URL组装；Instagram官方路由拒绝None；C1跨query缓存、terminal code、partial/metadata传播；各类None/0、raw&#95;count、creator指标量纲。</span>

<span id="p0725">2. 每个平台独立的脱敏静态fixture：有效响应、明确空、结构变化、403/429、登录/验证、部分结果、原生ID错配、缩写计数。不要把fixture通过写成live通过。</span>

<span id="p0726">3. 获得明确授权后，限定已获平台权限和只读worker开展最小live验收；保存调用入口(A/B)、请求身份、开始/结束时间、原生响应/DOM定位、输出字段、失败状态、无需记录凭据。缺字段留未知，不以主页可达或HTTP200抵消。</span>

<span id="p0727">4. 任何代码、数据库、运行环境修复都需用户具体修改授权；本文只提出建议。</span>

<span id="p0728"></span>

<span id="p0729">审查时间：2026-10-17 UTC。</span>

### <span id="p0730">结论与证据边界</span>

<span id="p0731">- 六个指定主链路文件的 A/B 原始字节完全相同，行号可共用；并非只比较了方法名。逐文件 SHA-256 与实际读取/检索范围在 社交适配器读取范围记录。</span>

<span id="p0732">- 五项存在可追踪的采集委托代码：Douyin、XHS、Instagram、Facebook、X；XHS App Topic 的两个核心提供方函数仍为固定空返回，只有接口框架。</span>

<span id="p0733">- enabled=True/False、注册、endpoint 配置、worker 可达、cookie 元数据、代码中的 SUCCESS 返回分支，均不构成平台实际采集成功证据。本次没有运行任何这些分支。</span>

<span id="p0734">- XHS 类默认启用；Douyin/Instagram/Facebook/X 类默认关闭；XHS App Topic 由导入时环境开关决定，默认关闭。除 App Topic 外，所审阅的 search 方法不在方法内检查类的 enabled，因此也不能将 enabled=False 解读为所有直接调用都被阻止。</span>

<span id="p0735">- 搜索列表不等于原文详情。Douyin/Instagram/Facebook/X 都有搜索观察与逐帖详情分离，但失败清空范围、身份键、完整性标签并不一致。图片/视频 URL hints 不代表媒体文件已下载或 artifact 已创建。</span>

<span id="p0736">- 高优先级静态风险：Instagram 的两条路径使用不同 ID/schema；Instagram 主链路详情异常处理引用未定义的 logger；Facebook 评论仍映射到 items 且缺原生评论身份；XHS App Topic health&#95;check 可把字符串配置误报为 SUCCESS；X 评论实际后端明确不支持。以下均有代码行号，未将静态风险表述为已复现故障。</span>

#### <span id="p0737">本次范围</span>

<span id="p0738">- A：主线commit 4dab98ed6357133da9307de846180ed4f7bba5f5。</span>

<span id="p0739">- B：2026-10-17恢复候选NOT&#95;FINAL。</span>

<span id="p0740">- 主文件前缀 M：lumenis/system/collector/adapters/。</span>

<span id="p0741">- 机制补充前缀 E：lumenis/adapters/；另只读必要的 collector.py、M/base.py、M/public&#95;source.py、M/routing.py 代码片段及函数/endpoint 索引。</span>

<span id="p0742">- 下文无特别注明的路径均相对 A。B 的一致性结论仅覆盖六个指定 M 文件；辅助文件未进行 B 内容审查，不能据此声称整棵依赖树、部署或配置一致。</span>

<span id="p0743">- 没有读取 .env、cookie 文件、凭据、session 数据、浏览器 profile 内容、git 认证或数据库；没有导入/运行产品代码、探测 endpoint、启动浏览器、执行测试或发起平台请求。读取源码中的配置变量名/文件引用不等于读取其实际值。</span>

<span id="p0744">- 没有审阅本轮真实运行记录或调用产物。因此运行证据均为“未在本次范围核验”，不能推导成“历史上从未运行”。本次未修改产品。</span>

### <span id="p0745">1. Douyin   抖音</span>

#### <span id="p0746">输入 → endpoint   浏览器   委托</span>

<span id="p0747">- M/douyin.py:232-240 search(keyword, kwargs) 把 max&#95;results 转 int（默认 20）。若后端有 breaker 与 safe&#95;collect，则调用 safe&#95;collect(keyword, max&#95;results, allow&#95;fallback=False)；否则直接调用 search。此 wrapper 没有 20 条上限钳制。</span>

<span id="p0748">- M/douyin.py:40-49 &#95;load&#95;backend 懒加载 E/douyin.py 的 DouyinAdapter；389-396 将详情、评论、作者分别委托为 aweme&#95;id、aweme&#95;id+max&#95;comments、sec&#95;uid。comments 的 include&#95;replies 参数没有下传。</span>

<span id="p0749">- E/douyin.py:39-84 &#95;configured&#95;browser&#95;worker&#95;url / &#95;new&#95;browser&#95;worker 要求显式 DOUYIN&#95;CDP&#95;URL，限制 URL 形状；本地例外须精确 opt-in DOUYIN&#95;READONLY、端口 9225 且 profile/进程匹配。这里是源码约束，不是本次观测到的实际配置。</span>

<span id="p0750">- E/douyin.py:123-171 &#95;search&#95;browser 连接 HumanBrowser/CDP，调用已有注入入口，监听完成的 xhr/fetch；36 的匹配键为 general/search/single 和 general/search/stream。浏览器访问 https://www.douyin.com/search/{URL编码关键词}?type=general，解析 JSON 或多段流式 JSON。211-227 有最多三轮滚动；没有结构化 notes 时才尝试 DOM 卡片兜底。不是 wrapper 直接向第三方 API 发 HTTP。</span>

<span id="p0751">- E/douyin.py:403-416、481-521 详情访问 /video/{aweme&#95;id}，等待完成的 aweme/detail 响应并核对返回 aweme&#95;id；577-605 评论监听 comment/list；634-654 作者页访问 /user/{sec&#95;uid} 并监听 user/profile。</span>

#### <span id="p0752">normalize 与真实性</span>

<span id="p0753">- M/douyin.py:71-104 &#95;v4&#95;notes&#95;to&#95;items：raw.aweme&#95;id → platform&#95;content&#95;id；CollectedNote 的 title/content/author&#95;id/author/publish&#95;date/url → 主字段；likes/comments/collects/shares 保留缺失。views 仅接受非负、非 bool 的 int，取 detail metrics.play&#95;count 或 search raw.play&#95;count，否则 None。</span>

<span id="p0754">- M/base.py:143-160 仅挑选跨平台 transport 字段；Douyin 在 M/douyin.py:98-102 特别补回 views，避免被共享 normalizer 丢掉。raw 保留。</span>

<span id="p0755">- M/douyin.py:140-158 存档搜索正文、标题、时间、指标和 JSON locator；161-230 写 detail&#95;observation。搜索中每个原生 ID 调后端 detail，必须匹配原生 ID 后才替换正文与详情指标（249-300）。成功详情仅保留 URL hints，media&#95;bytes&#95;saved/artifact&#95;created 都为 False。</span>

#### <span id="p0756">失败 重试 空值</span>

<span id="p0757">- &#95;v4&#95;status&#95;to&#95;main（52-69）按文本区分配置、session、风险、封禁、冷却、provider 与普通错误；详情另有 &#95;detail&#95;failure&#95;state（115-137）及终止集合（12-21）。终止后其余 items 为 PENDING，成功同 ID 在本次调用内复用（261-300），无详情失败重试循环。</span>

<span id="p0758">- 主链路确实走 E/base.py:214-296 的 collect/safe&#95;collect：令牌等待最多 10 秒、熔断、按配置 max&#95;retries 重试，延时 retry&#95;delay×(attempt+1)；认证/风控/限频等终态不继续重试（273-282）。本次未读取 ADAPTER&#95;CONFIG 的实际取值，不能报确定重试次数。allow&#95;fallback=False 在 298-303 阻止缓存或 fallback&#95;handler 冒充本次结果。</span>

<span id="p0759">- 搜索后端只有结构化空结果证据才返回正常空（E/douyin.py:235-241）；风险/登录/网络状态会保留已经观察到的部分卡片但返回失败（181-205）。</span>

<span id="p0760">- 详情失败清空正文、标题、views（M/douyin.py:202-210），但 search 的 author/publish&#95;datetime/likes/comments/collects/shares 不在该失败分支清空；它们同时存档在 search&#95;summary&#95;observation。因此下游必须区分“搜索所见指标”与“详情所见指标”。不能只看顶层值就说详情已验证。</span>

<span id="p0761">- body&#95;completeness=COMPLETE 在 307-316 仅由详情计数是否失败/待办决定，不能自动证明 caption 完整、媒体保存或所有时间字段存在。</span>

#### <span id="p0762">enabled   运行证据缺口   建议</span>

<span id="p0763">- 默认 enabled=False，monitor&#95;priority=secondary（32-34）。health&#95;check（398-461）最多证明 endpoint/worker 连通与 engine 能加载，成功连通返回 NEED&#95;VERIFY，明确保留 worker&#95;reachable&#95;unverified。</span>

<span id="p0764">- 缺本次运行的 worker owner/许可核验结果、平台登录实测、search/detail 原始匹配响应、逐项时间/指标 locator、空结果与限频样本。源码注释“完整搜索采集”不是验收记录；类 docstring 中“detail/comments/creator 待补全”也已与实际委托代码不完全一致。</span>

<span id="p0765">- 建议：清单标“浏览器+XHR 实现，默认关闭，运行未核验”；验收时覆盖终态停采与 summary-only 项；下游不得把 COMPLETE 和 top-level metrics 当作原文/媒体完备证明。任何修改仍需单独授权。</span>

### <span id="p0766">2. XHS   香港 国际小红书 RedNote</span>

#### <span id="p0767">输入 → endpoint   浏览器   委托</span>

<span id="p0768">- M/xhs.py:29-36 &#95;load&#95;backend 导入已有顶层 collector；38-149 search 调 search&#95;xiaohongshu。输入有 keyword、max&#95;scroll、max&#95;details/max&#95;results、region/account、time&#95;budget、worker&#95;chunk&#95;seconds、output/resume 路径、acquisition&#95;fingerprint、detail&#95;media&#95;mode（仅 legacy/cover&#95;only）。</span>

<span id="p0769">- 有 fingerprint 时必须为 64 位小写十六进制，详情 limit &gt;0 且钳制至 20；无 fingerprint 沿用 legacy max&#95;details（0 表示本次所见全部卡片）、固定 intl，account=None 交既有策略选择（47-77）。checkpoint 恢复核对任务、身份、路径和媒体模式，禁止调用方随意指定没有对应 owner 的恢复文件（84-130）。</span>

<span id="p0770">- collector.py:878-925 search&#95;xiaohongshu 经身份/区域策略 gate，取得已注册 worker；968-982 核验脚本与 CDP 在线后只调用 &#95;search&#95;via&#95;cdp，不在这条路径切到旧 standalone 搜索。</span>

<span id="p0771">- collector.py:351-374、442-495 &#95;resolve&#95;server&#95;cdp&#95;url 仅接受精确 SYSTEM 注册的 XHS worker；配置的远端 URL 直接返回 COLLECTOR&#95;REMOTE&#95;WORKER&#95;IDENTITY&#95;UNVERIFIED（450-456），实际本地 endpoint 来自注册状态，并验证账号、headless、loopback 与端口 owner。M 的“远程 Worker”提示语不能代替这里的运行边界事实。</span>

<span id="p0772">- collector.py:207 将 CDP&#95;SCRIPT 设为 xhs&#95;cdp&#95;collector.py；702-768 构造 Python 子进程参数传入 keyword、scroll/detail 上限、CDP URL、run-id、chunk/time budget 和恢复参数。已读范围只追到这个委托边界；本次未审阅该 worker 脚本或内部浏览器 DOM/HTTP API，不能臆报最终平台请求路径。源站身份固定 www.rednote.com（M/xhs.py:312、331；collector.py:779）。</span>

#### <span id="p0773">normalize 与真实性</span>

<span id="p0774">- wrapper 不调用 BasePlatformAdapter.normalize&#95;item，直接返回过滤后的 notes（M/xhs.py:150-152、302-307）；这与其他平台“统一 platform&#95;content&#95;id 字段”的假设不同。</span>

<span id="p0775">- collector.py:631-699 &#95;norm&#95;cdp&#95;note 负责映射：note&#95;id、详情/卡片 title/content、url/cover、作者、四项计数、publish&#95;date/publish&#95;time/detail&#95;publish&#95;time、时间来源观察、captured&#95;at、source&#95;channel、评论/媒体列表、detail&#95;fetched、detail&#95;identity&#95;verified、source&#95;note&#95;ids 等。数值只接受非负整数、整值浮点或 ASCII 数字字符串；bool、未知、负数→None，真实 0 保留。时间来源不属 detail/card 则发布时间置空；采集时间独立。</span>

<span id="p0776">- 有 fingerprint 时只有整体 identity&#95;verified 且每条 detail&#95;fetched/detail&#95;identity&#95;verified 为 True 的 notes 才进入结果（M/xhs.py:226-230）。无 fingerprint 的 legacy 分支没有同一筛选强度，不应把两个调用模式等同。</span>

<span id="p0777">- 恢复元数据记录 partial、pending&#95;note&#95;ids、continuation&#95;required、checkpoint&#95;complete/identity/run-id 等；pagination&#95;exhausted 固定 False（325-354），不能称完整翻页。</span>

#### <span id="p0778">失败 重试 空值</span>

<span id="p0779">- M/xhs.py:259-286 映射 IP&#95;RISK&#95;OR&#95;300012→RISK&#95;WARNING、SESSION&#95;EXPIRED、NEED&#95;VERIFY、配置/策略拒绝→NOT&#95;CONFIGURED、CDP 超时/不可达→PROVIDER&#95;UNAVAILABLE；其他 error→COLLECT&#95;ERROR；没有 error 才按 notes 判断 SUCCESS/NO&#95;NEW&#95;DATA。</span>

<span id="p0780">- collector.py:591-623 仅 CDP /json/version 连通性探针有可选 tenacity：最多 3 次，指数等待 0.2–1.2 秒，仅网络异常重试；未安装 tenacity 则单次。不能把它当作平台采集三次重试。</span>

<span id="p0781">- 子进程超时后仅恢复本次 run-id/keyword/source host/身份/fingerprint 绑定正确的原子 checkpoint；没有合法 checkpoint→CDP&#95;TIMEOUT&#95;NO&#95;CHECKPOINT，未完成→CDP&#95;TIMEOUT&#95;PARTIAL（collector.py:765-799）。M 层会验证新 chunk、持久化 owner 指针，失败可保留已验证项，continuation&#95;required 明示未完成（178-224、371-393）。不是自动循环直到成功。</span>

<span id="p0782">- 静态边界风险：M/xhs.py:150 将非 dict 后端返回降成 {}，notes 非 list 降为空（152），没有 error 时最终落 NO&#95;NEW&#95;DATA（283-286）。这意味着异常响应形状可能被当成正常空；本次未做复现。</span>

<span id="p0783">- 独立 detail 明确 NOT&#95;SUPPORTED（395-403）；该搜索链内部读详情不能被宣传成独立详情 API 已开放。</span>

#### <span id="p0784">enabled   运行证据缺口   建议</span>

<span id="p0785">- enabled=True、primary（21-23）。health&#95;check 先 gate 再解析 endpoint；缺少能力→NOT&#95;CONFIGURED，可达→NEED&#95;VERIFY，scope=worker&#95;connectivity（405-486）。因此启用或连通不代表平台登录及采集成功。</span>

<span id="p0786">- 缺本轮 SYSTEM 注册身份、运行许可、实际 CDP/平台访问、identity-verified checkpoint、worker 子脚本产物与完整时间语义证据；没有读取这些运行数据。</span>

<span id="p0787">- 建议：清单写“现有 collector 委托链，注册 SYSTEM 浏览器，独立 detail 未接”；区分 legacy 与 purpose-bound 调用；后续经授权应先为 malformed response、超时 checkpoint 与身份不匹配补 contract 测试，验收不可用普通空列表代替缺失响应证据。</span>

### <span id="p0788">3. XHS App Topic   App 话题</span>

#### <span id="p0789">输入 → endpoint   委托</span>

<span id="p0790">- M/xhs&#95;app&#95;topic.py:64-111 search 输入 keyword；113-151 detail 输入话题名/ID。构造函数接受 session&#95;manager/proxy&#95;manager/cdp&#95;port/app&#95;api&#95;endpoint（54-60），endpoint 可由 XHS&#95;APP&#95;API&#95;ENDPOINT 提供。</span>

<span id="p0791">- 但 &#95;discover&#95;topics&#95;from&#95;app（187-206）硬返回 &#91;&#93;，&#95;topic&#95;metrics&#95;from&#95;app（208-225）硬返回 None。当前没有使用 endpoint 发请求、没有 HTTP client、没有 App API/签名实现；cdp&#95;port 仅保存并显示在 health metadata。不得把预留字段当成已接 API。</span>

#### <span id="p0792">normalize   失败   重试   空值</span>

<span id="p0793">- 文档预期结构是 topic&#95;name/topic&#95;id/browse&#95;count/discussion&#95;count/note&#95;count/source；detail 还列 captured&#95;at。这只是 docstring 示例，当前无产生这些字段的请求逻辑。</span>

<span id="p0794">- search/detail 不调用 normalize&#95;item，若未来 hook 返回内容则直接作为 items；enrich&#95;note&#95;with&#95;source（230-237）只是原位追加 source/data&#95;source，不在 search/detail 内自动调用。</span>

<span id="p0795">- 开关关闭→COLLECT&#95;ERROR；开启但 hook 空→NO&#95;NEW&#95;DATA；异常→COLLECT&#95;ERROR（75-110、118-150）。无重试、无 Web 回退。虽然不伪造数值，但“未实现/未配置”目前被表达成“无新数据”，语义应区分。</span>

#### <span id="p0796">enabled   运行证据缺口   建议</span>

<span id="p0797">- 模块导入时读取 XHS&#95;APP&#95;TOPIC&#95;ENABLED，默认 false，类 enabled=FEATURE&#95;FLAG（28-29、50-52）；is&#95;enabled（240-242）返回同一个导入时值，不证明动态开关已经刷新。</span>

<span id="p0798">- health&#95;check（153-183）30 秒缓存，只检查 flag 与 endpoint 字符串是否非空；flag 开启且 endpoint 非空就 SUCCESS，无网络/CDP/API 调用。其 docstring“API可用性 + CDP连接状态”不能当作实现证据。</span>

<span id="p0799">- 缺实际 App 协议、endpoint、签名、响应 schema 和合法的真实运行产物。此项确定为“占位框架”，不能列“已完成第三方接入”。</span>

<span id="p0800">- 建议：保留未上线口径；后续需单独授权实现，届时将 NOT&#95;CONFIGURED/NOT&#95;SUPPORTED 与真实 NO&#95;NEW&#95;DATA 分开，health scope 先明确为 configuration&#95;only，再以获准真实请求验收。</span>

### <span id="p0801">4. Instagram</span>

#### <span id="p0802">输入 → 两条路径</span>

<span id="p0803">- M/instagram.py:405-447 search 先校验可选 native&#95;topic&#95;reference（142-193：必须精确匹配批准 seed 的摘要与行字段），再调用 resolve&#95;capability&#95;route。M/routing.py:65-82、202-215 声明并选择公开帖 URL 与登录 session 两类路线；这是路由代码，不是运行许可凭据。</span>

<span id="p0804">- 公开帖 URL → &#95;public&#95;detail（573-597），严格接受 HTTPS instagram.com/www.instagram.com 的 /p&#124;reel&#124;tv/{shortcode}，调用 public&#95;fetcher，最终 host 仍须官方。它使用普通 HTTP 文档路径，不经浏览器登录；不会因公开抓取失败自动降级成登录采集。</span>

<span id="p0805">- 公共传输 M/public&#95;source.py:416-532 使用 requests.Session.get、TLS 验证、逐跳重验、流式大小限制；31-32 上限 2 MiB 与最多 3 次跳转；398-413 拒绝 Authorization/Cookie 头。默认 timeout 10s、连接至多 5s/读取至多 15s，循环是 redirect 而非采集重试。</span>

<span id="p0806">- 登录查询 → &#95;get&#95;engine（133-139）→ E/instagram.py:146-255：已注册只读 HumanBrowser，打开官方主页，观察并操作可见搜索输入框 fill(keyword)+Enter；不是凭空调用某个搜索 API。批准原生 hashtag 则走 /explore/tags/{编码标签}/，核验最终路径和页面状态（352-420），超时不回退关键词搜索。</span>

<span id="p0807">- 搜索每条 shortcode→engine.detail，详情以 /p/{shortcode}/ 或 /reel/{shortcode}/ 读取 DOM，并校验最终官方 URL 的 shortcode（M:460-514；E:700-779）。评论/作者分别委托对应 engine 方法（M:635-706）；E:983-995、1111-1123 访问帖子或 username 页面。</span>

#### <span id="p0808">normalize 与真实性</span>

<span id="p0809">- 浏览器路线 &#95;notes&#95;to&#95;items / normalize&#95;item（M:220-225、732-757）：raw&#95;data.shortcode 优先，其次 URL 提取，作为 platform&#95;content&#95;id；author→author&#95;nickname、publish&#95;date→publish&#95;datetime，四项 count 经 optional&#95;int，保留 raw/captured&#95;at。optional&#95;int 的共用实现 E/base.py:24-31 是 int 转换+空值保留，并非严格非负验证器。</span>

<span id="p0810">- 搜索 preview 独立存档后，顶层正文/标题/作者/时间清空、四项计数为 None（296-329）；详情必须 raw.native&#95;identity 的 requested/observed shortcode、status=OBSERVED&#95;MATCH、raw shortcode 与官方 URL 同时一致（261-270）。</span>

<span id="p0811">- 详情标为 CAPTION&#95;OBSERVED&#95;COMPLETENESS&#95;UNKNOWN / DOM&#95;COMPLETENESS&#95;UNKNOWN；时间、指标、media ID 分别记录是否观察到；媒体仅 hints（332-400、520-536）。成功详情不能翻译为已证明完整 caption。</span>

<span id="p0812">- 公开路线 parse&#95;public&#95;instagram&#95;document（32-101）递归找唯一匹配 code/pk/if&#95;not&#95;gated&#95;logged&#95;out，对内外 pk/code 作一致检查；无非空 caption 则拒绝。提取 taken&#95;at（与 caption&#95;created&#95;at 区分）、作者、likes/comment&#95;count、公开评论白名单、媒体 URL、原文 SHA-256/locators/hashtags；缺 shares/views/collects→None。</span>

<span id="p0813">- 重要 schema 差异：公开返回 platform='instagram' 且 platform&#95;content&#95;id=media pk（97-101）；浏览器返回 source&#95;platform='instagram' 且 ID=shortcode（742-756）。公开项直接返回，未经过该类 normalize&#95;item（590-594）。下游若把两路 ID 当作同一空间，可能重复或无法关联；本次没有审阅下游去重，不能宣称已发生重复。</span>

<span id="p0814">- comments 把 notes&#91;0&#93;.raw&#95;data.comments 放入 CollectionResult.comments，items=&#91;&#93;；include&#95;replies 只写 metadata，未传给 engine（635-667）。</span>

#### <span id="p0815">失败 重试 空值</span>

<span id="p0816">- &#95;map&#95;status（199-215）与 &#95;detail&#95;failure&#95;state（273-293）细分 session/challenge/rate/provider；身份冲突或终态停后续 detail，留 PENDING；成功同 shortcode 本次复用，普通失败不是无界重试（460-514）。主 wrapper 直接 engine.search，未调用 BaseAdapter.safe&#95;collect，不能继承性宣称本调用有统一熔断重试。</span>

<span id="p0817">- 公开解析匹配失败→PROVIDER&#95;UNAVAILABLE，跨 host→BLOCKED，异常→PROVIDER&#95;UNAVAILABLE；无公开正文时不冒充空数据成功（573-597）。</span>

<span id="p0818">- 静态缺陷候选：M/instagram.py:488 的详情异常分支调用 logger.error，但全文唯一 logger 引用就是这里，未导入 logging、未定义 logger。若 engine.detail 抛异常且无外部注入全局 logger，此分支会再触发 NameError，随后 566-571 返回整批 COLLECT&#95;ERROR，可能丢掉原计划保留的部分 items/detail&#95;counts。未执行复现，建议先离线 fixture 验证。</span>

#### <span id="p0819">enabled   运行证据缺口   建议</span>

<span id="p0820">- enabled=False、secondary（115-117）。health&#95;check 对公开路线仅返回 NEED&#95;VERIFY/public&#95;document&#95;requires&#95;actual&#95;read；其他路线委托 readonly&#95;worker&#95;health，并明示登录与结果待验证（708-727）。COOKIE&#95;PATH 常量存在不是 session 已验证证据。</span>

<span id="p0821">- 缺公开文档真实 fetch/哈希、浏览器 worker 绑定、授权 session、精确 permalink 与 DOM 原文、关键字段缺失/限频样本；本次不读取 cookie，也未发请求。</span>

<span id="p0822">- 建议：清单分列“公开原生帖文档 HTTP”和“登录浏览器搜索/详情”；统一或显式标识 pk/shortcode 身份空间、source&#95;platform schema；优先验证 logger 异常路径与 include&#95;replies 合约。改代码需另获授权。</span>

### <span id="p0823">5. Facebook</span>

#### <span id="p0824">输入 → endpoint   委托</span>

<span id="p0825">- M/facebook.py:27-34 加载 E/facebook.py；203-213 search 输入 keyword、max&#95;results（默认 20、钳制 0–20）；332-344 detail/comments/creator 直接委托。</span>

<span id="p0826">- E/facebook.py:295-368 search 使用 registered read-only worker 的 HumanBrowser/CDP（auto&#95;ensure=False），已有 cookie 注入入口，访问 https://www.facebook.com/search/top?q={编码关键词}；读取 div&#91;role=article&#93;，无时用通用内容块选择器。不调用 Graph API。</span>

<span id="p0827">- M/facebook.py:73-93 原生身份必须 raw.post&#95;id 与 URL permalink 解析的 ID 一致。逐帖调用 backend.detail(item.url)（245-259）。E/facebook.py:493-540 detail 仅接受被 observed&#95;post&#95;permalink 识别的精确原生链接，核对最终 URL、目标 article 与返回 post&#95;id。</span>

<span id="p0828">- E/facebook.py:548-607 comments 浏览帖子页面、尝试“查看更多评论”按钮并读 DOM；609-651 creator 浏览主页读 h1。两者在已读函数中未采用 detail 同等的最终 permalink/目标身份核验。</span>

#### <span id="p0829">normalize 与真实性</span>

<span id="p0830">- M/facebook.py:51-70 raw.post&#95;id→platform&#95;content&#95;id，其余 title/content/author/date/url 与四指标映射至 M/base.py:143-160；未观察到的 metric 默认为 None。</span>

<span id="p0831">- search preview 独立存档（114-138），detail&#95;observation 记录正文、原生时间/指标、audience&#95;observation、media hints 与 locator（141-201）。详情失败仅清空正文与标题，保留搜索作者、时间和顶层四指标，须按 provenance 使用。</span>

<span id="p0832">- body&#95;completeness=COMPLETE（287-295）只统计是否有失败/待办/缺 ID；每条正文自己的 body&#95;status 仍可为 OBSERVED&#95;COMPLETENESS&#95;UNKNOWN 或 未观察（164-165）。因此整批 COMPLETE 不等于原文完整性已证实。</span>

<span id="p0833">- 评论合约差异：E/facebook.py:583-597 返回 CollectedNote，url/author&#95;id/publish&#95;date 空，raw 只有 metric&#95;display，没有原生 comment ID/parent post ID；M/facebook.py:341-350 用通用 &#95;v4&#95;notes&#95;to&#95;items 放进 items，而非 comments 字段。由 raw.post&#95;id 缺失导致 platform&#95;content&#95;id 为空，source&#95;platform 被设成 facebook。不能据存在 comments 方法宣称已提供可验证、可去重的规范评论结果。</span>

#### <span id="p0834">失败 重试 空值</span>

<span id="p0835">- wrapper status 映射 37-49，详情失败分类 96-111。身份冲突/session/risk/blocked/provider 等终止后续 detail 并保留 PENDING；成功同 ID 本次复用（223-280）。无 wrapper 自主重试，search 直接后端 search，未走 BaseAdapter.safe&#95;collect。</span>

<span id="p0836">- 搜索无 cards 时，仅看到明确无结果文案才正常空；无 card/无可解析 post observation 则 PROVIDER&#95;UNAVAILABLE（E:336-361）。limit=0 则直接 success empty（295-304），这是人为请求上限，不能用来证明平台无内容。</span>

<span id="p0837">- 评论后端没有 notes 也 success=True（E:601），wrapper 将映射 NO&#95;NEW&#95;DATA；该空结果未证实“帖子确实无评论”。creator 缺 h1 时用输入 username 兜底并返回成功（E:628-645），也不是所有字段均观察到。</span>

#### <span id="p0838">enabled   运行证据缺口   建议</span>

<span id="p0839">- 默认 enabled=False/secondary（19-21）；health&#95;check 仅 readonly&#95;worker&#95;health 与登录待实测声明（358-366）。</span>

<span id="p0840">- 缺注册 worker/授权状态、搜索与精确帖同 ID 运行产物、原文与 metric locator、评论 parent/ID 验证、private/audience 场景证据。类 docstring 与 route 存在不构成 Graph API 或官方平台合作接入。</span>

<span id="p0841">- 建议：按“浏览器 DOM 实现、默认关闭、运行未核验”列示；详情 COMPLETE 不作为全文验收；评论/作者能力应单独给低置信/合约缺口，先做离线错 ID、空 DOM、无原生评论 ID 的测试后再批准上线。</span>

### <span id="p0842">6. X   Twitter</span>

#### <span id="p0843">输入 → endpoint   委托</span>

<span id="p0844">- M/x&#95;platform.py:34-41 加载 E/x&#95;platform.py；289-325 search 输入 keyword、max&#95;results（默认 20、钳制 0–20）、可选 64 位小写十六进制 acquisition&#95;fingerprint。存在 fingerprint 时从 Checkpoint('x').seen&#95;ids('scope:'+fingerprint) 取得 skip&#95;tweet&#95;ids 后传给 engine；本次未读取 checkpoint 数据。</span>

<span id="p0845">- E/x&#95;platform.py:36-61 要求固定 X&#95;READONLY&#95;CDP&#95;URL 与 explicit X&#95;READONLY local worker opt-in、绑定的 profile/9226 listener；源码固定 loopback 常量见 33，实际配置未查。189-243 连接 HumanBrowser、注入已有 cookie、访问 https://x.com/search?q={编码关键词}&amp;src=typed&#95;query、读取 article 并滚动。</span>

<span id="p0846">- 后端是有界 DOM batch：最多 20 项、最多 8 轮滚动、连续 2 轮无新 ID 停止（E:137、241-258），不能称全量历史采集或完整分页。</span>

<span id="p0847">- M:359-367 逐帖 detail(tweet&#95;id)。E:623-668 将数值 ID/合法 X status URL 化为原生详情 URL，核对最终 URL 的 ID，目标 article 必须唯一匹配。E:677-706 creator 验证 handle 1–15 位、读 https://x.com/{handle} 的昵称/粉丝显示。</span>

<span id="p0848">- 评论后端明确返回失败：“reply-to-post relationships cannot be verified”，不会采集（E:670-675）。wrapper 与 routing 中虽然存在 comments 委托，实际能力应为 NOT&#95;SUPPORTED。</span>

#### <span id="p0849">normalize 与真实性</span>

<span id="p0850">- M:64-82 raw.tweet&#95;id→platform&#95;content&#95;id，其余为跨平台基本字段；raw 保留。搜索身份要求数字字符串 ID、item URL/raw URL 同 ID、tweet&#95;id&#95;locator、native&#95;identity.status=OBSERVED（102-118）；详情还要求 requested/final/observed ID 与官方 URL 一致、status=OBSERVED&#95;MATCH（121-131）。</span>

<span id="p0851">- &#95;begin&#95;detail&#95;observation（166-202）先存档 preview，再清理原生时间/指标/媒体 locator，清空顶层正文/标题/作者/发布时间与四项 count。&#95;record&#95;detail&#95;outcome（205-271）只有成功详情才恢复；缺正文→NATIVE&#95;BODY&#95;UNAVAILABLE，正文存在仍 DOM&#95;COMPLETENESS&#95;UNKNOWN，媒体仅 URL hints。</span>

<span id="p0852">- continuation 元数据（274-287、405-431）明确 committed&#95;id&#95;count=0、native&#95;cursor=None、pagination&#95;exhausted=None、coverage&#95;complete=False。这只说明当前适配器未承诺写入已提交 ID/完整分页，不代表别的流水线最终提交了或没提交。</span>

#### <span id="p0853">失败 重试 空值</span>

<span id="p0854">- &#95;v4&#95;status&#95;to&#95;main（44-62）区分 unsupported/config/session/risk/rate/provider。search 直接后端，不走 BaseAdapter.safe&#95;collect；详情没有主动重试。</span>

<span id="p0855">- 详情本次缓存成功和失败两种结果（348-382）；相同 ID 的失败不会重复抓。session/risk/blocked/provider/not configured/not supported 在终态集合（13-16），停止后续详情；IDENTITY&#95;MISMATCH 不在该全局终态集合，作为单帖失败处理，其他不同 ID 可继续。</span>

<span id="p0856">- 没有任何身份验证原文时整批强制 COLLECT&#95;ERROR（441-443），即便原 search.success=True。部分有效正文加其他 ID 失败仍可返回 partial，须看 detail 元数据。</span>

<span id="p0857">- 后端若观察的所有 ID 都在已提交 skip 集合可正常空（E:265-270）；否则无可验证帖子返回失败，不把未加载 DOM 当作无内容（271-274）。</span>

#### <span id="p0858">enabled   运行证据缺口   建议</span>

<span id="p0859">- 默认 enabled=False/secondary（26-28）。health&#95;check（496-511）只看 vault 的非秘密 auth-cookie 存在元数据，有则 NEED&#95;VERIFY，无则 NOT&#95;CONFIGURED；没有在这个方法核验 worker process/实际登录/采集能力。本次没有调用该方法或读取 vault。</span>

<span id="p0860">- 缺固定 worker 真实 owner、有效登录、页面原生 ID/时间/指标、skip 集合与最终入库衔接证据。8 轮滚动限制与 coverage&#95;complete=False 必须保留在使用口径中。</span>

<span id="p0861">- 建议：清单将 X 评论标为未支持，搜索标为有界浏览器批次；检查 partial 不被前端当“全量完成”；运行验收需包含无帖子、全 skip、错 ID、challenge、正文缺失、计数空值场景。</span>

### <span id="p0862">跨平台验收建议 仅建议 未执行</span>

<span id="p0863">1. 分开登记四种事实：代码存在、配置/worker 可达、真实平台读取、结果内容/身份/时间已核验。不得用任意一项替代其余三项。</span>

<span id="p0864">2. 为每条能力建立同一份证据包：输入与 route、获准 worker/身份的脱敏标识、原生 URL/ID 与字段 locator、search/detail 状态、unknown 与真实 0 的区别、partial/pending/stop reason、媒体是否仅 hints。敏感运行数据另行遵循授权范围，不在本章节中收集。</span>

<span id="p0865">3. 优先离线验证已发现的合约差异：IG pk/shortcode + platform/source&#95;platform；IG logger 异常分支；Facebook comments(items vs comments)；XHS malformed 非 dict 的正常空降级；App Topic 配置成功与能力未实现的区分。</span>

<span id="p0866">4. 对 summary-only 项、COMPLETE 标签和 new&#95;count 作谨慎解释。多个 wrapper 的 new&#95;count=len(items) 是返回项数，未证明最终入库新增、原文完整或媒体持久化。</span>

<span id="p0867">5. 本文不建议绕过登录墙、验证、平台限频或 worker owner 边界。需要产品修改或真实运行验证时，应先取得明确的具体修改/执行授权；本次审查没有实施修复或真实采集。</span>

<span id="p0868"></span>

### <span id="p0869">SYSTEM 共同合同与注册边界</span>

<span id="p0870">本章节的 A=main commit 4dab98ed6357133da9307de846180ed4f7bba5f5，B=恢复候选 NOT&#95;FINAL。以下是静态机制，不是连通、授权或生产运行验收。每项“未实测”均指本次没有请求平台、读取会话或启动采集器；旧报告中历史证据不能自动覆盖这些适配器。enabled 类属性、capability 配置、registry 注册和服务器 Permission 是四层独立事实。</span>

<span id="p0871">A 的 &#95;&#95;init&#95;&#95;.py:12–26 导入15个实现文件并注册；registry.py:22–30 仅对微信增加惰性导入。LinkedIn/Reddit/YouTube/TikTok/Channels 在A有文件、末尾register语句和目录记录，但不在该默认导入列表，不能据此说默认registry已有21项。B改为按config.adapter&#95;module导入，再保留xhs&#95;app&#95;topic兼容项。B注册仍不构造provider或自动授权；B config.py:211–224 明确这五个PLANNED项及GitHub manual&#95;collection&#95;enabled=False。secondary&#95;collection.py:68–81缓存adapter实例，因此已有breaker状态可跨调用存活。XHS主路径配置enabled=True是既有业务配置，不可被其他类默认False一概覆盖。</span>

<span id="p0872">base.py:36–70 的CollectionResult分别承载items/comments、status、raw&#95;count/new&#95;count、metadata、provenance、attempted与actual access事实；ok包括NO&#95;NEW&#95;DATA。normalize&#95;item:147–166统一source&#95;platform、platform&#95;content&#95;id、title/content、author&#95;id/nickname、publish&#95;datetime/url、likes/comments/collects/shares、captured&#95;at/raw，通常缺失为None。map&#95;v4&#95;comments:169–186由rpid/comment&#95;id/id取评论ID，作者/正文/时间缺失为空串，likes为None。capability&#95;map仅检查方法覆盖，A占位实现因此可能误报implemented。map&#95;raw&#95;to&#95;normalized (platform&#95;naming.py:751–790) 是另一套platform&#95;contents映射，缺字段None并保留raw&#95;data；不能混淆它和真实采集输出。</span>

#### <span id="p0873">共享公开HTTP transport PublicHttp Atom Sitemap WeChat</span>

<span id="p0874">public&#95;source.py:1–530：HTTP(S)无URL凭据、DNS结果必须公网、固定连接到校验IP，HTTPS保留原host的SNI/证书匹配；每次重定向重新验证，最多3次，响应最多2MiB，分块累计检查，连接≤5秒、读≤15秒（缺省读10秒）。这不是全任务墙钟deadline；慢速分块可延长总体时间。无应用级重试。拒绝Cookie/Authorization头；自建session清cookies并finally关闭response/session，调用者session还原mount并关新pool。可选DoH fallback请求dns.google/resolve且返回≤16KiB；这是额外外发hostname的机制，不等于当前启用。代理设置可能保留，仍须单独验证实际环境。YouTube视频feed显式阻断。provenance去query/fragment，商业许可仍pending&#95;review。保留该集中传输边界，建议验收总deadline、代理/DNS、内容类型和真实权限，不以“公开”推定商业可用。</span>

### <span id="p0875">SYSTEM 逐项机制 其余15项</span>

#### <span id="p0876">S07 BilibiliAdapter — bilibili.py 12–170</span>

<span id="p0877">- 输入/路径：keyword、max&#95;results→缓存的v4 Bilibili backend；存在breaker时调用safe&#95;collect(...allow&#95;fallback=False)，否则search。detail传bvid，comments传bvid/max&#95;comments，creator传mid，实际第一方API详见legacy同名项。</span>

<span id="p0878">- 输出：raw.bvid→ID，Note的title/content/author/publish&#95;date/url及四互动量→统一item，保留raw。评论独立进comments，new&#95;count取真实映射长度；不把未取字段写0。</span>

<span id="p0879">- 失败：成功空notes→NO&#95;NEW&#95;DATA；文本判别未配置、会话过期、风控/WBI、封禁412、冷却、provider unavailable；未知为COLLECT&#95;ERROR。backend不存在方法→NOT&#95;SUPPORTED；异常→PROVIDER&#95;UNAVAILABLE。外层不重试且禁v4缓存fallback；include&#95;replies未传下去。</span>

<span id="p0880">- 状态/建议：A/B相同，默认False、人工二级入口，health仅本地cookie状态+引擎存在，ACTIVE仍NEED&#95;VERIFY。本次未实测。保留委托，建议改结构化错误码替代字符串分类，并明确回复能力不支持。</span>

#### <span id="p0881">S08 WeiboAdapter — weibo.py 12–168</span>

<span id="p0882">- 输入/路径：keyword/max&#95;results→v4移动端第一方读API；search同样safe&#95;collect(allow&#95;fallback=False)。detail/comments用mid，creator用uid。</span>

<span id="p0883">- 输出：raw.id→内容ID，Note字段映射；评论通过map&#95;v4&#95;comments单独返回。缺失互动量None、缺失ID为空串，不自动构造ID。</span>

<span id="p0884">- 失败：未配置/过期/风控403/封禁/冷却/不可用字符串分类，空成功NO&#95;NEW&#95;DATA；缺方法NOT&#95;SUPPORTED，异常PROVIDER&#95;UNAVAILABLE，无wrapper重试。include&#95;replies未被转发。</span>

<span id="p0885">- 状态/建议：A/B相同、默认False、人工入口；health配置存在仍NEED&#95;VERIFY。本次未实测。保留现有权限入口；建议校验空ID、结构化失败和限流状态优先级，避免“不可用”先归BLOCKED导致后续provider分类不可达。</span>

#### <span id="p0886">S09 ZhihuAdapter — zhihu.py 12–143</span>

<span id="p0887">- 输入/路径：keyword/max&#95;results→v4.search直接调用；detail/comments携content&#95;type缺省answer，creator传user&#95;id。无注入backend时每次新构造v4，而非缓存到self.backend；实际搜索/详情HTTP见legacy项。</span>

<span id="p0888">- 输出：raw.id、Note文本/作者/时间/url；缺失互动字段默认0，comments也走&#95;items映射并放items，而不是独立comments；include&#95;replies未转发。</span>

<span id="p0889">- 失败：空成功NO&#95;NEW&#95;DATA；登录/cookie→SESSION&#95;EXPIRED，403/429→RISK&#95;WARNING，封禁/不可用→BLOCKED，其余COLLECT&#95;ERROR；委托未先验证方法，异常message=str(exc)。没有本层重试/缓存fallback。</span>

<span id="p0890">- 状态/建议：A/B相同、默认False。health只构造backend就SUCCESS并称公开无需cookie，不能证明在线可用。本次未实测。保留现有桥接但建议修正health语义、unknown与0区分、comments容器和异常脱敏；不得把docstring“待补全”当真实方法不存在。</span>

#### <span id="p0891">S10 KuaishouAdapter — kuaishou.py 9–85</span>

<span id="p0892">- 输入/路径：search/detail/comments/creator/author&#95;posts分别委托注入backend的方法；creator实际找author。文件没有平台endpoint、匿名抓取或自建浏览器，构造默认backend=None。</span>

<span id="p0893">- 输出：仅接受backend返回CollectionResult并原样转交，没有该层字段normalize或schema再验证。</span>

<span id="p0894">- 失败：无backend NOT&#95;CONFIGURED，方法缺失NOT&#95;SUPPORTED，异常或返回类型不符PROVIDER&#95;UNAVAILABLE；health兼容healthcheck/health&#95;check。无重试/空数据自动补偿。</span>

<span id="p0895">- 状态/建议：A/B相同、默认False；已注册不等于配置了提供方，本次未见实跑。保留未配置边界，后续只接显式授权provider并验证输出/权限/超时，不能按空实现算已上线快手采集。</span>

#### <span id="p0896">S11 GitHubAdapter — github.py 20–168 github&#95;connector.py 30–75 146–224</span>

<span id="p0897">- 输入/路径：keyword→GET https://api.github.com/search/repositories(q,per&#95;page≤50)，再按配置repo allowlist过滤；owner/name→/repos/{repo}；issues/pulls/releases固定后缀列表每页50；health GET /user。配置环境不允许改生产api&#95;base，代码注入对象仍是另一个边界。Bearer由connector提供，本次不读取值。API version2022-11-28、timeout15秒、读取上限2MiB，无分页/重试。</span>

<span id="p0898">- 输出：id/full&#95;name/number→ID；full&#95;name/name/title→标题、description/body→正文；owner/user.login→作者；created&#95;at/published&#95;at→时间；stars/reactions→likes、open&#95;issues&#95;count/comments→comments、forks→collects、watchers→shares。comments接口实际上返回issues，并同时填items/comments，不是issue评论。</span>

<span id="p0899">- 失败：缺连接NOT&#95;CONFIGURED、repo/endpoint不允许BLOCKED、401/403 SESSION&#95;EXPIRED（403限额也可能误归此类）、其他网络PROVIDER&#95;UNAVAILABLE；404/无效JSON映射COLLECT&#95;ERROR。无items为NO&#95;NEW&#95;DATA。</span>

<span id="p0900">- 状态/建议：A/B适配器相同、默认False/optional；health实际/user请求才可能SUCCESS，但本次未实测。保留只读allowlist，建议修正计数or对合法0的丢失、GitHub语义字段、issues与comments命名、分页和限额错误；读取到上限后没有额外字节明确判超长，需验证截断行为。</span>

#### <span id="p0901">S12 WebRSSAdapter — web&#95;rss.py 9–122 web&#95;discovery.py 160–229</span>

<span id="p0902">- 输入/路径：非空query≤120字、max&#95;results夹至1–20→requests.get固定news.google.com/rss/search，q编码，hl=zh-CN/gl=CN/ceid=CN:zh-Hans；timeout10秒。ElementTree读RSS channel/item；不走上述public&#95;source transport，Requests默认重定向且没有该helper的2MiB上限。</span>

<span id="p0903">- 输出：URL的SHA256前32位→google-news:ID，title/source/published&#95;at/url，content为空，互动量与author&#95;id为None；raw仅provider/source&#95;name/source&#95;keyword。日期parse失败保留原字串。</span>

<span id="p0904">- 失败：HTTP非200、XML缺channel/解析错、网络异常→ok=False再映射PROVIDER&#95;UNAVAILABLE；任一条缺URL整次失败，不默默制造身份；真空集合NO&#95;NEW&#95;DATA。detail NOT&#95;SUPPORTED、health NEED&#95;VERIFY；无重试。</span>

<span id="p0905">- 状态/建议：A/B相同、默认False，手动入口。未实测。保留作为发现索引而非正文，建议统一重定向/大小/总时限边界及日期时区，不把索引发布日证明成原站文章时间。</span>

#### <span id="p0906">S13 PublicHttpAdapter — public&#95;http.py 20–257 B新增135–165</span>

<span id="p0907">- 输入/路径：url或keyword是目标URL→fetch&#95;public&#95;url→BeautifulSoup。detail仅接受http(s)URL；没有搜索引擎请求。canonical仅接受同scheme/host/port且不把深路径折叠成首页。</span>

<span id="p0908">- 输出：canonical URL hash→public-http:ID；title、语义article/main正文优先，其次description/body；正文截16000字符；作者和互动量None；meta/JSON-LD/time日期必须能解析且同日，否则未知/冲突保留raw状态。metadata携来源解析与跳转链。</span>

<span id="p0909">- 失败：无URL NOT&#95;CONFIGURED，正文空PROVIDER&#95;UNAVAILABLE；传输/ValueError→PROVIDER&#95;UNAVAILABLE，其余COLLECT&#95;ERROR；不伪造成功空item、不重试。health有URL仍NEED&#95;VERIFY。</span>

<span id="p0910">- 状态/建议：默认False/人工；B新增fetch&#95;document：进程级锁+AdaptiveRateLimiter、等待后before&#95;fetch重检权限、允许MIME集合、2MiB非空、失败反馈限流。普通search未因此自动变为该document路径。本次未实测。保留原文语义抽取和日期冲突合同，建议对description退化、HTML可见正文/脚本和总时限做fixture验收。</span>

#### <span id="p0911">S14 AtomAdapter — web&#95;atom.py 15–168</span>

<span id="p0912">- 输入/路径：feed&#95;url或keyword→共享public transport→feedparser.parse(bytes)；请求前后都阻断YouTube /feeds/videos.xml。文件虽含YouTube字段解析，当前阻断路线不能被标成YouTube接入。</span>

<span id="p0913">- 输出：entry.id或link hash→atom:ID；title、summary或首content、author、published时间；保留source&#95;published&#95;at/source&#95;updated&#95;at。可解析媒体统计等raw字段，但不等于当前允许来源。互动量经基类缺失为None。</span>

<span id="p0914">- 失败：没URL NOT&#95;CONFIGURED；bozo且无entries/缺稳定身份→PROVIDER&#95;UNAVAILABLE；bozo有entries仍可返回部分数据；空entries NO&#95;NEW&#95;DATA。max&#95;results直接int切片，无本层正数/上限夹取；detail NOT&#95;SUPPORTED、health NEED&#95;VERIFY。无重试。</span>

<span id="p0915">- 状态/建议：A/B相同、默认False/人工，未实测。保留显式来源，建议统一limit验证、记录bozo警告、明确summary HTML清洗及不以updated替代published。</span>

#### <span id="p0916">S15 SitemapAdapter — sitemap.py 17–109</span>

<span id="p0917">- 输入/路径：sitemap&#95;url或keyword→共享public transport→ElementTree；只接受urlset/sitemapindex，提取loc/lastmod，不递归追子sitemap或下载全部正文。</span>

<span id="p0918">- 输出：loc hash→sitemap:ID，title=url=loc、content空、作者/互动未知；lastmod只raw.source&#95;updated&#95;at，publish&#95;datetime空；entry&#95;kind区分sitemap/url。max&#95;results夹1–5000，先解析整份2MiB受限XML后截断。</span>

<span id="p0919">- 失败：无loc跳过；传输/XML/输入类型错PROVIDER&#95;UNAVAILABLE；没有有效loc为NO&#95;NEW&#95;DATA。detail NOT&#95;SUPPORTED，health无输入NOT&#95;CONFIGURED、有输入NEED&#95;VERIFY；无重试。</span>

<span id="p0920">- 状态/建议：A/B相同、默认False/人工，未实测。保留发现而非文章证据身份；loc本次未fetch，后续必须再走公共URL/Permission验证，不可从sitemap宣告原文可达或已授权。</span>

#### <span id="p0921">S16 WechatPublicAdapter — wechat.py 22–238</span>

<span id="p0922">- 输入/路径：识别mp.weixin.qq.com原文URL则detail；普通query→https://weixin.sogou.com/weixin?type=2&amp;query=...&amp;page=...（页正整数、每次1–20）；索引链接仅支持原文或weixin.sogou.com/link可见跳转，用共享public transport，无cookie、无JS挑战求解。</span>

<span id="p0923">- 输出：#js&#95;content正文，#activity-name标题/#js&#95;name作者；原文&#95;&#95;biz/mid/idx/sn或/s/token组成原生ID；ct epoch10/13位→UTC时间，页面publish&#95;time字面仅保留不伪作已解析；read/like/comment/share/views未知None。原始文档与正文均hash，保存图片原生URL和locator。索引摘录/日期只discovery候选，不能冒充正文。</span>

<span id="p0924">- 失败：验证码/频控→NEED&#95;VERIFY并可带partial已得items，无法原文→PROVIDER&#95;UNAVAILABLE；没有索引候选NO&#95;NEW&#95;DATA；不支持链接NOT&#95;SUPPORTED且network&#95;attempted=False。非法page/size在try外抛ValueError。给next&#95;search&#95;url但不自动翻页，无重试；成功有items的new&#95;count仍默认0，消费者不得机械据此判无新增。</span>

<span id="p0925">- 状态/建议：A/B文件相同；A registry惰性加载、B统一导入；默认False，health NEED&#95;VERIFY。本次未实测。保留索引/原文分层、挑战即停；建议补计数一致性及输入错误合同，不绕过验证页。</span>

#### <span id="p0926">S17 LinkedInAdapter — linkedin.py 19–68 B至74</span>

<span id="p0927">- 输入/机制：keyword/content&#95;id/creator&#95;id均只到占位方法，没有endpoint请求或浏览器。原始mapping以post&#95;id、commentary、created&#95;at、impression&#95;count映射ID/正文/时间/浏览量，缺字段None；这是可传入raw的schema能力，不是抓取结果。</span>

<span id="p0928">- 失败/状态：A search/detail/comments/creator均COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA，继承capability&#95;map误以为方法覆盖就是implemented。B均NOT&#95;SUPPORTED、health NOT&#95;CONFIGURED且显式能力表不支持。默认False/planned；A无默认导入，B目录导入仍不构成采集。</span>

<span id="p0929">- 建议/证据：保持待接入，不将API权限说明写成已调用；未实测、没有提供方实现证据。正式接入须现有权限owner与官方许可范围；不以有表名当CRUD/自动运行已实现。</span>

#### <span id="p0930">S18 RedditAdapter — reddit.py 19–62 B至68</span>

<span id="p0931">- 输入/机制：keyword/content&#95;id/comments占位，无公开API实际endpoint。raw字段post&#95;id/selftext/created&#95;utc/permalink/score/num&#95;comments/num&#95;crossposts映射统一数据；RAW&#95;USER&#95;TABLE实际命名reddit&#95;subreddits，应避免解释成个人用户采集。</span>

<span id="p0932">- 失败/状态：A COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA；B NOT&#95;SUPPORTED/NOT&#95;CONFIGURED并纠正capability&#95;map。默认False/planned；A默认包不导入，B统一目录导入。没有重试或数据返回。</span>

<span id="p0933">- 建议/证据：未实测；保留计划条目，后续验证Reddit访问和商业使用授权，避免把“公开API”注释当无条件使用许可。</span>

#### <span id="p0934">S19 YouTubeAdapter — youtube.py 19–69 B至75</span>

<span id="p0935">- 输入/机制：keyword、video&#95;id、channel creator参数只到占位；不存在Data API v3调用。mapping video&#95;id/channel&#95;id/channel&#95;title/title/description/published&#95;at/like&#95;count/comment&#95;count/favorite&#95;count/view&#95;count/tags/default&#95;language，缺值None。</span>

<span id="p0936">- 失败/状态：A COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA；B NOT&#95;SUPPORTED、health NOT&#95;CONFIGURED及不支持能力表。False/planned；无重试。A默认包不导入，B目录导入不启用。</span>

<span id="p0937">- 建议/证据：未实测；保持计划，不因填Key就称上线；Atom共享路线亦阻断YouTube feed，不能当替代接入。正式启用需要API实现、权限与配额验证。</span>

#### <span id="p0938">S20 TikTokAdapter — tiktok.py 19–62 B至68</span>

<span id="p0939">- 输入/机制：keyword/content&#95;id/comments占位，没有国际版endpoint；不能借抖音实现替代。raw video&#95;id/desc/create&#95;time/digg&#95;count/comment&#95;count/share&#95;count/collect&#95;count/play&#95;count映射ID/正文/时间/互动，未定义抓取来源。</span>

<span id="p0940">- 失败/状态：A COLLECT&#95;ERROR/health NO&#95;NEW&#95;DATA；B NOT&#95;SUPPORTED/NOT&#95;CONFIGURED和明确能力表。False/planned、A默认未导入、B目录导入；无重试。</span>

<span id="p0941">- 建议/证据：未实测；保留未接入状态，接入时单独定义国际平台授权范围和原生ID，不复用抖音会话/计数假设。</span>

#### <span id="p0942">S21 ChannelsAdapter — channels.py 20–64 B至70</span>

<span id="p0943">- 输入/机制：keyword/object&#95;id/comments只到占位，无视频号网络抓取或browser机制。raw object&#95;id/desc/create&#95;time/view&#95;count/location等可做字段映射；文件“无公开API”是产品注释，本章节未在线验证当下平台API政策。</span>

<span id="p0944">- 失败/状态：A COLLECT&#95;ERROR、health NO&#95;NEW&#95;DATA；B NOT&#95;SUPPORTED/NOT&#95;CONFIGURED、能力表明确未支持。默认False/planned，A包未默认导入，B统一导入仍无采集。</span>

<span id="p0945">- 建议/证据：未实测。保留未实现边界，不以字段/schema、微信公众号原文或另一平台能力替代视频号证据；待合法提供方实现后单独验收。</span>

<span id="p0946"><br /></span>

## <span id="p0947">附录一 Python 完整声明与调用身份账</span>

<span id="p0948">状态释义：产品源import 机制见正文＝存在产品源import，深读范围见机制章节；CONDITIONAL＝条件功能；声明或传递 未见直接产品import＝仅声明或传递，未找到直接产品import；研究清单声明＝研究清单；RETIRED＝退休不可达；未观察＝该版本未发现；当前未验＝没有当前验收证据。</span>

<span id="p0949">本表逐项保留A/B声明与静态状态。版本栏先列历史共享环境或vendor，再列声明；不等当前部署版本。完整SHA256属于研究源码或vendor身份，未取得者明确留空。仅声明项未被提升为产品集成。</span>

<!-- table-03 -->
| <span id="p0950"><strong>包 身份 许可</strong></span> | <span id="p0951"><strong>A/B状态 声明与代表入口</strong></span> | <span id="p0952"><strong>固定研究来源SHA256</strong></span> |
| --- | --- | --- |
| <span id="p0953">aiohttp<br />历史 未见<br />许可未重新核实</span> | <span id="p0954">A 退休不可达XHS分支；B 退休不可达XHS分支<br />aiohttp==3.14.3; aiohttp&gt;=3.9.0<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/system/collector/runtime/xhs/client.py:75</span> | <span id="p0955">精确上游/部署hash未取得</span> |
| <span id="p0956">alembic<br />历史 未见<br />MIT</span> | <span id="p0957">A 产品源import 机制见正文；B 产品源import 机制见正文<br />alembic&gt;=1.19.1<br />迁移工具调用<br />入口 alembic/env.py:7; alembic/versions/e4278c4d1d79&#95;baseline&#95;existing&#95;54&#95;tables&#95;empty&#95;stamp.py:10</span> | <span id="p0958">rel&#95;1&#95;19&#95;1<br />2781f01b40ab31a2d2fdb1441a900f80​b7691d44f11562db622e3079a1ea7285</span><br /><br /><span id="p0959"><a href="https://codeload.github.com/sqlalchemy/alembic/zip/refs/tags/rel_1_19_1">官方固定来源</a></span> |
| <span id="p0960">anthropic<br />历史 未见<br />许可未重新核实</span> | <span id="p0961">A 研究清单声明；B 研究清单声明<br />anthropic==0.76.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p0962">精确上游/部署hash未取得</span> |
| <span id="p0963">anyio<br />历史 4.15.1<br />许可未重新核实</span> | <span id="p0964">A 研究清单声明；B 研究清单声明<br />anyio==4.12.1<br />见条件模型/可选/退休或声明分类</span> | <span id="p0965">精确上游/部署hash未取得</span> |
| <span id="p0966">apscheduler<br />历史 3.11.3<br />许可未重新核实</span> | <span id="p0967">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />APScheduler&gt;=3.10.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p0968">精确上游/部署hash未取得</span> |
| <span id="p0969">arviz<br />历史 0.22.0<br />Apache-2.0</span> | <span id="p0970">A 未观察；B 产品源import 机制见正文<br />arviz==0.22.0<br />MMM条件统计<br />入口 lumenis/shared/reporting/statistics&#95;mmm.py:227</span> | <span id="p0971">v0.22.0<br />f3e0dcbc848a74bd04758d5e20d97fef​51452caf137929ad7b5b038bd092d8ea</span><br /><br /><span id="p0972"><a href="https://codeload.github.com/arviz-devs/arviz/zip/refs/tags/v0.22.0">官方固定来源</a></span> |
| <span id="p0973">beautifulsoup4<br />历史 4.15.0<br />MIT（固定4.15.0源码许可已读；部署闭包未核）</span> | <span id="p0974">A 产品源import 机制见正文；B 产品源import 机制见正文<br />beautifulsoup4&gt;=4.12.0<br />html.parser builder/编码/树删除/文本与CSS转派已深读；最终description长度与降级需验收<br />入口 lumenis/adapters/sogou&#95;search.py:190; lumenis/adapters/sogou&#95;wechat.py:154 等7处</span> | <span id="p0975">4.15.0 official sdist<br />288e3ca7d54b06f2ac191970bc275c19​39cb46d450b255bf6718b04aa37ab4f7</span><br /><br /><span id="p0976"><a href="https://www.crummy.com/software/BeautifulSoup/bs4/download/4.15/beautifulsoup4-4.15.0.tar.gz">官方固定来源</a></span> |
| <span id="p0977">bertopic<br />历史 未见<br />MIT</span> | <span id="p0978">A 未观察；B 产品源import 机制见正文<br />bertopic==0.17.4<br />候选B主题模型<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:1472; lumenis/shared/reporting/statistics&#95;methods.py:1473</span> | <span id="p0979">v0.17.4<br />f8ce0e1ded6dcb7e840f3092024559be​96a8a4fbef4827e18b40ef30a6dce0cc</span><br /><br /><span id="p0980"><a href="https://codeload.github.com/MaartenGr/BERTopic/zip/refs/tags/v0.17.4">官方固定来源</a></span> |
| <span id="p0981">bitsandbytes<br />历史 未见<br />MIT; 固定官方源码许可，非部署闭包</span> | <span id="p0982">A 条件训练版本门禁；B 条件训练版本门禁<br />bitsandbytes==0.50.2 (runtime metadata check)<br />0.50.2量化/Linear4bit/CUDA分派/优化器状态已读；Unsloth补丁与实际native未核</span> | <span id="p0983">精确上游/部署hash未取得<br />许可文件 52412d7bc7ce4157ea628bbaacb8829e​0a9cb3c58f57f99176126bc8cf2bfc85</span><br /><br /><span id="p0984"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/LICENSE">固定许可来源</a></span> |
| <span id="p0985">browser-harness<br />历史 未见<br />许可未重新核实</span> | <span id="p0986">A 研究清单声明；B 研究清单声明<br />browser-harness==0.1.13<br />见条件模型/可选/退休或声明分类</span> | <span id="p0987">精确上游/部署hash未取得</span> |
| <span id="p0988">browser-use<br />历史 未见<br />许可未重新核实</span> | <span id="p0989">A 研究清单声明；B 研究清单声明<br />browser-use==0.13.10<br />见条件模型/可选/退休或声明分类</span> | <span id="p0990">精确上游/部署hash未取得</span> |
| <span id="p0991">browser-use-sdk<br />历史 未见<br />许可未重新核实</span> | <span id="p0992">A 研究清单声明；B 研究清单声明<br />browser-use-sdk==3.4.2<br />见条件模型/可选/退休或声明分类</span> | <span id="p0993">精确上游/部署hash未取得</span> |
| <span id="p0994">bubus<br />历史 未见<br />许可未重新核实</span> | <span id="p0995">A 研究清单声明；B 研究清单声明<br />bubus==1.5.6<br />见条件模型/可选/退休或声明分类</span> | <span id="p0996">精确上游/部署hash未取得</span> |
| <span id="p0997">cdp-use<br />历史 未见<br />许可未重新核实</span> | <span id="p0998">A 研究清单声明；B 研究清单声明<br />cdp-use==1.4.5<br />见条件模型/可选/退休或声明分类</span> | <span id="p0999">精确上游/部署hash未取得</span> |
| <span id="p1000">click<br />历史 8.5.0<br />许可未重新核实</span> | <span id="p1001">A 研究清单声明；B 研究清单声明<br />click==8.3.3<br />见条件模型/可选/退休或声明分类</span> | <span id="p1002">精确上游/部署hash未取得</span> |
| <span id="p1003">cloudpickle<br />历史 3.1.2<br />许可未重新核实</span> | <span id="p1004">A 研究清单声明；B 研究清单声明<br />cloudpickle==3.1.2<br />见条件模型/可选/退休或声明分类</span> | <span id="p1005">精确上游/部署hash未取得</span> |
| <span id="p1006">colorama<br />历史 未见 / vendor 0.4.6<br />BSD-3-Clause风格; 仓库vendor许可证已读</span> | <span id="p1007">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />colorama&gt;=0.4.6<br />见条件模型/可选/退休或声明分类</span> | <span id="p1008">vendor METADATA<br />7baed29eb50c3b29bdb33ff84e3177bf​1bc05784f7685ecdcaa4471c7dd810cc</span> |
| <span id="p1009">cryptography<br />历史 50.0.2<br />Apache-2.0 OR BSD-3-Clause + native notices</span> | <span id="p1010">A 产品源import 机制见正文；B 产品源import 机制见正文<br />cryptography==50.0.2<br />训练回执签名<br />入口 lumenis/system/security/training&#95;receipts.py:18; lumenis/system/security/training&#95;receipts.py:19 等3处</span> | <span id="p1011">50.0.2<br />5f44d10eac72a312fd6d09e6dc2e855b​4268e3a835db9cec8dda286f2faf81b6</span><br /><br /><span id="p1012"><a href="https://codeload.github.com/pyca/cryptography/zip/refs/tags/50.0.2">官方固定来源</a></span> |
| <span id="p1013">datasets<br />历史 未见<br />许可未重新核实</span> | <span id="p1014">A 条件模型训练链；B 条件模型训练链<br /><br />普通八包门未固定；checkpoint14包版本字典及策略摘要覆盖；实际明文版本/内核仍待核<br />入口 lumenis/system/ai&#95;gateway/owned&#95;training.py:528</span> | <span id="p1015">精确上游/部署hash未取得</span> |
| <span id="p1016">duckdb<br />历史 未见<br />MIT（Python/core固定LICENSE已读；native闭包未核）</span> | <span id="p1017">A 产品源import 机制见正文；B 产品源import 机制见正文<br />duckdb==1.5.5<br />绑定/FetchMany/Parquet扫描解码部分已深读；去重累计总内存与取消待验<br />入口 lumenis/system/collector/adapters/overture&#95;places.py:227</span> | <span id="p1018">1.5.5 / Python b236c819 / core d8cdaa33<br />固定许可源文件 075c33400ffcb0c586dd106a029d3e73​3e9da3693f8fcb9cebfc651c8a2f14e3<br />非归档或部署hash</span><br /><br /><span id="p1019"><a href="https://github.com/duckdb/duckdb-python/tree/b236c8194ed14c7a7c685e0534dde501cc855b3a">官方固定来源</a></span> |
| <span id="p1020">feedparser<br />历史 6.0.14<br />BSD-2-Clause（固定源码LICENSE已读；文档条款另列）</span> | <span id="p1021">A 产品源import 机制见正文；B 产品源import 机制见正文<br />feedparser&gt;=6.0.11<br />默认关闭Atom；字节输入/严格→宽松解析/bozo/相对URL/净化已读，非当前运行证明<br />入口 lumenis/system/collector/adapters/web&#95;atom.py:9</span> | <span id="p1022">v6.0.14<br />固定许可源文件 9f5e92783fd9beb2a9de76acda32a8f9​6ee8552a2b566e3923f037f0d754222a<br />非归档或部署hash</span><br /><br /><span id="p1023"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/LICENSE">官方固定来源</a></span> |
| <span id="p1024">flask<br />历史 3.1.3<br />BSD-3-Clause</span> | <span id="p1025">A 产品源import 机制见正文；B 产品源import 机制见正文<br />Flask&gt;=2.0.0<br />应用路由运行链<br />入口 account/api.py:13; account/api.py:8 等116处</span> | <span id="p1026">3.1.3<br />4c8bfa9d33ac64436875f3f7d213b4fd​3bbd855e0a4c4e4afaf7acc51f6b64ab</span><br /><br /><span id="p1027"><a href="https://codeload.github.com/pallets/flask/zip/refs/tags/3.1.3">官方固定来源</a></span> |
| <span id="p1028">flask-cors<br />历史 6.0.5<br />许可未重新核实</span> | <span id="p1029">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />Flask-CORS&gt;=3.0.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1030">精确上游/部署hash未取得</span> |
| <span id="p1031">flask-limiter<br />历史 4.1.1<br />许可未重新核实</span> | <span id="p1032">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />Flask-Limiter&gt;=3.5.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1033">精确上游/部署hash未取得</span> |
| <span id="p1034">google-api-core<br />历史 未见<br />许可未重新核实</span> | <span id="p1035">A 研究清单声明；B 研究清单声明<br />google-api-core==2.29.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1036">精确上游/部署hash未取得</span> |
| <span id="p1037">google-api-python-client<br />历史 未见<br />许可未重新核实</span> | <span id="p1038">A 研究清单声明；B 研究清单声明<br />google-api-python-client==2.188.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1039">精确上游/部署hash未取得</span> |
| <span id="p1040">google-auth<br />历史 未见<br />许可未重新核实</span> | <span id="p1041">A 研究清单声明；B 研究清单声明<br />google-auth==2.48.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1042">精确上游/部署hash未取得</span> |
| <span id="p1043">google-auth-oauthlib<br />历史 未见<br />许可未重新核实</span> | <span id="p1044">A 研究清单声明；B 研究清单声明<br />google-auth-oauthlib==1.2.4<br />见条件模型/可选/退休或声明分类</span> | <span id="p1045">精确上游/部署hash未取得</span> |
| <span id="p1046">google-genai<br />历史 未见<br />许可未重新核实</span> | <span id="p1047">A 研究清单声明；B 研究清单声明<br />google-genai==1.65.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1048">精确上游/部署hash未取得</span> |
| <span id="p1049">groq<br />历史 未见<br />许可未重新核实</span> | <span id="p1050">A 研究清单声明；B 研究清单声明<br />groq==1.0.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1051">精确上游/部署hash未取得</span> |
| <span id="p1052">hdbscan<br />历史 未见<br />许可未重新核实</span> | <span id="p1053">A 未观察；B 声明或传递 未见直接产品import<br />hdbscan==0.8.44<br />见条件模型/可选/退休或声明分类</span> | <span id="p1054">精确上游/部署hash未取得</span> |
| <span id="p1055">httpx<br />历史 0.28.1<br />BSD-3-Clause</span> | <span id="p1056">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />httpx==0.28.1; httpx&gt;=0.24.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1057">0.28.1<br />bb823b6e62db46a89f7351df68ee9474​1c4a3afd42f51b294dcd48742be344f1</span><br /><br /><span id="p1058"><a href="https://codeload.github.com/encode/httpx/zip/refs/tags/0.28.1">官方固定来源</a></span> |
| <span id="p1059">inquirerpy<br />历史 未见<br />许可未重新核实</span> | <span id="p1060">A 研究清单声明；B 研究清单声明<br />InquirerPy==0.3.4<br />见条件模型/可选/退休或声明分类</span> | <span id="p1061">精确上游/部署hash未取得</span> |
| <span id="p1062">jsonschema<br />历史 4.26.0<br />MIT</span> | <span id="p1063">A 未观察；B 产品源import 机制见正文<br />jsonschema&gt;=4.23,&lt;5<br />MCP条件校验<br />入口 mcp&#95;discovery.py:240</span> | <span id="p1064">v4.26.0<br />8b896478e19bb15e5d2d867ea0bcb101​b8b282686706fab075d130a8b4190c2a</span><br /><br /><span id="p1065"><a href="https://codeload.github.com/python-jsonschema/jsonschema/zip/refs/tags/v4.26.0">官方固定来源</a></span> |
| <span id="p1066">llvmlite<br />历史 未见<br />许可未重新核实</span> | <span id="p1067">A 未观察；B 声明或传递 未见直接产品import<br />llvmlite==0.50.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1068">精确上游/部署hash未取得</span> |
| <span id="p1069">lxml<br />历史 6.1.3<br />许可未重新核实</span> | <span id="p1070">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />lxml&gt;=4.9.0<br />见条件模型/可选/退休或声明分类<br />文档转换底层；无直接产品import不代表未用</span> | <span id="p1071">精确上游/部署hash未取得</span> |
| <span id="p1072">markdownify<br />历史 1.2.3<br />许可未重新核实</span> | <span id="p1073">A 研究清单声明；B 研究清单声明<br />markdownify==1.2.2<br />见条件模型/可选/退休或声明分类<br />文档转换底层；无直接产品import不代表未用</span> | <span id="p1074">精确上游/部署hash未取得</span> |
| <span id="p1075">markitdown<br />历史 0.1.8<br />MIT</span> | <span id="p1076">A 产品源import 机制见正文；B 产品源import 机制见正文<br />markitdown&#91;pptx&#93;==0.1.8<br />文档格式条件调用<br />入口 lumenis/importer/parser.py:90</span> | <span id="p1077">v0.1.8<br />681186bab521dc903892990f1f152de2​edd56610001cee4559ec44fe0a5812cf</span><br /><br /><span id="p1078"><a href="https://codeload.github.com/microsoft/markitdown/zip/refs/tags/v0.1.8">官方固定来源</a></span> |
| <span id="p1079">mcp<br />历史 未见<br />许可未重新核实</span> | <span id="p1080">A 研究清单声明；B 研究清单声明<br />mcp==2.1.1<br />见条件模型/可选/退休或声明分类</span> | <span id="p1081">精确上游/部署hash未取得</span> |
| <span id="p1082">networkx<br />历史 3.5<br />BSD-3-Clause</span> | <span id="p1083">A 未观察；B 产品源import 机制见正文<br />networkx==3.5<br />候选B图分析<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:27</span> | <span id="p1084">networkx-3.5<br />8a4796a757efeaedc1b285c0204a208b​a67962e15a7b001c863f9312ddf4df1d</span><br /><br /><span id="p1085"><a href="https://codeload.github.com/networkx/networkx/zip/refs/tags/networkx-3.5">官方固定来源</a></span> |
| <span id="p1086">numba<br />历史 未见<br />许可未重新核实</span> | <span id="p1087">A 未观察；B 声明或传递 未见直接产品import<br />numba==0.68.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1088">精确上游/部署hash未取得</span> |
| <span id="p1089">numpy<br />历史 2.5.4<br />BSD-3-Clause + bundled notices</span> | <span id="p1090">A 产品源import 机制见正文；B 产品源import 机制见正文<br /><br />数值链<br />入口 lumenis/shared/content&#95;creation/reference&#95;analysis.py:154; lumenis/shared/reporting/statistics&#95;methods.py:1131 等22处</span> | <span id="p1091">v2.5.4<br />7206f888610d48459be531ca4701a875​41023a6db8932cbaf6ba689022f57e1c</span><br /><br /><span id="p1092"><a href="https://codeload.github.com/numpy/numpy/zip/refs/tags/v2.5.4">官方固定来源</a></span> |
| <span id="p1093">ollama<br />历史 未见<br />许可未重新核实</span> | <span id="p1094">A 研究清单声明；B 研究清单声明<br />ollama==0.6.1<br />见条件模型/可选/退休或声明分类</span> | <span id="p1095">精确上游/部署hash未取得</span> |
| <span id="p1096">openai<br />历史 未见<br />许可未重新核实</span> | <span id="p1097">A 研究清单声明；B 研究清单声明<br />openai==2.26.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1098">精确上游/部署hash未取得</span> |
| <span id="p1099">openai-whisper<br />历史 未见<br />MIT</span> | <span id="p1100">A 产品源import 机制见正文；B 产品源import 机制见正文<br /><br />固定离线ASR条件调用<br />入口 lumenis/system/ai&#95;gateway/owned&#95;speech.py:366; lumenis/system/ai&#95;gateway/owned&#95;speech.py:424</span> | <span id="p1101">v20250625<br />6f71c98e3d92bf9e1553dd1bad41456a​73af4f291a1d03cf22a5161215d63c0e</span><br /><br /><span id="p1102"><a href="https://codeload.github.com/openai/whisper/zip/refs/tags/v20250625">官方固定来源</a></span> |
| <span id="p1103">openpyxl<br />历史 3.1.5<br />MIT; 本地受信工具运行时3.1.5许可已读，非产品部署证明</span> | <span id="p1104">A 产品源import 机制见正文；B 产品源import 机制见正文<br />openpyxl&gt;=3.0.0; openpyxl&gt;=3.1.5<br />XLSX解析与导出<br />入口 app.py:4343; app.py:4491 等6处</span> | <span id="p1105">精确上游/部署hash未取得</span> |
| <span id="p1106">ortools<br />历史 未见<br />Apache-2.0 + bundled notices</span> | <span id="p1107">A 未观察；B 产品源import 机制见正文<br />ortools==9.15.6755<br />候选B排程<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:1900; lumenis/shared/reporting/statistics&#95;methods.py:1901</span> | <span id="p1108">v9.15<br />920d8266b30a7a8f8572a5dc663fdf8d​2701792101dd95f09e72397c16e12858</span><br /><br /><span id="p1109"><a href="https://codeload.github.com/google/or-tools/zip/refs/tags/v9.15">官方固定来源</a></span> |
| <span id="p1110">pandas<br />历史 3.0.6<br />BSD-3-Clause + bundled notices</span> | <span id="p1111">A 产品源import 机制见正文；B 产品源import 机制见正文<br />pandas&gt;=1.3.0<br />XLSX ImportError备用及传递<br />入口 lumenis/importer/parser.py:288; lumenis/importer/parser.py:321</span> | <span id="p1112">v3.0.6<br />fe57fccfd2ebebdd5ba70931fbbe4fd3​d0c80301d17e079c64e904feb8f14602</span><br /><br /><span id="p1113"><a href="https://codeload.github.com/pandas-dev/pandas/zip/refs/tags/v3.0.6">官方固定来源</a></span> |
| <span id="p1114">pdfplumber<br />历史 0.11.10<br />MIT</span> | <span id="p1115">A 产品源import 机制见正文；B 产品源import 机制见正文<br />pdfplumber==0.11.10<br />PDF解析<br />入口 lumenis/importer/parser.py:161; lumenis/importer/parser.py:194</span> | <span id="p1116">v0.11.10<br />1eaf6488f6df36e5817e9d95872b9b22​b801bb847b768cfc315f77b170b1564a</span><br /><br /><span id="p1117"><a href="https://codeload.github.com/jsvine/pdfplumber/zip/refs/tags/v0.11.10">官方固定来源</a></span> |
| <span id="p1118">peft<br />历史 未见<br />许可未重新核实</span> | <span id="p1119">A 条件模型训练链；B 条件模型训练链<br /><br />普通八包门未固定；checkpoint14包版本字典及策略摘要覆盖；实际明文版本/内核仍待核<br />入口 lumenis/system/ai&#95;gateway/owned&#95;inference.py:159; lumenis/system/ai&#95;gateway/owned&#95;training.py:529 等3处</span> | <span id="p1120">精确上游/部署hash未取得</span> |
| <span id="p1121">pillow<br />历史 13.0.0<br />HPND/PIL + bundled notices</span> | <span id="p1122">A 研究清单声明；B 产品源import 机制见正文<br />pillow==12.3.0<br />媒体图片条件调用<br />入口 lumenis/shared/content&#95;creation/audio&#95;visuals.py:154; lumenis/shared/content&#95;creation/audio&#95;visuals.py:173 等5处</span> | <span id="p1123">13.0.0<br />99aad35fa52284ca1e0213927e2e8caf​012289a8eef11eb6df26cbdbf94e859b</span><br /><br /><span id="p1124"><a href="https://codeload.github.com/python-pillow/Pillow/zip/refs/tags/13.0.0">官方固定来源</a></span> |
| <span id="p1125">playwright<br />历史 未见<br />许可未重新核实</span> | <span id="p1126">A 产品源import 机制见正文；B 产品源import 机制见正文<br />playwright&gt;=1.30.0<br />浏览器worker条件调用<br />入口 ai&#95;browser&#95;runtime.py:1506; ai&#95;browser&#95;runtime.py:1517 等29处</span> | <span id="p1127">精确上游/部署hash未取得</span> |
| <span id="p1128">posthog<br />历史 未见<br />许可未重新核实</span> | <span id="p1129">A 研究清单声明；B 研究清单声明<br />posthog==7.7.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1130">精确上游/部署hash未取得</span> |
| <span id="p1131">psutil<br />历史 7.2.2<br />BSD-3-Clause</span> | <span id="p1132">A 产品源import 机制见正文；B 产品源import 机制见正文<br />psutil==7.2.2; psutil&gt;=5.9.0<br />进程管理<br />入口 ai&#95;task&#95;engine.py:1358; ai&#95;task&#95;engine.py:1376 等16处</span> | <span id="p1133">release-7.2.2<br />79f41465debe0ea73efa44386e17dddb​b4925f2ff0c3c543adf533b2bb5ac7d0</span><br /><br /><span id="p1134"><a href="https://codeload.github.com/giampaolo/psutil/zip/refs/tags/release-7.2.2">官方固定来源</a></span> |
| <span id="p1135">pydantic<br />历史 未见<br />许可未重新核实</span> | <span id="p1136">A 研究清单声明；B 研究清单声明<br />pydantic==2.13.5<br />见条件模型/可选/退休或声明分类</span> | <span id="p1137">精确上游/部署hash未取得</span> |
| <span id="p1138">pydantic-settings<br />历史 未见<br />许可未重新核实</span> | <span id="p1139">A 研究清单声明；B 研究清单声明<br />pydantic-settings==2.15.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1140">精确上游/部署hash未取得</span> |
| <span id="p1141">pymc<br />历史 5.25.1<br />Apache-2.0 + AePPL notices</span> | <span id="p1142">A 未观察；B 产品源import 机制见正文<br />pymc==5.25.1<br />候选B MMM<br />入口 lumenis/shared/reporting/statistics&#95;mmm.py:225</span> | <span id="p1143">v5.25.1<br />e02dedef73ef39a4aa8ddd2038519aa3​146279f954aa260381710ac63e562bc6</span><br /><br /><span id="p1144"><a href="https://codeload.github.com/pymc-devs/pymc/zip/refs/tags/v5.25.1">官方固定来源</a></span> |
| <span id="p1145">pyobjc<br />历史 未见<br />许可未重新核实</span> | <span id="p1146">A 研究清单声明；B 研究清单声明<br />pyobjc==12.1; sys&#95;platform == 'darwin'<br />见条件模型/可选/退休或声明分类</span> | <span id="p1147">精确上游/部署hash未取得</span> |
| <span id="p1148">pyotp<br />历史 未见<br />许可未重新核实</span> | <span id="p1149">A 研究清单声明；B 研究清单声明<br />pyotp==2.9.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1150">精确上游/部署hash未取得</span> |
| <span id="p1151">pypdf<br />历史 未见<br />许可未重新核实</span> | <span id="p1152">A 研究清单声明；B 研究清单声明<br />pypdf==6.16.2<br />见条件模型/可选/退休或声明分类</span> | <span id="p1153">精确上游/部署hash未取得</span> |
| <span id="p1154">pypdf2<br />历史 未见<br />许可未重新核实</span> | <span id="p1155">A 缺包备用 版本未固定；B 缺包备用 版本未固定<br /><br />见条件模型/可选/退休或声明分类<br />入口 lumenis/importer/parser.py:181; lumenis/importer/parser.py:214</span> | <span id="p1156">精确上游/部署hash未取得</span><br /><br /><span id="p1157">固定来源未得</span> |
| <span id="p1158">pytensor<br />历史 2.31.7<br />BSD-3-Clause + bundled notices</span> | <span id="p1159">A 未观察；B 产品源import 机制见正文<br /><br />候选B MMM计算图<br />入口 lumenis/shared/reporting/statistics&#95;mmm.py:226</span> | <span id="p1160">rel-2.31.7<br />57d286d72fb2c8216f35d6ea387045bb​3868ffc09a523a934a71f2888d12b663</span><br /><br /><span id="p1161"><a href="https://codeload.github.com/pymc-devs/pytensor/zip/refs/tags/rel-2.31.7">官方固定来源</a></span> |
| <span id="p1162">pytest<br />历史 9.1.1<br />许可未重新核实</span> | <span id="p1163">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />pytest&gt;=8.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1164">精确上游/部署hash未取得</span> |
| <span id="p1165">python-dateutil<br />历史 2.9.0.post0<br />许可未重新核实</span> | <span id="p1166">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />python-dateutil&gt;=2.8.2<br />见条件模型/可选/退休或声明分类</span> | <span id="p1167">精确上游/部署hash未取得</span> |
| <span id="p1168">python-docx<br />历史 1.2.0<br />MIT</span> | <span id="p1169">A 产品源import 机制见正文；B 产品源import 机制见正文<br />python-docx==1.2.0; python-docx&gt;=0.8.11; python-docx&gt;=1.1.2<br />DOCX解析与导出<br />入口 lumenis/importer/parser.py:207; lumenis/importer/parser.py:208 等11处</span> | <span id="p1170">v1.2.0<br />716de34faf82cb27d3c9748688287620​c7f356c59def24543d41f6ef89d80d07</span><br /><br /><span id="p1171"><a href="https://codeload.github.com/python-openxml/python-docx/zip/refs/tags/v1.2.0">官方固定来源</a></span> |
| <span id="p1172">python-dotenv<br />历史 1.2.4<br />BSD-3-Clause</span> | <span id="p1173">A 产品源import 机制见正文；B 产品源import 机制见正文<br />python-dotenv==1.2.2; python-dotenv&gt;=0.21.0<br />配置加载<br />入口 config.py:16; config.py:17 等3处</span> | <span id="p1174">v1.2.4<br />f869fada871c699a9250f77d29714a42​975ef84b946232ab9d3a333e2fc2097e</span><br /><br /><span id="p1175"><a href="https://codeload.github.com/theskumar/python-dotenv/zip/refs/tags/v1.2.4">官方固定来源</a></span> |
| <span id="p1176">python-pptx<br />历史 1.0.2<br />MIT</span> | <span id="p1177">A 仅开发直接导入；B 仅开发直接导入<br /><br />见条件模型/可选/退休或声明分类<br />文档转换底层；无直接产品import不代表未用</span> | <span id="p1178">v1.0.2<br />4fc305837d4af40a98537fb9c4acbd8d​8eacf57206967443255a221cca7b4a17</span><br /><br /><span id="p1179"><a href="https://codeload.github.com/scanny/python-pptx/zip/refs/tags/v1.0.2">官方固定来源</a></span> |
| <span id="p1180">pyyaml<br />历史 6.0.3<br />MIT</span> | <span id="p1181">A 产品源import 机制见正文；B 产品源import 机制见正文<br />PyYAML&gt;=6.0<br />规则加载<br />入口 data&#95;quality&#95;gate.py:120</span> | <span id="p1182">6.0.3<br />673e7e7de556542598ab38f43e09e714​d028383d8d8a62b3239c4e3541c8227b</span><br /><br /><span id="p1183"><a href="https://codeload.github.com/yaml/pyyaml/zip/refs/tags/6.0.3">官方固定来源</a></span> |
| <span id="p1184">qrcode<br />历史 未见 / vendor 8.2<br />BSD-3-Clause风格; 仓库vendor许可证已读</span> | <span id="p1185">A 产品源import 机制见正文；B 产品源import 机制见正文<br /><br />TOTP SVG调用<br />入口 account/totp.py:104; account/totp.py:105</span> | <span id="p1186">vendor METADATA<br />3a8f1be6da9428b97806292d05e31482​64b9053c22e79894918b670e930afc36</span> |
| <span id="p1187">referencing<br />历史 0.37.0<br />MIT</span> | <span id="p1188">A 未观察；B 产品源import 机制见正文<br /><br />MCP禁止外部引用<br />入口 mcp&#95;discovery.py:241; mcp&#95;discovery.py:242</span> | <span id="p1189">v0.37.0<br />66435aecb03efde47adaba73017f8c96​7c50578da5c79ab4c2c00b0dbbf6808b</span><br /><br /><span id="p1190"><a href="https://codeload.github.com/python-jsonschema/referencing/zip/refs/tags/v0.37.0">官方固定来源</a></span> |
| <span id="p1191">reportlab<br />历史 5.0.1<br />BSD-3-Clause风格（固定发布源码LICENSE已读）</span> | <span id="p1192">A 产品源import 机制见正文；B 产品源import 机制见正文<br />reportlab==4.4.9; reportlab&gt;=3.6.0<br />段落CJK换行/Frame拆页/字体子集/PDF写出已深读；三层导出清理分开<br />入口 lumenis/shared/reporting/routes.py:818; lumenis/shared/reporting/routes.py:819 等11处</span> | <span id="p1193">5.0.1 / c4c83349b7272094f7413f726dcf206dbde7836d<br />固定许可源文件 ef831761646313921375fc2cb888e8ee​af7da213d0b92852c10c42f3a0b4d138<br />非归档或部署hash</span><br /><br /><span id="p1194"><a href="https://github.com/MrBitBucket/reportlab-mirror/tree/c4c83349b7272094f7413f726dcf206dbde7836d">官方固定来源</a></span> |
| <span id="p1195">requests<br />历史 2.34.2<br />Apache-2.0</span> | <span id="p1196">A 产品源import 机制见正文；B 产品源import 机制见正文<br />requests==2.33.0; requests&gt;=2.32.3<br />多种网络适配<br />入口 ad&#95;intelligence/platforms/jiguang.py:178; ad&#95;intelligence/platforms/jiguang.py:273 等36处</span> | <span id="p1197">v2.34.2<br />f552f594e029e3631ed886dc34b42e86​bbaca0858b6d06ec55fe81385f3c8d46</span><br /><br /><span id="p1198"><a href="https://codeload.github.com/psf/requests/zip/refs/tags/v2.34.2">官方固定来源</a></span> |
| <span id="p1199">rich<br />历史 15.0.0<br />许可未重新核实</span> | <span id="p1200">A 研究清单声明；B 研究清单声明<br />rich==14.3.3<br />见条件模型/可选/退休或声明分类</span> | <span id="p1201">精确上游/部署hash未取得</span> |
| <span id="p1202">ruptures<br />历史 1.1.10<br />BSD-2-Clause</span> | <span id="p1203">A 未观察；B 产品源import 机制见正文<br />ruptures==1.1.10<br />候选B变化点<br />入口 trend&#95;api.py:703</span> | <span id="p1204">v1.1.10<br />eaf0faa393da86aeae47cb23a7a7d504​ac9b68af8710b0ae33c4b1de8820bf54</span><br /><br /><span id="p1205"><a href="https://codeload.github.com/deepcharles/ruptures/zip/refs/tags/v1.1.10">官方固定来源</a></span> |
| <span id="p1206">safetensors<br />历史 未见<br />许可未重新核实</span> | <span id="p1207">A 条件模型训练链；B 条件模型训练链<br /><br />普通八包门未固定；checkpoint14包版本字典及策略摘要覆盖；实际明文版本/内核仍待核<br />入口 lumenis/system/ai&#95;gateway/owned&#95;training&#95;checkpoints.py:1417</span> | <span id="p1208">精确上游/部署hash未取得</span> |
| <span id="p1209">schedule<br />历史 1.2.2<br />许可未重新核实</span> | <span id="p1210">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />schedule&gt;=1.2.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1211">精确上游/部署hash未取得</span> |
| <span id="p1212">scikit-learn<br />历史 1.7.2<br />BSD-3-Clause</span> | <span id="p1213">A 未观察；B 产品源import 机制见正文<br />scikit-learn==1.7.2<br />候选B统计主题<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:1012; lumenis/shared/reporting/statistics&#95;methods.py:1480 等7处</span> | <span id="p1214">1.7.2<br />43cb54b3d962e2b34898870e0392aa76​c02ac618e3e61a7634166a914be6d784</span><br /><br /><span id="p1215"><a href="https://codeload.github.com/scikit-learn/scikit-learn/zip/refs/tags/1.7.2">官方固定来源</a></span> |
| <span id="p1216">scipy<br />历史 1.18.1<br />BSD-3-Clause + bundled notices</span> | <span id="p1217">A 未观察；B 产品源import 机制见正文<br />scipy==1.18.1<br />候选B数值优化<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:1132; lumenis/shared/reporting/statistics&#95;methods.py:1133 等13处</span> | <span id="p1218">v1.18.1<br />156a30fe59def660174ddfc486d9642b​55b7e912b4e630c079f19a5abb7a00eb</span><br /><br /><span id="p1219"><a href="https://codeload.github.com/scipy/scipy/zip/refs/tags/v1.18.1">官方固定来源</a></span> |
| <span id="p1220">screeninfo<br />历史 未见<br />许可未重新核实</span> | <span id="p1221">A 研究清单声明；B 研究清单声明<br />screeninfo==0.8.1; platform&#95;system != 'Darwin'<br />见条件模型/可选/退休或声明分类</span> | <span id="p1222">精确上游/部署hash未取得</span> |
| <span id="p1223">sentence-transformers<br />历史 未见<br />许可未重新核实</span> | <span id="p1224">A 未观察；B 声明或传递 未见直接产品import<br />sentence-transformers==6.1.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1225">精确上游/部署hash未取得</span> |
| <span id="p1226">sqlalchemy<br />历史 未见<br />许可未重新核实</span> | <span id="p1227">A 产品源import 机制见正文；B 产品源import 机制见正文<br /><br />迁移工具底层<br />入口 alembic/env.py:4; alembic/env.py:5 等3处</span> | <span id="p1228">精确上游/部署hash未取得</span> |
| <span id="p1229">statsmodels<br />历史 0.14.6<br />BSD-3-Clause</span> | <span id="p1230">A 未观察；B 产品源import 机制见正文<br />statsmodels==0.14.6<br />候选B回归趋势<br />入口 lumenis/shared/reporting/statistics&#95;methods.py:660; trend&#95;api.py:702 等6处</span> | <span id="p1231">v0.14.6<br />b1cfac6f04d2adba486060b7a93e7490​da25ebf14cab2fdf27724552c08b2063</span><br /><br /><span id="p1232"><a href="https://codeload.github.com/statsmodels/statsmodels/zip/refs/tags/v0.14.6">官方固定来源</a></span> |
| <span id="p1233">tenacity<br />历史 未见<br />Apache-2.0</span> | <span id="p1234">A 产品源import 机制见正文；B 产品源import 机制见正文<br />tenacity&gt;=9.1.0<br />可选CDP探测重试<br />入口 collector.py:607</span> | <span id="p1235">9.1.2<br />334266d3c7022076f9a696b40431772c​0bada6ed651962c745e201456339ea95</span><br /><br /><span id="p1236"><a href="https://codeload.github.com/jd/tenacity/zip/refs/tags/9.1.2">官方固定来源</a></span> |
| <span id="p1237">tokenizers<br />历史 未见<br />Apache-2.0; 固定官方源码许可，非部署闭包</span> | <span id="p1238">A 条件训练版本门禁；B 条件训练版本门禁<br />tokenizers==0.22.2 (runtime metadata check)<br />NF4训练栈版本门禁；传递加载/量化/tokenizer/JIT职责待精确上游核验</span> | <span id="p1239">精确上游/部署hash未取得<br />许可文件 c71d239df91726fc519c6eb72d318ec6​5820627232b2f796219e87dcf35d0ab4</span><br /><br /><span id="p1240"><a href="https://raw.githubusercontent.com/huggingface/tokenizers/v0.22.2/LICENSE">固定许可来源</a></span> |
| <span id="p1241">torch<br />历史 未见<br />BSD-style PyTorch/Caffe2 notices; native bundle separate; 固定官方源码许可，非部署闭包</span> | <span id="p1242">A 条件模型训练链；B 条件模型训练链<br />torch==2.11.0+cu128 (NF4运行时版本门禁); torch==2.14.1+cpu<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/system/ai&#95;gateway/owned&#95;inference.py:160; lumenis/system/ai&#95;gateway/owned&#95;speech.py:365 等7处</span> | <span id="p1243">精确上游/部署hash未取得<br />许可文件 bd018feef8825e88181c84eb7e3aa4ea​fb8f08a20d9fd6ef948569610c4a3e43</span><br /><br /><span id="p1244"><a href="https://raw.githubusercontent.com/pytorch/pytorch/v2.11.0/LICENSE">固定许可来源</a></span> |
| <span id="p1245">tqdm<br />历史 未见<br />许可未重新核实</span> | <span id="p1246">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />tqdm&gt;=4.64.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1247">精确上游/部署hash未取得</span> |
| <span id="p1248">transformers<br />历史 未见<br />Apache-2.0; 固定官方源码许可，非部署闭包</span> | <span id="p1249">A 条件模型训练链；B 条件模型训练链<br />transformers==4.56.2 (NF4运行时版本门禁); transformers==5.20.1<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/system/ai&#95;gateway/owned&#95;inference.py:251; lumenis/system/ai&#95;gateway/owned&#95;training.py:530</span> | <span id="p1250">精确上游/部署hash未取得<br />许可文件 77fd4710def9ec3c0f6225800e0235f1​5a425abd4a8b03559127fcd782612049</span><br /><br /><span id="p1251"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/LICENSE">固定许可来源</a></span> |
| <span id="p1252">triton<br />历史 未见<br />MIT; 固定官方源码许可，非部署闭包</span> | <span id="p1253">A 条件训练版本门禁；B 条件训练版本门禁<br />triton==3.6.0 (runtime metadata check)<br />NF4训练栈版本门禁；传递加载/量化/tokenizer/JIT职责待精确上游核验</span> | <span id="p1254">精确上游/部署hash未取得<br />许可文件 92640fb97222fd0a698ff28ce0c3782c​172623f8d6c609b557636a80f28fb946</span><br /><br /><span id="p1255"><a href="https://raw.githubusercontent.com/triton-lang/triton/v3.6.0/LICENSE">固定许可来源</a></span> |
| <span id="p1256">trl<br />历史 未见<br />Apache-2.0; 固定官方源码许可，非部署闭包</span> | <span id="p1257">A 条件模型训练链；B 条件模型训练链<br />trl==0.22.2 (NF4运行时版本门禁)<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/system/ai&#95;gateway/owned&#95;training.py:531</span> | <span id="p1258">精确上游/部署hash未取得<br />许可文件 1d90ecbf7bb80ff27ef67b7785f62148​0b652b82e46c72d8a5730b0db65bf355</span><br /><br /><span id="p1259"><a href="https://raw.githubusercontent.com/huggingface/trl/v0.22.2/LICENSE">固定许可来源</a></span> |
| <span id="p1260">typing-extensions<br />历史 4.16.0<br />许可未重新核实</span> | <span id="p1261">A 研究清单声明；B 研究清单声明<br />typing-extensions==4.15.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1262">精确上游/部署hash未取得</span> |
| <span id="p1263">umap-learn<br />历史 未见<br />许可未重新核实</span> | <span id="p1264">A 未观察；B 声明或传递 未见直接产品import<br />umap-learn==0.5.12<br />见条件模型/可选/退休或声明分类</span> | <span id="p1265">精确上游/部署hash未取得</span> |
| <span id="p1266">unsloth<br />历史 未见<br />Apache-2.0（精确发行页声明；包内文本与部署闭包未核）</span> | <span id="p1267">A 条件模型训练链；B 条件模型训练链<br />unsloth==2026.9.12 (NF4运行时版本门禁)<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/system/ai&#95;gateway/owned&#95;inference.py:158; lumenis/system/ai&#95;gateway/owned&#95;training.py:516</span> | <span id="p1268">精确上游/部署hash未取得</span> |
| <span id="p1269">unsloth-zoo<br />历史 未见<br />LGPL-3.0-or-later（精确发行页声明；包内文本与部署闭包未核）</span> | <span id="p1270">A 条件训练版本门禁；B 条件训练版本门禁<br />unsloth-zoo==2026.9.8 (runtime metadata check)<br />NF4训练栈版本门禁；传递加载/量化/tokenizer/JIT职责待精确上游核验</span> | <span id="p1271">精确上游/部署hash未取得</span> |
| <span id="p1272">uuid7<br />历史 未见<br />许可未重新核实</span> | <span id="p1273">A 研究清单声明；B 研究清单声明<br />uuid7==0.1.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1274">精确上游/部署hash未取得</span> |
| <span id="p1275">waitress<br />历史 未见<br />ZPL-2.1</span> | <span id="p1276">A WSGI条件启用；B WSGI条件启用<br />waitress&gt;=2.1.0<br />见条件模型/可选/退休或声明分类<br />入口 app.py:8114; app.py:8298</span> | <span id="p1277">v2.1.0<br />0c43410808af2fdfa76b900f3f59e542​4091faa9b3d69e28c479b72505d50f99</span><br /><br /><span id="p1278"><a href="https://codeload.github.com/Pylons/waitress/zip/refs/tags/v2.1.0">官方固定来源</a></span> |
| <span id="p1279">websocket-client<br />历史 1.9.2<br />Apache-2.0</span> | <span id="p1280">A 产品源import 机制见正文；B 产品源import 机制见正文<br />websocket-client&gt;=1.6.0<br />CDP与浏览器链<br />入口 browser&#95;surface.py:40; cdp&#95;helper.py:947 等6处</span> | <span id="p1281">v1.9.2<br />be457b2968ed0895ba55d53c3915039a​0df2d5f66b168bd707833b758ba733be</span><br /><br /><span id="p1282"><a href="https://codeload.github.com/websocket-client/websocket-client/zip/refs/tags/v1.9.2">官方固定来源</a></span> |
| <span id="p1283">werkzeug<br />历史 3.1.9<br />BSD-3-Clause</span> | <span id="p1284">A 产品源import 机制见正文；B 产品源import 机制见正文<br />Werkzeug&gt;=2.0.0<br />Flask HTTP底层<br />入口 app.py:1169; app.py:1173 等7处</span> | <span id="p1285">3.1.9<br />5671240fb9cad3d0644eeaadc5f42e55​1cf0d905cfdd13657acf4ac48ef7d9f5</span><br /><br /><span id="p1286"><a href="https://codeload.github.com/pallets/werkzeug/zip/refs/tags/3.1.9">官方固定来源</a></span> |
| <span id="p1287">xlrd<br />历史 2.0.2<br />BSD-style two retained licenses</span> | <span id="p1288">A 产品源import 机制见正文；B 产品源import 机制见正文<br />xlrd==2.0.2<br />旧XLS解析<br />入口 lumenis/importer/parser.py:382; lumenis/importer/parser.py:417</span> | <span id="p1289">2.0.2<br />476da00efde77eb80226bb7a3d8c6dcf​26424a0d921676fcd2f0267049aa8154</span><br /><br /><span id="p1290"><a href="https://codeload.github.com/python-excel/xlrd/zip/refs/tags/2.0.2">官方固定来源</a></span> |
| <span id="p1291">xlsxwriter<br />历史 3.2.9<br />许可未重新核实</span> | <span id="p1292">A 声明或传递 未见直接产品import；B 声明或传递 未见直接产品import<br />xlsxwriter&gt;=3.0.0<br />见条件模型/可选/退休或声明分类</span> | <span id="p1293">精确上游/部署hash未取得</span> |
| <span id="p1294">yyds-logger<br />历史 未见<br />许可未重新核实</span> | <span id="p1295">A 可选日志 标准库回退；B 可选日志 标准库回退<br />yyds-logger&gt;=0.8.0<br />见条件模型/可选/退休或声明分类<br />入口 lumenis/unified&#95;logger.py:30; lumenis/unified&#95;logger.py:46</span> | <span id="p1296">精确上游/部署hash未取得</span> |

<span id="p1297"><br /></span>

## <span id="p1298">附录二 npm 与 Dart 全锁实例账</span>

<span id="p1299">锁代号R为根package-lock.json，W为website/package-lock.json，D为app/pubspec.lock。逐行对应锁实例，完整归档SHA256用于复核。名称链接指向本轮成功取得并验证锁hash的官方归档；SDK占位无归档。相同名称/版本在不同锁出现仍保留。用途栏与库能力不能替代当前平台实际安装和运行证明。</span>

### <span id="p1300">npm 锁实例</span>

<!-- table-04 -->
| <span id="p1301"><strong>包与锁</strong></span> | <span id="p1302"><strong>用途与许可证声明</strong></span> | <span id="p1303"><strong>官方归档 SHA256</strong></span> |
| --- | --- | --- |
| <span id="p1304"><a href="https://registry.npmjs.org/fsevents/-/fsevents-2.3.2.tgz">fsevents 2.3.2</a> R</span> | <span id="p1305">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1306">e17ade950c193fe09adfc7915fe29ac2​6166c8782d00e7c3879e7e9de02c5428</span> |
| <span id="p1307"><a href="https://registry.npmjs.org/playwright/-/playwright-1.62.1.tgz">playwright 1.62.1</a> R</span> | <span id="p1308">浏览器工具 / direct<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1309">1982556a882b246ccb7c16337fab5e4e​790292b69f835a2db1011dddc440ed98</span> |
| <span id="p1310"><a href="https://registry.npmjs.org/playwright-core/-/playwright-core-1.62.1.tgz">playwright-core 1.62.1</a> R</span> | <span id="p1311">浏览器工具 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1312">954be1e183d0ddb9748fe0d2d08b0b66​a9210c74dd75c397aeb70303b9f08a00</span> |
| <span id="p1313"><a href="https://registry.npmjs.org/@astrojs/compiler-binding/-/compiler-binding-0.4.1.tgz">@astrojs/compiler-binding 0.4.1</a> W</span> | <span id="p1314">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1315">391e7146dc91a6cf70f63e5642babc50​4a71d619d0b97680c7716af9e0de677e</span> |
| <span id="p1316"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-android-arm64/-/compiler-binding-android-arm64-0.4.1.tgz">@astrojs/compiler-binding-android-arm64 0.4.1</a> W</span> | <span id="p1317">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1318">64f58955535e13fba4a131c252007a0b​3ddd1c2f516a8d2e803d9a5c2434c48b</span> |
| <span id="p1319"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-darwin-arm64/-/compiler-binding-darwin-arm64-0.4.1.tgz">@astrojs/compiler-binding-darwin-arm64 0.4.1</a> W</span> | <span id="p1320">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1321">0a1b0ceb7e65bd051856b23fa081335b​9f863f9c9bec07fcb7c89c1afa690f59</span> |
| <span id="p1322"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-darwin-x64/-/compiler-binding-darwin-x64-0.4.1.tgz">@astrojs/compiler-binding-darwin-x64 0.4.1</a> W</span> | <span id="p1323">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1324">e37cbe9e5c1f3fef2175e74d0888500c​5f852bfc16e1c9dd0a66625df3a002d5</span> |
| <span id="p1325"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-linux-arm64-gnu/-/compiler-binding-linux-arm64-gnu-0.4.1.tgz">@astrojs/compiler-binding-linux-arm64-gnu 0.4.1</a> W</span> | <span id="p1326">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1327">0ee01014d7e39bc63cddcbf28210b68e​13e631d429dbad7a345575fc36494e6a</span> |
| <span id="p1328"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-linux-arm64-musl/-/compiler-binding-linux-arm64-musl-0.4.1.tgz">@astrojs/compiler-binding-linux-arm64-musl 0.4.1</a> W</span> | <span id="p1329">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1330">405c42a19256d232b9f12d01c516575f​b11fd6a517f9e3ad0f4bb67bd903d66c</span> |
| <span id="p1331"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-linux-x64-gnu/-/compiler-binding-linux-x64-gnu-0.4.1.tgz">@astrojs/compiler-binding-linux-x64-gnu 0.4.1</a> W</span> | <span id="p1332">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1333">cca61f86227a6c231a76288475bec0b6​8500f1a7e85bb46b0675b344efcf8694</span> |
| <span id="p1334"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-linux-x64-musl/-/compiler-binding-linux-x64-musl-0.4.1.tgz">@astrojs/compiler-binding-linux-x64-musl 0.4.1</a> W</span> | <span id="p1335">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1336">8690d584ae0c12c4d13616fcd5ab5987​cac30861455f81be7e1cd53959d5990b</span> |
| <span id="p1337"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-wasm32-wasi/-/compiler-binding-wasm32-wasi-0.4.1.tgz">@astrojs/compiler-binding-wasm32-wasi 0.4.1</a> W</span> | <span id="p1338">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1339">bc7c1a9866fdafb44fc1b822c0131afe​fdd2796b7a4ec569625148dae3392d4b</span> |
| <span id="p1340"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-win32-arm64-msvc/-/compiler-binding-win32-arm64-msvc-0.4.1.tgz">@astrojs/compiler-binding-win32-arm64-msvc 0.4.1</a> W</span> | <span id="p1341">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1342">2d2f6a89494ece85fca92b6e28cbd5d7​77e1525f3499e446c356f309187622f3</span> |
| <span id="p1343"><a href="https://registry.npmjs.org/@astrojs/compiler-binding-win32-x64-msvc/-/compiler-binding-win32-x64-msvc-0.4.1.tgz">@astrojs/compiler-binding-win32-x64-msvc 0.4.1</a> W</span> | <span id="p1344">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1345">e7b1ad496ee2ff2b91a9441994585014​22f2c97988411b2a3dd19c41a435ae4d</span> |
| <span id="p1346"><a href="https://registry.npmjs.org/@astrojs/compiler-rs/-/compiler-rs-0.4.1.tgz">@astrojs/compiler-rs 0.4.1</a> W</span> | <span id="p1347">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1348">13cb3750c801889bd9f93db29eeb9bc3​689d0c34309fccf2ef6d547050bf9490</span> |
| <span id="p1349"><a href="https://registry.npmjs.org/@astrojs/internal-helpers/-/internal-helpers-0.11.0.tgz">@astrojs/internal-helpers 0.11.0</a> W</span> | <span id="p1350">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1351">ce698096aeb0cabb6c1588caae841a0a​1e8b638e1637d30fe651610eaec75a63</span> |
| <span id="p1352"><a href="https://registry.npmjs.org/@astrojs/markdown-satteri/-/markdown-satteri-0.4.1.tgz">@astrojs/markdown-satteri 0.4.1</a> W</span> | <span id="p1353">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1354">6b4476c027b3664770ca8e25f4f3ee21​0e622e172c7391bd41f59b6cc60abe8b</span> |
| <span id="p1355"><a href="https://registry.npmjs.org/@astrojs/prism/-/prism-4.0.2.tgz">@astrojs/prism 4.0.2</a> W</span> | <span id="p1356">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1357">cac86f555b2dbdf34126137a20ea7c51​18c1f59174a1420f6e72f3909f6a2606</span> |
| <span id="p1358"><a href="https://registry.npmjs.org/@astrojs/telemetry/-/telemetry-3.3.3.tgz">@astrojs/telemetry 3.3.3</a> W</span> | <span id="p1359">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1360">7249cc7220e4d72db14bfdd9218a9c22​579257dae7708aea4497e4f12131ef63</span> |
| <span id="p1361"><a href="https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.29.7.tgz">@babel/helper-string-parser 7.29.7</a> W</span> | <span id="p1362">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1363">124565ecd300d7187973060ba6b1d1c4​f296e55f0489ddfd6af794f516fed127</span> |
| <span id="p1364"><a href="https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.29.7.tgz">@babel/helper-validator-identifier 7.29.7</a> W</span> | <span id="p1365">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1366">7a31904bc45f1bb232d5e5dd797d1229​6f4a27fb4bf0f6d517827700f997dc1f</span> |
| <span id="p1367"><a href="https://registry.npmjs.org/@babel/parser/-/parser-7.29.9.tgz">@babel/parser 7.29.9</a> W</span> | <span id="p1368">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1369">8f3b9fbc531e0c08e2c329cf1ff57bbe​121e2d10061b65a05614a25b2255cc43</span> |
| <span id="p1370"><a href="https://registry.npmjs.org/@babel/types/-/types-7.29.8.tgz">@babel/types 7.29.8</a> W</span> | <span id="p1371">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1372">514a4ed09355fe1417f03e89c5a5f518​745e2eb75a4069d25b55a3e7298069de</span> |
| <span id="p1373"><a href="https://registry.npmjs.org/@bruits/satteri-darwin-arm64/-/satteri-darwin-arm64-0.10.5.tgz">@bruits/satteri-darwin-arm64 0.10.5</a> W</span> | <span id="p1374">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1375">773cdd88fd5e53f400dee65bd91a4245​70583657126901d6a7f5b861cc318292</span> |
| <span id="p1376"><a href="https://registry.npmjs.org/@bruits/satteri-darwin-x64/-/satteri-darwin-x64-0.10.5.tgz">@bruits/satteri-darwin-x64 0.10.5</a> W</span> | <span id="p1377">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1378">c55ce01fa98b77a2e3699e4025a4ecec​f1487e818461f2c8344c1f7e775a8f4d</span> |
| <span id="p1379"><a href="https://registry.npmjs.org/@bruits/satteri-linux-arm64-gnu/-/satteri-linux-arm64-gnu-0.10.5.tgz">@bruits/satteri-linux-arm64-gnu 0.10.5</a> W</span> | <span id="p1380">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1381">4b8fccc2451f98066f78cc168df1e94d​f62abcd94b1a70691caccdbcd7931851</span> |
| <span id="p1382"><a href="https://registry.npmjs.org/@bruits/satteri-linux-arm64-musl/-/satteri-linux-arm64-musl-0.10.5.tgz">@bruits/satteri-linux-arm64-musl 0.10.5</a> W</span> | <span id="p1383">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1384">315f9a9c7651100448026d16d4156a28​e5aa7c9ed98234a029557e4bb8269891</span> |
| <span id="p1385"><a href="https://registry.npmjs.org/@bruits/satteri-linux-x64-gnu/-/satteri-linux-x64-gnu-0.10.5.tgz">@bruits/satteri-linux-x64-gnu 0.10.5</a> W</span> | <span id="p1386">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1387">c2b733e72cef4850da027a4dfdc06dbf​64fa2f99fb944a40016cb2a7aecb8a1e</span> |
| <span id="p1388"><a href="https://registry.npmjs.org/@bruits/satteri-linux-x64-musl/-/satteri-linux-x64-musl-0.10.5.tgz">@bruits/satteri-linux-x64-musl 0.10.5</a> W</span> | <span id="p1389">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1390">806a15789aa9b96951d30f112a10ad4a​a9e6de8fe2b7ba3a4aa7a004047c3ac1</span> |
| <span id="p1391"><a href="https://registry.npmjs.org/@bruits/satteri-wasm32-wasi/-/satteri-wasm32-wasi-0.10.5.tgz">@bruits/satteri-wasm32-wasi 0.10.5</a> W</span> | <span id="p1392">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1393">ce912c73a05576c670209eaf050c921b​4a37e7963b9ece47f3e1ae8078499f09</span> |
| <span id="p1394"><a href="https://registry.npmjs.org/@emnapi/core/-/core-1.11.1.tgz">@emnapi/core 1.11.1</a> W</span> | <span id="p1395">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1396">caf1d94fa748509b3fa6c91bf051547d​f62bcae204ec521d418759da1f573950</span> |
| <span id="p1397"><a href="https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.11.1.tgz">@emnapi/runtime 1.11.1</a> W</span> | <span id="p1398">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1399">0acb45d7992e5fba729bb1d8f2586af7​e522518aebd9b2859441b387ef890ad8</span> |
| <span id="p1400"><a href="https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.2.tgz">@emnapi/wasi-threads 1.2.2</a> W</span> | <span id="p1401">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1402">bc2f73bba7ec3f0bf52da313ed1e32b7​3e0ba36a300c9226cdc1d21383abcba6</span> |
| <span id="p1403"><a href="https://registry.npmjs.org/@bruits/satteri-win32-arm64-msvc/-/satteri-win32-arm64-msvc-0.10.5.tgz">@bruits/satteri-win32-arm64-msvc 0.10.5</a> W</span> | <span id="p1404">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1405">6c70eaad69aa18d5339007e4ee2de314​cc1313ea9fe55533e87e8923bbe3ffb2</span> |
| <span id="p1406"><a href="https://registry.npmjs.org/@bruits/satteri-win32-x64-msvc/-/satteri-win32-x64-msvc-0.10.5.tgz">@bruits/satteri-win32-x64-msvc 0.10.5</a> W</span> | <span id="p1407">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1408">b93a6a3fac13d0a8e1880845b004a173​bf6d62f9a2f7f6e0fcb9423b48c7eb44</span> |
| <span id="p1409"><a href="https://registry.npmjs.org/@capsizecss/unpack/-/unpack-4.0.1.tgz">@capsizecss/unpack 4.0.1</a> W</span> | <span id="p1410">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1411">923d58c144c9724af03638f2b26a57d4​2eda88dabe81dbf9b8a42a1992b791e3</span> |
| <span id="p1412"><a href="https://registry.npmjs.org/@clack/core/-/core-1.5.1.tgz">@clack/core 1.5.1</a> W</span> | <span id="p1413">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1414">256c7ba43e14da5e3bc5e79870f7e95b​cbd4eb7831f263fd11f5666b44d020dd</span> |
| <span id="p1415"><a href="https://registry.npmjs.org/@clack/prompts/-/prompts-1.8.1.tgz">@clack/prompts 1.8.1</a> W</span> | <span id="p1416">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1417">a4e1e70bf4bd35e82a76a3fc1dd7ab00​81d0a885dd80b81101310fe31c3e2d0b</span> |
| <span id="p1418"><a href="https://registry.npmjs.org/@emnapi/core/-/core-1.11.3.tgz">@emnapi/core 1.11.3</a> W</span> | <span id="p1419">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1420">2f902aa197cf64722e5afddabecf4af9​4f8cab161d06b2f036bc29f2039136de</span> |
| <span id="p1421"><a href="https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.11.3.tgz">@emnapi/runtime 1.11.3</a> W</span> | <span id="p1422">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1423">e6eb8913a08b551436d65f9a5cfbdcc8​006f58e6798226d24e695c25679b5e49</span> |
| <span id="p1424"><a href="https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.3.tgz">@emnapi/wasi-threads 1.2.3</a> W</span> | <span id="p1425">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1426">e1fc19dd8ecfde1313fd6afdf9b41a1a​22c690c59cd6b384a5c7c97f96acde33</span> |
| <span id="p1427"><a href="https://registry.npmjs.org/@esbuild/aix-ppc64/-/aix-ppc64-0.28.2.tgz">@esbuild/aix-ppc64 0.28.2</a> W</span> | <span id="p1428">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1429">df7900ab960d4eb54ac3d9a1fa21a604​416985017cf0398132def352014225eb</span> |
| <span id="p1430"><a href="https://registry.npmjs.org/@esbuild/android-arm/-/android-arm-0.28.2.tgz">@esbuild/android-arm 0.28.2</a> W</span> | <span id="p1431">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1432">1723a8da8ceec6f6900616d00ac068e7​05c0348587400d0ca80ea4daa87a4183</span> |
| <span id="p1433"><a href="https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-0.28.2.tgz">@esbuild/android-arm64 0.28.2</a> W</span> | <span id="p1434">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1435">faf07e1f4ffd327051edaa982cceacff​8a15138d4b7cdaa91064a1f0fe6f0943</span> |
| <span id="p1436"><a href="https://registry.npmjs.org/@esbuild/android-x64/-/android-x64-0.28.2.tgz">@esbuild/android-x64 0.28.2</a> W</span> | <span id="p1437">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1438">2f5c6be83dea93c0fa8a7b46590c9c8d​b229b2463ea35aa4626ef2658b7e657b</span> |
| <span id="p1439"><a href="https://registry.npmjs.org/@esbuild/darwin-arm64/-/darwin-arm64-0.28.2.tgz">@esbuild/darwin-arm64 0.28.2</a> W</span> | <span id="p1440">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1441">1980cde09749094452b20d36ff267585​ccb3f72749c7bc97291cd9996ccf5a2a</span> |
| <span id="p1442"><a href="https://registry.npmjs.org/@esbuild/darwin-x64/-/darwin-x64-0.28.2.tgz">@esbuild/darwin-x64 0.28.2</a> W</span> | <span id="p1443">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1444">abb6a7a895aaf2cc0df36fecc3bf0042​479ffec51a643a056d54e9109f27db55</span> |
| <span id="p1445"><a href="https://registry.npmjs.org/@esbuild/freebsd-arm64/-/freebsd-arm64-0.28.2.tgz">@esbuild/freebsd-arm64 0.28.2</a> W</span> | <span id="p1446">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1447">a3269361bfc571ebf6b8361b7a0cac29​0b23aed8332be81c322d52289ce2cdce</span> |
| <span id="p1448"><a href="https://registry.npmjs.org/@esbuild/freebsd-x64/-/freebsd-x64-0.28.2.tgz">@esbuild/freebsd-x64 0.28.2</a> W</span> | <span id="p1449">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1450">53e57271b5fc7ab39312b906d3ff84d0​633cfd067332f740e4b6f1f46803fb8a</span> |
| <span id="p1451"><a href="https://registry.npmjs.org/@esbuild/linux-arm/-/linux-arm-0.28.2.tgz">@esbuild/linux-arm 0.28.2</a> W</span> | <span id="p1452">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1453">bdf99344430174119a1403803b4400d1​cb93340b6f8fad2433c7cd55841ad327</span> |
| <span id="p1454"><a href="https://registry.npmjs.org/@esbuild/linux-arm64/-/linux-arm64-0.28.2.tgz">@esbuild/linux-arm64 0.28.2</a> W</span> | <span id="p1455">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1456">a96dbfa41d3ef5dbd1ef22b1c10d5187​be9267e86093a870f06402a7ec931596</span> |
| <span id="p1457"><a href="https://registry.npmjs.org/@esbuild/linux-ia32/-/linux-ia32-0.28.2.tgz">@esbuild/linux-ia32 0.28.2</a> W</span> | <span id="p1458">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1459">47540b6a8fce26aac6559630dc232f83​fe20642e87f1f1fab47512f0ea425084</span> |
| <span id="p1460"><a href="https://registry.npmjs.org/@esbuild/linux-loong64/-/linux-loong64-0.28.2.tgz">@esbuild/linux-loong64 0.28.2</a> W</span> | <span id="p1461">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1462">5f043a3f0e6180956d8cf4731b90858f​ec365c42fab4c1fada75085c4a94fdb9</span> |
| <span id="p1463"><a href="https://registry.npmjs.org/@esbuild/linux-mips64el/-/linux-mips64el-0.28.2.tgz">@esbuild/linux-mips64el 0.28.2</a> W</span> | <span id="p1464">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1465">c2a97154b4b7fb29567d56b3f26b1009​7c0582bf7fc224dd361eac8095327696</span> |
| <span id="p1466"><a href="https://registry.npmjs.org/@esbuild/linux-ppc64/-/linux-ppc64-0.28.2.tgz">@esbuild/linux-ppc64 0.28.2</a> W</span> | <span id="p1467">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1468">41f0068aaaf6d444bdb5238430ccbaa7​912ae769127576f90cd4c2adb2f1ca07</span> |
| <span id="p1469"><a href="https://registry.npmjs.org/@esbuild/linux-riscv64/-/linux-riscv64-0.28.2.tgz">@esbuild/linux-riscv64 0.28.2</a> W</span> | <span id="p1470">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1471">1b3108c646b20581440993de33d2cfd8​939aafc1933d62db211ed609da5066c6</span> |
| <span id="p1472"><a href="https://registry.npmjs.org/@esbuild/linux-s390x/-/linux-s390x-0.28.2.tgz">@esbuild/linux-s390x 0.28.2</a> W</span> | <span id="p1473">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1474">fb2faced3739cf64c755d64aee53cbe1​5f50aedaeb7a625ee63d29a8f58d187d</span> |
| <span id="p1475"><a href="https://registry.npmjs.org/@esbuild/linux-x64/-/linux-x64-0.28.2.tgz">@esbuild/linux-x64 0.28.2</a> W</span> | <span id="p1476">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1477">9573bb2233aab0f9ea7647d5cca97261​13cc1768de61d66b17267f4db84488f6</span> |
| <span id="p1478"><a href="https://registry.npmjs.org/@esbuild/netbsd-arm64/-/netbsd-arm64-0.28.2.tgz">@esbuild/netbsd-arm64 0.28.2</a> W</span> | <span id="p1479">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1480">8b0a5553e22db99b73f9620038f5e7bf​06ba4b2509e1bb540d822f64a35d1f4c</span> |
| <span id="p1481"><a href="https://registry.npmjs.org/@esbuild/netbsd-x64/-/netbsd-x64-0.28.2.tgz">@esbuild/netbsd-x64 0.28.2</a> W</span> | <span id="p1482">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1483">caf02fee8a2332d26af62d0a0c53abc3​5a42de5bcb968d9b94986b2c00c94f95</span> |
| <span id="p1484"><a href="https://registry.npmjs.org/@esbuild/openbsd-arm64/-/openbsd-arm64-0.28.2.tgz">@esbuild/openbsd-arm64 0.28.2</a> W</span> | <span id="p1485">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1486">7c03d85f4f182de6e38cd6335263e892​30f7fb72e4a23cd9d73da4357d18c1a0</span> |
| <span id="p1487"><a href="https://registry.npmjs.org/@esbuild/openbsd-x64/-/openbsd-x64-0.28.2.tgz">@esbuild/openbsd-x64 0.28.2</a> W</span> | <span id="p1488">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1489">0dd9cf7fdb29b09cad6d2b191244adcd​165444ec25d12ccbe098067d5a6d2ebf</span> |
| <span id="p1490"><a href="https://registry.npmjs.org/@esbuild/openharmony-arm64/-/openharmony-arm64-0.28.2.tgz">@esbuild/openharmony-arm64 0.28.2</a> W</span> | <span id="p1491">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1492">0f1cb63fd9beb4d6cda70c0976e168cd​d4f1ceb056b918a83607bb41516ab397</span> |
| <span id="p1493"><a href="https://registry.npmjs.org/@esbuild/sunos-x64/-/sunos-x64-0.28.2.tgz">@esbuild/sunos-x64 0.28.2</a> W</span> | <span id="p1494">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1495">86353429e0f040280094dae3073ac1ee​9310545b532e1c34a1a3617e4608b9e4</span> |
| <span id="p1496"><a href="https://registry.npmjs.org/@esbuild/win32-arm64/-/win32-arm64-0.28.2.tgz">@esbuild/win32-arm64 0.28.2</a> W</span> | <span id="p1497">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1498">b3cffeaa165134f7da679c8619266953​afd5f41641a254615a57e757f67c7336</span> |
| <span id="p1499"><a href="https://registry.npmjs.org/@esbuild/win32-ia32/-/win32-ia32-0.28.2.tgz">@esbuild/win32-ia32 0.28.2</a> W</span> | <span id="p1500">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1501">e05a9b0cb0c9c6facfb02222d00064dd​37baf5c1163f6c0eea936cb93f87a011</span> |
| <span id="p1502"><a href="https://registry.npmjs.org/@esbuild/win32-x64/-/win32-x64-0.28.2.tgz">@esbuild/win32-x64 0.28.2</a> W</span> | <span id="p1503">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1504">7286c3611b6f1f4c4d9ec90adcbc4784​07ff0d28ead96567f361d53e67613e19</span> |
| <span id="p1505"><a href="https://registry.npmjs.org/@img/colour/-/colour-1.1.0.tgz">@img/colour 1.1.0</a> W</span> | <span id="p1506">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1507">6c2df3ac33d4b8647191ad8942a579e6​004be00c25846677eab85f04702d85b1</span> |
| <span id="p1508"><a href="https://registry.npmjs.org/@img/sharp-darwin-arm64/-/sharp-darwin-arm64-0.35.4.tgz">@img/sharp-darwin-arm64 0.35.4</a> W</span> | <span id="p1509">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1510">03e524ae990783e8b343b0d32425f158​2216a4f1cd9c140d34c964ed4cf9450a</span> |
| <span id="p1511"><a href="https://registry.npmjs.org/@img/sharp-darwin-x64/-/sharp-darwin-x64-0.35.4.tgz">@img/sharp-darwin-x64 0.35.4</a> W</span> | <span id="p1512">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1513">9b253050dc8b68f6e0750e05c10ce652​a13fbd69a5c6d909af68d0846600f21d</span> |
| <span id="p1514"><a href="https://registry.npmjs.org/@img/sharp-freebsd-wasm32/-/sharp-freebsd-wasm32-0.35.4.tgz">@img/sharp-freebsd-wasm32 0.35.4</a> W</span> | <span id="p1515">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1516">1e3209fcd5889ae7aad9c8e83edd9198​bdf678d8e98edd99d1d5bc48ce4d1b34</span> |
| <span id="p1517"><a href="https://registry.npmjs.org/@img/sharp-libvips-darwin-arm64/-/sharp-libvips-darwin-arm64-1.3.3.tgz">@img/sharp-libvips-darwin-arm64 1.3.3</a> W</span> | <span id="p1518">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1519">81b140db70a2e92420c1ddeb2dacf43d​c70a76c7d55bc1dde118b5914a067b99</span> |
| <span id="p1520"><a href="https://registry.npmjs.org/@img/sharp-libvips-darwin-x64/-/sharp-libvips-darwin-x64-1.3.3.tgz">@img/sharp-libvips-darwin-x64 1.3.3</a> W</span> | <span id="p1521">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1522">23c0a9cec8e8c8a663b10cb56f39b310​fde4efb0ffabb520aa8c00f6d8fb38b4</span> |
| <span id="p1523"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-arm/-/sharp-libvips-linux-arm-1.3.3.tgz">@img/sharp-libvips-linux-arm 1.3.3</a> W</span> | <span id="p1524">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1525">0443175cbaca2f548049da8ef3204007​beef38030799b3d9fb06c56b009b59ef</span> |
| <span id="p1526"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-arm64/-/sharp-libvips-linux-arm64-1.3.3.tgz">@img/sharp-libvips-linux-arm64 1.3.3</a> W</span> | <span id="p1527">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1528">b56f6488e113c385a463fd3be8134b04​3a17114228f544701fc9c040227e4a59</span> |
| <span id="p1529"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-ppc64/-/sharp-libvips-linux-ppc64-1.3.3.tgz">@img/sharp-libvips-linux-ppc64 1.3.3</a> W</span> | <span id="p1530">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1531">866e8a21ea15c79556ea93c0a2870288​8a1a9a8cad1883d6e5f7290b74a7c252</span> |
| <span id="p1532"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-riscv64/-/sharp-libvips-linux-riscv64-1.3.3.tgz">@img/sharp-libvips-linux-riscv64 1.3.3</a> W</span> | <span id="p1533">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1534">f61dea685bcdb3740c3b4b0c83de018d​5073da066684e137de169bd2be3065fb</span> |
| <span id="p1535"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-s390x/-/sharp-libvips-linux-s390x-1.3.3.tgz">@img/sharp-libvips-linux-s390x 1.3.3</a> W</span> | <span id="p1536">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1537">b8d8c75eda81f597c1577c6a31f8640c​9f45d077463af37a0981af0f5a200422</span> |
| <span id="p1538"><a href="https://registry.npmjs.org/@img/sharp-libvips-linux-x64/-/sharp-libvips-linux-x64-1.3.3.tgz">@img/sharp-libvips-linux-x64 1.3.3</a> W</span> | <span id="p1539">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1540">74b6fa0abb2e41a163853a00e2f24718​8df5ec1e25bf62c4c5a041f2042a1f6a</span> |
| <span id="p1541"><a href="https://registry.npmjs.org/@img/sharp-libvips-linuxmusl-arm64/-/sharp-libvips-linuxmusl-arm64-1.3.3.tgz">@img/sharp-libvips-linuxmusl-arm64 1.3.3</a> W</span> | <span id="p1542">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1543">5f00ec306367cc523e641d43fbfbb539​f20519103b075caa1c628810b9fe73a6</span> |
| <span id="p1544"><a href="https://registry.npmjs.org/@img/sharp-libvips-linuxmusl-x64/-/sharp-libvips-linuxmusl-x64-1.3.3.tgz">@img/sharp-libvips-linuxmusl-x64 1.3.3</a> W</span> | <span id="p1545">可选平台构建 / transitive<br />LGPL-3.0-or-later<br />缺独立许可文本</span> | <span id="p1546">4261dcae140dbb569ff4b96a09dbfb1c​75fec728b8ff1f58b00b60e828947333</span> |
| <span id="p1547"><a href="https://registry.npmjs.org/@img/sharp-linux-arm/-/sharp-linux-arm-0.35.4.tgz">@img/sharp-linux-arm 0.35.4</a> W</span> | <span id="p1548">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1549">a61cdc511a63db8ce34791bd1eb9d5b6​b17d0c85f20a8e1b0b8a73c0af0b7af6</span> |
| <span id="p1550"><a href="https://registry.npmjs.org/@img/sharp-linux-arm64/-/sharp-linux-arm64-0.35.4.tgz">@img/sharp-linux-arm64 0.35.4</a> W</span> | <span id="p1551">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1552">556157e2f5de993f0b022d2cce22fd82​48daeb95610c37d5a7cb7cca41d5d467</span> |
| <span id="p1553"><a href="https://registry.npmjs.org/@img/sharp-linux-ppc64/-/sharp-linux-ppc64-0.35.4.tgz">@img/sharp-linux-ppc64 0.35.4</a> W</span> | <span id="p1554">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1555">c1d241e79afba66ca2388d10520457d4​dc5d5c0005df84e3a7f253a5c87dcede</span> |
| <span id="p1556"><a href="https://registry.npmjs.org/@img/sharp-linux-riscv64/-/sharp-linux-riscv64-0.35.4.tgz">@img/sharp-linux-riscv64 0.35.4</a> W</span> | <span id="p1557">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1558">9da242532a2feed3e05c9a8483aeb694​cf50500d0212c4c36feafdfa60ccc071</span> |
| <span id="p1559"><a href="https://registry.npmjs.org/@img/sharp-linux-s390x/-/sharp-linux-s390x-0.35.4.tgz">@img/sharp-linux-s390x 0.35.4</a> W</span> | <span id="p1560">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1561">acc64aa0412f713f0085041f0de930da​4a1fb96cc4daa5718bd7bcfc9eb8891b</span> |
| <span id="p1562"><a href="https://registry.npmjs.org/@img/sharp-linux-x64/-/sharp-linux-x64-0.35.4.tgz">@img/sharp-linux-x64 0.35.4</a> W</span> | <span id="p1563">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1564">9fe2de0bf57643eb603f16d5ed237dce​b1c1229ea76f5094aacab1e99162bf3b</span> |
| <span id="p1565"><a href="https://registry.npmjs.org/@img/sharp-linuxmusl-arm64/-/sharp-linuxmusl-arm64-0.35.4.tgz">@img/sharp-linuxmusl-arm64 0.35.4</a> W</span> | <span id="p1566">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1567">2372869bf1f00317ffb250f983f888de​18e747d37ee52795393caf2fa591ff53</span> |
| <span id="p1568"><a href="https://registry.npmjs.org/@img/sharp-linuxmusl-x64/-/sharp-linuxmusl-x64-0.35.4.tgz">@img/sharp-linuxmusl-x64 0.35.4</a> W</span> | <span id="p1569">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1570">8a15504e5c86d724aed9af846e4d62f3​4c360f846ae6d8fdd6390aa415342c18</span> |
| <span id="p1571"><a href="https://registry.npmjs.org/@img/sharp-wasm32/-/sharp-wasm32-0.35.4.tgz">@img/sharp-wasm32 0.35.4</a> W</span> | <span id="p1572">可选平台构建 / transitive<br />Apache-2.0 AND LGPL-3.0-or-later AND MIT<br />许可文件已保存</span> | <span id="p1573">d9ea28a3dc30c74046eff4e363041c0f​a397308193be45b6c32b717cbf5d8b6b</span> |
| <span id="p1574"><a href="https://registry.npmjs.org/@img/sharp-webcontainers-wasm32/-/sharp-webcontainers-wasm32-0.35.4.tgz">@img/sharp-webcontainers-wasm32 0.35.4</a> W</span> | <span id="p1575">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1576">b73eede74d68f536eddccb8ac994ba45​06587591e0bdd28cd61daa840d0f9a6f</span> |
| <span id="p1577"><a href="https://registry.npmjs.org/@img/sharp-win32-arm64/-/sharp-win32-arm64-0.35.4.tgz">@img/sharp-win32-arm64 0.35.4</a> W</span> | <span id="p1578">可选平台构建 / transitive<br />Apache-2.0 AND LGPL-3.0-or-later<br />许可文件已保存</span> | <span id="p1579">1a8c901a8dffaf4b1ae55fa5757e0518​8c12b16279eeff96b5c40a1ddcaa1d30</span> |
| <span id="p1580"><a href="https://registry.npmjs.org/@img/sharp-win32-ia32/-/sharp-win32-ia32-0.35.4.tgz">@img/sharp-win32-ia32 0.35.4</a> W</span> | <span id="p1581">可选平台构建 / transitive<br />Apache-2.0 AND LGPL-3.0-or-later<br />许可文件已保存</span> | <span id="p1582">f66f80d858292b6e31e574473d3c4225​699521bfed1af5522295587b7d5c98d4</span> |
| <span id="p1583"><a href="https://registry.npmjs.org/@img/sharp-win32-x64/-/sharp-win32-x64-0.35.4.tgz">@img/sharp-win32-x64 0.35.4</a> W</span> | <span id="p1584">可选平台构建 / transitive<br />Apache-2.0 AND LGPL-3.0-or-later<br />许可文件已保存</span> | <span id="p1585">5bae8109aa0c7d115788abc3dd9b241c​aa8d316c838f163a9dadc310dff4008b</span> |
| <span id="p1586"><a href="https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.6.0.tgz">@jridgewell/sourcemap-codec 1.6.0</a> W</span> | <span id="p1587">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1588">f30a35f6af8c347d01b8ff2f8662272f​7d986cf21b916704d86c249a90b97e25</span> |
| <span id="p1589"><a href="https://registry.npmjs.org/@napi-rs/wasm-runtime/-/wasm-runtime-1.2.4.tgz">@napi-rs/wasm-runtime 1.2.4</a> W</span> | <span id="p1590">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1591">e64c2013eba51ad6624ccf94f06c8a57​0c0d80488b7eabf17af2934690ccb887</span> |
| <span id="p1592"><a href="https://registry.npmjs.org/@oslojs/encoding/-/encoding-1.1.0.tgz">@oslojs/encoding 1.1.0</a> W</span> | <span id="p1593">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1594">3bb63f0032de73814387e42b747d2e4b​2b5a5f9a536e4dba87037ce524679a05</span> |
| <span id="p1595"><a href="https://registry.npmjs.org/@oxc-project/types/-/types-0.150.0.tgz">@oxc-project/types 0.150.0</a> W</span> | <span id="p1596">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1597">a05790e81e949ec9483aa013851236c0​2f19a9b503a8ff84783e48a448e33feb</span> |
| <span id="p1598"><a href="https://registry.npmjs.org/@rolldown/binding-android-arm-eabi/-/binding-android-arm-eabi-1.2.9.tgz">@rolldown/binding-android-arm-eabi 1.2.9</a> W</span> | <span id="p1599">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1600">2a7fc7d6ebbe4840fb4c05b846301b1d​49e3032dc2182aac829fe501687439f9</span> |
| <span id="p1601"><a href="https://registry.npmjs.org/@rolldown/binding-android-arm64/-/binding-android-arm64-1.2.9.tgz">@rolldown/binding-android-arm64 1.2.9</a> W</span> | <span id="p1602">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1603">0329058d7bdd75a884dcc2d691c2082e​4ee2731946e375c2f552c2b992384215</span> |
| <span id="p1604"><a href="https://registry.npmjs.org/@rolldown/binding-darwin-arm64/-/binding-darwin-arm64-1.2.9.tgz">@rolldown/binding-darwin-arm64 1.2.9</a> W</span> | <span id="p1605">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1606">7b7da204879507a070d723323439f107​d879cb8e11a4f2e2f0a9d3ee81ffbf80</span> |
| <span id="p1607"><a href="https://registry.npmjs.org/@rolldown/binding-darwin-x64/-/binding-darwin-x64-1.2.9.tgz">@rolldown/binding-darwin-x64 1.2.9</a> W</span> | <span id="p1608">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1609">a37d9166d018006a02a9694d8b0b8adc​6675fd2702553d0ffa6d93b7109dc10a</span> |
| <span id="p1610"><a href="https://registry.npmjs.org/@rolldown/binding-freebsd-x64/-/binding-freebsd-x64-1.2.9.tgz">@rolldown/binding-freebsd-x64 1.2.9</a> W</span> | <span id="p1611">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1612">365cf63d714518bb2ab009b9fdb05c31​48462f5765df838d14f8ef9187056f7c</span> |
| <span id="p1613"><a href="https://registry.npmjs.org/@rolldown/binding-linux-arm-gnueabihf/-/binding-linux-arm-gnueabihf-1.2.9.tgz">@rolldown/binding-linux-arm-gnueabihf 1.2.9</a> W</span> | <span id="p1614">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1615">5a1430961129ccfdccdd8e4c2319fb01​e365d4843e7b2f946a784d84bd149cd8</span> |
| <span id="p1616"><a href="https://registry.npmjs.org/@rolldown/binding-linux-arm64-gnu/-/binding-linux-arm64-gnu-1.2.9.tgz">@rolldown/binding-linux-arm64-gnu 1.2.9</a> W</span> | <span id="p1617">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1618">3c1356d59dea6c214370445893e269c6​c88e2f74f310e8a21487c560ac82b508</span> |
| <span id="p1619"><a href="https://registry.npmjs.org/@rolldown/binding-linux-arm64-musl/-/binding-linux-arm64-musl-1.2.9.tgz">@rolldown/binding-linux-arm64-musl 1.2.9</a> W</span> | <span id="p1620">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1621">e89c3714ecca4c5e4a9e386765d71b3c​e624ca4c796b1709ebe11ae58a301852</span> |
| <span id="p1622"><a href="https://registry.npmjs.org/@rolldown/binding-linux-ppc64-gnu/-/binding-linux-ppc64-gnu-1.2.9.tgz">@rolldown/binding-linux-ppc64-gnu 1.2.9</a> W</span> | <span id="p1623">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1624">aa6bf25391b2d901bb3b73595ccec8f7​9cea1782ca474b2166b36df7a4dd647b</span> |
| <span id="p1625"><a href="https://registry.npmjs.org/@rolldown/binding-linux-s390x-gnu/-/binding-linux-s390x-gnu-1.2.9.tgz">@rolldown/binding-linux-s390x-gnu 1.2.9</a> W</span> | <span id="p1626">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1627">e5c556e73fd01be057ddf6b99121dce6​bacb69cbff4c6f5e827c196a1f6bdb39</span> |
| <span id="p1628"><a href="https://registry.npmjs.org/@rolldown/binding-linux-x64-gnu/-/binding-linux-x64-gnu-1.2.9.tgz">@rolldown/binding-linux-x64-gnu 1.2.9</a> W</span> | <span id="p1629">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1630">cc5912bf3748daf3aa9aa5a60a2b63b6​8d985367d2af72ebb1db65a8c95d6d8d</span> |
| <span id="p1631"><a href="https://registry.npmjs.org/@rolldown/binding-linux-x64-musl/-/binding-linux-x64-musl-1.2.9.tgz">@rolldown/binding-linux-x64-musl 1.2.9</a> W</span> | <span id="p1632">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1633">35dc9646962d891c15ea1c2cb93e160d​1395e174988a1e7d86d9dfe51832c89d</span> |
| <span id="p1634"><a href="https://registry.npmjs.org/@rolldown/binding-openharmony-arm64/-/binding-openharmony-arm64-1.2.9.tgz">@rolldown/binding-openharmony-arm64 1.2.9</a> W</span> | <span id="p1635">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1636">9e335127acd141d3fdbc83158ed39907​2327cc9376f4e753c85a53341ba59cde</span> |
| <span id="p1637"><a href="https://registry.npmjs.org/@rolldown/binding-win32-arm64-msvc/-/binding-win32-arm64-msvc-1.2.9.tgz">@rolldown/binding-win32-arm64-msvc 1.2.9</a> W</span> | <span id="p1638">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1639">c0249bb3cae06c97045294b28cd1bc24​46ea60db02ccc20c7d4bc456cfcdad18</span> |
| <span id="p1640"><a href="https://registry.npmjs.org/@rolldown/binding-win32-x64-msvc/-/binding-win32-x64-msvc-1.2.9.tgz">@rolldown/binding-win32-x64-msvc 1.2.9</a> W</span> | <span id="p1641">可选平台构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1642">eab52dc8846b438bb55727b65883b31d​1716f686d3740f4ce4d18a5690fc1508</span> |
| <span id="p1643"><a href="https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.1.tgz">@rolldown/pluginutils 1.0.1</a> W</span> | <span id="p1644">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1645">13fcb3423d37f95a8e861c172e4b62fd​24f22412be4e942087367242476e3400</span> |
| <span id="p1646"><a href="https://registry.npmjs.org/@shikijs/core/-/core-4.4.3.tgz">@shikijs/core 4.4.3</a> W</span> | <span id="p1647">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1648">0889692e2609eaa85462744cf3d64e5c​3165528cc701913c6bcda9ce7a251103</span> |
| <span id="p1649"><a href="https://registry.npmjs.org/@shikijs/engine-javascript/-/engine-javascript-4.4.3.tgz">@shikijs/engine-javascript 4.4.3</a> W</span> | <span id="p1650">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1651">4e3dea18ad0bab80e4173ec413aa465e​a32499b556a80a276b8f65ecbe45544c</span> |
| <span id="p1652"><a href="https://registry.npmjs.org/@shikijs/engine-oniguruma/-/engine-oniguruma-4.4.3.tgz">@shikijs/engine-oniguruma 4.4.3</a> W</span> | <span id="p1653">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1654">55f01ac5549508bdd970eca18fec1c03​32cc5f875042c39b85eca09e9c2a43e1</span> |
| <span id="p1655"><a href="https://registry.npmjs.org/@shikijs/langs/-/langs-4.4.3.tgz">@shikijs/langs 4.4.3</a> W</span> | <span id="p1656">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1657">230dfb9fa5f55e2b446586c93c4d6866​af959109e31acc923c47c3b6d4f2e672</span> |
| <span id="p1658"><a href="https://registry.npmjs.org/@shikijs/primitive/-/primitive-4.4.3.tgz">@shikijs/primitive 4.4.3</a> W</span> | <span id="p1659">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1660">78234a4b2aa6ea5b2a57469b6e9f4148​1761bcad422c8bd402c4975332cdaa21</span> |
| <span id="p1661"><a href="https://registry.npmjs.org/@shikijs/themes/-/themes-4.4.3.tgz">@shikijs/themes 4.4.3</a> W</span> | <span id="p1662">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1663">a0e7f10d16995903c5e3b4d672b4e022​c545d39007e40daf1165dadb191c1e55</span> |
| <span id="p1664"><a href="https://registry.npmjs.org/@shikijs/types/-/types-4.4.3.tgz">@shikijs/types 4.4.3</a> W</span> | <span id="p1665">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1666">86ab1ecd51fb8ee466cb027202e85510​c2508ea9057e4fa7d256cba4189f7a2d</span> |
| <span id="p1667"><a href="https://registry.npmjs.org/@shikijs/vscode-textmate/-/vscode-textmate-10.0.2.tgz">@shikijs/vscode-textmate 10.0.2</a> W</span> | <span id="p1668">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1669">2164908fc8d7e4b891faa09953cf345f​922ab9359d9c4757e97e2620e6207f34</span> |
| <span id="p1670"><a href="https://registry.npmjs.org/@tybys/wasm-util/-/wasm-util-0.10.4.tgz">@tybys/wasm-util 0.10.4</a> W</span> | <span id="p1671">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1672">c6293ce0ae57dbf718723df204f014f6​e6285cefc2fee51ea65fe8cac5eef0a0</span> |
| <span id="p1673"><a href="https://registry.npmjs.org/@types/estree/-/estree-1.0.9.tgz">@types/estree 1.0.9</a> W</span> | <span id="p1674">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1675">ec8f3c0dfb21497db5a3480c45a6cf6f​9b18d3b337b2ea4d03e3ef2a9c2bb358</span> |
| <span id="p1676"><a href="https://registry.npmjs.org/@types/estree-jsx/-/estree-jsx-1.0.5.tgz">@types/estree-jsx 1.0.5</a> W</span> | <span id="p1677">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1678">51e4a90e34bab73ec7c2ab32d2a0f166​e3a1675559d5e7200575317b7db8883f</span> |
| <span id="p1679"><a href="https://registry.npmjs.org/@types/hast/-/hast-3.0.5.tgz">@types/hast 3.0.5</a> W</span> | <span id="p1680">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1681">a9b9ae07cbef416c00a5f1d7149ca03c​5e20e7f5addb67203b7849ac80f1f761</span> |
| <span id="p1682"><a href="https://registry.npmjs.org/@types/mdast/-/mdast-4.0.4.tgz">@types/mdast 4.0.4</a> W</span> | <span id="p1683">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1684">ca9d3f571a96c57b9412fa9ccc009a35​6990e5334ce2c56587218a2fa2d57ef3</span> |
| <span id="p1685"><a href="https://registry.npmjs.org/@types/nlcst/-/nlcst-2.0.3.tgz">@types/nlcst 2.0.3</a> W</span> | <span id="p1686">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1687">5bb2157f620c7f86e456d14011ea6b1e​63254fa6d9b7744e5aa194d92d5c40e0</span> |
| <span id="p1688"><a href="https://registry.npmjs.org/@types/unist/-/unist-3.0.3.tgz">@types/unist 3.0.3</a> W</span> | <span id="p1689">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1690">b50fd32f739207d1e8c96ef0b0c9dd00​3ef9cb0403c5b4eb71796b87332a2843</span> |
| <span id="p1691"><a href="https://registry.npmjs.org/@ungap/structured-clone/-/structured-clone-1.4.0.tgz">@ungap/structured-clone 1.4.0</a> W</span> | <span id="p1692">网站构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p1693">f481575dc2f23f404e3eec77eb6726bd​f9c7d130f1b43f214291e601acf50996</span> |
| <span id="p1694"><a href="https://registry.npmjs.org/am-i-vibing/-/am-i-vibing-0.4.0.tgz">am-i-vibing 0.4.0</a> W</span> | <span id="p1695">网站构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p1696">5e59f6fd20148e9753923d787b8dc9b6​623a647fcb05cccb8c40af75cfd44f5a</span> |
| <span id="p1697"><a href="https://registry.npmjs.org/anymatch/-/anymatch-3.1.3.tgz">anymatch 3.1.3</a> W</span> | <span id="p1698">网站构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p1699">bb629d6c832b73a127f1623867a2bf2f​161fa0bb185dbecb632a878621b8f78f</span> |
| <span id="p1700"><a href="https://registry.npmjs.org/picomatch/-/picomatch-2.3.2.tgz">picomatch 2.3.2</a> W</span> | <span id="p1701">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1702">4c843ba015bec815ac52116162559ab7​b4b4efbd3b86f7fcf38f3d770decace6</span> |
| <span id="p1703"><a href="https://registry.npmjs.org/argparse/-/argparse-2.0.1.tgz">argparse 2.0.1</a> W</span> | <span id="p1704">网站构建 / transitive<br />Python-2.0<br />许可文件已保存</span> | <span id="p1705">27903847fc8215e6fc5a33e81490f7ba​ba66403f8aade33771b988cca097728c</span> |
| <span id="p1706"><a href="https://registry.npmjs.org/aria-query/-/aria-query-5.3.2.tgz">aria-query 5.3.2</a> W</span> | <span id="p1707">网站构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1708">62691953222d8acef97db2daa0e84ade​dc8eb6b074c33ec02367291a32e4ad37</span> |
| <span id="p1709"><a href="https://registry.npmjs.org/astro/-/astro-7.3.3.tgz">astro 7.3.3</a> W</span> | <span id="p1710">网站构建 / direct<br />MIT<br />许可文件已保存</span> | <span id="p1711">4ee1d2f25ef5137d403226f55a722afe​04324f357577c51802e274d1888577fd</span> |
| <span id="p1712"><a href="https://registry.npmjs.org/axobject-query/-/axobject-query-4.1.0.tgz">axobject-query 4.1.0</a> W</span> | <span id="p1713">网站构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1714">040d97829212e5e9f48fb4069ca38d2d​23b34d4e65b7c7cab2a55ae3546c8d02</span> |
| <span id="p1715"><a href="https://registry.npmjs.org/bail/-/bail-2.0.2.tgz">bail 2.0.2</a> W</span> | <span id="p1716">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1717">11719f7e1f7a31432177dd0cd987e7c9​67a826426d281c39c0025b474056c88b</span> |
| <span id="p1718"><a href="https://registry.npmjs.org/boolbase/-/boolbase-1.0.0.tgz">boolbase 1.0.0</a> W</span> | <span id="p1719">网站构建 / transitive<br />ISC<br />缺独立许可文本</span> | <span id="p1720">69628ff8092c5ff940ea4a0f29da98d5​20615bae138755c9e059033606c6caa8</span> |
| <span id="p1721"><a href="https://registry.npmjs.org/ccount/-/ccount-2.0.1.tgz">ccount 2.0.1</a> W</span> | <span id="p1722">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1723">bdda8b4b3c7c3049bb118a9a01e36380​33473b90c09f58eee1e9f2dda27984ca</span> |
| <span id="p1724"><a href="https://registry.npmjs.org/character-entities-html4/-/character-entities-html4-2.1.0.tgz">character-entities-html4 2.1.0</a> W</span> | <span id="p1725">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1726">a1cdca963945f3fbb4ac4932d4b8e54c​eb66aba5a9bfc7254fb87a1f17cd04e6</span> |
| <span id="p1727"><a href="https://registry.npmjs.org/character-entities-legacy/-/character-entities-legacy-3.0.0.tgz">character-entities-legacy 3.0.0</a> W</span> | <span id="p1728">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1729">f36404294f0713ab8e3a08f133195d30​85d0367816fc6c74136babcf90fdc988</span> |
| <span id="p1730"><a href="https://registry.npmjs.org/chokidar/-/chokidar-5.0.0.tgz">chokidar 5.0.0</a> W</span> | <span id="p1731">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1732">45d07ea7d57ee482c733ab3c547cc49e​dc1423bc231507e41ff99d2711f7f5e3</span> |
| <span id="p1733"><a href="https://registry.npmjs.org/ci-info/-/ci-info-4.4.0.tgz">ci-info 4.4.0</a> W</span> | <span id="p1734">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1735">90dc91404af2f0354fc8af1e6195eddc​3df4a216b94aed7da602226b4cda591f</span> |
| <span id="p1736"><a href="https://registry.npmjs.org/clsx/-/clsx-2.1.1.tgz">clsx 2.1.1</a> W</span> | <span id="p1737">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1738">6320104b491ca645120e8f99589ce663​ff1fb337ba80066719a011bd95320303</span> |
| <span id="p1739"><a href="https://registry.npmjs.org/comma-separated-tokens/-/comma-separated-tokens-2.0.3.tgz">comma-separated-tokens 2.0.3</a> W</span> | <span id="p1740">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1741">88123eefbb07a6048efa112653c80f4a​0ac2e993bd1388c00273e14de29ec886</span> |
| <span id="p1742"><a href="https://registry.npmjs.org/commander/-/commander-11.1.0.tgz">commander 11.1.0</a> W</span> | <span id="p1743">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1744">54cbc888e72368c77004e9fbb3065596​910f5f9ffad23f01e78e31ad4da3d05e</span> |
| <span id="p1745"><a href="https://registry.npmjs.org/common-ancestor-path/-/common-ancestor-path-2.0.0.tgz">common-ancestor-path 2.0.0</a> W</span> | <span id="p1746">网站构建 / transitive<br />BlueOak-1.0.0<br />许可文件已保存</span> | <span id="p1747">7daee313a9d473eb69fd1ed25ae31cd6​0165e4bfbc7cf87a9a3ee1c7ee36d719</span> |
| <span id="p1748"><a href="https://registry.npmjs.org/cookie/-/cookie-2.0.1.tgz">cookie 2.0.1</a> W</span> | <span id="p1749">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1750">8516126668fc55128916561047c055db​77d0401dee1db108adce7267b4b06ff0</span> |
| <span id="p1751"><a href="https://registry.npmjs.org/cookie-es/-/cookie-es-1.2.3.tgz">cookie-es 1.2.3</a> W</span> | <span id="p1752">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1753">11433fb5d87d0e1dc572cb91873a853b​9bb8ae1101b3693d5e75b53ccbfd4352</span> |
| <span id="p1754"><a href="https://registry.npmjs.org/crossws/-/crossws-0.3.5.tgz">crossws 0.3.5</a> W</span> | <span id="p1755">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1756">fb9c11b94aab427e3757604a08de9bfd​a4091b219fe419fd42dea3cadc8e3346</span> |
| <span id="p1757"><a href="https://registry.npmjs.org/css-select/-/css-select-6.0.0.tgz">css-select 6.0.0</a> W</span> | <span id="p1758">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1759">7d05fd20ca96ad34abe6e5e82387ef9d​0e818d2b0774a5c1dcff400eb94dafc5</span> |
| <span id="p1760"><a href="https://registry.npmjs.org/css-tree/-/css-tree-3.2.1.tgz">css-tree 3.2.1</a> W</span> | <span id="p1761">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1762">4c06bfe733d006103a4c070dcf8e0a3b​2eb6b6a83e20e21c32d2d3b9c3ffae0a</span> |
| <span id="p1763"><a href="https://registry.npmjs.org/css-what/-/css-what-7.0.0.tgz">css-what 7.0.0</a> W</span> | <span id="p1764">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1765">e731ee3fe56f196edd6dc46e8ad25d4e​19a7fb1e350f5b99195334318f86df2c</span> |
| <span id="p1766"><a href="https://registry.npmjs.org/csso/-/csso-5.0.5.tgz">csso 5.0.5</a> W</span> | <span id="p1767">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1768">f7605918aff2de20dd00b741edbc888f​0f8ec0f79c060745c987a1ef50e54fd8</span> |
| <span id="p1769"><a href="https://registry.npmjs.org/css-tree/-/css-tree-2.2.1.tgz">css-tree 2.2.1</a> W</span> | <span id="p1770">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1771">c5133b59491ccd42e134153ccbd27e3c​cb1071c90ccedcd1b323c17e51ecf926</span> |
| <span id="p1772"><a href="https://registry.npmjs.org/mdn-data/-/mdn-data-2.0.28.tgz">mdn-data 2.0.28</a> W</span> | <span id="p1773">网站构建 / transitive<br />CC0-1.0<br />许可文件已保存</span> | <span id="p1774">c32c3c3f696871a78389962c348e6e7f​017a57228a0d3c096a422c180c60cf24</span> |
| <span id="p1775"><a href="https://registry.npmjs.org/defu/-/defu-6.1.7.tgz">defu 6.1.7</a> W</span> | <span id="p1776">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1777">c9a6777f6837633e4eba91ed78dbd0be​2d27ab0d9c53948dac6b927c819fbcd3</span> |
| <span id="p1778"><a href="https://registry.npmjs.org/dequal/-/dequal-2.0.3.tgz">dequal 2.0.3</a> W</span> | <span id="p1779">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1780">941d90d6629878167d10d2a05d8c6df8​f8fa13acc826616abb49db63ac6a5c35</span> |
| <span id="p1781"><a href="https://registry.npmjs.org/destr/-/destr-2.0.5.tgz">destr 2.0.5</a> W</span> | <span id="p1782">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1783">74e712f47d901d65965728643865cd47​c85a59908f48de042deb96823bd20a64</span> |
| <span id="p1784"><a href="https://registry.npmjs.org/detect-libc/-/detect-libc-2.1.2.tgz">detect-libc 2.1.2</a> W</span> | <span id="p1785">网站构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p1786">270dec0fc06cff86481da8af2dd8f18d​ee6b602790b14ef0e1c2c18d7da39427</span> |
| <span id="p1787"><a href="https://registry.npmjs.org/devalue/-/devalue-5.9.4.tgz">devalue 5.9.4</a> W</span> | <span id="p1788">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1789">d3fcc934bb84312e1326fba55d6dbf42​249fffb52f4c7cbd1a9986640084576b</span> |
| <span id="p1790"><a href="https://registry.npmjs.org/devlop/-/devlop-1.1.0.tgz">devlop 1.1.0</a> W</span> | <span id="p1791">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1792">aed0b5ba97cc3aba851946766b1e4804​e92a0d3b2051e047eed4e8bf508ecd5f</span> |
| <span id="p1793"><a href="https://registry.npmjs.org/diff/-/diff-9.0.0.tgz">diff 9.0.0</a> W</span> | <span id="p1794">网站构建 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p1795">b898bf23c95594607576e25ddd4013f1​d51ed0e862aaf0732815830c87b3b58f</span> |
| <span id="p1796"><a href="https://registry.npmjs.org/dom-serializer/-/dom-serializer-2.0.0.tgz">dom-serializer 2.0.0</a> W</span> | <span id="p1797">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1798">e34511f144fc6b34ce536bd60fb1ed27​dd965f07a7c317407e79dd6be9e8f399</span> |
| <span id="p1799"><a href="https://registry.npmjs.org/domelementtype/-/domelementtype-2.3.0.tgz">domelementtype 2.3.0</a> W</span> | <span id="p1800">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1801">c67164b4a994eaeaecbd968c2e5e5415​407ae6fb4486bbb470594154e25feb45</span> |
| <span id="p1802"><a href="https://registry.npmjs.org/domhandler/-/domhandler-5.0.3.tgz">domhandler 5.0.3</a> W</span> | <span id="p1803">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1804">f3952abb7e2635d8e942822d68cfb1fd​aba61148d17a1a5692bdd163d6ca4784</span> |
| <span id="p1805"><a href="https://registry.npmjs.org/domutils/-/domutils-3.2.2.tgz">domutils 3.2.2</a> W</span> | <span id="p1806">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1807">272918a13e7e093ddc983666954164e0​98fb2443f06f476f34bf47005e12c140</span> |
| <span id="p1808"><a href="https://registry.npmjs.org/dset/-/dset-3.1.4.tgz">dset 3.1.4</a> W</span> | <span id="p1809">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1810">ea5753352be6a2416c35f0f23831db3a​9986c6d9183c339fbb3f11f94d4c8357</span> |
| <span id="p1811"><a href="https://registry.npmjs.org/entities/-/entities-4.5.0.tgz">entities 4.5.0</a> W</span> | <span id="p1812">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1813">6b0c60f7351a0b65bb1fc8dbb9299f09​e7ecf6d89103d0651bf369e6f463a632</span> |
| <span id="p1814"><a href="https://registry.npmjs.org/es-module-lexer/-/es-module-lexer-2.3.2.tgz">es-module-lexer 2.3.2</a> W</span> | <span id="p1815">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1816">99b4da5f3bd7cc4483f3d892ee9037b1​0a1da26ac5bec374038cf0bd4a52e1a7</span> |
| <span id="p1817"><a href="https://registry.npmjs.org/esbuild/-/esbuild-0.28.2.tgz">esbuild 0.28.2</a> W</span> | <span id="p1818">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1819">e045f94c235c7adc50e77ba2a579c7be​c41b496b6b47c3a7845f7c1e19959a88</span> |
| <span id="p1820"><a href="https://registry.npmjs.org/eventemitter3/-/eventemitter3-5.0.4.tgz">eventemitter3 5.0.4</a> W</span> | <span id="p1821">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1822">21d4a36175672b9e6640c39a68613af7​3f9a4c47a4a4da39993e8cd085564eb6</span> |
| <span id="p1823"><a href="https://registry.npmjs.org/extend/-/extend-3.0.2.tgz">extend 3.0.2</a> W</span> | <span id="p1824">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1825">1d91d0b0faa50cba223fa937c7b5a4a6​62968b1d78b3e59dca5c917dd5cf72b2</span> |
| <span id="p1826"><a href="https://registry.npmjs.org/fast-string-truncated-width/-/fast-string-truncated-width-3.0.3.tgz">fast-string-truncated-width 3.0.3</a> W</span> | <span id="p1827">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1828">b5dace35423470b453ed5dba20419052​124b8a65cb233833f17e5483523b5eb1</span> |
| <span id="p1829"><a href="https://registry.npmjs.org/fast-string-width/-/fast-string-width-3.0.2.tgz">fast-string-width 3.0.2</a> W</span> | <span id="p1830">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1831">72daf113df209b0e55a227ff5f62683c​a99da07b59c5da36a2da62920cb3752a</span> |
| <span id="p1832"><a href="https://registry.npmjs.org/fast-wrap-ansi/-/fast-wrap-ansi-0.2.2.tgz">fast-wrap-ansi 0.2.2</a> W</span> | <span id="p1833">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1834">f6b4a10f346b4405f01a1734be4c29b1​aba315977f409ed11ea12ff2d3fae051</span> |
| <span id="p1835"><a href="https://registry.npmjs.org/fdir/-/fdir-6.5.0.tgz">fdir 6.5.0</a> W</span> | <span id="p1836">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1837">241ddcd9f31e2a1fca405326017dbb83​33ce174198e887f0f96387c29f0d365e</span> |
| <span id="p1838"><a href="https://registry.npmjs.org/find-proc/-/find-proc-0.2.0.tgz">find-proc 0.2.0</a> W</span> | <span id="p1839">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1840">8ca2dfaf6b35762239b7eacb2b7aca8e​c8cae016bd9285a4a25ae6f14a5409bd</span> |
| <span id="p1841"><a href="https://registry.npmjs.org/flattie/-/flattie-1.1.1.tgz">flattie 1.1.1</a> W</span> | <span id="p1842">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1843">c55bd1dec021aa961754477a2f001cda​f5cfe51d8696f1c246deecfdf6c19295</span> |
| <span id="p1844"><a href="https://registry.npmjs.org/fontace/-/fontace-0.4.1.tgz">fontace 0.4.1</a> W</span> | <span id="p1845">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1846">2b6126747a56082a84d437d28db029e0​4a621dedb84399f4aa706bf1b1386ff4</span> |
| <span id="p1847"><a href="https://registry.npmjs.org/fontkitten/-/fontkitten-1.0.3.tgz">fontkitten 1.0.3</a> W</span> | <span id="p1848">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1849">397ca03e21f813a5d6a7667461c2afbb​149cd30616d13b71d6809ab1e656acf1</span> |
| <span id="p1850"><a href="https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz">fsevents 2.3.3</a> W</span> | <span id="p1851">可选平台构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1852">c77e7a5d5ff31dd7acea7c44d4a0455e​0528cdacbd24a8cb6c82b66d239b587e</span> |
| <span id="p1853"><a href="https://registry.npmjs.org/get-tsconfig/-/get-tsconfig-5.0.0-beta.4.tgz">get-tsconfig 5.0.0-beta.4</a> W</span> | <span id="p1854">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1855">bcb9e623a2c7026218658719ae54028a​af0469852dd3c8a3570f0b95cd417a35</span> |
| <span id="p1856"><a href="https://registry.npmjs.org/github-slugger/-/github-slugger-2.0.0.tgz">github-slugger 2.0.0</a> W</span> | <span id="p1857">网站构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p1858">ddde66e96b7d722ff2c3d478e7595aec​cae7e75dde798d405510d862f1367d0f</span> |
| <span id="p1859"><a href="https://registry.npmjs.org/h3/-/h3-1.15.11.tgz">h3 1.15.11</a> W</span> | <span id="p1860">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1861">0a975bdfefa3daeac4c009c3e0f2fc1d​a8bebdb4a2e08d4aed561f44f27e90f4</span> |
| <span id="p1862"><a href="https://registry.npmjs.org/hast-util-to-html/-/hast-util-to-html-9.0.5.tgz">hast-util-to-html 9.0.5</a> W</span> | <span id="p1863">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1864">039bc4739cc0cafde07e0246f885a247​451e5061ae983908c1019427691eacc0</span> |
| <span id="p1865"><a href="https://registry.npmjs.org/hast-util-whitespace/-/hast-util-whitespace-3.0.0.tgz">hast-util-whitespace 3.0.0</a> W</span> | <span id="p1866">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1867">673f97f5bba3cac0184726f519a57502​73e4434b839a769f4fbf09e4b4da2ceb</span> |
| <span id="p1868"><a href="https://registry.npmjs.org/html-escaper/-/html-escaper-3.0.3.tgz">html-escaper 3.0.3</a> W</span> | <span id="p1869">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1870">19c5627ca8032d56a0ddbf2c80132ee8​f5ab257161e3767b608cb5e3b96dd109</span> |
| <span id="p1871"><a href="https://registry.npmjs.org/html-void-elements/-/html-void-elements-3.0.0.tgz">html-void-elements 3.0.0</a> W</span> | <span id="p1872">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1873">301b6ef51a58d296bb3f837c48402110​25a7e541f304d4a379e6062e45373530</span> |
| <span id="p1874"><a href="https://registry.npmjs.org/http-cache-semantics/-/http-cache-semantics-4.2.0.tgz">http-cache-semantics 4.2.0</a> W</span> | <span id="p1875">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1876">f57454db8ab2d06a4baabbfb7c70ad41​81a00b7ee0efebcdffa9ba313bd80eb7</span> |
| <span id="p1877"><a href="https://registry.npmjs.org/iron-webcrypto/-/iron-webcrypto-1.2.1.tgz">iron-webcrypto 1.2.1</a> W</span> | <span id="p1878">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1879">8ef2ee4739cc6679e5b888aeed512a95​8400b1ad8e8a4fe5f0f6c91d0a1c27fd</span> |
| <span id="p1880"><a href="https://registry.npmjs.org/is-docker/-/is-docker-4.0.0.tgz">is-docker 4.0.0</a> W</span> | <span id="p1881">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1882">247bf5bbbffbfbc4c85cf70f3fd13df5​e4232252e435c19d898480faa5a1b6b3</span> |
| <span id="p1883"><a href="https://registry.npmjs.org/is-plain-obj/-/is-plain-obj-4.1.0.tgz">is-plain-obj 4.1.0</a> W</span> | <span id="p1884">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1885">c71d874f7ab7cd560329b080ce790f97​68dea503337fe2e2719a18e28be621f7</span> |
| <span id="p1886"><a href="https://registry.npmjs.org/js-yaml/-/js-yaml-4.3.2.tgz">js-yaml 4.3.2</a> W</span> | <span id="p1887">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1888">c7b241d2224cf9253ff53854aa4cee87​da91bd889c4d0fa3a3ffd1041ecee5b1</span> |
| <span id="p1889"><a href="https://registry.npmjs.org/jsonc-parser/-/jsonc-parser-3.3.1.tgz">jsonc-parser 3.3.1</a> W</span> | <span id="p1890">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1891">4a0315b8671e7463bae7af7c142cdf19​e9aa7ba39eb36dc2df383b8648e3cbc9</span> |
| <span id="p1892"><a href="https://registry.npmjs.org/lightningcss/-/lightningcss-1.33.0.tgz">lightningcss 1.33.0</a> W</span> | <span id="p1893">网站构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1894">d492f4278bb7234ceaa3c2638ef944e1​08ea17a23db7c6a2367c14fa725598cf</span> |
| <span id="p1895"><a href="https://registry.npmjs.org/lightningcss-android-arm64/-/lightningcss-android-arm64-1.33.0.tgz">lightningcss-android-arm64 1.33.0</a> W</span> | <span id="p1896">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1897">e6fd2befa439a4934dd50a9283820a7b​95725246a3251c60588f074aff20509a</span> |
| <span id="p1898"><a href="https://registry.npmjs.org/lightningcss-darwin-arm64/-/lightningcss-darwin-arm64-1.33.0.tgz">lightningcss-darwin-arm64 1.33.0</a> W</span> | <span id="p1899">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1900">06e9d271513d7e3f08e680d5e48bb705​43c13161ff41bc5b56934726d9a2e913</span> |
| <span id="p1901"><a href="https://registry.npmjs.org/lightningcss-darwin-x64/-/lightningcss-darwin-x64-1.33.0.tgz">lightningcss-darwin-x64 1.33.0</a> W</span> | <span id="p1902">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1903">c0b555fe6ec4c5c660503b1e87aad7ac​90ba5af1e2cb1742155d485a39d5b973</span> |
| <span id="p1904"><a href="https://registry.npmjs.org/lightningcss-freebsd-x64/-/lightningcss-freebsd-x64-1.33.0.tgz">lightningcss-freebsd-x64 1.33.0</a> W</span> | <span id="p1905">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1906">828e9a915d504a2796bdbe56643397d3​ac639bf9abc629ba11163e7b7ef150a6</span> |
| <span id="p1907"><a href="https://registry.npmjs.org/lightningcss-linux-arm-gnueabihf/-/lightningcss-linux-arm-gnueabihf-1.33.0.tgz">lightningcss-linux-arm-gnueabihf 1.33.0</a> W</span> | <span id="p1908">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1909">b2a0af78c27da36a2449c2fe71eb3730​e6c40d7aaab20bdc3689282432bb3117</span> |
| <span id="p1910"><a href="https://registry.npmjs.org/lightningcss-linux-arm64-gnu/-/lightningcss-linux-arm64-gnu-1.33.0.tgz">lightningcss-linux-arm64-gnu 1.33.0</a> W</span> | <span id="p1911">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1912">257b51498dfd90fc99b87afd28408ff9​b53162e521db4e06a493e356b8536711</span> |
| <span id="p1913"><a href="https://registry.npmjs.org/lightningcss-linux-arm64-musl/-/lightningcss-linux-arm64-musl-1.33.0.tgz">lightningcss-linux-arm64-musl 1.33.0</a> W</span> | <span id="p1914">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1915">048a00d8ef519a413e01907a5a50e01d​7c4e86ddcde49a5020eed7747196b9f6</span> |
| <span id="p1916"><a href="https://registry.npmjs.org/lightningcss-linux-x64-gnu/-/lightningcss-linux-x64-gnu-1.33.0.tgz">lightningcss-linux-x64-gnu 1.33.0</a> W</span> | <span id="p1917">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1918">fd485dfd57082c4ef864dd867fa87fd8​e1a9b5d58ee85c2b76e28e42c8f3e1d3</span> |
| <span id="p1919"><a href="https://registry.npmjs.org/lightningcss-linux-x64-musl/-/lightningcss-linux-x64-musl-1.33.0.tgz">lightningcss-linux-x64-musl 1.33.0</a> W</span> | <span id="p1920">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1921">f3a1a10f3c393db5ce03438035b94fcd​48bc7b7b52bb97f76a3ed52784624441</span> |
| <span id="p1922"><a href="https://registry.npmjs.org/lightningcss-win32-arm64-msvc/-/lightningcss-win32-arm64-msvc-1.33.0.tgz">lightningcss-win32-arm64-msvc 1.33.0</a> W</span> | <span id="p1923">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1924">9c211ef0a63a92626091f7c0a97b0ddb​39b4278da5b11d13512b7eed9680bd7d</span> |
| <span id="p1925"><a href="https://registry.npmjs.org/lightningcss-win32-x64-msvc/-/lightningcss-win32-x64-msvc-1.33.0.tgz">lightningcss-win32-x64-msvc 1.33.0</a> W</span> | <span id="p1926">可选平台构建 / transitive<br />MPL-2.0<br />许可文件已保存</span> | <span id="p1927">feb506faf3bdf4139826f521777c71b5​3c355f8eb6bcdd3220e16c5e131f1197</span> |
| <span id="p1928"><a href="https://registry.npmjs.org/lru-cache/-/lru-cache-11.5.3.tgz">lru-cache 11.5.3</a> W</span> | <span id="p1929">网站构建 / transitive<br />BlueOak-1.0.0<br />许可文件已保存</span> | <span id="p1930">d18739bbd7d0091d30d2cca58e120c8b​70ac09a5a21aa4b2b3e9afb2dc4084d8</span> |
| <span id="p1931"><a href="https://registry.npmjs.org/magic-string/-/magic-string-1.4.1.tgz">magic-string 1.4.1</a> W</span> | <span id="p1932">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1933">bc9e80359069a9d84958ef3553e88b56​4269537edf51699b6bcd40aee9f06e33</span> |
| <span id="p1934"><a href="https://registry.npmjs.org/magicast/-/magicast-0.5.5.tgz">magicast 0.5.5</a> W</span> | <span id="p1935">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1936">5561d86abd904681f987e64f2a9ffc20​3da3d2067db88c174580864462c7dbec</span> |
| <span id="p1937"><a href="https://registry.npmjs.org/mdast-util-to-hast/-/mdast-util-to-hast-13.2.1.tgz">mdast-util-to-hast 13.2.1</a> W</span> | <span id="p1938">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1939">41f70e2f73a4ad9c67a401faa3143d16​d6a1bda2c6bf9ae48073a2d4f5ebb1f4</span> |
| <span id="p1940"><a href="https://registry.npmjs.org/mdn-data/-/mdn-data-2.27.1.tgz">mdn-data 2.27.1</a> W</span> | <span id="p1941">网站构建 / transitive<br />CC0-1.0<br />许可文件已保存</span> | <span id="p1942">63985bd4ce64e9a0142d70465c3a7f54​c488f3ef6da3f9512d54a728cde46870</span> |
| <span id="p1943"><a href="https://registry.npmjs.org/micromark-util-character/-/micromark-util-character-2.1.1.tgz">micromark-util-character 2.1.1</a> W</span> | <span id="p1944">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1945">bacefea968d21cedf290ec319ec92e2b​c20e4f7b02f62cb4ad1e7b07c5a45185</span> |
| <span id="p1946"><a href="https://registry.npmjs.org/micromark-util-encode/-/micromark-util-encode-2.0.1.tgz">micromark-util-encode 2.0.1</a> W</span> | <span id="p1947">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1948">c553824f256f5f99f8f8b172d25caa7b​2270ece5a00774cd1dbbc8bf9cd9090a</span> |
| <span id="p1949"><a href="https://registry.npmjs.org/micromark-util-sanitize-uri/-/micromark-util-sanitize-uri-2.0.1.tgz">micromark-util-sanitize-uri 2.0.1</a> W</span> | <span id="p1950">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1951">8fcf4cf2900f807194fc89fb3e4dd5e5​b28143cb44e55955a9f31d764264547e</span> |
| <span id="p1952"><a href="https://registry.npmjs.org/micromark-util-symbol/-/micromark-util-symbol-2.0.1.tgz">micromark-util-symbol 2.0.1</a> W</span> | <span id="p1953">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1954">d8d698fae34d4e5bcdc5caf552449dea​8aa46709dc76caea815c931cbd61e222</span> |
| <span id="p1955"><a href="https://registry.npmjs.org/micromark-util-types/-/micromark-util-types-2.0.2.tgz">micromark-util-types 2.0.2</a> W</span> | <span id="p1956">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1957">4b7223263259987280cb0f970887702e​7725af15644849cc584d300a43a6291d</span> |
| <span id="p1958"><a href="https://registry.npmjs.org/mrmime/-/mrmime-2.0.1.tgz">mrmime 2.0.1</a> W</span> | <span id="p1959">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1960">2cc6d534bb1f78f70dcb513c9b3b7ab9​82e22291ebc291e3366dee085fadbadd</span> |
| <span id="p1961"><a href="https://registry.npmjs.org/nanoid/-/nanoid-3.3.19.tgz">nanoid 3.3.19</a> W</span> | <span id="p1962">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1963">4e371b71e3d5081fa0052356d5c1904e​7a60e049864c26f0724cfd32dc303849</span> |
| <span id="p1964"><a href="https://registry.npmjs.org/neotraverse/-/neotraverse-1.0.1.tgz">neotraverse 1.0.1</a> W</span> | <span id="p1965">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1966">abc5bce723449ad33ee616d6681a6bb5​51fbe68f1a17b6f2f24444df6011750f</span> |
| <span id="p1967"><a href="https://registry.npmjs.org/nlcst-to-string/-/nlcst-to-string-4.0.0.tgz">nlcst-to-string 4.0.0</a> W</span> | <span id="p1968">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1969">2388bd502b2c6eab765026201700b5dd​cea019012b9e7e71beb6774fba217296</span> |
| <span id="p1970"><a href="https://registry.npmjs.org/node-fetch-native/-/node-fetch-native-1.6.7.tgz">node-fetch-native 1.6.7</a> W</span> | <span id="p1971">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1972">f60116b7c99ef401e3c46ec7d3ad97d6​6f5ccf1fd45eee9a2d95136c981314a7</span> |
| <span id="p1973"><a href="https://registry.npmjs.org/node-mock-http/-/node-mock-http-1.0.5.tgz">node-mock-http 1.0.5</a> W</span> | <span id="p1974">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1975">167bd074d5015e1cb343de6281f063bb​d05a23ea2e1fce1faaaf265fe688f40d</span> |
| <span id="p1976"><a href="https://registry.npmjs.org/normalize-path/-/normalize-path-3.0.0.tgz">normalize-path 3.0.0</a> W</span> | <span id="p1977">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1978">0b983cca55c555cdc0e919ed5ecd0e46​48f6e303f9dffeb449f1ad760d4f84fe</span> |
| <span id="p1979"><a href="https://registry.npmjs.org/nth-check/-/nth-check-2.1.1.tgz">nth-check 2.1.1</a> W</span> | <span id="p1980">网站构建 / transitive<br />BSD-2-Clause<br />许可文件已保存</span> | <span id="p1981">45dc0a2bc34205656c0fbe8374c725c0​4b71b40e739b74c9fc763480c8063642</span> |
| <span id="p1982"><a href="https://registry.npmjs.org/obug/-/obug-2.2.1.tgz">obug 2.2.1</a> W</span> | <span id="p1983">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1984">cbf042980f79918d07c46817fe18ed0d​b6a8e55893dd7347b7cad71e3e5f65a7</span> |
| <span id="p1985"><a href="https://registry.npmjs.org/ofetch/-/ofetch-1.5.1.tgz">ofetch 1.5.1</a> W</span> | <span id="p1986">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1987">0483ce6fbfce9f9d67eda8d2544bb867​7737729b6a1b2fec7c3b8f290b4a51fa</span> |
| <span id="p1988"><a href="https://registry.npmjs.org/ohash/-/ohash-2.0.12.tgz">ohash 2.0.12</a> W</span> | <span id="p1989">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1990">05875f32a0a3e6d1d3b8562961c1e0f7​b2c74d8697f29a1c4d33075d52070787</span> |
| <span id="p1991"><a href="https://registry.npmjs.org/oniguruma-parser/-/oniguruma-parser-0.12.2.tgz">oniguruma-parser 0.12.2</a> W</span> | <span id="p1992">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1993">c36b254375a4b8c306d72bf3191cd5bf​f7a6b46d75d0fe4775f48eb68460d6b4</span> |
| <span id="p1994"><a href="https://registry.npmjs.org/oniguruma-to-es/-/oniguruma-to-es-4.3.6.tgz">oniguruma-to-es 4.3.6</a> W</span> | <span id="p1995">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1996">9a5cfbc395d460bb3fec9797c5f4d2de​c88303f81f222c261f60422740f6058f</span> |
| <span id="p1997"><a href="https://registry.npmjs.org/p-limit/-/p-limit-7.3.3.tgz">p-limit 7.3.3</a> W</span> | <span id="p1998">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p1999">aede2030b82db2457fea89ffceaebcba​9877275246fe69de73a78f7b6a2432f7</span> |
| <span id="p2000"><a href="https://registry.npmjs.org/p-queue/-/p-queue-9.3.3.tgz">p-queue 9.3.3</a> W</span> | <span id="p2001">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2002">03955c45657d2b3c4f415eaf8f92fe7c​9c35f81ca5cbcb78e15c08a453b7f2a0</span> |
| <span id="p2003"><a href="https://registry.npmjs.org/p-timeout/-/p-timeout-7.0.2.tgz">p-timeout 7.0.2</a> W</span> | <span id="p2004">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2005">b862674f5e19b6e787918a2cdab67fbe​c39b33ee35fce3e96ffa8ed781c131e3</span> |
| <span id="p2006"><a href="https://registry.npmjs.org/package-manager-detector/-/package-manager-detector-1.8.0.tgz">package-manager-detector 1.8.0</a> W</span> | <span id="p2007">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2008">fcf82d09555ad9ed291500b5c358c81e​2a1860946b5b85e32477cbe31a59a6b1</span> |
| <span id="p2009"><a href="https://registry.npmjs.org/piccolore/-/piccolore-0.1.3.tgz">piccolore 0.1.3</a> W</span> | <span id="p2010">网站构建 / transitive<br />ISC<br />缺独立许可文本</span> | <span id="p2011">d80aca8423f431568f382a1df72a9648​0ea66186567598a8eeebc8e2d7c59b9b</span> |
| <span id="p2012"><a href="https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz">picocolors 1.1.1</a> W</span> | <span id="p2013">网站构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p2014">d3aedb2807967b7eb37fd11b03b7e370​1e725af79c650d0812ff7213f8f882d9</span> |
| <span id="p2015"><a href="https://registry.npmjs.org/picomatch/-/picomatch-4.0.7.tgz">picomatch 4.0.7</a> W</span> | <span id="p2016">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2017">697b463be3cdbd9ffc8f4194fd5019a6​9ddf95875fb703d78b2b115cc9e740a8</span> |
| <span id="p2018"><a href="https://registry.npmjs.org/postcss/-/postcss-8.5.28.tgz">postcss 8.5.28</a> W</span> | <span id="p2019">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2020">f63d6d9bce28989cd083add85af717c0​264e44323d35c909ae99ac934e9641a6</span> |
| <span id="p2021"><a href="https://registry.npmjs.org/prismjs/-/prismjs-1.30.0.tgz">prismjs 1.30.0</a> W</span> | <span id="p2022">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2023">ac16a9106a28c53b6a6313993c816a3a​02525fdfefd7614fc1703df915a9fc11</span> |
| <span id="p2024"><a href="https://registry.npmjs.org/process-ancestry/-/process-ancestry-0.1.0.tgz">process-ancestry 0.1.0</a> W</span> | <span id="p2025">网站构建 / transitive<br />MIT<br />缺独立许可文本</span> | <span id="p2026">b73a85f002681f3fd87ae9112e7b11bb​29a06bc90be2e359010c6a7d709a4ecf</span> |
| <span id="p2027"><a href="https://registry.npmjs.org/property-information/-/property-information-7.2.0.tgz">property-information 7.2.0</a> W</span> | <span id="p2028">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2029">22ab7ee8774c8c3c90086f2fec7d2d4c​ca7c16ac795596ae16cf326c763606c7</span> |
| <span id="p2030"><a href="https://registry.npmjs.org/radix3/-/radix3-1.1.2.tgz">radix3 1.1.2</a> W</span> | <span id="p2031">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2032">0a52222fae07c436ce682a0236ebb002​d0a937af9f9c1600ea7ddd8630899104</span> |
| <span id="p2033"><a href="https://registry.npmjs.org/readdirp/-/readdirp-5.1.1.tgz">readdirp 5.1.1</a> W</span> | <span id="p2034">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2035">935a688197715ea14c184e4a56542d6a​be99a75b2c6d805d24a4cdf36514d5a5</span> |
| <span id="p2036"><a href="https://registry.npmjs.org/regex/-/regex-6.1.0.tgz">regex 6.1.0</a> W</span> | <span id="p2037">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2038">0ae0b62eb4001fe41323c68de5b817bc​aa6a8f4121303c3a642adc05b46dba91</span> |
| <span id="p2039"><a href="https://registry.npmjs.org/regex-recursion/-/regex-recursion-6.0.2.tgz">regex-recursion 6.0.2</a> W</span> | <span id="p2040">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2041">0099aee04c6e7f912ae29e2e900bc5b4​c3f837836e632a9c358a7e714fca04e6</span> |
| <span id="p2042"><a href="https://registry.npmjs.org/regex-utilities/-/regex-utilities-2.3.0.tgz">regex-utilities 2.3.0</a> W</span> | <span id="p2043">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2044">b952edd3197f36694e1e3b72a0f3131c​515b256789f98d13d193ee03b2f3ecf5</span> |
| <span id="p2045"><a href="https://registry.npmjs.org/resolve-pkg-maps/-/resolve-pkg-maps-1.0.0.tgz">resolve-pkg-maps 1.0.0</a> W</span> | <span id="p2046">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2047">4a7cbdb7054b1dd6e466067129be9577​b495ff69d02064913e1723405db0df76</span> |
| <span id="p2048"><a href="https://registry.npmjs.org/retext-smartypants/-/retext-smartypants-6.2.0.tgz">retext-smartypants 6.2.0</a> W</span> | <span id="p2049">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2050">2628362b207b96c7872da3ecf1f10808​c4a1d36a4e9e7b1c1ce3f5b0a46af6be</span> |
| <span id="p2051"><a href="https://registry.npmjs.org/rolldown/-/rolldown-1.2.9.tgz">rolldown 1.2.9</a> W</span> | <span id="p2052">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2053">68c344a0cfab1cca11288b0175bab84a​6702cb7b0c7f60aa4322fb69782d34f8</span> |
| <span id="p2054"><a href="https://registry.npmjs.org/satteri/-/satteri-0.10.5.tgz">satteri 0.10.5</a> W</span> | <span id="p2055">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2056">aaf1038f2952e7755edf32419a70b44d​011c6c274ffd05d1b69ca4af9a907613</span> |
| <span id="p2057"><a href="https://registry.npmjs.org/sax/-/sax-1.6.1.tgz">sax 1.6.1</a> W</span> | <span id="p2058">网站构建 / transitive<br />BlueOak-1.0.0<br />许可文件已保存</span> | <span id="p2059">6e9abf03478608b80894bb8b6421271a​0e583504f785f749a700d6bb35be85bd</span> |
| <span id="p2060"><a href="https://registry.npmjs.org/semver/-/semver-7.8.5.tgz">semver 7.8.5</a> W</span> | <span id="p2061">可选平台构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p2062">d85045d4300d7d57c891336b95df532e​73f34c22ffcd222452b6d08b9d127d5d</span> |
| <span id="p2063"><a href="https://registry.npmjs.org/sharp/-/sharp-0.35.4.tgz">sharp 0.35.4</a> W</span> | <span id="p2064">可选平台构建 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p2065">6ebef10290372c7309d9e22e3ecb9e32​ca6a3aa6e07f3d83aa904df8ae4f6a5a</span> |
| <span id="p2066"><a href="https://registry.npmjs.org/shiki/-/shiki-4.4.3.tgz">shiki 4.4.3</a> W</span> | <span id="p2067">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2068">d8536a2fc9cb41782e551eabf61e44b7​c0ae18890ec201e790a3819be1ff98de</span> |
| <span id="p2069"><a href="https://registry.npmjs.org/sisteransi/-/sisteransi-1.0.5.tgz">sisteransi 1.0.5</a> W</span> | <span id="p2070">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2071">9e4d29b24315611de5a1767ca1b09716​f40bb04534836295fe36d80c643974b3</span> |
| <span id="p2072"><a href="https://registry.npmjs.org/smol-toml/-/smol-toml-1.8.0.tgz">smol-toml 1.8.0</a> W</span> | <span id="p2073">网站构建 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2074">1fc995be91cdb777fc13e20c2edfebaa​f60ef4e4d2d5331caef2837b04d37892</span> |
| <span id="p2075"><a href="https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz">source-map-js 1.2.1</a> W</span> | <span id="p2076">网站构建 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2077">f126a6f9fca487a43219d8cb8c3a9552​79187a966119d548eb5cd47e999d4853</span> |
| <span id="p2078"><a href="https://registry.npmjs.org/space-separated-tokens/-/space-separated-tokens-2.0.2.tgz">space-separated-tokens 2.0.2</a> W</span> | <span id="p2079">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2080">b386cce96593975cebbb054a8e287eb1​5c2e004cd6ef416f7a26b5c265930b67</span> |
| <span id="p2081"><a href="https://registry.npmjs.org/stringify-entities/-/stringify-entities-4.0.4.tgz">stringify-entities 4.0.4</a> W</span> | <span id="p2082">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2083">89052f611f0656a0e7d7c312f7b2e75e​949678ce4eff37a6fc416fa2be4f4024</span> |
| <span id="p2084"><a href="https://registry.npmjs.org/svgo/-/svgo-4.1.0.tgz">svgo 4.1.0</a> W</span> | <span id="p2085">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2086">6646ae27350d38dc2f08e708ee64b885​b9746775ef7c8091f171d94052a333a6</span> |
| <span id="p2087"><a href="https://registry.npmjs.org/tiny-inflate/-/tiny-inflate-1.0.3.tgz">tiny-inflate 1.0.3</a> W</span> | <span id="p2088">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2089">73932b339424e5ffaeaf043e6481229c​ab407ee277b2a01fa23938dfad6a8f4e</span> |
| <span id="p2090"><a href="https://registry.npmjs.org/tinyclip/-/tinyclip-0.1.15.tgz">tinyclip 0.1.15</a> W</span> | <span id="p2091">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2092">44023405fb52fc3e1676b3593c7de0c8​354c6fb412eabab97d235166568f75e1</span> |
| <span id="p2093"><a href="https://registry.npmjs.org/tinyexec/-/tinyexec-1.3.1.tgz">tinyexec 1.3.1</a> W</span> | <span id="p2094">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2095">540b804f39c7716c232252085e4d43d9​b10e2d89db39faaa1b31ed8cd93e2f1f</span> |
| <span id="p2096"><a href="https://registry.npmjs.org/tinyglobby/-/tinyglobby-0.2.17.tgz">tinyglobby 0.2.17</a> W</span> | <span id="p2097">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2098">afb4afae9175f8b873ac13e1d21cea09​97a0bcb40c3598613a834490058cb562</span> |
| <span id="p2099"><a href="https://registry.npmjs.org/trim-lines/-/trim-lines-3.0.1.tgz">trim-lines 3.0.1</a> W</span> | <span id="p2100">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2101">5880f0ef03e792c4705dc0789f299967​1d4796d1d10a0110df059f25c565d63d</span> |
| <span id="p2102"><a href="https://registry.npmjs.org/trough/-/trough-2.2.0.tgz">trough 2.2.0</a> W</span> | <span id="p2103">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2104">0a357f8de5e3a6f69fa3672daf31a19a​87fc153b21085790c78fa4097263ab58</span> |
| <span id="p2105"><a href="https://registry.npmjs.org/tslib/-/tslib-2.8.1.tgz">tslib 2.8.1</a> W</span> | <span id="p2106">可选平台构建 / transitive<br />0BSD<br />许可文件已保存</span> | <span id="p2107">66f635d5eeabae44807534976913a102​cf615b9a045368359c9f79ae6ee2119e</span> |
| <span id="p2108"><a href="https://registry.npmjs.org/ufo/-/ufo-1.6.4.tgz">ufo 1.6.4</a> W</span> | <span id="p2109">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2110">b060e20d485ef8f6a8b9d58dc0fb28e8​b9607dfeabf2b6007a73e60f012e6ab0</span> |
| <span id="p2111"><a href="https://registry.npmjs.org/ultrahtml/-/ultrahtml-1.7.0.tgz">ultrahtml 1.7.0</a> W</span> | <span id="p2112">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2113">e0841d8991cb62733c4a20cdaa471b6f​d207193c900f9c5a3a7375e4fdc8a45b</span> |
| <span id="p2114"><a href="https://registry.npmjs.org/uncrypto/-/uncrypto-0.1.3.tgz">uncrypto 0.1.3</a> W</span> | <span id="p2115">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2116">c4935f57eaa4cbac82ab58ad5b252a13​4acb49f6f7c521d2510821e990e40c71</span> |
| <span id="p2117"><a href="https://registry.npmjs.org/undici/-/undici-8.10.2.tgz">undici 8.10.2</a> W</span> | <span id="p2118">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2119">740638ae32d78d2646a6727950e365fa​26b6fa87913fa096e60ed4afeb4634aa</span> |
| <span id="p2120"><a href="https://registry.npmjs.org/unified/-/unified-11.0.5.tgz">unified 11.0.5</a> W</span> | <span id="p2121">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2122">bc6d6d9e336d7d775f3c369f0a294625​23ae75254d4a6e4888b95eba44c4aa78</span> |
| <span id="p2123"><a href="https://registry.npmjs.org/unifont/-/unifont-0.7.5.tgz">unifont 0.7.5</a> W</span> | <span id="p2124">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2125">75fa9edbd8d1e620c29eab7bcfea2bed​64330461157367be5408b7c6e07d9dc1</span> |
| <span id="p2126"><a href="https://registry.npmjs.org/unist-util-is/-/unist-util-is-6.0.1.tgz">unist-util-is 6.0.1</a> W</span> | <span id="p2127">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2128">6d406238b6e281d38d30c30f77287ce8​d70f6d9c4503612f979333865aaafff5</span> |
| <span id="p2129"><a href="https://registry.npmjs.org/unist-util-position/-/unist-util-position-5.0.0.tgz">unist-util-position 5.0.0</a> W</span> | <span id="p2130">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2131">248cefc2080c0a78817b20e88da7324e​7dee7175c5df8ac0e6d193d2d381c200</span> |
| <span id="p2132"><a href="https://registry.npmjs.org/unist-util-stringify-position/-/unist-util-stringify-position-4.0.0.tgz">unist-util-stringify-position 4.0.0</a> W</span> | <span id="p2133">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2134">8692d2396f091680fe342c344acc4594​534a9a811b0a9cbcfae7d71c694168b4</span> |
| <span id="p2135"><a href="https://registry.npmjs.org/unist-util-visit/-/unist-util-visit-5.1.0.tgz">unist-util-visit 5.1.0</a> W</span> | <span id="p2136">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2137">8d5724e443d279deda20fe03ce18de53​a944f8154e94297de0f49c5fb51f72ef</span> |
| <span id="p2138"><a href="https://registry.npmjs.org/unist-util-visit-parents/-/unist-util-visit-parents-6.0.2.tgz">unist-util-visit-parents 6.0.2</a> W</span> | <span id="p2139">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2140">5250902af03c4b335c68cd60ed5eb4f1​d9fbd6338e129d7df476690b8a245da5</span> |
| <span id="p2141"><a href="https://registry.npmjs.org/unstorage/-/unstorage-1.17.5.tgz">unstorage 1.17.5</a> W</span> | <span id="p2142">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2143">3f4685cc4d7300a8bcdde0d3dcc071ed​77ee7e20ce16f1e322f6e7eb39e25446</span> |
| <span id="p2144"><a href="https://registry.npmjs.org/verkit/-/verkit-0.4.1.tgz">verkit 0.4.1</a> W</span> | <span id="p2145">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2146">7e365ef868c537996dc19b54244466cb​b29b5045406ab152fa96faf1803ab26c</span> |
| <span id="p2147"><a href="https://registry.npmjs.org/vfile/-/vfile-6.0.3.tgz">vfile 6.0.3</a> W</span> | <span id="p2148">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2149">a0dbad2fd8dcc9ae9f652dee6ba49a1d​b5db2843a8ec2ceb9190ccdba0e0df0c</span> |
| <span id="p2150"><a href="https://registry.npmjs.org/vfile-message/-/vfile-message-4.0.3.tgz">vfile-message 4.0.3</a> W</span> | <span id="p2151">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2152">9d6d94ee59296ef0516217a79e902ba4​17fe3d8816ab1d0527ddf353b455c2cb</span> |
| <span id="p2153"><a href="https://registry.npmjs.org/vite/-/vite-8.3.0.tgz">vite 8.3.0</a> W</span> | <span id="p2154">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2155">8341c0e40cf1700c68998ce5e7b1c715​b9f89d700abf6c41f5d8af067a270a72</span> |
| <span id="p2156"><a href="https://registry.npmjs.org/vitefu/-/vitefu-1.1.3.tgz">vitefu 1.1.3</a> W</span> | <span id="p2157">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2158">91ac953765942a6f17277078d34ecd4e​5acdd999d0344262879c50a1baaf85d1</span> |
| <span id="p2159"><a href="https://registry.npmjs.org/xxhash-wasm/-/xxhash-wasm-1.1.0.tgz">xxhash-wasm 1.1.0</a> W</span> | <span id="p2160">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2161">cddd90f792012cd253728e11a643e152​51268a7a9588851ccc51a5c8f16340ad</span> |
| <span id="p2162"><a href="https://registry.npmjs.org/yargs-parser/-/yargs-parser-22.0.0.tgz">yargs-parser 22.0.0</a> W</span> | <span id="p2163">网站构建 / transitive<br />ISC<br />许可文件已保存</span> | <span id="p2164">2b640247b9ca6f540c708dfea99bafea​e59a46db66f491fb5b6d55fce1614d65</span> |
| <span id="p2165"><a href="https://registry.npmjs.org/yocto-queue/-/yocto-queue-1.2.2.tgz">yocto-queue 1.2.2</a> W</span> | <span id="p2166">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2167">69e7b1153fcfbc16b2cefb12c7a31b79​fa4f0fa2915f77ab8ca8afccac680bae</span> |
| <span id="p2168"><a href="https://registry.npmjs.org/zod/-/zod-4.6.5.tgz">zod 4.6.5</a> W</span> | <span id="p2169">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2170">a78c0c533de30dc1c4afc259ac43ac06​e390cb0da8d2e32eae355301b50b36fc</span> |
| <span id="p2171"><a href="https://registry.npmjs.org/zwitch/-/zwitch-2.0.4.tgz">zwitch 2.0.4</a> W</span> | <span id="p2172">网站构建 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2173">2c162e000f5fb5a816987d6f8ad7aad2​95203f777a5992d514ae4660778a51a4</span> |

### <span id="p2174">dart 锁实例</span>

<!-- table-05 -->
| <span id="p2175"><strong>包与锁</strong></span> | <span id="p2176"><strong>用途与许可证声明</strong></span> | <span id="p2177"><strong>官方归档 SHA256</strong></span> |
| --- | --- | --- |
| <span id="p2178"><a href="https://pub.dev/api/archives/async-2.13.1.tar.gz">async 2.13.1</a> D</span> | <span id="p2179">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2180">e2eb0491ba5ddb6177742d2da2390457​4082139b07c1e33b8503b9f46f3e1a37</span> |
| <span id="p2181"><a href="https://pub.dev/api/archives/boolean_selector-2.1.2.tar.gz">boolean&#95;selector 2.1.2</a> D</span> | <span id="p2182">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2183">8aab1771e1243a5063b8b0ff68042d67​334e3feab9e95b9490f9a6ebf73b42ea</span> |
| <span id="p2184"><a href="https://pub.dev/api/archives/characters-1.4.1.tar.gz">characters 1.4.1</a> D</span> | <span id="p2185">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2186">faf38497bda5ead2a8c7615f4f7939df​04333478bf32e4173fcb06d428b5716b</span> |
| <span id="p2187"><a href="https://pub.dev/api/archives/clock-1.1.3.tar.gz">clock 1.1.3</a> D</span> | <span id="p2188">应用平台传递 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p2189">e51d50bca3217c9a9fa2b41a30e4a389​71133f5f9ec7a3d57bae095007f1d28e</span> |
| <span id="p2190"><a href="https://pub.dev/api/archives/collection-1.19.1.tar.gz">collection 1.19.1</a> D</span> | <span id="p2191">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2192">2f5709ae4d3d59dd8f7cd309b4e02304​6b57d8a6c82130785d2b0e5868084e76</span> |
| <span id="p2193"><a href="https://pub.dev/api/archives/cross_file-0.3.5+5.tar.gz">cross&#95;file 0.3.5+5</a> D</span> | <span id="p2194">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2195">f141ea4f277af142a0356955707f6556​f37b03947d39d55585981a06ca437bd6</span> |
| <span id="p2196"><a href="https://pub.dev/api/archives/csslib-1.0.2.tar.gz">csslib 1.0.2</a> D</span> | <span id="p2197">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2198">09bad715f418841f976c77db72d5398d​c1253c21fb9c0c7f0b0b985860b2d58e</span> |
| <span id="p2199"><a href="https://pub.dev/api/archives/cupertino_icons-1.0.9.tar.gz">cupertino&#95;icons 1.0.9</a> D</span> | <span id="p2200">应用平台传递 / 直接生产<br />MIT<br />许可文件已保存</span> | <span id="p2201">41e005c33bd814be4d3096aff55b1908​d419fde52ca656c8c47719ec745873cd</span> |
| <span id="p2202"><a href="https://pub.dev/api/archives/cupertino_ui-1.0.2.tar.gz">cupertino&#95;ui 1.0.2</a> D</span> | <span id="p2203">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2204">e9dfe7fac704028f8928cbe4028a0be5​e8a709498e8daf8247de99e99a32aef3</span> |
| <span id="p2205"><a href="https://pub.dev/api/archives/fake_async-1.3.3.tar.gz">fake&#95;async 1.3.3</a> D</span> | <span id="p2206">应用平台传递 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p2207">5368f224a74523e8d2e7399ea1638b37​aecfca824a3cc4dfdf77bf1fa905ac44</span> |
| <span id="p2208"><a href="https://pub.dev/api/archives/ffi-2.2.0.tar.gz">ffi 2.2.0</a> D</span> | <span id="p2209">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2210">6d7fd89431262d8f3125e81b50d3847a​091d846eafcd4fdb88dd06f36d705a45</span> |
| <span id="p2211"><a href="https://pub.dev/api/archives/file-7.0.1.tar.gz">file 7.0.1</a> D</span> | <span id="p2212">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2213">a3b4f84adafef897088c160faf7dfffb​7696046cb13ae90b508c2cbc95d3b8d4</span> |
| <span id="p2214"><a href="https://pub.dev/api/archives/file_selector-1.1.0.tar.gz">file&#95;selector 1.1.0</a> D</span> | <span id="p2215">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2216">bd15e43e9268db636b53eeaca9f56324​d1622af30e5c34d6e267649758c84d9a</span> |
| <span id="p2217"><a href="https://pub.dev/api/archives/file_selector_android-0.5.2+11.tar.gz">file&#95;selector&#95;android 0.5.2+11</a> D</span> | <span id="p2218">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2219">d670cd0ce77a2e785b18d8b4d0a8d6a2​22d6a813ec9b7ddf2790a1b4fb6fa92c</span> |
| <span id="p2220"><a href="https://pub.dev/api/archives/file_selector_ios-0.5.3+6.tar.gz">file&#95;selector&#95;ios 0.5.3+6</a> D</span> | <span id="p2221">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2222">97269e5307a0ab813b1fa2430bada0a9​6e0afb74848417f8676f64ba5de0051c</span> |
| <span id="p2223"><a href="https://pub.dev/api/archives/file_selector_linux-0.9.4+1.tar.gz">file&#95;selector&#95;linux 0.9.4+1</a> D</span> | <span id="p2224">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2225">da76400e7872ce7637ffdce12749ec24​169c25f6195c28372208e65a24bcd2ab</span> |
| <span id="p2226"><a href="https://pub.dev/api/archives/file_selector_macos-0.9.5+1.tar.gz">file&#95;selector&#95;macos 0.9.5+1</a> D</span> | <span id="p2227">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2228">d57c62362766b5e7ae739448650b66c6​aab7a68ba7ecc65e04018652645ae0f4</span> |
| <span id="p2229"><a href="https://pub.dev/api/archives/file_selector_platform_interface-2.7.0.tar.gz">file&#95;selector&#95;platform&#95;interface 2.7.0</a> D</span> | <span id="p2230">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2231">35e0bd61ebcdb91a3505813b055b09b7​9dfdc7d0aee9c09a7ba59ae4bb13dc85</span> |
| <span id="p2232"><a href="https://pub.dev/api/archives/file_selector_web-0.9.5.tar.gz">file&#95;selector&#95;web 0.9.5</a> D</span> | <span id="p2233">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2234">73181fbc5257776d8ecaa6a94ab3c8e9​20ad143b9132a6d984a9271dfc6928d3</span> |
| <span id="p2235"><a href="https://pub.dev/api/archives/file_selector_windows-0.9.3+6.tar.gz">file&#95;selector&#95;windows 0.9.3+6</a> D</span> | <span id="p2236">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2237">fbefc5fb92c6d3cbe8d284a2cd971b59​3bb07d2cd6da8557b81a862250b4acec</span> |
| <span id="p2238">flutter<br />0.0.0 D</span> | <span id="p2239">运行测试共享 / 直接生产<br />UNKNOWN<br />缺独立许可文本</span> | <span id="p2240">SDK占位 未取得实际SDK hash</span> |
| <span id="p2241"><a href="https://pub.dev/api/archives/flutter_acrylic-1.1.4.tar.gz">flutter&#95;acrylic 1.1.4</a> D</span> | <span id="p2242">应用平台传递 / 直接生产<br />MIT<br />许可文件已保存</span> | <span id="p2243">b3996dbde5abf5823cc9ead4cf2e5267​c3181f15585fe47ce4dc4472e7ec827a</span> |
| <span id="p2244"><a href="https://pub.dev/api/archives/flutter_lints-6.0.0.tar.gz">flutter&#95;lints 6.0.0</a> D</span> | <span id="p2245">局部图仅开发测试 / 直接开发<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2246">3105dc8492f6183fb076ccf1f351ac3d​60564bff92e20bfc4af9cc1651f4e7e1</span> |
| <span id="p2247">flutter&#95;localizations<br />0.0.0 D</span> | <span id="p2248">SDK / 直接生产<br />UNKNOWN<br />缺独立许可文本</span> | <span id="p2249">SDK占位 未取得实际SDK hash</span> |
| <span id="p2250">flutter&#95;test<br />0.0.0 D</span> | <span id="p2251">局部图仅开发测试 / 直接开发<br />UNKNOWN<br />缺独立许可文本</span> | <span id="p2252">SDK占位 未取得实际SDK hash</span> |
| <span id="p2253">flutter&#95;web&#95;plugins<br />0.0.0 D</span> | <span id="p2254">SDK / 直接生产<br />UNKNOWN<br />缺独立许可文本</span> | <span id="p2255">SDK占位 未取得实际SDK hash</span> |
| <span id="p2256"><a href="https://pub.dev/api/archives/go_router-18.0.1.tar.gz">go&#95;router 18.0.1</a> D</span> | <span id="p2257">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2258">008ab21d89d0de8ccd79586838f7533f​126c2d894f50bf25f2947888d3c225b5</span> |
| <span id="p2259"><a href="https://pub.dev/api/archives/html-0.15.7.tar.gz">html 0.15.7</a> D</span> | <span id="p2260">应用平台传递 / transitive<br />MIT<br />许可文件已保存</span> | <span id="p2261">43b67b8f43321ab066817dfac5619596​c98bb1b61624e77203bb4351785f9699</span> |
| <span id="p2262"><a href="https://pub.dev/api/archives/http-1.6.0.tar.gz">http 1.6.0</a> D</span> | <span id="p2263">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2264">87721a4a50b19c7f1d49001e51409bdd​c46303966ce89a65af4f4e6004896412</span> |
| <span id="p2265"><a href="https://pub.dev/api/archives/http_parser-4.1.2.tar.gz">http&#95;parser 4.1.2</a> D</span> | <span id="p2266">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2267">178d74305e7866013777bab2c3d87262​05dc5a4dd935297175b19a23a2e66571</span> |
| <span id="p2268"><a href="https://pub.dev/api/archives/intl-0.20.3.tar.gz">intl 0.20.3</a> D</span> | <span id="p2269">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2270">1ca20c894b1717686a2319b8548763d8​12bc0aabdac580420a44c5178c57a867</span> |
| <span id="p2271"><a href="https://pub.dev/api/archives/leak_tracker-11.0.2.tar.gz">leak&#95;tracker 11.0.2</a> D</span> | <span id="p2272">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2273">33e2e26bdd85a0112ec15400c8cbffea​70d0f9c3407491f672a2fad47915e2de</span> |
| <span id="p2274"><a href="https://pub.dev/api/archives/leak_tracker_flutter_testing-3.0.10.tar.gz">leak&#95;tracker&#95;flutter&#95;testing 3.0.10</a> D</span> | <span id="p2275">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2276">1dbc140bb5a23c75ea9c481122275610​4fbcd1a27173f0c34ca01e16bea473c1</span> |
| <span id="p2277"><a href="https://pub.dev/api/archives/leak_tracker_testing-3.0.2.tar.gz">leak&#95;tracker&#95;testing 3.0.2</a> D</span> | <span id="p2278">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2279">8d5a2d49f4a66b49744b23b018848400​d23e54caf9463f4eb20df3eb8acb2eb1</span> |
| <span id="p2280"><a href="https://pub.dev/api/archives/lints-6.1.0.tar.gz">lints 6.1.0</a> D</span> | <span id="p2281">局部图仅开发测试 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2282">12f842a479589fea194fe5c5a3095abc​7be0c1f2ddfa9a0e76aed1dbd26a87df</span> |
| <span id="p2283"><a href="https://pub.dev/api/archives/logging-1.3.0.tar.gz">logging 1.3.0</a> D</span> | <span id="p2284">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2285">c8245ada5f1717ed44271ed1c26b8ce8​5ca3228fd2ffdb75468ab01979309d61</span> |
| <span id="p2286"><a href="https://pub.dev/api/archives/macos_window_utils-1.9.1.tar.gz">macos&#95;window&#95;utils 1.9.1</a> D</span> | <span id="p2287">应用平台传递 / 直接生产<br />MIT<br />许可文件已保存</span> | <span id="p2288">cb918e1ff0b31fdaa5cd8631eded7c24​bd72e1025cf1f95c819e483f0057c652</span> |
| <span id="p2289"><a href="https://pub.dev/api/archives/matcher-0.12.20.tar.gz">matcher 0.12.20</a> D</span> | <span id="p2290">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2291">31bd099b47c10cd1aeb55146a2d46ce0​277630ecef3f7dae54ad7873f36696cd</span> |
| <span id="p2292"><a href="https://pub.dev/api/archives/material_color_utilities-0.13.0.tar.gz">material&#95;color&#95;utilities 0.13.0</a> D</span> | <span id="p2293">应用平台传递 / transitive<br />Apache-2.0<br />许可文件已保存</span> | <span id="p2294">9c337007e82b1889149c82ed242ed1cb​24a66044e30979c44912381e9be4c48b</span> |
| <span id="p2295"><a href="https://pub.dev/api/archives/material_ui-1.2.0.tar.gz">material&#95;ui 1.2.0</a> D</span> | <span id="p2296">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2297">fbfb53cab6c4629438feeade5f3d305f​72944bc9d9f25786b19106d32b80ec45</span> |
| <span id="p2298"><a href="https://pub.dev/api/archives/meta-1.18.3.tar.gz">meta 1.18.3</a> D</span> | <span id="p2299">运行测试共享 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2300">c82594181e3312f3d0695fc95aaaf775​8d75b8d4ae2bbecf223b9fd5109a059d</span> |
| <span id="p2301"><a href="https://pub.dev/api/archives/path-1.9.1.tar.gz">path 1.9.1</a> D</span> | <span id="p2302">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2303">75cca69d1490965be98c73ceaea117e8​a04dd21217b37b292c9ddbec0d955bc5</span> |
| <span id="p2304"><a href="https://pub.dev/api/archives/path_provider_linux-2.2.2.tar.gz">path&#95;provider&#95;linux 2.2.2</a> D</span> | <span id="p2305">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2306">58c2005f147315b11e9b4a7bc889cd52​03e250cba8e3f012dae259b4972b5c16</span> |
| <span id="p2307"><a href="https://pub.dev/api/archives/path_provider_platform_interface-2.1.3.tar.gz">path&#95;provider&#95;platform&#95;interface 2.1.3</a> D</span> | <span id="p2308">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2309">484838772624c3a4b94f1e44a3e19897​fee738f2d5c4ce448443b0417f7c9dda</span> |
| <span id="p2310"><a href="https://pub.dev/api/archives/path_provider_windows-2.3.0.tar.gz">path&#95;provider&#95;windows 2.3.0</a> D</span> | <span id="p2311">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2312">bd6f00dbd873bfb70d0761682da2b3a2​c2fccc2b9e84c495821639601d81afe7</span> |
| <span id="p2313"><a href="https://pub.dev/api/archives/platform-3.2.0.tar.gz">platform 3.2.0</a> D</span> | <span id="p2314">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2315">a36d119c13416516a7b5913fbe8af853​1e11633d784c550b2125f76c758524ec</span> |
| <span id="p2316"><a href="https://pub.dev/api/archives/plugin_platform_interface-2.1.8.tar.gz">plugin&#95;platform&#95;interface 2.1.8</a> D</span> | <span id="p2317">运行测试共享 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2318">4820fbfdb9478b1ebae27888254d4450​73732dae3d6ea81f0b7e06d5dedc3f02</span> |
| <span id="p2319"><a href="https://pub.dev/api/archives/shared_preferences-2.5.5.tar.gz">shared&#95;preferences 2.5.5</a> D</span> | <span id="p2320">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2321">c3025c5534b01739267eb7d76959bbc2​5a6d10f6988e1c2a3036940133dd10bf</span> |
| <span id="p2322"><a href="https://pub.dev/api/archives/shared_preferences_android-2.4.28.tar.gz">shared&#95;preferences&#95;android 2.4.28</a> D</span> | <span id="p2323">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2324">1e12aafe408aa50da80edfd679a2a6bf​63ba7ab37c7fa98286da459a757b3399</span> |
| <span id="p2325"><a href="https://pub.dev/api/archives/shared_preferences_foundation-2.5.7.tar.gz">shared&#95;preferences&#95;foundation 2.5.7</a> D</span> | <span id="p2326">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2327">2ec3934efa51e46117f23031cc141b8f​c878e8525b94ec1ea4f7f586cf1b47ea</span> |
| <span id="p2328"><a href="https://pub.dev/api/archives/shared_preferences_linux-2.4.1.tar.gz">shared&#95;preferences&#95;linux 2.4.1</a> D</span> | <span id="p2329">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2330">580abfd40f415611503cae30adf626e6​656dfb2f0cee8f465ece7b6defb40f2f</span> |
| <span id="p2331"><a href="https://pub.dev/api/archives/shared_preferences_platform_interface-2.4.2.tar.gz">shared&#95;preferences&#95;platform&#95;interface 2.4.2</a> D</span> | <span id="p2332">运行测试共享 / 直接开发<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2333">649dc798a33931919ea356c4305c2d1f​81619ea6e92244070b520187b5140ef9</span> |
| <span id="p2334"><a href="https://pub.dev/api/archives/shared_preferences_web-2.4.3.tar.gz">shared&#95;preferences&#95;web 2.4.3</a> D</span> | <span id="p2335">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2336">c49bd060261c9a3f0ff445892695d621​2ff603ef3115edbb448509d407600019</span> |
| <span id="p2337"><a href="https://pub.dev/api/archives/shared_preferences_windows-2.4.1.tar.gz">shared&#95;preferences&#95;windows 2.4.1</a> D</span> | <span id="p2338">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2339">94ef0f72b2d71bc3e700e025db371091​1bd51a71cefb65cc609dd0d9a982e3c1</span> |
| <span id="p2340">sky&#95;engine<br />0.0.0 D</span> | <span id="p2341">SDK / transitive<br />UNKNOWN<br />缺独立许可文本</span> | <span id="p2342">SDK占位 未取得实际SDK hash</span> |
| <span id="p2343"><a href="https://pub.dev/api/archives/source_span-1.10.2.tar.gz">source&#95;span 1.10.2</a> D</span> | <span id="p2344">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2345">56a02f1f4cd1a2d96303c0144c93bd6d​909eea6bee6bf5a0e0b685edbd4c47ab</span> |
| <span id="p2346"><a href="https://pub.dev/api/archives/stack_trace-1.12.2.tar.gz">stack&#95;trace 1.12.2</a> D</span> | <span id="p2347">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2348">277654b3034d17ac6f9f1cb5595db011​b1d5d41e8806866db28e0abaa101c490</span> |
| <span id="p2349"><a href="https://pub.dev/api/archives/stream_channel-2.1.4.tar.gz">stream&#95;channel 2.1.4</a> D</span> | <span id="p2350">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2351">969e04c80b8bcdf826f8f16579c7b14d​780458bd97f56d107d3950fdbeef059d</span> |
| <span id="p2352"><a href="https://pub.dev/api/archives/string_scanner-1.4.1.tar.gz">string&#95;scanner 1.4.1</a> D</span> | <span id="p2353">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2354">921cd31725b72fe181906c6a94d987c7​8e3b98c2e205b397ea399d4054872b43</span> |
| <span id="p2355"><a href="https://pub.dev/api/archives/term_glyph-1.2.2.tar.gz">term&#95;glyph 1.2.2</a> D</span> | <span id="p2356">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2357">7f554798625ea768a7518313e58f8389​1c7f5024f88e46e7182a4558850a4b8e</span> |
| <span id="p2358"><a href="https://pub.dev/api/archives/test_api-0.7.12.tar.gz">test&#95;api 0.7.12</a> D</span> | <span id="p2359">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2360">2a122cbe059f8b610d3a5415f42e255b​6c17b1f21eee1d960f31080237fb4f11</span> |
| <span id="p2361"><a href="https://pub.dev/api/archives/typed_data-1.4.0.tar.gz">typed&#95;data 1.4.0</a> D</span> | <span id="p2362">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2363">f9049c039ebfeb4cf7a7104a675823cd​72dba8297f264b6637062516699fa006</span> |
| <span id="p2364"><a href="https://pub.dev/api/archives/vector_math-2.4.0.tar.gz">vector&#95;math 2.4.0</a> D</span> | <span id="p2365">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2366">1d774bbdf6b72a0b12122fc1560c9c2d​2a67db5a4a4cc2bd8a5c990ab20e3188</span> |
| <span id="p2367"><a href="https://pub.dev/api/archives/video_player-2.14.0.tar.gz">video&#95;player 2.14.0</a> D</span> | <span id="p2368">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2369">8c837b570dccb9ae6ff73d2e0b03c7e7​08bfefd3bd1194faa7f3e7f200dfc399</span> |
| <span id="p2370"><a href="https://pub.dev/api/archives/video_player_android-2.12.2.tar.gz">video&#95;player&#95;android 2.12.2</a> D</span> | <span id="p2371">传递 非当前Android/Linux平台 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2372">d27054dea34d748a44f06d433a57005d​2aac69944485b0abbaed3303dbcfa3f1</span> |
| <span id="p2373"><a href="https://pub.dev/api/archives/video_player_avfoundation-2.12.0.tar.gz">video&#95;player&#95;avfoundation 2.12.0</a> D</span> | <span id="p2374">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2375">2fc56e537324a19eb649fca991aa308a​c961b5406292876fa657b062de461fd8</span> |
| <span id="p2376"><a href="https://pub.dev/api/archives/video_player_platform_interface-6.9.0.tar.gz">video&#95;player&#95;platform&#95;interface 6.9.0</a> D</span> | <span id="p2377">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2378">92c0fbabe20c788e71fd10d26cea998d​0d253282e65d145aed0818731cf593ce</span> |
| <span id="p2379"><a href="https://pub.dev/api/archives/video_player_web-2.4.0.tar.gz">video&#95;player&#95;web 2.4.0</a> D</span> | <span id="p2380">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2381">9f3c00be2ef9b76a95d94ac5119fb843​dca6f2c69e6c9968f6f2b6c9e7afbdeb</span> |
| <span id="p2382"><a href="https://pub.dev/api/archives/video_player_win-3.3.0.tar.gz">video&#95;player&#95;win 3.3.0</a> D</span> | <span id="p2383">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2384">df03760c1498ee0c0efe2688b302c331​acf46489e9821761d1adb137148502f1</span> |
| <span id="p2385"><a href="https://pub.dev/api/archives/vm_service-15.3.0.tar.gz">vm&#95;service 15.3.0</a> D</span> | <span id="p2386">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2387">5f37239c4851efcef929cea7824e76df​7f2f0970aef85d66bbc430afa40e72f0</span> |
| <span id="p2388"><a href="https://pub.dev/api/archives/web-1.1.1.tar.gz">web 1.1.1</a> D</span> | <span id="p2389">应用平台传递 / 直接生产<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2390">868d88a33d8a87b18ffc05f9f030ba32​8ffefba92d6c127917a2ba740f9cfe4a</span> |
| <span id="p2391"><a href="https://pub.dev/api/archives/xdg_directories-1.1.0.tar.gz">xdg&#95;directories 1.1.0</a> D</span> | <span id="p2392">应用平台传递 / transitive<br />BSD-3-Clause<br />许可文件已保存</span> | <span id="p2393">7a3f37b05d989967cdddcbb571f1ea83​4867ae2faa29725fd085180e0883aa15</span> |

<span id="p2394"><br /></span>

## <span id="p2395">附录三 服务与原生接入身份账</span>

<!-- table-06 -->
| <span id="p2396"><strong>适配项与源级状态</strong></span> | <span id="p2397"><strong>入口及源码目标模板</strong></span> | <span id="p2398"><strong>源文件SHA256</strong></span> |
| --- | --- | --- |
| <span id="p2399">JiguangCollector<br />工厂已实现 未见业务caller</span> | <span id="p2400">ad&#95;intelligence/platforms/jiguang.py:72<br />运行 未观察<br />目标模板 https://ad.xiaohongshu.com; https://ad.xiaohongshu.com/</span> | <span id="p2401">A/B共同<br />13b6a38d6e4421ae9822671b7f193fbd​f80e803a942da014ae3f94135dac11ec</span> |
| <span id="p2402">OceanEngineCollector<br />工厂已实现 未见业务caller</span> | <span id="p2403">ad&#95;intelligence/platforms/ocean&#95;engine.py:69<br />运行 未观察<br />目标模板 https://api.oceanengine.com/open&#95;api</span> | <span id="p2404">A/B共同<br />96503e12a469703fecb757334eb6fd86​58aabda462d9c5c3686f57936411148d</span> |
| <span id="p2405">MetaAdsCollector<br />工厂已实现 未见业务caller</span> | <span id="p2406">ad&#95;intelligence/platforms/meta&#95;ads.py:74<br />运行 未观察<br />目标模板 https://graph.facebook.com</span> | <span id="p2407">A/B共同<br />b33d0e26ccc8b6c8190b5695c5e9bc14​c3462d135ed1e70442a59b8325b290ed</span> |
| <span id="p2408">XAdsCollector<br />工厂已实现 未见业务caller</span> | <span id="p2409">ad&#95;intelligence/platforms/x&#95;ads.py:82<br />运行 未观察<br />目标模板 https://api.x.com</span> | <span id="p2410">A/B共同<br />7d334f082eded37751855b4fc37b8020​08573be389f476a302ef6f6eac679b80</span> |
| <span id="p2411">FacebookAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2412">lumenis/adapters/facebook.py:32<br />运行 未观察<br />目标模板 https://www.facebook.com/; https://www.facebook.com/search/top</span> | <span id="p2413">A/B共同<br />a568d5fdfd2c73a2fa4c86b8585bc50d​158da9d48967f5144ffff1ff3c7984c9</span> |
| <span id="p2414">BingSearchAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2415">lumenis/adapters/bing&#95;search.py:7<br />运行 未观察<br />目标模板 https://www.bing.com/search</span> | <span id="p2416">A/B共同<br />f9ebece2343b769798b964a7acc29edd​cad2a64c553c5ff6be6af1ae8c3db89d</span> |
| <span id="p2417">SogouWechatAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2418">lumenis/adapters/sogou&#95;wechat.py:48<br />运行 未观察<br />目标模板 https://weixin.sogou.com; https://weixin.sogou.com/; https://weixin.sogou.com/weixin</span> | <span id="p2419">A/B共同<br />6cf8bbb22982468eb205ddea4291cfcd​301ec571023cbb0b10d5dd1d663b79a5</span> |
| <span id="p2420">XAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2421">lumenis/adapters/x&#95;platform.py:86<br />运行 未观察<br />目标模板 http://127.0.0.1; https://; https://x.com; https://x.com/; https://x.com/i/web/status/; https://x.com/search</span> | <span id="p2422">A/B共同<br />54ba8d9aa04167991f1c95e37e502cad​abb8401424cfcf555b647fe7cb7165b9</span> |
| <span id="p2423">WeiboAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2424">lumenis/adapters/weibo.py:38<br />运行 未观察<br />目标模板 https://m.weibo.cn/; https://m.weibo.cn/api/comments/show; https://m.weibo.cn/api/container/getIndex; https://m.weibo.cn/status/; https://m.weibo.cn/statuses/show; https://m.weibo.cn/u/</span> | <span id="p2425">A/B共同<br />cc8ef14747e81c126d7d9aa068fc662e​71eb135403c7806f461d614902d50c64</span> |
| <span id="p2426">SmzdmAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2427">lumenis/adapters/smzdm.py:7<br />运行 未观察<br />目标模板 https://search.smzdm.com/</span> | <span id="p2428">A/B共同<br />3498b80df6642cce014cf55f1808413d​33f507476dc8807e37ebada7621ff91f</span> |
| <span id="p2429">JiguangAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2430">lumenis/adapters/jiguang.py:27<br />运行 未观察<br />目标模板 https://www.jiguang.cn/</span> | <span id="p2431">A/B共同<br />ba24a51f8304bcffbc06db493b5ba172​657d9f692c5732cbbe8250f49f9ed598</span> |
| <span id="p2432">GoogleAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2433">lumenis/adapters/google.py:29<br />运行 未观察<br />目标模板 http://127.0.0.1; https://www.google.com; https://www.google.com/; https://www.google.com/search</span> | <span id="p2434">A/B共同<br />6f948e9ed7dc4f420d005633bb0e4566​166e6c07f987397fdacb9d20b653586d</span> |
| <span id="p2435">BaiduSearchAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2436">lumenis/adapters/baidu&#95;search.py:7<br />运行 未观察<br />目标模板 https://www.baidu.com/s</span> | <span id="p2437">A/B共同<br />78ab86b3960f4c1597b26de637e161aa​a51e4bac8ed7ed654110ca4d060971e4</span> |
| <span id="p2438">DouyinAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2439">lumenis/adapters/douyin.py:106<br />运行 未观察<br />目标模板 http://127.0.0.1; https://www.douyin.com/search/; https://www.douyin.com/user/; https://www.douyin.com/video/</span> | <span id="p2440">A/B共同<br />ba9f2461fd3a05aee0477e407509d2e0​8dbe466dd282efdd39fec7bd53014675</span> |
| <span id="p2441">BilibiliAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2442">lumenis/adapters/bilibili.py:35<br />运行 未观察<br />目标模板 https://api.bilibili.com/x/space/acc/info; https://api.bilibili.com/x/v2/reply; https://api.bilibili.com/x/web-interface/search/type; https://api.bilibili.com/x/web-interface/view; https://space.bilibili.com/; https://www.bilibili.com/; https://www.bilibili.com/video/</span> | <span id="p2443">A/B共同<br />53984d571bfba0886c3f7a878c810eb1​5be867c564b0085348d3523013dc1e8a</span> |
| <span id="p2444">ZhihuAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2445">lumenis/adapters/zhihu.py:38<br />运行 未观察<br />目标模板 https://www.zhihu.com; https://www.zhihu.com/; https://www.zhihu.com/api/v4/; https://www.zhihu.com/api/v4/answers/; https://www.zhihu.com/api/v4/articles/; https://www.zhihu.com/api/v4/members/; https://www.zhihu.com/api/v4/questions/; https://www.zhihu.com/api/v4/search&#95;v3; https://www.zhihu.com/people/; https://www.zhihu.com/question/; https://www.zhihu.com/search; https://zhuanlan.zhihu.com/p/</span> | <span id="p2446">A/B共同<br />268bc1080d5b301709c51ef71b8acc33​22365a0061765dccd4463631cf6cca68</span> |
| <span id="p2447">DianpingAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2448">lumenis/adapters/dianping.py:7<br />运行 未观察<br />目标模板 https://www.dianping.com; https://www.dianping.com/; https://www.dianping.com/search/keyword/1/0&#95;</span> | <span id="p2449">A/B共同<br />4a2297fbd06e1351cb6f62b5b405dbb0​049d90baaae66cbb088f2faf1d6e4e90</span> |
| <span id="p2450">InstagramAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2451">lumenis/adapters/instagram.py:32<br />运行 未观察<br />目标模板 https://; https://instagram.com; https://www.instagram.com; https://www.instagram.com/; https://www.instagram.com/explore/tags/; https://www.instagram.com/p/</span> | <span id="p2452">A/B共同<br />1ad803bdf026e611cea0ffb66f6f53e4​b008afd57123d4ea83fc1a1558c343f2</span> |
| <span id="p2453">SogouSearchAdapter<br />旧兼容链注册 见A/B差异</span> | <span id="p2454">lumenis/adapters/sogou&#95;search.py:54<br />运行 未观察<br />目标模板 https://news.sogou.com/; https://news.sogou.com/news; https://www.sogou.com; https://www.sogou.com/; https://www.sogou.com/link; https://www.sogou.com/web</span> | <span id="p2455">A/B共同<br />3dc2a7e7788845e701b0545cc794ad08​60c0488adc3cbdb0a61bf439aafb08bd</span> |
| <span id="p2456">FacebookAdapter<br />默认导入注册</span> | <span id="p2457">lumenis/system/collector/adapters/facebook.py:12<br />运行 未观察</span> | <span id="p2458">A/B共同<br />aedaf304f7fa3905a087f1fbe3e0edfb​19ad000df60eec85a2f1b43f93f44957</span> |
| <span id="p2459">XHSAppTopicAdapter<br />已注册骨架 发现空指标无</span> | <span id="p2460">lumenis/system/collector/adapters/xhs&#95;app&#95;topic.py:36<br />运行 未观察</span> | <span id="p2461">A/B共同<br />679aea9167b3ba7eef3e785aef6e82fb​ce69f6a95dc0b421e882b44fc4811353</span> |
| <span id="p2462">LinkedInAdapter<br />仅计划schema 无采集实现</span> | <span id="p2463">lumenis/system/collector/adapters/linkedin.py:19<br />运行 未观察</span> | <span id="p2464">A 7f941db59d8004e81f08b19006d49773​06a558094ad31c09ea63aa47854b75ac<br />B c666aaab6d0f51e0a2f76e985d481d82​0559c3dedb35f17b392417d74c4193ef</span> |
| <span id="p2465">XiaohongshuAdapter<br />默认导入注册</span> | <span id="p2466">lumenis/system/collector/adapters/xhs.py:13<br />运行 未观察</span> | <span id="p2467">A/B共同<br />9e6ae79eb01e0c15f78ec8d352653bd2​9d37e1232d5c75f2dd2bf58d082d8634</span> |
| <span id="p2468">KuaishouAdapter<br />已注册委托 无默认backend</span> | <span id="p2469">lumenis/system/collector/adapters/kuaishou.py:9<br />运行 未观察</span> | <span id="p2470">A/B共同<br />dcc83399ece9b8237b25c67482976c28​01faf23248a882ca386f9aa10bf455f2</span> |
| <span id="p2471">GitHubAdapter<br />默认导入注册</span> | <span id="p2472">lumenis/system/collector/adapters/github.py:21<br />运行 未观察</span> | <span id="p2473">A/B共同<br />91379e4474ea64bee04205863df45593​84ed2f95814108943d6ed480d2515ffb</span> |
| <span id="p2474">RedditAdapter<br />仅计划schema 无采集实现</span> | <span id="p2475">lumenis/system/collector/adapters/reddit.py:19<br />运行 未观察</span> | <span id="p2476">A 7cc6d8d04da3828e32eec6a9ba6eb42b​bedfaa915776359e8b647bcdc9416644<br />B 5bb25551246b800aa9a67f21942ddf22​a2b74c9a73b466a80e2c71942afb950d</span> |
| <span id="p2477">WebRSSAdapter<br />默认导入注册</span> | <span id="p2478">lumenis/system/collector/adapters/web&#95;rss.py:10<br />运行 未观察</span> | <span id="p2479">A/B共同<br />a89615ab86a7af265cc4dc1c1a4dc74a​14750e99ca12aa1fc3587dcce862c44d</span> |
| <span id="p2480">XAdapter<br />默认导入注册</span> | <span id="p2481">lumenis/system/collector/adapters/x&#95;platform.py:19<br />运行 未观察</span> | <span id="p2482">A/B共同<br />9f409347174c72ddfbe778e0908c0698​7b958e7fc53c955305634a7cd62ddaf6</span> |
| <span id="p2483">PublicHttpAdapter<br />默认导入注册</span> | <span id="p2484">lumenis/system/collector/adapters/public&#95;http.py:122<br />运行 未观察<br />目标模板 http://; https://</span> | <span id="p2485">A bc9c8fbbc0de32dda82190350185c69b​d1c7d36e1ce90914e4ba5756d5dca833<br />B 933e4f6a102e7474e11ed6ea52d14832​4b94f113522ecfbae924b0c4213a3b69</span> |
| <span id="p2486">WeiboAdapter<br />默认导入注册</span> | <span id="p2487">lumenis/system/collector/adapters/weibo.py:12<br />运行 未观察</span> | <span id="p2488">A/B共同<br />3a084385f6565dcd5e1f976527a9bcff​48ed59437d77556ebb44f55e885a5b4d</span> |
| <span id="p2489">YouTubeAdapter<br />仅计划schema 无采集实现</span> | <span id="p2490">lumenis/system/collector/adapters/youtube.py:19<br />运行 未观察</span> | <span id="p2491">A dad777939244e08e5e40ffb76cd69c2f​ebb0fc50ea1948793eb74269c7ac8c1b<br />B e9e7a3fdcffaad22b1053967faf7f417​93ad71448d8aa5085fe8d1054828f21d</span> |
| <span id="p2492">TikTokAdapter<br />仅计划schema 无采集实现</span> | <span id="p2493">lumenis/system/collector/adapters/tiktok.py:19<br />运行 未观察</span> | <span id="p2494">A a216934636af1562f2390f265fc7c143​133b5fc7748aa28f3b2a7383264f395b<br />B a7a8f23e9f8b25260d66cd4584f01456​8ba4ff9ff0b509351ab516bbf45bd26d</span> |
| <span id="p2495">AtomAdapter<br />默认导入注册</span> | <span id="p2496">lumenis/system/collector/adapters/web&#95;atom.py:33<br />运行 未观察</span> | <span id="p2497">A/B共同<br />4c94e3a886d1488dffca99a01ce58e64​5963776c2a3852cafb2535f5d2245fa5</span> |
| <span id="p2498">DouyinAdapter<br />默认导入注册</span> | <span id="p2499">lumenis/system/collector/adapters/douyin.py:24<br />运行 未观察</span> | <span id="p2500">A/B共同<br />f0526316ce258320687918ca99525898​432fd2149c007bb24bc171521b41c2de</span> |
| <span id="p2501">BilibiliAdapter<br />默认导入注册</span> | <span id="p2502">lumenis/system/collector/adapters/bilibili.py:12<br />运行 未观察</span> | <span id="p2503">A/B共同<br />bd1ef1e968dbbabdc17f1b95de2d9401​ac1c41605382203f68267facbe45a0c7</span> |
| <span id="p2504">ChannelsAdapter<br />仅计划schema 无采集实现</span> | <span id="p2505">lumenis/system/collector/adapters/channels.py:20<br />运行 未观察</span> | <span id="p2506">A bb4e439b9ce83414208d877c8ad094db​1650683d19d624a8b5f2df524a968910<br />B 119da37032bf96e35f329c7b6d7b6040​91b4ead387657c25af941b7a151bd686</span> |
| <span id="p2507">WechatPublicAdapter<br />模块注册 需核惰性caller</span> | <span id="p2508">lumenis/system/collector/adapters/wechat.py:112<br />运行 未观察<br />目标模板 https://weixin.sogou.com/weixin</span> | <span id="p2509">A/B共同<br />544c8dfa1fa8a62bc7f8d87b3fbcc61d​d262adeaf74ec54dcb1861a697234e67</span> |
| <span id="p2510">ZhihuAdapter<br />默认导入注册</span> | <span id="p2511">lumenis/system/collector/adapters/zhihu.py:12<br />运行 未观察</span> | <span id="p2512">A/B共同<br />37c2ee86e52e46f26ba5f297bfd978bf​d50b3df8fd06c80c499e1e11033d6c1f</span> |
| <span id="p2513">SitemapAdapter<br />默认导入注册</span> | <span id="p2514">lumenis/system/collector/adapters/sitemap.py:16<br />运行 未观察</span> | <span id="p2515">A/B共同<br />0518b3eac7103be2077da65a2f89581b​42fc0f25fa92f017162a798d8d87066d</span> |
| <span id="p2516">InstagramAdapter<br />默认导入注册</span> | <span id="p2517">lumenis/system/collector/adapters/instagram.py:104<br />运行 未观察</span> | <span id="p2518">A/B共同<br />1db211062fce4c1bd9004ebb6a5601f9​9aa62d1826598d3d9528a7e2a015ee27</span> |
| <span id="p2519">Groq/user&#95;api<br />A任意HTTPS B固定Groq及权限</span> | <span id="p2520">lumenis/system/ai&#95;gateway/user&#95;api&#95;adapter.py:<br />运行 未观察<br />目标模板 https://api.groq.com/openai/v1</span> | <span id="p2521">A f446526bc7cec36bd44572a285bf1994​be6ba8cbbbe40c79e155158bfee1a0ca<br />B 63058e51509d2da54ba5cbe68df52e80​08b9c9826e5492537cf95f0bec22d64e</span> |
| <span id="p2522">Owned AI executor<br />绑定实现 当前未验</span> | <span id="p2523">lumenis/system/ai&#95;gateway/owned&#95;service.py:<br />运行 未观察</span> | <span id="p2524">A 08b44550fb525b0776639e01eddaece4​6089ef03a86766f00727b33826b69947<br />B d595e151b075c71a5e0f861006c3721f​ddd5ea16c98fb2358418c4faef9ca154</span> |
| <span id="p2525">Whisper ASR<br />A base B加small评估</span> | <span id="p2526">lumenis/system/ai&#95;gateway/owned&#95;speech.py:<br />运行 未观察</span> | <span id="p2527">A 72f9ac5fa89fae0879f58bf07a882387​b7227239d1fef3ebd61e0c0b7f369885<br />B 5c1df750f0b255543df9102671ded452​d63c12aaf9c1161389723fff5f294523</span> |
| <span id="p2528">gpt-oss/Unsloth training<br />固定准入实现 权重未恢复</span> | <span id="p2529">lumenis/system/ai&#95;gateway/owned&#95;training.py:<br />运行 未观察<br />目标模板 https://developers.openai.com/cookbook/articles/gpt-oss/fine-tune-transfomers; https://huggingface.co/</span> | <span id="p2530">A/B共同<br />fea9d52ae119b13247b961bd4c80c311​8ede8866b25664e2c0d16a950dfdcff3</span> |
| <span id="p2531">OSAI Agent<br />外仓未固定 继承环境</span> | <span id="p2532">agent&#95;runtime&#95;adapter.py:<br />运行 未观察</span> | <span id="p2533">A/B共同<br />fa433a13bff12524094dff4bf5399393​4f0072a1db22e44daab0526e452a3244</span> |
| <span id="p2534">OSAI Skills<br />外仓未固定 继承环境</span> | <span id="p2535">lumenis&#95;skill&#95;adapter.py:<br />运行 未观察</span> | <span id="p2536">A/B共同<br />9baa31c2da14ca9fa7fc79be778e875f​59007548c88baa71f599bc30e394c3fe</span> |
| <span id="p2537">GitHub Connector<br />产品连接器实现</span> | <span id="p2538">github&#95;connector.py:<br />运行 未观察<br />目标模板 https://api.github.com; https://github.com/login/oauth/authorize</span> | <span id="p2539">A/B共同<br />2da2814365ed9b0ff8d7fc0f77159861​44dcdd9cf7945ec37da1081cdbceac3a</span> |
| <span id="p2540">MCP discovery<br />stdio实现 无恢复Skill包</span> | <span id="p2541">mcp&#95;discovery.py:<br />运行 未观察</span> | <span id="p2542">A bb487a0422b0ab9c1da1457d9fba434b​776a3ecb797c5945d9f89fb205ed8260<br />B 375e6c9a91b670d4b7459e47c2578199​a561078e0d2fa78203ea48697ddd3d39</span> |
| <span id="p2543">MCP Skill runtime<br />本地安装门禁 无恢复Skill包</span> | <span id="p2544">mcp&#95;skill&#95;runtime.py:<br />运行 未观察</span> | <span id="p2545">A 847e0c2c4511f450112a4c0e324d7cb7​9558eb090a4cdac6c81cf8892dcf44aa<br />B 76b60306ca14719e5245fff63db54093​07301a7f3204511944b771cfc32f6dd4</span> |
| <span id="p2546">SMTP invitation<br />A直接SMTP B默认无发送adapter</span> | <span id="p2547">kos&#95;ops.py:<br />运行 未观察</span> | <span id="p2548">A 88dc242d901866b67e9753be2f4654ee​70f705aca3e6067b7419acacb59c8a02<br />B 36ffc2c053599b5bc385ce0d2d7582a2​791ce7d9cbd9271655c5e0dc57436f90</span> |
| <span id="p2549">Email verification<br />占位 始终阻断</span> | <span id="p2550">account/verification.py:<br />运行 未观察</span> | <span id="p2551">A/B共同<br />794832aa9f4c1accd80ccff73fb0732e​13fabecd74bea2ddb3e7b86b110c8605</span> |
| <span id="p2552">SMS verification<br />占位 始终阻断</span> | <span id="p2553">account/verification.py:<br />运行 未观察</span> | <span id="p2554">A/B共同<br />794832aa9f4c1accd80ccff73fb0732e​13fabecd74bea2ddb3e7b86b110c8605</span> |
| <span id="p2555">FFmpeg/ffprobe<br />子进程 依赖运行时路径</span> | <span id="p2556">lumenis/shared/content&#95;creation/rendering.py:<br />运行 未观察</span> | <span id="p2557">A f7b511ddeeccb076794e274763f1255c​914013c92f225ed11999bdb30d13e9af<br />B ecf4895a394166c40d436d1a4733ccd8​4ef7bac1291012dac30cd42075fa6a67</span> |
| <span id="p2558">LibreOffice DOC<br />可选本地转换</span> | <span id="p2559">lumenis/importer/parser.py:<br />运行 未观察</span> | <span id="p2560">A e4360cc9d9dc554422c1e08b35a4fbc9​8c482c8b3ffff6fc853e446238a677ed<br />B bdee7f2f23f1307d8396826f64e08f02​8e1f7cad120303c3a74c6ade88cb07b5</span> |
| <span id="p2561">Git package runtime<br />GitHub源码取回实现</span> | <span id="p2562">lumenis/shared/agents/skills/package&#95;runtime.py:<br />运行 未观察<br />目标模板 https://</span> | <span id="p2563">A/B共同<br />a38cb1873465b2a9b73817551531305d​0cc0a0606ae9f9ae938d6b22507a0005</span> |
| <span id="p2564">Git version center<br />版本owner注册</span> | <span id="p2565">lumenis/version&#95;center/git&#95;manager.py:<br />运行 未观察<br />目标模板 http://127.0.0.1</span> | <span id="p2566">A/B共同<br />63a7be425cbdfb04737153f87e3d0eb5​46fca9583b29b0bc64fbad05ea87daac</span> |
| <span id="p2567">SSH training<br />需明确endpoint及源码pin</span> | <span id="p2568">lumenis/system/ai&#95;gateway/owned&#95;training&#95;ssh.py:<br />运行 未观察</span> | <span id="p2569">A/B共同<br />149e61799607568c91ec89f48193be19​ba08af14614ab5fa06c051fc24250a0d</span> |
| <span id="p2570">eSpeak NG formant<br />B独有实现</span> | <span id="p2571">lumenis/shared/content&#95;creation/offline&#95;formant&#95;speech.py:<br />运行 未观察<br />目标模板 https://github.com/espeak-ng/espeak-ng; https://github.com/espeak-ng/espeak-ng/blob/master/docs/languages.md</span> | <span id="p2572">A 无文件<br />B f32f6607dfd5281114a65c1932ff2261​24b0063d379d597fe0396394ef0858ab</span> |
| <span id="p2573">Browser Use<br />延期诊断 无执行桥</span> | <span id="p2574">lumenis/system/browser/runtime/browser&#95;use&#95;adapter.py:<br />运行 未观察</span> | <span id="p2575">A/B共同<br />fd3b7d4fb22e5189c7ec93336a6f81e3​e48570e6d76485ed3345049a46b468b4</span> |
| <span id="p2576">WeComBotChannel<br />配置驱动 未见外部业务caller</span> | <span id="p2577">wechat&#95;notifier.py:84<br />运行 未观察<br />目标模板 http://www.pushplus.plus/send; https://api.weixin.qq.com/cgi-bin/message/template/send; https://api.weixin.qq.com/cgi-bin/token; https://sctapi.ftqq.com/</span> | <span id="p2578">A 无文件<br />B 无文件</span> |
| <span id="p2579">ServerChanChannel<br />配置驱动 未见外部业务caller</span> | <span id="p2580">wechat&#95;notifier.py:143<br />运行 未观察<br />目标模板 http://www.pushplus.plus/send; https://api.weixin.qq.com/cgi-bin/message/template/send; https://api.weixin.qq.com/cgi-bin/token; https://sctapi.ftqq.com/</span> | <span id="p2581">A 无文件<br />B 无文件</span> |
| <span id="p2582">PushPlusChannel<br />配置驱动 未见外部业务caller</span> | <span id="p2583">wechat&#95;notifier.py:186<br />运行 未观察<br />目标模板 http://www.pushplus.plus/send; https://api.weixin.qq.com/cgi-bin/message/template/send; https://api.weixin.qq.com/cgi-bin/token; https://sctapi.ftqq.com/</span> | <span id="p2584">A 无文件<br />B 无文件</span> |
| <span id="p2585">WeChatOfficialAccountChannel<br />配置驱动 未见外部业务caller</span> | <span id="p2586">wechat&#95;notifier.py:231<br />运行 未观察<br />目标模板 http://www.pushplus.plus/send; https://api.weixin.qq.com/cgi-bin/message/template/send; https://api.weixin.qq.com/cgi-bin/token; https://sctapi.ftqq.com/</span> | <span id="p2587">A 无文件<br />B 无文件</span> |
| <span id="p2588">zhipu<br />退休 禁止fallback</span> | <span id="p2589">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2590">A 无文件<br />B 无文件</span> |
| <span id="p2591">ollama<br />退休 禁止fallback</span> | <span id="p2592">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2593">A 无文件<br />B 无文件</span> |
| <span id="p2594">lmstudio<br />退休 禁止fallback</span> | <span id="p2595">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2596">A 无文件<br />B 无文件</span> |
| <span id="p2597">llama&#95;cpp<br />退休 禁止fallback</span> | <span id="p2598">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2599">A 无文件<br />B 无文件</span> |
| <span id="p2600">ark<br />退休 禁止fallback</span> | <span id="p2601">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2602">A 无文件<br />B 无文件</span> |
| <span id="p2603">qwen<br />退休 禁止fallback</span> | <span id="p2604">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2605">A 无文件<br />B 无文件</span> |
| <span id="p2606">openai<br />退休 禁止fallback</span> | <span id="p2607">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2608">A 无文件<br />B 无文件</span> |
| <span id="p2609">deepseek<br />退休 禁止fallback</span> | <span id="p2610">lumenis/system/ai&#95;gateway/providers.py:19:<br />运行 NOT&#95;PROBED</span> | <span id="p2611">A 无文件<br />B 无文件</span> |
| <span id="p2612">Overture Places<br />本地Parquet 此解析器不联网</span> | <span id="p2613">lumenis/system/collector/adapters/overture&#95;places.py:<br />运行 未观察</span> | <span id="p2614">A/B共同<br />dfd401bff3b7bdf6fbfe7dc2fb4732e8​badcf9665f584d18349d970a745b4644</span> |
| <span id="p2615">Public HTTPS fetch<br />共享网络边界源adapter</span> | <span id="p2616">lumenis/system/collector/adapters/public&#95;source.py:<br />运行 未观察<br />目标模板 http://; https://; https://dns.google/resolve</span> | <span id="p2617">A/B共同<br />f482bee782f7a6c92297b3d412501ac1​785f25000b390930830d29f3dcfcca71</span> |
| <span id="p2618">Secondary collection routing<br />公开原生捕获 惰性平台导入</span> | <span id="p2619">lumenis/system/collector/adapters/secondary&#95;collection.py:<br />运行 未观察<br />目标模板 http://; https://</span> | <span id="p2620">A 2b8886d7eb4a10a77ef85a6321d9939e​2e88485ccfdf96d045208ab68e939f3f<br />B 9f745515550e2f618aeb6da03d01bad0​c5d218ff16e4dde272f226eaeacd7b63</span> |

## <span id="p2621">附录四 历史环境记录及可还原传递片段</span>

<span id="p2622">以下只证明恢复证据里记录过这些环境状态。它们不是全量产品已接入清单，也不证明当前机器安装。Python完整传递锁和实际二进制闭包仍缺，须在获准目标环境补验。</span>

### <span id="p2623">target.freeze.txt</span>

<span id="p2624">证据SHA256 1c00a9c93653a42437ab5c4eecaf84a8​7d433b4b3f3d18a33e40282e7d2c15bf</span>

<span id="p2625">greenlet 3.2.4；playwright 1.55.0；pyee 13.0.0</span>

### <span id="p2626">shared.after.freeze.txt</span>

<span id="p2627">证据SHA256 b8be521df3106f2028b5b1ee2bb655b2​3aaa8e5bcd23a5554ff47b5c0ee5df3a</span>

<span id="p2628">anyio 4.15.1；APScheduler 3.11.3；arviz 0.22.0；attrs 26.1.0；beautifulsoup4 4.15.0；blinker 1.9.0；cachetools 7.2.3；certifi 2026.7.22；cffi 2.1.1；charset-normalizer 3.5.2；click 8.5.0；cloudpickle 3.1.2；cons 0.4.7；contourpy 1.4.0；cryptography 50.0.2；cycler 0.12.1；defusedxml 0.7.1；Deprecated 3.0.0；et&#95;xmlfile 2.0.0；etuples 0.3.10；feedparser 6.0.14；feedparser-sgmllib 2.1.0；filelock 4.2.0；Flask 3.1.3；flask-cors 6.0.5；Flask-Limiter 4.1.1；flatbuffers 25.12.19；fonttools 4.67.0；h11 0.16.0；h5netcdf 1.8.1；httpcore 1.0.9；httpx 0.28.1；idna 3.20；iniconfig 2.3.1；itsdangerous 2.2.0；Jinja2 3.1.6；joblib 1.6.0；jsonschema 4.26.0；jsonschema-specifications 2025.9.1；kiwisolver 1.5.1；limits 5.8.0；logical-unification 0.4.7；lxml 6.1.3；magika 0.6.3；markdown-it-py 4.2.0；markdownify 1.2.3；markitdown 0.1.8；MarkupSafe 3.0.4；matplotlib 3.11.2；mdurl 0.1.2；miniKanren 1.0.5；multipledispatch 1.0.0；networkx 3.5；numpy 2.5.4；onnxruntime 1.31.0；openpyxl 3.1.5；ordered-set 4.1.0；packaging 26.3；pandas 3.0.6；patsy 1.0.3；pdfminer.six 20260107；pdfplumber 0.11.10；pillow 13.0.0；pluggy 1.7.0；protobuf 7.36.2；psutil 7.2.2；pycparser 3.11；Pygments 2.21.0；pymc 5.25.1；pyparsing 3.3.3；pypdfium2 5.14.0；pytensor 2.31.7；pytest 9.1.1；python-dateutil 2.9.0.post0；python-docx 1.2.0；python-dotenv 1.2.4；python-pptx 1.0.2；PyYAML 6.0.3；referencing 0.37.0；reportlab 5.0.1；requests 2.34.2；rich 15.0.0；rpds-py 2026.9.1；ruptures 1.1.10；schedule 1.2.2；scikit-learn 1.7.2；scipy 1.18.1；setuptools 84.0.0；six 1.17.0；soupsieve 3.0.3；statsmodels 0.14.6；threadpoolctl 3.7.0；toolz 1.2.0；typing&#95;extensions 4.16.0；tzlocal 5.4.4；urllib3 2.8.0；websocket-client 1.9.2；Werkzeug 3.1.9；wrapt 2.5.1；xarray 2026.9.0；xarray-einstats 0.11.0；xlrd 2.0.2；xlsxwriter 3.2.9；xlwt 1.3.0</span>

### <span id="p2629">数学独立环境十九个安装记录</span>

<span id="p2630">ortools 9.15.6755；许可元数据 Apache 2.0</span>

<span id="p2631">Requires-Dist absl-py&gt;=2.0.0; numpy&gt;=2.0.2; pandas&gt;=2.0.0; protobuf&lt;6.34,&gt;=6.33.1; typing-extensions&gt;=4.12; immutabledict&gt;=3.0.0</span>

<span id="p2632">wheel SHA256 033836c0eb33bc72697a299e0caedbb2​5fc9d1cee0b13832d69cb30405f57b3e</span>

<span id="p2633">protobuf 6.33.6；许可元数据 3-Clause BSD License</span>

<span id="p2634">Requires-Dist </span>

<span id="p2635">wheel SHA256 e9db7e292e0ab79dd108d7f1a94fe316​01ce1ee3f7b79e0692043423020b0593</span>

<span id="p2636">absl-py 2.5.1；许可元数据 Apache-2.0</span>

<span id="p2637">Requires-Dist </span>

<span id="p2638">wheel SHA256 721200f2f0e9960f2ca9dc3a2a706b20​1f5f75d812c158f059cbbe29eeafbdb8</span>

<span id="p2639">immutabledict 4.3.1；许可元数据 MIT</span>

<span id="p2640">Requires-Dist </span>

<span id="p2641">wheel SHA256 c9facdc0ff30fdb8e35bd16532026cac​472a549e182c94fa201b51b25e4bf7bf</span>

<span id="p2642">bertopic 0.17.4；许可元数据 MIT License Copyright (c) 2024, Maarten P. Grootendorst Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. </span>

<span id="p2643">Requires-Dist hdbscan&gt;=0.8.29; umap-learn&gt;=0.5.0; numpy&gt;=1.20.0; pandas&gt;=1.1.5; plotly&gt;=4.7.0; scikit-learn&gt;=1.0; sentence-transformers&gt;=0.4.1; tqdm&gt;=4.41.1; llvmlite&gt;0.36.0; datamapplot&gt;=0.1; extra == "datamap"; matplotlib&gt;=3.8; extra == "datamap"; bertopic&#91;docs,test&#93;; extra == "dev"; mkdocs==1.5.3; extra == "docs"; mkdocs-material==9.5.18; extra == "docs"; mkdocstrings-python==1.10.0; extra == "docs"; mkdocstrings==0.24.3; extra == "docs"; fastembed&gt;=0.6.0; extra == "fastembed"; flair&gt;=0.7; extra == "flair"; torch&gt;=1.4.0; extra == "flair"; transformers&gt;=3.5.1; extra == "flair"; gensim&gt;=4.0.0; extra == "gensim"; spacy&gt;=3.0.1; extra == "spacy"; pytest&gt;=5.4.3; extra == "test"; pytest-cov&gt;=2.6.1; extra == "test"; ruff~=0.14.0; extra == "test"; tensorflow; extra == "use"; tensorflow&#95;hub; extra == "use"; tensorflow&#95;text; extra == "use"; accelerate&gt;=0.19.0; extra == "vision"; Pillow&gt;=9.2.0; extra == "vision"</span>

<span id="p2644">wheel SHA256 0dbe7ee22c18fb76efe7f4fbf3a14b51​c1e67d9fccc569e3f81e75b8f32646d1</span>

<span id="p2645">hdbscan 0.8.44；许可元数据 BSD</span>

<span id="p2646">Requires-Dist numpy&lt;3,&gt;=1.20; scipy&gt;=1.0; scikit-learn&gt;=1.6; joblib&gt;=1.0</span>

<span id="p2647">wheel SHA256 d67f2b3628a80764a07fff3a994df2c6​b2d9a6b9c8024edde7b36c184f6657f6</span>

<span id="p2648">umap-learn 0.5.12；许可元数据 BSD</span>

<span id="p2649">Requires-Dist numpy&gt;=1.23; scipy&gt;=1.3.1; scikit-learn&gt;=1.6; numba&gt;=0.51.2; pynndescent&gt;=0.5; tqdm; pandas; extra == "plot"; matplotlib; extra == "plot"; datashader; extra == "plot"; bokeh; extra == "plot"; holoviews; extra == "plot"; colorcet; extra == "plot"; seaborn; extra == "plot"; scikit-image; extra == "plot"; dask; extra == "plot"; tensorflow&gt;=2.1; extra == "parametric-umap"; tbb&gt;=2019.0; extra == "tbb"; pytest; extra == "test"</span>

<span id="p2650">wheel SHA256 f2a85d2a2adcb52b541bed9b27a23ca1​69b56bb1b23283abeebfb8dfb8a42fe5</span>

<span id="p2651">sentence-transformers 6.1.0；许可元数据 Apache-2.0</span>

<span id="p2652">Requires-Dist transformers&lt;6.0.0,&gt;=5.0.0; tokenizers&gt;=0.19; huggingface-hub&lt;2.0.0,&gt;=1.3.0; torch&gt;=2.2; numpy&gt;=1.24.0; scikit-learn&gt;=1.1.0; scipy&gt;=1.0.0; typing&#95;extensions&gt;=4.10.0; tqdm&gt;=4.0.0; transformers&#91;vision&#93;; extra == "image"; transformers&#91;audio&#93;; extra == "audio"; transformers&#91;video&#93;; extra == "video"; datasets&gt;=2.16.0; extra == "train"; accelerate&gt;=1.3.0; extra == "train"; optimum-onnx&#91;onnxruntime&#93;; extra == "onnx"; optimum-onnx&#91;onnxruntime-gpu&#93;; extra == "onnx-gpu"; optimum-intel&#91;openvino&#93;&gt;=2.0.0; extra == "openvino"; datasets&gt;=2.16.0; extra == "dev"; accelerate&gt;=1.3.0; extra == "dev"; pre-commit; extra == "dev"; pytest; extra == "dev"; pytest-cov; extra == "dev"; pytest-env; extra == "dev"; pytest-subtests; extra == "dev"; pytest-xdist; extra == "dev"; peft; extra == "dev"; transformers&#91;audio,video,vision&#93;; extra == "dev"</span>

<span id="p2653">wheel SHA256 eb8122f4d180f552eda26dc3d77e84e8​c11dc2b1d456a406b9f24abb70ceeadd</span>

<span id="p2654">transformers 5.20.1；许可元数据 Apache 2.0 License</span>

<span id="p2655">Requires-Dist huggingface-hub&lt;3.0,&gt;=1.31.0; numpy&gt;=1.17; packaging&gt;=20.0; pyyaml&gt;=5.1; regex&gt;=2025.10.22; tokenizers&lt;0.24.0,&gt;=0.23.1; typer; safetensors&gt;=0.8.0; tqdm&gt;=4.60; torch&gt;=2.6; extra == "torch"; accelerate&gt;=1.1.0; extra == "torch"; torchvision; extra == "vision"; Pillow&lt;=15.0,&gt;=10.0.1; extra == "vision"; torchaudio; extra == "audio"; librosa; extra == "audio"; pyctcdecode&gt;=0.4.0; extra == "audio"; phonemizer; extra == "audio"; kenlm; extra == "audio"; av; extra == "video"; timm&gt;=1.0.23; extra == "timm"; datasets&gt;=2.15.0; extra == "quality"; ruff==0.14.10; extra == "quality"; GitPython&lt;3.1.19; extra == "quality"; urllib3&lt;2.0.0; extra == "quality"; libcst; extra == "quality"; rich; extra == "quality"; ty==0.0.20; extra == "quality"; tomli; extra == "quality"; transformers-mlinter==0.1.5; extra == "quality"; hf-doc-builder; extra == "docs"; kernels&lt;0.18,&gt;=0.17.2; extra == "kernels"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "sentencepiece"; protobuf; extra == "sentencepiece"; tiktoken; extra == "tiktoken"; blobfile; extra == "tiktoken"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "mistral-common"; jinja2&gt;=3.1.0; extra == "chat-template"; scikit-learn; extra == "sklearn"; accelerate&gt;=1.1.0; extra == "accelerate"; faiss-cpu; extra == "retrieval"; datasets&gt;=2.15.0; extra == "retrieval"; sagemaker&gt;=2.31.0; extra == "sagemaker"; deepspeed&gt;=0.9.3; extra == "deepspeed"; accelerate&gt;=1.1.0; extra == "deepspeed"; optuna; extra == "optuna"; kernels&lt;0.18,&gt;=0.17.2; extra == "integrations"; optuna; extra == "integrations"; codecarbon&gt;=2.8.1; extra == "integrations"; ray&#91;tune&#93;&gt;=2.7.0; extra == "integrations"; ray&#91;tune&#93;&gt;=2.7.0; extra == "ray"; codecarbon&gt;=2.8.1; extra == "codecarbon"; openai&gt;=1.98.0; extra == "serving"; pydantic&gt;=2; extra == "serving"; uvicorn; extra == "serving"; fastapi; extra == "serving"; starlette; extra == "serving"; rich; extra == "serving"; torch&gt;=2.6; extra == "serving"; accelerate&gt;=1.1.0; extra == "serving"; num2words; extra == "num2words"; optimum-benchmark&gt;=0.3.0; extra == "benchmark"; fugashi&gt;=1.0; extra == "ja"; ipadic&lt;2.0,&gt;=1.0.0; extra == "ja"; unidic&#95;lite&gt;=1.0.7; extra == "ja"; unidic&gt;=1.0.2; extra == "ja"; rhoknp&lt;1.3.1,&gt;=1.1.0; extra == "ja"; sudachipy&gt;=0.6.6; extra == "ja"; sudachidict&#95;core&gt;=20220729; extra == "ja"; pytest&lt;9.0.0,&gt;=7.2.0; extra == "testing"; pytest-asyncio&gt;=1.2.0; extra == "testing"; pytest-random-order; extra == "testing"; pytest-rich; extra == "testing"; pytest-xdist; extra == "testing"; pytest-order; extra == "testing"; pytest-rerunfailures&lt;16.0; extra == "testing"; pytest-timeout; extra == "testing"; pytest-env; extra == "testing"; timeout-decorator; extra == "testing"; parameterized&gt;=0.9; extra == "testing"; psutil; extra == "testing"; diffusers==0.35.2; extra == "testing"; nltk&lt;=3.8.1; extra == "testing"; sacremoses; extra == "testing"; rjieba; extra == "testing"; beautifulsoup4; extra == "testing"; tensorboard; extra == "testing"; filelock; extra == "testing"; hf-doc-builder; extra == "testing"; datasets&gt;=2.15.0; extra == "testing"; ruff==0.14.10; extra == "testing"; GitPython&lt;3.1.19; extra == "testing"; urllib3&lt;2.0.0; extra == "testing"; libcst; extra == "testing"; rich; extra == "testing"; ty==0.0.20; extra == "testing"; tomli; extra == "testing"; transformers-mlinter==0.1.5; extra == "testing"; faiss-cpu; extra == "testing"; datasets&gt;=2.15.0; extra == "testing"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "testing"; protobuf; extra == "testing"; openai&gt;=1.98.0; extra == "testing"; pydantic&gt;=2; extra == "testing"; uvicorn; extra == "testing"; fastapi; extra == "testing"; starlette; extra == "testing"; rich; extra == "testing"; torch&gt;=2.6; extra == "testing"; accelerate&gt;=1.1.0; extra == "testing"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "testing"; deepspeed&gt;=0.9.3; extra == "deepspeed-testing"; accelerate&gt;=1.1.0; extra == "deepspeed-testing"; pytest&lt;9.0.0,&gt;=7.2.0; extra == "deepspeed-testing"; pytest-asyncio&gt;=1.2.0; extra == "deepspeed-testing"; pytest-random-order; extra == "deepspeed-testing"; pytest-rich; extra == "deepspeed-testing"; pytest-xdist; extra == "deepspeed-testing"; pytest-order; extra == "deepspeed-testing"; pytest-rerunfailures&lt;16.0; extra == "deepspeed-testing"; pytest-timeout; extra == "deepspeed-testing"; pytest-env; extra == "deepspeed-testing"; timeout-decorator; extra == "deepspeed-testing"; parameterized&gt;=0.9; extra == "deepspeed-testing"; psutil; extra == "deepspeed-testing"; diffusers==0.35.2; extra == "deepspeed-testing"; nltk&lt;=3.8.1; extra == "deepspeed-testing"; sacremoses; extra == "deepspeed-testing"; rjieba; extra == "deepspeed-testing"; beautifulsoup4; extra == "deepspeed-testing"; tensorboard; extra == "deepspeed-testing"; filelock; extra == "deepspeed-testing"; hf-doc-builder; extra == "deepspeed-testing"; datasets&gt;=2.15.0; extra == "deepspeed-testing"; ruff==0.14.10; extra == "deepspeed-testing"; GitPython&lt;3.1.19; extra == "deepspeed-testing"; urllib3&lt;2.0.0; extra == "deepspeed-testing"; libcst; extra == "deepspeed-testing"; rich; extra == "deepspeed-testing"; ty==0.0.20; extra == "deepspeed-testing"; tomli; extra == "deepspeed-testing"; transformers-mlinter==0.1.5; extra == "deepspeed-testing"; faiss-cpu; extra == "deepspeed-testing"; datasets&gt;=2.15.0; extra == "deepspeed-testing"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "deepspeed-testing"; protobuf; extra == "deepspeed-testing"; openai&gt;=1.98.0; extra == "deepspeed-testing"; pydantic&gt;=2; extra == "deepspeed-testing"; uvicorn; extra == "deepspeed-testing"; fastapi; extra == "deepspeed-testing"; starlette; extra == "deepspeed-testing"; rich; extra == "deepspeed-testing"; torch&gt;=2.6; extra == "deepspeed-testing"; accelerate&gt;=1.1.0; extra == "deepspeed-testing"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "deepspeed-testing"; optuna; extra == "deepspeed-testing"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "deepspeed-testing"; protobuf; extra == "deepspeed-testing"; torch&gt;=2.6; extra == "all"; accelerate&gt;=1.1.0; extra == "all"; torchvision; extra == "all"; Pillow&lt;=15.0,&gt;=10.0.1; extra == "all"; torchaudio; extra == "all"; librosa; extra == "all"; pyctcdecode&gt;=0.4.0; extra == "all"; phonemizer; extra == "all"; kenlm; extra == "all"; av; extra == "all"; kernels&lt;0.18,&gt;=0.17.2; extra == "all"; timm&gt;=1.0.23; extra == "all"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "all"; protobuf; extra == "all"; tiktoken; extra == "all"; blobfile; extra == "all"; jinja2&gt;=3.1.0; extra == "all"; num2words; extra == "all"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "all"; torch&gt;=2.6; extra == "dev"; accelerate&gt;=1.1.0; extra == "dev"; torchvision; extra == "dev"; Pillow&lt;=15.0,&gt;=10.0.1; extra == "dev"; torchaudio; extra == "dev"; librosa; extra == "dev"; pyctcdecode&gt;=0.4.0; extra == "dev"; phonemizer; extra == "dev"; kenlm; extra == "dev"; av; extra == "dev"; kernels&lt;0.18,&gt;=0.17.2; extra == "dev"; timm&gt;=1.0.23; extra == "dev"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "dev"; protobuf; extra == "dev"; tiktoken; extra == "dev"; blobfile; extra == "dev"; jinja2&gt;=3.1.0; extra == "dev"; num2words; extra == "dev"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "dev"; pytest&lt;9.0.0,&gt;=7.2.0; extra == "dev"; pytest-asyncio&gt;=1.2.0; extra == "dev"; pytest-random-order; extra == "dev"; pytest-rich; extra == "dev"; pytest-xdist; extra == "dev"; pytest-order; extra == "dev"; pytest-rerunfailures&lt;16.0; extra == "dev"; pytest-timeout; extra == "dev"; pytest-env; extra == "dev"; timeout-decorator; extra == "dev"; parameterized&gt;=0.9; extra == "dev"; psutil; extra == "dev"; diffusers==0.35.2; extra == "dev"; nltk&lt;=3.8.1; extra == "dev"; sacremoses; extra == "dev"; rjieba; extra == "dev"; beautifulsoup4; extra == "dev"; tensorboard; extra == "dev"; filelock; extra == "dev"; hf-doc-builder; extra == "dev"; datasets&gt;=2.15.0; extra == "dev"; ruff==0.14.10; extra == "dev"; GitPython&lt;3.1.19; extra == "dev"; urllib3&lt;2.0.0; extra == "dev"; libcst; extra == "dev"; rich; extra == "dev"; ty==0.0.20; extra == "dev"; tomli; extra == "dev"; transformers-mlinter==0.1.5; extra == "dev"; faiss-cpu; extra == "dev"; datasets&gt;=2.15.0; extra == "dev"; sentencepiece!=0.1.92,&gt;=0.1.91; extra == "dev"; protobuf; extra == "dev"; openai&gt;=1.98.0; extra == "dev"; pydantic&gt;=2; extra == "dev"; uvicorn; extra == "dev"; fastapi; extra == "dev"; starlette; extra == "dev"; rich; extra == "dev"; torch&gt;=2.6; extra == "dev"; accelerate&gt;=1.1.0; extra == "dev"; mistral-common&#91;image&#93;&gt;=1.11.7; extra == "dev"; fugashi&gt;=1.0; extra == "dev"; ipadic&lt;2.0,&gt;=1.0.0; extra == "dev"; unidic&#95;lite&gt;=1.0.7; extra == "dev"; unidic&gt;=1.0.2; extra == "dev"; rhoknp&lt;1.3.1,&gt;=1.1.0; extra == "dev"; sudachipy&gt;=0.6.6; extra == "dev"; sudachidict&#95;core&gt;=20220729; extra == "dev"; scikit-learn; extra == "dev"</span>

<span id="p2656">wheel SHA256 5f51ce444193e5d0a751e3fa489ddbc2​224ff12f6675a5cfefd4044b09757c19</span>

<span id="p2657">huggingface&#95;hub 1.33.0；许可元数据 Apache-2.0</span>

<span id="p2658">Requires-Dist click&lt;9.0.0,&gt;=8.4.2; filelock&gt;=3.10.0; fsspec&gt;=2023.5.0; hf-xet&lt;2.0.0,&gt;=1.6.0; platform&#95;machine == "x86&#95;64" or platform&#95;machine == "amd64" or platform&#95;machine == "AMD64" or platform&#95;machine == "arm64" or platform&#95;machine == "aarch64"; httpx&lt;1,&gt;=0.23.0; packaging&gt;=20.9; pyyaml&gt;=5.1; tomli&gt;=1.1.0; python&#95;version &lt; "3.11"; tqdm&gt;=4.42.1; typing-extensions&gt;=4.1.0; authlib&gt;=1.3.2; extra == "oauth"; fastapi; extra == "oauth"; httpx; extra == "oauth"; itsdangerous; extra == "oauth"; torch; extra == "torch"; safetensors&#91;torch&#93;; extra == "torch"; toml; extra == "fastai"; fastai&gt;=2.4; extra == "fastai"; fastcore&gt;=1.3.27; extra == "fastai"; hf-xet&lt;2.0.0,&gt;=1.6.0; extra == "hf-xet"; mcp&lt;2.0.0,&gt;=1.9.4; extra == "mcp"; authlib&gt;=1.3.2; extra == "testing"; fastapi; extra == "testing"; httpx; extra == "testing"; itsdangerous; extra == "testing"; jedi; extra == "testing"; Jinja2; extra == "testing"; pytest&gt;=8.4.2; extra == "testing"; pytest-cov; extra == "testing"; pytest-env; extra == "testing"; pytest-xdist; extra == "testing"; pytest-vcr; extra == "testing"; pytest-asyncio; extra == "testing"; pytest-rerunfailures&gt;=16.2; extra == "testing"; pytest-mock; extra == "testing"; urllib3&lt;2.0; extra == "testing"; soundfile; extra == "testing"; Pillow; extra == "testing"; numpy; extra == "testing"; duckdb; extra == "testing"; fastapi; extra == "testing"; gradio&gt;=5.0.0; extra == "gradio"; requests; extra == "gradio"; typing-extensions&gt;=4.8.0; extra == "typing"; types-PyYAML; extra == "typing"; types-simplejson; extra == "typing"; types-toml; extra == "typing"; types-tqdm; extra == "typing"; types-urllib3; extra == "typing"; ruff&gt;=0.9.0; extra == "quality"; mypy==1.15.0; extra == "quality"; libcst&gt;=1.4.0; extra == "quality"; ty; extra == "quality"; authlib&gt;=1.3.2; extra == "all"; fastapi; extra == "all"; httpx; extra == "all"; itsdangerous; extra == "all"; jedi; extra == "all"; Jinja2; extra == "all"; pytest&gt;=8.4.2; extra == "all"; pytest-cov; extra == "all"; pytest-env; extra == "all"; pytest-xdist; extra == "all"; pytest-vcr; extra == "all"; pytest-asyncio; extra == "all"; pytest-rerunfailures&gt;=16.2; extra == "all"; pytest-mock; extra == "all"; urllib3&lt;2.0; extra == "all"; soundfile; extra == "all"; Pillow; extra == "all"; numpy; extra == "all"; duckdb; extra == "all"; fastapi; extra == "all"; ruff&gt;=0.9.0; extra == "all"; mypy==1.15.0; extra == "all"; libcst&gt;=1.4.0; extra == "all"; ty; extra == "all"; typing-extensions&gt;=4.8.0; extra == "all"; types-PyYAML; extra == "all"; types-simplejson; extra == "all"; types-toml; extra == "all"; types-tqdm; extra == "all"; types-urllib3; extra == "all"; authlib&gt;=1.3.2; extra == "dev"; fastapi; extra == "dev"; httpx; extra == "dev"; itsdangerous; extra == "dev"; jedi; extra == "dev"; Jinja2; extra == "dev"; pytest&gt;=8.4.2; extra == "dev"; pytest-cov; extra == "dev"; pytest-env; extra == "dev"; pytest-xdist; extra == "dev"; pytest-vcr; extra == "dev"; pytest-asyncio; extra == "dev"; pytest-rerunfailures&gt;=16.2; extra == "dev"; pytest-mock; extra == "dev"; urllib3&lt;2.0; extra == "dev"; soundfile; extra == "dev"; Pillow; extra == "dev"; numpy; extra == "dev"; duckdb; extra == "dev"; fastapi; extra == "dev"; ruff&gt;=0.9.0; extra == "dev"; mypy==1.15.0; extra == "dev"; libcst&gt;=1.4.0; extra == "dev"; ty; extra == "dev"; typing-extensions&gt;=4.8.0; extra == "dev"; types-PyYAML; extra == "dev"; types-simplejson; extra == "dev"; types-toml; extra == "dev"; types-tqdm; extra == "dev"; types-urllib3; extra == "dev"</span>

<span id="p2659">wheel SHA256 04e434b06e100eddbce9a6e817d72693​a7884b10a79bd67ab48080d5c07eb899</span>

<span id="p2660">plotly 7.1.0；许可元数据 MIT</span>

<span id="p2661">Requires-Dist narwhals&gt;=1.15.1; packaging; anywidget; extra == 'dev'; build; extra == 'dev'; colorcet; extra == 'dev'; fiona&lt;=1.9.6; (python&#95;version &lt;= '3.8') and extra == 'dev'; geopandas; extra == 'dev'; inflect; extra == 'dev'; jupyter-builder; extra == 'dev'; jupyterlab; extra == 'dev'; kaleido&gt;=1.3.0; extra == 'dev'; numpy&gt;=1.22; extra == 'dev'; orjson; extra == 'dev'; pandas; extra == 'dev'; pdfrw; extra == 'dev'; pillow; extra == 'dev'; polars&#91;timezone&#93;; extra == 'dev'; pyarrow; extra == 'dev'; pytest; extra == 'dev'; pytz; extra == 'dev'; requests; extra == 'dev'; ruff==0.11.12; extra == 'dev'; scikit-image; extra == 'dev'; scipy; extra == 'dev'; sphinx-gallery; extra == 'dev'; statsmodels; extra == 'dev'; vaex; (python&#95;version &lt;= '3.9') and extra == 'dev'; xarray; extra == 'dev'; build; extra == 'dev-build'; jupyter-builder; extra == 'dev-build'; pytest; extra == 'dev-build'; requests; extra == 'dev-build'; ruff==0.11.12; extra == 'dev-build'; inflect; extra == 'dev-codegen'; pytest; extra == 'dev-codegen'; requests; extra == 'dev-codegen'; ruff==0.11.12; extra == 'dev-codegen'; pytest; extra == 'dev-core'; requests; extra == 'dev-core'; ruff==0.11.12; extra == 'dev-core'; anywidget; extra == 'dev-optional'; build; extra == 'dev-optional'; colorcet; extra == 'dev-optional'; fiona&lt;=1.9.6; (python&#95;version &lt;= '3.8') and extra == 'dev-optional'; geopandas; extra == 'dev-optional'; inflect; extra == 'dev-optional'; jupyter-builder; extra == 'dev-optional'; jupyterlab; extra == 'dev-optional'; kaleido&gt;=1.3.0; extra == 'dev-optional'; numpy&gt;=1.22; extra == 'dev-optional'; orjson; extra == 'dev-optional'; pandas; extra == 'dev-optional'; pdfrw; extra == 'dev-optional'; pillow; extra == 'dev-optional'; polars&#91;timezone&#93;; extra == 'dev-optional'; pyarrow; extra == 'dev-optional'; pytest; extra == 'dev-optional'; pytz; extra == 'dev-optional'; requests; extra == 'dev-optional'; ruff==0.11.12; extra == 'dev-optional'; scikit-image; extra == 'dev-optional'; scipy; extra == 'dev-optional'; sphinx-gallery; extra == 'dev-optional'; statsmodels; extra == 'dev-optional'; vaex; (python&#95;version &lt;= '3.9') and extra == 'dev-optional'; xarray; extra == 'dev-optional'; numpy&lt;2,&gt;=1; extra == 'dev-pandas1'; pandas&lt;2,&gt;=1; extra == 'dev-pandas1'; setuptools&lt;82; extra == 'dev-pandas1'; pandas&lt;3,&gt;=2; extra == 'dev-pandas2'; pandas&gt;=3; (python&#95;version &gt;= '3.11') and extra == 'dev-pandas3'; numpy&gt;=1.22; extra == 'express'; kaleido&gt;=1.3.0; extra == 'kaleido'</span>

<span id="p2662">wheel SHA256 dbb7fa18afce40d0a8e80d1bf162eceb​3faa0ce5a77fe741ad09a74cf78f53f3</span>

<span id="p2663">pynndescent 0.6.0；许可元数据 BSD-2-Clause</span>

<span id="p2664">Requires-Dist scikit-learn&gt;=0.18; scipy&gt;=1.0; numba&gt;=0.55.0; llvmlite&gt;=0.38; joblib&gt;=0.11; pytest; extra == "testing"</span>

<span id="p2665">wheel SHA256 dc8c74844e4c7f5cbd1e0cd6909da86f​dc789e6ff4997336e344779c3d5538ef</span>

<span id="p2666">safetensors 0.8.0；许可元数据 未记录</span>

<span id="p2667">Requires-Dist safetensors&#91;torch&#93; ; extra == 'all'; safetensors&#91;numpy&#93; ; extra == 'all'; safetensors&#91;jax&#93; ; extra == 'all'; safetensors&#91;paddlepaddle&#93; ; extra == 'all'; safetensors&#91;convert&#93; ; extra == 'all'; safetensors&#91;quality&#93; ; extra == 'all'; safetensors&#91;testing&#93; ; extra == 'all'; safetensors&#91;torch&#93; ; extra == 'convert'; huggingface-hub&gt;=1.4 ; extra == 'convert'; safetensors&#91;all&#93; ; extra == 'dev'; safetensors&#91;pinned-tf&#93; ; extra == 'dev'; safetensors&#91;numpy&#93; ; extra == 'jax'; flax&gt;=0.6.3 ; extra == 'jax'; jax&gt;=0.3.25 ; extra == 'jax'; jaxlib&gt;=0.3.25 ; extra == 'jax'; mlx&gt;=0.0.9 ; extra == 'mlx'; numpy&gt;=1.24.6 ; extra == 'numpy'; safetensors&#91;numpy&#93; ; extra == 'paddlepaddle'; paddlepaddle&gt;=2.4.1 ; extra == 'paddlepaddle'; safetensors&#91;numpy&#93; ; extra == 'pinned-tf'; tensorflow==2.18.0 ; extra == 'pinned-tf'; ruff ; extra == 'quality'; safetensors&#91;numpy&#93; ; extra == 'tensorflow'; tensorflow&gt;=2.11.0 ; extra == 'tensorflow'; safetensors&#91;numpy&#93; ; extra == 'testing'; h5py&gt;=3.7.0 ; extra == 'testing'; setuptools-rust&gt;=1.12.0 ; extra == 'testing'; pytest&gt;=9.0 ; extra == 'testing'; pytest-benchmark&gt;=5.2 ; extra == 'testing'; hypothesis&gt;=6.70.2 ; extra == 'testing'; fsspec&gt;=2024.6.0 ; extra == 'testing'; s3fs&gt;=2024.6.0 ; extra == 'testing'; safetensors&#91;numpy&#93; ; extra == 'tf-nightly'; tf-nightly ; extra == 'tf-nightly'; safetensors&#91;numpy&#93; ; extra == 'torch'; torch&gt;=2.4 ; extra == 'torch'</span>

<span id="p2668">wheel SHA256 fd6f3f93c9a0a7cc2788ee63fb763353​d4bd2e89b0751bc78fcf7dda00bea774</span>

<span id="p2669">tokenizers 0.23.3；许可元数据 未记录</span>

<span id="p2670">Requires-Dist huggingface-hub&gt;=0.16.4,&lt;3.0; tokenizers&#91;testing&#93; ; extra == 'dev'; sphinx ; extra == 'docs'; sphinx-rtd-theme ; extra == 'docs'; setuptools-rust ; extra == 'docs'; pytest ; extra == 'testing'; pytest-asyncio ; extra == 'testing'; requests ; extra == 'testing'; numpy ; extra == 'testing'; datasets ; extra == 'testing'; ruff ; extra == 'testing'; ty ; extra == 'testing'</span>

<span id="p2671">wheel SHA256 376851d22bcf9d650a5c3090bb83e6cf​9e895fbf0595369fa4cd43c1f69b5f87</span>

<span id="p2672">typer 0.27.3；许可元数据 MIT</span>

<span id="p2673">Requires-Dist shellingham&gt;=1.3.0; rich&gt;=13.8.0; annotated-doc&gt;=0.0.2; colorama; platform&#95;system == "Windows"</span>

<span id="p2674">wheel SHA256 e50022f28b82a86313e54501317a1db6​4bf8f8d036ff8cfe5ca7e47675454aff</span>

<span id="p2675">annotated-doc 0.0.5；许可元数据 MIT</span>

<span id="p2676">Requires-Dist </span>

<span id="p2677">wheel SHA256 117bac03a25ede5df5440e855b32d556​049ca169ead221505badf432fed4b101</span>

<span id="p2678">hf-xet 1.7.0；许可元数据 Apache-2.0</span>

<span id="p2679">Requires-Dist pytest ; extra == 'tests'</span>

<span id="p2680">wheel SHA256 2814a6e999d13464c4d679b788cc5d78​4eb5a4edfc638a31f10e9a11ab531ef8</span>

<span id="p2681">narwhals 2.27.1；许可元数据 MIT</span>

<span id="p2682">Requires-Dist cudf-cu12&gt;=24.10.0 ; sys&#95;platform == 'linux' and extra == 'cudf'; dask&#91;dataframe&#93;&gt;=2024.8 ; extra == 'dask'; duckdb&gt;=1.1 ; extra == 'duckdb'; ibis-framework&gt;=6.0.0 ; extra == 'ibis'; packaging&gt;=21.3 ; extra == 'ibis'; pyarrow-hotfix&gt;=0.7 ; extra == 'ibis'; modin&gt;=0.22.0 ; extra == 'modin'; pandas&gt;=1.3.4 ; extra == 'pandas'; polars&gt;=0.20.4 ; extra == 'polars'; pyarrow&gt;=13.0.0 ; extra == 'pyarrow'; pyspark&gt;=3.5.0 ; extra == 'pyspark'; pyspark&#91;connect&#93;&gt;=3.5.0 ; extra == 'pyspark-connect'; narwhals&#91;duckdb&#93; ; extra == 'sql'; sqlparse&gt;=0.5.5 ; extra == 'sql'; sqlframe&gt;=3.22.0,!=3.39.3 ; extra == 'sqlframe'</span>

<span id="p2683">wheel SHA256 d057df13f5852b8e157596e82eb5e955​fad267425df5e420e0ee9863da483b31</span>

<span id="p2684">shellingham 1.5.4；许可元数据 ISC License</span>

<span id="p2685">Requires-Dist </span>

<span id="p2686">wheel SHA256 7ecfff8f2fd72616f7481040475a65b2​bf8af90a56c89140852d1120324e8686</span>

## <span id="p2687">附录五 字体 素材与模型文件身份</span>

<span id="p2688">资产hash为恢复产品文件实际字节；模型表hash为产品声明的预期值，22项均未找到匹配恢复字节。二者证据层级不同。</span>

<!-- table-07 -->
| <span id="p2689"><strong>资源相对路径</strong></span> | <span id="p2690"><strong>字节数与许可</strong></span> | <span id="p2691"><strong>实际SHA256</strong></span> |
| --- | --- | --- |
| <span id="p2692">app/assets/fonts/NotoColorEmoji.ttf</span> | <span id="p2693">10730124<br />OFL-1.1 (bundled notices)</span> | <span id="p2694">15671215ab769fdc7162a045d56fd7d7​e477c51b04e6b3c761d914d8fdd6cc44</span> |
| <span id="p2695">app/assets/fonts/NotoSansKR-OFL.txt</span> | <span id="p2696">4387<br />OFL-1.1 (bundled notices)</span> | <span id="p2697">babcfe66c8a098b2fa279bc724a3a342​f8124f77ce18941fbcc1bbb39823cded</span> |
| <span id="p2698">app/assets/fonts/NotoSansKR.ttf</span> | <span id="p2699">10414588<br />OFL-1.1 (bundled notices)</span> | <span id="p2700">194018e6b2b293a7964f037b25c0249c​e1418bc9ab3c971060a03aa57861e252</span> |
| <span id="p2701">app/assets/fonts/NotoSansSC.ttf</span> | <span id="p2702">17772300<br />OFL-1.1 (bundled notices)</span> | <span id="p2703">a3041811a78c361b1de50f953c805e02​44951c21c5bd412f7232ef0d899af0da</span> |
| <span id="p2704">app/assets/fonts/NotoSansSC-OFL.txt</span> | <span id="p2705">4387<br />OFL-1.1 (bundled notices)</span> | <span id="p2706">babcfe66c8a098b2fa279bc724a3a342​f8124f77ce18941fbcc1bbb39823cded</span> |
| <span id="p2707">app/assets/fonts/NotoColorEmoji-OFL.txt</span> | <span id="p2708">4301<br />OFL-1.1 (bundled notices)</span> | <span id="p2709">6a73f9541c2de74158c0e7cf6b0a58ef​774f5a780bf191f2d7ec9cc53efe2bf2</span> |
| <span id="p2710">app/assets/wallpapers/README.md</span> | <span id="p2711">556<br />user-supplied usage provenance; no public license</span> | <span id="p2712">5e54ee48226d4266e6da09a28a714add​0c9223aa1772078101a6688be5637153</span> |
| <span id="p2713">app/assets/wallpapers/cobalt-dusk.jpg</span> | <span id="p2714">159638<br />user-supplied usage provenance; no public license</span> | <span id="p2715">f50de0951c1a106b139dc606d1362674​8c8fbcc18ebedcfc4353eeab4c45c587</span> |
| <span id="p2716">app/assets/wallpapers/crimson-sunset.jpg</span> | <span id="p2717">182063<br />user-supplied usage provenance; no public license</span> | <span id="p2718">dbd5e3375d13ea0faedc97ae0312ac4c​3294a2577a01afbed27063d8251ab8f1</span> |
| <span id="p2719">website/public/favicon.svg</span> | <span id="p2720">431<br />project original; not independently verified</span> | <span id="p2721">ce888a80fd38df55cc1a9d1ad6747a1d​a2d9eb5c2ce6517e7cbedefb7ea2ce4f</span> |

### <span id="p2722">openai gpt-oss-20b</span>

<span id="p2723">revision 6cee5e81ee83917806bbde320786a8fb61efebee</span>

<!-- table-08 -->
| <span id="p2724"><strong>声明文件</strong></span> | <span id="p2725"><strong>声明字节数</strong></span> | <span id="p2726"><strong>预期SHA256 未恢复字节</strong></span> |
| --- | --- | --- |
| <span id="p2727">LICENSE</span> | <span id="p2728">11357</span> | <span id="p2729">58d1e17ffe5109a7ae296caafcadfdbe​6a7d176f0bc4ab01e12a689b0499d8bd</span> |
| <span id="p2730">USAGE&#95;POLICY</span> | <span id="p2731">200</span> | <span id="p2732">d6387ef7985019c45db8d9801e6ac5fd​9f98f02b9f1c56f8c5af80c3e8f385d0</span> |
| <span id="p2733">chat&#95;template.jinja</span> | <span id="p2734">16738</span> | <span id="p2735">a4c9919cbbd4acdd51ccffe22da04926​4b1b73e59055fa58811a99efbd7c8146</span> |
| <span id="p2736">config.json</span> | <span id="p2737">1806</span> | <span id="p2738">3a2a26ded679375b7928ddeca59764df​7cea83220c1961035f6d6e232659e9ce</span> |
| <span id="p2739">model-00000-of-00002.safetensors</span> | <span id="p2740">4792272488</span> | <span id="p2741">16d0f997dcfc4462089d536bffe51b4b​cea2f872f5c430be09ef8ed392312427</span> |
| <span id="p2742">model-00001-of-00002.safetensors</span> | <span id="p2743">4798702184</span> | <span id="p2744">4fbe328ab445455d6f58dc73852b8587​3bd626986310abd91cd4d2ce3245eaea</span> |
| <span id="p2745">model-00002-of-00002.safetensors</span> | <span id="p2746">4170342232</span> | <span id="p2747">a18106b209e9ab35c3406db4f6f12a92​7364a058b21e9d1373d682e20674b303</span> |
| <span id="p2748">model.safetensors.index.json</span> | <span id="p2749">36355</span> | <span id="p2750">0e085b977c4c9942f85938828e8c989e​d7d5cdabf852e4da6a67c116cd502cd1</span> |
| <span id="p2751">special&#95;tokens&#95;map.json</span> | <span id="p2752">98</span> | <span id="p2753">dd5e191d20c12d2fee1da5bae14ca1db​0f5f4215300af691f23cdee97120a293</span> |
| <span id="p2754">tokenizer.json</span> | <span id="p2755">27868174</span> | <span id="p2756">0614fe83cadab421296e664e1f48f426​1fa8fef6e03e63bb75c20f38e37d07d3</span> |
| <span id="p2757">tokenizer&#95;config.json</span> | <span id="p2758">4200</span> | <span id="p2759">9279e942392b742d633c7adbb89ebe00​2c98399db8926a7af5125c726f404070</span> |

### <span id="p2760">其他固定衍生模型声明</span>

<!-- table-09 -->
| <span id="p2761"><strong>模型与文件</strong></span> | <span id="p2762"><strong>revision</strong></span> | <span id="p2763"><strong>预期SHA256 未恢复字节</strong></span> |
| --- | --- | --- |
| <span id="p2764">unsloth/gpt-oss-20b-unsloth-bnb-4bit / chat&#95;template.json</span> | <span id="p2765">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2766">7bfd294f3e29b53db1e126d5cec050a1​2dc27adad4445fb5eab540e1cad74ea1</span> |
| <span id="p2767">unsloth/gpt-oss-20b-unsloth-bnb-4bit / config.json</span> | <span id="p2768">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2769">8d2a25b5980bb9135abe915c9e62ed57​dd824bec53dfb57b3dbfc4abe5d2d39c</span> |
| <span id="p2770">unsloth/gpt-oss-20b-unsloth-bnb-4bit / generation&#95;config.json</span> | <span id="p2771">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2772">199566674b96510c3b9a1141b494223a​86a3ff83097e2c2f259c4d94fafc5847</span> |
| <span id="p2773">unsloth/gpt-oss-20b-unsloth-bnb-4bit / model.safetensors.index.json</span> | <span id="p2774">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2775">e1f5f117b5ca6c1e532d7c04247ae4d1​ca481190eec11fb4402fe1305064a7cf</span> |
| <span id="p2776">unsloth/gpt-oss-20b-unsloth-bnb-4bit / special&#95;tokens&#95;map.json</span> | <span id="p2777">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2778">c661c7dc897a8d9851446db24876bbc2​43e6ad2f58542e9147190e6654f92855</span> |
| <span id="p2779">unsloth/gpt-oss-20b-unsloth-bnb-4bit / tokenizer&#95;config.json</span> | <span id="p2780">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2781">1dc1edbfd80613ee13e7882e7bdbd554​26d08f88cf38c5de19785219a3ffb076</span> |
| <span id="p2782">unsloth/gpt-oss-20b-unsloth-bnb-4bit / tokenizer.json</span> | <span id="p2783">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2784">0614fe83cadab421296e664e1f48f426​1fa8fef6e03e63bb75c20f38e37d07d3</span> |
| <span id="p2785">unsloth/gpt-oss-20b-unsloth-bnb-4bit / model-00001-of-00004.safetensors</span> | <span id="p2786">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2787">f229f4364b1f2cfa7df0ced4d2277714​5d3d552f95512f98b20493ea094e8b89</span> |
| <span id="p2788">unsloth/gpt-oss-20b-unsloth-bnb-4bit / model-00002-of-00004.safetensors</span> | <span id="p2789">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2790">2b75ef14502b54c47cad18bb6c2f96e9​19991ba994a3331799e38891ac290a30</span> |
| <span id="p2791">unsloth/gpt-oss-20b-unsloth-bnb-4bit / model-00003-of-00004.safetensors</span> | <span id="p2792">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2793">76cc7c3bf1cd287a8a7cea77e00eb45c​e6d6a0fbc7084d29a347eed0b398af90</span> |
| <span id="p2794">unsloth/gpt-oss-20b-unsloth-bnb-4bit / model-00004-of-00004.safetensors</span> | <span id="p2795">093fba6992ef5a7152481afec0bdfca1ac486998</span> | <span id="p2796">31709e4bd1403df4437091d952e2ec83​7efbbfc06337b4b2b6c6875491e0e7bc</span> |

### <span id="p2797">Whisper v20250625 源码与资源核对</span>

<!-- table-10 -->
| <span id="p2798"><strong>文件</strong></span> | <span id="p2799"><strong>实际SHA256 与产品pin相同</strong></span> |
| --- | --- |
| <span id="p2800">&#95;&#95;init&#95;&#95;.py</span> | <span id="p2801">79ecbed714783b6230931a3dba6d5da6​d386e2d44f9fc27256e4fc72751e1f62</span> |
| <span id="p2802">&#95;&#95;main&#95;&#95;.py</span> | <span id="p2803">c519d586c3a6b639f64e59d2d6fd6b59​1a67ecd739f9727492911fc4ce4d545a</span> |
| <span id="p2804">assets/gpt2.tiktoken</span> | <span id="p2805">306cd27f03c1a714eca7108e03d66b7d​c042abe8c258b44c199a7ed9838dd930</span> |
| <span id="p2806">assets/mel&#95;filters.npz</span> | <span id="p2807">7450ae70723a5ef9d341e3cee628c7cb​0177f36ce42c44b7ed2bf3325f0f6d4c</span> |
| <span id="p2808">assets/multilingual.tiktoken</span> | <span id="p2809">b34b360dbb493e781e479794586d6617​00670d65564001f23024971d1f2fa126</span> |
| <span id="p2810">audio.py</span> | <span id="p2811">36ed287b2de3eaf40207cd2a44a8d45d​57ea5c212a39df07401d4fcb4d5a5a1a</span> |
| <span id="p2812">decoding.py</span> | <span id="p2813">94084fedc5af74cabf8e1883a8555270​0057081f00ea669ad49435ecb29039db</span> |
| <span id="p2814">model.py</span> | <span id="p2815">473491a97554ad1d0beaaef6fe91d965​f12785b466b93ebb61024307b50ad683</span> |
| <span id="p2816">normalizers/&#95;&#95;init&#95;&#95;.py</span> | <span id="p2817">f18fcdce4caee7f2e80e4c01ab0457d3​a080a872a29489542c6d23c4b0bba572</span> |
| <span id="p2818">normalizers/basic.py</span> | <span id="p2819">4742eaa040e0657fa1247a1361e0d856​c62317a43326ea59a40c2e9edd8d2c38</span> |
| <span id="p2820">normalizers/english.py</span> | <span id="p2821">2898e4672aeefc9f44cb4de38c115cdf​286f5b35ae321433467a7674ce8841d0</span> |
| <span id="p2822">timing.py</span> | <span id="p2823">bb091c973c428697012f0f8d1b4f5f3a​605cd93c5d1c129957f712a6a878a59c</span> |
| <span id="p2824">tokenizer.py</span> | <span id="p2825">3b48e361a7e95b4ec0356ca6d72bba63​5778aa10269153136ee7bc34cae30b85</span> |
| <span id="p2826">transcribe.py</span> | <span id="p2827">848b82877500d6fb8f0b91bee7a08ac6​7ef670a113591d11b494848d263ad0f6</span> |
| <span id="p2828">triton&#95;ops.py</span> | <span id="p2829">26c5082f029bbd2b7ae77ecf5a3f7f19​6f220e5850e2c9d0ec42961caf0dde4c</span> |
| <span id="p2830">utils.py</span> | <span id="p2831">c25990446ab7dd5ba30bd52bd4f0e653​7f11b5e361a015f02c21355d41027b05</span> |
| <span id="p2832">version.py</span> | <span id="p2833">c4d27ecccdd52a9cded762f1a82da315​2db12cbc0aa6ea781f945446a143cfaf</span> |

## <span id="p2834">附录六 来源与机制阅读范围</span>

<span id="p2835">产品源码以官方主线commit和恢复候选指纹定位；正文路径均为仓库相对位置。上游官方源码仅静态阅读，未执行其代码。各包归档hash和锁身份见前述唯一总账。</span>

### <span id="p2836">声明与锁文件身份</span>

<!-- table-11 -->
| <span id="p2837"><strong>两版相同的前端文件</strong></span> | <span id="p2838"><strong>SHA256</strong></span> |
| --- | --- |
| <span id="p2839">package.json</span> | <span id="p2840">34d90164e03e833d49a3c212412c55a5​ec56d5ebd5c39a962708ea7eb4b7dfbd</span> |
| <span id="p2841">package-lock.json</span> | <span id="p2842">6a88a1c44f826770c7395ff9f2c81c26​ec0770c3424f8c3f8f1e0ef2313c8f43</span> |
| <span id="p2843">website/package.json</span> | <span id="p2844">d7999c59aa20c2bcc9270b706e2abf3d​d39594bc232051e5742f69c89a16c8fd</span> |
| <span id="p2845">website/package-lock.json</span> | <span id="p2846">225960c8ae39c9b276653b700a351c79​1d596596bd6193b166e195bc660cd33f</span> |
| <span id="p2847">app/pubspec.yaml</span> | <span id="p2848">3a0b17b9b48c318418136b3eddae6c87​00d3439b469848dbf43bc9d2f8730129</span> |
| <span id="p2849">app/pubspec.lock</span> | <span id="p2850">dedefadcf86edbd93357b4ba5ad43329​2d3a51ab3f5e8b2138788e7f9745968a</span> |

<!-- table-12 -->
| <span id="p2851"><strong>Python声明文件</strong></span> | <span id="p2852"><strong>SHA256</strong></span> |
| --- | --- |
| <span id="p2853">A report&#95;export/requirements&#95;report&#95;export.txt</span> | <span id="p2854">c1a05e2f626613469d89466450263d5c​541ea53a121eca580150e82d940833b3</span> |
| <span id="p2855">A requirements-browser-use.txt</span> | <span id="p2856">be4568898c8e54f51d6da0b3df169b47​fff6bb8613c05609029d95fb473b68b3</span> |
| <span id="p2857">A requirements-dev.txt</span> | <span id="p2858">f298c9ac6ff241ed52aaaaceec0c5914​ae7e1014b3c2f79441ba3a9a9d51ed2d</span> |
| <span id="p2859">A requirements.txt</span> | <span id="p2860">4dc2aead92efee4cf1c1e875316f5def​6dd744d648ab555adc460683ac361eec</span> |

<!-- table-13 -->
| <span id="p2861"><strong>Python声明文件</strong></span> | <span id="p2862"><strong>SHA256</strong></span> |
| --- | --- |
| <span id="p2863">B report&#95;export/requirements&#95;report&#95;export.txt</span> | <span id="p2864">c1a05e2f626613469d89466450263d5c​541ea53a121eca580150e82d940833b3</span> |
| <span id="p2865">B requirements-browser-use.txt</span> | <span id="p2866">be4568898c8e54f51d6da0b3df169b47​fff6bb8613c05609029d95fb473b68b3</span> |
| <span id="p2867">B requirements-dev.txt</span> | <span id="p2868">55b2395cad38c3c7e8024d3a8160bf65​7e789178562bad7a6e8b51379384d682</span> |
| <span id="p2869">B requirements-statistics-cpu.txt</span> | <span id="p2870">ce9682e9171aad32fe6c112eeceeb258​31451b91db4ae1ed59ed10c7bb99700d</span> |
| <span id="p2871">B requirements.txt</span> | <span id="p2872">5ab175044f0a831998e2e4b921b1f77f​2a9723e2860db1ff037293c4c41ba6b2</span> |

<span id="p2873"><a href="https://pypi.org/project/beautifulsoup4/4.15.0/">BeautifulSoup 4.15.0 官方项目元数据</a></span>

<span id="p2874"><a href="https://pypi.org/project/reportlab/5.0.1/">ReportLab 5.0.1 官方项目页</a></span>

<span id="p2875"><a href="https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle">MCP 2025 11 25 生命周期</a></span>

<span id="p2876"><a href="https://modelcontextprotocol.io/specification/2025-11-25/basic/transports">MCP 2025 11 25 传输</a></span>

<span id="p2877"><a href="https://modelcontextprotocol.io/specification/2025-11-25/server/tools">MCP 2025 11 25 工具</a></span>

<span id="p2878">flask/src/flask/app.py  dispatch&#95;request  行879至902</span>

<span id="p2879">文件SHA256 93bb56f0b1d14a57548baccab0528aec​0c5afd62f8ceed5edb03cdb6122cbbba；函数片段SHA256 7b946113c7aa57148a7131fd7ec76d43​829ba1d38a9ab3c0adccdb1ba6361d44</span>

<span id="p2880">flask/src/flask/app.py  full&#95;dispatch&#95;request  行904至920</span>

<span id="p2881">文件SHA256 93bb56f0b1d14a57548baccab0528aec​0c5afd62f8ceed5edb03cdb6122cbbba；函数片段SHA256 0f1d04f3d13874646e601cdc0ccffe8c​8a578e0395781aee069a2aaa2088d6ef</span>

<span id="p2882">flask/src/flask/app.py  finalize&#95;request  行922至951</span>

<span id="p2883">文件SHA256 93bb56f0b1d14a57548baccab0528aec​0c5afd62f8ceed5edb03cdb6122cbbba；函数片段SHA256 19e630399064e88ce31b2dd48f3dad16​d8f286574469a552401cbf42ab9efedb</span>

<span id="p2884">flask/src/flask/app.py  wsgi&#95;app  行1479至1527</span>

<span id="p2885">文件SHA256 93bb56f0b1d14a57548baccab0528aec​0c5afd62f8ceed5edb03cdb6122cbbba；函数片段SHA256 bc14c030295bd7e30d362d08d46bbf7c​f5eb1259914c164058ca37ed7b884319</span>

<span id="p2886">werkzeug/src/werkzeug/wrappers/response.py  get&#95;app&#95;iter  行520至545</span>

<span id="p2887">文件SHA256 c0feff98d4f443f4ea3d6fba795ef88e​021b4cebba5e60b37abd421395b506b2；函数片段SHA256 39ca85765d88819329f95bebf8fa4d38​f58b9135563871b5135a5d80c24ae156</span>

<span id="p2888">werkzeug/src/werkzeug/wrappers/response.py  &#95;&#95;call&#95;&#95;  行566至578</span>

<span id="p2889">文件SHA256 c0feff98d4f443f4ea3d6fba795ef88e​021b4cebba5e60b37abd421395b506b2；函数片段SHA256 dc1e1a93bc694ee77b2c1f59d06ee8b2​2c3fea4910657c2547b850cecd30f6f1</span>

<span id="p2890">requests/src/requests/sessions.py  send  行132至132</span>

<span id="p2891">文件SHA256 96fbb30bbbf06a59a5268d13b5788514​9756aa3f31695b5c15e41dd7bb2f67a6；函数片段SHA256 059af0bdb17a54eddc490ace8659584a​67d2660c906dc417b8ffe04755af6842</span>

<span id="p2892">requests/src/requests/sessions.py  resolve&#95;redirects  行186至307</span>

<span id="p2893">文件SHA256 96fbb30bbbf06a59a5268d13b5788514​9756aa3f31695b5c15e41dd7bb2f67a6；函数片段SHA256 b6f9a61ecd3f96c97c78748aee528b9a​dcf3dcfe1ec015698800dc5381a1d156</span>

<span id="p2894">requests/src/requests/sessions.py  request  行557至653</span>

<span id="p2895">文件SHA256 96fbb30bbbf06a59a5268d13b5788514​9756aa3f31695b5c15e41dd7bb2f67a6；函数片段SHA256 e5f6c309a7fb6392906cd2e375cd6de4​6981c2ed44afea845c61b7f0871504c1</span>

<span id="p2896">requests/src/requests/sessions.py  send  行752至829</span>

<span id="p2897">文件SHA256 96fbb30bbbf06a59a5268d13b5788514​9756aa3f31695b5c15e41dd7bb2f67a6；函数片段SHA256 ee680a2136df9d7eb8fd90129c9c2970​1597a3158fadd119dd67021339be7ef0</span>

<span id="p2898">requests/src/requests/adapters.py  send  行128至151</span>

<span id="p2899">文件SHA256 647eabd4453de232aa40b55ff033d6f1​9778910b7e7069c51fdf63076fc77493；函数片段SHA256 87b15481f2960c96d1f77b110cc00ef7​a82750427225b6c6f39d922248c18da2</span>

<span id="p2900">requests/src/requests/adapters.py  send  行634至748</span>

<span id="p2901">文件SHA256 647eabd4453de232aa40b55ff033d6f1​9778910b7e7069c51fdf63076fc77493；函数片段SHA256 97de1691e5648992827654eea0bcb749​82ffbbca45597f2a215fbb4e938b4177</span>

<span id="p2902">jsonschema/jsonschema/validators.py  validate  行1265至1332</span>

<span id="p2903">文件SHA256 97f171b995b4b0ca05530a9366a1252f​b1753f99f3cb7b1068b6d9aab1096fa5；函数片段SHA256 a95ea31dabb33ec2fec1abee5c12be69​70b47f0c49fefdf6d26e54971dd21048</span>

<span id="p2904">jsonschema/jsonschema/validators.py  iter&#95;errors  行349至394</span>

<span id="p2905">文件SHA256 97f171b995b4b0ca05530a9366a1252f​b1753f99f3cb7b1068b6d9aab1096fa5；函数片段SHA256 52589150d31f3feb469117a316e8efb9​652b07f5f12ed8a111ff424602e51693</span>

<span id="p2906">jsonschema/jsonschema/validators.py  validate  行448至450</span>

<span id="p2907">文件SHA256 97f171b995b4b0ca05530a9366a1252f​b1753f99f3cb7b1068b6d9aab1096fa5；函数片段SHA256 ac62476f699566ca2b62cd21c0776a64​600e58acc88de740deb6178256f214b5</span>

<span id="p2908">referencing/referencing/&#95;core.py  get&#95;or&#95;retrieve  行410至438</span>

<span id="p2909">文件SHA256 d923c67da4efcc0dec46a6e3ff8476c0​2fbe7e25e8942515a4b14b249eb3759f；函数片段SHA256 9da9b950cd50dae7a26144ff8bcee281​afec549650d93b568f17f95c9147c09e</span>

<span id="p2910">tenacity/tenacity/&#95;&#95;init&#95;&#95;.py  &#95;&#95;call&#95;&#95;  行455至461</span>

<span id="p2911">文件SHA256 2cb4e6bb30acfa1a977904959408a0e8​6c120a3dd5d4f7b00bdf9bde64d79f58；函数片段SHA256 55d1464143df33731af6f54db18ad721​d6ec998cc3f75175f595777d51632230</span>

<span id="p2912">tenacity/tenacity/&#95;&#95;init&#95;&#95;.py  &#95;&#95;call&#95;&#95;  行467至489</span>

<span id="p2913">文件SHA256 2cb4e6bb30acfa1a977904959408a0e8​6c120a3dd5d4f7b00bdf9bde64d79f58；函数片段SHA256 265c6cc0af160327fc68cf1a26dedc50​c2306648e02746bb6eaa90faab9d0f53</span>

<span id="p2914">waitress/src/waitress/task.py  execute  行347至358</span>

<span id="p2915">文件SHA256 9a35ed8ddec9e4d4a64551a7239a4817​c90398b1827b8eb3a853396b28ad6a8d；函数片段SHA256 cdf9e5d284639db140b8fa0f90add5eb​00b8b9c833fed7eb460b681f4b84970d</span>

<span id="p2916">waitress/src/waitress/task.py  execute  行366至489</span>

<span id="p2917">文件SHA256 9a35ed8ddec9e4d4a64551a7239a4817​c90398b1827b8eb3a853396b28ad6a8d；函数片段SHA256 60c3c9191641e9beff53e2249e5d6f48​1e861455f8be6c8f1ceed91df5859040</span>

<span id="p2918">alembic/alembic/command.py  upgrade  行446至487</span>

<span id="p2919">文件SHA256 40fa925f798b81fb4f35c8bc8deb25af​5ee697ace63bb680856b6de7292e90ad；函数片段SHA256 86cb0a3b4674280595ad2708230e5a5b​37c2701f76dba0361961154574e012e7</span>

<span id="p2920">alembic/alembic/command.py  stamp  行729至793</span>

<span id="p2921">文件SHA256 40fa925f798b81fb4f35c8bc8deb25af​5ee697ace63bb680856b6de7292e90ad；函数片段SHA256 7e168bda1fcaeb6a5717d8d324caec2b​b91860f58b7c67cc62f59f3c9e7b3633</span>

<span id="p2922">alembic/alembic/command.py  upgrade  行475至476</span>

<span id="p2923">文件SHA256 40fa925f798b81fb4f35c8bc8deb25af​5ee697ace63bb680856b6de7292e90ad；函数片段SHA256 01d80d725e45c6871e22c96537e7ee00​3db9675708fb2e9be5695e340364dc5a</span>

<span id="p2924">pillow/src/PIL/Image.py  &#95;decompression&#95;bomb&#95;check  行3577至3597</span>

<span id="p2925">文件SHA256 04050c2d4dd67931ce8c3cfdbc49ac4a​6944d379d037c8f1d5eeeb67fba29a10；函数片段SHA256 37d8d2a2d803acbaa79e1ef2e87f956d​0bca6ddd2ecdde7fef04d94d97a11de8</span>

<span id="p2926">pillow/src/PIL/Image.py  open  行3600至3730</span>

<span id="p2927">文件SHA256 04050c2d4dd67931ce8c3cfdbc49ac4a​6944d379d037c8f1d5eeeb67fba29a10；函数片段SHA256 888ffce651ec7a50b8e1d87c57e850ee​578869b9c2db69d48cd01b1d0301ff28</span>

<span id="p2928">pdfplumber/pdfplumber/page.py  extract&#95;tables  行481至486</span>

<span id="p2929">文件SHA256 ef423b47ed5a2a467275277f4a672ac2​a1b8a1af103aa424248f85d5a0be4bba；函数片段SHA256 cc34c3f99a4f307f8c8abc505c16961d​2c220cf665d0c306190eb94400d131ac</span>

<span id="p2930">pdfplumber/pdfplumber/page.py  extract&#95;text  行529至530</span>

<span id="p2931">文件SHA256 ef423b47ed5a2a467275277f4a672ac2​a1b8a1af103aa424248f85d5a0be4bba；函数片段SHA256 6cfcebaa7bf01d41743da8eff9f86760​624a73ceaa464f88c772671ab9f19710</span>

<span id="p2932">xlrd/xlrd/&#95;&#95;init&#95;&#95;.py  open&#95;workbook  行84至185</span>

<span id="p2933">文件SHA256 926b88133f1cbad6ad1a38d6dc499a02​94c481c1e672c628d027161ffb61d8fd；函数片段SHA256 587be315ffc406103c12530366e42715​0b08d58e3560521dd2264e632d84a534</span>

<span id="p2934">python-docx/src/docx/api.py  Document  行19至31</span>

<span id="p2935">文件SHA256 d77539ea23d2336b4c44311bd373a649​94240c03e6c068dfc68b189164b6b5c7；函数片段SHA256 33f94fced9f3ea17fe6a8521184ee5a6​705d0eac1c20ce3beb065281768e01cb</span>

<span id="p2936">openai-whisper/whisper/audio.py  阅读行段 &#91;&#91;110, 157&#93;&#93;  文件SHA256 36ed287b2de3eaf40207cd2a44a8d45d​57ea5c212a39df07401d4fcb4d5a5a1a</span>

<span id="p2937">openai-whisper/whisper/transcribe.py  阅读行段 &#91;&#91;128, 225&#93;&#93;  文件SHA256 848b82877500d6fb8f0b91bee7a08ac6​7ef670a113591d11b494848d263ad0f6</span>

<span id="p2938">openai-whisper/whisper/model.py  阅读行段 &#91;&#91;174, 250&#93;&#93;  文件SHA256 473491a97554ad1d0beaaef6fe91d965​f12785b466b93ebb61024307b50ad683</span>

<span id="p2939">openai-whisper/whisper/decoding.py  阅读行段 &#91;&#91;272, 300&#93;, &#91;535, 565&#93;&#93;  文件SHA256 94084fedc5af74cabf8e1883a8555270​0057081f00ea669ad49435ecb29039db</span>

<span id="p2940">openai-whisper/whisper/timing.py  阅读行段 &#91;&#91;163, 221&#93;&#93;  文件SHA256 bb091c973c428697012f0f8d1b4f5f3a​605cd93c5d1c129957f712a6a878a59c</span>

<span id="p2941">cryptography/src/cryptography/hazmat/primitives/asymmetric/ed25519.py  阅读行段 &#91;&#91;1, 120&#93;&#93;  文件SHA256 99b7df2efb3edcf8020de835ad05d55e​1ec62e7b6554be004e390811ce29b793</span>

<span id="p2942">cryptography/src/rust/src/backend/ed25519.rs  阅读行段 &#91;&#91;66, 81&#93;, &#91;132, 153&#93;&#93;  文件SHA256 f2928ec984a915b1c62abb173b79f660​d00f293f4d870016f19697f68a557305</span>

<span id="p2943">PyYAML/lib/yaml/&#95;&#95;init&#95;&#95;.py  阅读行段 &#91;&#91;74, 135&#93;&#93;  文件SHA256 b19dfcc333d6a75dfd73073901164507​252f271b41d3b5f7d85510033a0547a7</span>

<span id="p2944">python-dotenv/src/dotenv/main.py  阅读行段 &#91;&#91;97, 113&#93;, &#91;388, 443&#93;&#93;  文件SHA256 697eb33eee75d78b73db61eaf96bf9a6​547548c1811c93501b67e056e5470dea</span>

### <span id="p2945">固定上游补充来源与阅读范围</span>

<span id="p2946">以下记录补充研究的固定源文件及摘要。文件取得不代表全部函数均深审；实际机制范围以正文和所列行段为准。精确部署身份缺失者仍保持未核。</span>

<!-- table-14 -->
| <span id="p2947"><strong>文档与Parquet上游文件及深读行段</strong></span> | <span id="p2948"><strong>文件SHA256</strong></span> |
| --- | --- |
| <span id="p2949">bs4/bs4/&#95;&#95;init&#95;&#95;.py<br />211–290 BeautifulSoup.&#95;&#95;init&#95;&#95; inputs；350–497 builder selection, prepare&#95;markup, error and success cleanup；658–676 &#95;feed</span> | <span id="p2950">90e007f82a9fc5bcf22a8df3b395b7bc​5245e54d65cd68fd51ca12a414718d4e</span> |
| <span id="p2951">bs4/bs4/builder/&#95;htmlparser.py<br />148–230 start/end/data events, duplicate attributes；413–517 prepare&#95;markup and feed</span> | <span id="p2952">4ab8d0bee2fc48a3ab5f28f33611355d​3049a46b25a44d4b2bedc1d6f9bbfebd</span> |
| <span id="p2953">bs4/bs4/element.py<br />534–558 get&#95;text；648–673 decompose；3293–3337 CSS delegation</span> | <span id="p2954">a109bc64af4fd5137b4e739ac254b9c1​d518c2cb36391d21e59113e95b862641</span> |
| <span id="p2955">bs4/bs4/css.py<br />59–68 missing soupsieve；162–200 select</span> | <span id="p2956">fe6fe5ff84865879d8eb6d15276d63fe​a407d515f7a7dd6c6157a680ac5a2ec3</span> |
| <span id="p2957">reportlab/src/reportlab/platypus/doctemplate.py<br />898–971 handle&#95;flowable；1030–1112 build/endBuild；1301–1329 SimpleDocTemplate.build</span> | <span id="p2958">15d6585be6c6e26e8db33e8df1836063​e643c7cbd53c5a20a7d1a2b10a05d717</span> |
| <span id="p2959">reportlab/src/reportlab/platypus/paragraph.py<br />1873–1937 &#95;setup/wrap；1966–2051 split；2509–2550 breakLinesCJK</span> | <span id="p2960">c9f4a40a05dba9878b52f9d25231eaa2​e51fc4db4be95c742adaa77dc1e91ce8</span> |
| <span id="p2961">reportlab/src/reportlab/platypus/paraparser.py<br />3211–3237 parse and dispatch</span> | <span id="p2962">60ec07084e217fb1d6dd5b20282a6751​364108086df241afb486d2de8713923c</span> |
| <span id="p2963">reportlab/src/reportlab/platypus/frames.py<br />132–190 Frame.&#95;add</span> | <span id="p2964">61a06c1f20fa9550c5bd7c87bac935ce​7539c91f827196ecb94cd3d24f8dd895</span> |
| <span id="p2965">reportlab/src/reportlab/platypus/tables.py<br />2177–2201 Table.split</span> | <span id="p2966">c2a7699cb9d6d984a42fa56e52119aaf​9fdae7337e6f5649754102925055b7cb</span> |
| <span id="p2967">reportlab/src/reportlab/pdfbase/ttfonts.py<br />1231–1289 splitString；1303–1345 addObjects</span> | <span id="p2968">9df9d24832e36a8db85408845558fe25​08580d8565f3b0447033c11f0ab3a2c7</span> |
| <span id="p2969">reportlab/src/reportlab/pdfbase/pdfdoc.py<br />192–225 SaveToFile</span> | <span id="p2970">22019a5fae551f3b430b666e568e5ba0​d199376b59474675f96a659de8cd0a86</span> |
| <span id="p2971">reportlab/src/reportlab/pdfgen/canvas.py<br />1297–1312 save/getpdfdata</span> | <span id="p2972">a5583a68a867e903b3b4d28e5c60ac59​04fc812fa8dae2aa50d709461fd2a290</span> |
| <span id="p2973">duckdb-python/src/duckdb&#95;py/pyconnection.cpp<br />301–312 read&#95;parquet registration；1777–1813 FromParquet；1882–1908 Close/Interrupt；2235–2268 Connect</span> | <span id="p2974">a2028c581d1f28c3732e3067bdd5b457​bb8c8619f92a938fc2dd302b9bf1b179</span> |
| <span id="p2975">duckdb-python/src/duckdb&#95;py/pyrelation.cpp<br />818–835 ExecuteInternal/ExecuteOrThrow；851–875 FetchOne/FetchMany</span> | <span id="p2976">21658a597f1d93bcef58c286b3ef3b25​72756c5eaba3777222f896be4db9e0da</span> |
| <span id="p2977">duckdb-python/src/duckdb&#95;py/pyresult.cpp<br />74–117 FetchNext；132–170 Fetchone/Fetchmany</span> | <span id="p2978">9117fe99b115d68432c5ca690ecb350a​e12688b88040e8d2a82e0c8e1071dfe8</span> |
| <span id="p2979">duckdb/extension/parquet/parquet&#95;reader.cpp<br />58–82 ParseParquetFooter；869–914 reader initialization；1290–1323 InitializeScan；1395–1585 row-group and vector scan; selected read, not complete function</span> | <span id="p2980">154d773db508da80652fbd0a5d1ab59e​f44fe92f7e391c45b3cfd619cfc89b8d</span> |
| <span id="p2981">duckdb/extension/parquet/parquet&#95;extension.cpp<br />851–856 read&#95;parquet/parquet&#95;scan alias registration</span> | <span id="p2982">75de902adf05226ba14579fb4416f25c​e6679a8f0e5e9125697870624e4e5423</span> |
| <span id="p2983">duckdb/extension/parquet/column&#95;reader.cpp<br />268–322 PrepareRead page type；401–505 PreparePage and DecompressInternal；507–584 PrepareDataPage encoding；607–707 ReadData and ReadInternal</span> | <span id="p2984">7700a83b6a24c828c941c576739c3648​1c09ed6a48d97f29eb8e629b90d96de6</span> |
| <span id="p2985">duckdb/extension/parquet/reader/struct&#95;column&#95;reader.cpp<br />30–76 StructColumnReader.Read</span> | <span id="p2986">19bab51571b92d732d41052d4efcdfdd​27e5b8e2377f87d60b33947236e252cc</span> |
| <span id="p2987">duckdb/extension/parquet/reader/list&#95;column&#95;reader.cpp<br />78–110 ListColumnReader.ReadInternal prefix</span> | <span id="p2988">fcc7b091ff6d5a61e7e6ee8a22d7d2c8​784229d407a679471e8fb921926926ec</span> |

<span id="p2989"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/__init__.py">MrBitBucket/reportlab-mirror src/reportlab/&#95;&#95;init&#95;&#95;.py</a></span>

<span id="p2990"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/VERSION.txt">MrBitBucket/reportlab-mirror VERSION.txt</a></span>

<span id="p2991"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/CHANGES.md">MrBitBucket/reportlab-mirror CHANGES.md</a></span>

<span id="p2992"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/README.txt">MrBitBucket/reportlab-mirror README.txt</a></span>

<span id="p2993"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/LICENSE">MrBitBucket/reportlab-mirror LICENSE</a></span>

<span id="p2994"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/platypus/doctemplate.py">MrBitBucket/reportlab-mirror src/reportlab/platypus/doctemplate.py</a></span>

<span id="p2995"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/platypus/paragraph.py">MrBitBucket/reportlab-mirror src/reportlab/platypus/paragraph.py</a></span>

<span id="p2996"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/platypus/paraparser.py">MrBitBucket/reportlab-mirror src/reportlab/platypus/paraparser.py</a></span>

<span id="p2997"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/platypus/frames.py">MrBitBucket/reportlab-mirror src/reportlab/platypus/frames.py</a></span>

<span id="p2998"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/platypus/tables.py">MrBitBucket/reportlab-mirror src/reportlab/platypus/tables.py</a></span>

<span id="p2999"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/pdfbase/ttfonts.py">MrBitBucket/reportlab-mirror src/reportlab/pdfbase/ttfonts.py</a></span>

<span id="p3000"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/pdfbase/pdfdoc.py">MrBitBucket/reportlab-mirror src/reportlab/pdfbase/pdfdoc.py</a></span>

<span id="p3001"><a href="https://raw.githubusercontent.com/MrBitBucket/reportlab-mirror/c4c83349b7272094f7413f726dcf206dbde7836d/src/reportlab/pdfgen/canvas.py">MrBitBucket/reportlab-mirror src/reportlab/pdfgen/canvas.py</a></span>

<span id="p3002"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/src/duckdb_py/pyconnection.cpp">duckdb/duckdb-python src/duckdb&#95;py/pyconnection.cpp</a></span>

<span id="p3003"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/src/duckdb_py/pyrelation.cpp">duckdb/duckdb-python src/duckdb&#95;py/pyrelation.cpp</a></span>

<span id="p3004"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/src/duckdb_py/pyresult.cpp">duckdb/duckdb-python src/duckdb&#95;py/pyresult.cpp</a></span>

<span id="p3005"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/LICENSE">duckdb/duckdb-python LICENSE</a></span>

<span id="p3006"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/.gitmodules">duckdb/duckdb-python .gitmodules</a></span>

<span id="p3007"><a href="https://raw.githubusercontent.com/duckdb/duckdb-python/b236c8194ed14c7a7c685e0534dde501cc855b3a/pyproject.toml">duckdb/duckdb-python pyproject.toml</a></span>

<span id="p3008"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/parquet/parquet_extension.cpp">duckdb/duckdb extension/parquet/parquet&#95;extension.cpp</a></span>

<span id="p3009"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/parquet/parquet_reader.cpp">duckdb/duckdb extension/parquet/parquet&#95;reader.cpp</a></span>

<span id="p3010"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/LICENSE">duckdb/duckdb LICENSE</a></span>

<span id="p3011"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/parquet/column_reader.cpp">duckdb/duckdb extension/parquet/column&#95;reader.cpp</a></span>

<span id="p3012"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/parquet/reader/struct_column_reader.cpp">duckdb/duckdb extension/parquet/reader/struct&#95;column&#95;reader.cpp</a></span>

<span id="p3013"><a href="https://raw.githubusercontent.com/duckdb/duckdb/d8cdaa33fda8df955cc76ef58a280f68f4cd43fa/extension/parquet/reader/list_column_reader.cpp">duckdb/duckdb extension/parquet/reader/list&#95;column&#95;reader.cpp</a></span>

<!-- table-15 -->
| <span id="p3014"><strong>训练与Atom固定源文件</strong></span> | <span id="p3015"><strong>文件SHA256</strong></span> |
| --- | --- |
| <span id="p3016"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/nn/modules.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/nn/modules.py</a></span> | <span id="p3017">f7ab2160681e2f089caae80d6fd283ac​6a9b9f1b82269e6f395c3b046faf606e</span> |
| <span id="p3018"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/functional.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/functional.py</a></span> | <span id="p3019">520a9e9d3afba11124734df60e48a27e​38b6389305df888834405b435e285817</span> |
| <span id="p3020"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/autograd/_functions.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/autograd/&#95;functions.py</a></span> | <span id="p3021">77ca54c87b69ad470ac73e5d7dde9494​8f20de9de8b8764957728bc29831f37f</span> |
| <span id="p3022"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/optim/adamw.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/optim/adamw.py</a></span> | <span id="p3023">da6b56da8475cf2eb5591e68114501d1​59b4e40f9367c463a3324dc202aa263b</span> |
| <span id="p3024"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/optim/optimizer.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/optim/optimizer.py</a></span> | <span id="p3025">2e07a06ea0736e4e6ce7bb821207264a​a5c2e7044718c88021b7bae3a15ddf2e</span> |
| <span id="p3026"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/backends/cuda/ops.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/backends/cuda/ops.py</a></span> | <span id="p3027">d58fa0a0c053d5a0ecd1e93d847531d5​e0226a0bd8048472ee0ca632464cc20f</span> |
| <span id="p3028"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/bitsandbytes/cextension.py">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;bitsandbytes/cextension.py</a></span> | <span id="p3029">a7ce4d7bcb504bf7d268ce96658dbe83​2804b6f6ed999f61eaf2beeb9385c9bd</span> |
| <span id="p3030"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/csrc/kernels.cu">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;csrc/kernels.cu</a></span> | <span id="p3031">a88d7a522b21b3d6e50cacad890c0c3a​c44ad17b5f205c4b34ae91995ba1e5d6</span> |
| <span id="p3032"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/csrc/ops.cu">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;csrc/ops.cu</a></span> | <span id="p3033">8e49f02cb671dba082d1c32b2c7fbea3​ca943211038acdd8c95acefaea3e5113</span> |
| <span id="p3034"><a href="https://raw.githubusercontent.com/huggingface/trl/v0.22.2/trl/trainer/sft_trainer.py">huggingface/trl @v0.22.2&#10;trl/trainer/sft&#95;trainer.py</a></span> | <span id="p3035">8df4a7f671a6b838c26b3e8870bdc83c​20d78fe5811dfa38e08bc536d538c8e3</span> |
| <span id="p3036"><a href="https://raw.githubusercontent.com/huggingface/trl/v0.22.2/trl/trainer/sft_config.py">huggingface/trl @v0.22.2&#10;trl/trainer/sft&#95;config.py</a></span> | <span id="p3037">1f77b55a4ca912b81639a64ee595e5de​9b98f84fd4c4d52f2564d04774ebf5b2</span> |
| <span id="p3038"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/src/transformers/trainer.py">huggingface/transformers @v4.56.2&#10;src/transformers/trainer.py</a></span> | <span id="p3039">67d86e8dddc37e6c6fc611d595166eb7​956afb1faa07633008033e43ac04d095</span> |
| <span id="p3040"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/src/transformers/integrations/bitsandbytes.py">huggingface/transformers @v4.56.2&#10;src/transformers/integrations/bitsandbytes.py</a></span> | <span id="p3041">511ec139809c9d80e08b2ae6cd7ccb43​91087532bc1f1b4d943b5930da9e547a</span> |
| <span id="p3042"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/src/transformers/quantizers/quantizer_bnb_4bit.py">huggingface/transformers @v4.56.2&#10;src/transformers/quantizers/quantizer&#95;bnb&#95;4bit.py</a></span> | <span id="p3043">838ac986c3a7f61a07c41728d270e086​8eb540aee5c8550716475b96ffe329ef</span> |
| <span id="p3044"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/src/transformers/tokenization_utils_base.py">huggingface/transformers @v4.56.2&#10;src/transformers/tokenization&#95;utils&#95;base.py</a></span> | <span id="p3045">2e2dada865cce42b73387240716a12ff​5c0a56977cfd680dc8fa937b0dc0ef51</span> |
| <span id="p3046"><a href="https://raw.githubusercontent.com/huggingface/transformers/v4.56.2/src/transformers/modeling_utils.py">huggingface/transformers @v4.56.2&#10;src/transformers/modeling&#95;utils.py</a></span> | <span id="p3047">fde37eeec1333d2022b9f925907f7075​03d4199b7946a890adbd170b9c3a307f</span> |
| <span id="p3048"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/LICENSE">kurtmckee/feedparser @v6.0.14&#10;LICENSE</a></span> | <span id="p3049">9f5e92783fd9beb2a9de76acda32a8f9​6ee8552a2b566e3923f037f0d754222a</span> |
| <span id="p3050"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/pyproject.toml">kurtmckee/feedparser @v6.0.14&#10;pyproject.toml</a></span> | <span id="p3051">6a9f0ed8846e3c39f355128e51da89b3​8224976961e1e3bdd2363bfc48b1536c</span> |
| <span id="p3052"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/feedparser/api.py">kurtmckee/feedparser @v6.0.14&#10;feedparser/api.py</a></span> | <span id="p3053">00f5414a23b161146607a88b8b94d8f1​5b9076ce9a8f9d92c5c6d1f173f72371</span> |
| <span id="p3054"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/feedparser/mixin.py">kurtmckee/feedparser @v6.0.14&#10;feedparser/mixin.py</a></span> | <span id="p3055">d1f0a225f0cfac36343949e7847dd563​e9b726fd7a17e0a7e4ffb7a85b3064fc</span> |
| <span id="p3056"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/feedparser/sanitizer.py">kurtmckee/feedparser @v6.0.14&#10;feedparser/sanitizer.py</a></span> | <span id="p3057">ad96e3fe10b69c2164fd64e282144d8f​32164628b16943b49b15e0bc13cae73b</span> |
| <span id="p3058"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/feedparser/__init__.py">kurtmckee/feedparser @v6.0.14&#10;feedparser/&#95;&#95;init&#95;&#95;.py</a></span> | <span id="p3059">a10280c5a4350666c6ffdfa8f5f6a658​ea8be6ac2c8c65fb796a8a94969827e5</span> |
| <span id="p3060"><a href="https://raw.githubusercontent.com/bitsandbytes-foundation/bitsandbytes/0.50.2/csrc/gemm_4bit.cu">bitsandbytes-foundation/bitsandbytes @0.50.2&#10;csrc/gemm&#95;4bit.cu</a></span> | <span id="p3061">0af029821fa01814ec630cb8637c10fe​e92ebaa9a847c16434f15b4c5e97ab6b</span> |
| <span id="p3062"><a href="https://raw.githubusercontent.com/kurtmckee/feedparser/v6.0.14/setup.py">kurtmckee/feedparser @v6.0.14&#10;setup.py</a></span> | <span id="p3063">656a0b108c668e248a638c507327a336​4005a904714fcf1c6423a583fd9cbdc5</span> |

### <span id="p3064">构建工具及许可补充来源</span>

<span id="p3065">本表的源文件摘要对应所链接的单个官方文本。归档成员另列包内相对路径、成员SHA256及整包归档SHA256；同一归档链接下多个成员具有不同摘要，不应混作包摘要。</span>

<!-- table-16 -->
| <span id="p3066"><strong>构建工具与许可的官方来源及包内文件</strong></span> | <span id="p3067"><strong>对应摘要 类型明确分列</strong></span> |
| --- | --- |
| <span id="p3068"><a href="https://raw.githubusercontent.com/withastro/compiler-rs/v0.4.1/LICENSE">astro-compiler</a></span> | <span id="p3069">官方源文件 SHA256<br />ee92354a87bc4a402e022fa15e10a6c7​13136aba84c46095dccc2b8091132806</span> |
| <span id="p3070"><a href="https://raw.githubusercontent.com/evanw/esbuild/v0.28.2/LICENSE.md">esbuild</a></span> | <span id="p3071">官方源文件 SHA256<br />b40ec5baec7bb34fa5b1c09521fa3cd5​2d5fad7adafed74932a2010d3612a681</span> |
| <span id="p3072"><a href="https://raw.githubusercontent.com/lovell/sharp-libvips/v1.3.3/README.md">sharp-libvips</a></span> | <span id="p3073">官方源文件 SHA256<br />52f8b2931fa6d496c792a2ed80817741​4ac24f2f87b667bb13fbc21bf1d99758</span> |
| <span id="p3074"><a href="https://raw.githubusercontent.com/napi-rs/napi-rs/@napi-rs/wasm-runtime@1.2.4/LICENSE">wasm-runtime</a></span> | <span id="p3075">官方源文件 SHA256<br />3f1ce66533302df3a32edbfdfc0b78f0​dd34659e4c1f5817162e5ea3c2297215</span> |
| <span id="p3076"><a href="https://raw.githubusercontent.com/rolldown/rolldown/v1.2.9/LICENSE">rolldown</a></span> | <span id="p3077">官方源文件 SHA256<br />23ecfff35a5a2e80d92142f75228912c​3b1abc4b5a8337a821ff4397e2f9f734</span> |
| <span id="p3078"><a href="https://raw.githubusercontent.com/rolldown/rolldown/v1.2.9/THIRD-PARTY-LICENSE">rolldown-third</a></span> | <span id="p3079">官方源文件 SHA256<br />a877291d800ed43692f3f9ae09d8e01c​c6f7293ad39d43896059c188ffbb8b7c</span> |
| <span id="p3080"><a href="https://raw.githubusercontent.com/lovell/sharp-libvips/v1.3.3/THIRD-PARTY-NOTICES.md">libvips-third</a></span> | <span id="p3081">官方源文件 SHA256<br />25ffcfa69e28b1913ced27ec778b90f2​4911a1bb3021253577e8b0af55db0d49</span> |
| <span id="p3082"><a href="https://raw.githubusercontent.com/lovell/sharp-libvips/v1.3.3/LICENSE">libvips-packaging</a></span> | <span id="p3083">官方源文件 SHA256<br />b40930bbcf80744c86c46a12bc9da056​641d722716c378f5659b9e555ef833e1</span> |
| <span id="p3084"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/LICENSE">satteri-LICENSE</a></span> | <span id="p3085">官方源文件 SHA256<br />902c04ca47795eb6e9b2a2f178a9d9e6​2f5330988a8d6e1818ee33aeb0f426c1</span> |
| <span id="p3086"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-mdxjs-rs/license">bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-mdxjs-rs/license</a></span> | <span id="p3087">官方源文件 SHA256<br />191f8cb444ca61a0a04730684bd05f7a​1643c2ecb9353b6b6534988c9456d43d</span> |
| <span id="p3088"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/LICENSE">bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/LICENSE</a></span> | <span id="p3089">官方源文件 SHA256<br />f70f9e40f496ca88ab5f624c7aea80eb​60ad1e21d8b7dbb3c22ded4ea97292d0</span> |
| <span id="p3090"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third_party/CommonMark/LICENSE">bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third&#95;party/CommonMark/LICENSE</a></span> | <span id="p3091">官方源文件 SHA256<br />3026a329eb5a8c5814f48bb1047970ac​e2a7d877c4973401a24b5563d76e345a</span> |
| <span id="p3092"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third_party/GitHub/LICENSE">bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third&#95;party/GitHub/LICENSE</a></span> | <span id="p3093">官方源文件 SHA256<br />c22e885f33b821bddb24cf007145e554​0655b6c0f403e49e6c76a93c28e6d9a9</span> |
| <span id="p3094"><a href="https://raw.githubusercontent.com/bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third_party/commonmark.js/LICENSE">bruits/satteri/b3d38e1e341c809b20b76a655e9b1601d11bd1f0/crates/satteri-pulldown-cmark/third&#95;party/commonmark.js/LICENSE</a></span> | <span id="p3095">官方源文件 SHA256<br />6cc4b9b28cf68e5bd20f9e94859a85cd​e35095ef4f9d0f7385b0b6166642f50b</span> |
| <span id="p3096"><a href="https://raw.githubusercontent.com/ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/cli.ts">ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/cli.ts</a></span> | <span id="p3097">官方源文件 SHA256<br />59ecbd5fdd15202bfdc1bcee03f55416​6f8bbf5a500cb5716d7d965755381990</span> |
| <span id="p3098"><a href="https://raw.githubusercontent.com/ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/detector.ts">ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/detector.ts</a></span> | <span id="p3099">官方源文件 SHA256<br />6e3f701d0d485ba6898e50a7082d3306​74dea048e1b9320835a5e508be6fca11</span> |
| <span id="p3100"><a href="https://raw.githubusercontent.com/ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/index.ts">ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/index.ts</a></span> | <span id="p3101">官方源文件 SHA256<br />4433579d4d2649e6989d27fc3c590b0b​b59f49c9eb54d19602cc32982fe916a4</span> |
| <span id="p3102"><a href="https://raw.githubusercontent.com/ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/providers.ts">ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/providers.ts</a></span> | <span id="p3103">官方源文件 SHA256<br />0dffd3cbee8893f4c885a1f05d052097​5b491ab6075087ab257c05ee9cf29306</span> |
| <span id="p3104"><a href="https://raw.githubusercontent.com/ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/types.ts">ascorbic/am-i-vibing/7e343f755e33876bf17a614af821e90005349a98/packages/am-i-vibing/src/types.ts</a></span> | <span id="p3105">官方源文件 SHA256<br />7e01bd6dca1f98f68af484af06ceae67​17a052c7ef1f1131e76b630a51ca0132</span> |
| <span id="p3106"><a href="https://raw.githubusercontent.com/ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/index.ts">ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/index.ts</a></span> | <span id="p3107">官方源文件 SHA256<br />917439eebd87b6e7b46637db34c9287f​29d6a88016578bd2faada3b5fe1ebd50</span> |
| <span id="p3108"><a href="https://raw.githubusercontent.com/ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/lib/unix.ts">ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/lib/unix.ts</a></span> | <span id="p3109">官方源文件 SHA256<br />c6cfb45722afd3d63d3ca6471fd01191​b6375e895e4803c0a7252f74a75205d8</span> |
| <span id="p3110"><a href="https://raw.githubusercontent.com/ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/lib/windows.ts">ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/lib/windows.ts</a></span> | <span id="p3111">官方源文件 SHA256<br />9f6e0930816b914da017c984f7ececd5​449a408f43d8223b80bec0a8489cf800</span> |
| <span id="p3112"><a href="https://raw.githubusercontent.com/ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/types.ts">ascorbic/process-ancestry/45004fd6155437eef40a632877a567db1b9addc5/packages/process-ancestry/src/types.ts</a></span> | <span id="p3113">官方源文件 SHA256<br />11a4186867ea2ff9eb9501493cad485b​4c1cd8f280c73f593f6a5a9f28d55b50</span> |
| <span id="p3114"><a href="https://registry.npmjs.org/am-i-vibing/-/am-i-vibing-0.4.0.tgz">am-i-vibing-0.4.0.tgz&#10;包内 package/dist/cli.mjs</a></span> | <span id="p3115">成员文件 SHA256<br />e4bebc9b2fb104f1bb4e915dae231b0b​e890528a48d08d531421150f766d4f1d<br />整包归档 SHA256<br />5e59f6fd20148e9753923d787b8dc9b6​623a647fcb05cccb8c40af75cfd44f5a</span> |
| <span id="p3116"><a href="https://registry.npmjs.org/am-i-vibing/-/am-i-vibing-0.4.0.tgz">am-i-vibing-0.4.0.tgz&#10;包内 package/dist/detector-Boc&#95;-HQ9.mjs</a></span> | <span id="p3117">成员文件 SHA256<br />c9811f95d0c629744c333973f845f4ae​0ef8d15f586f6e36c8cb3aba62efed0c<br />整包归档 SHA256<br />5e59f6fd20148e9753923d787b8dc9b6​623a647fcb05cccb8c40af75cfd44f5a</span> |
| <span id="p3118"><a href="https://registry.npmjs.org/am-i-vibing/-/am-i-vibing-0.4.0.tgz">am-i-vibing-0.4.0.tgz&#10;包内 package/dist/index.mjs</a></span> | <span id="p3119">成员文件 SHA256<br />30351a8a480508d88869868fa6a135f4​918b3dddf4ab405f31927dad40df3985<br />整包归档 SHA256<br />5e59f6fd20148e9753923d787b8dc9b6​623a647fcb05cccb8c40af75cfd44f5a</span> |
| <span id="p3120"><a href="https://registry.npmjs.org/process-ancestry/-/process-ancestry-0.1.0.tgz">process-ancestry-0.1.0.tgz&#10;包内 package/dist/index.js</a></span> | <span id="p3121">成员文件 SHA256<br />c645d5c77e3c06758921a089e0bcb95e​2296151c84c7d80b51ea9e7ca3ae152e<br />整包归档 SHA256<br />b73a85f002681f3fd87ae9112e7b11bb​29a06bc90be2e359010c6a7d709a4ecf</span> |

<span id="p3122"></span>

# <span id="p3123">附录 固定发行依赖与声音候选补核</span>

<span id="p3124">研究截止 2026年10月18日 00时25分 UTC    文档更新 v11</span>

## <span id="p3125">旧报告说法定位与更新解释</span>

<span id="p3126">以下页码均指原报告标示页码，不是本版PDF物理页码。每条保留历史说法，说明新证据关闭了什么、仍未关闭什么。旧报告不同章节使用“上游hash”“部署hash”“源码未取得”时并不总是同一证据层级，不能合并为单一结论。</span>

### <span id="p3127">原第14页与第25页</span>

<span id="p3128">旧说法或范围：“Unsloth精确发行源码…仍待核”“精确发行物源码尚未取得”。</span>

<span id="p3129">最新限定：本轮取得官方固定wheel并验证SHA256，仅读取归档文字成员，已核部分许可与训练导入源文件。因此“尚未取得发行物”已过时；实际Triton补丁、全部kernel及部署二进制闭包仍未核。原tag读取失败仍是历史事实。</span>

### <span id="p3130">原第15页与第26页</span>

<span id="p3131">旧说法或范围：Unsloth声明Apache 2.0、Zoo声明LGPL，包内许可未核。</span>

<span id="p3132">最新限定：包级METADATA声明仍准确，现已补到文件级反例：AGPL的COPYING、Studio源码及Zoo pad&#95;token等。不能继续把“包内尚未核”当最新状态，也不能据若干文件将整包/产品/权重一律归为AGPL。</span>

### <span id="p3133">原第30页与第31页</span>

<span id="p3134">旧说法或范围：“未取得精确Unsloth发行源码到…完整对应”“未下载/安装这些发行物”。</span>

<span id="p3135">最新限定：完整运行映射仍未闭合；“未下载”仅限旧截止时点。此次下载两个wheel但未安装/执行，官方文件hash已实算一致。第31页可选Studio许可提示不意味着非Studio无AGPL，pad&#95;token静态导入链提供反例。</span>

### <span id="p3136">原第33页与第35页</span>

<span id="p3137">旧说法或范围：先下载核包内许可；仍缺两包固定发行源码/完整许可。</span>

<span id="p3138">最新限定：下载及部分成员许可静态核对已完成，后续任务应转为实际使用模块、全发行物/依赖许可分类及部署构建物审阅；不能把“已拿到wheel”写成“完整许可闭包已通过”。</span>

### <span id="p3139">原第35至36页</span>

<span id="p3140">旧说法或范围：LGPL发行声明的使用与交付审查范围。</span>

<span id="p3141">最新限定：这些一般边界仍保留，但不能把该章节直接用于涵盖Zoo全部成员。新增AGPL成员及pad&#95;token头部only/or-later冲突，须按实际文件和使用/修改/提供方式单独审阅；无整产品必须开源、禁止商用等法律结论。</span>

### <span id="p3142">原第107至108页</span>

<span id="p3143">旧说法或范围：Unsloth及Zoo行列“精确上游/部署hash未取得”。</span>

<span id="p3144">最新限定：旧第31页同时列有官方发行页hash，形成范围混读风险。最新应拆开：上游wheel文件身份已实算验证；部署wheel/native identity仍未取得。表内旧状态保留为历史账，不应作为当前已核范围。</span>

### <span id="p3145">原第14页 第25页及第27至28页</span>

<span id="p3146">旧说法或范围：PEFT/datasets/safetensors未取得真实精确版本。</span>

<span id="p3147">最新限定：该缺口仍成立。checkpoint要求14包版本字典与批准摘要匹配，普通NF4八包门未显式列三包；新补发行约束只能缩小可选范围，不能反推摘要、证明兼容或替换成最新版。</span>

### <span id="p3148">原第56页与第165页</span>

<span id="p3149">旧说法或范围：NF4 base&#95;revision&#95;state为UPSTREAM&#95;UNSPECIFIED；固定权重清单。</span>

<span id="p3150">最新限定：本轮模型卡仍未提供原始基础commit转换证明。清单中的预期hash不等于本次下载权重后验证；未下载大权重，不声明数值等价、转换可重建或LoRA可互换。</span>

### <span id="p3151">新增声音及Quickstarts研究</span>

<span id="p3152">旧说法或范围：旧报告不能作为这些新增候选的集成或许可验收。</span>

<span id="p3153">最新限定：Qwen3 TTS固定版本、tokenizer与音色条件、transformers等式冲突，以及Quickstarts当前commit根许可/服务边界见后文。没有产品故障实测、声音质量实测、API授权或已完成移植。</span>

## <span id="p3154">完整补核研究正文</span>

### <span id="p3155">序境模型依赖研究补核 固定发行物 复建边界与新增声音链</span>

<span id="p3156">研究时间：2026-10-18 00:25 UTC。性质：只读研究；不是法律意见、商业分发验收或执行许可。原 20B 基础目标保持，小模型、多模态和多语言是补充。没有修改产品、数据库、运行环境或 GitHub；没有安装/导入所下载代码、运行模型、训练、下载大权重或调用外部模型 API。</span>

### <span id="p3157">1  去重基线与研究方法</span>

<span id="p3158">已读 owned&#95;ai&#95;research&#95;20261018 的主报告、许可证增补，voice&#95;postproduction&#95;research&#95;​20261018/mobile&#95;voice/report.m​d，第三方盘点最新 followup&#95;training&#95;libraries/REPORT.md 与固定发行元数据，以及 Claude Quickstarts 历史 LICENSE&#95;SERVICE&#95;REVIEW.md。产品基线是第三方盘点 main4dab 副本，commit 4dab98ed6357133da9307de846180e​d4f7bba5f5，不把恢复旧副本当最新部署。</span>

<span id="p3159">既有工作已覆盖：TRL 固定源码读取、text-only loss 与 tokenization 差异、checkpoint safetensors 不代表无 pickle、Whisper 不是 TTS、12 语 ASR 与 10 语 TTS 不同、App 私有声音包不等于通用权重。这些不重复作为新发现。新的问题是：发布的 wheel 实际含什么许可；TTS 与 20B 的环境是否可共存；固定权重与原基座、音色条件的可重建关系是否闭合。</span>

<span id="p3160">方法：官方 PyPI release JSON → 官方文件地址 → 仅下载两个普通 Python wheel 到研究目录 → SHA256 与 PyPI 声明比较 → 用标准库 zipfile 仅读取文字成员，未执行归档内代码。另读取 GitHub/Hugging Face 官方元数据并将 main 解析为 commit 后读取固定原文。对模型仓库仅读模型卡和 config，不下载权重。所有成功读取 URL、大小、哈希见 SOURCE&#95;MANIFEST.json 与 ADDITIONAL&#95;SOURCE&#95;MANIFEST.json。未成功的 LICENSE 路径另列 READ&#95;FAILURES.json。静态检查/反例不是动态兼容性实验。</span>

### <span id="p3161">2  最高优先级新增发现 固定 Unsloth wheel 是混合许可发行物</span>

#### <span id="p3162">问题与原证据</span>

<span id="p3163">旧增补只确认 PyPI 元数据：Unsloth 2026.9.12 声明 Apache-2.0，Zoo 2026.9.8 声明 LGPL-3.0-or-later。该观察正确，但不能替代实际文件级许可闭包。两版 PyPI 发行日期均为 2026-09-28。</span>

<span id="p3164">官方固定来源：</span>

<span id="p3165">- https://pypi.org/pypi/unsloth/​2026.9.12/json</span>

<span id="p3166">- https://pypi.org/pypi/unsloth-​zoo/2026.9.8/json</span>

<span id="p3167">已下载并本地验证：</span>

<span id="p3168">- unsloth-2026.9.12-py3-none-any.whl：SHA256 0b0a8d5694c693ff7a5183b1df073a​2b045f503193d76a0beec1696d1fef​6013。</span>

<span id="p3169">- unsloth&#95;zoo-2026.9.8-py3-none-any.whl：SHA256 740aacbb70f6f735ef367905cd753d​321b3088aaff404ebfb4f1cdf9f62e​56e8。</span>

#### <span id="p3170">文件级结果与反例</span>

<span id="p3171">1. Unsloth dist-info/METADATA 第 8 行声明 Apache-2.0；dist-info/licenses/LICENSE 为 Apache2 文本，但同目录 COPYING 是 AGPL3。studio/LICENSE.AGPL-3.0 及 Studio 源文件头明确 AGPL-3.0-only。</span>

<span id="p3172">2. Zoo METADATA 第 8 行声明 LGPL-3.0-or-later；licenses/LICENSE 为 LGPL3，COPYING 却为 AGPL3。不能简单用 COPYING 覆盖所有文件，也不能忽略它。</span>

<span id="p3173">3. 更关键，AGPL 并不只在 Studio：unsloth&#95;zoo/pad&#95;token.py 第 1 行 SPDX 标为 AGPL-3.0-only，第 4 行同样如此，但第 6–7 行模板正文允许 version 3 或更晚，存在原文口径冲突，需要上游/法律审阅澄清。</span>

<span id="p3174">4. 静态可达路径：Unsloth unsloth/models/&#95;utils.py:144 导入 unsloth&#95;zoo.tokenizer&#95;utils；Zoo tokenizer&#95;utils.py:611 导入 .pad&#95;token。Unsloth tokenizer&#95;utils.py:920 另有条件导入 fix&#95;pad&#95;token。因此“删去 Studio 即能保证训练链无 AGPL 文件”已有直接反例。</span>

<span id="p3175">5. Unsloth 核心目录还发现 dataset&#95;num&#95;proc.py、models/&#95;custom&#95;dtype.py、models/fp8&#95;to&#95;nf4.py、models/grouped&#95;linear&#95;lora.py 等 AGPL 文件头。扫描归档内 Python 文件前 20 行，共找到 623 个含 AGPL 的文件头（包括大量 Studio/CLI 文件），详细记录在 AGPL&#95;FILE&#95;MAP.json。此数字不是完整许可分类数量，也不是实际运行模块数量。</span>

<span id="p3176">提取许可原文/成员哈希见 sources/unsloth&#95;wheel&#95;members.json、sources/unsloth-zoo&#95;wheel&#95;memb​ers.json；训练相关导入证据见 sources/pad&#95;token&#95;import&#95;evide​nce.json。只把这些作为文件许可及静态导入事实，不推定所有组件同一许可，不推定全部序境产品必须开源，也不凭解释器导入就作法律链接结论。</span>

#### <span id="p3177">产品适配与下一步</span>

<span id="p3178">保持 20B 目标，但在批准安装/交付训练镜像前必须明确：实际 wheel、用到的模块、修改内容、内部训练还是向客户分发、是否网络提供相关修改程序、应提供的许可/源码/通知材料。按实际构建物审阅，不能以模型权重 Apache2 替代运行库条款。若需上游澄清，先拟问题，未经许可不联系第三方。本研究未替换版本或规避许可证。</span>

### <span id="p3179">3  可重建依赖 补到了范围 不应伪造精确版本</span>

#### <span id="p3180">问题与原版本</span>

<span id="p3181">main4dab/lumenis/system/ai&#95;gat​eway/owned&#95;training.py:510–515 固定 8 个 NF4 包；PEFT/datasets/safetensors 不在该常量。owned&#95;training&#95;checkpoints.py:46–49 的 14 包集合包含三者，:285–292 按批准摘要验证，:1249 读取运行版本。config/ai-owned-foundation.json:163、219 保留框架 lock SHA 220e8e688ce0fb05779c5f7f640476​bf928c11e185e00c0552cb3cf8b3a6​ea21。</span>

<span id="p3182">本轮限定 main4dab 的 JSON/TXT/MD 检索只找到上述摘要，未得到三包精确版本原文。摘要不能反推出版本。既有 followup&#95;training&#95;libraries/ve​rsion-evidence-search.json 空结果仅说明其限定范围没有发现，不代表历史环境从未记录。</span>

#### <span id="p3183">新补官方发行约束</span>

<span id="p3184">Zoo 固定 wheel METADATA:24 要求 peft&gt;=0.18.0 且排除0.11.0；:32 对 datasets 给出 &gt;=3.4.1,&lt;5.0.0，并排除4.0.&#42;、4.1.0、4.4.&#42;、4.5.0。Unsloth 固定 wheel METADATA:36 则要求 datasets&gt;=3.4.1,&lt;4.4.0 并排除4.0.&#42;、4.1.0。这是多个可选版本的约束交集，不是部署锁，也不是任取范围内版本已兼容。Unsloth 声明 Zoo&gt;=2026.9.8，本产品才进一步锁具体 Zoo 版。</span>

<span id="p3185">反例：同样满足范围的两个 datasets 版本可能具有不同 Arrow、map、缓存和传递依赖；pip 成功解析不能复现之前 checkpoint 的 framework&#95;lock 摘要。即使版本字符串一致，本地补丁与 wheel 内容仍可能不同。</span>

<span id="p3186">结论：普通训练依赖可重建性仍未闭合，但缺口已从“未知上游约束”缩小为“缺实际完整 lock/wheel/native identity”。下一步先取受控历史 checkpoint manifest 中的 framework&#95;versions 原文或原环境锁/安装收据；随后逐版本核 PEFT target&#95;parameters、datasets 行处理、safetensors 读写。未经授权不连接/修改环境，不选最新版填空，不把 CPU 统计栈替换进训练栈。</span>

### <span id="p3187">4  NF4 权重固定 不等于基座转换可重建</span>

<span id="p3188">问题：已批准原基座 openai/gpt-oss-20b@6cee5e81ee8​3917806bbde320786a8fb61efebee 与 NF4 变体 @093fba6992ef5a7152481afec0bdf​ca1ac486998 是否能证明同一原始基座转换而来？</span>

<span id="p3189">产品 config/ai-owned-foundation.json 明确标 NF4 base&#95;revision&#95;state=UPSTREAM&#95;U​NSPECIFIED。官方固定 NF4 模型卡 https://huggingface.co/unsloth​/gpt-oss-20b-unsloth-bnb-4bit/​blob/093fba6992ef5a7152481afec​0bdfca1ac486998/README.md 第 2–4 行给 base&#95;model 名称和 Apache2 元数据，但没有把基础 checkpoint commit 写成产品批准 SHA。本轮 LICENSE 固定路径404，不把模型卡声明冒充已获该仓库独立许可证全文。</span>

<span id="p3190">静态反例：固定最终文件 hash 可验证“同一制成品”，却不能证明“从指定基础 commit + 指定量化工具/参数重建得相同制成品”。产品配置的文件 hash 是预期身份，不是本次下载权重后实算的结果。本轮没有权重，不能确认数值等价、量化误差或其上 LoRA 与原版可互换。</span>

<span id="p3191">资源说明：配置所列原始三份权重约13.76GB十进制，NF4四份约12.53GB十进制；这是文件体积，不是 VRAM、反量化峰值、optimizer/KV/activation 或训练预算。保持原20B目标和设备门，不据体积推断16GB卡一定能训。</span>

<span id="p3192">下一步：补发布方 conversion provenance（原 commit、量化脚本/依赖、dtype、排除模块、随机/确定性设置），再在批准资源上验证文件 hash、重载和同输入差分；若上游未公开则诚实保留不可完全重建，并由批准者决定是否接受该依赖风险。</span>

### <span id="p3193">5  Qwen3 TTS 新增声音能力的精确身份与环境冲突</span>

#### <span id="p3194">来源版本</span>

<span id="p3195">- 官方代码 commit 022e286b98fbec7e1e916cb940cdf5​32cd9f488e，提交时间2026-03-17，pyproject 声明 qwen-tts0.1.1。</span>

<span id="p3196">- Base 权重候选 Qwen/Qwen3-TTS-12Hz-0.6B-Base@​5d83992436eae1d760afd27aff78a7​1d676296fc，HF lastModified 2026-01-29。</span>

<span id="p3197">- 独立声学 tokenizer Qwen/Qwen3-TTS-Tokenizer-12Hz@​7dd38ad4e9bad454aae9cd937d0cd5​77604fe229，同日更新。</span>

<span id="p3198">- 两模型卡均声明 Apache2；固定 LICENSE 路径均404，仓库 siblings 不含独立LICENSE。代码仓库有 Apache2全文。不能把这三层写成同一件已完整法律验收的资产；基础训练语料完整权利链亦未获得。</span>

#### <span id="p3199">新的确定性反例 不能与20B配方原样共用一个环境</span>

<span id="p3200">固定代码 pyproject.toml:22–24 要求 transformers==4.57.3 和 accelerate==1.12.0，而产品 NF4 固定 transformers==4.56.2。相同环境不可能同时满足两个精确等式。此为文本约束矛盾，无需安装即可确证；不说明模型本身无法并存于同一机器。应研究独立受控 runtime /进程边界及明确通信合同，不能偷偷升级原20B训练依赖。其余 gradio/librosa/torchaudio/soun​dfile/sox/onnxruntime/einops 多未精确锁定，CUDA/FlashAttention亦须分别锁。</span>

#### <span id="p3201">voice prompt 究竟是什么</span>

<span id="p3202">固定 qwen&#95;tts/inference/qwen3&#95;tts&#95;m​odel.py:41–51 的 VoiceClonePromptItem 包括 ref&#95;code、ref&#95;spk&#95;embedding、x&#95;vector&#95;only&#95;mode、icl&#95;mode、ref&#95;text；:356–454 用声学tokenizer和说话人embedding生成这些内容；:614–626 生成后还使用参考code长度进行音频拼接/切分。</span>

<span id="p3203">所以音色包不是一个任意向量或完整独立模型。Base 仓库本身包含 speech&#95;tokenizer/ 子目录；独立Tokenizer仓库用于单独编码/训练数据准备，不能仅凭名称一致推断嵌套权重与独立repo字节相同。必须分别固定实际使用文件hash、采样率、codebook/tensor形状、tokenizer版本和主模型适配关系。</span>

<span id="p3204">反例：仅导出 speaker embedding 不等价于带 ref&#95;code/ref&#95;text 的完整上下文克隆；传入另一 checkpoint 接受同shape也不保证同音色/文本对齐。官方复用内存中的 prompt&#95;items 示例没有建立跨App长期序列化标准，更未证明 .voicenpc 与其等价。自定义安全容器应保存最小字段与版本，不直接反序列化不可信 pickle。</span>

#### <span id="p3205">功能 数据与资源边界</span>

<span id="p3206">官方 finetuning/README.md:1–9 在该固定版本只承诺单说话人微调，多说话人是未来功能；:12–30 要求audio、text、ref&#95;audio，建议同一参考音频；:35–42 使用独立Tokenizer CUDA提取code。它不同于数秒参考条件克隆，不可将两者统称已训练个人完整模型。</span>

<span id="p3207">语言集合仍为中英日韩德法俄葡西意，缺阿拉伯/印地/印尼；小模型/语音不替换20B文本目标。模型卡97ms是上游声明，未测本环境/手机/产品端到端首包、网络、打断和恢复，不能作为SLA。0.6B只给出参数量，不覆盖全部tokenizer/缓存/峰值内存。无声样、听测、训练数据、GPU实验，质量与耗时均未验。</span>

<span id="p3208">产品适配：先明确播客离线成片与实时交互各自预算；外部手机录音+准确文本+授权可作为输入，私有音色包导入仍需格式样本和许可。实际安装、声音上传、训练与产品集成都须另获明确授权。</span>

### <span id="p3209">6  Claude Quickstarts 只补当前版本边界 不重复旧适配设计</span>

<span id="p3210">本轮将官方main固定为9ec32b91df50b0d4906cae64b13c62​98055ff40d（2026-10-07）。LICENSE为MIT，保留版权及许可文本要求；范围是源码/文档，不提供Claude权重，也不授权序境使用托管/API。https://github.com/anthropics/​claude-quickstarts/tree/9ec32b​91df50b0d4906cae64b13c6298055f​f40d</span>

<span id="p3211">README:3、7说明集合基于Claude API并要求API key；Managed Agents例子涉及session、vault、webhook、cron等托管语义。复制界面或调度片段不等于可以离线运行整项目。已有历史适配报告仍可复用，但它的旧SDK版本研究不能自动覆盖当前新增示例和锁文件。</span>

<span id="p3212">本轮仅确认当前入口说明和根许可，未取得每示例精确传递依赖闭包，未调用服务。合法代码二改应先按批准文件范围建立NOTICE、逐文件/依赖许可，再由序境已有Gateway、Task、SourceUse和本地持久化合同替代云服务语义；这是一项待批准的实现，不是研究中已经完成。原20B继续承担其获准能力，不能把Quickstarts当作免费Claude能力。</span>

### <span id="p3213">7  下一步验证顺序及停止边界</span>

<span id="p3214">1. 最优先：审阅固定wheel混合许可与训练可达文件，明确实际安装/分发方案；任何许可裁决交给合格审阅者，不自动更换训练栈。</span>

<span id="p3215">2. 找到现有framework&#95;versions原文与相应wheel/native锁，才开展三包精确版本研究。没有原文就保持未知。</span>

<span id="p3216">3. 冻结NF4转换溯源与最终权重验证计划，分别区分来源可重建和产物可复验。</span>

<span id="p3217">4. 为TTS单独设计环境锁及音色条件数据合同；以用户授权的本人声样做中英韩专名、数字、长文本、首包/打断/取消、音色撤回验证。样本与模型、tokenizer身份全部绑定，真实运行需另批。</span>

<span id="p3218">5. Quickstarts只移植获准的许可代码机制，不引入其API、托管、模型服务或自动外传。</span>

<span id="p3219">停止条件：研究报告与可核原文完成；缺少真实环境/权重/声样/法律判断的项目标为未验，不以静态材料升级成“已商用可用”。本次未触发任何产品晋升、训练、权限授予或对外通信。</span>

## <span id="p3220">本轮审核需要决定的事项</span>

<span id="p3221">一 请确认新增事实与仍未闭合的边界。原报告或本附录的版式QA通过不代表已获安装、商业分发或产品集成批准。</span>

<span id="p3222">二 在任何安装或交付之前，明确混合许可实际使用、修改、分发或网络服务方案，以及承担具体许可审阅的责任人。</span>

<span id="p3223">三 决定是否继续开展声音独立运行时方案、原训练锁和NF4转换溯源的具体研究或验证。认可研究方案仍不直接授权修改环境。实际模型加载、权重下载、训练、本人声音使用及产品集成须分别给出范围和预算。</span>

<span id="p3224">声音输入继续按外部手机制作本人声音材料或包后受控导入的方向研究；不因此新建采声App、上传声音或启动训练。旧Quickstarts适配研究继续保留，不能自动覆盖当前新增示例和锁文件。</span>

## <span id="p3225">证据清单与复核边界</span>

<span id="p3226">本附录对应70文件证据清单 FILE&#95;MANIFEST.json。清单列相对路径、文件字节数及SHA256，另有SOURCE&#95;MANIFEST、ADDITIONAL&#95;SOURCE&#95;MANIFEST及PRODUCT&#95;SOURCE&#95;MANIFEST记录来源。READ&#95;FAILURES保留固定LICENSE路径未成功读取的事实；未读取的独立许可全文不能由模型卡元数据代替。证据文件单独保存，未嵌入或执行下载代码。</span>

<span id="p3227">新证据正文SHA256 c0dd4e4be8ebd860e86585bb4740db​85abf62c4e80b4c180900a54666030​e564</span>

<span id="p3228">旧180页报告SHA256 12596e6ee2adba492743de4e0b0642​005fcfa2ef2ef37df2474f658e2ccf​ca30</span>

<span id="p3229">许可结论须由合格审阅者基于实际构建物、使用、修改和交付事实判断。所有未授权的安装、运行、训练、上传、产品集成及对外联系均不属于本次文档操作。</span>

## 转换附注

原文页脚仅含 Word PAGE 自动页码字段，无正文文字。Markdown 不保留分页及动态页码；正文段落、表格单元格内容、换行和超链接按原文顺序完整保留。
