# 原REA三样本研究证据重建与深化

2026-10-18 北京时间；真实执行2026-10-17 21:28–21:29 UTC。Owner C6研发证据/连续性、C1采集/来源、C4媒体任务、C5证据/Artifact、F用户状态。原完整规划§20.4、全19组第14/15，关联原G185–187/J7/J8及媒体任务、浏览器/消息连续性要求。

## 结论与完成边界

原报告 saas_rea_scope.md 引用的三个官方样本已重新取得固定公开源码，使用已核官方REA 6.5.0真实静态分析，三次exit0、JSON可解析且有evidence_id，输入文件前后SHA256全部相同。新证据重建完成；历史原JSON没有找回，不把新文件冒充历史原件。Figma取固定当前官方commit（旧报告没有固定commit），另两项按旧报告精确commit；输入集合也显式记录，不能要求新旧图数必同。

|样本|固定来源|输入与新结果|
|---|---|---|
|Figma post-message|figma/plugin-samples@03131bef561eb25ee2b704e3b39e40acc70330e0|code.js/ui.html/manifest.json/LICENSE.md；6节点5边；64,355字节Evidence|
|Brandwatch旧Node客户端|BrandwatchLtd/node-brandwatch-api@661f5e1f5e3b29246c5db7e09ad7df11148e195f|lib/api.js、package.json、LICENSE；14节点13边；373,035字节Evidence|
|Runway轮询SDK片段|runwayml/sdk-node@4b0ae07d8bf62e414a216b8ea4c21440704c2c2e|src/lib/polling.ts、LICENSE；16节点15边；822,048字节Evidence|

只下载公开文件并作为惰性文本分析。未安装三个目标项目依赖、未执行下载JS/TS/HTML、未启动插件或浏览器、未登录/取token/请求付费API。REA自己的静态解析器实际运行；这是工具研究执行，非SaaS目标执行。

## 1. Figma：图缺失反例再次复现

官方固定文件：https://github.com/figma/plugin-samples/tree/03131bef561eb25ee2b704e3b39e40acc70330e0/post-message 。许可 https://github.com/figma/plugin-samples/blob/03131bef561eb25ee2b704e3b39e40acc70330e0/LICENSE.md 为MIT。

人工全文核读code.js、ui.html、manifest.json：code.js 1显示UI，3–9接收消息并延迟500ms发回；ui.html13监听pluginMessage，14–16按钮向parent.postMessage发消息。manifest指定figma/figjam、API1.0.0、动态页面访问及allowedDomains=[none]。这些是样本声明/源码，不等真实宿主运行权限验证。

REA再次明确ui.html第12行起1段内联JS未分析，graph coverage incomplete；summary.ipc.operations=0。因此“0 IPC”不是“没有通信”，更不是没有风险。程序图枚举偏向特定边界类型，非通用浏览器消息覆盖率。

适配：序境自己的UI↔业务调用应绑定schema/session/request ID/对象revision、大小与取消；迟到回包不能更新已经改版或撤权对象。样本的"*"用于演示，不能据此宣布Figma生产漏洞，也不能直接抄为序境安全默认。私有协同、渲染、存储、服务端授权与四端性能全未知。

## 2. Brandwatch：最小wrapper不等采集闭环

固定源：https://github.com/BrandwatchLtd/node-brandwatch-api/blob/661f5e1f5e3b29246c5db7e09ad7df11148e195f/lib/api.js ，同commit LICENSE为MIT。package.json标0.4.0/request ^2.36.0；这是旧仓维护/依赖事实，不推断现行Brandwatch服务状态。

全文静态观察：5–9设置请求默认超时240秒、无cookie jar、JSON；12–51构建请求；29–38旧apiHost/apiPort分支使用HTTP；43调debug时包含auth变量，45–48才写Bearer header并删auth；62–65动态生成HTTP动词函数。只说明代码路径存在，未提供凭据或证明日志实际泄漏。

