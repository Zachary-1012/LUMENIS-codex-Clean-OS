# 2026-08-30 架构决策历史记录

**归档状态：HISTORICAL / NOT EXECUTION。** 本文件只记录旧 Z-Brand 阶段的架构背景，不再提供研发指令、施工顺序、模型默认值或发布授权。原始正文在本文件 Git 历史版本中保留，不另建执行规则副本。

## 当时的背景与可追溯问题

原记录研究旧 CTH-POMS、ZBMP、Development-Command-Console 的关系，以及同一 Core、主体筛选、发布时间、Evidence、风控失败、备份恢复和敏感客户数据边界。这些是历史关注点，是否构成现行义务，以当前唯一产品架构、Source Owner 和实际源码为准。

原版本列有 Ollama、本地模型、旧三套运行关系和先 CTH 后 BMP 的研发顺序。**这些不是当前序境生产、研发或发布命令**，不得据此选择模型、启动窗口、冻结业务范围。

## 当前定位

现行唯一仓库执行路由为 AGENTS.md；产品架构由 00-GOVERNANCE/LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md 拥有；业务职责和历史有效要求由 00-GOVERNANCE/LUMENIS-SOURCE-OWNER-INDEX-CURRENT.md 拥有；用户体验由 00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md 拥有。

本文件仅供日期明确的 ADR 历史研究和来源追溯。实际实施、权限、数据与用户结果必须另以当前源码和运行证据验收。
