# SYS-02 — 草图增补：采集：默认 AUTO + 可选手动采集按钮

> 草稿，未入仓库。格式按 SCREEN_SPEC_TEMPLATE §5/§5A/§6；只升级，不改原有内容。规划依据：O1,G2。

## 5. Purpose-built desktop composition
```
主体行：<主体名> | 模式 [AUTO ▾] | 上次 hh:mm | [立即采集] [暂停]
平台矩阵：平台 × 状态（运行/冷却/缺失）
缺失字段显示「—（数据缺失）」不显示 0
```

## 5A. Web Workspace composition
同桌面布局；批量：[对所选主体立即采集]

## 6. Purpose-built mobile composition
主体卡 + 同按钮。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 全部已登记主体默认 AUTO；无单主体硬编码；R&D 期风险闸门关、闭环前开（显示当前状态徽标）。
