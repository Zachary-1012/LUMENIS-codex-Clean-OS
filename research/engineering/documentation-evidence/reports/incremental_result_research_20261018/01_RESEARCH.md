# ORG-MECH-05：增量块、重放、用户编辑与父版本保存

## 1. 结论前置与版本

**SOURCE研究与自写参考实验；当前产品运行未验证。** 固定main为4dab98ed6357133da9307de846180ed4f7bba5f5。源切片完整保存，整文件SHA本轮实算；只声明receipt列出的阅读范围。

不能复制旧采用报告的旧断点：AI-01已有提交，产品有SSE。这里研究的是如何让既有链可靠交付有用的、可编辑、可保存的结果块，不把Browser画面流当Task成果流，也不派产品修复。

## 2. 当前源码实读及可复用边界

|位置|实际观察|适配边界|
|---|---|---|
|ai01_repository.dart:1–33；Core client:497–515|load及submitIntent均存在，提交task和ANALYZE|旧“只有读取”已不成立；未见块流订阅|
|experience_runtime.py:3920–4021|JSON校验、Permission、服务端scope、run_execution_chain、execution_id/status/evidence_recorded一次性JSON返回|提交存在不等持续结果、正常模型执行或GLOBAL可执行；当前trusted缺失明确not_executable|
|ai01_intent.dart:1–85|pending_approval与completed等严格解析；2xx不自动成功|复用状态真实性，不把其completed解释成已SavedWork|
|ai01_view_model.dart:83–170|submit不自动重试；refresh有generation过期防护；updateDraft保留用户输入；dispose阻断回调|当前代码未把结果正文写回draft，所以不能宣称它已覆盖用户文稿；未来块编辑需要更细版本绑定|
|web transport:1–42、112–163|普通HTTP收齐body；另有EventSource，onmessage只传data，onerror主动close，不自动续连|确实有流；没有将lastEventId、event type带入此返回类型。现新连接不能被当作自动延续旧游标|
|IO transport:125–177|检查200及text/event-stream，按data行组包，非data字段忽略|不等通用id/event/retry语义保留；现在用途须保留，不能无证宣称帧链故障|
|Core client:1494–1525；ai_browser_api.py:1020–1065|browserFrameStream消费上述传输；服务器重复核Actor/权限并no-store输出帧|帧可采用新鲜快照，不等每条业务增量都可丢弃；不复用帧存储为成果Truth|
|SavedWork:630–797|scope/Effect授权、BEGIN IMMEDIATE、同request同输入回放、同request异输入拒绝、parent一致、draft_digest、不可变artifact、提交前回调/权限/引用复核、独立重开回执|原Owner已有保存控制；勿新增平行版本库。幂等回放仍经当前授权/引用检查|
|SavedWork:968–1018|通用research/report局部修改需父SHA，记录Unicode codepoint偏移/父版本/原因；Task-owned和creation合同拒绝走此通用修订入口|流式任务不能偷用通用修订绕开任务Owner；人工更改要走正确现Owner|
|api_dual_domain.py:473–515、983–1051|幂等先于乐观revision冲突；save-request仅资源请求；save在before_commit复核业务revision，Shared持有持久receipt|原业务版本与结果版本双绑定；已保存旧版仍诚实显示SAVED_PREVIOUS_REVISION，不谎称当前|
|source_brief_tasks.py:1–85|复用SYSTEM TaskEngine；Actor/scope精确检查，进程身份与interrupted分开；旧任务JSON不算授权|断线重连读取结果与重启执行不同；不能凭旧任务持久化自动复工|

