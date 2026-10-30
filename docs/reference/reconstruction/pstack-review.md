# pstack：原作者、实际内容与寰意的采用边界

2026-10-30。用户提供截图“pstack，58项技能”，并补充作者参与GrokBot。先研究原始公开文件，后依用户明确要求将适用方法落实到[仓内工程技能](../../../.agents/skills/oevira-pstack/SKILL.md)与开发入口；来源版本、方法及适配边界见下文。

## 身份与版本

- 原项目：[cursor/plugins/pstack](https://github.com/cursor/plugins/tree/main/pstack)，不是搜索结果里的社区镜像。官方[插件页](https://cursor.com/marketplace/cursor/pstack)列58项技能、2个子代理；本轮目录也计58项。
- [固定版本manifest](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/plugin.json)：0.15.36，作者Lauren Tan。GitHub主线本轮读回为`1ba91fc25c0977741dd0e267849e6234b037ed0a`，提交时间2026-10-29。11份已审技能与此commit内容逐一相同。
- [作者GitHub](https://github.com/poteto)指向[X @poteto](https://x.com/poteto)。[AMA主持人的记录](https://www.rasaljay.com/blog/grokbot-ama)确认她是pstack作者并参与GrokBot。X直读403、定向搜索未获得可可靠审读的原帖，不能称X原帖已核。第三方转载的PR数量、收入或团队结构未作为效果证据。
- [LICENSE](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/LICENSE)为MIT，版权Lauren Tan；若以后复制或改编实质内容，保留适用版权和许可。许可允许使用，不证明流程适合本产品。

## 已读范围

完整审读11份：poteto-mode、correct、architect、blast-radius、benchmark-checklist，以及principle-experience-first、principle-subtract-before-you-add、principle-prove-it-works、principle-outcome-oriented-execution、principle-model-the-domain、principle-encode-lessons-in-structure。README已查看说明/目录/部分末段；未逐一审读其余47份技能、全部playbook、脚本、适配器或自动化包。58是包目录数量，不是58项已采用。

## 值得落到寰意开发中的方法

| 原方法 | 针对寰意的实际问题 | 采用方式及边界 |
|---|---|---|
| [correct](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/correct/SKILL.md) | 同一错误反复提醒，规则加长却继续缩水或误报完成 | 追到错误成立的位置：错误对象归属先修边界，非法状态用类型/状态约束，确定性问题才加检查；最后补必要解释。用真实失败例证明约束能拦住。视觉和创意不可全编码时保人工评审，不能用关键词扫描代替。复用现有合同，不再造监督体系。 |
| [model-the-domain](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-model-the-domain/SKILL.md) | Work/Material/Artifact概括吞掉专业语义 | 事件、意见、决定、实际动作，公式、图表、声音、时间线各保真正结构与变化；共用权限版本，不共用一个万能正文。 |
| [architect](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/architect/SKILL.md) | 接口能返回，但调用者无法完成实际工作 | 先用调用者的完整操作确认输入输出、状态、取消和异常，再确定边界。已明确部分不重复开全仓设计，不据其默认值更换模型。 |
| [blast-radius](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/blast-radius/SKILL.md) | 局部修订破坏其他页、轨道、导出或异步任务 | 追消费者、格式关系、跨语言边界、持久版本和异步结果；用受影响业务证明保全，不仅搜索函数调用。 |
| [prove-it-works](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-prove-it-works/SKILL.md) | 编译、HTTP、文件生成或哈希被当专业交付 | 实际打开、操作、修改、保存、重开、导出及恢复。哈希只核身份/未改部件；需要专业质量、听审和真实用户任务的结果另外验证。 |
| [benchmark-checklist](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/benchmark-checklist/SKILL.md) | 90ms常量、微基准、测试数量冒用户体验 | 明确所测操作、输入规模、设备/版本、错误和分布；测端到端，解释瓶颈。90ms首次反馈与任务完成、播放连续性分开；不为美化数字关闭正常安全/恢复机制。 |
| [encode-lessons-in-structure](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-encode-lessons-in-structure/SKILL.md) | 已纠正的事实在下一轮又被丢失 | 可机械验证的约束纳入既有结构；不能自动化的专业判断明确评审对象/证据与责任，避免假装一条lint能懂产品。 |

## 不能照搬的部分

[Experience First](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-experience-first/SKILL.md)倡导较少但打磨好的功能。采用体验优先，**不采用缩减已批准范围**。[Subtract Before You Add](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-subtract-before-you-add/SKILL.md)可用于删重复路径和错误实现；替代行为未证明、用户数据与原始研究未保全时不据此删除。[Outcome-Oriented Execution](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/principle-outcome-oriented-execution/SKILL.md)允许有界中间状态，不允许把空壳或破坏现有工作当交付。

[poteto-mode](https://github.com/cursor/plugins/blob/1ba91fc25c0977741dd0e267849e6234b037ed0a/pstack/skills/poteto-mode/SKILL.md)包含默认模型/推理/速度调整、较宽外部执行权限、自动化和多方案代理流程。它们不取得本会话授权，不覆盖用户选择，不触发消息、部署、付费或安装。当前仍先完成全产品审计与规划审阅；前端视觉由根亲自处理。上游偏好少做前期规划，也不能覆盖本次明确的先审阅要求。

## 实际采用

仓内技能固定采用0.15.36的correct、architect、blast-radius、benchmark-checklist、model-the-domain、prove-it-works和encode-lessons-in-structure七项方法，保原来源与MIT许可。AGENTS与CONTRIBUTING链接同一入口，按具体任务使用，不维护第二套产品方案。

适配保留原方法的关键动作：从真实调用者推导领域结构；对反复错误优先修结构并用实际旧反例验证；跨格式、持久化及异步消费者追踪；直接读回结果；测性能时核实际执行、正确性、失败、瓶颈和波动。架构方法不执行上游默认模型/arena调度，证明质量不退化为哈希或关键词计数。未审的其余技能不自动启用，也不因安装数量声称全部采用。

这是开发工具的采用，不是产品接入，也不把技能操作展示给产品用户。可机械验证的缺陷修进现有检查；无法自动判定的专业质量继续按适用真实任务和评审验证。
