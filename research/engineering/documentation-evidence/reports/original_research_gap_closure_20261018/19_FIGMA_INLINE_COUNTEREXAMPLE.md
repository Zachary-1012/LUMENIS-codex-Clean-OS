# Figma内联脚本盲区的第二次控制分析

2026-10-18；接17报告，C6研究工具、F消息边界、C5证据映射。静态研究真实执行，无目标运行。

为区分“解析器根本未读内联JS”和“解析成功即应有完整消息发现”，把固定Figma ui.html唯一script正文原样提取为独立分析衍生物。原始HTML完全不改，保留来源SHA256、原文起点和衍生文件SHA256；不把衍生物冒充官方独立JS文件。

REA 6.5.0静态分析衍生文件成功exit0，1个JS、47 AST节点、0解析失败；图3节点2边，findings=0。原源码仍明确存在window.onmessage、按钮事件与parent.postMessage。说明即使消除HTML内联漏读，分析器“零finding”也不能成为零消息行为或零风险的证明。

采用结论：
1. REA提供artifact与语法候选证据，人工源码审阅必须覆盖工具声明和实际未覆盖的消息边界。
2. findings计数与解析成功率分别展示，均不得叫功能覆盖率/风险覆盖率。
3. 衍生物必须保存原件映射；独立JS输入失去完整HTML执行上下文，不能据此判断真实window/parent绑定、事件执行或宿主安全。
4. 本例不是Figma漏洞报告，也没有证明序境已存在同类缺陷。对应产品测试仍未运行。

收据：rea_public_reconstruction/evidence/FIGMA_DERIVATION.json、figma_inline_derived_rea_analysis.json、figma_inline_derived_stderr.log、figma_inline_derived_exit.txt；输入在figma_inline_derived/ui_inline_1.js。该增量发生在18清单冻结后，另见20清单。
