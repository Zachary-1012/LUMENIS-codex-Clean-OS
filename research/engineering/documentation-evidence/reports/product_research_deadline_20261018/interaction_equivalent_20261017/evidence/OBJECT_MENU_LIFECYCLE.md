# 33对象菜单与弹层生命周期修复

依据现行完整规划§18的上下文菜单/键盘可达和Experience的对象、版本、权限/来源绑定；本例依然只有人工研究篮，无产品请求。2026-10-17实际读取官方 [APG Menu Button](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/) 与 [Menu and Menubar](https://www.w3.org/WAI/ARIA/apg/patterns/menubar/) 的键盘/焦点规范，选择按钮与上下文操作共用同一菜单，禁用项可聚焦但不执行。

修复内容：
- choose重复激活不再保留上次effect，避免重复本地动作；关闭菜单move不生成NaN。
- 引用动作绑定打开时的精确片段及对象revision；撤权/片段/对象版本改变均拒绝旧动作。
- 移除、撤销产生新局部revision；已移除项不能再次移除。
- 菜单代次隔离旧节点回调，旧菜单按钮不能作用于新打开菜单。
- Enter/Space、ShiftF10、上下键、Home/End、Escape及Tab路径明确；焦点回到可用触发元素，否则安全工作区。
- Tab不阻止原生后续遍历；外部pointer/focusout关闭而不夺新目标焦点。resize/scroll/blur关闭，卸载清监听及失效回调。
- 权限夹具放统一设置；触控始终可用显式资料操作按钮，不要求右键。

8条纯逻辑+8条最小DOM实际测试覆盖上述合同。原生Tab顺序、读屏宣读、触屏及视觉仍需真实浏览器验收，当前只记录BROWSER_PENDING，不能把模拟focus计为可访问性完成。接口仍沿createObjectMenu，settingsRoot是新增可选注入；objectMenu state新增selection/effect字段以明确快照与单次效果，原公开函数名保留。没有新增入口或新的业务写入。
