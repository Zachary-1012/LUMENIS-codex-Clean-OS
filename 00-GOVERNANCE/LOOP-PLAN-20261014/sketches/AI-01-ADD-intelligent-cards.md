# AI-01 — 草图增补：聊天智能 UI 卡片

> 已入库参考草图；实施与验收归现有ScreenSpec，按§5/§5A/§6原位维护，不自称已实现或已验收。规划依据：G14,G116。

## 5. Purpose-built desktop composition
```
用户：…
序境：[决策卡：选项A/B 依据▸ 证据▸ (采纳)(修改)]
      [表格卡] [表单卡] [图表卡] [证据卡 来源↗]
顶部切换：(卡片模式)(简洁模式)
```

## 5A. Web Workspace composition
Web：输入区与正在完成的任务独立，流式更新不抢输入焦点；卡片按宽度重排，刷新后由服务端读回任务与成果，未保存输入明确保留。

## 6. Purpose-built mobile composition
卡片全宽堆叠。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 用户可选简洁模式。
