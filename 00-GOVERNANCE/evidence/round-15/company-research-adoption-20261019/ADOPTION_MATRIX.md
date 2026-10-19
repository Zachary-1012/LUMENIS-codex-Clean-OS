# 24项公司研究采用矩阵（独立候选，未写活跃root）

现行条款仅为部分等效要求，不代表全合同已经覆盖；完整范围由本次有界方案裁决补齐。代码路径仅核原Owner可复用入口，未作公司研究因果归属。

| 编号 | 采用决定/Owner | 现行部分等效证据 | 基线合同 | 合并后实现验收 |
|---|---|---|---|---|
| ATS-01 真实阶段与进度 | ADAPT C2/C6/F/C1/C4/C5 | 700行 | 以原Task/run/attempt和observed_at解释阶段；done/total必须同单位，total未知=null；成功须原成果Owner持久化读回。 | 断线重连；乱序/重复/旧attempt；阶段完成但持久保存失败；成功均可读回；未知进度不假百分比；任务间不串结果 |
| ATS-02 撤销、取消、恢复与补偿分开 | ADAPT C4/C5/C6/F | 1100行 | 编辑撤销绑定操作/选区及父版本；保存版本恢复形成新修订；取消须等安全边界；外部已发生效果只对账或经批准补偿。 | 撤销/重做/冷重开；并发版本冲突；取消后旧回调；可逆编辑真实恢复；已发生效果不假称撤销；保留序境原有回滚要求 |
| ATS-03 同任务跨端接续 | ADAPT C6/C5/C4/C3/F | 647行 | 接收端按task/work、workspace、source/resource revision重新鉴权；恢复合法选区/播放头及最后确认点，离线草稿与服务端稿分列。 | 过期链接；用户/工作区切换；双端编辑；撤权；接收端重新鉴权；不重新上传合法已有材料；四端独立实测 |
| ATS-04 按需最小权限与拒绝退路 | ADAPT C6/C1/C4/C5/F | 1510行 | 权限绑定actor/resource/action/purpose/expiry/version；仅实际需权限的动作请求，拒绝/撤权只阻相关路径，普通上传不添通用用途问卷。 | 拒绝麦克风；撤权；旧批准；多成员；无越权；拒绝仅阻断相关动作；普通上传无多余用途表单 |
| ATS-05 未知效果先对账 | ADAPT C2/C6/C3/C4/C5 | 1601行 | 原Effect Fence以意图摘要、幂等键、attempt及真实回执绑定；可能成功先读回，不重发；仅证实无效果的可重试失败按原预算退避。 | 成功后丢响应；重复提交；进程重启；旧参数批准；可能成功先对账；同意图无重复效果；unknown不假success |
| ATS-06 健康分层 | ADAPT C1/C6/F | 1567行 | 区分configured、鉴权检查、依赖健康、业务读回和覆盖；显示实际检查时间，未检查=NOT_VERIFIED，配置读取不触发隐式网络探测。 | 无token；无效/user；401/403/429；超时；撤权；status不暗中探测；健康需真实授权检查；/user成功不扩成仓库业务成功 |
| ATS-07 类型、单位与版本合同 | ADAPT C1/C3/C4/C5/C6/F | 1563行 | 原typed contract明确值/单位/分母/期间/时区/币种和来源时间；动作由真实能力与权限共同决定；空值、0及错误分列。 | 秒/毫秒；0/null；百分比/比例；DST/跨日；旧客户端；前后端单位一致；未知不变0；不猜币种/范围 |
| ATS-08 更新阶段透明并保工作 | ADAPT C6/C5/C4/F | 779行 | 复用release/recovery记录目标与实际build、兼容性、checkpoint和rollback artifact；更新前核未保存稿与活跃任务，恢复须实际读回成果。 | 迁移中断；空间不足；启动失败；旧客户端；真实备份可恢复；成果与项目可读回；不降低原取消/回滚要求 |
| ATS-09 同流程合法信息复用 | ADAPT C3/C5/C4/C6/F | 1045行 | 原SourceBrief→SavedWork→制作链传已确认问题、语言、约束及source_refs/version；用户新改优先，每次使用重验用途，Shared可空白开始。 | 切工作区；清Focus；后退；引用撤回；同一流程不重复合法已有输入；上下文不授权；独立Shared保留 |
| ATS-10 真实任务可访问性 | ADAPT F/C6/C4 | 1083行 | 状态语义可读且不抢焦点，拖拽有键盘/点按等价，zh/en/ko、200%字体与减少动态保全部操作；各表面分别验。 | 键盘；读屏；缩放；拖拽替代；中英韩；异步不抢焦点；状态可读；原生与Web分别验收 |
| ATS-11 同版真实成果门禁 | ADAPT M/C6/C1/C2/C3/C4/C5/F | 1119行 | 沿原门禁绑定source/build、依赖、输入、成果读回、失败与恢复；区分合成/真实数据/实机/生产/收益，未跑不记PASS。 | 干净启动；故障注入；取消/重启/撤权；四表面；未跑不算PASS；不同候选绿灯不拼接；测试数不代替真实业务 |
| ATS-12 可重现的原Owner交接 | ADAPT M/C1/C2/C3/C4/C5/C6/F | 113行 | 交接仅记录用户工作、原Owner/caller、合同、精确源码版本、失败复现和验收证据；跨Owner缺口归原责任，不另建管理层/队列。 | 三项跨Owner抽查；另一审阅者重现；证据能定位版本和责任；不新增管理层/队列；研究不冒充实现 |
| OA-ANT-T01 按问题选择编排复杂度 | ADAPT C2/C3/C5 | 8005行 | 确定性路径为普通业务基础，增强与有限并行沿原router/loop选择；输入、权限、质量门槛和父任务总预算固定后才比较收益。 | 同业务基线对照；固定数据/预算；重复trial |
| OA-ANT-T02 类型化呈现与动作同一可信边界 | ADAPT F/C2/C6 | 1126行 | 呈现建议绑定schemaVersion、task/run/attempt、sourceRefs、allowedActionId和resultVersion；Core校验事实/权限/动作，未知拒绝并保原视图与dirty稿。 | 未知字段、HTML/JS、伪授权、乱序旧回调测试 |
| OA-ANT-T03 持久任务与执行器解耦 | ADAPT C2/C6 | 1558行 | TaskEngine持有事实，DurableAdapter存可验证checkpoint，Artifact存成果；恢复核任务身份、输入/工具版本、当前权利和效果回执后续未完成步骤。 | 5个故障点冷重开；真实回执核对 |
| OA-ANT-T04 动作级持久审批 | ADAPT C6/C2 | 1603行 | 原Permission/Firewall/Fence绑定actor/scope/operation/resource/paramsHash/inputVersion/toolContractHash/expiry/attempt；执行前重查撤权，实质变化重批。 | 改变目标/参数/工具版本与重复点击负例 |
| OA-ANT-T05 精确上下文与记忆隔离 | ADAPT C2/C5/C6/F | 289行 | 项目/任务按ID引用可读原文、版本与当前scope；记忆是辅助材料非Permission；切任务保合法稿，复制配置不默认复制历史资料。 | 2成员2项目移入移出/撤权/导出缓存 |
| OA-ANT-T06 成果可编辑可冷开 | ADAPT C4/C5/F | 1119行 | 原Artifact/SavedWork保存可编辑源、导出版、parent revision、来源/权限；局部修改先审差异再新revision，冲突保双方，失败保上版及草稿。 | 报告/提案/播客完整保存导出冷开旅程 |
| OA-ANT-T07 评价看真实结果与人工代价 | ADAPT C5/C3/C6/F | 1036行 | Shared Evaluation核task/trial/trajectory/outcome及同版来源/运行/DB/测试；确定性裁判核权限/数值/引用，创意人工盲评校准，失败与超时保留。 | 保留集多trial+盲评校准+真实产物读回 |
| OA-ANT-T08 脱敏可观测性 | ADAPT C6/C2 | 1563行 | 沿原日志记录task/run/attempt/step、耗时、错误码、合同hash及权限化引用；秘密/客户原文不复制到遥测，外部trace默认关闭，访问重验scope。 | 合成哨兵覆盖日志、导出、备份、恢复 |
| OA-ANT-T09 协议互通不自动信任 | ADAPT C2/C6 | 1057行 | 既有发现→合同审阅→权限→隔离自测→启用→更新/回滚绑定schema hash/endpoint/version/audience/scope；变更须原Owner重新审阅，停用拒绝老session。 | SSRF/外部ref/恶意描述/撤权老session |
| OA-ANT-T10 累计预算与真实取消 | ADAPT C2/C6/F | 1603行 | 父子attempt沿原预算共同记已耗/预留，恢复重试不清零；软取消先停新步骤，工具能否硬停据真实边界，迟到结果先核效果再终态。 | 并发预留、重启余额、取消提交竞态 |
| OA-ANT-T11 少打扰的多任务审阅 | ADAPT F/C3/C6 | 1126行 | 原任务台按待决定/异常/可审成果/运行中组织；同主题通知合并但授权不混，审阅含结论、变化、证据、风险与最小决策，完整记录可读。 | 3并发任务与原体验对照 |
| OA-ANT-T12 智能呈现服务完整工作 | ADAPT F及现有C1–C6 | 1500,1871行 | CTH来源/比较/决策、BMP约束/方案/效果、Shared材料/编辑/版本、SYSTEM真实状态/恢复按原任务重组；原生组件执行，AI只提合法呈现，无AI可完成基础工作。 | CTH/BMP/Shared/SYSTEM，Web/Desktop/iOS按职责分别验 |

YEARLY PLAN已确认身份；仅current plan两处纠正，不改历史、不冒视觉完成。

规划增补在原研究章10.7后作为10.8，采用24行紧凑映射，不重写设计系统；具体来源/拒绝项/静态路径及原故障验收完整保留JSON。若规划base SHA变化，integrator按语义rebase，禁止覆盖publisher。
