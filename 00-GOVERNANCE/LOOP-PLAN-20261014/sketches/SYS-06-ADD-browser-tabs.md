# SYS-06 — 草图增补：内置浏览器：标签/地址栏/前进后退/折叠/查看原文

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：G1,G97。

## 5. Purpose-built desktop composition
```
[◀][▶][⟳] [地址栏 https://… ][☆][⋯]  [⌄折叠]
[标签1 ×][标签2 ×][+]
┌ 真实页面（同一受控会话）┐  右侧：当前任务卡 [返回任务]
└───────────────────────┘  底部：[在外部浏览器查看原文 ↗]（仅用户点，无采集）
```

## 5A. Web Workspace composition
同桌面布局；折叠后收为顶栏胶囊「浏览器·2 个标签」，任务不中断。

## 6. Purpose-built mobile composition
全屏单标签+底部标签切换；折叠为底部条。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 外部打开永不自动触发、永不采集；无 Edge/9222；书签/历史/阅读模式可选。
