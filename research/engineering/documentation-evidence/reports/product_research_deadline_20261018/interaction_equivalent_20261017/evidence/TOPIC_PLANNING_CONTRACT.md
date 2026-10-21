# 选题与嘉宾规划：独立审核原型合同

记录时间：2026-10-17 UTC。范围仅为新纯逻辑模块和测试；没有修改产品源码、数据库、运行环境或发起网络/API/模型调用。不是历史字节恢复，不是产品接通或视觉验收。

## 只读来源

以下路径相对于 `recovery_inspection_20261017/remote-main-readback/source/LUMENIS-codex-Clean-OS-main/`：

- `AGENTS.md` 当前首段：独立创作不依赖 CTH/BMP/品牌任务；基本业务不依赖 AI；结果、权限、Canonical 事实分离；用户无需选择算法或任意权重。
- `podcast_routes.py` `/api/podcast/topic-score`：真实调用 `podcast/intelligence/topic_scoring.py`，不是另一份 `topic_score.py` 旧公式。缺项返回 `input_required`，score/stage 为 null，非法输入返回 invalid_input。实际 route 的 weights 为 null（owner 没有 WEIGHTS 属性）。原型常量是源码公式的可检查说明，不能表示服务端返回了权重。
- `podcast/intelligence/topic_scoring.py`：十信号、分数公式与分类顺序。
- `tests/test_podcast_topic_signal_truth.py`：缺项、显式零、无类型转换、无 store 初始化、范围不可用及错误状态。
- `00-GOVERNANCE/LOOP-PLAN-20261014/product-plan-full.md` §14 P1/P3（行491/493）：逐项信号/来源，人工嘉宾三标准，提纲可编辑版本化。
- `contracts/experience/screen-specifications/BMP-08.md` 当前独立制作入口、增补选题卡要求及独立稿/音频制作路径。
- `00-GOVERNANCE/LOOP-PLAN-20261014/sketches/FULL-PRODUCT-SKETCH.md` §3.3（行188–199）、BMP-08（行674–725）：独立已有稿/音频入口，十信号缺项不评分，三个人工 Gate 不全局阻断。

## 数值合同

输入是 JS/Python 对应的有限 IEEE-754 双精度 0..1 数值或 null；不自动把字符串、布尔、undefined、NaN、无穷或越界数转为有效输入。省略的合法信号补 null，未知字段拒绝。任一 null 保持 score/stage=null，显式 0 是观测值。

分数为 round(100 × clamp(正向和 − 惩罚和, 0, 1), 2)。正向权重依次为 demand .16、timeliness .12、novelty .10、human_relevance .14、guest_fit .12、evidence .10、content_yield .10、distribution .06；惩罚 risk .05 + cost .05。正向满值无惩罚为90分，并非100分。先按原始数值计算，再舍入最终分数。API返回 signals 三位小数与计算输入精度不是同一回事；原型保留原始输入，不假造 API 响应。

roundTopicScore 使用精确二进制有理数与 BigInt 实现到百分位的 ties-to-even；不用 Math.round 或 epsilon。适用本合同有限非负 0..100 分值。各乘加顺序与 Python owner 一致，包含二进制表达误差。固定边界（2.675→2.67、1.125→1.12 等）和种子20261017的10,000组有限输入对照实际 Python owner，score及stage完全一致。有限测试不是全部可表示输入的穷尽证明。

分类顺序：score<35 rejected；否则 timeliness>=.85 now；否则 score>=75 soon；否则 score>=55 evergreen；其余 watch。缺分数或时效返回 null。

## 接口与保护

- `createTopicPlanning({title, originalText, sourceRef, signals})` 创建本地审核草稿。`originalText/sourceRef` 不可通过 reducer 改写；`editedText` 从原文初始化，之后独立修订。
- `topicPlanningReduce(state,event)` 返回新状态，不修改旧状态。edit-signal/edit-gate 使用 key/value；edit-text 仅 title/editedText；undo 恢复上一 draft 但 revision 继续递增。
- suggest 必须明确 simulation:true、id、baseRevision、signals、rationale。不调用 AI、不自动变事实、不修改手工值。部分建议信号采用 patch merge，遗漏字段保留当前观测，只有显式 null 才清空；未知字段仍拒绝。compareTopicSuggestion 提供当前与建议的分数及逐项差异。
- accept-suggestion/reject-suggestion 必须匹配当前建议 id。采纳要求 pending 且 baseRevision 等于当前 revision。任意手动编辑，甚至编辑后撤销，都不能令旧建议再次有效。拒绝不改变 draft。采纳可撤销。
- 嘉宾 gate 为 public_value（独特体验且有公共价值）、expression（有表达能力与意愿）、resonance（能引发共鸣）。三项仅允许 null/true/false；全部 true 才 qualified。AI建议无法写 gate。
- `canEnterPodcastPath` 中 owned-audio/owned-script 始终独立于评分和 gate；guest-outline 才检查三项人工判断。allowed 只表示审核原型流程可进入，不是媒体权益或生产权限许可：productionPermission 恒为 NOT_VERIFIED。
- `serializeTopicPlanning` 与 `reopenTopicPlanning` 采用严格 schema/字段/类型校验，保存 draft、history、revision、suggestion。历史最多32次（超出时淘汰最旧撤销点）；title最多500字符、sourceRef最多4000字符、原文/校对稿各20000字符，建议理由最多2000字符；序列化字符串最多4,000,000个UTF-16码元，重开在JSON解析前检查上限，保存超出预算明确拒绝。异常 JSON、旧版本、非法字段/数值/门控及异常历史拒绝，不静默归零或伪造成功。原文空白、CRLF、Unicode 保真。
- 本模块不实现产品保存；由视图保存本地 JSON 后重新读取验证。JSON 校验可发现结构损坏，不能鉴别攻击者伪造的有效数据或证明作者身份。不存在服务端签名、跨设备存储或产品权限验证。

## 实际验证

命令：`node --test review_working/tests/topic-planning.test.mjs`

2026-10-17：33 tests，33 pass，0 fail，0 skip。其中数值对照项执行 Python `-B` 只读导入源码 owner，对照10,000组固定种子输入；缺失只读快照时该项明确 skip，不伪报 parity。测试覆盖十信号各项缺失/非法值、显式零、权重与阈值、二进制舍入、不可变修订/撤销、模拟建议比较/采纳/拒绝/过期保护、三个 gate、独立音频/稿入口、保存重开和坏数据拒绝。

未执行浏览器操作、视觉验收、产品 API、真实 AI、真实音频制作或平台验收；这些不能由 Node 测试代替。

## 可独立交接的数值回归（2026-10-17 13:42 UTC）
新增 tests/fixtures/topic-owner-golden.json：从只读当前工作树 Owner 实际计算的256组固定随机数输入、分数与分类，附源码SHA256及来源说明。只包含合成人工数值，不包含产品源码或业务数据；34条选题模块测试实际通过。离开当前机器仍可运行该便携回归。原10000例Python实时对照保留，缺只读Owner快照时会明确跳过，不能把黄金样本对照说成当时最新Owner动态验证。未来Owner公式变化需先核合同再显式重新生成，不能为测试通过自动改预期。
