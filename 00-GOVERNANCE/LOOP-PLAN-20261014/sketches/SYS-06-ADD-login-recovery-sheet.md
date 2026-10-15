# SYS-06 — 草图增补：产品内登录失效弹窗 LumenisPlatformRecoverySheet

> 已入库参考草图；实施与验收归现有ScreenSpec，按§5/§5A/§6原位维护，不自称已实现或已验收。规划依据：G51,G133。

## 5. Purpose-built desktop composition
```
┌ 小红书（RedNote·香港账号来源）登录已失效 ┐
│ 任务「<主体> 采集」已暂停，进度已保存      │
│ [扫码登录] [在内置浏览器登录] [稍后]       │
│ 状态：等待验证 / 冷却中 mm:ss             │
└──────────────────────────────────────────┘
```

## 5A. Web Workspace composition
Web：受控标签、地址、任务返回和停止始终可达；窄屏将辅助栏展开为独立面板，独占接管与刷新后的会话读回由服务端核验，不能复用个人浏览器。 同一时刻只弹一个；成功后自动回到原任务并续跑。

## 6. Purpose-built mobile composition
底部 Sheet，同内容。

## 4. State additions
Ready / Loading / 数据缺失（显示缺失，不补 0/50）/ 不可用（显示原因，不自动回退）/ 权限不足。

## 9. Executable acceptance
- 三语 zh-CN/en/ko 完整；适用全部已登记主体；无账号墙。
- 后台采集本身不弹窗；仅登录失效弹；适用全部平台与全部已登记主体。
