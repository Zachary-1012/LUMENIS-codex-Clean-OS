# 选择范围与产品 Unicode 单位

当前只读工作树 lumenis/shared/reporting/saved_work.py:961–1001 的局部替换使用Python Unicode code point偏移；浏览器selectionStart/End是UTF-16单位。新增contentSelectionRange只转换已验证、整字素边界的选择，返回原样expected与codepoint start/end，拒绝代理对、组合字符、emoji ZWJ、Indic字素中间边界，不静默扩展选区。无法Intl.Segmenter时明确拒绝局部范围，调用者可提供显式整字段替换路径。

4条实际Node测试覆盖astral前缀偏移、字素切割、12种语言原文与空插入、畸形Unicode/越界/能力缺失。此为可接入纯逻辑，尚未接到产品或新的报告提交。下一文稿示例使用现Flutter相同的整字段expected→value，所以不依赖本helper才能保存。字素边界实现依运行平台Unicode/Intl版本，真实浏览器输入法/选区/字体显示待验。未作翻译或语言理解证明。