新增适配结论：25使用_.defaults(options, requestOptions)，之后修改method/uri、删除url/auth，存在修改调用方options对象的静态可能；不能把一个带权限/身份的可变请求对象复用于并发任务。此处未执行underscore验证，标为源码推论而非运行结果。

该片段没有cursor遍历、增量水位、限流/重试、持久恢复或对账循环。REA的图不能把动态动词闭包补成完整采集器。选择：不引入旧wrapper依赖树，参考其边界反例；C1以现行官方endpoint合同实现adapter，C6分风险/权限，C5记录分页/缺失和真实取得量。现行API权限/数据限制仍按平台研究另核。

## 3. Runway：停止等待与远端任务必须分开

固定源：https://github.com/runwayml/sdk-node/blob/4b0ae07d8bf62e414a216b8ea4c21440704c2c2e/src/lib/polling.ts ，同commit LICENSE为Apache-2.0。仅此片段和许可，不是完整SDK依赖审计。

人工全文190行核读：普通任务87–131及workflow invocation145–190均封装轮询。基准6000ms、抖动±1500ms；默认timeout10分钟，null无限；成功返回，FAILED/CANCELLED抛对应错误，THROTTLED/PENDING/RUNNING继续。

较旧报告新增的精确边界：
- 初始等待发生在timeout计时之前（99–105；157–163）；create responsePromise等待也不计入该计时。因此10分钟不是端到端操作硬时限。
- AbortSignal只在轮询迭代开始检查；未传到retrieve调用或定时器，也不调用远端取消。它不能证明正在进行的网络请求立即中断，更不能证明远端任务取消。
- timeout判断在retrieve及下一次等待之后；请求耗时与轮询等待可超过名义阈值。未知状态最终也走超时错误，不能在前端把该错误一律解释为“远端失败”。
- workflow invocation和普通task有不同retrieve入口及错误类型；不能仅保留一个没有resource_type的taskID。

适配：C4持久保存provider、task/workflow类型、ID、创建意图/输入revision、状态观察时刻；C6本地cancel后远端状态unknown直到获准查询/取消确认；重开按原ID对账，不自动重生成造成费用。C5把生成成功与Artifact下载、hash/格式、权利/参数和可编辑保存分开。F显示停止等待、远端运行中/未知、归档待完成等真实事实；这些方案尚未产品实现。

## 4. 已做与未做的验证

已做：9文件固定公开取得；取回文本保持工具返回末尾换行语义；保存每文件来源/commit/SHA256/长度；三次静态分析；前后hash一致；JSON/evidence_id/exit检查；人工阅读全部目标逻辑文件及许可。

未做：SaaS登录/现场交互/HAR、远端API、目标代码运行、模块依赖补全、私有服务器推断、生产性能、全SDK和全平台覆盖。Figma旧原件无commit无法证逐字同一；原三历史JSON仍缺。新结果只关闭三份固定公开片段的重新分析证据缺口。

## 5. 可执行验收提案（未运行）

1. Figma式消息：错误schema/session、超大包、重复request、撤权后迟到回包、原对象已修订；图遗漏触发人工补核，不报无通信。
2. Brandwatch式adapter：可变options并发隔离、无HTTP回退、无敏感debug、cursor/限流/重试/幂等、字段缺失与真实计数分别验收。
3. Runway式异步：create后崩溃只retrieve；本地abort和远端cancel分开；retrieve悬挂/初始等待不冒端到端10分钟；未知状态不伪造失败；workflow类型准确；成功下载失败仍artifact_pending。

## 收据位置

rea_public_reconstruction/evidence/INPUT_MANIFEST_BEFORE.json：每文件固定官方URL、commit、字节数/hash。
rea_public_reconstruction/evidence/RUN_RECEIPTS.json：输入不变、三次exit、Evidence ID/hash、图统计、limitations。
rea_public_reconstruction/evidence/{figma,brandwatch,runway}_rea_analysis.json：完整新Evidence。
对应stderr.log/exit.txt保存完整进度与退出码。工具版本/发布完整性/安装锁见13报告。
