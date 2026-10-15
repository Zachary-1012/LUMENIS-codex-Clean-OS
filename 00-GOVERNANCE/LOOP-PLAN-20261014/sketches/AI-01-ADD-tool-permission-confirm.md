# AI-01 — 草图增补：免命令行工具调用与高风险确认

> 已入库参考草图；实施与验收归现有ScreenSpec，按§5/§5A/§6原位维护，不自称已实现或已验收。规划依据：G115。

## 5. Purpose-built desktop composition
```
┌ 序境要在内置浏览器执行：提交表单 <站点> ┐
│ 权限范围：本任务  风险：高               │
│ [允许一次] [本任务内允许] [拒绝]          │
└──────────────────────────────────────────┘ 执行后留证据卡
```

## 5A. Web Workspace composition
Web：输入区与正在完成的任务独立，流式更新不抢输入焦点；卡片按宽度重排，刷新后由服务端读回任务与成果，未保存输入明确保留。

## 6. Purpose-built mobile composition
底部 Sheet。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 只用注册工具；评论/私信只生成草稿不自动发。