静态扫描*.py/*.dart的text/event-stream命中Browser；这是所扫代码类型/切片事实，不证明全仓或部署不存在其他stream。没有打开生产数据库、运行入口或账号。

## 3. 官方原始协议实读

- WHATWG HTML《Server-sent events》§9.2.2–9.2.6，页面显示2026-10-16更新，2026-10-17本轮读取。id支持续连标识，事件类型与data分开；EOF未完成事件不派发；close关闭传输。以上均不承诺业务持久化或效果恰好一次。[官方正文](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- RFC9110 §13.1.1：If-Match的强比较可防并发丢失更新；前置条件失败不执行修改。仅借鉴条件写语义，当前产品采用自己的expected_revision/父SHA合同，不声称已实现HTTP ETag。[官方正文](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1.1)

来源只读相应章节，未读全HTML标准或全RFC。原网页不作用户附件已读计数。下面是序境适配推论，非这些标准的业务保证。

## 4. 建议精确合同，落既有Owner

1. C6用现Task身份绑定run/attempt、Actor/scope及输入版本；C5结果块绑定block_id、块revision、源引用版本、父成果版本。字段名须映射现接口，不规定新增数据库/总线。只给既有受支持组件与动作，未完整/未校验块不可执行。
2. 传输收到、结构验过、已应用投影、可恢复持久化、正式保存五层分开。不能把浏览器收到id当服务端保存receipt，也不能把UI显示当SavedWork。
3. 恢复游标只指连续已确认前缀；出现seq1、seq3不得从3继续而丢2。乱序先缓冲或请求现Owner完整快照，需有界窗口/字节/时间上限；超界转显式重同步。生产需要窗口过期/游标丢失的snapshot路径，不能无限等缺段。
4. 同身份重复同内容幂等；同身份不同内容为合同冲突，不能静默吞掉。缺序完整块可用于明确“部分”阅读，但不能标全结果完成或提前执行依赖缺块的动作。
5. 人工编辑提高该块的编辑版本；生成结果必须携带生成基线。基线落后时保留人工文稿，显示可审核提案/差异，而非直接覆盖或全局重跑。无冲突块可独立继续。若需合并，调用原修订Owner明确采用，不凭模型自行合并业务事实。
6. 关闭页面/暂停阅读/取消任务/撤销已保存版本为不同动作。cancel_requested先阻止本地继续应用并等待原Task确认；不能用断开SSE证明执行已停。取消前已提交的artifact保留真实receipt；外部效果未知要对账，不能显示已撤销。读权限撤回立即阻断相应展示/操作；仅执行权限撤回不自动等于删除仍可读历史。
7. 保存携带原request_id、原work_id、准确parent_artifact与digest、业务revision和引用。丢失响应查回同receipt，不重新生成id造成重复版本；相同id不同输入拒绝。保存前与事务提交前复核权限/源/任务取消。新版本正常返回后再标保存，UI取消不删除已提交事实。
8. Undo采用正确Owner的新修订或既有回滚动作，保留父链，不改旧artifact。通用SavedWork本地修订只支持其声明kind，Task/媒体必须走专属现Owner。
9. 每段明确引用、完整/部分/冲突状态；最终核对全答一致性。计时分受理、首个有依据有用结果、首个真实可操作块、完整、保存；用同材料预算任务比较，p50/p95与准确性一起验。首token与动画不算有用。

## 5. 可复现反例与结果

python lab/event_sequences.py，21断言通过。序列覆盖重复、同id变内容、乱序/缺段、重连重复、人工修改后迟到、旧run、错scope、取消请求/确认区别、撤回读取、提前terminal、EOF、保存响应丢失、request复用冲突、陈旧父版本、撤权后重放、提交前绑定变化、Undo父链及UTF8长度。

关键反例：只记max(seq)会跳过缺失段；按到达顺序覆盖会让seq1压掉seq2；自动覆盖会抹人工编辑；重新发送新save id会生出多份版本；断线当完成会把部分成果升格。

附带限制观察：当前两个传输以String.length检查名为maxEventBytes的阈值。中文5个字符UTF8为15字节，可超过10字节但字符数仍5。这是固定源码计量单位差异的独立反例，未证明实际线上超限、攻击或产品运行故障；交原C6核定义/测试，不在研究中改产品。

实验模型没有网络、真实并发、事务DB、引用授权系统或平台UI；它是可复核逻辑反例，不是拟安装的新Task系统。模型未覆盖持久化崩溃恢复、跨设备冲突、缓冲上限、完整JSON/schema安全及所有排列，生产需要下面真实验收。

## 6. 真正待运行验收

原G14/G116/Experience§38保持OPEN。C2/C6/F在同main/现运行入口接线后验证：

- 正常业务材料→真实可用块→用户局部修改→保存新父版本→跨端重开；不止拒绝非法输入。
- 注入重复/乱序/缺段与断线，服务端确认游标/快照恢复；不要重新执行业务效果。
- 改稿、换scope、换run、源更正与旧回包竞争，人工内容保留，引用更正可追溯。
- 保存提交前取消/撤权阻断；提交后响应丢失能查原receipt；旧结果与当前业务revision明确区分。
- Web/Windows/macOS/Mobile实际焦点、选区、朗读/辅助技术、减少动画、网络断连，逐端证据。
- 实测已定义五段时间与错误率，不用研究21断言或旧smoke声称速度收益。

待研究之外：TTS停止失败与本地离线声音验证、Creator归因机制仍在原队列。原件字节缺口未因此减少。
