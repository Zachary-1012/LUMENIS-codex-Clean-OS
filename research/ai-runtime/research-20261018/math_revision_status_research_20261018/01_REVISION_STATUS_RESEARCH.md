# 数学26篇官方版本与撤回状态补核

## 1. 结论和截至时间

2026-10-18 00:23–00:25 UTC（北京时间08:23–08:25）只读核查完成。26/26原论文的官方OpenAI发布身份、当前README、路径提交历史和目录对象均已对照。官方main两次读取均为原研究pin `1581d4cbdd69a0faf34b2089614fe2a814316a6a`，commit日期2026-10-12。26个论文目录对象与原pin完全一致，涵盖PDF及目录内配套文件；逐篇README内容亦通过Git blob SHA复算，全部匹配。26条路径历史均返回1项2026-10-06 Initial commit，非100项分页截断。

没有发现这26篇在已读官方README及发布history中的修订、撤回或勘误公告。这是官方发布渠道的定点观测，不是所有上游渠道无更正的绝对结论。arXiv ID/期刊DOI未在已读官方元数据中声明，跨渠道状态逐篇记录UNKNOWN。没有搜索不到就判定无撤回。

## 2. 原要求、既有研究与本次新增

原G143–169完整数学要求和九family 102/103/104/107/113/114/115/139/140原范围全部保留，随包baseline原样复制。旧27_REQUIREMENTS_NEXT_ACTIONS里的“24稿/两稿缺失”属于历史快照，已由math_research_completion_20261018的26/26、1121页、64视觉核页阅读记录更新；本次不回退，也不重复宣称又读1121页。

本次只推进G165的26篇官方发布版本状态观察。G160全文阅读已完成这一层；G161业务适用、G163训练、G164正式证明、G143–159/162真实工作流和G166–169真实财务/预算证据均不因此完成。没有修改G165现有候选补丁、失败计数、scope校验或产品执行状态。

## 3. 来源、版本与方法

来源为官方openai/math仓库，经已连接GitHub只读工具获取，未使用付费研究API。证据包括：两次main commit读回、当前root/preprints Git trees、26篇当前README完整内容、26篇路径commit历史、全库README/history。

当前root tree `45074722c918576d65b4c8be9686c76f508ba696`明确指向preprints tree `df0564b2deaab87e07854b6344d8c2f037682e77`。每篇当前目录tree与原研究recursive tree相同，由不可变Git对象内容地址推导PDF blob及配套目录未变；本次没有重新下载PDF字节。旧PDF和目录blob、当前blob及引用URL均在02台账、03逐篇报告。

官方README说明不同结果验证阶段不同、部分未形式化可能有问题；其版本政策是保留旧版并记录新版本。history当前记载2026-10-07的3篇撤回、14篇修订及13篇引用更新。明确撤回的是Weil classes、Kuga–Satake correspondences和products of K3 surfaces三篇，均不属于这26篇。此处不能推断这些跨领域撤回对26篇的所有间接外部数学依赖都已经审计。

官方来源：https://github.com/openai/math/blob/main/README.md ；https://github.com/openai/math/blob/main/history.md 。逐篇正式URL及OAI原ID见03报告。

## 4. 原结论影响与重读决定

26篇均无此次版本差分引起的全文重读范围。保留原26份阅读结论、假设、适用边界及依赖缺口。UG局部标签评估不是一般归约；stochastic104的CHANCE/折扣整数box/负最终阈值要求不变；103空间复杂度、107数值证书与张量证明、113/114/115计数采样的一般性和资源门槛、139 oracle复杂度与140下界性质不升级。

如果以后出现新commit或官方公告，先确认论文ID和版本链，再重读变更定理/证明/假设、引用及依赖闭包，重新评估受影响业务映射。不得用“README相同”替代独立证明验证。

## 5. 撤回与勘误状态的严格边界

逐篇状态为UNCHANGED_IN_OFFICIAL_RELEASE_SNAPSHOT与NO_NOTICE_IN_READ_OFFICIAL_README_AND_RELEASE_HISTORY，而不是NOT_WITHDRAWN或PROVEN。外部arXiv/期刊状态UNKNOWN；没有凭标题虚构arXiv号，没有全库全依赖撤回穷举，也没有检查论坛/社区争议来冒充正式更正。日期来自工具观测窗口与来源提交元数据；提交日期不等于论文标示日期。

本次状态截止观察窗口，不是未来持续监控保证，也不是“所有26篇最终正确”的评定。GitHub提交签名状态只涉及提交真实性，不证明数学。

## 6. 实际检查与未运行项

完成离线证据交叉核对：26身份、26 README blob复算、26目录相等、26 PDF blob可定位、26历史返回不足100项、两次HEAD相等、总页数1121继承一致。完整原始工具响应及基线目录树随包保留。

Lean/lake/Comparator、数值证书、算法、模型训练、数据库、产品代码、部署环境、产品HTTP/UI验收全部NOT_RUN。未安装软件、未触发源码build hook、未写仓库或生产数据。

## 7. 后续验收与可执行决定

原研究可继续用作研究与交接的版本固定依据，无需因为本次补核重读千页。正式证明仍需要固定toolchain、信任闭包、完整目标及另外明确授权。一般算法落地和实际业务验收分别保留原门槛。若要声称跨渠道“当前未撤回”，还须取得可验证arXiv/期刊身份及对应官方修订记录；当前不能给这种结论。

## 8. 交付清单与完整性

02_PAPER_STATUS_LEDGER.json为逐篇机器可读状态；03_PER_PAPER_VERSION_STATUS.md为逐篇人读报告；evidence保存工具原始响应和README；baseline原样保留原数学需求、阅读台账和补全报告。MANIFEST.json保存每文件SHA-256与字节数，SHA256SUMS供离线校验。报告是研究材料，没有赋予产品修改授权。
